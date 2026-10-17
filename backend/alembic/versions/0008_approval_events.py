"""persistent approval comments and history

Revision ID: 0008_approval_events
Revises: 0007_workspace_features
"""

import sqlalchemy as sa

from alembic import op

revision = "0008_approval_events"
down_revision = "0007_workspace_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("approval_events"):
        return
    op.create_table(
        "approval_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("post_id", sa.String(length=36), nullable=False),
        sa.Column("actor_id", sa.String(length=36), nullable=True),
        sa.Column("actor_name", sa.String(length=120), nullable=False),
        sa.Column("event_type", sa.String(length=24), nullable=False),
        sa.Column("action", sa.String(length=48), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_approval_events_workspace_id", "approval_events", ["workspace_id"])
    op.create_index("ix_approval_events_post_id", "approval_events", ["post_id"])
    op.create_index("ix_approval_events_actor_id", "approval_events", ["actor_id"])
    op.create_index("ix_approval_events_created_at", "approval_events", ["created_at"])
    op.create_index(
        "ix_approval_events_workspace_post_created",
        "approval_events",
        ["workspace_id", "post_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("approval_events")
