from __future__ import annotations

import hashlib
import json
import sys
import wave
from pathlib import Path

import pytest

from app.domain.studios.contracts import (
    SpeechSynthesisRequestV1,
    VoiceCloneReferenceV1,
)
from app.domain.studios.speech_assets import (
    ChatterboxModelAssetManifestV1,
    OpenVoiceModelAssetManifestV1,
)
from app.providers.studios.voice_clone_sidecar import (
    create_chatterbox_sidecar_provider,
    create_openvoice_sidecar_provider,
)
from app.services.object_storage import sha256_file

ROOT = Path(__file__).resolve().parents[2]
OPENVOICE_MANIFEST = ROOT / "workers/speech-gpu/openvoice-model-assets.v1.json"
CHATTERBOX_MANIFEST = ROOT / "workers/speech-gpu/chatterbox-model-assets.v1.json"
SHA = "a" * 64
IMAGE = f"sha256:{'b' * 64}"


def _write_fake_sidecar(path: Path) -> None:
    path.write_text(
        """import argparse, json, wave
p=argparse.ArgumentParser()
p.add_argument('--request', required=True)
p.add_argument('--reference', required=True)
p.add_argument('--output', required=True)
p.add_argument('--result', required=True)
a=p.parse_args()
request=json.load(open(a.request, encoding='utf-8'))
assert request['reference']['retentionMode'] == 'job-ephemeral'
with wave.open(a.reference, 'rb') as source:
    assert source.getnchannels() == 1 and source.getframerate() == 24000
with wave.open(a.output, 'wb') as output:
    output.setnchannels(1); output.setsampwidth(2); output.setframerate(24000)
    output.writeframes(b'\\x00\\x00' * 24000)
result={'schemaVersion':'clicko.voice-clone-sidecar-result.v1'}
result['pipelineContract']=request['pipelineContract']
result['watermarkApplied']=True
json.dump(result, open(a.result, 'w', encoding='utf-8'))
""",
        encoding="utf-8",
    )


def _tiny_openvoice_manifest(root: Path, manifest_path: Path) -> None:
    payload = json.loads(OPENVOICE_MANIFEST.read_text(encoding="utf-8"))
    for index, entry in enumerate(payload["files"]):
        content = f"{entry['runtimePath']}:{index}".encode()
        entry["sizeBytes"] = len(content)
        entry["checksumSha256"] = hashlib.sha256(content).hexdigest()
        target = root / entry["runtimePath"]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    OpenVoiceModelAssetManifestV1.model_validate(payload)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")


def _tiny_chatterbox_manifest(root: Path, manifest_path: Path) -> None:
    payload = json.loads(CHATTERBOX_MANIFEST.read_text(encoding="utf-8"))
    for variant in payload["variants"]:
        for index, entry in enumerate(variant["files"]):
            content = f"{variant['candidateId']}:{entry['runtimePath']}:{index}".encode()
            entry["sizeBytes"] = len(content)
            entry["checksumSha256"] = hashlib.sha256(content).hexdigest()
            target = root / variant["candidateId"] / entry["runtimePath"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
    ChatterboxModelAssetManifestV1.model_validate(payload)
    manifest_path.write_text(json.dumps(payload), encoding="utf-8")


def _request_and_reference(tmp_path: Path):
    text = "Teste privado da voz consentida."
    request = SpeechSynthesisRequestV1(
        locale="pt-BR",
        text=text,
        script_digest_sha256=hashlib.sha256(text.encode()).hexdigest(),
        voice_key="voice-version-001",
    )
    reference_path = tmp_path / "reference.wav"
    with wave.open(str(reference_path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24_000)
        output.writeframes(b"\x00\x00" * 24_000 * 4)
    reference = VoiceCloneReferenceV1(
        voice_version_id=request.voice_key,
        consent_grant_id="consent-001",
        source_asset_id="asset-001",
        source_checksum_sha256="c" * 64,
        normalized_checksum_sha256=sha256_file(reference_path),
        duration_ms=4_000,
    )
    return request, reference, reference_path


def test_openvoice_candidate_sidecar_is_checksum_bound_and_not_self_registered(tmp_path: Path) -> None:
    assets = tmp_path / "openvoice-assets"
    manifest_path = tmp_path / "openvoice-manifest.json"
    script = tmp_path / "fake-sidecar.py"
    _tiny_openvoice_manifest(assets, manifest_path)
    _write_fake_sidecar(script)
    provider = create_openvoice_sidecar_provider(
        manifest_path=manifest_path,
        asset_root=assets,
        worker_manifest_digest_sha256=SHA,
        worker_image_digest=IMAGE,
        command=(sys.executable, str(script)),
        gpu_hourly_cost_usd=0.75,
        timeout_seconds=10,
    )
    request, reference, reference_path = _request_and_reference(tmp_path)
    destination = tmp_path / "output.wav"

    result = provider.clone(request, reference, reference_path, destination, lambda _: None, lambda: False)

    assert provider.name == "candidate.kokoro-openvoice-v2"
    assert result.artifact_checksum_sha256 == sha256_file(destination)
    assert result.provenance.voice_version_id == reference.voice_version_id
    assert result.provenance.consent_grant_id == reference.consent_grant_id
    assert result.provenance.voice_reference_checksum_sha256 == reference.normalized_checksum_sha256
    assert not (tmp_path / "voice-clone-sidecar-request.json").exists()
    assert not (tmp_path / "voice-clone-sidecar-result.json").exists()


def test_chatterbox_variants_keep_distinct_loader_contracts(tmp_path: Path) -> None:
    assets = tmp_path / "chatterbox-assets"
    manifest_path = tmp_path / "chatterbox-manifest.json"
    script = tmp_path / "fake-sidecar.py"
    _tiny_chatterbox_manifest(assets, manifest_path)
    _write_fake_sidecar(script)
    request, reference, reference_path = _request_and_reference(tmp_path)

    for candidate_id, expected_contract in (
        ("chatterbox-multilingual-v3", "chatterbox.multilingual.from-local.v1"),
        ("chatterbox-pt-br", "clicko.chatterbox.pt-br-from-local.v1"),
    ):
        provider = create_chatterbox_sidecar_provider(
            candidate_id=candidate_id,
            manifest_path=manifest_path,
            asset_root=assets,
            worker_manifest_digest_sha256=SHA,
            worker_image_digest=IMAGE,
            command=(sys.executable, str(script)),
            gpu_hourly_cost_usd=0.75,
            timeout_seconds=10,
        )
        assert provider.config.pipeline_contract == expected_contract
        result = provider.clone(
            request,
            reference,
            reference_path,
            tmp_path / f"{candidate_id}.wav",
            lambda _: None,
            lambda: False,
        )
        assert result.provenance.model_digest_sha256 == provider.config.asset_manifest_digest_sha256


def test_sidecar_rechecks_assets_and_rejects_tampering_before_process(tmp_path: Path) -> None:
    assets = tmp_path / "openvoice-assets"
    manifest_path = tmp_path / "openvoice-manifest.json"
    script = tmp_path / "fake-sidecar.py"
    _tiny_openvoice_manifest(assets, manifest_path)
    _write_fake_sidecar(script)
    provider = create_openvoice_sidecar_provider(
        manifest_path=manifest_path,
        asset_root=assets,
        worker_manifest_digest_sha256=SHA,
        worker_image_digest=IMAGE,
        command=(sys.executable, str(script)),
        gpu_hourly_cost_usd=0.75,
        timeout_seconds=10,
    )
    request, reference, reference_path = _request_and_reference(tmp_path)
    (assets / "converter/config.json").write_bytes(b"tampered")

    with pytest.raises(ValueError, match="size_mismatch|checksum_mismatch"):
        provider.clone(
            request,
            reference,
            reference_path,
            tmp_path / "must-not-exist.wav",
            lambda _: None,
            lambda: False,
        )

    assert not (tmp_path / "must-not-exist.wav").exists()


def test_sidecar_cancellation_terminates_process_and_cleans_control_files(tmp_path: Path) -> None:
    assets = tmp_path / "openvoice-assets"
    manifest_path = tmp_path / "openvoice-manifest.json"
    script = tmp_path / "sleeping-sidecar.py"
    _tiny_openvoice_manifest(assets, manifest_path)
    script.write_text("import time; time.sleep(30)\n", encoding="utf-8")
    provider = create_openvoice_sidecar_provider(
        manifest_path=manifest_path,
        asset_root=assets,
        worker_manifest_digest_sha256=SHA,
        worker_image_digest=IMAGE,
        command=(sys.executable, str(script)),
        gpu_hourly_cost_usd=0.75,
        timeout_seconds=10,
    )
    request, reference, reference_path = _request_and_reference(tmp_path)
    checks = 0

    def cancelled() -> bool:
        nonlocal checks
        checks += 1
        return checks >= 3

    with pytest.raises(InterruptedError, match="cancelled_during_inference"):
        provider.clone(
            request,
            reference,
            reference_path,
            tmp_path / "cancelled.wav",
            lambda _: None,
            cancelled,
        )

    assert not (tmp_path / "cancelled.wav").exists()
    assert not (tmp_path / "voice-clone-sidecar-request.json").exists()
    assert not (tmp_path / "voice-clone-sidecar-result.json").exists()
