"""Add raw_content and content_hash to page_chunks for RAG v2.

Revision ID: a2b3c4d5e6f7
Revises: 0381657a47c7
Create Date: 2026-03-23
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "1f8fcc3ba0a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add raw_content column for BM25 search
    op.add_column(
        "page_chunks",
        sa.Column("raw_content", sa.Text(), nullable=True),
    )
    # Add content_hash for duplicate detection
    op.add_column(
        "page_chunks",
        sa.Column("content_hash", sa.String(64), nullable=True),
    )
    # Unique index on document_id + content_hash for dedup
    # Scoped per-document (not per-project) so different docs can have same content
    op.create_index(
        "idx_page_chunks_content_hash",
        "page_chunks",
        ["document_id", "content_hash"],
        unique=True,
    )
    # Backfill raw_content from content for existing rows
    op.execute("UPDATE page_chunks SET raw_content = content WHERE raw_content IS NULL")


def downgrade() -> None:
    op.drop_index("idx_page_chunks_content_hash", table_name="page_chunks")
    op.drop_column("page_chunks", "content_hash")
    op.drop_column("page_chunks", "raw_content")
