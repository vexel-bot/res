"""version brand profiles

Revision ID: 0009_brand_versions
Revises: 0008_approval_events
"""

import sqlalchemy as sa

from alembic import op

revision = "0009_brand_versions"
down_revision = "0008_approval_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("brand_profiles")}
    if "versions" not in columns:
        op.add_column(
            "brand_profiles",
            sa.Column("versions", sa.JSON(), server_default=sa.text("'[]'"), nullable=False),
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("brand_profiles")}
    if "versions" in columns:
        op.drop_column("brand_profiles", "versions")
