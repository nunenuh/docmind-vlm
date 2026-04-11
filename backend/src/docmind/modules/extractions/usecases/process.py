"""Extraction process usecase — trigger pipeline and classify documents."""

import asyncio
import json
from collections.abc import AsyncGenerator

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.modules.documents.protocols import (
    DocumentRepositoryProtocol,
    StorageServiceProtocol,
)
from docmind.modules.templates.protocols import TemplateRepositoryProtocol
from docmind.shared.exceptions import NotFoundException

from ..protocols import ClassificationServiceProtocol, PipelineServiceProtocol
from ..services import ClassificationService, ExtractionPipelineService

logger = get_logger(__name__)


class ExtractionProcessUseCase:
    """Orchestrates extraction triggering and document classification."""

    def __init__(
        self,
        pipeline_service: PipelineServiceProtocol | None = None,
        classification_service: ClassificationServiceProtocol | None = None,
        doc_repo: DocumentRepositoryProtocol | None = None,
        storage_service: StorageServiceProtocol | None = None,
        template_repo: TemplateRepositoryProtocol | None = None,
    ) -> None:
        self.pipeline_service = pipeline_service or ExtractionPipelineService()
        self.classification_service = (
            classification_service or ClassificationService()
        )

        # Cross-module deps — lazy defaults
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

        if template_repo is not None:
            self.template_repo = template_repo
        else:
            from docmind.modules.templates.repositories import TemplateRepository
            self.template_repo = TemplateRepository()

    def trigger_processing(
        self, document_id: str, user_id: str, template_type: str | None = None
    ) -> AsyncGenerator[str, None]:
        """Entry point for SSE processing stream."""
        return self._processing_stream(document_id, user_id, template_type)

    async def _processing_stream(
        self, document_id: str, user_id: str, template_type: str | None
    ) -> AsyncGenerator[str, None]:
        """SSE stream: classify -> preprocess -> extract -> postprocess -> store."""

        def _sse(step: str, progress: int, message: str) -> str:
            return f"data: {json.dumps({'step': step, 'progress': progress, 'message': message})}\n\n"

        doc = await self.doc_repo.get_by_id(document_id, user_id=user_id)
        if doc is None:
            yield _sse("error", 0, "Document not found")
            return

        await self.doc_repo.update_status(document_id, "processing")

        try:
            file_bytes = await asyncio.to_thread(
                self.storage_service.load_file_bytes, doc.storage_path
            )
        except Exception as e:
            logger.error("file_load_failed: %s", e)
            await self.doc_repo.update_status(document_id, "error")
            yield _sse("error", 0, "Failed to load document file")
            return

        # Resolve user provider override
        from docmind.shared.provider_resolver import resolve_provider_override

        vlm_override = await resolve_provider_override(user_id, "vlm")

        # Auto-classify if no template specified
        if not template_type:
            yield _sse("classify", 5, "Auto-detecting document type...")
            try:
                templates = await self.template_repo.list_all()
                template_types = [t.type for t in templates]
                detected_type = await self.classification_service.classify(
                    file_bytes, getattr(doc, "file_type", "pdf"), template_types,
                    override=vlm_override,
                )
                if detected_type and detected_type != "unknown":
                    template_type = detected_type
                    yield _sse("classify", 10, f"Detected: {detected_type}")
                else:
                    yield _sse("classify", 10, "Using general extraction")
            except Exception as e:
                logger.warning("Auto-classify failed: %s", e)
                yield _sse("classify", 10, "Using general extraction")

        queue: asyncio.Queue[dict | None] = asyncio.Queue()

        def on_progress(step: str, progress: float, message: str) -> None:
            queue.put_nowait({
                "step": step,
                "progress": int(progress),
                "message": message,
            })

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
            "provider_override": vlm_override,
        }

        pipeline_task = asyncio.create_task(
            asyncio.to_thread(self.pipeline_service.run_pipeline, initial_state)
        )

        settings = get_settings()
        try:
            while not pipeline_task.done():
                try:
                    event = await asyncio.wait_for(
                        queue.get(), timeout=settings.SSE_HEARTBEAT_TIMEOUT
                    )
                    if event is None:
                        break
                    yield _sse(event["step"], event["progress"], event["message"])
                except asyncio.TimeoutError:
                    yield _sse("heartbeat", -1, "alive")

            while not queue.empty():
                event = queue.get_nowait()
                if event is not None:
                    yield _sse(event["step"], event["progress"], event["message"])

            result = await pipeline_task
            if result.get("status") == "error":
                await self.doc_repo.update_status(document_id, "error")
                yield _sse(
                    "error", 0, result.get("error_message", "Processing failed")
                )
            else:
                yield _sse("complete", 100, "Done")

        except Exception as e:
            logger.error("processing_stream_error: %s", e, exc_info=True)
            await self.doc_repo.update_status(document_id, "error")
            yield _sse("error", 0, "Processing failed unexpectedly")

    async def classify_document(
        self, document_id: str, user_id: str
    ) -> dict:
        """Auto-detect document type without running extraction."""
        from docmind.shared.provider_resolver import resolve_provider_override

        doc = await self.doc_repo.get_by_id(document_id, user_id)
        if doc is None:
            raise NotFoundException("Document not found")

        file_bytes = await asyncio.to_thread(
            self.storage_service.load_file_bytes, doc.storage_path
        )

        templates = await self.template_repo.list_all()
        template_types = [t.type for t in templates]

        vlm_override = await resolve_provider_override(user_id, "vlm")
        detected = await self.classification_service.classify(
            file_bytes, doc.file_type, template_types, override=vlm_override
        )

        return {
            "document_type": detected,
            "confidence": 0.9 if detected else 0.0,
        }
