"""Add provider-neutral media ingest persistence.

Revision ID: 0018_media_ingest
Revises: 0017_identity_delete
"""

import sqlalchemy as sa

from alembic import op

revision = "0018_media_ingest"
down_revision = "0017_identity_delete"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("studio_media_ingests"):
        return
    op.create_table(
        "studio_media_ingests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("probe_provider", sa.String(length=120), nullable=False),
        sa.Column("media_info", sa.JSON(), nullable=True),
        sa.Column("validation_errors", sa.JSON(), nullable=False),
        sa.Column("proxy_asset_id", sa.String(length=36), nullable=True),
        sa.Column("waveform_asset_id", sa.String(length=36), nullable=True),
        sa.Column("generation_job_id", sa.String(length=36), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["asset_id"], ["library_assets.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["proxy_asset_id"], ["library_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["waveform_asset_id"], ["library_assets.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["generation_job_id"], ["studio_generation_jobs.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_media_ingest_scope_key"),
    )
    for name, columns in (
        ("ix_studio_media_ingests_workspace_id", ["workspace_id"]),
        ("ix_studio_media_ingests_asset_id", ["asset_id"]),
        ("ix_studio_media_ingests_proxy_asset_id", ["proxy_asset_id"]),
        ("ix_studio_media_ingests_waveform_asset_id", ["waveform_asset_id"]),
        ("ix_studio_media_ingests_generation_job_id", ["generation_job_id"]),
        ("ix_studio_media_ingests_requested_by", ["requested_by"]),
        ("ix_studio_media_ingests_workspace_status", ["workspace_id", "status"]),
    ):
        op.create_index(name, "studio_media_ingests", columns)


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("studio_media_ingests"):
        op.drop_table("studio_media_ingests")
