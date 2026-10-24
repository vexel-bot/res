"""Versioned cast selection shared by the library and creative projects."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...models import StudioIdentityProfile, StudioIdentityVersion, StudioVoiceProfile, StudioVoiceVersion


def resolve_cast(db: Session, workspace_id: str, identity_id: str | None, voice_id: str | None):
    from .identity import require_active_version_consent, require_consent

    result = {}
    for kind, version_id, version_type, profile_type in (
        ("identity", identity_id, StudioIdentityVersion, StudioIdentityProfile),
        ("voice", voice_id, StudioVoiceVersion, StudioVoiceProfile),
    ):
        if not version_id:
            continue
        version = db.scalar(
            select(version_type)
            .where(version_type.id == version_id, version_type.workspace_id == workspace_id)
            .execution_options(populate_existing=True)
        )
        if not version:
            raise ValueError(f"{kind}_version_not_found")
        profile = db.get(profile_type, version.profile_id, populate_existing=True)
        if not profile or profile.workspace_id != workspace_id or profile.status != "active":
            raise ValueError(f"{kind}_profile_not_active")
        require_active_version_consent(db, version, consent_grant_id=version.consent_grant_id)
        subject = profile
        scopes = {"identity.enroll", "avatar.generate"}
        if kind == "voice":
            if profile.voice_type == "stock":
                subject = None
            else:
                subject = db.get(StudioIdentityProfile, profile.identity_profile_id, populate_existing=True)
                if (
                    not subject
                    or subject.workspace_id != workspace_id
                    or subject.status in {"revoked", "deleting", "deleted"}
                ):
                    raise ValueError("voice_identity_not_usable")
                scopes = {"voice.enroll", "voice.clone"}
        elif profile.identity_type == "synthetic_character":
            subject = None
        if subject:
            require_consent(
                db,
                consent_grant_id=version.consent_grant_id,
                workspace_id=workspace_id,
                subject_key=subject.subject_key,
                scopes=scopes,
            )
        result[kind] = {"id": version.id, "version": version.version, "consentGrantId": version.consent_grant_id}
    # Appearance and narration are intentionally independent: a stock narrator
    # or another authorized voice can accompany a character or a static image.
    return result


def validate_document_cast(db: Session, document):
    identity = document.identity_ref
    voice = document.voice_ref
    refs = resolve_cast(db, document.workspace_id, identity.id if identity else None, voice.id if voice else None)
    for kind, ref in (("identity", identity), ("voice", voice)):
        if ref and (
            str(ref.version) != str(refs[kind]["version"]) or ref.consent_grant_id != refs[kind]["consentGrantId"]
        ):
            raise ValueError("cast_version_reference_mismatch")


def resolve_avatar_cast(db: Session, record, identity_id: str, voice_id: str, consent_id: str | None):
    """Resolve the two separately authorized subjects of an image/audio avatar.

    The legacy consent field is the appearance grant, or the narrator grant
    when the appearance is synthetic. Neither grant substitutes for the other.
    The returned versioned references are frozen in the execution binding.
    """
    from .compatibility import record_to_contract

    refs = resolve_cast(db, record.workspace_id, identity_id, voice_id)
    version = db.get(StudioIdentityVersion, identity_id)
    if "avatar.generate" not in set(version.capabilities or []):
        raise ValueError("identity_capability_missing")
    primary = refs["identity"]["consentGrantId"] or refs["voice"]["consentGrantId"]
    if primary != consent_id:
        raise ValueError("identity_version_consent_mismatch")
    document = record_to_contract(record)
    for kind, saved in (("identity", document.identity_ref), ("voice", document.voice_ref)):
        if saved and (
            saved.id != refs[kind]["id"]
            or str(saved.version) != str(refs[kind]["version"])
            or saved.consent_grant_id != refs[kind]["consentGrantId"]
        ):
            raise ValueError("cast_version_reference_mismatch")
    return {"schemaVersion": "studio.avatar-cast-binding.v1", **refs}


def validate_publication_cast(db: Session, document, channel: str):
    from ...models import StudioConsentGrant

    validate_document_cast(db, document)
    for ref in (document.identity_ref, document.voice_ref):
        if not ref or not ref.consent_grant_id:
            continue
        grant = db.get(StudioConsentGrant, ref.consent_grant_id, populate_existing=True)
        if "publish.synthetic" not in grant.scopes:
            raise ValueError("cast_publication_scope_missing")
        if grant.channels and channel not in grant.channels:
            raise ValueError("cast_publication_channel_not_authorized")
        if grant.brand_ids and (not document.brand_memory_ref or document.brand_memory_ref.id not in grant.brand_ids):
            raise ValueError("cast_publication_brand_not_authorized")
