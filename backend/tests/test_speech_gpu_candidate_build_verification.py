from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "workers/speech-gpu/candidate/build-verification.v1.json"
WORKER_MANIFEST = ROOT / "workers/speech-gpu/worker.manifest.json"
INVENTORIES = {
    "chatterbox-multilingual-v3-pt-br": (
        ROOT / "workers/speech-gpu/chatterbox.artifacts.json",
        "chatterbox-worker-container",
    ),
    "kokoro-openvoice-v2-pt-br": (
        ROOT / "workers/speech-gpu/openvoice-v2.artifacts.json",
        "openvoice-worker-container",
    ),
}


def test_candidate_build_verification_is_evaluation_only() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    assert evidence["schemaVersion"] == (
        "clicko.speech-gpu-candidate-build-verification.v1"
    )
    assert evidence["dependencyVerificationOutputMode"] == "cacheonly"
    assert evidence["finalImageOutputMode"] == "docker-load-local-only"
    assert evidence["promotionStatus"] == (
        "evaluation-only-blocked-by-required-gates"
    )
    assert len(evidence["candidates"]) == 2

    for candidate in evidence["candidates"]:
        assert candidate["sourceAudit"] == "passed"
        assert candidate["dependencyInstall"] == "passed"
        assert candidate["offlineImportSmoke"] == "passed"
        assert candidate["externalVoiceCloneModelWeightsPresent"] is False
        assert candidate["inferenceExecuted"] is False
        assert candidate["finalImage"]["ociDigest"].startswith("sha256:")
        assert candidate["finalImage"]["providerLabel"] == "none"
        assert candidate["finalImage"]["candidateStatusLabel"] == "evaluation"
        assert candidate["runtimeIsolationSmoke"] == {
            "status": "passed",
            "network": "none",
            "readOnlyRootFilesystem": True,
            "capabilitiesDropped": "all",
            "noNewPrivileges": True,
            "runtimeUid": 10001,
            "runtimeGid": 10001,
            "ephemeralTmpfs": "/tmp/clicko-speech",
            "ephemeralTmpfsUid": 10001,
            "ephemeralTmpfsGid": 10001,
            "offlineImport": "passed",
        }

    safety = evidence["safetyAssertions"]
    assert safety == {
        "finalOciImageProduced": True,
        "externalVoiceCloneModelWeightsDownloaded": False,
        "humanBiometricDataUsed": False,
        "inferenceExecuted": False,
        "providerPromoted": False,
        "workerProvidersRemainEmpty": True,
        "sbomProduced": False,
        "packageFocusedSpdxProduced": True,
        "buildkitAttestationManifestProduced": True,
        "promotionGradeProvenanceReviewed": False,
        "signatureProduced": False,
        "vpsAccessedOrChanged": False,
    }


def test_candidate_evidence_matches_unannounced_worker_manifest() -> None:
    manifest = json.loads(WORKER_MANIFEST.read_text(encoding="utf-8"))

    assert manifest["capability"] == "speech_gpu"
    assert manifest["providers"] == []


def test_final_image_digests_are_bound_to_artifact_inventories() -> None:
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8"))

    for candidate in evidence["candidates"]:
        inventory_path, artifact_id = INVENTORIES[candidate["candidateId"]]
        inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
        artifact = next(
            item for item in inventory["artifacts"] if item["artifact_id"] == artifact_id
        )
        image = candidate["finalImage"]
        assert artifact["resolution_status"] == "resolved"
        assert artifact["verification_method"] == "registry_manifest"
        assert artifact["integrity"] == {
            "method": "oci_digest",
            "value": image["ociDigest"],
            "size_bytes": image["sizeBytes"],
        }
