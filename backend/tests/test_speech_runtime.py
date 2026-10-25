"""Runtime configuration and real DB admission; no model or GPU qualification."""

import json
import os
import sys
from pathlib import Path

import pytest

from app.config import get_settings
from app.database import SessionLocal
from app.domain.studios.providers import SPEECH_PROVIDERS, VOICE_CLONE_PROVIDERS
from app.models import StudioModelRegistration, StudioProviderRegistration
from app.services.studios.speech_runtime import (
    load_speech_runtime_configuration,
    resolve_speech_provider,
)
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest

ROOT = Path(__file__).resolve().parents[2]
PROVIDER = "kokoro-82m-stock"
VERSION = "kokoro-aaaaaaaaaaaa+model-bbbbbbbbbbbb"


def setup(monkeypatch, tmp_path, advertised=True):
    worker = json.loads((ROOT / "workers/speech-cpu/worker.manifest.json").read_text())
    worker["providers"] = [PROVIDER] if advertised else []
    worker_path = tmp_path / "worker.json"
    worker_path.write_text(json.dumps(worker))
    spec = {
        "kind": "kokoro-docker",
        "dockerExecutable": str(Path(sys.executable).resolve()),
        "sourceRevision": "a" * 40,
        "modelRevision": "b" * 40,
        "modelDigestSha256": "c" * 64,
        "workerManifestPath": str(worker_path),
        "workerImageDigest": "sha256:" + "d" * 64,
        "cpuHourlyCostUsd": 0.04,
    }
    path = tmp_path / "runtimes.json"
    payload = {"schemaVersion": "studio.speech-runtime-config.v1", "runtimes": [spec]}
    path.write_text(json.dumps(payload))
    monkeypatch.setattr(get_settings(), "studio_speech_runtime_config_file", str(path))
    binding = {
        "schemaVersion": "studio.speech-runtime-binding.v1",
        "kind": spec["kind"],
        "sourceRevision": spec["sourceRevision"],
        "modelDigestSha256": spec["modelDigestSha256"],
        "workerManifestDigestSha256": manifest_digest(load_worker_manifest(worker_path)),
        "workerImageDigest": spec["workerImageDigest"],
    }
    return path, payload, binding


def admit(db, binding):
    provider = StudioProviderRegistration(
        capability="stock_voice",
        provider=PROVIDER,
        provider_version=VERSION,
        source_url="https://example.invalid/explicit-contract-fixture",
        source_revision="a" * 40,
        code_license="MIT",
        status="approved",
        manifest={"benchmarkStatus": "passed", "workerAdvertised": True, "runtimeBinding": binding},
    )
    db.add(provider)
    db.flush()
    model = StudioModelRegistration(
        provider_registration_id=provider.id,
        name="Explicit contract fixture",
        version="test",
        digest_sha256="c" * 64,
        model_license="MIT",
        commercial_use="approved",
        languages=["pt-BR"],
        capabilities=["stock_voice"],
        status="approved",
        manifest={"benchmarkStatus": "passed"},
    )
    db.add(model)
    db.commit()
    return provider, model


def test_configuration_alone_never_admits_or_registers_a_model(monkeypatch, tmp_path):
    setup(monkeypatch, tmp_path)
    with SessionLocal() as db:
        with pytest.raises(ValueError, match="speech_provider_not_approved"):
            resolve_speech_provider(db, job_type="stock_voice", provider_name=PROVIDER)
    assert PROVIDER not in SPEECH_PROVIDERS and not VOICE_CLONE_PROVIDERS


def test_exact_binding_resolves_lazily_and_revocation_is_fresh(monkeypatch, tmp_path):
    _, _, binding = setup(monkeypatch, tmp_path)
    previous_environment = {key: os.environ.get(key) for key in ("HF_HOME", "HF_HUB_OFFLINE")}
    with SessionLocal() as db:
        provider, _ = admit(db, binding)
        adapter = resolve_speech_provider(db, job_type="stock_voice", provider_name=PROVIDER)
        assert adapter.name == PROVIDER and adapter.version == VERSION
        assert adapter.config.worker_image_digest == binding["workerImageDigest"]
        assert PROVIDER not in SPEECH_PROVIDERS
        provider.status = "revoked"
        db.commit()
        with pytest.raises(ValueError, match="speech_provider_not_approved"):
            resolve_speech_provider(db, job_type="stock_voice", provider_name=PROVIDER)
    assert {key: os.environ.get(key) for key in previous_environment} == previous_environment


def test_older_release_does_not_shadow_the_exact_admitted_runtime(monkeypatch, tmp_path):
    _, _, binding = setup(monkeypatch, tmp_path)
    with SessionLocal() as db:
        db.add(
            StudioProviderRegistration(
                capability="stock_voice",
                provider=PROVIDER,
                provider_version="old-pending-benchmark",
                source_url="https://example.invalid/older-contract-fixture",
                source_revision="e" * 40,
                code_license="MIT",
                status="approved",
                manifest={"benchmarkStatus": "pending"},
            )
        )
        db.flush()
        admit(db, binding)
        assert resolve_speech_provider(db, job_type="stock_voice", provider_name=PROVIDER).version == VERSION


@pytest.mark.parametrize("tamper", ["binding", "model", "version", "source", "benchmark", "worker"])
def test_runtime_rejects_different_or_unqualified_release(monkeypatch, tmp_path, tamper):
    _, _, binding = setup(monkeypatch, tmp_path, advertised=tamper != "worker")
    with SessionLocal() as db:
        provider, model = admit(db, binding)
        if tamper == "binding":
            provider.manifest = {
                **provider.manifest,
                "runtimeBinding": {**binding, "workerImageDigest": "sha256:" + "e" * 64},
            }
        elif tamper == "model":
            model.digest_sha256 = "e" * 64
        elif tamper == "version":
            provider.provider_version = "different-release"
        elif tamper == "source":
            provider.source_revision = "e" * 40
        elif tamper == "benchmark":
            model.manifest = {"benchmarkStatus": "pending"}
        db.commit()
        with pytest.raises(ValueError):
            resolve_speech_provider(db, job_type="stock_voice", provider_name=PROVIDER)
    assert PROVIDER not in SPEECH_PROVIDERS


@pytest.mark.parametrize("invalid", ["relative", "duplicate", "unknown", "huge", "bad-json"])
def test_invalid_configuration_fails_without_execution_or_path_disclosure(monkeypatch, tmp_path, invalid):
    path, payload, _ = setup(monkeypatch, tmp_path)
    if invalid == "relative":
        payload["runtimes"][0]["dockerExecutable"] = "docker"
    elif invalid == "duplicate":
        payload["runtimes"] *= 2
    elif invalid == "unknown":
        payload["runtimes"][0]["kind"] = "arbitrary-import"
    path.write_text(" " * 65537 if invalid == "huge" else "{" if invalid == "bad-json" else json.dumps(payload))
    with pytest.raises(ValueError, match="^speech_runtime_configuration_invalid$"):
        load_speech_runtime_configuration()


def test_unconfigured_runtime_is_unavailable_without_side_effects(monkeypatch):
    monkeypatch.setattr(get_settings(), "studio_speech_runtime_config_file", None)
    with SessionLocal() as db:
        assert resolve_speech_provider(db, job_type="voice_clone", provider_name="candidate.chatterbox-pt-br") is None


@pytest.mark.parametrize("kind", ["chatterbox-multilingual-v3", "chatterbox-pt-br", "kokoro-openvoice-v2"])
def test_clone_configuration_builds_the_pinned_existing_adapter(monkeypatch, tmp_path, kind):
    from app.services.studios.speech_runtime import CloneRuntime, _construct

    spec = CloneRuntime(
        kind=kind,
        worker_manifest_path=tmp_path / "worker.json",
        worker_image_digest="sha256:" + "a" * 64,
        manifest_path=ROOT
        / "workers/speech-gpu"
        / ("openvoice-model-assets.v1.json" if kind == "kokoro-openvoice-v2" else "chatterbox-model-assets.v1.json"),
        asset_root=tmp_path / "models",
        command=(str(Path(sys.executable).resolve()), "private-sidecar.py"),
        gpu_hourly_cost_usd=1,
    )
    adapter = _construct(spec, "b" * 64)
    assert adapter.name == "candidate." + kind
    assert adapter.execution_environment == "local"
    assert adapter.config.worker_image_digest == spec.worker_image_digest
    assert adapter.config.worker_manifest_digest_sha256 == "b" * 64
    assert adapter.config.watermark_required is True
    assert adapter.name not in VOICE_CLONE_PROVIDERS


def test_project_narration_uses_configured_runtime_without_registry_injection(client, monkeypatch, tmp_path):
    from test_project_narration import prepare
    from test_speech_synthesis_execution import FakeSpeechProvider

    from app.domain.studios.contracts import SpeechProvenanceV1
    from app.models import StudioGenerationJob, StudioVoiceVersion
    from app.providers.studios.kokoro_docker import KokoroDockerSpeechProvider
    from app.services.studios.jobs import execute_job_once

    case = prepare(client, monkeypatch, tmp_path, kind="stock", format="video")
    _, _, binding = setup(monkeypatch, tmp_path)

    def synthesize(self, request, destination, progress, cancelled):
        assert request.voice_key == "pf_dora"
        result = FakeSpeechProvider.synthesize(self, request, destination, progress, cancelled)
        return result.model_copy(
            update={
                "provenance": SpeechProvenanceV1(
                    source_revision=self.config.source_revision,
                    model_digest_sha256=self.config.model_digest_sha256,
                    worker_manifest_digest_sha256=self.config.worker_manifest_digest_sha256,
                    worker_image_digest=self.config.worker_image_digest,
                    provenance_mode="explicit-silent-test-fixture",
                )
            }
        )

    monkeypatch.setattr(KokoroDockerSpeechProvider, "synthesize", synthesize)
    with SessionLocal() as db:
        admit(db, binding)
        voice = db.get(StudioVoiceVersion, case.voice_id)
        voice.pronunciation_profile = {"synthesisBinding": {"provider": PROVIDER, "voiceKey": "pf_dora"}}
        db.commit()
    assert PROVIDER not in SPEECH_PROVIDERS
    state = client.get(case.path, headers=case.headers).json()
    assert state["canGenerate"]
    response = client.post(case.path, headers=case.headers, json=case.body)
    assert response.status_code == 202, response.text
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["job"]["id"])
        assert job.provider == PROVIDER and job.voice_version_id == case.voice_id
        assert execute_job_once(db, job) == "succeeded", job.error_message
    monkeypatch.setattr(get_settings(), "studio_speech_runtime_config_file", None)
    saved = client.get(case.path, headers=case.headers).json()
    assert saved["job"]["status"] == "succeeded" and saved["assetId"]
    audio = client.get(f"/api/v1/assets/{saved['assetId']}/content", headers=case.headers)
    assert audio.status_code == 200 and audio.content.startswith(b"RIFF")
    assert PROVIDER not in SPEECH_PROVIDERS
