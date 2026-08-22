"""Add campaign history, scoped feedback links and metric snapshots.

Revision ID: 0006_history_learning
Revises: 0005_creative_documents
"""

import sqlalchemy as sa

from alembic import op

revision = "0006_history_learning"
down_revision = "0005_creative_documents"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    campaign_columns = {column["name"] for column in inspector.get_columns("campaigns")}
    with op.batch_alter_table("campaigns") as batch:
        if "versions" not in campaign_columns:
            batch.add_column(sa.Column("versions", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))
        if "decisions" not in campaign_columns:
            batch.add_column(sa.Column("decisions", sa.JSON(), server_default=sa.text("'[]'"), nullable=False))

    feedback_columns = {column["name"] for column in inspector.get_columns("feedback_events")}
    feedback_indexes = {index["name"] for index in inspector.get_indexes("feedback_events")}
    with op.batch_alter_table("feedback_events") as batch:
        if "campaign_id" not in feedback_columns:
            batch.add_column(sa.Column("campaign_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_feedback_events_campaign_id", "campaigns", ["campaign_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_feedback_events_campaign_id", ["campaign_id"])
        if "content_id" not in feedback_columns:
            batch.add_column(sa.Column("content_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_feedback_events_content_id", "posts", ["content_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_feedback_events_content_id", ["content_id"])
        if "creative_document_id" not in feedback_columns:
            batch.add_column(sa.Column("creative_document_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_feedback_events_creative_document_id",
                "creative_documents",
                ["creative_document_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index("ix_feedback_events_creative_document_id", ["creative_document_id"])
        if "user_id" not in feedback_columns:
            batch.add_column(sa.Column("user_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key("fk_feedback_events_user_id", "users", ["user_id"], ["id"], ondelete="SET NULL")
            batch.create_index("ix_feedback_events_user_id", ["user_id"])
        if "ix_feedback_events_workspace_type_occurred" not in feedback_indexes:
            batch.create_index(
                "ix_feedback_events_workspace_type_occurred", ["workspace_id", "event_type", "occurred_at"]
            )

    if not inspector.has_table("post_metric_snapshots"):
        op.create_table(
            "post_metric_snapshots",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("post_id", sa.String(length=36), nullable=False),
            sa.Column("recorded_by", sa.String(length=36), nullable=True),
            sa.Column("source", sa.String(length=32), nullable=False),
            sa.Column("metrics", sa.JSON(), nullable=False),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["recorded_by"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_post_metric_snapshots_workspace_id", "post_metric_snapshots", ["workspace_id"])
        op.create_index("ix_post_metric_snapshots_post_id", "post_metric_snapshots", ["post_id"])
        op.create_index("ix_post_metric_snapshots_recorded_by", "post_metric_snapshots", ["recorded_by"])
        op.create_index("ix_post_metric_snapshots_observed_at", "post_metric_snapshots", ["observed_at"])
        op.create_index(
            "ix_post_metric_snapshots_workspace_observed",
            "post_metric_snapshots",
            ["workspace_id", "observed_at"],
        )


def downgrade() -> None:
    op.drop_table("post_metric_snapshots")
    with op.batch_alter_table("feedback_events") as batch:
        batch.drop_index("ix_feedback_events_workspace_type_occurred")
        for column in ("user_id", "creative_document_id", "content_id", "campaign_id"):
            batch.drop_index(f"ix_feedback_events_{column}")
            batch.drop_constraint(f"fk_feedback_events_{column}", type_="foreignkey")
            batch.drop_column(column)
    with op.batch_alter_table("campaigns") as batch:
        batch.drop_column("decisions")
        batch.drop_column("versions")
