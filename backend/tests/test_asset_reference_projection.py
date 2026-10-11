"""Synthetic receipts exercise reference guards; they do not prove rendered quality."""
# ruff: noqa: F811
import copy

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project

from app.database import SessionLocal
from app.domain.studios.contextual_editing import digest
from app.domain.studios.engine_qualification import EngineRenderReferenceV1
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob
from app.services.studios.compatibility import record_to_contract
from app.services.studios.engine_qualification import _reference


@pytest.fixture
def bound_reference(project):
    with SessionLocal() as db:
        record = db.get(CreativeDocument, project["document"])
        contract = record_to_contract(record)
        snapshot = contract.model_dump(mode="json", by_alias=True)
        source = db.get(LibraryAsset, project["asset"])
        artifact = {"assetId": "unit-render", "checksumSha256": "b" * 64, "width": 1080, "height": 1920,
                    "fps": 30, "durationMs": 15000, "audioCodec": "aac"}
        metadata = {"generationJobId": "unit-job", "derivation": "video_render", "documentId": record.id,
                    "documentRevision": record.revision, "documentSnapshotSha256": digest(snapshot),
                    "sourceAssetBindings": [{"assetId": source.id, "checksumSha256": source.checksum_sha256}],
                    "qualityEvaluation": {"status": "passed"}, "visualHumanReview": {"status": "pending"},
                    "contextualEditing": {"manifest": {"executableDirection": {"expectedDocumentRevision": 1,
                        "renderEngine": "current", "executionVersions": {}, "message": "original direction"}},
                        "rendererChecks": {"graphics": {"alightReceipt": {"unit": "legacy receipt retained"},
                                                          "unconsumed": "x" * 100_000}}}}
        db.add(LibraryAsset(id="unit-render", workspace_id=project["workspace"], title="Synthetic unit receipt",
                            asset_type="video", media_type="video/mp4", checksum_sha256="b" * 64,
                            object_metadata=metadata, storage_key="unit/render.mp4"))
        db.add(StudioGenerationJob(id="unit-job", workspace_id=project["workspace"], document_id=record.id,
            job_type="video_render", provider="unit-provider", idempotency_key="unit-reference",
            payload_hash="c" * 64, correlation_id="unit-reference", status="succeeded",
            request_payload={"documentSnapshot": snapshot}, result_payload={"artifact": artifact}))
        db.commit()
    return {**project, "metadata": metadata, "snapshot": snapshot,
            "reference": EngineRenderReferenceV1(document_id=project["document"], document_revision=1,
                asset_id="unit-render", checksum="b" * 64)}


def test_reference_projection_preserves_binding_digests_review_and_receipt(bound_reference):
    fixture = bound_reference
    with SessionLocal() as db:
        result = _reference(db, fixture["workspace"], fixture["reference"])
    assert result["reference"] == fixture["reference"].model_dump(mode="json", by_alias=True)
    assert result["provider"] == "unit-provider"
    assert result["sourceDigest"] == digest(result["sourceManifest"])
    assert result["recipeDigest"] == digest({"direction": {"message": "original direction"}, "recipes": []})
    assert result["review"] == {"status": "pending"}
    assert result["receipt"] == {"unit": "legacy receipt retained"}
    assert result["recipeEvidencePresent"] is True


@pytest.mark.parametrize("change, code", [
    ("checksum", "engine_render_checksum_or_scope_conflict"),
    ("snapshot", "engine_render_snapshot_conflict"),
    ("qc", "engine_technical_qc_not_passed"),
    ("binding", "engine_render_binding_invalid"),
    ("source", "engine_render_source_stale_or_unverified"),
])
def test_reference_projection_still_rejects_invalid_binding_and_evidence(bound_reference, change, code):
    fixture = bound_reference
    with SessionLocal() as db:
        asset = db.get(LibraryAsset, "unit-render")
        metadata = copy.deepcopy(asset.object_metadata)
        if change == "checksum":
            asset.checksum_sha256 = "d" * 64
        elif change == "snapshot":
            metadata["documentSnapshotSha256"] = "d" * 64
        elif change == "qc":
            metadata["qualityEvaluation"]["status"] = "failed"
        elif change == "binding":
            metadata["documentRevision"] = 2
        else:
            metadata["sourceAssetBindings"][0]["checksumSha256"] = "d" * 64
        asset.object_metadata = metadata
        db.commit()
    with SessionLocal() as db, pytest.raises(ValueError, match=code):
        _reference(db, fixture["workspace"], fixture["reference"])
