"""Opt-in isolated project test with actual CPU models and a synthetic voice reference.

This does not approve a real provider or voice: registrations exist only in the
temporary test database, and the reference is a previously generated voice.
"""

import json
import os
import shutil
from pathlib import Path

import pytest
from test_project_narration import prepare

from app.database import SessionLocal
from app.domain.studios.providers import VOICE_CLONE_PROVIDERS, VOICE_REFERENCE_NORMALIZERS
from app.models import (
    LibraryAsset,
    StudioGenerationJob,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioVoiceVersion,
)
from app.providers.studios.openvoice_cpu import create_openvoice_cpu_provider
from app.providers.studios.voice_reference import FFmpegVoiceReferenceNormalizer
from app.services.object_storage import sha256_file
from app.services.studios.jobs import execute_job_once
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest

ROOT = Path(__file__).resolve().parents[2]
REFERENCE = ROOT / ".codex-runtime/team-sync/openvoice-adapter-20261025-01"
IMAGE = "sha256:7c923389d77263918518a92e0564138b83d69ce00356b91d40650d964e6367f0"


@pytest.mark.skipif(os.getenv("CLICKO_TEST_REAL_OPENVOICE") != "1", reason="Explicit local real-model test only")
def test_project_narration_runs_real_openvoice_with_synthetic_reference(client, tmp_path, monkeypatch):
    receipt = json.loads((REFERENCE / "reference-receipt.json").read_text(encoding="utf8"))
    reference = REFERENCE / "input/reference.wav"
    assert receipt["humanSubjects"] == 0 and receipt["voiceKey"] == "pm_alex"
    assert sha256_file(reference) == receipt["speech"]["artifactChecksumSha256"]
    case = prepare(client, monkeypatch, tmp_path, kind="cloned", format="video")
    worker = load_worker_manifest(ROOT / "workers/speech-cpu/openvoice.worker.manifest.json")
    provider = create_openvoice_cpu_provider(
        manifest_path=ROOT / "workers/speech-gpu/openvoice-model-assets.v1.json",
        asset_root=ROOT / ".candidate-build/model-assets/openvoice-v2",
        kokoro_manifest_path=ROOT / ".candidate-build/kokoro-model-assets.json",
        kokoro_repository=ROOT / ".candidate-build/model-assets/kokoro-openvoice-base",
        worker_manifest_digest_sha256=manifest_digest(worker),
        worker_image_digest=IMAGE,
        docker_executable=Path(shutil.which("docker")),
        cpu_hourly_cost_usd=0.04,
        timeout_seconds=900,
    )
    monkeypatch.setitem(VOICE_CLONE_PROVIDERS, provider.name, provider)
    monkeypatch.setitem(
        VOICE_REFERENCE_NORMALIZERS,
        "builtin.ffmpeg-voice-reference-v1",
        FFmpegVoiceReferenceNormalizer(shutil.which("ffmpeg"), 120),
    )
    with SessionLocal() as db:
        voice = db.get(StudioVoiceVersion, case.voice_id)
        asset = db.get(LibraryAsset, voice.sample_asset_ids[0])
        stored = case.storage.put_file(
            reference, key=f"{case.workspace}/fixtures/synthetic-reference.wav", media_type="audio/wav"
        )
        asset.storage_key, asset.storage_backend = stored.key, stored.backend
        asset.checksum_sha256, asset.size_bytes = stored.checksum_sha256, stored.size_bytes
        voice.pronunciation_profile = {**voice.pronunciation_profile, "synthesisBinding": {"provider": provider.name}}
        registration = StudioProviderRegistration(
            capability="voice_clone",
            provider=provider.name,
            provider_version=provider.version,
            source_url="https://example.invalid/temporary-synthetic-fixture",
            source_revision=provider.config.source_revision,
            code_license="MIT",
            status="approved",
            manifest={"benchmarkStatus": "passed", "workerAdvertised": True},
        )
        db.add(registration)
        db.flush()
        db.add(
            StudioModelRegistration(
                provider_registration_id=registration.id,
                name="Temporary synthetic test",
                version="fixture",
                digest_sha256=provider.config.model_digest_sha256,
                model_license="MIT",
                commercial_use="approved",
                languages=["pt-BR"],
                capabilities=["voice_clone"],
                status="approved",
                manifest={"benchmarkStatus": "passed"},
            )
        )
        db.commit()
    response = client.post(case.path, headers=case.headers, json=case.body)
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["job"]["id"])
        assert execute_job_once(db, job) == "succeeded", job.error_message
        assert job.result_payload["speech"]["provenance"]["voiceVersionId"] == case.voice_id
        assert job.result_payload["speech"]["metrics"]["watermarkVerified"] == 1.0
    state = client.get(case.path, headers=case.headers).json()
    assert state["job"]["status"] == "succeeded" and state["assetId"]
    audio = client.get(f"/api/v1/assets/{state['assetId']}/content", headers=case.headers)
    assert audio.status_code == 200 and audio.content[:4] == b"RIFF"
