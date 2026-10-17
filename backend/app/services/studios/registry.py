from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain.studios.contracts import ModelRegistrationV1, ProviderRegistrationV1
from ...models import StudioModelRegistration, StudioProviderRegistration, User


def provider_registration_out(registration: StudioProviderRegistration) -> ProviderRegistrationV1:
    return ProviderRegistrationV1.model_validate(registration)


def model_registration_out(registration: StudioModelRegistration) -> ModelRegistrationV1:
    return ModelRegistrationV1.model_validate(registration)


def register_provider(
    db: Session,
    *,
    capability: str,
    provider: str,
    provider_version: str,
    source_url: str,
    source_revision: str,
    code_license: str,
    risk_class: Literal["low", "medium", "high", "biometric"],
    manifest: dict[str, Any] | None = None,
) -> StudioProviderRegistration:
    existing = db.scalar(
        select(StudioProviderRegistration).where(
            StudioProviderRegistration.capability == capability,
            StudioProviderRegistration.provider == provider,
            StudioProviderRegistration.provider_version == provider_version,
        )
    )
    if existing:
        return existing
    registration = StudioProviderRegistration(
        capability=capability,
        provider=provider,
        provider_version=provider_version,
        source_url=source_url,
        source_revision=source_revision,
        code_license=code_license,
        status="evaluation",
        risk_class=risk_class,
        manifest=manifest or {},
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


def register_model(
    db: Session,
    *,
    provider_registration: StudioProviderRegistration,
    name: str,
    version: str,
    digest_sha256: str,
    model_license: str,
    commercial_use: Literal["approved", "restricted", "unknown"],
    languages: list[str],
    capabilities: list[str],
    manifest: dict[str, Any] | None = None,
) -> StudioModelRegistration:
    existing = db.scalar(
        select(StudioModelRegistration).where(StudioModelRegistration.digest_sha256 == digest_sha256)
    )
    if existing:
        return existing
    registration = StudioModelRegistration(
        provider_registration_id=provider_registration.id,
        name=name,
        version=version,
        digest_sha256=digest_sha256,
        model_license=model_license,
        commercial_use=commercial_use,
        languages=languages,
        capabilities=capabilities,
        status="evaluation",
        manifest=manifest or {},
    )
    db.add(registration)
    db.commit()
    db.refresh(registration)
    return registration


def approve_provider(
    db: Session, registration: StudioProviderRegistration, *, user: User
) -> StudioProviderRegistration:
    required_manifest_fields = {"sbom", "licenseEvidence", "exitStrategy"}
    if not required_manifest_fields.issubset(registration.manifest):
        raise ValueError("provider_manifest_incomplete")
    registration.status = "approved"
    registration.approved_by = user.id
    registration.approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(registration)
    return registration


def approve_model(
    db: Session, registration: StudioModelRegistration, *, user: User
) -> StudioModelRegistration:
    provider = db.get(StudioProviderRegistration, registration.provider_registration_id)
    if not provider or provider.status != "approved":
        raise ValueError("provider_not_approved")
    if registration.commercial_use != "approved":
        raise ValueError("model_commercial_use_not_approved")
    required_manifest_fields = {"weightsSource", "licenseEvidence", "datasetDisclosure", "deletionPolicy"}
    if not required_manifest_fields.issubset(registration.manifest):
        raise ValueError("model_manifest_incomplete")
    registration.status = "approved"
    registration.approved_by = user.id
    registration.approved_at = datetime.now(UTC)
    db.commit()
    db.refresh(registration)
    return registration
