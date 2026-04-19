"""Project document usecase — add, remove, list, reindex documents."""

import asyncio

from docmind.core.logging import get_logger
from docmind.modules.documents.protocols import (
    DocumentRepositoryProtocol,
    StorageServiceProtocol,
)
from docmind.shared.exceptions import NotFoundException

from ..protocols import IndexingServiceProtocol, ProjectRepositoryProtocol
from ..repositories import ProjectRepository
from ..schemas import ProjectDocumentResponse
from ..services import ProjectIndexingService

logger = get_logger(__name__)


class ProjectDocumentUseCase:
    """Orchestrates project document management and RAG indexing."""

    def __init__(
        self,
        repo: ProjectRepositoryProtocol | None = None,
        indexing_service: IndexingServiceProtocol | None = None,
        doc_repo: DocumentRepositoryProtocol | None = None,
        storage_service: StorageServiceProtocol | None = None,
    ) -> None:
        self.repo = repo or ProjectRepository()
        self.indexing_service = indexing_service or ProjectIndexingService()

        # Cross-module deps — lazy defaults to avoid circular imports
        if doc_repo is not None:
            self.doc_repo = doc_repo
        else:
            from docmind.modules.documents.repositories import DocumentRepository
            self.doc_repo = DocumentRepository()

        if storage_service is not None:
            self.storage_service = storage_service
        else:
            from docmind.modules.documents.services import DocumentStorageService
            self.storage_service = DocumentStorageService()

    async def add_document(
        self, user_id: str, project_id: str, document_id: str
    ) -> bool:
        """Link a document to a project and trigger RAG indexing."""
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return False

        added = await self.repo.add_document(project_id, document_id)
        if not added:
            return False

        asyncio.create_task(
            self._safe_index(project_id, document_id, user_id)
        )
        return True

    async def _safe_index(
        self, project_id: str, document_id: str, user_id: str
    ) -> None:
        """Background wrapper for RAG indexing with error handling."""
        try:
            await self._index_document_for_rag(project_id, document_id, user_id)
        except Exception as e:
            logger.error("RAG indexing failed for doc %s: %s", document_id, e)

    async def _index_document_for_rag(
        self, project_id: str, document_id: str, user_id: str
    ) -> None:
        """Download file and run RAG indexing pipeline."""
        doc = await self.doc_repo.get_by_id(document_id, user_id)
        if doc is None:
            logger.warning("Document %s not found for RAG indexing", document_id)
            return

        file_bytes = await asyncio.to_thread(
            self.storage_service.load_file_bytes, doc.storage_path
        )

        chunk_count = await self.indexing_service.index(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=doc.file_type,
            filename=doc.filename,
        )
        logger.info(
            "RAG indexed doc %s: %d chunks for project %s",
            document_id,
            chunk_count,
            project_id,
        )

    async def list_documents(
        self, user_id: str, project_id: str
    ) -> list[ProjectDocumentResponse]:
        """List all documents in a project."""
        docs = await self.repo.list_documents(project_id, user_id)
        return [
            ProjectDocumentResponse(
                id=str(doc.id),
                filename=doc.filename,
                file_type=doc.file_type,
                file_size=doc.file_size or 0,
                page_count=doc.page_count or 0,
                status=doc.status,
                created_at=doc.created_at,
            )
            for doc in docs
        ]

    async def remove_document(
        self, user_id: str, project_id: str, document_id: str
    ) -> bool:
        """Fully delete a document from a project (issue #104).

        Deletes DB rows (Document, PageChunks, ChunkEmbeddings, Extractions,
        ChatMessages, Citations) in a single transaction, then removes the
        storage file. Storage errors are logged but do not fail the operation —
        the DB is the source of truth.
        """
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            raise NotFoundException("Project not found")
        storage_path = await self.repo.remove_document(project_id, document_id)
        if storage_path is None:
            raise NotFoundException("Document not found in project")

        try:
            await asyncio.to_thread(
                self.storage_service.delete_storage_file, storage_path
            )
        except Exception as e:
            logger.warning(
                "storage_file_delete_failed",
                storage_path=storage_path,
                document_id=document_id,
                error=str(e),
                exc_info=True,
            )

        return True

    async def reindex_document(
        self, user_id: str, project_id: str, document_id: str
    ) -> int:
        """Re-index a document: delete old RAG chunks and re-index."""
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            raise NotFoundException("Project not found")

        docs = await self.repo.list_documents(project_id, user_id)
        doc = next((d for d in docs if str(d.id) == document_id), None)
        if doc is None:
            raise NotFoundException("Document not found in project")

        file_bytes = self.storage_service.load_file_bytes(doc.storage_path)

        count = await self.indexing_service.reindex(
            document_id=document_id,
            project_id=project_id,
            file_bytes=file_bytes,
            file_type=doc.file_type,
            filename=doc.filename,
        )

        logger.info("Reindexed document %s: %d chunks", document_id, count)
        return count

    async def list_chunks(
        self, user_id: str, project_id: str, document_id: str | None = None
    ) -> dict:
        """List RAG chunks for a project."""
        project = await self.repo.get_by_id(project_id, user_id)
        if project is None:
            return {"total": 0, "items": []}

        chunks, total = await self.repo.list_chunks(project_id, document_id)
        return {
            "total": total,
            "items": [
                {
                    "id": c.id,
                    "document_id": c.document_id,
                    "page_number": c.page_number,
                    "chunk_index": c.chunk_index,
                    "content": (
                        c.content[:200] + "..."
                        if len(c.content or "") > 200
                        else c.content
                    ),
                    "raw_content": (
                        (c.raw_content or "")[:200] + "..."
                        if len(c.raw_content or "") > 200
                        else c.raw_content
                    ),
                    "content_hash": c.content_hash,
                    "metadata": c.metadata_json,
                    "created_at": (
                        str(c.created_at) if c.created_at else None
                    ),
                }
                for c in chunks
            ],
        }
