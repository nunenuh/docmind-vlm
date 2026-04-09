"""
docmind/modules/documents/usecase.py

Document use case — pure file CRUD + search.
Extraction is handled by the extractions module.
"""

import asyncio
import uuid

from docmind.core.logging import get_logger
from docmind.shared.exceptions import NotFoundException

from .repositories import DocumentRepository
from .schemas import DocumentListResponse, DocumentResponse
from .services import DocumentStorageService

logger = get_logger(__name__)


class DocumentUseCase:
    """Orchestrates document file operations. NEVER calls library directly."""

    def __init__(
        self,
        repo: DocumentRepository | None = None,
        storage_service: DocumentStorageService | None = None,
    ) -> None:
        self.repo = repo or DocumentRepository()
        self.storage_service = storage_service or DocumentStorageService()

    async def create_document(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        file_bytes: bytes,
        content_type: str,
    ) -> DocumentResponse:
        """Upload file to storage and create DB record.

        If the DB insert fails, the uploaded file is cleaned up.
        """
        doc_id = str(uuid.uuid4())

        storage_path = await asyncio.to_thread(
            self.storage_service.upload_file,
            user_id=user_id,
            document_id=doc_id,
            filename=filename,
            file_bytes=file_bytes,
            content_type=content_type,
        )

        try:
            doc = await self.repo.create(
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                storage_path=storage_path,
            )
        except Exception as e:
            logger.error("document_create_failed: %s", e)
            try:
                await asyncio.to_thread(
                    self.storage_service.delete_storage_file, storage_path
                )
            except Exception as e_cleanup:
                logger.error("storage_cleanup_failed: %s", e_cleanup, storage_path=storage_path)
            raise

        return DocumentResponse(
            id=str(doc.id),
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            document_type=doc.document_type,
            page_count=doc.page_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def get_document(self, user_id: str, document_id: str) -> DocumentResponse:
        """Get a single document by ID."""
        doc = await self.repo.get_by_id(document_id, user_id)
        if doc is None:
            raise NotFoundException("Document not found")
        return DocumentResponse(
            id=str(doc.id),
            filename=doc.filename,
            file_type=doc.file_type,
            file_size=doc.file_size,
            status=doc.status,
            document_type=doc.document_type,
            page_count=doc.page_count,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        )

    async def get_documents(
        self, user_id: str, page: int, limit: int, standalone_only: bool = False
    ) -> DocumentListResponse:
        """List documents with pagination."""
        items, total = await self.repo.list_for_user(user_id, page, limit, standalone_only=standalone_only)
        return DocumentListResponse(
            items=[
                DocumentResponse(
                    id=str(doc.id),
                    filename=doc.filename,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    status=doc.status,
                    document_type=doc.document_type,
                    page_count=doc.page_count,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                )
                for doc in items
            ],
            total=total,
            page=page,
            limit=limit,
        )

    async def search_documents(
        self,
        user_id: str,
        query: str | None = None,
        file_type: str | None = None,
        status: str | None = None,
        standalone_only: bool = True,
        page: int = 1,
        limit: int = 20,
    ) -> DocumentListResponse:
        """Search documents by filename, file_type, and/or status."""
        items, total = await self.repo.search(
            user_id=user_id,
            query=query,
            file_type=file_type,
            status=status,
            standalone_only=standalone_only,
            page=page,
            limit=limit,
        )
        return DocumentListResponse(
            items=[
                DocumentResponse(
                    id=str(doc.id),
                    filename=doc.filename,
                    file_type=doc.file_type,
                    file_size=doc.file_size,
                    status=doc.status,
                    document_type=doc.document_type,
                    page_count=doc.page_count,
                    created_at=doc.created_at,
                    updated_at=doc.updated_at,
                )
                for doc in items
            ],
            total=total,
            page=page,
            limit=limit,
        )

    async def get_document_url(self, user_id: str, document_id: str) -> dict:
        """Get a signed URL for a document file."""
        doc = await self.repo.get_by_id(document_id, user_id)
        if doc is None:
            raise NotFoundException("Document not found")
        url = self.storage_service.get_signed_url(doc.storage_path)
        return {"url": url}

    async def delete_document(self, user_id: str, document_id: str) -> None:
        """Delete a document and clean up storage."""
        storage_path = await self.repo.delete(document_id, user_id)
        if storage_path is None:
            raise NotFoundException("Document not found")
        try:
            await asyncio.to_thread(self.storage_service.delete_storage_file, storage_path)
        except Exception as e:
            logger.warning("storage_cleanup_failed: %s", e, storage_path=storage_path)
