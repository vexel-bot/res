import hashlib
import json
import subprocess
import sys
from email.parser import BytesParser
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.domain.studios.avatar_generation import longcat_segment_timing
from app.domain.studios.contracts import AvatarVideoRequestV1, AvatarVideoRequestV2
from app.providers.studios import longcat_avatar as transport
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


def transport_fixture(tmp_path, monkeypatch, *, bad_receipt=False, bad_artifact=False, waiting=False):
    """Network protocol fixture; no model is loaded or qualified."""
    image, audio, destination = tmp_path / "image", tmp_path / "audio", tmp_path / "artifact.mp4"
    image.write_bytes(b"portrait-fixture")
    audio.write_bytes(b"final-speech-fixture")
    artifact = b"transport-fixture-only"
    submissions, cancellations = [], []
    current = {}

    def handle(request):
        nonlocal current
        if request.method == "POST" and request.url.path.endswith("/executions"):
            message = BytesParser().parsebytes(
                b"Content-Type: " + request.headers["content-type"].encode() + b"\r\n\r\n" + request.read()
            )
            part = next(p for p in message.walk() if p.get_param("name", header="content-disposition") == "metadata")
            payload = json.loads(part.get_payload(decode=True))
            submissions.append(payload)
            current = {
                "executionId": payload["execution_id"],
                "profileId": payload["profile_id"],
                "requestDigestSha256": "f" * 64 if bad_receipt else payload["request_digest_sha256"],
                "status": "running" if waiting else "succeeded",
                "durationMs": 3720,
                "artifactChecksumSha256": "f" * 64 if bad_artifact else hashlib.sha256(artifact).hexdigest(),
            }
            return httpx.Response(202, json=current)
        if request.url.path.endswith("/artifact"):
            return httpx.Response(200, content=artifact)
        if request.url.path.endswith("/cancel"):
            cancellations.append(request.url.path)
            return httpx.Response(200, json={"status": "cancel_requested"})
        return httpx.Response(200, json=current)

    client = httpx.Client
    monkeypatch.setattr(
        transport.httpx, "Client", lambda **kwargs: client(transport=httpx.MockTransport(handle), **kwargs)
    )
    monkeypatch.setattr(transport.time, "sleep", lambda _seconds: None)
    request = v2_request(
        referenceImageChecksumSha256=hashlib.sha256(image.read_bytes()).hexdigest(),
        drivingAudioChecksumSha256=hashlib.sha256(audio.read_bytes()).hexdigest(),
    )
    return SimpleNamespace(
        image=image,
        audio=audio,
        destination=destination,
        request=request,
        submissions=submissions,
        cancellations=cancellations,
        provider=LongCatAvatarProvider("http://127.0.0.1:8095", "x" * 32),
    )


def test_transport_sends_the_complete_request_and_separates_different_directions(tmp_path, monkeypatch):
    case = transport_fixture(tmp_path, monkeypatch)
    for request in (
        case.request,
        case.request.model_copy(update={"performance_direction": "Outra direção de atuação."}),
    ):
        result = case.provider.render(
            SimpleNamespace(id="document"),
            request,
            [case.image],
            case.audio,
            case.destination,
            lambda _: None,
            lambda: False,
        )
        assert result.duration_ms == request.driving_audio_duration_ms
        assert result.artifact_checksum_sha256 == hashlib.sha256(case.destination.read_bytes()).hexdigest()
    assert case.submissions[0]["avatar_request"] == case.request.model_dump(by_alias=True, mode="json")
    assert case.submissions[0]["execution_id"] != case.submissions[1]["execution_id"]


@pytest.mark.parametrize(
    "kind,code", [("receipt", "receipt_binding_mismatch"), ("artifact", "artifact_checksum_mismatch")]
)
def test_transport_rejects_a_result_bound_to_another_request_or_checksum(tmp_path, monkeypatch, kind, code):
    case = transport_fixture(tmp_path, monkeypatch, bad_receipt=kind == "receipt", bad_artifact=kind == "artifact")
    with pytest.raises(ValueError, match=code):
        case.provider.render(
            SimpleNamespace(id="document"),
            case.request,
            [case.image],
            case.audio,
            case.destination,
            lambda _: None,
            lambda: False,
        )
    assert not case.destination.exists()


def test_transport_cancels_the_worker_after_the_polling_deadline(tmp_path, monkeypatch):
    case = transport_fixture(tmp_path, monkeypatch, waiting=True)
    with pytest.raises(ValueError, match="longcat_avatar_timeout"):
        case.provider.render(
            SimpleNamespace(id="document"),
            case.request,
            [case.image],
            case.audio,
            case.destination,
            lambda _: None,
            lambda: False,
        )
    assert len(case.cancellations) == 1
    assert not case.destination.exists()
