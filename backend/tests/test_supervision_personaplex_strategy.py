from __future__ import annotations

import hashlib
import json
from pathlib import Path

from app.domain.studios.artifacts import ArtifactInventoryV1, artifact_inventory_digest

ROOT = Path(__file__).resolve().parents[2]
SUPERVISION_INVENTORY = (
    ROOT / "workers/vision-gpu/providers/supervision-toolkit.artifacts.json"
)
PERSONAPLEX_INVENTORY = (
    ROOT / "workers/speech-gpu/personaplex-reference.artifacts.json"
)
VISION_MANIFEST = ROOT / "workers/vision-gpu/worker.manifest.json"
SPEECH_MANIFEST = ROOT / "workers/speech-gpu/worker.manifest.json"
REPORT = (
    ROOT
    / "docs/studios/research/SUPERVISION_PERSONAPLEX_STRATEGY_2026-08-27.md"
)
BASELINE = (
    ROOT
    / "benchmarks/studios/reality/supervision-duplex-baseline.v1.json"
)
ALTERNATIVES = ROOT / "workers/speech-gpu/duplex-alternatives.research.json"
QWEN_VENDOR_MANIFEST = (
    ROOT / "workers/speech-gpu/qwen3-omni-30b-a3b.vendor-manifest.v1.json"
)


def _inventory(path: Path) -> ArtifactInventoryV1:
    """Load a frozen candidate inventory through the canonical validator."""
    return ArtifactInventoryV1.model_validate_json(path.read_text(encoding="utf-8"))


def test_supervision_inventory_has_local_oci_but_requires_human_review() -> None:
    """Accept material OCI evidence while failing closed on legal/signature gates."""
    inventory = _inventory(SUPERVISION_INVENTORY)
    records = {item.artifact_id: item for item in inventory.artifacts}

    assert inventory.status == "review_required"
    assert records["supervision-code"].source_revision == (
        "5f25aa0ee6dc22891415b6e3d2e1689ce7a32952"
    )
    assert records["supervision-code"].license.decision == "approved"
    assert records["supervision-clicko-lock"].resolution_status == "resolved"
    assert records["supervision-clicko-lock"].integrity is not None
    assert records["supervision-clicko-lock"].integrity.value == (
        "9cc82bd9dd4e7b291d5a85ad3f8718009da30bf4f372edc0d8a8503d85b41284"
    )
    assert records["supervision-clicko-lock"].license.decision == "review_required"
    container = records["supervision-vision-worker-container"]
    assert container.resolution_status == "resolved"
    assert container.verification_method == "local_oci_layout"
    assert container.integrity is not None
    assert container.integrity.value == (
        "sha256:92dbfe133f63ce899637d9bad3fc24a53448eee32043d0773f1f8a2fb875d6a6"
    )
    assert container.license.decision == "review_required"
    assert artifact_inventory_digest(inventory) == (
        "2ad5d4add7314797bcf908b9451409721c3aa783f29885292d882e5cfadbda88"
    )


def test_personaplex_weights_are_rejected_without_acceptance_or_bytes() -> None:
    """Keep MIT code separable from the policy-rejected NVIDIA checkpoint."""
    inventory = _inventory(PERSONAPLEX_INVENTORY)
    records = {item.artifact_id: item for item in inventory.artifacts}
    weights = records["personaplex-7b-v1-weights"]

    assert inventory.status == "rejected"
    assert records["personaplex-code"].source_revision == (
        "3428dfd95309a7f3c84fd93259ded0f810d1ff91"
    )
    assert weights.source_revision == "fdaf4090a61cb315c138a1faee287ffd6c716309"
    assert weights.resolution_status == "rejected"
    assert weights.integrity is None
    assert weights.license.decision == "rejected"
    assert weights.license.commercial_saas_use_allowed is None
    assert artifact_inventory_digest(inventory) == (
        "3c20c53e0ee99fc4b039aee7ecab8e3d708f1ecbe6494be4dd78a52e8c15910d"
    )


def test_research_does_not_activate_a_worker_provider() -> None:
    """Research artifacts must never self-promote into runtime manifests."""
    vision = json.loads(VISION_MANIFEST.read_text(encoding="utf-8"))
    speech = json.loads(SPEECH_MANIFEST.read_text(encoding="utf-8"))

    assert vision["providers"] == []
    assert speech["providers"] == []
    supervision_candidate = json.loads(
        (
            ROOT
            / "workers/vision-gpu/providers/supervision-toolkit.provider.json"
        ).read_text(encoding="utf-8")
    )
    assert supervision_candidate["status"] == "evaluation"
    assert supervision_candidate["advertised_by_worker_manifest"] is False
    assert not set(supervision_candidate["provider_ids"]) & set(vision["providers"])
    assert not (ROOT / "workers/speech-gpu/personaplex.provider.json").exists()


def test_qwen_challenger_is_fully_inventoried_but_license_blocked() -> None:
    alternatives = json.loads(ALTERNATIVES.read_text(encoding="utf-8"))
    manifest = json.loads(QWEN_VENDOR_MANIFEST.read_text(encoding="utf-8"))
    candidate = next(
        item
        for item in alternatives["candidates"]
        if item["id"] == "qwen3-omni-30b-a3b-instruct"
    )
    weight_files = [item for item in manifest["files"] if item["kind"] == "weight"]

    assert candidate["code_revision"] == "e4235853125589c789f06a2dd83e9f4126df5e9d"
    assert candidate["model_revision"] == "26291f793822fb6be9555850f06dfe95f2d7e695"
    assert candidate["artifact_manifest_digest_sha256"] == hashlib.sha256(
        QWEN_VENDOR_MANIFEST.read_bytes()
    ).hexdigest()
    assert manifest["model"]["declaredLicense"] == "other"
    assert manifest["model"]["declaredLicenseName"] == "apache-2.0"
    assert manifest["model"]["licenseFilePresent"] is False
    assert manifest["model"]["licenseDecision"] == "review_required"
    assert manifest["weightsDownloaded"] is False
    assert manifest["runtimeAuthorized"] is False
    assert manifest["providersEnabled"] == []
    assert len(weight_files) == 15
    assert sum(item["sizeBytes"] for item in weight_files) == 70_523_299_202
    assert all(len(item["sha256"]) == 64 for item in weight_files)
    assert all(item["downloaded"] is False for item in weight_files)


def test_research_keeps_upstream_types_out_of_product_runtime() -> None:
    """Avoid accidental package activation or canonical-domain imports."""
    dependency_files = [
        ROOT / "backend/requirements.txt",
        ROOT / "workers/vision-gpu/requirements.in",
        ROOT / "workers/vision-gpu/requirements.lock",
    ]
    dependency_text = "\n".join(
        path.read_text(encoding="utf-8").lower() for path in dependency_files
    )
    domain_text = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (ROOT / "backend/app/domain/studios").glob("*.py")
    )

    assert "supervision" not in dependency_text
    assert "personaplex" not in dependency_text
    assert "supervision" not in domain_text
    assert "personaplex" not in domain_text


def test_strategy_records_boundaries_and_upstream_risks() -> None:
    """Keep the strategic decisions reviewable beside executable gates."""
    report = REPORT.read_text(encoding="utf-8")

    assert "Supervision entra como detalhe descartável" in report
    assert "não é detector, world model nem motor de física" in report
    assert "torch.load" in report
    assert "checkpoint fica **rejeitado**" in report
    assert "DuplexConversationProvider" in report
    assert "nenhum peso baixado" in report.lower()


def test_execution_baseline_freezes_protected_boundaries() -> None:
    """Detect accidental runtime activation or canonical-domain contamination."""
    baseline = json.loads(BASELINE.read_text(encoding="utf-8"))

    assert baseline["schemaVersion"] == "clicko.supervision-duplex-baseline.v1"
    assert baseline["upstreamPins"]["supervision"]["sourceRevision"] == (
        "5f25aa0ee6dc22891415b6e3d2e1689ce7a32952"
    )
    assert baseline["upstreamPins"]["personaplexWeights"]["decision"] == (
        "rejected"
    )
    assert baseline["upstreamPins"]["personaplexWeights"]["bytesPresent"] is False
    for boundary in baseline["protectedBoundaries"]:
        content = (ROOT / boundary["path"]).read_bytes()
        assert hashlib.sha256(content).hexdigest() == boundary["sha256"]
