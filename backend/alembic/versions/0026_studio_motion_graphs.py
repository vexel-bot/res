"""Persist versioned, tenant-scoped Studio motion graphs.

Revision ID: 0026_studio_motion_graphs
Revises: 0025_transcript_provenance
"""

import sqlalchemy as sa

from alembic import op

revision = "0026_studio_motion_graphs"
down_revision = "0025_transcript_provenance"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("studio_motion_graphs"):
        return
    op.create_table(
        "studio_motion_graphs",
        sa.Column("id", sa.String(length=160), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_revision", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="suggested"),
        sa.Column("storage_revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("graph_digest_sha256", sa.String(length=64), nullable=False),
        sa.Column("graph", sa.JSON(), nullable=False),
        sa.Column("evaluation", sa.JSON(), nullable=True),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("payload_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("updated_by", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["document_id"], ["creative_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "workspace_id",
            "idempotency_key",
            name="uq_studio_motion_graph_scope_key",
        ),
    )
    op.create_index(
        "ix_studio_motion_graphs_workspace_document",
        "studio_motion_graphs",
        ["workspace_id", "document_id"],
    )
    op.create_index(
        "ix_studio_motion_graphs_workspace_status",
        "studio_motion_graphs",
        ["workspace_id", "status"],
    )
    op.create_index(
        op.f("ix_studio_motion_graphs_workspace_id"),
        "studio_motion_graphs",
        ["workspace_id"],
    )
    op.create_index(
        op.f("ix_studio_motion_graphs_document_id"),
        "studio_motion_graphs",
        ["document_id"],
    )
    op.create_index(
        op.f("ix_studio_motion_graphs_created_by"),
        "studio_motion_graphs",
        ["created_by"],
    )
    op.create_index(
        op.f("ix_studio_motion_graphs_updated_by"),
        "studio_motion_graphs",
        ["updated_by"],
    )


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("studio_motion_graphs"):
        op.drop_table("studio_motion_graphs")
