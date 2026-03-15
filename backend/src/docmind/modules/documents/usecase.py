"""docmind/modules/documents/usecase.py — Stub."""

from datetime import UTC, datetime
from typing import AsyncGenerator

from docmind.core.logging import get_logger

from .schemas import DocumentListResponse, DocumentResponse

logger = get_logger(__name__)


class DocumentUseCase:
    def create_document(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> DocumentResponse:
        return DocumentResponse(
            id="stub-id",
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            status="uploaded",
            document_type=None,
            page_count=0,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
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
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
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
