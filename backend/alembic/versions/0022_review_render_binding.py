"""Bind Studio video reviews to an immutable rendered artifact.

Revision ID: 0022_review_render
Revises: 0021_media_waveform
"""

import sqlalchemy as sa

from alembic import op

revision = "0022_review_render"
down_revision = "0021_media_waveform"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not sa.inspect(op.get_bind()).has_table("studio_review_requests"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_review_requests")
    }
    with op.batch_alter_table("studio_review_requests") as batch:
        if "render_job_id" not in columns:
            batch.add_column(sa.Column("render_job_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_studio_review_render_job",
                "studio_generation_jobs",
                ["render_job_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index("ix_studio_review_requests_render_job_id", ["render_job_id"])
        if "render_asset_id" not in columns:
            batch.add_column(sa.Column("render_asset_id", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                "fk_studio_review_render_asset",
                "library_assets",
                ["render_asset_id"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index("ix_studio_review_requests_render_asset_id", ["render_asset_id"])
        if "render_checksum_sha256" not in columns:
            batch.add_column(
                sa.Column("render_checksum_sha256", sa.String(length=64), nullable=True)
            )
            batch.create_index(
                "ix_studio_review_requests_render_checksum_sha256",
                ["render_checksum_sha256"],
            )


def downgrade() -> None:
    bind = op.get_bind()
    if not sa.inspect(bind).has_table("studio_review_requests"):
        return
    columns = {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns("studio_review_requests")
    }
    batch_options = {}
    render_asset_fk = "fk_studio_review_render_asset"
    render_job_fk = "fk_studio_review_render_job"
    if bind.dialect.name == "sqlite":
        # SQLite does not persist FK names. A naming convention lets Alembic
        # address the reflected constraints during batch table recreation.
        batch_options["naming_convention"] = {
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s"
        }
        render_asset_fk = (
            "fk_studio_review_requests_render_asset_id_library_assets"
        )
        render_job_fk = (
            "fk_studio_review_requests_render_job_id_studio_generation_jobs"
        )
    with op.batch_alter_table("studio_review_requests", **batch_options) as batch:
        if "render_checksum_sha256" in columns:
            batch.drop_index("ix_studio_review_requests_render_checksum_sha256")
            batch.drop_column("render_checksum_sha256")
        if "render_asset_id" in columns:
            batch.drop_index("ix_studio_review_requests_render_asset_id")
            batch.drop_constraint(render_asset_fk, type_="foreignkey")
            batch.drop_column("render_asset_id")
        if "render_job_id" in columns:
            batch.drop_index("ix_studio_review_requests_render_job_id")
            batch.drop_constraint(render_job_fk, type_="foreignkey")
            batch.drop_column("render_job_id")
