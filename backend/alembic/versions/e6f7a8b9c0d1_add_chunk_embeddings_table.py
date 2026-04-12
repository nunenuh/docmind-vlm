"""Add chunk_embeddings table for multi-model embedding storage.

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-04-10
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e6f7a8b9c0d1"
down_revision: Union[str, None] = "d5e6f7a8b9c0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create chunk_embeddings table
    op.create_table(
        "chunk_embeddings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "chunk_id",
            sa.String(36),
            sa.ForeignKey("page_chunks.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("documents.id"),
            nullable=False,
        ),
        sa.Column("provider_name", sa.String(50), nullable=False),
        sa.Column("model_name", sa.String(100), nullable=False),
        sa.Column("dimensions", sa.Integer, nullable=False),
        sa.Column("embedding", sa.Text, nullable=False),
        sa.Column(
            "embedded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("chunk_id", "model_name", name="uq_chunk_model"),
    )
    op.create_index("idx_chunk_emb_doc_model", "chunk_embeddings", ["document_id", "model_name"])
    op.create_index("idx_chunk_emb_chunk_id", "chunk_embeddings", ["chunk_id"])
    op.create_index("idx_chunk_emb_document_id", "chunk_embeddings", ["document_id"])

    # 2. Migrate existing embeddings from page_chunks to chunk_embeddings
    op.execute(
        """
        INSERT INTO chunk_embeddings (id, chunk_id, document_id, provider_name, model_name, dimensions, embedding, embedded_at)
        SELECT
            gen_random_uuid()::varchar,
            pc.id,
            pc.document_id,
            'system_default',
            'system_default',
            1024,
            pc.embedding,
            pc.created_at
        FROM page_chunks pc
        WHERE pc.embedding IS NOT NULL
        """
    )

    # 3. Drop embedding column from page_chunks
    op.drop_column("page_chunks", "embedding")


def downgrade() -> None:
    # 1. Re-add embedding column to page_chunks
    op.add_column(
        "page_chunks",
        sa.Column("embedding", sa.Text, nullable=True),
    )

    # 2. Copy system_default embeddings back to page_chunks
    op.execute(
        """
        UPDATE page_chunks pc
        SET embedding = ce.embedding
        FROM chunk_embeddings ce
        WHERE ce.chunk_id = pc.id
          AND ce.model_name = 'system_default'
        """
    )

    # 3. Drop chunk_embeddings table
    op.drop_index("idx_chunk_emb_document_id", table_name="chunk_embeddings")
    op.drop_index("idx_chunk_emb_chunk_id", table_name="chunk_embeddings")
    op.drop_index("idx_chunk_emb_doc_model", table_name="chunk_embeddings")
    op.drop_table("chunk_embeddings")
