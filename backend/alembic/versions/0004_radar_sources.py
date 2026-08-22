"""Add scheduled Radar RSS sources and tenant-aware signal deduplication.

Revision ID: 0004_radar_sources
Revises: 0003_knowledge_search
"""

import sqlalchemy as sa

from alembic import op

revision = "0004_radar_sources"
down_revision = "0003_knowledge_search"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    signal_constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("external_signals")}
    if "uq_signal_source_hash" in signal_constraints:
        op.drop_constraint("uq_signal_source_hash", "external_signals", type_="unique")
    if "uq_signal_workspace_source_hash" not in signal_constraints:
        op.create_unique_constraint(
            "uq_signal_workspace_source_hash",
            "external_signals",
            ["workspace_id", "source", "content_hash"],
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("radar_sources"):
        op.create_table(
            "radar_sources",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("name", sa.String(length=120), nullable=False),
            sa.Column("connector_type", sa.String(length=32), nullable=False),
            sa.Column("feed_url", sa.Text(), nullable=False),
            sa.Column("region", sa.String(length=32), nullable=False),
            sa.Column("language", sa.String(length=16), nullable=False),
            sa.Column("category", sa.String(length=80), nullable=False),
            sa.Column("is_active", sa.Boolean(), nullable=False),
            sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("last_status", sa.String(length=32), nullable=False),
            sa.Column("last_error", sa.Text(), nullable=True),
            sa.Column("last_item_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workspace_id", "feed_url", name="uq_radar_source_workspace_feed"),
        )
        op.create_index("ix_radar_sources_workspace_id", "radar_sources", ["workspace_id"])
        op.create_index("ix_radar_sources_workspace_active", "radar_sources", ["workspace_id", "is_active"])


def downgrade() -> None:
    op.drop_table("radar_sources")
    op.drop_constraint("uq_signal_workspace_source_hash", "external_signals", type_="unique")
    op.create_unique_constraint("uq_signal_source_hash", "external_signals", ["source", "content_hash"])
