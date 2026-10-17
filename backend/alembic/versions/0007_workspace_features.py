"""workspace features and audit log

Revision ID: 0007_workspace_features
Revises: 0006_history_learning
"""

import sqlalchemy as sa

from alembic import op

revision = "0007_workspace_features"
down_revision = "0006_history_learning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("workspace_resources"):
        op.create_table(
            "workspace_resources",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("kind", sa.String(length=48), nullable=False),
            sa.Column("resource_key", sa.String(length=120), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workspace_id", "kind", "resource_key", name="uq_workspace_resource_kind_key"),
        )
        op.create_index("ix_workspace_resources_workspace_id", "workspace_resources", ["workspace_id"])
        op.create_index("ix_workspace_resources_created_by", "workspace_resources", ["created_by"])
        op.create_index("ix_workspace_resources_workspace_kind", "workspace_resources", ["workspace_id", "kind"])
    if not inspector.has_table("audit_events"):
        op.create_table(
            "audit_events",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("actor_id", sa.String(length=36), nullable=True),
            sa.Column("actor_name", sa.String(length=120), nullable=False),
            sa.Column("action", sa.String(length=80), nullable=False),
            sa.Column("resource", sa.String(length=80), nullable=False),
            sa.Column("detail", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"])
        op.create_index("ix_audit_events_actor_id", "audit_events", ["actor_id"])
        op.create_index("ix_audit_events_created_at", "audit_events", ["created_at"])
        op.create_index("ix_audit_events_workspace_created", "audit_events", ["workspace_id", "created_at"])


def downgrade() -> None:
    op.drop_table("audit_events")
    op.drop_table("workspace_resources")
