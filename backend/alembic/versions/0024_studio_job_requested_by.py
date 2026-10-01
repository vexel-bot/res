"""Track the actor that requested a Studio generation job.

Revision ID: 0024_job_actor
Revises: 0023_worker_execution
"""

import sqlalchemy as sa

from alembic import op

revision = "0024_job_actor"
down_revision = "0023_worker_execution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_generation_jobs"):
        return
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")
    }
    if "requested_by" not in columns:
        with op.batch_alter_table("studio_generation_jobs") as batch:
            batch.add_column(
                sa.Column(
                    "requested_by",
                    sa.String(length=36),
                    nullable=True,
                )
            )
            batch.create_foreign_key(
                "fk_studio_generation_jobs_requested_by",
                "users",
                ["requested_by"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index("ix_studio_generation_jobs_requested_by", ["requested_by"])


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_generation_jobs"):
        return
    columns = {
        column["name"] for column in sa.inspect(op.get_bind()).get_columns("studio_generation_jobs")
    }
    if "requested_by" in columns:
        with op.batch_alter_table("studio_generation_jobs") as batch:
            batch.drop_index("ix_studio_generation_jobs_requested_by")
            batch.drop_column("requested_by")
