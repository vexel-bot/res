"""Container lifecycle contracts use an explicit fake daemon, not an ML benchmark."""

import hashlib
import json
import subprocess
import sys
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.domain.studios.contracts import SpeechSynthesisRequestV1, SpeechSynthesisResultV1
from app.providers.studios.kokoro_docker import CONTRACT, KokoroDockerSpeechProvider, SpeechDockerExecutionError
from app.providers.studios.kokoro_stock import KokoroStockConfig
from app.services.object_storage import sha256_file


def config():
    return KokoroStockConfig(
        source_revision="a" * 40,
        model_revision="b" * 40,
        model_digest_sha256="c" * 64,
        worker_manifest_digest_sha256="d" * 64,
        worker_image_digest="sha256:" + "e" * 64,
        cpu_hourly_cost_usd=0.04,
    )


def request():
    text = "Áudio de teste do contrato, sem inferência real."
    return SpeechSynthesisRequestV1(
        text=text,
        locale="pt-BR",
        script_digest_sha256=hashlib.sha256(text.encode()).hexdigest(),
        voice_key="pf_dora",
    )


def setup(monkeypatch, mode="success", mutation=None, cleanup_fails=False):
    provider = KokoroDockerSpeechProvider(config(), docker_executable=Path(sys.executable))
    calls, runs, roots = [], [], []

    def docker(args, timeout=20):
        calls.append(args)
        if args[0] == "create":
            return SimpleNamespace(returncode=0, stdout="f" * 64)
        if args[:2] == ["image", "inspect"]:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps(
                    [
                        {
                            "Id": config().worker_image_digest,
                            "Config": {
                                "Labels": {
                                    "io.clicko.sidecar.contract": CONTRACT,
                                    "io.clicko.model-manifest.digest": config().model_digest_sha256,
                                }
                            },
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
            runs.append((args, kwargs))
            assert args[1:] == ["start", "--attach", "f" * 64]
            args = next(call for call in calls if call[0] == "create")
            input_mount = next(arg for arg in args if arg.endswith("target=/job/input,readonly"))
            output_mount = next(arg for arg in args if arg.endswith("target=/job/output"))
            inputs = Path(input_mount.split("source=", 1)[1].split(",target=", 1)[0])
            outputs = Path(output_mount.split("source=", 1)[1].split(",target=", 1)[0])
            roots.append(outputs.parent)
            assert json.loads((inputs / "request.json").read_text(encoding="utf-8"))["text"] == request().text
            assert (
                json.loads((inputs / "config.json").read_text())["worker_image_digest"] == config().worker_image_digest
            )
            audio = outputs / "speech.wav"
            with wave.open(str(audio), "wb") as wav:
                wav.setparams((1, 2, 24000, 0, "NONE", "not compressed"))
                wav.writeframes(b"\0\0" * 2400)
            result = SpeechSynthesisResultV1(
                provider=provider.name,
                provider_version=provider.version,
                audio_format="wav",
                sample_rate=24000,
                duration_ms=100,
                artifact_checksum_sha256=sha256_file(audio),
                provenance={
                    "sourceRevision": config().source_revision,
                    "modelDigestSha256": config().model_digest_sha256,
                    "workerManifestDigestSha256": config().worker_manifest_digest_sha256,
                    "workerImageDigest": config().worker_image_digest,
                    "provenanceMode": "explicit-test-fixture",
                },
            ).model_dump(by_alias=True, mode="json")
            if mutation:
                mutation(result)
            (outputs / "result.json").write_text(json.dumps(result))
            if mode == "success":
                self.returncode = 0
            elif mode == "failure":
                kwargs["stdout"].write(b"private diagnostic fixture\n")
                self.returncode = 1

        def poll(self):
            return self.returncode

        def kill(self):
            self.returncode = -1

        def wait(self, timeout):
            return self.returncode

    monkeypatch.setattr(provider, "_docker", docker)
    monkeypatch.setattr(subprocess, "Popen", Process)
    return provider, calls, runs, roots


def test_offline_pinned_container_and_private_output(monkeypatch, tmp_path):
    provider, calls, runs, roots = setup(monkeypatch)
    destination = tmp_path / "result.wav"
    result = provider.synthesize(request(), destination, lambda _: None, lambda: False)
    assert result.artifact_checksum_sha256 == sha256_file(destination)
    assert runs
    args = next(call for call in calls if call[0] == "create")
    for flag, value in [
        ("--network", "none"),
        ("--pull", "never"),
        ("--memory", "3g"),
        ("--memory-swap", "3g"),
        ("--cap-drop", "ALL"),
        ("--cpus", "4"),
    ]:
        assert args[args.index(flag) + 1] == value
    assert "--read-only" in args
    assert "/tmp:rw,noexec,nosuid,size=256m,mode=1777" in args
    assert "/run/clicko-phonemizer:rw,exec,nosuid,nodev,size=64m,mode=1777" in args
    assert "TMPDIR=/run/clicko-phonemizer" in args
    assert args[args.index("--user") + 1].split(":")[0] != "0"
    assert config().worker_image_digest in args
    assert calls[-2][:3] == ["container", "rm", "--force"]
    assert calls[-1][:3] == ["container", "ls", "--all"]
    assert all(not path.exists() for path in roots)


@pytest.mark.parametrize("reason", ["cancel_before_start", "cancel_during_run", "timeout"])
def test_cancel_or_timeout_removes_daemon_container(monkeypatch, tmp_path, reason):
    provider, calls, _, roots = setup(monkeypatch, mode="running")
    if reason == "timeout":
        provider.timeout_seconds = -1  # Explicit clock fixture after validating the public constructor.
    checks = 0

    def cancelled():
        nonlocal checks
        checks += 1
        return (reason == "cancel_before_start" and checks > 1) or (reason == "cancel_during_run" and checks > 2)

    destination = tmp_path / "result.wav"
    with pytest.raises(TimeoutError if reason == "timeout" else InterruptedError):
        provider.synthesize(request(), destination, lambda _: None, cancelled)
    assert any(call[:3] == ["container", "rm", "--force"] for call in calls)
    assert not destination.exists() and all(not path.exists() for path in roots)


@pytest.mark.parametrize("field", ["workerImageDigest", "modelDigestSha256", "workerManifestDigestSha256"])
def test_result_cannot_claim_another_runtime(monkeypatch, tmp_path, field):
    def mutate(result):
        result["provenance"][field] = ("sha256:" if field == "workerImageDigest" else "") + "f" * 64

    provider, _, _, roots = setup(monkeypatch, mutation=mutate)
    destination = tmp_path / "result.wav"
    with pytest.raises(ValueError, match="speech_docker_result_binding_mismatch"):
        provider.synthesize(request(), destination, lambda _: None, lambda: False)
    assert not destination.exists() and all(not path.exists() for path in roots)


def test_unknown_cleanup_prevents_persisting_audio(monkeypatch, tmp_path):
    provider, _, _, roots = setup(monkeypatch, cleanup_fails=True)
    destination = tmp_path / "result.wav"
    with pytest.raises(RuntimeError, match="speech_docker_cleanup_unverified"):
        provider.synthesize(request(), destination, lambda _: None, lambda: False)
    assert not destination.exists() and all(not path.exists() for path in roots)


def test_missing_or_replaced_image_never_starts_container(monkeypatch, tmp_path):
    provider, _, runs, _ = setup(monkeypatch)
    monkeypatch.setattr(provider, "_docker", lambda *args: SimpleNamespace(returncode=1, stdout="[]"))
    with pytest.raises(ValueError, match="speech_docker_image_binding_mismatch"):
        provider.synthesize(request(), tmp_path / "result.wav", lambda _: None, lambda: False)
    assert not runs


def test_failure_keeps_public_code_separate_from_private_diagnostics(monkeypatch, tmp_path):
    provider, calls, _, roots = setup(monkeypatch, mode="failure")
    destination = tmp_path / "result.wav"
    with pytest.raises(SpeechDockerExecutionError) as error:
        provider.synthesize(request(), destination, lambda _: None, lambda: False)
    assert str(error.value) == "speech_docker_synthesis_failed"
    assert error.value.diagnostics == "private diagnostic fixture\n"
    assert calls[-2][:3] == ["container", "rm", "--force"]
    assert not destination.exists() and all(not path.exists() for path in roots)
