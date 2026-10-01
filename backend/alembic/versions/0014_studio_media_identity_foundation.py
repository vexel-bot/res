"""Add Studio media identity, consent, and provider registries.

Revision ID: 0014_media_identity
Revises: 0013_studio_document_idempotency
"""

import sqlalchemy as sa

from alembic import op

revision = "0014_media_identity"
down_revision = "0013_studio_document_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())

    if not inspector.has_table("studio_consent_grants"):
        op.create_table(
            "studio_consent_grants",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("subject_key", sa.String(length=160), nullable=False),
            sa.Column("subject_display_name", sa.String(length=240), nullable=False),
            sa.Column("purpose", sa.Text(), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=False),
            sa.Column("brand_ids", sa.JSON(), nullable=False),
            sa.Column("channels", sa.JSON(), nullable=False),
            sa.Column("policy_version", sa.String(length=120), nullable=False),
            sa.Column("evidence_asset_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("granted_by", sa.String(length=36), nullable=False),
            sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_by", sa.String(length=36), nullable=True),
            sa.Column("revocation_reason", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["evidence_asset_id"], ["library_assets.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["granted_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["revoked_by"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_studio_consent_grants_workspace_id", "studio_consent_grants", ["workspace_id"])
        op.create_index("ix_studio_consent_grants_evidence_asset_id", "studio_consent_grants", ["evidence_asset_id"])
        op.create_index("ix_studio_consent_grants_granted_by", "studio_consent_grants", ["granted_by"])
        op.create_index("ix_studio_consent_grants_revoked_by", "studio_consent_grants", ["revoked_by"])
        op.create_index("ix_studio_consent_grants_expires_at", "studio_consent_grants", ["expires_at"])
        op.create_index("ix_studio_consents_workspace_status", "studio_consent_grants", ["workspace_id", "status"])
        op.create_index("ix_studio_consents_subject", "studio_consent_grants", ["workspace_id", "subject_key"])

    if not inspector.has_table("studio_identity_profiles"):
        op.create_table(
            "studio_identity_profiles",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("subject_key", sa.String(length=160), nullable=False),
            sa.Column("display_name", sa.String(length=240), nullable=False),
            sa.Column("identity_type", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("owner_user_id", sa.String(length=36), nullable=True),
            sa.Column("created_by", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["owner_user_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workspace_id", "subject_key", name="uq_studio_identity_subject"),
        )
        op.create_index("ix_studio_identity_profiles_workspace_id", "studio_identity_profiles", ["workspace_id"])
        op.create_index("ix_studio_identity_profiles_owner_user_id", "studio_identity_profiles", ["owner_user_id"])
        op.create_index("ix_studio_identity_profiles_created_by", "studio_identity_profiles", ["created_by"])
        op.create_index("ix_studio_identity_workspace_status", "studio_identity_profiles", ["workspace_id", "status"])

    if not inspector.has_table("studio_identity_versions"):
        op.create_table(
            "studio_identity_versions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("profile_id", sa.String(length=36), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("consent_grant_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("capabilities", sa.JSON(), nullable=False),
            sa.Column("sample_asset_ids", sa.JSON(), nullable=False),
            sa.Column("derived_artifacts", sa.JSON(), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["consent_grant_id"], ["studio_consent_grants.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["profile_id"], ["studio_identity_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("profile_id", "version", name="uq_studio_identity_version"),
        )
        op.create_index("ix_studio_identity_versions_workspace_id", "studio_identity_versions", ["workspace_id"])
        op.create_index("ix_studio_identity_versions_profile_id", "studio_identity_versions", ["profile_id"])
        op.create_index(
            "ix_studio_identity_versions_consent_grant_id",
            "studio_identity_versions",
            ["consent_grant_id"],
        )
        op.create_index("ix_studio_identity_versions_created_by", "studio_identity_versions", ["created_by"])
        op.create_index(
            "ix_studio_identity_versions_workspace_status", "studio_identity_versions", ["workspace_id", "status"]
        )

    if not inspector.has_table("studio_voice_profiles"):
        op.create_table(
            "studio_voice_profiles",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("identity_profile_id", sa.String(length=36), nullable=True),
            sa.Column("display_name", sa.String(length=240), nullable=False),
            sa.Column("locale", sa.String(length=32), nullable=False),
            sa.Column("voice_type", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["identity_profile_id"], ["studio_identity_profiles.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_studio_voice_profiles_workspace_id", "studio_voice_profiles", ["workspace_id"])
        op.create_index(
            "ix_studio_voice_profiles_identity_profile_id",
            "studio_voice_profiles",
            ["identity_profile_id"],
        )
        op.create_index("ix_studio_voice_profiles_created_by", "studio_voice_profiles", ["created_by"])
        op.create_index("ix_studio_voice_workspace_status", "studio_voice_profiles", ["workspace_id", "status"])

    if not inspector.has_table("studio_voice_versions"):
        op.create_table(
            "studio_voice_versions",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("profile_id", sa.String(length=36), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("consent_grant_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("sample_asset_ids", sa.JSON(), nullable=False),
            sa.Column("derived_artifacts", sa.JSON(), nullable=False),
            sa.Column("pronunciation_profile", sa.JSON(), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["consent_grant_id"], ["studio_consent_grants.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["profile_id"], ["studio_voice_profiles.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("profile_id", "version", name="uq_studio_voice_version"),
        )
        op.create_index("ix_studio_voice_versions_workspace_id", "studio_voice_versions", ["workspace_id"])
        op.create_index("ix_studio_voice_versions_profile_id", "studio_voice_versions", ["profile_id"])
        op.create_index("ix_studio_voice_versions_consent_grant_id", "studio_voice_versions", ["consent_grant_id"])
        op.create_index("ix_studio_voice_versions_created_by", "studio_voice_versions", ["created_by"])
        op.create_index(
            "ix_studio_voice_versions_workspace_status", "studio_voice_versions", ["workspace_id", "status"]
        )

    if not inspector.has_table("studio_provider_registrations"):
        op.create_table(
            "studio_provider_registrations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("capability", sa.String(length=120), nullable=False),
            sa.Column("provider", sa.String(length=120), nullable=False),
            sa.Column("provider_version", sa.String(length=120), nullable=False),
            sa.Column("source_url", sa.Text(), nullable=False),
            sa.Column("source_revision", sa.String(length=160), nullable=False),
            sa.Column("code_license", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("risk_class", sa.String(length=32), nullable=False),
            sa.Column("manifest", sa.JSON(), nullable=False),
            sa.Column("approved_by", sa.String(length=36), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("capability", "provider", "provider_version", name="uq_studio_provider_version"),
        )
        op.create_index(
            "ix_studio_provider_capability_status", "studio_provider_registrations", ["capability", "status"]
        )
        op.create_index(
            "ix_studio_provider_registrations_approved_by",
            "studio_provider_registrations",
            ["approved_by"],
        )

    if not inspector.has_table("studio_model_registrations"):
        op.create_table(
            "studio_model_registrations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("provider_registration_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=240), nullable=False),
            sa.Column("version", sa.String(length=120), nullable=False),
            sa.Column("digest_sha256", sa.String(length=64), nullable=False),
            sa.Column("model_license", sa.String(length=160), nullable=False),
            sa.Column("commercial_use", sa.String(length=32), nullable=False),
            sa.Column("languages", sa.JSON(), nullable=False),
            sa.Column("capabilities", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("manifest", sa.JSON(), nullable=False),
            sa.Column("approved_by", sa.String(length=36), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["approved_by"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(
                ["provider_registration_id"], ["studio_provider_registrations.id"], ondelete="CASCADE"
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("digest_sha256", name="uq_studio_model_digest"),
            sa.UniqueConstraint(
                "provider_registration_id", "name", "version", name="uq_studio_model_version"
            ),
        )
        op.create_index(
            "ix_studio_model_registrations_provider_registration_id",
            "studio_model_registrations",
            ["provider_registration_id"],
        )
        op.create_index("ix_studio_model_status", "studio_model_registrations", ["status"])
        op.create_index("ix_studio_model_registrations_approved_by", "studio_model_registrations", ["approved_by"])

    job_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")}
    job_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("studio_generation_jobs")}
    with op.batch_alter_table("studio_generation_jobs") as batch:
        if "consent_grant_id" not in job_columns:
            batch.add_column(sa.Column("consent_grant_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_studio_jobs_consent_grant",
                "studio_consent_grants",
                ["consent_grant_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "identity_version_id" not in job_columns:
            batch.add_column(sa.Column("identity_version_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_studio_jobs_identity_version",
                "studio_identity_versions",
                ["identity_version_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "voice_version_id" not in job_columns:
            batch.add_column(sa.Column("voice_version_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_studio_jobs_voice_version",
                "studio_voice_versions",
                ["voice_version_id"],
                ["id"],
                ondelete="SET NULL",
            )
        if "ix_studio_generation_jobs_consent_grant_id" not in job_indexes:
            batch.create_index("ix_studio_generation_jobs_consent_grant_id", ["consent_grant_id"])
        if "ix_studio_generation_jobs_identity_version_id" not in job_indexes:
            batch.create_index("ix_studio_generation_jobs_identity_version_id", ["identity_version_id"])
        if "ix_studio_generation_jobs_voice_version_id" not in job_indexes:
            batch.create_index("ix_studio_generation_jobs_voice_version_id", ["voice_version_id"])


def downgrade() -> None:
    is_sqlite = op.get_bind().dialect.name == "sqlite"
    job_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")}
    with op.batch_alter_table("studio_generation_jobs") as batch:
        if "voice_version_id" in job_columns:
            batch.drop_index("ix_studio_generation_jobs_voice_version_id")
            if not is_sqlite:
                batch.drop_constraint("fk_studio_jobs_voice_version", type_="foreignkey")
            batch.drop_column("voice_version_id")
        if "identity_version_id" in job_columns:
            batch.drop_index("ix_studio_generation_jobs_identity_version_id")
            if not is_sqlite:
                batch.drop_constraint("fk_studio_jobs_identity_version", type_="foreignkey")
            batch.drop_column("identity_version_id")
        if "consent_grant_id" in job_columns:
            batch.drop_index("ix_studio_generation_jobs_consent_grant_id")
            if not is_sqlite:
                batch.drop_constraint("fk_studio_jobs_consent_grant", type_="foreignkey")
            batch.drop_column("consent_grant_id")

    op.drop_table("studio_model_registrations")
    op.drop_table("studio_provider_registrations")
    op.drop_table("studio_voice_versions")
    op.drop_table("studio_voice_profiles")
    op.drop_table("studio_identity_versions")
    op.drop_table("studio_identity_profiles")
    op.drop_table("studio_consent_grants")
