"""Private Docker/job contracts with an explicit fake daemon, never an ML benchmark."""

import json
import subprocess
import sys
import wave
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

import pytest
from test_kokoro_model_assets import _fixture
from test_voice_clone_sidecar_provider import _request_and_reference, _tiny_openvoice_manifest

from app.config import Settings
from app.domain.studios.execution import OPENVOICE_CPU_PROVIDER, execution_profile
from app.providers.studios import openvoice_cpu
from app.services.object_storage import sha256_file
from app.services.studios.worker_runtime import load_worker_manifest, validate_worker_manifest

ROOT = Path(__file__).resolve().parents[2]


def make_provider(tmp_path):
    assets, manifest_path = tmp_path / "openvoice", tmp_path / "converter.json"
    _tiny_openvoice_manifest(assets, manifest_path)
    snapshot, kokoro = _fixture(tmp_path / "base")
    base_manifest = tmp_path / "base.json"
    base_manifest.write_text(kokoro.model_dump_json(by_alias=True), encoding="utf-8")
    return openvoice_cpu.create_openvoice_cpu_provider(
        manifest_path=manifest_path,
        asset_root=assets,
        kokoro_manifest_path=base_manifest,
        kokoro_repository=snapshot.parent.parent,
        worker_manifest_digest_sha256="a" * 64,
        worker_image_digest="sha256:" + "b" * 64,
        docker_executable=Path(sys.executable),
        cpu_hourly_cost_usd=0.04,
    )


def fake_daemon(monkeypatch, *, behavior="success", mutate=None, cleanup_fails=False, bad_isolation=False):
    state = {"calls": [], "runs": [], "roots": []}

    def docker(self, args, timeout=20):
        state["calls"].append(args)
        state["provider"] = self
        if args[:2] == ["image", "inspect"]:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "Id": self.config.worker_image_digest,
                            "Config": {
                                "Labels": {
                                    "io.clicko.execution-device": "cpu",
                                    "io.clicko.model-manifest.digest": self.config.model_digest_sha256,
                                    "io.clicko.base-model-manifest.digest": self.config.kokoro_model_digest_sha256,
                                    "io.clicko.worker-manifest.digest": self.config.worker_manifest_digest_sha256,
                                }
                            },
                        }
                    ]
                ),
            )
        if args[0] == "create":
            state["create"] = args
            state["roots"].append(
                Path(
                    next(arg for arg in args if "target=/job/output" in arg)
                    .split("source=", 1)[1]
                    .split(",target=", 1)[0]
                ).parent
            )
            return SimpleNamespace(returncode=0, stdout="c" * 64)
        if args[:2] == ["container", "inspect"]:
            created = state["create"]
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "Config": {
                                "Image": self.config.worker_image_digest,
                                "User": created[created.index("--user") + 1],
                            },
                            "HostConfig": {
                                "NetworkMode": "bridge" if bad_isolation else "none",
                                "ReadonlyRootfs": True,
                                "Memory": 3 * 1024**3,
                                "MemorySwap": 3 * 1024**3,
                                "NanoCpus": 4_000_000_000,
                                "PidsLimit": 128,
                                "CapDrop": ["ALL"],
                                "SecurityOpt": ["no-new-privileges"],
                            },
                            "Mounts": [
                                {"Destination": target, "Type": "bind", "RW": writable}
                                for target, writable in (
                                    ("/job/input", False),
                                    ("/job/output", True),
                                    ("/models/kokoro-repo", False),
                                    ("/models/openvoice", False),
                                )
                            ],
                        }
                    ]
                ),
            )
        if args[:2] == ["container", "ls"]:
            return SimpleNamespace(returncode=1 if cleanup_fails else 0, stdout="")
        return SimpleNamespace(returncode=0, stdout="")

    class Process:
        returncode = None

        def __init__(self, args, **kwargs):
            state["runs"].append(args)
            assert args[1:] == ["start", "--attach", "c" * 64]
            created = state["create"]
            mounts = [value for value in created if value.startswith("type=bind,")]
            inputs = Path(
                next(value for value in mounts if "target=/job/input" in value)
                .split("source=", 1)[1]
                .split(",target=", 1)[0]
            )
            output = Path(
                next(value for value in mounts if "target=/job/output" in value)
                .split("source=", 1)[1]
                .split(",target=", 1)[0]
            )
            packet = json.loads((inputs / "request.json").read_text(encoding="utf-8"))
            assert sha256_file(inputs / "reference.wav") == packet["reference"]["normalizedChecksumSha256"]
            cfg = state["provider"].config
            result = {
                "schemaVersion": "clicko.voice-clone-sidecar-result.v1",
                "pipelineContract": openvoice_cpu.PIPELINE,
                "executionDevice": "cpu",
                "watermarkApplied": True,
                "watermarkScheme": "wavmark-0.0.3-local-verified",
                "scriptDigestSha256": packet["speech"]["scriptDigestSha256"],
                "voiceVersionId": packet["reference"]["voiceVersionId"],
                "consentGrantId": packet["reference"]["consentGrantId"],
                "voiceReferenceChecksumSha256": packet["reference"]["normalizedChecksumSha256"],
                "kokoroModelManifestDigestSha256": cfg.kokoro_model_digest_sha256,
                "openvoiceModelManifestDigestSha256": cfg.model_digest_sha256,
                **packet["executionBinding"],
                "wallSeconds": 0.1,
                "peakResidentBytes": 1024,
            }
            if mutate:
                mutate(result)
            with wave.open(str(output / "speech.wav"), "wb") as wav:
                wav.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                wav.writeframes(b"\0\0" * 24000)
            (output / "result.json").write_text(json.dumps(result), encoding="utf-8")
            if behavior == "success":
                self.returncode = 0

        def poll(self):
            return self.returncode

        def kill(self):
            self.returncode = -1

        def wait(self, timeout):
            return self.returncode

    monkeypatch.setattr(openvoice_cpu.OpenVoiceCPUProvider, "_docker", docker)
    monkeypatch.setattr(subprocess, "Popen", Process)
    return state


def test_clone_binds_voice_consent_models_image_and_private_output(tmp_path, monkeypatch):
    provider = make_provider(tmp_path)
    state = fake_daemon(monkeypatch)
    request, reference, source = _request_and_reference(tmp_path)
    destination = tmp_path / "converted.wav"
    result = provider.clone(request, reference, source, destination, lambda _: None, lambda: False)
    assert result.provider == OPENVOICE_CPU_PROVIDER and result.artifact_checksum_sha256 == sha256_file(destination)
    assert result.provenance.voice_version_id == reference.voice_version_id
    assert result.provenance.consent_grant_id == reference.consent_grant_id
    assert result.provenance.voice_reference_checksum_sha256 == reference.normalized_checksum_sha256
    assert result.metrics["containerNetworkDisabled"] == result.metrics["watermarkVerified"] == 1
    assert result.metrics["containerCpuLimit"] == 4
    assert all(not path.exists() for path in state["roots"])


@pytest.mark.parametrize(
    "field",
    [
        "voiceVersionId",
        "consentGrantId",
        "voiceReferenceChecksumSha256",
        "scriptDigestSha256",
        "workerImageDigest",
        "workerManifestDigestSha256",
        "openvoiceModelManifestDigestSha256",
        "kokoroModelManifestDigestSha256",
        "watermarkApplied",
        "executionDevice",
    ],
)
def test_mismatched_receipt_never_persists_an_audio(tmp_path, monkeypatch, field):
    provider = make_provider(tmp_path)
    state = fake_daemon(
        monkeypatch, mutate=lambda result: result.update({field: False if field == "watermarkApplied" else "wrong"})
    )
    request, reference, source = _request_and_reference(tmp_path)
    destination = tmp_path / "converted.wav"
    with pytest.raises(ValueError, match="result_binding_mismatch"):
        provider.clone(request, reference, source, destination, lambda _: None, lambda: False)
    assert not destination.exists() and all(not path.exists() for path in state["roots"])


@pytest.mark.parametrize("reason", ["cancel_before_start", "cancel_during_run", "timeout", "cleanup", "isolation"])
def test_interruption_or_unverified_cleanup_does_not_publish_audio(tmp_path, monkeypatch, reason):
    provider = make_provider(tmp_path)
    state = fake_daemon(
        monkeypatch,
        behavior="running" if reason in {"cancel_during_run", "timeout"} else "success",
        cleanup_fails=reason == "cleanup",
        bad_isolation=reason == "isolation",
    )
    checks = 0

    def cancelled():
        nonlocal checks
        checks += 1
        return checks > (1 if reason == "cancel_before_start" else 2) if reason.startswith("cancel") else False

    if reason == "timeout":
        provider.config = replace(provider.config, timeout_seconds=1)
        clock = iter([0, 2, 3, 4])
        monkeypatch.setattr(
            openvoice_cpu, "time", SimpleNamespace(perf_counter=lambda: next(clock), sleep=lambda _: None)
        )
    request, reference, source = _request_and_reference(tmp_path)
    destination = tmp_path / "converted.wav"
    with pytest.raises((InterruptedError, TimeoutError, ValueError, RuntimeError)):
        provider.clone(request, reference, source, destination, lambda _: None, cancelled)
    assert any(call[:3] == ["container", "rm", "--force"] for call in state["calls"])
    assert not destination.exists() and all(not path.exists() for path in state["roots"])


def test_reference_tampering_is_rejected_before_daemon_access(tmp_path, monkeypatch):
    provider = make_provider(tmp_path)
    state = fake_daemon(monkeypatch)
    request, reference, source = _request_and_reference(tmp_path)
    source.write_bytes(b"tampered")
    with pytest.raises(ValueError, match="reference_checksum_mismatch"):
        provider.clone(request, reference, source, tmp_path / "converted.wav", lambda _: None, lambda: False)
    assert not state["calls"]


@pytest.mark.parametrize("invalid", ["missing_converter", "invalid_base"])
def test_model_manifest_unavailable_is_a_configuration_error_without_host_path(tmp_path, invalid):
    provider = make_provider(tmp_path)
    converter, base = tmp_path / "converter.json", tmp_path / "base.json"
    if invalid == "missing_converter":
        converter.unlink()
    else:
        base.write_text("not-json", encoding="utf-8")
    with pytest.raises(ValueError, match="^openvoice_cpu_model_manifest_invalid$"):
        openvoice_cpu.create_openvoice_cpu_provider(
            manifest_path=converter,
            asset_root=provider.asset_root,
            kokoro_manifest_path=base,
            kokoro_repository=provider.kokoro_repository,
            worker_manifest_digest_sha256=provider.config.worker_manifest_digest_sha256,
            worker_image_digest=provider.config.worker_image_digest,
            docker_executable=Path(sys.executable),
            cpu_hourly_cost_usd=0.04,
        )


def test_cpu_job_profile_and_manifest_do_not_reassign_gpu_providers():
    assert execution_profile("voice_clone", OPENVOICE_CPU_PROVIDER).capability == "speech_cpu"
    assert execution_profile("voice_clone").capability == "speech_gpu"
    assert execution_profile("voice_clone", "candidate.chatterbox-pt-br").capability == "speech_gpu"
    manifest = load_worker_manifest(ROOT / "workers/speech-cpu/openvoice.worker.manifest.json")
    assert manifest.providers == []
    manifest = manifest.model_copy(update={"required_environment": [], "required_paths": []})
    settings = Settings(
        studio_isolated_queues_enabled=True, celery_task_always_eager=False, studio_worker_capability="speech_cpu"
    )
    assert (
        validate_worker_manifest(manifest, settings, tool_runner=lambda _: "Python 3.11.9")["python"] == "Python 3.11.9"
    )
    with pytest.raises(ValueError, match="worker_job_queue_mismatch"):
        validate_worker_manifest(manifest.model_copy(update={"queues": ["studio.gpu.speech"]}), settings)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.update(watermarkApplied=1),
        lambda value: value.update(wallSeconds=float("nan")),
        lambda value: value.update(peakResidentBytes=-1),
    ],
)
def test_receipt_requires_a_boolean_watermark_and_measured_finite_metrics(tmp_path, monkeypatch, mutate):
    provider = make_provider(tmp_path)
    fake_daemon(monkeypatch, mutate=mutate)
    request, reference, source = _request_and_reference(tmp_path)
    destination = tmp_path / "converted.wav"
    with pytest.raises(ValueError, match="result_(binding_mismatch|metrics_invalid)"):
        provider.clone(request, reference, source, destination, lambda _: None, lambda: False)
    assert not destination.exists()


def test_project_uses_configured_cpu_clone_and_keeps_its_voice_and_history(client, tmp_path, monkeypatch):
    from test_project_narration import prepare

    from app.config import get_settings
    from app.database import SessionLocal
    from app.domain.studios.providers import VOICE_CLONE_PROVIDERS
    from app.models import StudioGenerationJob, StudioModelRegistration, StudioProviderRegistration, StudioVoiceVersion
    from app.services.studios.jobs import execute_job_once
    from app.services.studios.worker_runtime import manifest_digest

    case = prepare(client, monkeypatch, tmp_path, kind="cloned", format="video")
    provider = make_provider(tmp_path / "models")
    worker = load_worker_manifest(ROOT / "workers/speech-cpu/openvoice.worker.manifest.json").model_copy(
        update={"providers": [OPENVOICE_CPU_PROVIDER]}
    )
    worker_path = tmp_path / "admission-fixture-worker.json"
    worker_path.write_text(worker.model_dump_json(by_alias=True), encoding="utf-8")
    config_path = tmp_path / "runtime.json"
    config_path.write_text(
        json.dumps(
            {
                "schemaVersion": "studio.speech-runtime-config.v1",
                "runtimes": [
                    {
                        "kind": "kokoro-openvoice-cpu-docker",
                        "dockerExecutable": sys.executable,
                        "manifestPath": str(tmp_path / "models/converter.json"),
                        "assetRoot": str(provider.asset_root),
                        "kokoroManifestPath": str(tmp_path / "models/base.json"),
                        "kokoroRepository": str(provider.kokoro_repository),
                        "workerManifestPath": str(worker_path),
                        "workerImageDigest": provider.config.worker_image_digest,
                        "cpuHourlyCostUsd": 0.04,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(get_settings(), "studio_speech_runtime_config_file", str(config_path))
    with SessionLocal() as db:
        registration = StudioProviderRegistration(
            capability="voice_clone",
            provider=provider.name,
            provider_version=provider.version,
            source_url="https://example.invalid/explicit-admission-fixture",
            source_revision=provider.config.source_revision,
            code_license="MIT",
            status="approved",
            manifest={
                "benchmarkStatus": "passed",
                "workerAdvertised": True,
                "runtimeBinding": {
                    "schemaVersion": "studio.speech-runtime-binding.v1",
                    "kind": "kokoro-openvoice-cpu-docker",
                    "sourceRevision": provider.config.source_revision,
                    "modelDigestSha256": provider.config.model_digest_sha256,
                    "workerManifestDigestSha256": manifest_digest(worker),
                    "workerImageDigest": provider.config.worker_image_digest,
                },
            },
        )
        db.add(registration)
        db.flush()
        db.add(
            StudioModelRegistration(
                provider_registration_id=registration.id,
                name="Explicit CPU admission fixture",
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
        voice = db.get(StudioVoiceVersion, case.voice_id)
        voice.pronunciation_profile = {"synthesisBinding": {"provider": provider.name}}
        db.commit()
    state = fake_daemon(monkeypatch)
    status = client.get(case.path, headers=case.headers)
    assert status.status_code == 200 and status.json()["canGenerate"]
    assert not state["calls"]  # Resolving a configuration never launches or imports a model.
    response = client.post(case.path, headers=case.headers, json=case.body)
    assert response.status_code == 202, response.text
    replay = client.post(case.path, headers=case.headers, json=case.body)
    assert replay.json()["job"]["id"] == response.json()["job"]["id"]
    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, response.json()["job"]["id"])
        assert job.provider == provider.name and job.execution_capability == "speech_cpu"
        assert job.queue_name == "studio.speech.cpu" and job.resource_class == "cpu.speech"
        assert job.voice_version_id == case.voice_id and job.consent_grant_id == case.grant_id
        assert execute_job_once(db, job) == "succeeded", job.error_message
        assert job.worker_execution_context["attested"] is False
    loaded = client.get(case.path, headers=case.headers).json()
    assert loaded["job"]["status"] == "succeeded" and loaded["assetId"]
    monkeypatch.setattr(get_settings(), "studio_speech_runtime_config_file", None)
    reopened = client.get(case.path, headers=case.headers).json()
    assert reopened["assetId"] == loaded["assetId"]
    assert client.get(f"/api/v1/assets/{loaded['assetId']}/content", headers=case.headers).status_code == 200
    assert provider.name not in VOICE_CLONE_PROVIDERS
