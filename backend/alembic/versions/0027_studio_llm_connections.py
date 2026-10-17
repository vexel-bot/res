"""Workspace LLM endpoints with credentials encrypted outside public metadata."""

import sqlalchemy as sa

from alembic import op

revision = "0027_studio_llm_connections"
down_revision = "0026_studio_motion_graphs"
branch_labels = None
depends_on = None


def upgrade():
    if sa.inspect(op.get_bind()).has_table("studio_llm_connections"):
        return
    op.create_table(
        "studio_llm_connections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("workspace_id", sa.String(36), sa.ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("provider", sa.String(80), nullable=False),
        sa.Column("config", sa.JSON(), nullable=False),
        sa.Column("credential_ciphertext", sa.Text(), nullable=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_studio_llm_connections_workspace_id", "studio_llm_connections", ["workspace_id"])


def downgrade():
    op.drop_table("studio_llm_connections")
