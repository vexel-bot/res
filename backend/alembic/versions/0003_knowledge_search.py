"""Add workspace knowledge documents and hybrid search indexes.

Revision ID: 0003_knowledge_search
Revises: 0002_library_assets
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import VECTOR
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "0003_knowledge_search"
down_revision = "0002_library_assets"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if bind.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    if not inspector.has_table("knowledge_documents"):
        op.create_table(
            "knowledge_documents",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("asset_id", sa.String(length=36), nullable=True),
            sa.Column("title", sa.String(length=240), nullable=False),
            sa.Column("source_type", sa.String(length=32), nullable=False),
            sa.Column("source_url", sa.Text(), nullable=True),
            sa.Column("language", sa.String(length=16), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=False),
            sa.Column("content_hash", sa.String(length=64), nullable=False),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column("embedding_status", sa.String(length=32), nullable=False),
            sa.Column("embedding_model", sa.String(length=160), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["asset_id"], ["library_assets.id"], ondelete="SET NULL"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("workspace_id", "content_hash", name="uq_knowledge_document_workspace_hash"),
        )
        op.create_index("ix_knowledge_documents_workspace_id", "knowledge_documents", ["workspace_id"])
        op.create_index("ix_knowledge_documents_asset_id", "knowledge_documents", ["asset_id"])
        op.create_index(
            "ix_knowledge_documents_workspace_created",
            "knowledge_documents",
            ["workspace_id", "created_at"],
        )

    inspector = sa.inspect(bind)
    if not inspector.has_table("knowledge_chunks"):
        search_vector_type = postgresql.TSVECTOR() if bind.dialect.name == "postgresql" else sa.Text()
        search_vector = sa.Column("search_vector", search_vector_type, nullable=True)
        if bind.dialect.name == "postgresql":
            search_vector = sa.Column(
                "search_vector",
                search_vector_type,
                sa.Computed("to_tsvector('simple', coalesce(content, ''))", persisted=True),
                nullable=True,
            )
        embedding_type = VECTOR(1536) if bind.dialect.name == "postgresql" else sa.JSON()
        op.create_table(
            "knowledge_chunks",
            sa.Column("id", sa.String(length=36), nullable=False),
            sa.Column("document_id", sa.String(length=36), nullable=False),
            sa.Column("workspace_id", sa.String(length=36), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("char_start", sa.Integer(), nullable=False),
            sa.Column("char_end", sa.Integer(), nullable=False),
            sa.Column("citation", sa.JSON(), nullable=False),
            sa.Column("embedding", embedding_type, nullable=True),
            search_vector,
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(["document_id"], ["knowledge_documents.id"], ondelete="CASCADE"),
            sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("document_id", "chunk_index", name="uq_knowledge_chunk_document_index"),
        )
        op.create_index("ix_knowledge_chunks_document_id", "knowledge_chunks", ["document_id"])
        op.create_index("ix_knowledge_chunks_workspace_id", "knowledge_chunks", ["workspace_id"])
        op.create_index(
            "ix_knowledge_chunks_workspace_document",
            "knowledge_chunks",
            ["workspace_id", "document_id"],
        )

    if bind.dialect.name == "postgresql":
        inspector = sa.inspect(bind)
        chunk_columns = {column["name"] for column in inspector.get_columns("knowledge_chunks")}
        if "search_vector" not in chunk_columns:
            op.add_column(
                "knowledge_chunks",
                sa.Column(
                    "search_vector",
                    postgresql.TSVECTOR(),
                    sa.Computed("to_tsvector('simple', coalesce(content, ''))", persisted=True),
                    nullable=True,
                ),
            )
        indexes = {index["name"] for index in sa.inspect(bind).get_indexes("knowledge_chunks")}
        if "ix_knowledge_chunks_search_vector" not in indexes:
            op.create_index(
                "ix_knowledge_chunks_search_vector",
                "knowledge_chunks",
                ["search_vector"],
                postgresql_using="gin",
            )
        if "ix_knowledge_chunks_embedding_hnsw" not in indexes:
            op.create_index(
                "ix_knowledge_chunks_embedding_hnsw",
                "knowledge_chunks",
                ["embedding"],
                postgresql_using="hnsw",
                postgresql_ops={"embedding": "vector_cosine_ops"},
            )


def downgrade() -> None:
    op.drop_table("knowledge_chunks")
    op.drop_table("knowledge_documents")
