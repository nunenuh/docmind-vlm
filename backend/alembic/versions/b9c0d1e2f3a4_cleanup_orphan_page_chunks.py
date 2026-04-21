"""One-time cleanup of orphaned page_chunks + chunk_embeddings.

Before issue #104 was merged, removing a document from a project only
unlinked the document (set documents.project_id = NULL) and left the
associated page_chunks rows pointing at the project. These orphan chunks
leaked into RAG retrieval. The code-level fix now requires
``documents.project_id = page_chunks.project_id`` at query time, but
existing orphan rows must be deleted so historical projects no longer
hold phantom context.

Revision ID: b9c0d1e2f3a4
Revises: a8b9c0d1e2f3
Create Date: 2026-04-21
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b9c0d1e2f3a4"
down_revision: Union[str, None] = "a8b9c0d1e2f3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Delete orphan chunks where either the document was unlinked or its
    # project assignment has moved. ChunkEmbedding rows cascade via
    # chunk_embeddings.chunk_id (ON DELETE CASCADE).
    op.execute(
        """
        DELETE FROM page_chunks pc
        USING documents d
        WHERE pc.document_id = d.id
          AND (d.project_id IS NULL OR d.project_id <> pc.project_id);
        """
    )

    # Belt-and-braces: also delete chunks whose document row no longer
    # exists at all (should be empty after #104's delete path ships).
    op.execute(
        """
        DELETE FROM page_chunks
        WHERE document_id NOT IN (SELECT id FROM documents);
        """
    )


def downgrade() -> None:
    # Irreversible data cleanup — no-op downgrade.
    pass
