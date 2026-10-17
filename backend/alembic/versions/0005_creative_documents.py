"""Add editable, versioned creative documents.

Revision ID: 0005_creative_documents
Revises: 0004_radar_sources
"""

import sqlalchemy as sa

from alembic import op

revision = "0005_creative_documents"
down_revision = "0004_radar_sources"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("creative_documents"):
        return
    op.create_table(
        "creative_documents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("campaign_id", sa.String(length=36), nullable=True),
        sa.Column("post_id", sa.String(length=36), nullable=True),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("title", sa.String(length=240), nullable=False),
        sa.Column("document", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("versions", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_creative_documents_workspace_id", "creative_documents", ["workspace_id"])
    op.create_index("ix_creative_documents_campaign_id", "creative_documents", ["campaign_id"])
    op.create_index("ix_creative_documents_post_id", "creative_documents", ["post_id"])
    op.create_index("ix_creative_documents_kind", "creative_documents", ["kind"])
    op.create_index("ix_creative_documents_workspace_updated", "creative_documents", ["workspace_id", "updated_at"])


def downgrade() -> None:
    op.drop_table("creative_documents")
