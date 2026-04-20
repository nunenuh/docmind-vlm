"""Rescope ``idx_page_chunks_content_hash`` to (document_id, content_hash).

Different documents in the same project can legitimately share identical
text blocks (e.g., standard government form headers). The original unique
index was ``(project_id, content_hash)`` which caused the second document's
indexing to fail. Commit 031d578 updated the constraint in the model and in
`a2b3c4d5e6f7`'s source, but databases already at that revision retained the
old project-scoped index. This migration safely rescopes any existing
index regardless of its current columns.

Revision ID: a8b9c0d1e2f3
Revises: f7a8b9c0d1e2
Create Date: 2026-04-20
"""

from typing import Sequence, Union

from alembic import op

revision: str = "a8b9c0d1e2f3"
down_revision: Union[str, None] = "f7a8b9c0d1e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


INDEX_NAME = "idx_page_chunks_content_hash"


def upgrade() -> None:
    # Drop any existing unique index on content_hash regardless of scope.
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    op.create_index(
        INDEX_NAME,
        "page_chunks",
        ["document_id", "content_hash"],
        unique=True,
    )


def downgrade() -> None:
    op.execute(f"DROP INDEX IF EXISTS {INDEX_NAME}")
    op.create_index(
        INDEX_NAME,
        "page_chunks",
        ["project_id", "content_hash"],
        unique=True,
    )
