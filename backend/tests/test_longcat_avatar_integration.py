import json
import subprocess
import sys
from pathlib import Path

import pytest

from app.domain.studios.avatar_generation import longcat_segment_timing
from app.domain.studios.contracts import AvatarVideoRequestV1, AvatarVideoRequestV2
from app.providers.studios.longcat_avatar import LongCatAvatarProvider

ROOT = Path(__file__).resolve().parents[2]
WORKER = ROOT / "workers" / "longcat-avatar"


def v2_request(**changes):
    payload = {
        "expectedDocumentRevision": 3,
        "sceneId": "scene-1",
        "requirementId": "avatar-1",
        "script": "Uma ideia encontra as pessoas.",
        "referenceImageAssetId": "image-1",
        "referenceImageChecksumSha256": "a" * 64,
        "drivingAudioAssetId": "audio-final-1",
        "drivingAudioChecksumSha256": "b" * 64,
        "drivingAudioDurationMs": 3720,
        "drivingAudioOrigin": "cloned_voice_synthesis",
        "performanceDirection": "Plano médio, fala calma e olhar para a câmera.",
        "acceptanceCriteria": ["Identidade estável", "Sincronismo em português"],
        "profileId": "longcat-avatar-1.5-ai2v-480p-int8-experimental-v1",
    }
    payload.update(changes)
    return AvatarVideoRequestV2.model_validate(payload)


def test_v2_requires_final_audio_and_keeps_v1_compatible():
    old = AvatarVideoRequestV1(script="Teste V1.")
    request = v2_request()
    assert old.schema_version == "studio.avatar-video-request.v1"
    assert request.operation == "image_audio_to_avatar"
    assert request.fps == 25
    assert request.width == 832
    assert request.height == 480
    assert request.driving_audio_asset_id != request.reference_image_asset_id


def test_longcat_adapter_rejects_v1_before_network(tmp_path):
    provider = LongCatAvatarProvider("http://127.0.0.1:8095", "x" * 32)
    with pytest.raises(ValueError, match="request_v2_required"):
        provider.render(
            type("Document", (), {"id": "document"})(),
            AvatarVideoRequestV1(script="Teste."),
            [tmp_path / "image.png"],
            tmp_path / "audio.wav",
            tmp_path / "output.mp4",
            lambda _value: None,
            lambda: False,
        )


def test_preflight_is_read_only_and_reports_hardware_blockers():
    completed = subprocess.run(
        [sys.executable, str(WORKER / "preflight.py")],
        check=True,
        capture_output=True,
        text=True,
        timeout=10,
    )
    receipt = json.loads(completed.stdout)
    assert receipt["state"] == "unavailable"
    assert receipt["usableNow"] is False
    assert "weights_not_installed" in receipt["reasons"]
    assert receipt["effectiveParameters"]["segmentFrames"] == 93
    assert receipt["effectiveParameters"]["overlapFrames"] == 13
    assert not (WORKER / ".runs").exists()


def test_manifest_pins_large_binary_checksums_without_downloading_them():
    manifest = json.loads((WORKER / "model-manifest.json").read_text(encoding="utf-8"))
    files = [item for model in manifest["models"] for item in model["files"]]
    assert manifest["status"] == "not_installed"
    assert manifest["runtime"]["vocalSeparatorEnabled"] is False
    assert manifest["runtime"]["cleanAudioOnly"] is True
    assert all(len(item["sha256"]) == 64 and item["sizeBytes"] > 0 for item in files)
    assert not any((WORKER / item["path"]).exists() for item in files)


def test_longcat_continuation_timing_accounts_for_overlap_and_trim():
    native = longcat_segment_timing(3720)
    continued = longcat_segment_timing(10_000)
    assert native.segment_count == 1
    assert native.produced_frames == 93
    assert native.trim_tail_ms == 0
    assert continued.segment_count == 3
    assert continued.produced_frames == 253
    assert continued.produced_duration_ms == 10_120
    assert continued.trim_tail_ms == 120
