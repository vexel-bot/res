"""Add immutable Studio review requests.

Revision ID: 0011_studio_production_rail
Revises: 0010_studio_kernel
"""

import sqlalchemy as sa

from alembic import op

revision = "0011_studio_production_rail"
down_revision = "0010_studio_kernel"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("studio_review_requests"):
        return
    op.create_table(
        "studio_review_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("document_id", sa.String(length=36), nullable=False),
        sa.Column("document_version", sa.Integer(), nullable=False),
        sa.Column("post_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=True),
        sa.Column("decided_by", sa.String(length=36), nullable=True),
        sa.Column("decision_comment", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["document_id"], ["creative_documents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["post_id"], ["posts.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["decided_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_studio_review_requests_workspace_id", "studio_review_requests", ["workspace_id"])
    op.create_index("ix_studio_review_requests_document_id", "studio_review_requests", ["document_id"])
    op.create_index("ix_studio_review_requests_post_id", "studio_review_requests", ["post_id"])
    op.create_index("ix_studio_review_requests_requested_by", "studio_review_requests", ["requested_by"])
    op.create_index("ix_studio_review_requests_decided_by", "studio_review_requests", ["decided_by"])
    op.create_index(
        "ix_studio_reviews_workspace_status", "studio_review_requests", ["workspace_id", "status"]
    )
    op.create_index(
        "ix_studio_reviews_document_requested", "studio_review_requests", ["document_id", "requested_at"]
    )


def downgrade() -> None:
    op.drop_table("studio_review_requests")
