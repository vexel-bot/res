"""Add guarded physical identity deletion and asset tombstones.

Revision ID: 0020_identity_delete_exec
Revises: 0019_transcript_edits
"""

import sqlalchemy as sa

from alembic import op

revision = "0020_identity_delete_exec"
down_revision = "0019_transcript_edits"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    asset_columns = {column["name"] for column in inspector.get_columns("library_assets")}
    with op.batch_alter_table("library_assets") as batch:
        if "lifecycle_status" not in asset_columns:
            batch.add_column(
                sa.Column("lifecycle_status", sa.String(length=32), server_default="active", nullable=False)
            )
        if "legal_hold" not in asset_columns:
            batch.add_column(sa.Column("legal_hold", sa.Boolean(), server_default=sa.false(), nullable=False))
        if "legal_hold_reason" not in asset_columns:
            batch.add_column(sa.Column("legal_hold_reason", sa.Text(), nullable=True))
        if "deleted_at" not in asset_columns:
            batch.add_column(sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
        if "deletion_receipt" not in asset_columns:
            batch.add_column(
                sa.Column("deletion_receipt", sa.JSON(), server_default=sa.text("'{}'"), nullable=False)
            )
    asset_indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("library_assets")}
    if "ix_library_assets_lifecycle_status" not in asset_indexes:
        op.create_index("ix_library_assets_lifecycle_status", "library_assets", ["lifecycle_status"])

    deletion_columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_identity_deletion_requests")
    }
    with op.batch_alter_table("studio_identity_deletion_requests") as batch:
        if "queued_at" not in deletion_columns:
            batch.add_column(sa.Column("queued_at", sa.DateTime(timezone=True), nullable=True))
        if "started_at" not in deletion_columns:
            batch.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        if "attempt_count" not in deletion_columns:
            batch.add_column(sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False))
        if "execution_receipt" not in deletion_columns:
            batch.add_column(
                sa.Column("execution_receipt", sa.JSON(), server_default=sa.text("'{}'"), nullable=False)
            )


def downgrade() -> None:
    deletion_columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_identity_deletion_requests")
    }
    with op.batch_alter_table("studio_identity_deletion_requests") as batch:
        for column in ("execution_receipt", "attempt_count", "started_at", "queued_at"):
            if column in deletion_columns:
                batch.drop_column(column)

    inspector = sa.inspect(op.get_bind())
    asset_indexes = {index["name"] for index in inspector.get_indexes("library_assets")}
    if "ix_library_assets_lifecycle_status" in asset_indexes:
        op.drop_index("ix_library_assets_lifecycle_status", table_name="library_assets")
    asset_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("library_assets")}
    with op.batch_alter_table("library_assets") as batch:
        for column in (
            "deletion_receipt",
            "deleted_at",
            "legal_hold_reason",
            "legal_hold",
            "lifecycle_status",
        ):
            if column in asset_columns:
                batch.drop_column(column)
