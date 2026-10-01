"""Add object storage lineage and execution placement policies.

Revision ID: 0015_object_storage
Revises: 0014_media_identity
"""

import sqlalchemy as sa

from alembic import op

revision = "0015_object_storage"
down_revision = "0014_media_identity"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("library_assets")}
    with op.batch_alter_table("library_assets") as batch:
        if "storage_backend" not in columns:
            batch.add_column(
                sa.Column("storage_backend", sa.String(length=32), server_default="local", nullable=False)
            )
        if "media_type" not in columns:
            batch.add_column(sa.Column("media_type", sa.String(length=160), nullable=True))
        if "size_bytes" not in columns:
            batch.add_column(sa.Column("size_bytes", sa.BigInteger(), nullable=True))
        if "checksum_sha256" not in columns:
            batch.add_column(sa.Column("checksum_sha256", sa.String(length=64), nullable=True))
        if "metadata" not in columns:
            batch.add_column(sa.Column("metadata", sa.JSON(), server_default=sa.text("'{}'"), nullable=False))
    indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes("library_assets")}
    if "ix_library_assets_checksum_sha256" not in indexes:
        op.create_index("ix_library_assets_checksum_sha256", "library_assets", ["checksum_sha256"])

    job_columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")}
    with op.batch_alter_table("studio_generation_jobs") as batch:
        if "execution_capability" not in job_columns:
            batch.add_column(
                sa.Column("execution_capability", sa.String(length=32), server_default="control", nullable=False)
            )
        if "queue_name" not in job_columns:
            batch.add_column(sa.Column("queue_name", sa.String(length=80), server_default="studio.cpu", nullable=False))
        if "resource_class" not in job_columns:
            batch.add_column(
                sa.Column("resource_class", sa.String(length=80), server_default="cpu.standard", nullable=False)
            )
        if "hard_time_limit_seconds" not in job_columns:
            batch.add_column(
                sa.Column("hard_time_limit_seconds", sa.Integer(), server_default="300", nullable=False)
            )


def downgrade() -> None:
    job_columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")
    }
    with op.batch_alter_table("studio_generation_jobs") as batch:
        for column in ("hard_time_limit_seconds", "resource_class", "queue_name", "execution_capability"):
            if column in job_columns:
                batch.drop_column(column)

    inspector = sa.inspect(op.get_bind())
    indexes = {index["name"] for index in inspector.get_indexes("library_assets")}
    if "ix_library_assets_checksum_sha256" in indexes:
        op.drop_index("ix_library_assets_checksum_sha256", table_name="library_assets")
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("library_assets")}
    with op.batch_alter_table("library_assets") as batch:
        for column in ("metadata", "checksum_sha256", "size_bytes", "media_type", "storage_backend"):
            if column in columns:
                batch.drop_column(column)
