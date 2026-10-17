from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

from app.domain.studios.execution import execution_profile
from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
LLM_ROOT = REPOSITORY_ROOT / "workers" / "llm-gpu"
POLICY_DIGEST = "88a37ca064d36a8b0f3c58fe4751f0a721b008359a80fe62212c452b4b17bc54"
QWEN_INVENTORY_DIGEST = "b81d63250d935ca5f6875a57fee0e44051ba706dbf96e8e081bb9c815acd6f67"
KIMI_INVENTORY_DIGEST = "2f747a155fa2b5182a82cf5804090feeed5968390bf41bc7174311b76d0a251d"
LOCK_DIGEST = "1a40b7d969f33e72e8886ff898789f0191a5c63a63d958555ea23b736ee97fe0"
MANIFEST_DIGEST = "102c8edaabec362d64be1c1b70955fbb8de4f7124d09d3d298a97265575cc6c1"


def _verify_command(*, lock_path: Path, lock_digest: str = LOCK_DIGEST) -> list[str]:
    return [
        sys.executable,
        str(LLM_ROOT / "verify_build.py"),
        "--backend",
        str(REPOSITORY_ROOT / "backend"),
        "--qwen-inventory",
        str(LLM_ROOT / "providers/qwen3-planning-copy.artifacts.json"),
        "--qwen-inventory-digest",
        QWEN_INVENTORY_DIGEST,
        "--kimi-inventory",
        str(LLM_ROOT / "providers/kimi-k2-5-planning-copy.artifacts.json"),
        "--kimi-inventory-digest",
        KIMI_INVENTORY_DIGEST,
        "--lock",
        str(lock_path),
        "--lock-digest",
        lock_digest,
        "--manifest",
        str(LLM_ROOT / "worker.manifest.json"),
        "--manifest-digest",
        MANIFEST_DIGEST,
        "--policy",
        str(REPOSITORY_ROOT / "benchmarks/studios/intelligence/planning-copy-pt-br-policy.v1.json"),
        "--policy-digest",
        POLICY_DIGEST,
    ]


def test_llm_execution_profile_isolated_from_vision() -> None:
    profile = execution_profile("planning_copy")

    assert profile.capability == "llm_gpu"
    assert profile.queue == "studio.gpu.llm"
    assert profile.resource_class == "gpu.llm"


def test_llm_manifest_is_fail_closed_and_recomputable() -> None:
    manifest = load_worker_manifest(LLM_ROOT / "worker.manifest.json")

    assert manifest_digest(manifest) == MANIFEST_DIGEST
    assert manifest.capability == "llm_gpu"
    assert manifest.job_types == ["planning_copy"]
    assert manifest.providers == []
    assert manifest.accelerator is not None
    assert manifest.accelerator.minimum_memory_mib == 22_528


def test_llm_celery_app_exposes_only_attestation_probe() -> None:
    script = """
import json
from app.llm_celery_app import llm_celery_app
import app.llm_tasks
print(json.dumps({
    "include": llm_celery_app.conf.include,
    "registered": sorted(name for name in llm_celery_app.tasks if name.startswith("app.")),
    "eager": llm_celery_app.conf.task_always_eager,
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
        "include": ["app.llm_tasks"],
        "registered": ["app.tasks.probe_studio_worker"],
        "eager": False,
    }


def test_llm_preflight_lock_digest_is_frozen() -> None:
    lock = LLM_ROOT / "requirements.lock"

    assert hashlib.sha256(lock.read_bytes()).hexdigest() == LOCK_DIGEST
    assert all(
        not line or line.startswith("#") or " --hash=sha256:" in line
        for line in lock.read_text(encoding="utf-8").splitlines()
    )


def test_llm_preflight_verifier_accepts_only_inactive_inventories() -> None:
    completed = subprocess.run(
        _verify_command(lock_path=LLM_ROOT / "requirements.lock"),
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "inventories": {"kimi_inventory": "incomplete", "qwen_inventory": "incomplete"},
        "providers": [],
        "runtime": "clicko-llm-gpu",
        "status": "preflight-verified",
    }


def test_llm_preflight_verifier_rejects_tampered_lock(tmp_path: Path) -> None:
    tampered_lock = tmp_path / "requirements.lock"
    tampered_lock.write_bytes((LLM_ROOT / "requirements.lock").read_bytes() + b"# tampered\n")

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
