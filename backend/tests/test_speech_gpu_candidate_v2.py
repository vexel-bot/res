from __future__ import annotations

import hashlib
import json
import tomllib
from pathlib import Path

from scripts.verify_speech_gpu_candidate_v2_lock import verify_v2_lock

ROOT = Path(__file__).resolve().parents[2]
V2_ROOT = ROOT / "workers/speech-gpu/candidate-v2"
VERIFICATION = V2_ROOT / "verification.v1.json"
WORKER_MANIFEST = ROOT / "workers/speech-gpu/worker.manifest.json"


def test_v2_locks_are_frozen_and_minimized() -> None:
    chatterbox = verify_v2_lock(V2_ROOT / "chatterbox/uv.lock", "chatterbox")
    openvoice = verify_v2_lock(V2_ROOT / "openvoice/uv.lock", "openvoice")

    assert chatterbox["packageCount"] == 95
    assert chatterbox["removedPackageCount"] == 30
    assert openvoice["packageCount"] == 96
    assert openvoice["removedPackageCount"] == 34


def test_v2_project_dependencies_do_not_restore_forbidden_frontends() -> None:
    forbidden = {
        "cn2an",
        "eng-to-ipa",
        "inflect",
        "jieba",
        "kokoro",
        "num2words",
        "praat-parselmouth",
        "pykakasi",
        "pypinyin",
        "resemble-perth",
        "spacy",
        "spacy-curated-transformers",
        "unidecode",
    }

    for project in ("chatterbox", "openvoice"):
        lock = tomllib.loads((V2_ROOT / project / "uv.lock").read_text(encoding="utf-8"))
        packages = {package["name"] for package in lock["package"]}
        assert forbidden.isdisjoint(packages)


def test_v2_patch_digests_and_dependency_stage_status_are_bound() -> None:
    verification = json.loads(VERIFICATION.read_text(encoding="utf-8"))
    patches = {
        wheel["patch"]["path"]: wheel["patch"]["sha256"]
        for candidate in verification["candidates"]
        for wheel in candidate["sourceWheels"]
        if wheel["patch"] is not None
    }

    assert len(patches) == 2
    for relative_path, expected_digest in patches.items():
        assert hashlib.sha256((ROOT / relative_path).read_bytes()).hexdigest() == (
            expected_digest
        )

    evidence = verification["verification"]
    assert evidence["patchesApplyToPinnedRevisions"] is True
    assert evidence["staticImportProof"] == "passed"
    assert evidence["sourceAuditsPassed"] is True
    assert evidence["sourceWheelsBuiltNoDeps"] is True
    assert evidence["dependencyStagesPassed"] is True
    assert evidence["offlineImportSmokesPassed"] is True
    assert evidence["imageBuilt"] is False
    assert evidence["providerPromoted"] is False
    assert evidence["workerProvidersRemainEmpty"] is True
    assert json.loads(WORKER_MANIFEST.read_text(encoding="utf-8"))["providers"] == []
    for candidate in verification["candidates"]:
        linux = candidate["linuxBuildEvidence"]
        assert linux["sourceAudit"] == "passed"
        assert linux["sourceWheelsBuiltNoDeps"] == "passed"
        assert linux["frozenDependencyInstall"] == "passed"
        assert linux["offlineImportSmoke"] == "passed"
        assert linux["weightsDownloaded"] is False
        assert linux["inferenceExecuted"] is False


def test_v2_patch_keeps_language_imports_lazy() -> None:
    openvoice_patch = (
        V2_ROOT / "patches/openvoice-tone-color-only.patch"
    ).read_text(encoding="utf-8")
    kokoro_patch = (
        V2_ROOT / "patches/kokoro-lazy-language-g2p.patch"
    ).read_text(encoding="utf-8")

    assert "-from openvoice.text import text_to_sequence" in openvoice_patch
    assert "+        from openvoice.text import text_to_sequence" in openvoice_patch
    assert "-from misaki import en, espeak" in kokoro_patch
    assert "+            from misaki import en" in kokoro_patch
