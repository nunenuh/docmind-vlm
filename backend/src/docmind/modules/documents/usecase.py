"""
docmind/modules/documents/usecase.py

Document use case — orchestrates service + repository calls.
"""

import asyncio
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator

from docmind.core.logging import get_logger

from .repositories import DocumentRepository
from .schemas import DocumentListResponse, DocumentResponse
from .services import DocumentService

logger = get_logger(__name__)


class DocumentUseCase:
    """Orchestrates document operations across service and repository layers."""

    def __init__(
        self,
        service: DocumentService | None = None,
        repo: DocumentRepository | None = None,
    ) -> None:
        self.service = service or DocumentService()
        self.repo = repo or DocumentRepository()

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
            self.service.upload_file,
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
        except Exception:
            try:
                await asyncio.to_thread(
                    self.service.delete_storage_file, storage_path
                )
            except Exception:
                logger.error("storage_cleanup_failed", storage_path=storage_path)
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

    def get_document(self, user_id: str, document_id: str) -> DocumentResponse | None:
        return DocumentResponse(
            id=document_id,
            filename="stub.pdf",
            file_type="pdf",
            file_size=1024,
            status="uploaded",
            document_type=None,
            page_count=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )

    def get_documents(
        self, user_id: str, page: int, limit: int
    ) -> DocumentListResponse:
        return DocumentListResponse(items=[], total=0, page=page, limit=limit)

    def delete_document(self, user_id: str, document_id: str) -> bool:
        return False

    def trigger_processing(
        self, document_id: str, template_type: str | None = None
    ) -> AsyncGenerator[str, None]:
        return self._processing_stream(document_id, template_type)

    async def _processing_stream(
        self, document_id: str, template_type: str | None
    ) -> AsyncGenerator[str, None]:
        import json

        payload = {
            "step": "complete",
            "progress": 100,
            "message": "Stub - not implemented",
        }
        yield f"data: {json.dumps(payload)}\n\n"
