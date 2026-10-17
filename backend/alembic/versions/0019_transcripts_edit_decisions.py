"""Add versioned transcripts and edit decision sets.

Revision ID: 0019_transcript_edits
Revises: 0018_media_ingest
"""

import sqlalchemy as sa

from alembic import op

revision = "0019_transcript_edits"
down_revision = "0018_media_ingest"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("studio_transcripts"):
        op.create_table(
            "studio_transcripts",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("media_ingest_id", sa.String(length=36), nullable=False),
            sa.Column("asset_id", sa.String(length=36), nullable=False),
            sa.Column("locale", sa.String(length=32), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("provider", sa.String(length=120), nullable=False),
            sa.Column("provider_version", sa.String(length=240), nullable=True),
            sa.Column("document", sa.JSON(), nullable=False),
            sa.Column("versions", sa.JSON(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=False),
            sa.Column("updated_by", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["media_ingest_id"], ["studio_media_ingests.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["asset_id"], ["library_assets.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workspace_id", "idempotency_key", name="uq_studio_transcript_scope_key"),
        )
        for name, columns in (
            ("ix_studio_transcripts_workspace_id", ["workspace_id"]),
            ("ix_studio_transcripts_media_ingest_id", ["media_ingest_id"]),
            ("ix_studio_transcripts_asset_id", ["asset_id"]),
            ("ix_studio_transcripts_created_by", ["created_by"]),
            ("ix_studio_transcripts_updated_by", ["updated_by"]),
            ("ix_studio_transcripts_workspace_status", ["workspace_id", "status"]),
        ):
            op.create_index(name, "studio_transcripts", columns)

    inspector = sa.inspect(op.get_bind())
    if not inspector.has_table("studio_edit_decision_sets"):
        op.create_table(
            "studio_edit_decision_sets",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("media_ingest_id", sa.String(length=36), nullable=False),
            sa.Column("transcript_id", sa.String(length=36), nullable=True),
            sa.Column("document_id", sa.String(length=36), nullable=True),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("revision", sa.Integer(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.Column("decisions", sa.JSON(), nullable=False),
            sa.Column("versions", sa.JSON(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=160), nullable=False),
            sa.Column("created_by", sa.String(length=36), nullable=False),
            sa.Column("updated_by", sa.String(length=36), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(
                ["media_ingest_id"], ["studio_media_ingests.id"], ondelete="CASCADE"
            ),
            sa.ForeignKeyConstraint(["transcript_id"], ["studio_transcripts.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["document_id"], ["creative_documents.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
            sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint(
                "workspace_id", "idempotency_key", name="uq_studio_edit_decision_scope_key"
            ),
        )
        for name, columns in (
            ("ix_studio_edit_decision_sets_workspace_id", ["workspace_id"]),
            ("ix_studio_edit_decision_sets_media_ingest_id", ["media_ingest_id"]),
            ("ix_studio_edit_decision_sets_transcript_id", ["transcript_id"]),
            ("ix_studio_edit_decision_sets_document_id", ["document_id"]),
            ("ix_studio_edit_decision_sets_created_by", ["created_by"]),
            ("ix_studio_edit_decision_sets_updated_by", ["updated_by"]),
            ("ix_studio_edit_decisions_workspace_status", ["workspace_id", "status"]),
        ):
            op.create_index(name, "studio_edit_decision_sets", columns)


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("studio_edit_decision_sets"):
        op.drop_table("studio_edit_decision_sets")
    if sa.inspect(op.get_bind()).has_table("studio_transcripts"):
        op.drop_table("studio_transcripts")
