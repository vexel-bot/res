"""Prevent duplicate Studio documents during concurrent mounts.

Revision ID: 0013_studio_document_idempotency
Revises: 0012_radar_contextual_v2
"""

import sqlalchemy as sa

from alembic import op

revision = "0013_studio_document_idempotency"
down_revision = "0012_radar_contextual_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns("creative_documents")}
    indexes = {index["name"] for index in inspector.get_indexes("creative_documents")}
    constraints = {item["name"] for item in inspector.get_unique_constraints("creative_documents")}
    with op.batch_alter_table("creative_documents") as batch:
        if "studio_creation_key" not in columns:
            batch.add_column(sa.Column("studio_creation_key", sa.String(length=300), nullable=True))
        if "uq_creative_documents_studio_creation_key" not in constraints:
            batch.create_unique_constraint("uq_creative_documents_studio_creation_key", ["studio_creation_key"])
        if "ix_creative_documents_studio_creation_key" not in indexes:
            batch.create_index("ix_creative_documents_studio_creation_key", ["studio_creation_key"])


def downgrade() -> None:
    with op.batch_alter_table("creative_documents") as batch:
        batch.drop_index("ix_creative_documents_studio_creation_key")
        batch.drop_constraint("uq_creative_documents_studio_creation_key", type_="unique")
        batch.drop_column("studio_creation_key")
