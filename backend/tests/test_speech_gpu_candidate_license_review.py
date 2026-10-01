from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVIEW = ROOT / "workers/speech-gpu/candidate/license-review.v1.json"
BUILD_EVIDENCE = ROOT / "workers/speech-gpu/candidate/build-verification.v1.json"
WORKER_MANIFEST = ROOT / "workers/speech-gpu/worker.manifest.json"


def test_license_review_is_partial_and_promotion_blocking() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert review["schemaVersion"] == (
        "clicko.speech-gpu-candidate-license-review.v1"
    )
    assert review["reviewStatus"] == "review_required"
    assert review["legalConclusion"] is False
    assert review["providerPromotionAllowed"] is False
    assert review["scope"]["kind"] == "package-focused-spdx"
    assert "file-by-file inventory" in review["scope"]["excludes"]
    assert review["scannerEvidence"]["dockerScout"]["completeSbomProduced"] is False
    assert review["scannerEvidence"]["syft"]["completeSbomProduced"] is False
    assert len(review["requiredGates"]) >= 6


def test_license_review_is_bound_to_the_built_images() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    build = json.loads(BUILD_EVIDENCE.read_text(encoding="utf-8"))
    built_by_candidate = {
        candidate["candidateId"]: candidate["finalImage"]["ociDigest"]
        for candidate in build["candidates"]
    }

    assert len(review["images"]) == 2
    for image in review["images"]:
        assert image["ociDigest"] == built_by_candidate[image["candidateId"]]
        assert len(image["spdxSha256"]) == 64
        assert image["pythonPackageCount"] in {125, 130}
        assert image["debianPackageCount"] == 95
        assert image["packageCountExcludingImage"] == (
            image["pythonPackageCount"] + image["debianPackageCount"]
        )


def test_known_copyleft_and_proprietary_surfaces_have_dispositions() -> None:
    review = json.loads(REVIEW.read_text(encoding="utf-8"))
    findings = {
        finding["package"]: finding
        for image in review["images"]
        for finding in image["findings"]
    }

    assert findings["pykakasi"]["disposition"] == "remove_from_pt_br_candidate"
    assert findings["praat-parselmouth"]["licenseSignal"] == "GPL-3.0-or-later"
    assert findings["Unidecode"]["licenseSignal"] == "GPL-2.0-or-later"
    assert findings["phonemizer-fork"]["licenseSignal"] == "GPL-3.0-or-later"
    assert findings["nvidia-cuda-python-wheels"]["licenseSignal"] == (
        "NVIDIA Proprietary Software"
    )


def test_license_review_does_not_announce_a_provider() -> None:
    manifest = json.loads(WORKER_MANIFEST.read_text(encoding="utf-8"))
    review = json.loads(REVIEW.read_text(encoding="utf-8"))

    assert manifest["providers"] == []
    assert review["dependencyMinimizationRevision"]["status"] == (
        "planned_not_locked_or_built"
    )
