"""Add versioned Radar evidence and shadow evaluation persistence.

Revision ID: 0012_radar_contextual_v2
Revises: 0011_studio_production_rail
"""

import sqlalchemy as sa

from alembic import op

revision = "0012_radar_contextual_v2"
down_revision = "0011_studio_production_rail"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    signal_columns = {column["name"] for column in inspector.get_columns("external_signals")}
    with op.batch_alter_table("external_signals") as batch:
        if "schema_version" not in signal_columns:
            batch.add_column(
                sa.Column("schema_version", sa.String(length=32), nullable=False, server_default="radar.signal.v1")
            )
        if "source_type" not in signal_columns:
            batch.add_column(sa.Column("source_type", sa.String(length=32), nullable=False, server_default="external"))
        if "confidence" not in signal_columns:
            batch.add_column(sa.Column("confidence", sa.Float(), nullable=True))
        if "knowledge_type" not in signal_columns:
            batch.add_column(sa.Column("knowledge_type", sa.String(length=32), nullable=False, server_default="fact"))
        if "provider_trace" not in signal_columns:
            batch.add_column(sa.Column("provider_trace", sa.JSON(), nullable=False, server_default=sa.text("'{}'")))

    feedback_columns = {column["name"] for column in inspector.get_columns("feedback_events")}
    with op.batch_alter_table("feedback_events") as batch:
        if "schema_version" not in feedback_columns:
            batch.add_column(
                sa.Column("schema_version", sa.String(length=32), nullable=False, server_default="feedback.v1")
            )
        if "opportunity_score_version" not in feedback_columns:
            batch.add_column(sa.Column("opportunity_score_version", sa.String(length=32), nullable=True))
        if "object_version" not in feedback_columns:
            batch.add_column(sa.Column("object_version", sa.Integer(), nullable=True))

    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("radar_shadow_evaluations"):
        return
    op.create_table(
        "radar_shadow_evaluations",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("signal_id", sa.String(length=36), nullable=False),
        sa.Column("active_opportunity_id", sa.String(length=36), nullable=True),
        sa.Column("baseline_version", sa.String(length=32), nullable=False),
        sa.Column("baseline_score", sa.Float(), nullable=False),
        sa.Column("candidate_version", sa.String(length=32), nullable=False),
        sa.Column("candidate_score", sa.Float(), nullable=True),
        sa.Column("brand_revision", sa.Integer(), nullable=False),
        sa.Column("candidate", sa.JSON(), nullable=False),
        sa.Column("comparison", sa.JSON(), nullable=False),
        sa.Column("provider_trace", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["active_opportunity_id"], ["opportunities.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["signal_id"], ["external_signals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_radar_shadow_evaluations_workspace_id", "radar_shadow_evaluations", ["workspace_id"])
    op.create_index("ix_radar_shadow_evaluations_signal_id", "radar_shadow_evaluations", ["signal_id"])
    op.create_index(
        "ix_radar_shadow_evaluations_active_opportunity_id",
        "radar_shadow_evaluations",
        ["active_opportunity_id"],
    )
    op.create_index("ix_radar_shadow_workspace_created", "radar_shadow_evaluations", ["workspace_id", "created_at"])
    op.create_index("ix_radar_shadow_signal_candidate", "radar_shadow_evaluations", ["signal_id", "candidate_version"])


def downgrade() -> None:
    op.drop_table("radar_shadow_evaluations")
    with op.batch_alter_table("feedback_events") as batch:
        batch.drop_column("object_version")
        batch.drop_column("opportunity_score_version")
        batch.drop_column("schema_version")
    with op.batch_alter_table("external_signals") as batch:
        batch.drop_column("provider_trace")
        batch.drop_column("knowledge_type")
        batch.drop_column("confidence")
        batch.drop_column("source_type")
        batch.drop_column("schema_version")
