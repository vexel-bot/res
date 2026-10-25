"""Independent face/voice enrollment and the real, workspace-owned cast catalog."""

from datetime import datetime
from hashlib import sha256
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field, field_validator, model_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.studios.contracts import (
    CreateConsentGrantRequest,
    CreateIdentityProfileRequest,
    CreateIdentityVersionRequest,
    CreateVoiceProfileRequest,
    CreateVoiceVersionRequest,
    StudioContract,
)
from ..models import (
    LibraryAsset,
    Membership,
    StudioConsentGrant,
    StudioIdentityProfile,
    StudioIdentityVersion,
    StudioVoiceProfile,
    StudioVoiceVersion,
    User,
    WorkspaceResource,
)
from ..security import get_current_user
from ..services.studios import identity
from ..services.studios.casting import resolve_cast
from .studios import assert_access, studio_identity_error, validate_references

router = APIRouter(prefix="/studios/v1/identity-library", tags=["studio-identity-library"])
KIND = "studio_identity_enrollment"


class EnrollmentRequest(StudioContract):
    workspace_id: str
    request_key: str = Field(min_length=8, max_length=80)
    mode: Literal["face", "voice", "face_voice", "character", "stock_voice"]
    display_name: str = Field(min_length=2, max_length=160)
    image_asset_id: str | None = None
    audio_asset_id: str | None = None
    evidence_asset_id: str
    purpose: str = Field(min_length=8, max_length=2000)
    expires_at: datetime | None = None
    rights_reference: str = Field(default="", max_length=2000)
    declared: Literal[True]

    @field_validator("display_name", "purpose", "rights_reference", mode="before")
    @classmethod
    def trim_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @model_validator(mode="after")
    def mode_inputs(self):
        if (self.mode in {"face", "face_voice", "character"}) != bool(self.image_asset_id):
            raise ValueError("Informe uma imagem apenas para o cadastro de rosto/personagem.")
        if (self.mode in {"voice", "face_voice", "stock_voice"}) != bool(self.audio_asset_id):
            raise ValueError("Informe uma amostra de áudio apenas para o cadastro de voz.")
        if self.mode in {"character", "stock_voice"}:
            if len(self.rights_reference.strip()) < 8:
                raise ValueError("Informe a origem e os direitos de uso do personagem ou voz.")
        elif not self.expires_at:
            raise ValueError("Informe o prazo da autorização.")
        if self.evidence_asset_id in {self.image_asset_id, self.audio_asset_id}:
            raise ValueError("Anexe a autorização separadamente das amostras de rosto e voz.")
        return self


def stored_asset(db, workspace_id, asset_id, prefix=None):
    asset = db.get(LibraryAsset, asset_id)
    if not asset or asset.workspace_id != workspace_id:
        raise ValueError("identity_sample_not_found")
    if asset.lifecycle_status != "active" or not asset.storage_key or not asset.checksum_sha256:
        raise ValueError("identity_sample_not_stored")
    if prefix and not (asset.media_type or "").startswith(prefix):
        raise ValueError("identity_sample_media_type_mismatch")
    return asset


@router.post("/enrollments", status_code=201)
def enroll(request: EnrollmentRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assert_access(db, user.id, request.workspace_id)
    fingerprint = sha256(request.model_dump_json(exclude={"request_key"}).encode()).hexdigest()

    def replay():
        row = db.scalar(
            select(WorkspaceResource).where(
                WorkspaceResource.workspace_id == request.workspace_id,
                WorkspaceResource.kind == KIND,
                WorkspaceResource.resource_key == request.request_key,
            )
        )
        if row and row.payload["fingerprint"] != fingerprint:
            raise HTTPException(409, "Este pedido de cadastro já foi usado com outros dados.")
        return row

    existing = replay()
    if existing:
        return existing.payload["receipt"]
    validate_references(
        db,
        request.workspace_id,
        asset_ids=[
            value for value in [request.image_asset_id, request.audio_asset_id, request.evidence_asset_id] if value
        ],
    )
    try:
        stored_asset(db, request.workspace_id, request.evidence_asset_id)
        if request.image_asset_id:
            stored_asset(db, request.workspace_id, request.image_asset_id, "image/")
        if request.audio_asset_id:
            stored_asset(db, request.workspace_id, request.audio_asset_id, "audio/")
        subject_key = f"{'character' if request.mode == 'character' else 'person'}/{uuid4()}"
        grant = None
        if request.mode not in {"character", "stock_voice"}:
            scopes = []
            if request.image_asset_id:
                scopes += ["identity.enroll", "avatar.generate"]
            if request.audio_asset_id:
                scopes += ["voice.enroll", "voice.clone"]
            grant = identity.create_consent_grant(
                db,
                CreateConsentGrantRequest(
                    workspace_id=request.workspace_id,
                    subject_key=subject_key,
                    subject_display_name=request.display_name.strip(),
                    purpose=request.purpose.strip(),
                    scopes=scopes,
                    channels=["private-preview"],
                    policy_version="clicko.identity-consent.v1",
                    evidence_asset_id=request.evidence_asset_id,
                    expires_at=request.expires_at,
                ),
                user,
                commit=False,
            )
        profile = version = voice = voice_version = None
        if request.mode != "stock_voice":
            profile = identity.create_identity_profile(
                db,
                CreateIdentityProfileRequest(
                    workspace_id=request.workspace_id,
                    subject_key=subject_key,
                    display_name=request.display_name.strip(),
                    identity_type="synthetic_character" if request.mode == "character" else "natural_person",
                ),
                user,
                commit=False,
            )
        if request.image_asset_id:
            version = identity.create_identity_version(
                db,
                profile,
                CreateIdentityVersionRequest(
                    consent_grant_id=grant.id if grant else None,
                    capabilities=["image.use", "avatar.generate"],
                    sample_asset_ids=[request.image_asset_id],
                ),
                user,
                commit=False,
            )
        if request.audio_asset_id:
            voice = identity.create_voice_profile(
                db,
                CreateVoiceProfileRequest(
                    workspace_id=request.workspace_id,
                    identity_profile_id=profile.id if profile else None,
                    display_name=request.display_name.strip(),
                    locale="pt-BR",
                    voice_type="stock" if request.mode == "stock_voice" else "cloned",
                ),
                user,
                commit=False,
            )
            voice_version = identity.create_voice_version(
                db,
                voice,
                CreateVoiceVersionRequest(
                    consent_grant_id=grant.id if grant else None,
                    sample_asset_ids=[request.audio_asset_id],
                ),
                user,
                commit=False,
            )
        receipt = {
            "schemaVersion": "clicko.identity-enrollment.v1",
            "identityProfileId": profile.id if profile else None,
            "identityVersionId": version.id if version else None,
            "voiceProfileId": voice.id if voice else None,
            "voiceVersionId": voice_version.id if voice_version else None,
            "consentGrantId": grant.id if grant else None,
            "status": "draft",
        }
        db.add(
            WorkspaceResource(
                workspace_id=request.workspace_id,
                kind=KIND,
                resource_key=request.request_key,
                created_by=user.id,
                payload={
                    "fingerprint": fingerprint,
                    "receipt": receipt,
                    "mode": request.mode,
                    "purpose": request.purpose,
                    "evidenceAssetId": request.evidence_asset_id,
                    "rightsReference": request.rights_reference,
                },
            )
        )
        db.commit()
        return receipt
    except IntegrityError:
        db.rollback()
        existing = replay()
        if existing:
            return existing.payload["receipt"]
        raise HTTPException(409, "O cadastro foi alterado em outra sessão. Recarregue.") from None
    except ValueError as error:
        db.rollback()
        raise studio_identity_error(error) from error


@router.get("")
def catalog(workspace_id: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    assert_access(db, user.id, workspace_id)
    identities = db.scalars(
        select(StudioIdentityProfile)
        .where(StudioIdentityProfile.workspace_id == workspace_id)
        .order_by(StudioIdentityProfile.created_at.desc())
    ).all()
    voices = db.scalars(
        select(StudioVoiceProfile)
        .where(StudioVoiceProfile.workspace_id == workspace_id)
        .order_by(StudioVoiceProfile.created_at.desc())
    ).all()
    identity_versions = db.scalars(
        select(StudioIdentityVersion)
        .where(StudioIdentityVersion.workspace_id == workspace_id)
        .order_by(StudioIdentityVersion.version.desc())
    ).all()
    voice_versions = db.scalars(
        select(StudioVoiceVersion)
        .where(StudioVoiceVersion.workspace_id == workspace_id)
        .order_by(StudioVoiceVersion.version.desc())
    ).all()
    sample_ids = {
        asset_id for version in [*identity_versions, *voice_versions] for asset_id in version.sample_asset_ids
    }
    assets = (
        {
            asset.id: asset
            for asset in db.scalars(
                select(LibraryAsset).where(LibraryAsset.workspace_id == workspace_id, LibraryAsset.id.in_(sample_ids))
            ).all()
        }
        if sample_ids
        else {}
    )

    def card(profile, versions, kind):
        relevant = [version for version in versions if version.profile_id == profile.id]
        active = next((version for version in relevant if version.status == "active"), None)
        reason = "Sem versão aprovada. O cadastro precisa de avaliação e revisão."
        if active:
            try:
                resolve_cast(
                    db, workspace_id, active.id if kind == "identity" else None, active.id if kind == "voice" else None
                )
                reason = None
            except ValueError as error:
                reason = str(error)
        latest = active or next(iter(relevant), None)
        preview_id = next(
            (
                asset_id
                for asset_id in (latest.sample_asset_ids if latest else [])
                if asset_id in assets
                and assets[asset_id].lifecycle_status == "active"
                and assets[asset_id].storage_key
                and (assets[asset_id].media_type or "").startswith("image/" if kind == "identity" else "audio/")
            ),
            None,
        )
        return {
            "profile": (
                identity.identity_profile_out(profile) if kind == "identity" else identity.voice_profile_out(profile)
            ),
            "versions": [
                (identity.identity_version_out(version) if kind == "identity" else identity.voice_version_out(version))
                for version in relevant
            ],
            "selectedVersionId": active.id if active and not reason else None,
            "previewAssetId": preview_id,
            "unavailableReason": reason,
        }

    grants = db.scalars(select(StudioConsentGrant).where(StudioConsentGrant.workspace_id == workspace_id)).all()
    membership = db.scalar(
        select(Membership).where(Membership.user_id == user.id, Membership.workspace_id == workspace_id)
    )
    return {
        "schemaVersion": "clicko.identity-library.v1",
        "workspaceId": workspace_id,
        "permissions": {"canReview": bool(membership and membership.role.lower() in {"owner", "admin"})},
        "identities": [card(profile, identity_versions, "identity") for profile in identities],
        "voices": [card(profile, voice_versions, "voice") for profile in voices],
        "consents": [identity.consent_out(grant) for grant in grants],
    }
