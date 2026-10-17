from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SUPERVISION_ROOT = ROOT / "workers/vision-gpu/supervision"
LOCK = SUPERVISION_ROOT / "requirements.lock"
SBOM = SUPERVISION_ROOT / "sbom.spdx.json"
REVIEW = SUPERVISION_ROOT / "license-review.v1.json"
BENCHMARK = (
    ROOT
    / "benchmarks/studios/reality/supervision-benchmark-run-2026-08-28.v1.json"
)
MANIFEST = ROOT / "workers/vision-gpu/worker.manifest.json"

LOCK_DIGEST = "9cc82bd9dd4e7b291d5a85ad3f8718009da30bf4f372edc0d8a8503d85b41284"
SBOM_DIGEST = "22d543bc3c7e734454e252fcf60846af2d9f2e81ebf301d1cd876616d0a544c5"
REVIEW_DIGEST = "f8c7412117aaa046dec90ee3e18781a74b3f591772bfb60eadcae4f9b4521f41"
BENCHMARK_DIGEST = "df2155e926afe933f4bcda47a99a68b4364c1234bb804afade0dd7da75b5c867"
MANIFEST_DIGEST = "381f5809a61bceb7f24b446f664666969418efa33b5bfb6138e3d99de114a622"


def _verify_command(*, lock: Path = LOCK, lock_digest: str = LOCK_DIGEST) -> list[str]:
    return [
        sys.executable,
        str(SUPERVISION_ROOT / "verify_build.py"),
        "--adapter",
        str(ROOT / "backend/app/providers/studios/supervision_detection.py"),
        "--domain",
        str(ROOT / "backend/app/domain/studios"),
        "--lock",
        str(lock),
        "--lock-digest",
        lock_digest,
        "--sbom",
        str(SBOM),
        "--sbom-digest",
        SBOM_DIGEST,
        "--review",
        str(REVIEW),
        "--review-digest",
        REVIEW_DIGEST,
        "--benchmark",
        str(BENCHMARK),
        "--benchmark-digest",
        BENCHMARK_DIGEST,
        "--manifest",
        str(MANIFEST),
        "--manifest-digest",
        MANIFEST_DIGEST,
    ]


def test_supervision_linux_lock_and_focused_sbom_are_bound() -> None:
    assert hashlib.sha256(LOCK.read_bytes()).hexdigest() == LOCK_DIGEST
    assert hashlib.sha256(SBOM.read_bytes()).hexdigest() == SBOM_DIGEST
    assert hashlib.sha256(REVIEW.read_bytes()).hexdigest() == REVIEW_DIGEST
    lock_lines = [
        line
        for line in LOCK.read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    ]
    sbom = json.loads(SBOM.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert len(lock_lines) == 29
    assert all(" --hash=sha256:" in line for line in lock_lines)
    assert sbom["spdxVersion"] == "SPDX-2.3"
    assert len(sbom["packages"]) == len(lock_lines)
    assert review["lockDigestSha256"] == LOCK_DIGEST
    assert review["status"] == "review_required"
    assert review["pendingNativeBundleReview"]
    package_names = {item["name"].lower() for item in sbom["packages"]}
    assert "supervision" in package_names
    assert "opencv-python-headless" not in package_names


def test_supervision_evaluation_recipe_is_hermetic_and_non_promoting() -> None:
    dockerfile = (SUPERVISION_ROOT / "Dockerfile.evaluation").read_text(
        encoding="utf-8"
    )
    workflow = (
        ROOT / ".github/workflows/studios-supervision-evaluation.yml"
    ).read_text(encoding="utf-8")

    assert "sha256:2856e6af199e8128161abd320575eb9b341f3b76f017b5d0c9cd364f60d8a050" in dockerfile
    assert "--no-index" in dockerfile
    assert "--require-hashes" in dockerfile
    assert 'io.clicko.providers="none"' in dockerfile
    assert "USER clicko" in dockerfile
    assert "--uid 10001" in dockerfile
    assert "HEALTHCHECK" in dockerfile
    assert "curl " not in dockerfile and "wget " not in dockerfile
    assert "workflow_dispatch:" in workflow
    assert "network: none" in workflow
    assert "push: false" in workflow
    assert "provenance: mode=max" in workflow
    assert "sbom: true" in workflow
    assert "--read-only" in workflow
    assert "--cap-drop ALL" in workflow
    assert "--security-opt no-new-privileges" in workflow
    assert "--network none" in workflow
    assert "--pids-limit 128" in workflow
    assert "rootfs-must-be-read-only" in workflow
    assert "NoNewPrivs" in workflow
    assert "upload-artifact" in workflow
    assert "deploy" not in workflow.lower()


def test_supervision_preflight_verifier_accepts_evidence_and_rejects_tamper(
    tmp_path: Path,
) -> None:
    completed = subprocess.run(
        _verify_command(),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0, completed.stderr
    assert json.loads(completed.stdout) == {
        "benchmark": "passed",
        "licenseReview": "review_required",
        "packageCount": 29,
        "providers": [],
        "status": "supervision-evaluation-preflight-verified",
    }

    tampered = tmp_path / "requirements.lock"
    tampered.write_bytes(LOCK.read_bytes() + b"# tampered\n")
    rejected = subprocess.run(
        _verify_command(lock=tampered),
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert rejected.returncode != 0
    assert "supervision_lock_digest_mismatch" in rejected.stderr
