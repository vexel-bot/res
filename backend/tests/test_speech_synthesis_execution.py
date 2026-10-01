from __future__ import annotations

import hashlib
import wave
from datetime import UTC, datetime, timedelta
from pathlib import Path

from conftest import register
from sqlalchemy import select

import app.services.studios.speech as speech_service
from app.database import SessionLocal
from app.domain.studios.contracts import (
    CreateGenerationJobRequest,
    SpeechProvenanceV1,
    SpeechSynthesisRequestV1,
    SpeechSynthesisResultV1,
    VoiceCloneReferenceV1,
)
from app.domain.studios.providers import (
    SPEECH_PROVIDERS,
    VOICE_CLONE_PROVIDERS,
    VOICE_REFERENCE_NORMALIZERS,
)
from app.models import (
    LibraryAsset,
    StudioConsentGrant,
    StudioGenerationJob,
    StudioIdentityProfile,
    StudioModelRegistration,
    StudioProviderRegistration,
    StudioVoiceProfile,
    StudioVoiceVersion,
    User,
)
from app.services.object_storage import LocalObjectStorage, object_key, sha256_file
from app.services.studios.jobs import create_job, execute_job_once


class FakeSpeechProvider:
    name = "fake.speech.v1"
    version = "1.0.0"

    def synthesize(self, request, destination: Path, progress, is_cancelled):
        progress(40)
        if is_cancelled():
            raise InterruptedError
        frames = b"\x00\x00" * (request.sample_rate // 10)
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(request.sample_rate)
            output.writeframes(frames)
        return SpeechSynthesisResultV1(
            provider=self.name,
            provider_version=self.version,
            audio_format=request.audio_format,
            sample_rate=request.sample_rate,
            duration_ms=100,
            artifact_checksum_sha256=sha256_file(destination),
            provenance=SpeechProvenanceV1(
                source_revision="fake-revision-1",
                model_digest_sha256="1" * 64,
                worker_manifest_digest_sha256="2" * 64,
                worker_image_digest=f"sha256:{'3' * 64}",
                provenance_mode="test-fixture",
            ),
            metrics={"realTimeFactor": 0.01},
        )


class TamperedSpeechProvider(FakeSpeechProvider):
    name = "fake.speech.tampered"

    def synthesize(self, request, destination: Path, progress, is_cancelled):
        result = super().synthesize(request, destination, progress, is_cancelled)
        return result.model_copy(update={"artifact_checksum_sha256": "f" * 64})


class FakeVoiceReferenceNormalizer:
    name = "builtin.ffmpeg-voice-reference-v1"
    version = "test"

    def __init__(self) -> None:
        self.normalized_path: Path | None = None

    def normalize(
        self,
        source,
        destination,
        *,
        voice_version_id,
        consent_grant_id,
        source_asset_id,
        source_checksum_sha256,
        progress,
        is_cancelled,
    ):
        assert source.is_file()
        assert sha256_file(source) == source_checksum_sha256
        assert not is_cancelled()
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24_000)
            output.writeframes(b"\x00\x00" * 24_000 * 4)
        self.normalized_path = destination
        progress(15)
        return VoiceCloneReferenceV1(
            voice_version_id=voice_version_id,
            consent_grant_id=consent_grant_id,
            source_asset_id=source_asset_id,
            source_checksum_sha256=source_checksum_sha256,
            normalized_checksum_sha256=sha256_file(destination),
            duration_ms=4_000,
        )


class FakeVoiceCloneProvider:
    name = "fake.voice-clone.v1"
    version = "1.0.0"

    def __init__(self) -> None:
        self.reference_path: Path | None = None

    def clone(
        self,
        request,
        reference,
        reference_path,
        destination,
        progress,
        is_cancelled,
    ):
        assert request.voice_key == reference.voice_version_id
        assert reference_path.is_file()
        assert sha256_file(reference_path) == reference.normalized_checksum_sha256
        assert not is_cancelled()
        self.reference_path = reference_path
        with wave.open(str(destination), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(request.sample_rate)
            output.writeframes(b"\x00\x00" * request.sample_rate)
        progress(80)
        return SpeechSynthesisResultV1(
            provider=self.name,
            provider_version=self.version,
            audio_format="wav",
            sample_rate=request.sample_rate,
            duration_ms=1_000,
            artifact_checksum_sha256=sha256_file(destination),
            provenance=SpeechProvenanceV1(
                source_revision="fake-clone-revision",
                model_digest_sha256="4" * 64,
                worker_manifest_digest_sha256="5" * 64,
                worker_image_digest=f"sha256:{'6' * 64}",
                provenance_mode="test-clone-sidecar",
                voice_version_id=reference.voice_version_id,
                consent_grant_id=reference.consent_grant_id,
                voice_reference_checksum_sha256=reference.normalized_checksum_sha256,
            ),
            metrics={"realTimeFactor": 0.1},
        )


def _job_request(workspace_id: str, provider: str) -> CreateGenerationJobRequest:
    text = "Café Aurora: uma pausa boa começa aqui."
    speech = SpeechSynthesisRequestV1(
        locale="pt-BR",
        text=text,
        script_digest_sha256=hashlib.sha256(text.encode()).hexdigest(),
        voice_key="pt-br-stock-01",
    )
    return CreateGenerationJobRequest(
        workspace_id=workspace_id,
        job_type="stock_voice",
        provider=provider,
        request=speech.model_dump(by_alias=True, mode="json"),
    )


def _clone_job_request(
    workspace_id: str,
    provider: str,
    *,
    voice_version_id: str,
    consent_grant_id: str,
    voice_key: str | None = None,
) -> CreateGenerationJobRequest:
    text = "Café Aurora: sua pausa com a sua própria voz."
    speech = SpeechSynthesisRequestV1(
        locale="pt-BR",
        text=text,
        script_digest_sha256=hashlib.sha256(text.encode()).hexdigest(),
        voice_key=voice_key or voice_version_id,
    )
    return CreateGenerationJobRequest(
        workspace_id=workspace_id,
        job_type="voice_clone",
        provider=provider,
        voice_version_id=voice_version_id,
        consent_grant_id=consent_grant_id,
        request=speech.model_dump(by_alias=True, mode="json"),
    )


def _admit_fake_provider(db, provider_name: str) -> None:
    provider = StudioProviderRegistration(
        capability="stock_voice",
        provider=provider_name,
        provider_version="1.0.0",
        source_url="https://example.invalid/fake-speech",
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
            name="fake-speech-model",
            version="1.0.0",
            digest_sha256="1" * 64,
            model_license="MIT",
            commercial_use="approved",
            languages=["pt-BR"],
            capabilities=["stock_voice"],
            status="approved",
            manifest={"benchmarkStatus": "passed"},
        )
    )
    db.flush()


def _admit_fake_voice_clone_provider(db, provider_name: str) -> None:
    provider = StudioProviderRegistration(
        capability="voice_clone",
        provider=provider_name,
        provider_version="1.0.0",
        source_url="https://example.invalid/fake-voice-clone",
        source_revision="fake-clone-revision",
        code_license="MIT",
        status="approved",
        risk_class="biometric",
        manifest={"benchmarkStatus": "passed", "workerAdvertised": True},
    )
    db.add(provider)
    db.flush()
    db.add(
        StudioModelRegistration(
            provider_registration_id=provider.id,
            name="fake-voice-clone-model",
            version="1.0.0",
            digest_sha256="4" * 64,
            model_license="MIT",
            commercial_use="approved",
            languages=["pt-BR"],
            capabilities=["voice_clone"],
            status="approved",
            manifest={"benchmarkStatus": "passed"},
        )
    )
    db.flush()


def _create_voice_clone_identity(db, tmp_path: Path, storage: LocalObjectStorage, user, workspace_id: str):
    source = tmp_path / "consented-reference.wav"
    with wave.open(str(source), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(48_000)
        output.writeframes(b"\x00\x00\x00\x00" * 48_000 * 4)
    stored = storage.put_file(
        source,
        key=object_key(workspace_id, "identity", ".wav"),
        media_type="audio/wav",
        metadata={"purpose": "consented-voice-reference"},
    )
    asset = LibraryAsset(
        workspace_id=workspace_id,
        title="Referência consentida",
        asset_type="audio",
        storage_key=stored.key,
        storage_backend=stored.backend,
        media_type=stored.media_type,
        size_bytes=stored.size_bytes,
        checksum_sha256=stored.checksum_sha256,
        object_metadata=stored.metadata,
    )
    db.add(asset)
    db.flush()

    consent = StudioConsentGrant(
        workspace_id=workspace_id,
        subject_key="subject-owner-001",
        subject_display_name="Pessoa autorizadora",
        purpose="Gerar amostra privada da própria voz",
        scopes=["voice.enroll", "voice.clone"],
        brand_ids=[],
        channels=["private_preview"],
        policy_version="voice-consent-v1",
        status="active",
        granted_by=user.id,
        expires_at=datetime.now(UTC) + timedelta(days=30),
    )
    db.add(consent)
    db.flush()
    identity = StudioIdentityProfile(
        workspace_id=workspace_id,
        subject_key=consent.subject_key,
        display_name=consent.subject_display_name,
        identity_type="natural_person",
        status="active",
        owner_user_id=user.id,
        created_by=user.id,
    )
    db.add(identity)
    db.flush()
    profile = StudioVoiceProfile(
        workspace_id=workspace_id,
        identity_profile_id=identity.id,
        display_name="Voz consentida",
        locale="pt-BR",
        voice_type="cloned",
        status="active",
        created_by=user.id,
    )
    db.add(profile)
    db.flush()
    version = StudioVoiceVersion(
        workspace_id=workspace_id,
        profile_id=profile.id,
        version=1,
        consent_grant_id=consent.id,
        status="active",
        sample_asset_ids=[asset.id],
        derived_artifacts=[],
        pronunciation_profile={"primarySampleAssetId": asset.id},
        content_hash="7" * 64,
        created_by=user.id,
        reviewed_by=user.id,
        reviewed_at=datetime.now(UTC),
        review_comment="Fixture de integração privada",
    )
    db.add(version)
    db.flush()
    return asset, consent, version


def test_speech_job_persists_private_audio_lineage_and_checksum(client, tmp_path, monkeypatch) -> None:
    _, workspace_id = register(client, "speech-execution@example.com", "Speech Execution")
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    monkeypatch.setattr(speech_service, "get_object_storage", lambda: storage)
    monkeypatch.setitem(SPEECH_PROVIDERS, FakeSpeechProvider.name, FakeSpeechProvider())

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "speech-execution@example.com"))
        assert user is not None
        _admit_fake_provider(db, FakeSpeechProvider.name)
        job, created = create_job(db, _job_request(workspace_id, FakeSpeechProvider.name), "speech-real-001", user)
        assert created is True
        assert execute_job_once(db, job) == "succeeded"
        db.refresh(job)
        result = job.result_payload
        assert result["schemaVersion"] == "studio.speech-synthesis-job-result.v1"
        assert result["speech"]["schemaVersion"] == "studio.speech-synthesis-result.v1"
        assert result["speech"]["provenance"]["syntheticContentDisclosed"] is True
        asset = db.get(LibraryAsset, result["assetId"])
        assert asset is not None
        assert asset.workspace_id == workspace_id
        assert asset.storage_key.startswith(f"{workspace_id}/voice/")
        assert storage.exists(asset.storage_key)
        assert asset.checksum_sha256 == result["checksumSha256"]
        assert asset.object_metadata["generationJobId"] == job.id
        assert asset.object_metadata["speechSynthesisJobResult"]["assetId"] == asset.id
        assert db.scalar(
            select(StudioGenerationJob).where(StudioGenerationJob.id == job.id)
        ).worker_execution_context["attested"] is False


def test_speech_job_rejects_provider_checksum_tampering_without_asset(client, tmp_path, monkeypatch) -> None:
    _, workspace_id = register(client, "speech-tamper@example.com", "Speech Tamper")
    storage_root = tmp_path / "storage"
    storage = LocalObjectStorage(str(storage_root))
    monkeypatch.setattr(speech_service, "get_object_storage", lambda: storage)
    monkeypatch.setitem(SPEECH_PROVIDERS, TamperedSpeechProvider.name, TamperedSpeechProvider())

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "speech-tamper@example.com"))
        assert user is not None
        _admit_fake_provider(db, TamperedSpeechProvider.name)
        job, _ = create_job(db, _job_request(workspace_id, TamperedSpeechProvider.name), "speech-tamper-001", user)
        for _ in range(job.max_attempts):
            execute_job_once(db, job)
        db.refresh(job)
        assert job.status == "failed"
        assert job.error_message == "speech_result_binding_mismatch"
        assert db.scalars(select(LibraryAsset).where(LibraryAsset.workspace_id == workspace_id)).all() == []
        assert not storage_root.exists() or not any(storage_root.rglob("*"))


def test_worker_rejects_legacy_voice_clone_without_binding_before_provider(client, tmp_path, monkeypatch) -> None:
    _, workspace_id = register(client, "speech-legacy-clone@example.com", "Speech Legacy Clone")
    storage_root = tmp_path / "storage"
    storage = LocalObjectStorage(str(storage_root))
    monkeypatch.setattr(speech_service, "get_object_storage", lambda: storage)
    monkeypatch.setitem(SPEECH_PROVIDERS, FakeSpeechProvider.name, FakeSpeechProvider())

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "speech-legacy-clone@example.com"))
        assert user is not None
        job = StudioGenerationJob(
            workspace_id=workspace_id,
            job_type="voice_clone",
            provider=FakeSpeechProvider.name,
            execution_capability="speech_gpu",
            queue_name="studio.gpu.speech",
            resource_class="gpu.speech",
            hard_time_limit_seconds=3_600,
            idempotency_key="legacy-clone-without-binding",
            payload_hash="a" * 64,
            correlation_id="legacy-clone-without-binding",
            request_payload={"locale": "pt-BR", "text": "não deve sintetizar"},
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        assert execute_job_once(db, job) == "retrying"
        db.refresh(job)
        assert job.error_message == "voice_version_required"
        assert db.scalars(select(LibraryAsset).where(LibraryAsset.workspace_id == workspace_id)).all() == []
        assert not storage_root.exists() or not any(storage_root.rglob("*"))


def test_voice_clone_uses_ephemeral_consent_bound_reference(client, tmp_path, monkeypatch) -> None:
    _, workspace_id = register(client, "voice-clone-execution@example.com", "Voice Clone Execution")
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    normalizer = FakeVoiceReferenceNormalizer()
    provider = FakeVoiceCloneProvider()
    monkeypatch.setattr(speech_service, "get_object_storage", lambda *_: storage)
    monkeypatch.setitem(VOICE_REFERENCE_NORMALIZERS, normalizer.name, normalizer)
    monkeypatch.setitem(VOICE_CLONE_PROVIDERS, provider.name, provider)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "voice-clone-execution@example.com"))
        assert user is not None
        source_asset, consent, version = _create_voice_clone_identity(
            db, tmp_path, storage, user, workspace_id
        )
        _admit_fake_voice_clone_provider(db, provider.name)
        job, created = create_job(
            db,
            _clone_job_request(
                workspace_id,
                provider.name,
                voice_version_id=version.id,
                consent_grant_id=consent.id,
            ),
            "voice-clone-real-001",
            user,
        )

        assert created is True
        assert execute_job_once(db, job) == "succeeded"
        db.refresh(job)
        result = job.result_payload
        reference = result["voiceReference"]
        provenance = result["speech"]["provenance"]
        assert reference["schemaVersion"] == "studio.voice-clone-reference.v1"
        assert reference["retentionMode"] == "job-ephemeral"
        assert reference["voiceVersionId"] == version.id
        assert reference["consentGrantId"] == consent.id
        assert reference["sourceAssetId"] == source_asset.id
        assert reference["sourceChecksumSha256"] == source_asset.checksum_sha256
        assert provenance["voiceVersionId"] == version.id
        assert provenance["consentGrantId"] == consent.id
        assert provenance["voiceReferenceChecksumSha256"] == reference["normalizedChecksumSha256"]

        output_asset = db.get(LibraryAsset, result["assetId"])
        assert output_asset is not None
        assert output_asset.storage_key.startswith(f"{workspace_id}/voice/")
        assert storage.exists(output_asset.storage_key)
        assert storage.exists(source_asset.storage_key)

    assert normalizer.normalized_path is not None
    assert provider.reference_path == normalizer.normalized_path
    assert not normalizer.normalized_path.exists()


def test_voice_clone_rejects_request_version_mismatch_before_reference_handoff(
    client, tmp_path, monkeypatch
) -> None:
    _, workspace_id = register(client, "voice-clone-mismatch@example.com", "Voice Clone Mismatch")
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    normalizer = FakeVoiceReferenceNormalizer()
    provider = FakeVoiceCloneProvider()
    monkeypatch.setattr(speech_service, "get_object_storage", lambda *_: storage)
    monkeypatch.setitem(VOICE_REFERENCE_NORMALIZERS, normalizer.name, normalizer)
    monkeypatch.setitem(VOICE_CLONE_PROVIDERS, provider.name, provider)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "voice-clone-mismatch@example.com"))
        assert user is not None
        source_asset, consent, version = _create_voice_clone_identity(
            db, tmp_path, storage, user, workspace_id
        )
        _admit_fake_voice_clone_provider(db, provider.name)
        job, _ = create_job(
            db,
            _clone_job_request(
                workspace_id,
                provider.name,
                voice_version_id=version.id,
                consent_grant_id=consent.id,
                voice_key="different-voice-version",
            ),
            "voice-clone-mismatch-001",
            user,
        )

        assert execute_job_once(db, job) == "retrying"
        db.refresh(job)
        assert job.error_message == "voice_clone_request_version_mismatch"
        assert normalizer.normalized_path is None
        assert provider.reference_path is None
        assert storage.exists(source_asset.storage_key)


def test_voice_clone_rejects_tampered_source_before_normalization(client, tmp_path, monkeypatch) -> None:
    _, workspace_id = register(client, "voice-clone-source-tamper@example.com", "Voice Source Tamper")
    storage = LocalObjectStorage(str(tmp_path / "storage"))
    normalizer = FakeVoiceReferenceNormalizer()
    provider = FakeVoiceCloneProvider()
    monkeypatch.setattr(speech_service, "get_object_storage", lambda *_: storage)
    monkeypatch.setitem(VOICE_REFERENCE_NORMALIZERS, normalizer.name, normalizer)
    monkeypatch.setitem(VOICE_CLONE_PROVIDERS, provider.name, provider)

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == "voice-clone-source-tamper@example.com"))
        assert user is not None
        source_asset, consent, version = _create_voice_clone_identity(
            db, tmp_path, storage, user, workspace_id
        )
        source_path = storage.local_path(source_asset.storage_key)
        assert source_path is not None
        source_path.write_bytes(source_path.read_bytes() + b"tampered")
        _admit_fake_voice_clone_provider(db, provider.name)
        job, _ = create_job(
            db,
            _clone_job_request(
                workspace_id,
                provider.name,
                voice_version_id=version.id,
                consent_grant_id=consent.id,
            ),
            "voice-clone-source-tamper-001",
            user,
        )

        assert execute_job_once(db, job) == "retrying"
        db.refresh(job)
        assert job.error_message == "voice_reference_source_checksum_mismatch"
        assert normalizer.normalized_path is None
        assert provider.reference_path is None
