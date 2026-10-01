"""Add governed evaluation and activation for identity and voice versions.

Revision ID: 0016_identity_gate
Revises: 0015_object_storage
"""

import sqlalchemy as sa

from alembic import op

revision = "0016_identity_gate"
down_revision = "0015_object_storage"
branch_labels = None
depends_on = None


def _add_review_columns(table_name: str) -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}
    with op.batch_alter_table(table_name) as batch:
        if "reviewed_by" not in columns:
            batch.add_column(sa.Column("reviewed_by", sa.String(length=36), nullable=True))
            batch.create_foreign_key(
                f"fk_{table_name}_reviewed_by",
                "users",
                ["reviewed_by"],
                ["id"],
                ondelete="SET NULL",
            )
            batch.create_index(f"ix_{table_name}_reviewed_by", ["reviewed_by"])
        if "reviewed_at" not in columns:
            batch.add_column(sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True))
        if "review_comment" not in columns:
            batch.add_column(sa.Column("review_comment", sa.Text(), nullable=True))


def upgrade() -> None:
    _add_review_columns("studio_identity_versions")
    _add_review_columns("studio_voice_versions")
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("studio_identity_evaluations"):
        op.create_table(
            "studio_identity_evaluations",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("target_type", sa.String(length=32), nullable=False),
            sa.Column("identity_version_id", sa.String(length=36), nullable=True),
            sa.Column("voice_version_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("evaluator_kind", sa.String(length=32), nullable=False),
            sa.Column("quality_metrics", sa.JSON(), nullable=False),
            sa.Column("checks", sa.JSON(), nullable=False),
            sa.Column("preview_asset_ids", sa.JSON(), nullable=False),
            sa.Column("provider_registration_id", sa.String(length=36), nullable=True),
            sa.Column("model_registration_id", sa.String(length=36), nullable=True),
            sa.Column("evaluated_by", sa.String(length=36), nullable=False),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.CheckConstraint(
                "(identity_version_id IS NOT NULL AND voice_version_id IS NULL) OR "
                "(identity_version_id IS NULL AND voice_version_id IS NOT NULL)",
                name="ck_studio_identity_evaluation_one_target",
            ),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["identity_version_id"], ["studio_identity_versions.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["voice_version_id"], ["studio_voice_versions.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["provider_registration_id"], ["studio_provider_registrations.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["model_registration_id"], ["studio_model_registrations.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(["evaluated_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            "ix_studio_identity_evaluations_workspace_id", "studio_identity_evaluations", ["workspace_id"]
        )
        op.create_index(
            "ix_studio_identity_evaluations_identity_version_id",
            "studio_identity_evaluations",
            ["identity_version_id"],
        )
        op.create_index(
            "ix_studio_identity_evaluations_voice_version_id",
            "studio_identity_evaluations",
            ["voice_version_id"],
        )
        op.create_index(
            "ix_studio_identity_evaluations_provider_registration_id",
            "studio_identity_evaluations",
            ["provider_registration_id"],
        )
        op.create_index(
            "ix_studio_identity_evaluations_model_registration_id",
            "studio_identity_evaluations",
            ["model_registration_id"],
        )
        op.create_index(
            "ix_studio_identity_evaluations_evaluated_by",
            "studio_identity_evaluations",
            ["evaluated_by"],
        )
        op.create_index(
            "ix_studio_identity_evaluations_workspace_status",
            "studio_identity_evaluations",
            ["workspace_id", "status"],
        )


def _drop_review_columns(table_name: str) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    is_sqlite = op.get_bind().dialect.name == "sqlite"
    review_index = f"ix_{table_name}_reviewed_by"
    if review_index in indexes:
        op.drop_index(review_index, table_name=table_name)
    with op.batch_alter_table(table_name) as batch:
        if "review_comment" in columns:
            batch.drop_column("review_comment")
        if "reviewed_at" in columns:
            batch.drop_column("reviewed_at")
        if "reviewed_by" in columns:
            if not is_sqlite:
                batch.drop_constraint(f"fk_{table_name}_reviewed_by", type_="foreignkey")
            batch.drop_column("reviewed_by")


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("studio_identity_evaluations"):
        op.drop_table("studio_identity_evaluations")
    _drop_review_columns("studio_voice_versions")
    _drop_review_columns("studio_identity_versions")
