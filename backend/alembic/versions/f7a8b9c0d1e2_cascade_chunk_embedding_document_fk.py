"""Add ON DELETE CASCADE on chunk_embeddings.document_id FK (issue #104).

When a Document is deleted, orphaned ChunkEmbedding rows previously remained
in the database and leaked into RAG retrieval. This migration alters the FK
so deletions cascade automatically as defense-in-depth on top of the
application-layer deletion logic.

Revision ID: f7a8b9c0d1e2
Revises: e6f7a8b9c0d1
Create Date: 2026-04-19
"""

from typing import Sequence, Union

from alembic import op

revision: str = "f7a8b9c0d1e2"
down_revision: Union[str, None] = "e6f7a8b9c0d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "chunk_embeddings_document_id_fkey"


def upgrade() -> None:
    # Drop any existing FK on document_id regardless of its auto-generated
    # name, so the migration is safe across databases initialised via
    # `alembic upgrade` or `create_all`.
    op.execute(
        """
        DO $$
        DECLARE
            existing_name text;
        BEGIN
            SELECT conname INTO existing_name
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_attribute a ON a.attrelid = t.oid AND a.attnum = ANY (c.conkey)
            WHERE t.relname = 'chunk_embeddings'
              AND a.attname = 'document_id'
              AND c.contype = 'f'
            LIMIT 1;

            IF existing_name IS NOT NULL THEN
                EXECUTE format(
                    'ALTER TABLE chunk_embeddings DROP CONSTRAINT %I',
                    existing_name
                );
            END IF;
        END $$;
        """
    )
    op.create_foreign_key(
        CONSTRAINT_NAME,
        "chunk_embeddings",
        "documents",
        ["document_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    op.execute(
        f"ALTER TABLE chunk_embeddings DROP CONSTRAINT IF EXISTS {CONSTRAINT_NAME}"
    )
    op.create_foreign_key(
        CONSTRAINT_NAME,
        "chunk_embeddings",
        "documents",
        ["document_id"],
        ["id"],
    )
