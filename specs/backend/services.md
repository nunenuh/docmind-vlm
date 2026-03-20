# Backend Spec: Service Layer (Per-Module)

Files: `backend/src/docmind/modules/` — each module contains `services.py`, `repositories.py`, `usecase.py`

See also: [[projects/docmind-vlm/specs/backend/api]] · [[projects/docmind-vlm/specs/backend/pipeline-processing]] · [[projects/docmind-vlm/specs/backend/pipeline-chat]]

---

## Architecture: Handler -> UseCase -> Service -> Repository

Each feature module under `docmind/modules/` follows a 4-layer pattern:

```
modules/{module}/
├── apiv1/
│   └── handler.py       # FastAPI route handlers (thin — validate, delegate, serialize)
├── schemas.py           # Pydantic request/response models
├── usecase.py           # Orchestration — wires service + repository (+ library pipeline)
├── services.py          # Business logic — uses library only, NO DB access
└── repositories.py      # DB operations only — SQLAlchemy queries
```

**Dependency direction:** `handler.py` -> `usecase.py` -> `services.py` + `repositories.py` -> `library/` + `dbase/psql/` + `dbase/supabase/` (storage only)

**Key constraint:** Services never import from `modules/{other_module}/`. Cross-module coordination happens through `shared/` or at the usecase level.

---

## Module Summary

| Module | UseCase | Service | Repository |
|--------|---------|---------|------------|
| **health** | `HealthUseCase` | `HealthService` | — (no DB) |
| **documents** | `DocumentUseCase` | `DocumentService` | `DocumentRepository` |
| **extractions** | `ExtractionUseCase` | `ExtractionService` | `ExtractionRepository` |
| **chat** | `ChatUseCase` | `ChatService` | `ChatRepository` |
| **templates** | — (static data) | — | — |
| **projects** | `ProjectUseCase` | `ProjectService` | `ProjectRepository` |
| **personas** | — (thin CRUD) | — | `PersonaRepository` |

---

## Imports Pattern

```python
# UseCase imports
from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.library.pipeline import run_processing_pipeline, run_chat_pipeline
from docmind.shared.exceptions import ServiceException

from .services import DocumentService
from .repositories import DocumentRepository

# Service imports (library only — NO DB)
from docmind.library.providers import get_vlm_provider
from docmind.library.cv import convert_to_page_images

# Repository imports (DB only — SQLAlchemy)
from sqlalchemy import select, update, delete
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import Document, Extraction, ExtractedField
from docmind.shared.exceptions import RepositoryException
```

---

## Documents Module

### `modules/documents/repositories.py`

```python
"""
docmind/modules/documents/repositories.py

Document database operations via SQLAlchemy.
"""
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    AuditEntry,
    ChatMessage,
    Document,
    ExtractedField,
    Extraction,
)

logger = get_logger(__name__)


class DocumentRepository:
    """Repository for document CRUD operations via SQLAlchemy."""

    async def create(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> Document:
        """Insert a new document record. Returns the created ORM instance."""
        async with AsyncSessionLocal() as session:
            doc = Document(
                user_id=user_id,
                filename=filename,
                file_type=file_type,
                file_size=file_size,
                storage_path=storage_path,
            )
            session.add(doc)
            await session.commit()
            await session.refresh(doc)
            return doc

    async def get_by_id(self, document_id: str, user_id: str) -> Document | None:
        """Get a single document by ID, scoped to user."""
        async with AsyncSessionLocal() as session:
            stmt = select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[Document], int]:
        """Get paginated documents for a user. Returns (items, total_count)."""
        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            # Count total
            count_stmt = select(func.count()).select_from(Document).where(
                Document.user_id == user_id
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            # Fetch page
            stmt = (
                select(Document)
                .where(Document.user_id == user_id)
                .order_by(Document.created_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def delete(self, document_id: str, user_id: str) -> str | None:
        """Delete a document and cascaded records. Returns storage_path if found."""
        async with AsyncSessionLocal() as session:
            # Get document first
            stmt = select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc is None:
                return None

            storage_path = doc.storage_path

            # Cascading delete (order matters for FK constraints)
            # Get extraction IDs
            ext_stmt = select(Extraction.id).where(Extraction.document_id == document_id)
            ext_result = await session.execute(ext_stmt)
            ext_ids = [row[0] for row in ext_result.all()]

            if ext_ids:
                await session.execute(
                    sa_delete(AuditEntry).where(AuditEntry.extraction_id.in_(ext_ids))
                )
                await session.execute(
                    sa_delete(ExtractedField).where(ExtractedField.extraction_id.in_(ext_ids))
                )

            await session.execute(
                sa_delete(ChatMessage).where(ChatMessage.document_id == document_id)
            )
            await session.execute(
                sa_delete(Extraction).where(Extraction.document_id == document_id)
            )
            await session.delete(doc)
            await session.commit()

            return storage_path

    async def update_status(
        self,
        document_id: str,
        status: str,
        **kwargs,
    ) -> None:
        """Update document status and optional fields."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(
                    status=status,
                    updated_at=datetime.now(timezone.utc),
                    **kwargs,
                )
            )
            await session.execute(stmt)
            await session.commit()
```

### `modules/documents/services.py`

```python
"""
docmind/modules/documents/services.py

Document business logic — uses library only, NO direct DB access.
"""
from docmind.core.logging import get_logger
from docmind.dbase.supabase.storage import get_file_bytes, delete_file

logger = get_logger(__name__)


class DocumentService:
    """Business logic for document operations (no DB)."""

    def load_file_bytes(self, storage_path: str) -> bytes:
        """Load document file bytes from Supabase storage."""
        return get_file_bytes(storage_path)

    def delete_storage_file(self, storage_path: str) -> None:
        """Delete file from Supabase storage. Logs warning on failure."""
        try:
            delete_file(storage_path)
        except Exception as e:
            logger.warning("Failed to delete file %s: %s", storage_path, e)
```

### `modules/documents/usecase.py`

```python
"""
docmind/modules/documents/usecase.py

Orchestrates document operations — wires service + repository + pipeline.
"""
import asyncio
import json
from datetime import datetime, timezone
from typing import AsyncGenerator

from docmind.core.logging import get_logger
from docmind.library.pipeline import run_processing_pipeline

from .repositories import DocumentRepository
from .schemas import DocumentListResponse, DocumentResponse
from .services import DocumentService

logger = get_logger(__name__)


class DocumentUseCase:
    """Orchestrates the full document lifecycle."""

    def __init__(self):
        self.repo = DocumentRepository()
        self.service = DocumentService()

    def create_document(
        self,
        user_id: str,
        filename: str,
        file_type: str,
        file_size: int,
        storage_path: str,
    ) -> DocumentResponse:
        """Create a new document record."""
        row = self.repo.create(
            user_id=user_id,
            filename=filename,
            file_type=file_type,
            file_size=file_size,
            storage_path=storage_path,
        )
        return DocumentResponse(**row)

    def get_document(self, user_id: str, document_id: str) -> DocumentResponse | None:
        """Get a single document by ID, scoped to user."""
        row = self.repo.get_by_id(document_id, user_id)
        if row is None:
            return None
        return DocumentResponse(**row)

    def get_documents(
        self,
        user_id: str,
        page: int,
        limit: int,
    ) -> DocumentListResponse:
        """Get paginated list of documents for a user."""
        items, total = self.repo.list_for_user(user_id, page, limit)
        return DocumentListResponse(
            items=[DocumentResponse(**row) for row in items],
            total=total,
            page=page,
            limit=limit,
        )

    def delete_document(self, user_id: str, document_id: str) -> bool:
        """Delete a document and all associated data."""
        storage_path = self.repo.delete(document_id, user_id)
        if storage_path is None:
            return False
        self.service.delete_storage_file(storage_path)
        logger.info("Deleted document %s and all associated data", document_id)
        return True

    def trigger_processing(
        self,
        document_id: str,
        template_type: str | None = None,
    ) -> AsyncGenerator[str, None]:
        """Start processing pipeline and return SSE stream."""
        return self._processing_stream(document_id, template_type)

    async def _processing_stream(
        self,
        document_id: str,
        template_type: str | None,
    ) -> AsyncGenerator[str, None]:
        """Internal SSE stream generator for processing."""
        progress_queue: asyncio.Queue = asyncio.Queue()

        def on_progress(step: str, progress: int, message: str) -> None:
            progress_queue.put_nowait({
                "step": step,
                "progress": progress,
                "message": message,
            })

        # Get document metadata
        doc = self.repo.get_by_id(document_id, user_id="")  # system-level access
        if doc is None:
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': 'Document not found'})}\n\n"
            return

        # Update status to processing
        self.repo.update_status(document_id, "processing")

        # Load file bytes
        try:
            file_bytes = self.service.load_file_bytes(doc["storage_path"])
        except Exception as e:
            logger.error("Failed to load file %s: %s", doc["storage_path"], e)
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': 'Failed to load file'})}\n\n"
            return

        # Build initial state
        initial_state = {
            "document_id": document_id,
            "user_id": "",
            "file_bytes": file_bytes,
            "file_type": doc["file_type"],
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

        # Run pipeline in background
        task = asyncio.create_task(
            asyncio.to_thread(run_processing_pipeline, initial_state)
        )

        while not task.done():
            try:
                event = await asyncio.wait_for(progress_queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'step': 'heartbeat', 'progress': -1, 'message': 'alive'})}\n\n"

        # Drain remaining events
        while not progress_queue.empty():
            event = progress_queue.get_nowait()
            yield f"data: {json.dumps(event)}\n\n"

        # Check for errors
        result = task.result()
        if result.get("status") == "error":
            self.repo.update_status(document_id, "error")
            yield f"data: {json.dumps({'step': 'error', 'progress': 0, 'message': result.get('error_message', 'Processing failed')})}\n\n"
```

---

## Extractions Module

### `modules/extractions/repositories.py`

```python
"""
docmind/modules/extractions/repositories.py

Extraction database operations via SQLAlchemy.
"""
from sqlalchemy import select

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import AuditEntry, ExtractedField, Extraction

logger = get_logger(__name__)


class ExtractionRepository:
    """Repository for extraction result queries via SQLAlchemy."""

    async def get_latest_extraction(self, document_id: str) -> Extraction | None:
        """Get the most recent extraction record for a document."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Extraction)
                .where(Extraction.document_id == document_id)
                .order_by(Extraction.created_at.desc())
                .limit(1)
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def get_fields(self, extraction_id: str) -> list[ExtractedField]:
        """Get all extracted fields for an extraction."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ExtractedField)
                .where(ExtractedField.extraction_id == extraction_id)
                .order_by(ExtractedField.page_number, ExtractedField.field_key)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_audit_trail(self, extraction_id: str) -> list[AuditEntry]:
        """Get audit trail entries for an extraction."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(AuditEntry)
                .where(AuditEntry.extraction_id == extraction_id)
                .order_by(AuditEntry.step_order)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
```

### `modules/extractions/services.py`

```python
"""
docmind/modules/extractions/services.py

Extraction business logic — overlay coloring, comparison building.
"""
from docmind.core.logging import get_logger

logger = get_logger(__name__)

# Confidence color thresholds for overlay visualization
COLOR_HIGH = "#22c55e"    # Green: confidence >= 0.8
COLOR_MEDIUM = "#eab308"  # Yellow: confidence >= 0.5
COLOR_LOW = "#ef4444"     # Red: confidence < 0.5


class ExtractionService:
    """Business logic for extraction results (no DB)."""

    @staticmethod
    def confidence_color(confidence: float) -> str:
        """Map confidence score to hex color for overlay visualization."""
        if confidence >= 0.8:
            return COLOR_HIGH
        if confidence >= 0.5:
            return COLOR_MEDIUM
        return COLOR_LOW

    @staticmethod
    def build_overlay_region(field: dict) -> dict | None:
        """Convert an extracted field to an overlay region. Returns None if no bbox."""
        bbox = field.get("bounding_box", {})
        if not bbox or not bbox.get("x"):
            return None

        confidence = field.get("confidence", 0.0)
        field_key = field.get("field_key", "")
        field_value = field.get("field_value", "")
        tooltip = f"{field_key}: {field_value}" if field_key else field_value

        return {
            "x": bbox["x"],
            "y": bbox["y"],
            "width": bbox["width"],
            "height": bbox["height"],
            "confidence": confidence,
            "color": ExtractionService.confidence_color(confidence),
            "tooltip": tooltip[:200],
        }
```

### `modules/extractions/usecase.py`

```python
"""
docmind/modules/extractions/usecase.py

Orchestrates extraction result operations — wires service + repository.
"""
from docmind.core.logging import get_logger

from .repositories import ExtractionRepository
from .schemas import (
    AuditEntryResponse,
    ComparisonResponse,
    ExtractedFieldResponse,
    ExtractionResponse,
    OverlayRegion,
)
from .services import ExtractionService

logger = get_logger(__name__)


class ExtractionUseCase:
    """Orchestrates extraction result queries."""

    def __init__(self):
        self.repo = ExtractionRepository()
        self.service = ExtractionService()

    def get_extraction(self, document_id: str) -> ExtractionResponse | None:
        """Get the extraction result for a document."""
        ext = self.repo.get_latest_extraction(document_id)
        if ext is None:
            return None

        fields = self.repo.get_fields(ext["id"])

        return ExtractionResponse(
            id=ext["id"],
            document_id=ext["document_id"],
            mode=ext["mode"],
            template_type=ext.get("template_type"),
            fields=[ExtractedFieldResponse(**f) for f in fields],
            processing_time_ms=ext["processing_time_ms"],
            created_at=ext["created_at"],
        )

    def get_audit_trail(self, document_id: str) -> list[AuditEntryResponse]:
        """Get the processing audit trail for a document."""
        ext = self.repo.get_latest_extraction(document_id)
        if ext is None:
            return []

        entries = self.repo.get_audit_trail(ext["id"])
        return [AuditEntryResponse(**e) for e in entries]

    def get_overlay_data(self, document_id: str) -> list[OverlayRegion]:
        """Get bounding box overlay data for document visualization."""
        ext = self.repo.get_latest_extraction(document_id)
        if ext is None:
            return []

        fields = self.repo.get_fields(ext["id"])
        regions = []
        for field in fields:
            region = self.service.build_overlay_region(field)
            if region:
                regions.append(OverlayRegion(**region))

        return regions

    def get_comparison(self, document_id: str) -> ComparisonResponse | None:
        """Get enhanced vs raw extraction comparison."""
        extraction = self.get_extraction(document_id)
        if extraction is None:
            return None

        audit_trail = self.get_audit_trail(document_id)
        postprocess_entry = next(
            (e for e in audit_trail if e.step_name == "postprocess"),
            None,
        )

        corrected: list[str] = []
        added: list[str] = []

        if postprocess_entry:
            output = postprocess_entry.output_summary
            corrected = output.get("corrected_ids", [])
            added = output.get("added_ids", [])

        # Build raw fields (strip pipeline enhancements)
        raw_fields = [
            {
                "id": f.id,
                "field_type": f.field_type,
                "field_key": f.field_key,
                "field_value": f.field_value,
                "page_number": f.page_number,
                "bounding_box": f.bounding_box,
                "confidence": f.vlm_confidence,  # Raw = VLM confidence only
            }
            for f in extraction.fields
            if f.id not in added
        ]

        return ComparisonResponse(
            enhanced_fields=extraction.fields,
            raw_fields=raw_fields,
            corrected=corrected,
            added=added,
        )
```

---

## Chat Module

### `modules/chat/repositories.py`

```python
"""
docmind/modules/chat/repositories.py

Chat message database operations via SQLAlchemy.
"""
from sqlalchemy import func, select

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import ChatMessage, ExtractedField, Extraction

logger = get_logger(__name__)


class ChatRepository:
    """Repository for chat message operations via SQLAlchemy."""

    async def save_message(
        self,
        document_id: str,
        user_id: str,
        role: str,
        content: str,
        citations: list[dict] | None = None,
    ) -> str:
        """Save a chat message. Returns the message ID."""
        async with AsyncSessionLocal() as session:
            msg = ChatMessage(
                document_id=document_id,
                user_id=user_id,
                role=role,
                content=content,
                citations=citations or [],
            )
            session.add(msg)
            await session.commit()
            await session.refresh(msg)
            return str(msg.id)

    async def get_history(
        self,
        document_id: str,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[ChatMessage], int]:
        """Get paginated chat history. Returns (items, total_count)."""
        offset = (page - 1) * limit

        async with AsyncSessionLocal() as session:
            # Count total
            count_stmt = (
                select(func.count())
                .select_from(ChatMessage)
                .where(
                    ChatMessage.document_id == document_id,
                    ChatMessage.user_id == user_id,
                )
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            # Fetch page
            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.document_id == document_id,
                    ChatMessage.user_id == user_id,
                )
                .order_by(ChatMessage.created_at)
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())

            return items, total

    async def get_recent_messages(
        self,
        document_id: str,
        user_id: str,
        limit: int = 20,
    ) -> list[ChatMessage]:
        """Get recent messages for conversation context."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(ChatMessage)
                .where(
                    ChatMessage.document_id == document_id,
                    ChatMessage.user_id == user_id,
                )
                .order_by(ChatMessage.created_at)
                .limit(limit)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def get_extracted_fields(self, document_id: str) -> list[ExtractedField]:
        """Get extracted fields for a document (for chat context)."""
        async with AsyncSessionLocal() as session:
            # Get latest extraction ID
            ext_stmt = (
                select(Extraction.id)
                .where(Extraction.document_id == document_id)
                .order_by(Extraction.created_at.desc())
                .limit(1)
            )
            ext_result = await session.execute(ext_stmt)
            ext_row = ext_result.first()

            if not ext_row:
                return []

            extraction_id = ext_row[0]

            stmt = (
                select(ExtractedField)
                .where(ExtractedField.extraction_id == extraction_id)
                .order_by(ExtractedField.page_number)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())
```

### `modules/chat/services.py`

```python
"""
docmind/modules/chat/services.py

Chat business logic — context loading, no DB access.
"""
from docmind.core.logging import get_logger
from docmind.dbase.supabase.storage import get_file_bytes
from docmind.library.cv import convert_to_page_images

logger = get_logger(__name__)


class ChatService:
    """Business logic for chat operations (no DB)."""

    def load_page_images(self, storage_path: str, file_type: str) -> list:
        """Load and convert document to page images for VLM context."""
        file_bytes = get_file_bytes(storage_path)
        return convert_to_page_images(file_bytes, file_type)
```

### `modules/chat/usecase.py`

```python
"""
docmind/modules/chat/usecase.py

Orchestrates chat operations — wires service + repository + pipeline.
"""
import asyncio
import json
from typing import AsyncGenerator

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import Document
from docmind.library.pipeline import run_chat_pipeline
from sqlalchemy import select

from .repositories import ChatRepository
from .schemas import ChatHistoryResponse, ChatMessageResponse, Citation
from .services import ChatService

logger = get_logger(__name__)


class ChatUseCase:
    """Orchestrates the full chat lifecycle."""

    def __init__(self):
        self.repo = ChatRepository()
        self.service = ChatService()

    def send_message(
        self,
        document_id: str,
        user_id: str,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Send a chat message and return an SSE stream."""
        return self._chat_stream(document_id, user_id, message)

    async def _chat_stream(
        self,
        document_id: str,
        user_id: str,
        message: str,
    ) -> AsyncGenerator[str, None]:
        """Internal SSE stream generator for chat."""
        token_queue: asyncio.Queue = asyncio.Queue()

        # Step 1: Persist user message
        self.repo.save_message(document_id, user_id, "user", message)

        # Step 2: Load context
        try:
            page_images, extracted_fields, conversation_history = self._load_context(
                document_id, user_id
            )
        except Exception as e:
            logger.error("Failed to load chat context: %s", e)
            yield f"data: {json.dumps({'type': 'error', 'message': 'Failed to load document context'})}\n\n"
            return

        # Step 3: Set up streaming callback
        def on_stream(type: str, **kwargs) -> None:
            token_queue.put_nowait({"type": type, **kwargs})

        initial_state = {
            "document_id": document_id,
            "user_id": user_id,
            "message": message,
            "page_images": page_images,
            "extracted_fields": extracted_fields,
            "conversation_history": conversation_history,
            "intent": "",
            "intent_confidence": 0.0,
            "relevant_fields": [],
            "re_queried_regions": [],
            "raw_answer": "",
            "answer": "",
            "citations": [],
            "error_message": None,
            "stream_callback": on_stream,
        }

        config = {"configurable": {"thread_id": f"{document_id}:{user_id}"}}
        task = asyncio.create_task(
            asyncio.to_thread(run_chat_pipeline, initial_state, config)
        )

        # Stream events
        while not task.done():
            try:
                event = await asyncio.wait_for(token_queue.get(), timeout=30.0)
                yield f"data: {json.dumps(event)}\n\n"
                if event.get("type") == "done":
                    break
            except asyncio.TimeoutError:
                yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"

        # Drain remaining events
        while not token_queue.empty():
            event = token_queue.get_nowait()
            yield f"data: {json.dumps(event)}\n\n"

        # Step 4: Persist assistant response
        result = task.result()
        answer = result.get("answer", "")
        citations = result.get("citations", [])

        assistant_message_id = self.repo.save_message(
            document_id, user_id, "assistant", answer, citations
        )

        # Final done event with message ID
        yield f"data: {json.dumps({'type': 'done', 'message_id': assistant_message_id})}\n\n"

    async def _load_context(
        self,
        document_id: str,
        user_id: str,
    ) -> tuple[list, list, list[dict]]:
        """Load document context: page images, extracted fields, conversation history."""
        # Load document metadata via SQLAlchemy
        async with AsyncSessionLocal() as session:
            stmt = select(Document).where(Document.id == document_id)
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()

        if not doc:
            raise ValueError(f"Document not found: {document_id}")

        # Load page images from Supabase Storage
        page_images = self.service.load_page_images(
            doc.storage_path, doc.file_type
        )

        # Load extracted fields
        extracted_fields = await self.repo.get_extracted_fields(document_id)

        # Load conversation history
        history_msgs = await self.repo.get_recent_messages(document_id, user_id)
        conversation_history = [
            {"role": msg.role, "content": msg.content}
            for msg in history_msgs
        ]

        return page_images, extracted_fields, conversation_history

    def get_history(
        self,
        document_id: str,
        user_id: str,
        page: int,
        limit: int,
    ) -> ChatHistoryResponse:
        """Get paginated chat history for a document."""
        items, total = self.repo.get_history(document_id, user_id, page, limit)

        return ChatHistoryResponse(
            items=[
                ChatMessageResponse(
                    id=row["id"],
                    role=row["role"],
                    content=row["content"],
                    citations=json.loads(row["citations"]) if isinstance(row["citations"], str) else row["citations"],
                    created_at=row["created_at"],
                )
                for row in items
            ],
            total=total,
            page=page,
            limit=limit,
        )
```

---

## Health Module

### `modules/health/usecase.py`

```python
"""
docmind/modules/health/usecase.py

Health check orchestration.
"""
import time

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.library.providers import get_vlm_provider
from sqlalchemy import text

from .schemas import ComponentHealth

logger = get_logger(__name__)

_start_time = time.time()


class HealthUseCase:
    """Orchestrates health checks."""

    async def get_basic_health(self) -> tuple[str, list[ComponentHealth], float]:
        """
        Check all components and return overall status.

        Returns:
            Tuple of (overall_status, components, uptime_seconds).
        """
        components = []

        # Check Database (Supabase Postgres via SQLAlchemy)
        try:
            t0 = time.time()
            async with AsyncSessionLocal() as session:
                await session.execute(text("SELECT 1"))
            ms = (time.time() - t0) * 1000
            components.append(ComponentHealth(
                name="database",
                status="healthy",
                message="Connected",
                response_time_ms=round(ms, 1),
            ))
        except Exception as e:
            components.append(ComponentHealth(
                name="database",
                status="unhealthy",
                message=str(e),
            ))

        # Check VLM provider
        try:
            provider = get_vlm_provider()
            components.append(ComponentHealth(
                name="vlm_provider",
                status="healthy",
                message=f"{provider.provider_name} ({provider.model_name})",
            ))
        except Exception as e:
            components.append(ComponentHealth(
                name="vlm_provider",
                status="unhealthy",
                message=str(e),
            ))

        overall = "healthy" if all(c.status == "healthy" for c in components) else "degraded"
        uptime = time.time() - _start_time

        return overall, components, uptime
```

---

## Shared Exceptions — `shared/exceptions.py`

```python
"""
docmind/shared/exceptions.py

Shared exception types used across modules.
"""


class ServiceException(Exception):
    """Raised by service layer for business logic errors."""
    pass


class RepositoryException(Exception):
    """Raised by repository layer for database errors."""
    pass
```

---

## Projects Module

### `modules/projects/repositories.py`

```python
"""
docmind/modules/projects/repositories.py

Project database operations via SQLAlchemy.
"""
from datetime import datetime, timezone

from sqlalchemy import delete as sa_delete
from sqlalchemy import func, select, update

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import (
    Document,
    PageChunk,
    Project,
    ProjectConversation,
    ProjectMessage,
)

logger = get_logger(__name__)


class ProjectRepository:
    """Repository for project CRUD operations via SQLAlchemy."""

    async def create(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        persona_id: str | None = None,
    ) -> Project:
        """Insert a new project record. Returns the created ORM instance."""
        async with AsyncSessionLocal() as session:
            project = Project(
                user_id=user_id,
                name=name,
                description=description,
                persona_id=persona_id,
            )
            session.add(project)
            await session.commit()
            await session.refresh(project)
            return project

    async def get_by_id(self, project_id: str, user_id: str) -> Project | None:
        """Get a single project by ID, scoped to user."""
        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def list_for_user(
        self,
        user_id: str,
        page: int,
        limit: int,
    ) -> tuple[list[Project], int]:
        """Get paginated projects for a user. Returns (items, total_count)."""
        offset = (page - 1) * limit
        async with AsyncSessionLocal() as session:
            count_stmt = select(func.count()).select_from(Project).where(
                Project.user_id == user_id
            )
            total = (await session.execute(count_stmt)).scalar() or 0

            stmt = (
                select(Project)
                .where(Project.user_id == user_id)
                .order_by(Project.updated_at.desc())
                .offset(offset)
                .limit(limit)
            )
            result = await session.execute(stmt)
            items = list(result.scalars().all())
            return items, total

    async def update(
        self,
        project_id: str,
        user_id: str,
        **kwargs,
    ) -> Project | None:
        """Update project fields. Returns updated instance or None."""
        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()
            if project is None:
                return None

            for key, value in kwargs.items():
                setattr(project, key, value)
            project.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(project)
            return project

    async def delete(self, project_id: str, user_id: str) -> bool:
        """Delete a project and cascade: docs association, chunks, conversations, messages."""
        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                Project.id == project_id,
                Project.user_id == user_id,
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()
            if project is None:
                return False

            # Delete page chunks for project documents
            await session.execute(
                sa_delete(PageChunk).where(PageChunk.project_id == project_id)
            )

            # Delete conversation messages, then conversations
            conv_stmt = select(ProjectConversation.id).where(
                ProjectConversation.project_id == project_id
            )
            conv_result = await session.execute(conv_stmt)
            conv_ids = [row[0] for row in conv_result.all()]
            if conv_ids:
                await session.execute(
                    sa_delete(ProjectMessage).where(
                        ProjectMessage.conversation_id.in_(conv_ids)
                    )
                )
            await session.execute(
                sa_delete(ProjectConversation).where(
                    ProjectConversation.project_id == project_id
                )
            )

            await session.delete(project)
            await session.commit()
            return True

    async def add_document(self, project_id: str, document_id: str) -> None:
        """Associate a document with a project (via project_id FK on Document)."""
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(project_id=project_id)
            )
            await session.execute(stmt)
            await session.commit()

    async def remove_document(self, project_id: str, document_id: str) -> bool:
        """Remove document association and delete its chunks."""
        async with AsyncSessionLocal() as session:
            stmt = select(Document).where(
                Document.id == document_id,
                Document.project_id == project_id,
            )
            result = await session.execute(stmt)
            doc = result.scalar_one_or_none()
            if doc is None:
                return False

            # Delete chunks for this document in this project
            await session.execute(
                sa_delete(PageChunk).where(
                    PageChunk.document_id == document_id,
                    PageChunk.project_id == project_id,
                )
            )

            # Clear project association
            doc.project_id = None
            await session.commit()
            return True
```

### `modules/projects/services.py`

```python
"""
docmind/modules/projects/services.py

Project business logic — validates project names, orchestrates RAG indexing.
"""
from docmind.core.logging import get_logger
from docmind.library.rag import index_document_for_rag
from docmind.shared.exceptions import ServiceException

logger = get_logger(__name__)


class ProjectService:
    """Business logic for project operations (no DB)."""

    @staticmethod
    def validate_project_name(name: str) -> str:
        """Validate and normalize project name."""
        name = name.strip()
        if not name:
            raise ServiceException("Project name cannot be empty")
        if len(name) > 255:
            raise ServiceException("Project name too long")
        return name

    async def index_document(
        self,
        project_id: str,
        document_id: str,
        storage_path: str,
        file_type: str,
    ) -> int:
        """
        Index a document for RAG retrieval.

        Orchestrates: text extraction → chunking → embedding → storage.
        Returns the number of chunks created.
        """
        return await index_document_for_rag(
            project_id=project_id,
            document_id=document_id,
            storage_path=storage_path,
            file_type=file_type,
        )
```

### `modules/projects/usecase.py`

```python
"""
docmind/modules/projects/usecase.py

Orchestrates project operations — wires service + repository + RAG pipeline.
"""
from docmind.core.logging import get_logger

from .repositories import ProjectRepository
from .services import ProjectService

logger = get_logger(__name__)


class ProjectUseCase:
    """Orchestrates the full project lifecycle."""

    def __init__(self):
        self.repo = ProjectRepository()
        self.service = ProjectService()

    # Project CRUD methods: create_project, get_project, list_projects,
    # update_project, delete_project

    # Document management: add_document (creates doc + triggers RAG indexing),
    # list_documents, remove_document (removes doc + deletes chunks)

    # Chat: send_message (retrieves relevant chunks via RAG retriever,
    # builds prompt with persona system prompt, streams VLM response,
    # persists conversation + messages)

    # Conversations: list_conversations, get_conversation, delete_conversation
```

---

## Personas Module

Personas are thin CRUD — no service layer needed, repository handles everything directly.

### `modules/personas/repositories.py`

```python
"""
docmind/modules/personas/repositories.py

Persona database operations via SQLAlchemy.
"""
from sqlalchemy import delete as sa_delete, select

from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models import Persona

logger = get_logger(__name__)


class PersonaRepository:
    """Repository for persona CRUD operations via SQLAlchemy."""

    async def list_for_user(self, user_id: str) -> list[Persona]:
        """List all personas: built-in defaults + user's custom personas."""
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Persona)
                .where(
                    (Persona.user_id == user_id) | (Persona.is_default == True)
                )
                .order_by(Persona.is_default.desc(), Persona.name)
            )
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def create(self, user_id: str, data) -> Persona:
        """Create a custom persona."""
        async with AsyncSessionLocal() as session:
            persona = Persona(
                user_id=user_id,
                name=data.name,
                system_prompt=data.system_prompt,
                description=data.description,
                is_default=False,
            )
            session.add(persona)
            await session.commit()
            await session.refresh(persona)
            return persona

    async def update(self, user_id: str, persona_id: str, data) -> Persona | None:
        """Update a custom persona. Cannot update built-in defaults."""
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(
                Persona.id == persona_id,
                Persona.user_id == user_id,
                Persona.is_default == False,
            )
            result = await session.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona is None:
                return None

            if data.name is not None:
                persona.name = data.name
            if data.system_prompt is not None:
                persona.system_prompt = data.system_prompt
            if data.description is not None:
                persona.description = data.description

            await session.commit()
            await session.refresh(persona)
            return persona

    async def delete(self, user_id: str, persona_id: str) -> bool:
        """Delete a custom persona. Cannot delete built-in defaults."""
        async with AsyncSessionLocal() as session:
            stmt = select(Persona).where(
                Persona.id == persona_id,
                Persona.user_id == user_id,
                Persona.is_default == False,
            )
            result = await session.execute(stmt)
            persona = result.scalar_one_or_none()
            if persona is None:
                return False

            await session.delete(persona)
            await session.commit()
            return True
```

---

## RAG Library

Files: `backend/src/docmind/library/rag/`

The RAG library provides reusable functions for indexing documents into vector-searchable chunks and retrieving relevant context at query time. It is used by the Projects module but lives in `library/` because it has no database-layer dependency (chunk storage is handled by the caller via repository).

### `library/rag/text_extract.py`

```python
"""
docmind/library/rag/text_extract.py

Extract plain text from documents for RAG chunking.
"""

def extract_text_from_pdf(file_bytes: bytes) -> list[tuple[int, str]]:
    """
    Extract text from a PDF file.

    Returns:
        List of (page_number, page_text) tuples.
        Page numbers are 1-indexed.
    """
    ...

def extract_text_from_image(file_bytes: bytes) -> str:
    """
    Extract text from an image file using OCR (via VLM provider).

    Returns:
        Extracted text content.
    """
    ...
```

### `library/rag/chunker.py`

```python
"""
docmind/library/rag/chunker.py

Split text into overlapping chunks for embedding.
Uses recursive character splitting with configurable size and overlap.
"""

def chunk_text(
    text: str,
    chunk_size: int = 512,
    chunk_overlap: int = 64,
) -> list[str]:
    """
    Split text into overlapping chunks.

    Args:
        text: Input text to chunk.
        chunk_size: Maximum characters per chunk (from RAG_CHUNK_SIZE setting).
        chunk_overlap: Overlap between consecutive chunks (from RAG_CHUNK_OVERLAP setting).

    Returns:
        List of text chunks.
    """
    ...
```

### `library/rag/embedder.py`

```python
"""
docmind/library/rag/embedder.py

Embedding provider abstraction for RAG.
"""
from typing import Protocol


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of texts. Returns list of embedding vectors."""
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Embed a single query. Returns embedding vector."""
        ...


class DashScopeEmbedder:
    """DashScope text-embedding-v3 implementation."""

    def __init__(self, api_key: str, model: str, dimensions: int):
        ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        ...

    async def embed_query(self, query: str) -> list[float]:
        ...


def get_embedder() -> EmbeddingProvider:
    """
    Factory: create embedder from settings.

    Reads EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_DIMENSIONS from config.
    Currently supports: dashscope.
    """
    ...
```

### `library/rag/retriever.py`

```python
"""
docmind/library/rag/retriever.py

Retrieve relevant chunks for a query using cosine similarity.
"""

async def retrieve_chunks(
    query: str,
    project_id: str,
    top_k: int = 8,
    similarity_threshold: float = 0.3,
) -> list[dict]:
    """
    Retrieve the most relevant chunks for a query within a project.

    Args:
        query: User's question.
        project_id: Project to search within.
        top_k: Maximum number of chunks to return (from RAG_TOP_K setting).
        similarity_threshold: Minimum cosine similarity (from RAG_SIMILARITY_THRESHOLD setting).

    Returns:
        List of dicts: [{chunk_text, document_id, page_number, similarity_score}]
        Sorted by similarity_score descending.
    """
    ...
```

### `library/rag/indexer.py`

```python
"""
docmind/library/rag/indexer.py

Orchestrates the full RAG indexing pipeline for a document:
    text extraction → chunking → embedding → storage.
"""

async def index_document_for_rag(
    project_id: str,
    document_id: str,
    storage_path: str,
    file_type: str,
) -> int:
    """
    Index a document for RAG retrieval.

    Pipeline:
        1. Download file bytes from Supabase Storage
        2. Extract text (PDF → per-page text, image → OCR text)
        3. Chunk text with overlap
        4. Generate embeddings via configured provider
        5. Store chunks + embeddings in page_chunks table

    Args:
        project_id: Project this document belongs to.
        document_id: Document ID.
        storage_path: Supabase Storage path.
        file_type: File type (pdf, png, jpg, etc.).

    Returns:
        Number of chunks created and stored.
    """
    ...
```

---

## Rules

- **Services never import from `docmind/modules/{other_module}/`**. Cross-module coordination happens at the usecase level or through `shared/`.
- **Repositories use SQLAlchemy async sessions** — all database queries go through `AsyncSessionLocal()`. Supabase client is only for Auth + Storage.
- **UseCase is the orchestration layer** — it wires service (library calls) + repository (DB) + pipeline (LangGraph). Handlers create UseCase instances and delegate.
- **Services contain business logic but NO database access**. They call `library/` functions and `dbase/supabase/storage.py` helpers.
- **Repositories contain database queries but NO business logic**. They return ORM model instances. Mapping to Pydantic schemas happens in the UseCase.
- **Cascading deletes are explicit**: `DocumentRepository.delete()` manually deletes all associated records in FK order rather than relying on database cascades, for portability and clarity.
- **Chat context loading is eager**: `_load_context` loads page images, extracted fields, and history in one call. This is acceptable because chat is already a heavy operation (VLM call).
- **Conversation history is capped at 20 messages** when loading context for the chat pipeline.
- **SSE heartbeats every 30 seconds** prevent proxy/load balancer timeouts on long-running operations.
- **Error states in processing** trigger a document status update to "error" so the frontend can display the failure.
