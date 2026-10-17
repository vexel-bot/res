from __future__ import annotations

from pathlib import Path

import pytest
from conftest import register
from sqlalchemy import select

import app.services.studios.transcription as transcription_service
from app.database import SessionLocal
from app.domain.studios.contracts import (
    CreateGenerationJobRequest,
    TranscriptionProvenanceV1,
    TranscriptionRequestV1,
    TranscriptionResultV1,
    TranscriptSegmentV1,
)
from app.domain.studios.providers import TRANSCRIPTION_PROVIDERS
from app.models import (
    LibraryAsset,
    StudioGenerationJob,
    StudioMediaIngest,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioTranscript,
    User,
)
from app.services.object_storage import LocalObjectStorage, object_key, sha256_file
from app.services.studios.jobs import create_job, execute_job_once


class FakeTranscriptionProvider:
    name = "fake.transcription.v1"
    version = "1.0.0"

    def transcribe(self, request, source: Path, progress, is_cancelled):
        progress(55)
        if is_cancelled():
            raise InterruptedError
        return TranscriptionResultV1(
            media_ingest_id=request.media_ingest_id,
            source_asset_id=request.source_asset_id,
            source_checksum_sha256=sha256_file(source),
            locale=request.locale,
            provider=self.name,
            provider_version=self.version,
            segments=[
                TranscriptSegmentV1(
                    id="segment-1",
                    start_microseconds=0,
                    end_microseconds=900_000,
                    text="Olá, Clicko.",
                )
            ],
            provenance=TranscriptionProvenanceV1(
                source_revision="fake-revision-1",
                model_digest_sha256="1" * 64,
                worker_manifest_digest_sha256="2" * 64,
                worker_image_digest=f"sha256:{'3' * 64}",
            ),
            metrics={"wer": 0.0, "realTimeFactor": 0.01},
        )


class BoundFakeTranscriptionProvider(FakeTranscriptionProvider):
    pass


class TamperedTranscriptionProvider(BoundFakeTranscriptionProvider):
    name = "fake.transcription.tampered"

    def transcribe(self, request, source: Path, progress, is_cancelled):
        result = super().transcribe(request, source, progress, is_cancelled)
        return result.model_copy(update={"source_checksum_sha256": "f" * 64})


def _admit_fake_provider(db, provider_name: str) -> None:
    provider = StudioProviderRegistration(
        capability="transcription",
        provider=provider_name,
        provider_version="1.0.0",
        source_url="https://example.invalid/fake-transcription",
        source_revision="fake-revision-1",
        code_license="MIT",
        status="approved",
        risk_class="low",
        manifest={"benchmarkStatus": "passed", "workerAdvertised": True},
    )
    db.add(provider)
    db.flush()
    db.add(
        StudioModelRegistration(
            provider_registration_id=provider.id,
            name="fake-transcription-model",
            version="1.0.0",
            digest_sha256="1" * 64,
            model_license="MIT",
            commercial_use="approved",
            languages=["pt-BR"],
            capabilities=["transcription"],
            status="approved",
            manifest={"benchmarkStatus": "passed"},
        )
    )
    db.flush()


def _source_fixture(
    db,
    storage: LocalObjectStorage,
    workspace_id: str,
    tmp_path: Path,
    requested_by: str,
) -> tuple[LibraryAsset, StudioMediaIngest]:
    source = tmp_path / "source.mp4"
    source.write_bytes(b"fake-video-source")
    stored = storage.put_file(
        source,
        key=object_key(workspace_id, "raw", ".mp4"),
        media_type="video/mp4",
    )
    asset = LibraryAsset(
        workspace_id=workspace_id,
        title="Original UGC",
        asset_type="video",
        storage_key=stored.key,
        storage_backend=stored.backend,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
    )
    db.add(asset)
    db.flush()
    ingest = StudioMediaIngest(
        workspace_id=workspace_id,
        asset_id=asset.id,
        status="ready",
        probe_provider="builtin.ffprobe",
        media_info={"durationMicroseconds": 2_000_000},
        validation_errors=[],
        idempotency_key="transcription-ingest-001",
        requested_by=requested_by,
    )
    db.add(ingest)
    db.flush()
    return asset, ingest


def _job_request(
    workspace_id: str,
    ingest_id: str,
    asset: LibraryAsset,
    provider: str,
) -> CreateGenerationJobRequest:
    assert asset.checksum_sha256 is not None
    request = TranscriptionRequestV1(
        media_ingest_id=ingest_id,
        source_asset_id=asset.id,
        source_checksum_sha256=asset.checksum_sha256,
    )
    return CreateGenerationJobRequest(
        workspace_id=workspace_id,
        job_type="transcription",
        provider=provider,
        request=request.model_dump(by_alias=True, mode="json"),
    )


def test_transcription_job_persists_versioned_transcript_and_provenance(client, tmp_path, monkeypatch) -> None:
    _, workspace_id = register(client, "transcription-execution@example.com", "Transcription Execution")
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    monkeypatch.setattr(transcription_service, "get_object_storage", lambda _backend="local": storage)
    provider = BoundFakeTranscriptionProvider()
    monkeypatch.setitem(TRANSCRIPTION_PROVIDERS, provider.name, provider)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "transcription-execution@example.com"))
        assert user is not None
        asset, ingest = _source_fixture(db, storage, workspace_id, tmp_path, user.id)
        request = _job_request(workspace_id, ingest.id, asset, provider.name)
        _admit_fake_provider(db, provider.name)
        job, created = create_job(db, request, "transcription-job-001", user)
        assert created is True
        assert job.requested_by == user.id
        assert execute_job_once(db, job) == "succeeded"
        db.refresh(job)
        result = job.result_payload
        assert result["schemaVersion"] == "studio.transcription-job-result.v1"
        assert result["transcription"]["provenance"]["modelDigestSha256"] == "1" * 64
        transcript = db.get(StudioTranscript, result["transcriptId"])
        assert transcript is not None
        assert transcript.workspace_id == workspace_id
        assert transcript.provider == provider.name
        assert transcript.source_checksum_sha256 == asset.checksum_sha256
        assert transcript.provenance["workerImageDigest"] == f"sha256:{'3' * 64}"
        assert transcript.metrics["wer"] == 0.0
        assert transcript.transcript_document["provider"] == provider.name
        replayed = transcription_service.execute_transcription(
            db,
            job,
            lambda _value: None,
            lambda: False,
        )
        assert replayed["transcriptId"] == transcript.id
        assert len(
            db.scalars(
                select(StudioTranscript).where(StudioTranscript.workspace_id == workspace_id)
            ).all()
        ) == 1


def test_transcription_job_rejects_source_tampering_without_transcript(client, tmp_path, monkeypatch) -> None:
    _, workspace_id = register(client, "transcription-tamper@example.com", "Transcription Tamper")
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    monkeypatch.setattr(transcription_service, "get_object_storage", lambda _backend="local": storage)
    provider = TamperedTranscriptionProvider()
    monkeypatch.setitem(TRANSCRIPTION_PROVIDERS, provider.name, provider)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "transcription-tamper@example.com"))
        assert user is not None
        asset, ingest = _source_fixture(db, storage, workspace_id, tmp_path, user.id)
        request = _job_request(workspace_id, ingest.id, asset, provider.name)
        _admit_fake_provider(db, provider.name)
        job, _ = create_job(db, request, "transcription-job-tamper", user)
        for _ in range(job.max_attempts):
            execute_job_once(db, job)
        db.refresh(job)
        assert job.status == "failed"
        assert job.error_message == "transcription_result_checksum_mismatch"
        assert db.scalars(select(StudioTranscript).where(StudioTranscript.workspace_id == workspace_id)).all() == []


def test_transcription_job_rejects_unbound_source_before_job_creation(client, tmp_path) -> None:
    _, workspace_id = register(client, "transcription-binding@example.com", "Transcription Binding")
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    provider = BoundFakeTranscriptionProvider()

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "transcription-binding@example.com"))
        assert user is not None
        asset, ingest = _source_fixture(db, storage, workspace_id, tmp_path, user.id)
        request = _job_request(workspace_id, ingest.id, asset, provider.name)
        request.request["sourceChecksumSha256"] = "f" * 64
        _admit_fake_provider(db, provider.name)

        with pytest.raises(ValueError, match="transcription_source_checksum_mismatch"):
            create_job(db, request, "transcription-unbound-source", user)
        assert db.scalars(
            select(StudioGenerationJob).where(
                StudioGenerationJob.workspace_id == workspace_id,
                StudioGenerationJob.job_type == "transcription",
            )
        ).all() == []
