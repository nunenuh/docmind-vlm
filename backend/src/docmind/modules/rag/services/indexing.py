"""RAG indexing service — extract → chunk → dedup → embed → store."""

from __future__ import annotations

from docmind.core.config import Settings, get_settings
from docmind.core.logging import get_logger
from docmind.library.rag.chunker import chunk_pages
from docmind.library.rag.embedder import embed_texts
from docmind.library.rag.text_extract import extract_text
from docmind.shared.exceptions import IndexingException

from ..repositories import ChunkRepository
from ..schemas import IndexResult

logger = get_logger(__name__)


def _estimate_tokens(text: str) -> int:
    """Rough token estimate: ~3 chars per token for mixed English/CJK."""
    return len(text) // 3


class RAGIndexingService:
    """Document indexing: extract → chunk → dedup → embed → store.

    Owns the full indexing pipeline but delegates storage to ChunkRepository.
    """

    def __init__(
        self,
        chunk_repo: ChunkRepository | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._chunk_repo = chunk_repo or ChunkRepository()
        self._settings = settings or get_settings()

    async def index_document(
        self,
        document_id: str,
        project_id: str,
        file_bytes: bytes,
        file_type: str,
        filename: str = "",
    ) -> IndexResult:
        """Index a document for RAG: extract → chunk → dedup → embed → store."""
        try:
            pages = extract_text(file_bytes, file_type)
            doc_context = filename or document_id[:8]
            chunks = chunk_pages(pages, doc_context=doc_context)

            if not chunks:
                logger.warning("No chunks extracted from document %s", document_id)
                return IndexResult(document_id=document_id, project_id=project_id, chunks_created=0)

            logger.info("Chunked document %s into %d chunks (from %d pages)", document_id, len(chunks), len(pages))

            existing_hashes = await self._chunk_repo.get_existing_hashes(project_id)
            new_chunks = [c for c in chunks if c.get("content_hash") not in existing_hashes]
            duplicates_skipped = len(chunks) - len(new_chunks)

            if duplicates_skipped > 0:
                logger.info("Skipped %d duplicate chunks for document %s", duplicates_skipped, document_id)

            if not new_chunks:
                return IndexResult(document_id=document_id, project_id=project_id, chunks_created=0, duplicates_skipped=duplicates_skipped)

            safe_chunks = self._apply_token_guard(new_chunks, self._settings.RAG_MAX_EMBEDDING_TOKENS, document_id)
            texts = [c["content"] for c in safe_chunks]
            embeddings = await embed_texts(texts)

            created = await self._chunk_repo.bulk_create(
                chunks=safe_chunks, embeddings=embeddings,
                document_id=document_id, project_id=project_id,
                filename=filename, file_type=file_type,
            )

            logger.info("Indexed document %s: %d new chunks stored", document_id, created)
            return IndexResult(document_id=document_id, project_id=project_id, chunks_created=created, duplicates_skipped=duplicates_skipped)

        except IndexingException:
            raise
        except Exception as e:
            logger.error("index_document_failed: document=%s error=%s", document_id, e)
            raise IndexingException(f"Failed to index document {document_id}: {e}") from e

    async def reindex_document(
        self, document_id: str, project_id: str,
        file_bytes: bytes, file_type: str, filename: str = "",
    ) -> IndexResult:
        """Re-index: delete old chunks → index fresh."""
        deleted = await self._chunk_repo.delete_by_document(document_id)
        logger.info("Deleted %d old chunks for document %s", deleted, document_id)
        return await self.index_document(document_id=document_id, project_id=project_id, file_bytes=file_bytes, file_type=file_type, filename=filename)

    async def delete_document_chunks(self, document_id: str) -> int:
        """Delete all chunks for a document."""
        return await self._chunk_repo.delete_by_document(document_id)

    async def delete_project_chunks(self, project_id: str) -> int:
        """Delete all chunks for a project."""
        return await self._chunk_repo.delete_by_project(project_id)

    def _apply_token_guard(self, chunks: list[dict], max_tokens: int, document_id: str) -> list[dict]:
        """Truncate chunks that exceed embedding token limit."""
        safe: list[dict] = []
        for chunk in chunks:
            if _estimate_tokens(chunk["content"]) > max_tokens:
                logger.warning("Chunk exceeds token limit, truncating for doc %s page %d", document_id, chunk["page_number"])
                safe.append({**chunk, "content": chunk["content"][:max_tokens * 3]})
            else:
                safe.append(chunk)
        return safe
