from __future__ import annotations

import io
import wave
from datetime import UTC, datetime
from types import SimpleNamespace

import pytest
from conftest import register
from test_studio_kernel import auth, create_document

from app.database import SessionLocal
from app.domain.studios.acoustic_qualification import (
    AcousticAggregateMetricsV1,
    AcousticQualificationAssessmentV1,
    contract_digest,
    sign_acoustic_promotion_receipt,
)
from app.domain.studios.contracts import (
    CreativeDocumentV1,
    StudioAcousticDetectionCheckV1,
    StudioAcousticDetectorResultV1,
    StudioAssetRightsReviewRecordV1,
    StudioListeningReviewRecordV1,
    StudioListeningReviewSubmissionV1,
)
from app.domain.studios.providers import ACOUSTIC_ANALYSIS_PROVIDERS
from app.models import (
    LibraryAsset,
    StudioDomainEvent,
    StudioGenerationJob,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioReviewRequest,
    User,
)
from app.services.object_storage import get_object_storage
from app.services.studios.acoustic_analysis import snapshot_checksum
from app.services.studios.jobs import execute_job_once
from app.services.studios.publication import _require_audio_admission

RENDER_BYTES = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"


def wav_fixture() -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as target:
        target.setnchannels(1)
        target.setsampwidth(2)
        target.setframerate(16_000)
        target.writeframes(bytes(16_000 * 2))
    return output.getvalue()


class FakeQualifiedAcousticProvider:
    name = "fake.acoustic-qualified"
    version = "1.0.0"

    def analyze(self, source, request, progress, is_cancelled):
        assert source.read_bytes() == RENDER_BYTES
        assert request.policy == "no-speech-no-music-v1"
        assert not is_cancelled()
        progress(55)
        return StudioAcousticDetectorResultV1(
            provider=self.name,
            provider_version=self.version,
            source_checksum_sha256=request.render_checksum_sha256,
            analyzed_duration_ms=1_000,
            checks=[
                StudioAcousticDetectionCheckV1(
                    kind="speech",
                    status="pass",
                    detected_duration_ms=0,
                    maximum_score=0.01,
                    decision_threshold=0.5,
                    detail="Fixture qualificada não contém fala.",
                ),
                StudioAcousticDetectionCheckV1(
                    kind="music",
                    status="pass",
                    detected_duration_ms=0,
                    maximum_score=0.02,
                    decision_threshold=0.5,
                    detail="Fixture qualificada não contém música.",
                ),
            ],
        )


def test_acoustic_analysis_requires_promotion_and_admits_only_same_final_render(
    client,
    tmp_path,
    monkeypatch,
):
    from app import tasks
    from app.routers import assets as assets_router
    from app.services.studios import acoustic_analysis as acoustic_analysis_service
    from app.services.studios import jobs as jobs_service

    monkeypatch.setattr(assets_router.settings, "storage_path", str(tmp_path))
    promotion_secret = "acoustic-service-test-secret-with-more-than-32-characters"
    promotion_key_id = "acoustic-service-test-key"
    qualification_settings = SimpleNamespace(
        studio_acoustic_promotion_hmac_secret=promotion_secret,
        studio_acoustic_promotion_key_id=promotion_key_id,
    )
    monkeypatch.setattr(acoustic_analysis_service, "get_settings", lambda: qualification_settings)
    monkeypatch.setattr(jobs_service, "get_settings", lambda: qualification_settings)
    token, workspace = register(client, "acoustic-owner@example.com", "Acoustic Owner")
    foreign_token, _ = register(client, "acoustic-foreign@example.com", "Acoustic Foreign")
    render_response = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "MP4 final privado"},
        files={"file": ("final.mp4", RENDER_BYTES, "video/mp4")},
    )
    assert render_response.status_code == 201, render_response.text
    render = render_response.json()
    sound_response = client.post(
        "/api/v1/assets/upload",
        headers=auth(token),
        data={"workspace_id": workspace, "title": "Foley próprio"},
        files={"file": ("foley.wav", wav_fixture(), "audio/wav")},
    )
    assert sound_response.status_code == 201, sound_response.text
    sound = sound_response.json()
    document = create_document(client, token, workspace, content_type="video").json()
    source_declaration = "Captação própria CLICK-ACOUSTIC-001"
    license_declaration = "Direitos próprios CLICK-ACOUSTIC-RIGHTS-001"

    with SessionLocal() as db:
        owner = db.query(User).filter_by(email="acoustic-owner@example.com").one()
        rights_event = StudioDomainEvent(
            workspace_id=workspace,
            event_type="studio.asset.rights_reviewed",
            aggregate_type="studio_asset",
            aggregate_id=sound["id"],
            correlation_id="acoustic-rights-fixture",
            actor_id=owner.id,
            payload={},
        )
        db.add(rights_event)
        db.flush()
        rights = StudioAssetRightsReviewRecordV1(
            review_id=rights_event.id,
            workspace_id=workspace,
            document_id=document["documentId"],
            document_revision=document["revision"],
            asset_id=sound["id"],
            asset_checksum_sha256=sound["checksumSha256"],
            decision="verified",
            basis="owned",
            source_declaration=source_declaration,
            license_declaration=license_declaration,
            source_reference="Registro técnico CLICK-ACOUSTIC-001",
            rights_reference="Declaração técnica CLICK-ACOUSTIC-RIGHTS-001",
            no_expiration_confirmed=True,
            reviewer_id=owner.id,
            reviewed_at=datetime.now(UTC),
        )
        rights_event.payload = {"record": rights.model_dump(by_alias=True, mode="json")}
        snapshot = document
        snapshot["composition"]["narrative"].update(
            {
                "audioMode": "natural-foley-only",
                "voicePolicy": "prohibited",
                "musicPolicy": "prohibited",
                "captionMode": "editorial-burned-in",
            }
        )
        snapshot["assets"] = [
            {
                "id": sound["id"],
                "mediaType": "audio/wav",
                "checksum": sound["checksumSha256"],
                "rightsStatus": "verified",
                "provenance": {
                    "purpose": "natural-sound-candidate",
                    "sourceDeclaration": source_declaration,
                    "licenseDeclaration": license_declaration,
                    "rightsReviewId": rights.review_id,
                },
            }
        ]
        review = StudioReviewRequest(
            workspace_id=workspace,
            document_id=document["documentId"],
            document_version=document["version"],
            status="approved",
            snapshot=snapshot,
            render_asset_id=render["id"],
            render_checksum_sha256=render["checksumSha256"],
            requested_by=owner.id,
            decided_by=owner.id,
            decided_at=datetime.now(UTC),
        )
        db.add(review)
        db.flush()
        listening_event = StudioDomainEvent(
            workspace_id=workspace,
            event_type="studio.review.listening_recorded",
            aggregate_type="studio_review",
            aggregate_id=review.id,
            correlation_id="acoustic-listening-fixture",
            actor_id=owner.id,
            payload={},
        )
        db.add(listening_event)
        db.flush()
        listening_event.payload = StudioListeningReviewRecordV1(
            assessment_id=listening_event.id,
            review_id=review.id,
            document_id=review.document_id,
            document_version=review.document_version,
            snapshot_checksum_sha256=snapshot_checksum(review),
            reviewer_id=owner.id,
            reviewed_at=datetime.now(UTC),
            result="pass",
            submission=StudioListeningReviewSubmissionV1(
                render_asset_id=render["id"],
                render_checksum_sha256=render["checksumSha256"],
                listened_entire_mix=True,
                speech_absent="pass",
                music_absent="pass",
                natural_sounds_coherent="pass",
                mix_balanced="pass",
            ),
        ).model_dump(by_alias=True, mode="json")
        db.commit()
        review_id = review.id

    capability_url = f"/api/v1/studios/v1/reviews/{review_id}/acoustic-analysis-capability"
    unavailable = client.get(capability_url, headers=auth(token))
    assert unavailable.status_code == 200
    assert unavailable.json()["reasonCode"] == "acoustic_detector_not_approved"
    endpoint = f"/api/v1/studios/v1/reviews/{review_id}/acoustic-analyses"
    denied = client.post(endpoint, headers={**auth(token), "Idempotency-Key": "acoustic-before-promotion"})
    assert denied.status_code == 409
    assert denied.json()["detail"]["code"] == "acoustic_detector_not_approved"
    assert client.get(capability_url, headers=auth(foreign_token)).status_code == 404

    zero_error_metrics = AcousticAggregateMetricsV1(
        case_count=20,
        succeeded_count=20,
        inconclusive_count=0,
        failed_count=0,
        speech={
            "truePositive": 8,
            "trueNegative": 12,
            "falsePositive": 0,
            "falseNegative": 0,
        },
        music={
            "truePositive": 8,
            "trueNegative": 12,
            "falsePositive": 0,
            "falseNegative": 0,
        },
        speech_false_negative_rate=0,
        speech_false_positive_rate=0,
        music_false_negative_rate=0,
        music_false_positive_rate=0,
        inconclusive_rate=0,
    )
    assessment = AcousticQualificationAssessmentV1(
        run_id="service-integration-fixture-run",
        suite_id="acoustic-presence-ptbr-v1",
        provider=FakeQualifiedAcousticProvider.name,
        provider_version=FakeQualifiedAcousticProvider.version,
        model_name="fake-acoustic-model",
        model_version="1.0.0",
        model_digest_sha256="a" * 64,
        policy_digest_sha256="b" * 64,
        corpus_manifest_digest_sha256="c" * 64,
        run_digest_sha256="d" * 64,
        worker_manifest_digest_sha256="e" * 64,
        license_review_digest_sha256="f" * 64,
        conversion_provenance_digest_sha256="1" * 64,
        decision="passed",
        recomputed_metrics=zero_error_metrics,
        evaluator_digest_sha256="2" * 64,
        evaluated_at=datetime.now(UTC),
    )
    receipt = sign_acoustic_promotion_receipt(
        assessment,
        secret=promotion_secret,
        signer_key_id=promotion_key_id,
    )
    receipt_digest = contract_digest(receipt)
    with SessionLocal() as db:
        owner = db.query(User).filter_by(email="acoustic-owner@example.com").one()
        registration = StudioProviderRegistration(
            capability="acoustic_analysis",
            provider=FakeQualifiedAcousticProvider.name,
            provider_version=FakeQualifiedAcousticProvider.version,
            source_url="https://example.invalid/acoustic-fixture",
            source_revision="fixture-revision-1",
            code_license="Apache-2.0",
            status="approved",
            risk_class="medium",
            manifest={
                "acousticPromotionReceipt": receipt.model_dump(by_alias=True, mode="json"),
            },
            approved_by=owner.id,
            approved_at=datetime.now(UTC),
        )
        db.add(registration)
        db.flush()
        db.add(
            StudioModelRegistration(
                provider_registration_id=registration.id,
                name="fake-acoustic-model",
                version="1.0.0",
                digest_sha256="a" * 64,
                model_license="Apache-2.0",
                commercial_use="approved",
                languages=["pt-BR"],
                capabilities=["acoustic_analysis"],
                status="approved",
                manifest={
                    "acousticPromotionReceiptDigestSha256": receipt_digest,
                },
                approved_by=owner.id,
                approved_at=datetime.now(UTC),
            )
        )
        db.commit()
    monkeypatch.setitem(
        ACOUSTIC_ANALYSIS_PROVIDERS,
        FakeQualifiedAcousticProvider.name,
        FakeQualifiedAcousticProvider(),
    )
    queued: list[str] = []
    monkeypatch.setattr(tasks.execute_studio_generation, "delay", lambda job_id: queued.append(job_id))
    ready = client.get(capability_url, headers=auth(token)).json()
    assert ready["status"] == "ready"
    accepted = client.post(
        endpoint,
        headers={**auth(token), "Idempotency-Key": "acoustic-qualified-final-001"},
    )
    assert accepted.status_code == 202, accepted.text
    assert accepted.json()["executionCapability"] == "media_cpu"
    assert queued == [accepted.json()["id"]]
    replay = client.post(
        endpoint,
        headers={**auth(token), "Idempotency-Key": "acoustic-qualified-final-001"},
    )
    assert replay.status_code == 202
    assert replay.json()["id"] == accepted.json()["id"]

    with SessionLocal() as db:
        job = db.get(StudioGenerationJob, accepted.json()["id"])
        assert execute_job_once(db, job) == "succeeded"
        db.refresh(job)
        assert job.result_payload["status"] == "pass"
        review = db.get(StudioReviewRequest, review_id)
        _require_audio_admission(
            CreativeDocumentV1.model_validate(snapshot),
            db=db,
            review=review,
        )
        model = db.query(StudioModelRegistration).filter_by(name="fake-acoustic-model").one()
        model.status = "rejected"
        db.commit()
        with pytest.raises(ValueError, match="studio_publication_acoustic_promotion_revoked"):
            _require_audio_admission(
                CreativeDocumentV1.model_validate(snapshot),
                db=db,
                review=review,
            )
        model.status = "approved"
        db.commit()
        registration = db.query(StudioProviderRegistration).filter_by(provider=FakeQualifiedAcousticProvider.name).one()
        valid_manifest = registration.manifest
        tampered_receipt = dict(valid_manifest["acousticPromotionReceipt"])
        tampered_receipt["signatureHmacSha256"] = "0" * 64
        registration.manifest = {"acousticPromotionReceipt": tampered_receipt}
        db.commit()
        with pytest.raises(ValueError, match="studio_publication_acoustic_promotion_revoked"):
            _require_audio_admission(
                CreativeDocumentV1.model_validate(snapshot),
                db=db,
                review=review,
            )
        registration.manifest = valid_manifest
        db.commit()
        stored = db.get(LibraryAsset, render["id"])
        render_path = get_object_storage(stored.storage_backend).local_path(stored.storage_key)
        assert render_path is not None
        original = render_path.read_bytes()
        render_path.write_bytes(b"changed-after-analysis")
        with pytest.raises(ValueError, match="studio_publication_render_changed"):
            _require_audio_admission(
                CreativeDocumentV1.model_validate(snapshot),
                db=db,
                review=review,
            )
        render_path.write_bytes(original)

    latest = client.get(
        "/api/v1/studios/v1/reviews/latest",
        headers=auth(token),
        params={"workspace_id": workspace, "document_id": document["documentId"]},
    )
    assert latest.status_code == 200
    payload = latest.json()
    assert payload["acousticAnalysis"]["status"] == "pass"
    assert payload["acousticAnalysis"]["productionQualified"] is True
    assert payload["naturalSoundAdmission"]["publicationAdmitted"] is True
    assert payload["naturalSoundAdmission"]["renderChecksumSha256"] == render["checksumSha256"]
