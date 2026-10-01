"""Persist the runtime attestation for each Studio job execution.

Revision ID: 0023_worker_execution
Revises: 0022_review_render
"""

import sqlalchemy as sa

from alembic import op

revision = "0023_worker_execution"
down_revision = "0022_review_render"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_generation_jobs"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")
    }
    if "worker_execution_context" not in columns:
        with op.batch_alter_table("studio_generation_jobs") as batch:
            batch.add_column(sa.Column("worker_execution_context", sa.JSON(), nullable=True))


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_generation_jobs"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")
    }
    if "worker_execution_context" in columns:
        with op.batch_alter_table("studio_generation_jobs") as batch:
            batch.drop_column("worker_execution_context")
