"""Add provider-neutral Studio kernel persistence.

Revision ID: 0010_studio_kernel
Revises: 0009_brand_versions
"""

import sqlalchemy as sa

from alembic import op

revision = "0010_studio_kernel"
down_revision = "0009_brand_versions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    creative_columns = {column["name"] for column in inspector.get_columns("creative_documents")}
    with op.batch_alter_table("creative_documents") as batch:
        if "schema_version" not in creative_columns:
            batch.add_column(
                sa.Column("schema_version", sa.String(length=64), nullable=False, server_default="creative-v1")
            )
        if "canonical_document" not in creative_columns:
            batch.add_column(sa.Column("canonical_document", sa.JSON(), nullable=True))
        if "revision" not in creative_columns:
            batch.add_column(sa.Column("revision", sa.Integer(), nullable=False, server_default="1"))
        if "correlation_id" not in creative_columns:
            batch.add_column(sa.Column("correlation_id", sa.String(length=128), nullable=True))
            batch.create_index("ix_creative_documents_correlation_id", ["correlation_id"])
        if "created_by" not in creative_columns:
            batch.add_column(sa.Column("created_by", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_creative_documents_created_by", "users", ["created_by"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_creative_documents_created_by", ["created_by"])

    if not inspector.has_table("studio_generation_jobs"):
        op.create_table(
            "studio_generation_jobs",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=True),
            sa.Column("job_type", sa.String(length=80), nullable=False),
            sa.Column("provider", sa.String(length=120), nullable=False),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("payload_hash", sa.String(length=64), nullable=False),
            sa.Column("correlation_id", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("progress", sa.Integer(), nullable=False),
            sa.Column("attempts", sa.Integer(), nullable=False),
            sa.Column("max_attempts", sa.Integer(), nullable=False),
            sa.Column("request", sa.JSON(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=True),
            sa.Column("error_code", sa.String(length=120), nullable=True),
            sa.Column("error_message", sa.Text(), nullable=True),
            sa.Column("cancel_reason", sa.Text(), nullable=True),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["creative_documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workspace_id", "job_type", "idempotency_key", name="uq_studio_job_scope_key"),
        )
        op.create_index("ix_studio_generation_jobs_workspace_id", "studio_generation_jobs", ["workspace_id"])
        op.create_index("ix_studio_generation_jobs_document_id", "studio_generation_jobs", ["document_id"])
        op.create_index("ix_studio_generation_jobs_correlation_id", "studio_generation_jobs", ["correlation_id"])
        op.create_index("ix_studio_jobs_workspace_status", "studio_generation_jobs", ["workspace_id", "status"])

    if not inspector.has_table("studio_domain_events"):
        op.create_table(
            "studio_domain_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("event_type", sa.String(length=120), nullable=False),
            sa.Column("schema_version", sa.String(length=64), nullable=False),
            sa.Column("aggregate_type", sa.String(length=80), nullable=False),
            sa.Column("aggregate_id", sa.String(length=120), nullable=False),
            sa.Column("correlation_id", sa.String(length=128), nullable=False),
            sa.Column("actor_id", sa.String(length=36), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_studio_domain_events_workspace_id", "studio_domain_events", ["workspace_id"])
        op.create_index("ix_studio_domain_events_event_type", "studio_domain_events", ["event_type"])
        op.create_index("ix_studio_domain_events_actor_id", "studio_domain_events", ["actor_id"])
        op.create_index("ix_studio_domain_events_correlation_id", "studio_domain_events", ["correlation_id"])
        op.create_index("ix_studio_domain_events_occurred_at", "studio_domain_events", ["occurred_at"])
        op.create_index("ix_studio_events_workspace_occurred", "studio_domain_events", ["workspace_id", "occurred_at"])
        op.create_index("ix_studio_events_aggregate", "studio_domain_events", ["aggregate_type", "aggregate_id"])


def downgrade() -> None:
    op.drop_table("studio_domain_events")
    op.drop_table("studio_generation_jobs")
    with op.batch_alter_table("creative_documents") as batch:
        batch.drop_index("ix_creative_documents_created_by")
        batch.drop_index("ix_creative_documents_correlation_id")
        batch.drop_column("created_by")
        batch.drop_column("correlation_id")
        batch.drop_column("revision")
        batch.drop_column("canonical_document")
        batch.drop_column("schema_version")
