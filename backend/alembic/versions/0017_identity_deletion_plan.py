"""Add idempotent identity deletion plans.

Revision ID: 0017_identity_delete
Revises: 0016_identity_gate
"""

import sqlalchemy as sa

from alembic import op

revision = "0017_identity_delete"
down_revision = "0016_identity_gate"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("studio_identity_deletion_requests"):
        return
    op.create_table(
        "studio_identity_deletion_requests",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("target_type", sa.String(length=32), nullable=False),
        sa.Column("identity_profile_id", sa.String(length=36), nullable=True),
        sa.Column("voice_profile_id", sa.String(length=36), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("delete_source_samples", sa.Boolean(), nullable=False),
        sa.Column("deletion_plan", sa.JSON(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=False),
        sa.Column("requested_by", sa.String(length=36), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "(identity_profile_id IS NOT NULL AND voice_profile_id IS NULL) OR "
            "(identity_profile_id IS NULL AND voice_profile_id IS NOT NULL)",
            name="ck_studio_identity_deletion_one_target",
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["identity_profile_id"], ["studio_identity_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["voice_profile_id"], ["studio_voice_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_identity_deletion_scope_key"),
    )
    for name, columns in (
        ("ix_studio_identity_deletion_requests_workspace_id", ["workspace_id"]),
        ("ix_studio_identity_deletion_requests_identity_profile_id", ["identity_profile_id"]),
        ("ix_studio_identity_deletion_requests_voice_profile_id", ["voice_profile_id"]),
        ("ix_studio_identity_deletion_requests_requested_by", ["requested_by"]),
        ("ix_studio_identity_deletion_workspace_status", ["workspace_id", "status"]),
    ):
        op.create_index(name, "studio_identity_deletion_requests", columns)


def downgrade() -> None:
    if sa.inspect(op.get_bind()).has_table("studio_identity_deletion_requests"):
        op.drop_table("studio_identity_deletion_requests")
