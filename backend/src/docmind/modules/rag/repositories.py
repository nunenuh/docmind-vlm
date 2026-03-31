"""
docmind/modules/rag/repositories.py

PageChunk data access — owns all chunk CRUD operations.
All queries filter by project_id for data isolation.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import PageChunk
from docmind.shared.exceptions import DatabaseException, RecordNotFoundException

logger = get_logger(__name__)


class ChunkRepository:
    """Repository for PageChunk CRUD operations.

    This is the single source of truth for chunk data access.
    No other module should query PageChunk directly.
    """

    async def list_by_project(
        self,
        project_id: str,
        document_id: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[list[PageChunk], int]:
        """List chunks for a project, optionally filtered by document.

        Args:
            project_id: Project scope.
            document_id: Optional document filter.
            limit: Max results.
            offset: Pagination offset.

        Returns:
            Tuple of (chunk_list, total_count).
        """
        async with AsyncSessionLocal() as session:
            filters = [PageChunk.project_id == project_id]
            if document_id:
                filters.append(PageChunk.document_id == document_id)

            count_stmt = select(func.count()).select_from(PageChunk).where(*filters)
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(PageChunk)
                .where(*filters)
                .order_by(PageChunk.page_number, PageChunk.chunk_index)
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            chunks = list(result.scalars().all())

            return chunks, total

    async def get_by_id(self, chunk_id: str, project_id: str) -> PageChunk:
        """Get a single chunk by ID, scoped to project.

        Raises:
            RecordNotFoundException: If chunk not found.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(PageChunk).where(
                PageChunk.id == chunk_id,
                PageChunk.project_id == project_id,
            )
            result = await session.execute(stmt)
            chunk = result.scalar_one_or_none()
            if chunk is None:
                raise RecordNotFoundException(f"Chunk {chunk_id} not found")
            return chunk

    async def count_by_project(self, project_id: str) -> int:
        """Count all chunks for a project."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(PageChunk)
                .where(PageChunk.project_id == project_id)
            )
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def count_by_document(self, document_id: str) -> int:
        """Count all chunks for a document."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(func.count())
                .select_from(PageChunk)
                .where(PageChunk.document_id == document_id)
            )
            result = await session.execute(stmt)
            return result.scalar() or 0

    async def get_existing_hashes(self, project_id: str) -> set[str]:
        """Get all content hashes for chunks in a project.

        Used for duplicate detection at indexing time.
        """
        async with AsyncSessionLocal() as session:
            stmt = select(PageChunk.content_hash).where(
                PageChunk.project_id == project_id,
                PageChunk.content_hash.isnot(None),
            )
            result = await session.execute(stmt)
            rows = result.all()
            return {row[0] for row in rows if row[0]}

    async def bulk_create(
        self,
        chunks: list[dict],
        embeddings: list[list[float]],
        document_id: str,
        project_id: str,
        filename: str,
        file_type: str,
    ) -> int:
        """Bulk insert chunks with embeddings.

        Args:
            chunks: List of chunk dicts from chunker.
            embeddings: Corresponding embedding vectors.
            document_id: Document ID.
            project_id: Project ID.
            filename: Original filename for metadata.
            file_type: File type for metadata.

        Returns:
            Number of chunks created.

        Raises:
            DatabaseException: On database write failure.
        """
        if not chunks:
            return 0

        try:
            async with AsyncSessionLocal() as session:
                for chunk_data, embedding in zip(chunks, embeddings):
                    metadata = {
                        "section_header": chunk_data.get("section_header", ""),
                        "filename": filename,
                        "file_type": file_type,
                    }
                    chunk = PageChunk(
                        document_id=document_id,
                        project_id=project_id,
                        page_number=chunk_data["page_number"],
                        chunk_index=chunk_data["chunk_index"],
                        content=chunk_data["content"],
                        raw_content=chunk_data.get("raw_content", ""),
                        content_hash=chunk_data.get("content_hash", ""),
                        embedding=embedding,
                        metadata_json=json.dumps(metadata),
                    )
                    session.add(chunk)
                await session.commit()
                return len(chunks)
        except Exception as e:
            logger.error("bulk_create_chunks_failed: %s", e)
            raise DatabaseException(f"Failed to store chunks: {e}") from e

    async def delete_by_document(self, document_id: str) -> int:
        """Delete all chunks for a document.

        Returns:
            Number of chunks deleted.
        """
        async with AsyncSessionLocal() as session:
            stmt = sa_delete(PageChunk).where(PageChunk.document_id == document_id)
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount or 0
            logger.info("Deleted %d chunks for document %s", count, document_id)
            return count

    async def delete_by_project(self, project_id: str) -> int:
        """Delete all chunks for a project.

        Returns:
            Number of chunks deleted.
        """
        async with AsyncSessionLocal() as session:
            stmt = sa_delete(PageChunk).where(PageChunk.project_id == project_id)
            result = await session.execute(stmt)
            await session.commit()
            count = result.rowcount or 0
            logger.info("Deleted %d chunks for project %s", count, project_id)
            return count
