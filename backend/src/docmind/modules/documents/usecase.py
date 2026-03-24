"""
docmind/modules/documents/usecase.py

Document use case — orchestrates service + repository calls.
High-level business logic. NEVER calls library directly.
"""

import asyncio
import uuid
from typing import AsyncGenerator

from docmind.core.config import get_settings
from docmind.core.logging import get_logger

from .repositories import DocumentRepository
from .schemas import DocumentListResponse, DocumentResponse
from .services import DocumentStorageService, DocumentExtractionService, DocumentClassificationService

logger = get_logger(__name__)


class DocumentUseCase:
    """Orchestrates document operations. NEVER calls library directly."""

    def __init__(self) -> None:
        self.repo = DocumentRepository()
        self.storage_service = DocumentStorageService()
        self.extraction_service = DocumentExtractionService()
        self.classification_service = DocumentClassificationService()

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
        except Exception:
            try:
                await asyncio.to_thread(
                    self.storage_service.delete_storage_file, storage_path
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

    async def get_document(self, user_id: str, document_id: str) -> DocumentResponse | None:
        doc = await self.repo.get_by_id(document_id, user_id)
        if doc is None:
            return None
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

    async def get_document_url(self, user_id: str, document_id: str) -> dict | None:
        """Get a signed URL for a document file."""
        doc = await self.repo.get_by_id(document_id, user_id)
        if doc is None:
            return None
        try:
            url = self.storage_service.get_signed_url(doc.storage_path)
            return {"url": url}
        except Exception as e:
            logger.error("Failed to generate signed URL: %s", e)
            return None

    async def delete_document(self, user_id: str, document_id: str) -> bool:
        storage_path = await self.repo.delete(document_id, user_id)
        if storage_path is None:
            return False
        try:
            await asyncio.to_thread(self.storage_service.delete_storage_file, storage_path)
        except Exception:
            logger.warning("storage_cleanup_failed", storage_path=storage_path)
        return True

    def trigger_processing(
        self, document_id: str, user_id: str, template_type: str | None = None
    ) -> AsyncGenerator[str, None]:
        return self._processing_stream(document_id, user_id, template_type)

    async def _processing_stream(
        self, document_id: str, user_id: str, template_type: str | None
    ) -> AsyncGenerator[str, None]:
        import json

        def _sse(step: str, progress: int, message: str) -> str:
            return f"data: {json.dumps({'step': step, 'progress': progress, 'message': message})}\n\n"

        # Look up document
        doc = await self.repo.get_by_id(document_id, user_id=user_id)
        if doc is None:
            yield _sse("error", 0, "Document not found")
            return

        # Update status to processing
        await self.repo.update_status(document_id, "processing")

        # Load file bytes
        try:
            file_bytes = await asyncio.to_thread(
                self.storage_service.load_file_bytes, doc.storage_path
            )
        except Exception as e:
            logger.error("file_load_failed: %s", e)
            await self.repo.update_status(document_id, "error")
            yield _sse("error", 0, "Failed to load document file")
            return

        # Auto-classify if no template specified
        if not template_type:
            yield _sse("classify", 5, "Auto-detecting document type...")
            try:
                from docmind.modules.templates.repositories import TemplateRepository
                template_repo = TemplateRepository()
                templates = await template_repo.list_all()
                template_types = [t.type for t in templates]
                detected_type = await self.classification_service.classify(
                    file_bytes, getattr(doc, "file_type", "pdf"), template_types
                )
                if detected_type and detected_type != "unknown":
                    template_type = detected_type
                    yield _sse("classify", 10, f"Detected: {detected_type}")
                else:
                    yield _sse("classify", 10, "Using general extraction")
            except Exception as e:
                logger.warning("Auto-classify failed: %s", e)
                yield _sse("classify", 10, "Using general extraction")

        # Build initial pipeline state
        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def on_progress(step: str, progress: float, message: str) -> None:
            queue.put_nowait({"step": step, "progress": int(progress), "message": message})

        initial_state: dict = {
            "document_id": document_id,
            "user_id": user_id,
            "file_bytes": file_bytes,
            "file_type": getattr(doc, "file_type", "pdf"),
            "template_type": template_type,
            "page_images": [],
            "page_count": 0,
            "quality_map": {},
            "skew_angles": [],
            "raw_fields": [],
            "vlm_response": {},
            "document_type": None,
            "enhanced_fields": [],
            "comparison_data": {},
            "extraction_id": "",
            "status": "processing",
            "error_message": None,
            "audit_entries": [],
            "progress_callback": on_progress,
        }

        # Run pipeline in background thread
        pipeline_task = asyncio.create_task(
            asyncio.to_thread(self.extraction_service.run_pipeline, initial_state)
        )

        # Yield SSE events from the queue
        try:
            while not pipeline_task.done():
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=get_settings().SSE_HEARTBEAT_TIMEOUT)
                    if event is None:
                        break
                    yield _sse(event["step"], event["progress"], event["message"])
                except asyncio.TimeoutError:
                    yield _sse("heartbeat", -1, "alive")

            # Drain remaining events
            while not queue.empty():
                event = queue.get_nowait()
                if event is not None:
                    yield _sse(event["step"], event["progress"], event["message"])

            # Check pipeline result
            result = await pipeline_task
            if result.get("status") == "error":
                await self.repo.update_status(document_id, "error")
                yield _sse("error", 0, result.get("error_message", "Processing failed"))
            else:
                yield _sse("complete", 100, "Done")

        except Exception as e:
            logger.error("processing_stream_error: %s", e, exc_info=True)
            await self.repo.update_status(document_id, "error")
            yield _sse("error", 0, "Processing failed unexpectedly")

