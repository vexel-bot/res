"""Persist automatic transcript source and provenance metadata.

Revision ID: 0025_transcript_provenance
Revises: 0024_job_actor
"""

import sqlalchemy as sa

from alembic import op

revision = "0025_transcript_provenance"
down_revision = "0024_job_actor"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_transcripts"):
        return
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_transcripts")
    }
    with op.batch_alter_table("studio_transcripts") as batch:
        if "source_checksum_sha256" not in columns:
            batch.add_column(sa.Column("source_checksum_sha256", sa.String(length=64), nullable=True))
        if "provenance" not in columns:
            batch.add_column(sa.Column("provenance", sa.JSON(), nullable=True))
        if "metrics" not in columns:
            batch.add_column(
                sa.Column("metrics", sa.JSON(), nullable=False, server_default=sa.text("'{}'"))
            )


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_transcripts"):
        return
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_transcripts")
    }
    with op.batch_alter_table("studio_transcripts") as batch:
        if "metrics" in columns:
            batch.drop_column("metrics")
        if "provenance" in columns:
            batch.drop_column("provenance")
        if "source_checksum_sha256" in columns:
            batch.drop_column("source_checksum_sha256")
