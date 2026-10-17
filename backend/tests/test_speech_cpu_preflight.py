from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SPEECH_ROOT = REPOSITORY_ROOT / "workers" / "speech-cpu"
REQUIREMENTS = REPOSITORY_ROOT / "backend" / "requirements.txt"
REQUIREMENTS_DIGEST = "5c7a2132a641b00e2f52e60503ae71c738335a00c6a62b6aa3c19763fab8cc0e"
MANIFEST_DIGEST = "36f45dd041744f671a68c8980711c44088592da1b06a3ce77c725bce074b4837"
POLICY_DIGEST = "97dcfb0f58775e4a6b779c0158a72746d39eb24425cf027d1decab2bf9ef55e7"


def _verify_command(*, requirements_path: Path, requirements_digest: str = REQUIREMENTS_DIGEST) -> list[str]:
    return [
        sys.executable,
        str(SPEECH_ROOT / "verify_build.py"),
        "--backend",
        str(REPOSITORY_ROOT / "backend"),
        "--requirements",
        str(requirements_path),
        "--requirements-digest",
        requirements_digest,
        "--manifest",
        str(SPEECH_ROOT / "worker.manifest.json"),
        "--manifest-digest",
        MANIFEST_DIGEST,
        "--policy",
        str(REPOSITORY_ROOT / "benchmarks/studios/identity/voice-stock-pt-br-policy.v1.json"),
        "--policy-digest",
        POLICY_DIGEST,
    ]


def test_speech_cpu_manifest_is_stock_only_and_unadvertised() -> None:
    payload = json.loads((SPEECH_ROOT / "worker.manifest.json").read_text(encoding="utf-8"))
    assert payload["capability"] == "speech_cpu"
    assert payload["jobTypes"] == ["stock_voice"]
    assert payload["providers"] == []


def test_speech_cpu_requirements_digest_is_frozen() -> None:
    assert hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest() == REQUIREMENTS_DIGEST


def test_speech_cpu_preflight_verifier_accepts_frozen_inputs() -> None:
    completed = subprocess.run(
        _verify_command(requirements_path=REQUIREMENTS),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "capability": "speech_cpu",
        "policy": "clicko.voice-stock.pt-br.v1",
        "providers": [],
        "runtime": "clicko-speech-cpu",
        "status": "preflight-verified",
    }


def test_speech_cpu_preflight_rejects_tampered_requirements(tmp_path: Path) -> None:
    tampered = tmp_path / "requirements.txt"
    tampered.write_bytes(REQUIREMENTS.read_bytes() + b"\n# tampered\n")

    completed = subprocess.run(
        _verify_command(requirements_path=tampered),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode != 0
    assert "backend_requirements_digest_mismatch" in completed.stderr
