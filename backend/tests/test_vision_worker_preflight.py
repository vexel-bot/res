from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
VISION_ROOT = REPOSITORY_ROOT / "workers" / "vision-gpu"
LOCK_DIGEST = "1a40b7d969f33e72e8886ff898789f0191a5c63a63d958555ea23b736ee97fe0"
MANIFEST_DIGEST = "fbe3c7a55ba2d98a7a12a4ae37e8b97b46d2282bcb89cfe5a657d6b60ac0efb1"


def _verify_command(*, lock_path: Path, lock_digest: str = LOCK_DIGEST) -> list[str]:
    return [
        sys.executable,
        str(VISION_ROOT / "verify_build.py"),
        "--backend",
        str(REPOSITORY_ROOT / "backend"),
        "--inventory",
        str(REPOSITORY_ROOT / "benchmarks/studios/reality/pgv1-artifact-inventory.v1.json"),
        "--inventory-digest",
        "d1935d35ed3af59d792a5b0c9607d477ea661a862170f4e8574c7a94015dea0c",
        "--lock",
        str(lock_path),
        "--lock-digest",
        lock_digest,
        "--manifest",
        str(VISION_ROOT / "worker.manifest.json"),
        "--manifest-digest",
        MANIFEST_DIGEST,
        "--policy",
        str(REPOSITORY_ROOT / "benchmarks/studios/reality/physical-plausibility-policy.v1.json"),
        "--policy-digest",
        "8f4ff3bb19caf1c50dd6a6cd627ad6cd8b58f20bd6340f2efdd9abf01712aad0",
    ]


def test_vision_celery_app_exposes_only_attestation_probe() -> None:
    script = """
import json
from app.vision_celery_app import vision_celery_app
import app.vision_tasks
print(json.dumps({
    "include": vision_celery_app.conf.include,
    "registered": sorted(name for name in vision_celery_app.tasks if name.startswith("app.")),
    "eager": vision_celery_app.conf.task_always_eager,
}))
"""
    completed = subprocess.run(
        [sys.executable, "-c", script],
        cwd=REPOSITORY_ROOT / "backend",
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "include": ["app.vision_tasks"],
        "registered": ["app.tasks.probe_studio_worker"],
        "eager": False,
    }


def test_preflight_lock_digest_is_frozen() -> None:
    lock = VISION_ROOT / "requirements.lock"

    assert hashlib.sha256(lock.read_bytes()).hexdigest() == LOCK_DIGEST
    assert all(
        not line or line.startswith("#") or " --hash=sha256:" in line
        for line in lock.read_text(encoding="utf-8").splitlines()
    )


def test_preflight_verifier_accepts_frozen_inputs() -> None:
    completed = subprocess.run(
        _verify_command(lock_path=VISION_ROOT / "requirements.lock"),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "inventoryStatus": "review_required",
        "providers": [],
        "runtime": "clicko-vision-gpu",
        "status": "preflight-verified",
    }


def test_preflight_verifier_rejects_tampered_lock(tmp_path: Path) -> None:
    tampered_lock = tmp_path / "requirements.lock"
    tampered_lock.write_bytes((VISION_ROOT / "requirements.lock").read_bytes() + b"# tampered\n")

    completed = subprocess.run(
        _verify_command(lock_path=tampered_lock),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode != 0
    assert "requirements_lock_digest_mismatch" in completed.stderr
