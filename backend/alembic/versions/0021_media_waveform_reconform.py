"""Add persisted proxy reconform time map.

Revision ID: 0021_media_waveform
Revises: 0020_identity_delete_exec
"""

import sqlalchemy as sa

from alembic import op

revision = "0021_media_waveform"
down_revision = "0020_identity_delete_exec"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_media_ingests"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_media_ingests")
    }
    if "proxy_time_map" not in columns:
        with op.batch_alter_table("studio_media_ingests") as batch:
            batch.add_column(
                sa.Column(
                    "proxy_time_map",
                    sa.JSON(),
                    nullable=True,
                )
            )


def downgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_media_ingests"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_media_ingests")
    }
    if "proxy_time_map" in columns:
        with op.batch_alter_table("studio_media_ingests") as batch:
            batch.drop_column("proxy_time_map")
