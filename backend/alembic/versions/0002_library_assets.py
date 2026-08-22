"""Add persistent operations metadata and private library assets.

Revision ID: 0002_library_assets
Revises: 0001_initial
"""

import sqlalchemy as sa

from alembic import op

revision = "0002_library_assets"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not inspector.has_table("library_assets"):
        op.create_table(
            "library_assets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("title", sa.String(length=240), nullable=False),
            sa.Column("type", sa.String(length=32), nullable=False),
            sa.Column("tags", sa.JSON(), nullable=False),
            sa.Column("campaign_id", sa.String(length=36), nullable=True),
            sa.Column("content_id", sa.String(length=36), nullable=True),
            sa.Column("url", sa.Text(), nullable=True),
            sa.Column("storage_key", sa.String(length=120), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["campaign_id"], ["campaigns.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["content_id"], ["posts.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("storage_key", name="uq_library_assets_storage_key"),
        )
        op.create_index("ix_library_assets_workspace_id", "library_assets", ["workspace_id"])
        op.create_index("ix_library_assets_campaign_id", "library_assets", ["campaign_id"])
        op.create_index("ix_library_assets_content_id", "library_assets", ["content_id"])
        op.create_index("ix_library_assets_workspace_created", "library_assets", ["workspace_id", "created_at"])

    post_columns = {column["name"] for column in sa.inspect(bind).get_columns("posts")}
    additions = {
        "campaign_id": sa.Column("campaign_id", sa.String(length=36), nullable=True),
        "strategy_id": sa.Column("strategy_id", sa.String(length=36), nullable=True),
        "brain_revision": sa.Column("brain_revision", sa.Integer(), nullable=True),
        "objective": sa.Column("objective", sa.Text(), nullable=True),
        "origin": sa.Column("origin", sa.String(length=32), nullable=True),
        "versions": sa.Column("versions", sa.JSON(), nullable=False, server_default=sa.text("'[]'")),
    }
    for name, column in additions.items():
        if name not in post_columns:
            op.add_column("posts", column)
    if "campaign_id" not in post_columns:
        op.create_foreign_key(
            "fk_posts_campaign_id", "posts", "campaigns", ["campaign_id"], ["id"], ondelete="SET NULL"
        )
        op.create_index("ix_posts_campaign_id", "posts", ["campaign_id"])
    if "strategy_id" not in post_columns:
        op.create_index("ix_posts_strategy_id", "posts", ["strategy_id"])


def downgrade() -> None:
    op.drop_index("ix_posts_strategy_id", table_name="posts")
    op.drop_index("ix_posts_campaign_id", table_name="posts")
    op.drop_constraint("fk_posts_campaign_id", "posts", type_="foreignkey")
    for column in ("versions", "origin", "objective", "brain_revision", "strategy_id", "campaign_id"):
        op.drop_column("posts", column)
    op.drop_table("library_assets")
