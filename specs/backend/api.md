# Backend Spec: API Layer

Files: `backend/src/docmind/main.py`, `backend/src/docmind/router.py`

See also: [[projects/docmind-vlm/specs/backend/services]]

---

## Responsibility

| File | Does |
|------|------|
| `docmind/main.py` | App factory (`create_app()`) — creates FastAPI app, registers CORS, mounts aggregated router |
| `docmind/router.py` | Aggregates module routers under `/api/v1/{module}` |
| `docmind/modules/{module}/apiv1/handler.py` | Per-module endpoint definitions |
| `docmind/modules/{module}/schemas.py` | Per-module Pydantic request/response models |
| `docmind/core/config.py` | `Settings` (pydantic-settings) + `get_settings()` with `lru_cache` |
| `docmind/core/auth.py` | Supabase JWT verification — `get_current_user` dependency |
| `docmind/core/dependencies.py` | `get_current_user()`, `get_supabase_client()` |
| `docmind/core/logging.py` | structlog setup via `setup_logging()`, `get_logger(__name__)` |
| `docmind/dbase/supabase/client.py` | Supabase client init (Auth + Storage only) |
| `docmind/dbase/supabase/storage.py` | File upload/download/signed-URL helpers |
| `docmind/dbase/psql/core/engine.py` | Async SQLAlchemy engine + session factory |
| `docmind/dbase/psql/models/` | ORM models (Document, Extraction, etc.) |

The API layer is **thin**: validate -> delegate to `usecase` -> serialize response. No business logic in handlers.

---

## `main.py`

```python
"""
docmind/main.py

FastAPI app factory. Configures CORS, registers routers, manages lifecycle.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .core.config import get_settings
from .core.logging import setup_logging
from .router import api_router

logger = logging.getLogger(__name__)


def get_docs_path():
    """Get docs path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/docs"
    return None


def get_redoc_path():
    """Get redoc path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/redoc"
    return None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=get_docs_path(),
        redoc_url=get_redoc_path(),
        debug=settings.APP_DEBUG,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
```

**Rules:**
- Settings loaded via `get_settings()` (cached with `lru_cache`) — never import a global `settings` object directly
- CORS origins come from `settings.allowed_origins` — never hardcode URLs
- Router prefix is `/api`; version prefix `/v1` is added by the aggregating router
- Swagger docs (`/docs`, `/redoc`) are disabled in production via `get_docs_path()` / `get_redoc_path()`
- No business logic in `main.py`
- Default port is **8000** (configured via `APP_PORT`)

---

## `router.py` — Route Aggregator

```python
"""
docmind/router.py

Aggregates all module routers under versioned prefixes.
"""
from fastapi import APIRouter

from .modules.health.apiv1.handler import router as health_router
from .modules.documents.apiv1.handler import router as documents_router
from .modules.extractions.apiv1.handler import router as extractions_router
from .modules.chat.apiv1.handler import router as chat_router
from .modules.templates.apiv1.handler import router as templates_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/v1/health", tags=["Health"])
api_router.include_router(documents_router, prefix="/v1/documents", tags=["Documents"])
api_router.include_router(extractions_router, prefix="/v1/extractions", tags=["Extractions"])
api_router.include_router(chat_router, prefix="/v1/chat", tags=["Chat"])
api_router.include_router(templates_router, prefix="/v1/templates", tags=["Templates"])
```

There is **no monolithic router** with all endpoints. Each module owns its own `apiv1/handler.py`. The aggregating `router.py` only wires them together.

---

## Endpoint Summary

| Method | Full Path | Module | Auth | Handler |
|--------|-----------|--------|------|---------|
| `GET` | `/api/v1/health/ping` | health | None | `modules/health/apiv1/handler.py` |
| `GET` | `/api/v1/health/status` | health | None | `modules/health/apiv1/handler.py` |
| `POST` | `/api/v1/documents` | documents | JWT | `modules/documents/apiv1/handler.py` |
| `GET` | `/api/v1/documents` | documents | JWT | `modules/documents/apiv1/handler.py` |
| `GET` | `/api/v1/documents/{id}` | documents | JWT | `modules/documents/apiv1/handler.py` |
| `DELETE` | `/api/v1/documents/{id}` | documents | JWT | `modules/documents/apiv1/handler.py` |
| `POST` | `/api/v1/documents/{id}/process` | documents | JWT | `modules/documents/apiv1/handler.py` |
| `GET` | `/api/v1/extractions/{document_id}` | extractions | JWT | `modules/extractions/apiv1/handler.py` |
| `GET` | `/api/v1/extractions/{document_id}/audit` | extractions | JWT | `modules/extractions/apiv1/handler.py` |
| `GET` | `/api/v1/extractions/{document_id}/overlay` | extractions | JWT | `modules/extractions/apiv1/handler.py` |
| `GET` | `/api/v1/extractions/{document_id}/comparison` | extractions | JWT | `modules/extractions/apiv1/handler.py` |
| `POST` | `/api/v1/chat/{document_id}` | chat | JWT | `modules/chat/apiv1/handler.py` |
| `GET` | `/api/v1/chat/{document_id}/history` | chat | JWT | `modules/chat/apiv1/handler.py` |
| `GET` | `/api/v1/templates` | templates | JWT | `modules/templates/apiv1/handler.py` |

---

## Pydantic Models

Models live in each module's `schemas.py` file, not in the router.

### Health Module — `modules/health/schemas.py`

```python
class PingResponse(BaseModel):
    status: str
    timestamp: datetime
    message: str

class ComponentHealth(BaseModel):
    name: str
    status: str                          # "healthy" | "unhealthy"
    message: str | None = None
    response_time_ms: float | None = None

class HealthStatusResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str
    components: list[ComponentHealth]
    uptime_seconds: float
```

### Documents Module — `modules/documents/schemas.py`

```python
class DocumentCreate(BaseModel):
    """Request body for creating a document record after upload."""
    filename: str = Field(..., min_length=1, max_length=255)
    file_type: str = Field(..., pattern="^(pdf|png|jpg|jpeg|tiff|webp)$")
    file_size: int = Field(..., gt=0, le=20_971_520)  # 20MB max
    storage_path: str

class DocumentResponse(BaseModel):
    """Single document in API responses."""
    id: str  # UUID
    filename: str
    file_type: str
    file_size: int
    status: str  # uploaded, processing, ready, error
    document_type: str | None
    page_count: int
    created_at: datetime
    updated_at: datetime

class DocumentListResponse(BaseModel):
    """Paginated list of documents."""
    items: list[DocumentResponse]
    total: int
    page: int
    limit: int

class ProcessRequest(BaseModel):
    """Request body for triggering document processing."""
    template_type: str | None = None
```

### Extractions Module — `modules/extractions/schemas.py`

```python
class ExtractedFieldResponse(BaseModel):
    """Single extracted field with confidence and spatial data."""
    id: str
    field_type: str  # key_value, table_cell, entity, text_block
    field_key: str | None
    field_value: str
    page_number: int
    bounding_box: dict  # {x, y, width, height}
    confidence: float = Field(..., ge=0.0, le=1.0)
    vlm_confidence: float
    cv_quality_score: float
    is_required: bool
    is_missing: bool

class ExtractionResponse(BaseModel):
    """Complete extraction result for a document."""
    id: str
    document_id: str
    mode: str  # general, template
    template_type: str | None
    fields: list[ExtractedFieldResponse]
    processing_time_ms: int
    created_at: datetime

class AuditEntryResponse(BaseModel):
    """Single audit trail entry from the processing pipeline."""
    step_name: str
    step_order: int
    input_summary: dict
    output_summary: dict
    parameters: dict
    duration_ms: int

class OverlayRegion(BaseModel):
    """Bounding box region for document overlay visualization."""
    x: float
    y: float
    width: float
    height: float
    confidence: float
    color: str  # hex color, e.g. "#22c55e"
    tooltip: str | None

class ComparisonResponse(BaseModel):
    """Side-by-side comparison of enhanced vs raw extraction."""
    enhanced_fields: list[ExtractedFieldResponse]
    raw_fields: list[dict]
    corrected: list[str]  # field IDs corrected by pipeline
    added: list[str]  # field IDs added by pipeline
```

### Chat Module — `modules/chat/schemas.py`

```python
class ChatMessageRequest(BaseModel):
    """Request body for sending a chat message."""
    message: str = Field(..., min_length=1)

class Citation(BaseModel):
    """Citation linking a chat response to a document region."""
    page: int
    bounding_box: dict
    text_span: str

class ChatMessageResponse(BaseModel):
    """Single chat message in API responses."""
    id: str
    role: str  # user, assistant
    content: str
    citations: list[Citation]
    created_at: datetime

class ChatHistoryResponse(BaseModel):
    """Paginated chat history."""
    items: list[ChatMessageResponse]
    total: int
    page: int
    limit: int
```

### Templates Module — `modules/templates/schemas.py`

```python
class TemplateResponse(BaseModel):
    """Document template definition."""
    type: str
    name: str
    description: str
    required_fields: list[str]
    optional_fields: list[str]

class TemplateListResponse(BaseModel):
    """List of available templates."""
    items: list[TemplateResponse]
```

**Model Rules:**
- Use `Field(..., min_length=1)` for required non-empty strings
- Use `Field(default_factory=dict)` for optional dict fields (not `{}` as default)
- `file_type` validated by regex pattern — only allowed document formats
- `file_size` capped at 20MB (`20_971_520` bytes)
- `confidence` always bounded `[0.0, 1.0]`
- `status` is a string enum in practice: `uploaded`, `processing`, `ready`, `error`

---

## Module Handlers

Each module follows the pattern: handler imports a `UseCase` class, instantiates it (injecting dependencies via `Depends` where needed), and delegates all logic.

### Health Handler — `modules/health/apiv1/handler.py`

```python
from docmind.core.config import get_settings
from docmind.core.logging import get_logger

from ..schemas import HealthStatusResponse, PingResponse
from ..usecase import HealthUseCase

router = APIRouter()
_health_usecase = HealthUseCase()

@router.get("/ping", response_model=PingResponse)
async def ping():
    return PingResponse(status="ok", timestamp=datetime.now(UTC), message="pong")

@router.get("/status", response_model=HealthStatusResponse)
async def get_health_status():
    usecase = HealthUseCase()
    overall_status, components, uptime = usecase.get_basic_health()
    return HealthStatusResponse(
        status=overall_status,
        timestamp=datetime.now(UTC),
        version=get_settings().APP_VERSION,
        components=components,
        uptime_seconds=uptime,
    )
```

### Documents Handler — `modules/documents/apiv1/handler.py`

```python
from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..schemas import (
    DocumentCreate,
    DocumentListResponse,
    DocumentResponse,
    ProcessRequest,
)
from ..usecase import DocumentUseCase

logger = get_logger(__name__)
router = APIRouter()

@router.post("", response_model=DocumentResponse, status_code=201)
async def create_document(
    body: DocumentCreate,
    current_user: dict = Depends(get_current_user),
):
    usecase = DocumentUseCase()
    return usecase.create_document(
        user_id=current_user["id"],
        filename=body.filename,
        file_type=body.file_type,
        file_size=body.file_size,
        storage_path=body.storage_path,
    )

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    usecase = DocumentUseCase()
    return usecase.get_documents(
        user_id=current_user["id"],
        page=page,
        limit=limit,
    )

@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = DocumentUseCase()
    document = usecase.get_document(
        user_id=current_user["id"],
        document_id=document_id,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@router.delete("/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = DocumentUseCase()
    deleted = usecase.delete_document(
        user_id=current_user["id"],
        document_id=document_id,
    )
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")

@router.post("/{document_id}/process")
async def process_document(
    document_id: str,
    body: ProcessRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Trigger document processing pipeline.

    Returns an SSE stream with progress updates:
        data: {"step": "preprocess", "progress": 25, "message": "Deskewing..."}
        data: {"step": "extract", "progress": 50, "message": "Running VLM..."}
        data: {"step": "postprocess", "progress": 75, "message": "Validating..."}
        data: {"step": "complete", "progress": 100, "message": "Done"}
    """
    usecase = DocumentUseCase()
    document = usecase.get_document(
        user_id=current_user["id"],
        document_id=document_id,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    event_stream = usecase.trigger_processing(
        document_id=document_id,
        template_type=body.template_type,
    )

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
```

### Extractions Handler — `modules/extractions/apiv1/handler.py`

```python
from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..schemas import (
    AuditEntryResponse,
    ComparisonResponse,
    ExtractionResponse,
    OverlayRegion,
)
from ..usecase import ExtractionUseCase

logger = get_logger(__name__)
router = APIRouter()

@router.get("/{document_id}", response_model=ExtractionResponse)
async def get_extraction(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ExtractionUseCase()
    extraction = usecase.get_extraction(document_id=document_id)
    if extraction is None:
        raise HTTPException(status_code=404, detail="Extraction not found")
    return extraction

@router.get("/{document_id}/audit", response_model=list[AuditEntryResponse])
async def get_audit_trail(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ExtractionUseCase()
    return usecase.get_audit_trail(document_id=document_id)

@router.get("/{document_id}/overlay", response_model=list[OverlayRegion])
async def get_overlay_data(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Get bounding box overlay data for document visualization.

    Colors are assigned by confidence level:
    - Green (#22c55e): confidence >= 0.8
    - Yellow (#eab308): confidence >= 0.5
    - Red (#ef4444): confidence < 0.5
    """
    usecase = ExtractionUseCase()
    return usecase.get_overlay_data(document_id=document_id)

@router.get("/{document_id}/comparison", response_model=ComparisonResponse)
async def get_comparison(
    document_id: str,
    current_user: dict = Depends(get_current_user),
):
    usecase = ExtractionUseCase()
    comparison = usecase.get_comparison(document_id=document_id)
    if comparison is None:
        raise HTTPException(status_code=404, detail="Comparison not available")
    return comparison
```

### Chat Handler — `modules/chat/apiv1/handler.py`

```python
from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.modules.documents.usecase import DocumentUseCase

from ..schemas import ChatHistoryResponse, ChatMessageRequest
from ..usecase import ChatUseCase

logger = get_logger(__name__)
router = APIRouter()

@router.post("/{document_id}")
async def send_message(
    document_id: str,
    body: ChatMessageRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Send a chat message about a document.

    Returns an SSE stream with the assistant response:
        data: {"type": "token", "content": "The"}
        data: {"type": "token", "content": " invoice"}
        data: {"type": "citation", "citation": {"page": 1, "bounding_box": {...}, "text_span": "..."}}
        data: {"type": "done", "message_id": "uuid"}
    """
    doc_usecase = DocumentUseCase()
    document = doc_usecase.get_document(
        user_id=current_user["id"],
        document_id=document_id,
    )
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if document.status != "ready":
        raise HTTPException(
            status_code=400,
            detail="Document must be processed before chatting",
        )

    chat_usecase = ChatUseCase()
    event_stream = chat_usecase.send_message(
        document_id=document_id,
        user_id=current_user["id"],
        message=body.message,
    )

    return StreamingResponse(
        event_stream,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

@router.get("/{document_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    document_id: str,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=50, ge=1, le=100),
    current_user: dict = Depends(get_current_user),
):
    chat_usecase = ChatUseCase()
    return chat_usecase.get_history(
        document_id=document_id,
        user_id=current_user["id"],
        page=page,
        limit=limit,
    )
```

### Templates Handler — `modules/templates/apiv1/handler.py`

```python
from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger

from ..schemas import TemplateListResponse, TemplateResponse

logger = get_logger(__name__)
router = APIRouter()

TEMPLATES = [
    TemplateResponse(
        type="invoice",
        name="Invoice",
        description="Commercial invoices with line items, totals, and vendor info",
        required_fields=["invoice_number", "date", "total_amount", "vendor_name"],
        optional_fields=["due_date", "tax_amount", "line_items", "purchase_order"],
    ),
    TemplateResponse(
        type="receipt",
        name="Receipt",
        description="Purchase receipts with itemized costs",
        required_fields=["date", "total_amount", "merchant_name"],
        optional_fields=["tax_amount", "payment_method", "line_items"],
    ),
    TemplateResponse(
        type="medical_report",
        name="Medical Report",
        description="Medical lab reports and diagnostic documents",
        required_fields=["patient_name", "report_date", "report_type"],
        optional_fields=["doctor_name", "diagnosis", "test_results", "facility"],
    ),
    TemplateResponse(
        type="contract",
        name="Contract",
        description="Legal contracts and agreements",
        required_fields=["parties", "effective_date", "contract_type"],
        optional_fields=["expiry_date", "terms", "signatures", "governing_law"],
    ),
    TemplateResponse(
        type="id_document",
        name="ID Document",
        description="Government-issued identification documents",
        required_fields=["full_name", "document_number", "date_of_birth"],
        optional_fields=["expiry_date", "nationality", "address", "issuing_authority"],
    ),
]

@router.get("", response_model=TemplateListResponse)
async def list_templates(
    current_user: dict = Depends(get_current_user),
):
    """List all available document templates."""
    return TemplateListResponse(items=TEMPLATES)
```

---

## SSE Streaming Pattern

Both processing and chat endpoints use Server-Sent Events. The generator pattern:

```python
import json
from typing import AsyncGenerator


async def sse_event(data: dict) -> str:
    """Format a dict as an SSE event string."""
    return f"data: {json.dumps(data)}\n\n"


async def processing_stream(document_id: str) -> AsyncGenerator[str, None]:
    """
    Example SSE stream for document processing.

    Yields:
        data: {"step": "preprocess", "progress": 25, "message": "..."}
        data: {"step": "extract", "progress": 50, "message": "..."}
        ...
        data: {"step": "complete", "progress": 100, "message": "Done"}
    """
    yield await sse_event({"step": "preprocess", "progress": 0, "message": "Starting..."})
    # ... pipeline runs ...
    yield await sse_event({"step": "complete", "progress": 100, "message": "Done"})
```

---

## Authentication — `core/auth.py`

```python
"""
docmind/core/auth.py

Supabase JWT verification dependency.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate Supabase JWT token and return user payload.

    Returns:
        dict with at minimum: {"id": str, "email": str}

    Raises:
        HTTPException 401 if token is missing or invalid
        HTTPException 403 if token is valid but user lacks access
    """
    token = credentials.credentials
    try:
        payload = decode_jwt(token)  # implementation depends on Supabase JWT secret
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload
```

Use as a dependency: `Depends(get_current_user)`.

---

## Dependency Injection — `core/dependencies.py`

```python
"""
docmind/core/dependencies.py

FastAPI dependency functions for auth and database clients.
"""
from docmind.core.auth import get_current_user  # re-export
from docmind.dbase.psql.core.session import get_async_db_session  # re-export
from docmind.dbase.supabase.client import get_supabase_client  # re-export (Auth + Storage)
```

Handlers inject dependencies via `Depends(get_current_user)` and `Depends(get_async_db_session)`.

---

## `dbase/supabase/client.py`

```python
"""
docmind/dbase/supabase/client.py

Supabase client initialization and singleton.
Used for Auth (JWT verification) and Storage (file upload/download) ONLY.
All database queries go through SQLAlchemy (dbase/psql/).
"""
from supabase import create_client, Client

from docmind.core.config import get_settings
from docmind.core.logging import get_logger

logger = get_logger(__name__)

_supabase_client: Client | None = None


def get_supabase_client() -> Client:
    """Get or create Supabase client singleton (Auth + Storage only)."""
    global _supabase_client
    if _supabase_client is None:
        settings = get_settings()
        _supabase_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
        logger.info("Supabase client initialized", url=settings.SUPABASE_URL)
    return _supabase_client
```

## `dbase/psql/core/engine.py`

```python
"""
docmind/dbase/psql/core/engine.py

Async SQLAlchemy engine.
Connects to Supabase Postgres via DATABASE_URL.
"""
from sqlalchemy.ext.asyncio import create_async_engine

from docmind.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.DATABASE_URL, echo=settings.APP_DEBUG)
```

---

## `dbase/psql/core/session.py`

```python
"""
docmind/dbase/psql/core/session.py

Async session factory and FastAPI dependency.
"""
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from docmind.dbase.psql.core.engine import engine

AsyncSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async session."""
    async with AsyncSessionLocal() as session:
        yield session
```

---

## `dbase/psql/core/base.py`

```python
"""
docmind/dbase/psql/core/base.py

SQLAlchemy declarative base. All ORM models inherit from Base.
"""
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

---

## `dbase/psql/models/`

All models use `uuid4` primary keys and define `__tablename__` explicitly.
`user_id` is stored as a plain `String` (Supabase Auth UUID — no FK to an `auth.users` ORM model).

```python
"""
docmind/dbase/psql/models/

ORM models for DocMind-VLM.
All tables are owned per-user; every query MUST filter by user_id.
"""
import uuid
from datetime import datetime, UTC

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(UTC)


# ─────────────────────────────────────────────
# Document
# ─────────────────────────────────────────────

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)       # pdf|png|jpg|jpeg|tiff|webp
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)           # bytes
    storage_path: Mapped[str] = mapped_column(String(512), nullable=False)   # Supabase Storage path
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="uploaded")  # uploaded|processing|ready|error
    document_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    page_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    extractions: Mapped[list["Extraction"]] = relationship(back_populates="document", cascade="all, delete-orphan")
    chat_messages: Mapped[list["ChatMessage"]] = relationship(back_populates="document", cascade="all, delete-orphan")


# ─────────────────────────────────────────────
# Extraction
# ─────────────────────────────────────────────

class Extraction(Base):
    __tablename__ = "extractions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    mode: Mapped[str] = mapped_column(String(20), nullable=False, default="general")  # general|template
    template_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    processing_time_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    document: Mapped["Document"] = relationship(back_populates="extractions")
    fields: Mapped[list["ExtractedField"]] = relationship(back_populates="extraction", cascade="all, delete-orphan")
    audit_entries: Mapped[list["AuditEntry"]] = relationship(back_populates="extraction", cascade="all, delete-orphan")


class ExtractedField(Base):
    __tablename__ = "extracted_fields"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    extraction_id: Mapped[str] = mapped_column(String(36), ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    field_type: Mapped[str] = mapped_column(String(30), nullable=False)       # key_value|table_cell|entity|text_block
    field_key: Mapped[str | None] = mapped_column(String(100), nullable=True)
    field_value: Mapped[str] = mapped_column(Text, nullable=False)
    page_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # {x, y, width, height}
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    vlm_confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    cv_quality_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    is_missing: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    extraction: Mapped["Extraction"] = relationship(back_populates="fields")


class AuditEntry(Base):
    __tablename__ = "audit_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    extraction_id: Mapped[str] = mapped_column(String(36), ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True)
    step_name: Mapped[str] = mapped_column(String(50), nullable=False)
    step_order: Mapped[int] = mapped_column(Integer, nullable=False)
    input_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    output_summary: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    parameters: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    duration_ms: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    extraction: Mapped["Extraction"] = relationship(back_populates="audit_entries")


# ─────────────────────────────────────────────
# Chat
# ─────────────────────────────────────────────

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)             # user|assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)

    document: Mapped["Document"] = relationship(back_populates="chat_messages")
    citations: Mapped[list["Citation"]] = relationship(back_populates="message", cascade="all, delete-orphan")


class Citation(Base):
    __tablename__ = "citations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)  # {x, y, width, height}
    text_span: Mapped[str] = mapped_column(Text, nullable=False, default="")

    message: Mapped["ChatMessage"] = relationship(back_populates="citations")
```

**ORM Rules:**
- All `id` columns are `String(36)` UUIDs generated via `_uuid()` — not `UUID` type, for portability
- `user_id` is plain `String(36)` — never a FK to `auth.users` (Supabase Auth lives outside SQLAlchemy scope)
- All cascades are `"all, delete-orphan"` — deleting a Document removes its Extractions, Fields, AuditEntries, Messages, Citations
- `bounding_box` fields use PostgreSQL `JSON` column — stored as `{x, y, width, height}` dict
- `status` and `role` use plain `String` columns — validated at the Pydantic/handler layer, not DB-level constraints
- `_now()` always uses `UTC` — no naive datetimes anywhere
- Import path: `from docmind.dbase.psql.models import Document, Extraction, ExtractedField, AuditEntry, ChatMessage, Citation`

---

## `dbase/supabase/storage.py`

```python
"""
docmind/dbase/supabase/storage.py

File upload/download/signed-URL helpers using Supabase Storage.
"""
from docmind.core.logging import get_logger
from docmind.dbase.supabase.client import get_supabase_client

logger = get_logger(__name__)

BUCKET_NAME = "documents"


def get_file_bytes(storage_path: str) -> bytes:
    """Download file bytes from Supabase storage."""
    client = get_supabase_client()
    return client.storage.from_(BUCKET_NAME).download(storage_path)


def delete_file(storage_path: str) -> None:
    """Delete a file from Supabase storage."""
    client = get_supabase_client()
    client.storage.from_(BUCKET_NAME).remove([storage_path])


def get_signed_url(storage_path: str, expires_in: int = 3600) -> str:
    """Generate a signed URL for file download."""
    client = get_supabase_client()
    result = client.storage.from_(BUCKET_NAME).create_signed_url(
        storage_path, expires_in
    )
    return result["signedURL"]
```

---

## Logging — `core/logging.py`

- Uses **structlog** for structured logging
- Development: colorized console output at DEBUG level
- Production: JSON output at INFO level
- Get a logger: `from docmind.core.logging import get_logger`
- Structured context via `logger.bind(key=value).info("message")`
- Third-party loggers (uvicorn, fastapi) set to WARNING

---

## Configuration — `core/config.py`

Key settings (loaded from env vars via `pydantic-settings`):

| Setting | Default | Description |
|---------|---------|-------------|
| `APP_NAME` | `"DocMind-VLM"` | Application name |
| `APP_DESCRIPTION` | `"Intelligent document extraction..."` | App description |
| `APP_HOST` | `"0.0.0.0"` | Server bind host |
| `APP_PORT` | `8000` | Server port |
| `APP_VERSION` | `"0.1.0"` | App version |
| `APP_ENVIRONMENT` | `"development"` | Environment |
| `APP_DEBUG` | `False` | Debug mode |
| `ALLOWED_ORIGINS_STR` | `"http://localhost:5173,http://localhost:3000"` | CORS origins |
| `SUPABASE_URL` | `""` | Supabase project URL (Auth + Storage) |
| `SUPABASE_ANON_KEY` | `""` | Supabase anon key |
| `SUPABASE_SERVICE_ROLE_KEY` | `""` | Supabase service role key |
| `SUPABASE_JWT_SECRET` | `""` | JWT secret for token verification |
| `DATABASE_URL` | `"postgresql+asyncpg://..."` | Supabase Postgres connection (SQLAlchemy) |
| `VLM_PROVIDER` | `"dashscope"` | VLM provider (dashscope\|openai\|google\|ollama) |
| `DASHSCOPE_API_KEY` | `""` | DashScope API key |
| `DASHSCOPE_MODEL` | `"qwen-vl-max"` | DashScope model |
| `OPENAI_API_KEY` | `""` | OpenAI API key |
| `OPENAI_MODEL` | `"gpt-4o"` | OpenAI model |
| `GOOGLE_API_KEY` | `""` | Google API key |
| `GOOGLE_MODEL` | `"gemini-2.0-flash"` | Google model |
| `OLLAMA_BASE_URL` | `"http://localhost:11434"` | Ollama base URL |
| `OLLAMA_MODEL` | `"llava:13b"` | Ollama model |

Access via `get_settings()` — cached with `@lru_cache()`.

---

## Error Handling Rules

| Scenario | HTTP Status | `detail` message |
|----------|-------------|-----------------|
| Invalid request body | 422 (auto by Pydantic) | Pydantic validation error |
| Missing/invalid JWT | 401 | `"Invalid or expired token"` |
| User accessing another user's document | 403 | `"Access denied"` |
| Document/extraction not found | 404 | `"Document not found"` / `"Extraction not found"` |
| Document not yet processed (chat) | 400 | `"Document must be processed before chatting"` |
| File too large | 422 (Pydantic `le=20_971_520`) | Pydantic validation error |
| Unsupported file type | 422 (Pydantic `pattern`) | Pydantic validation error |
| VLM provider error | 500 | `"Processing failed"` |
| Database error | 500 | `"Internal server error"` |
| Internal error | 500 | Generic message — no stack traces in responses |

**Never expose internal errors** (stack traces, provider error messages, SQL errors) in the HTTP response. Log them server-side with structlog, return a generic message to the client.

---

## CORS Configuration

```bash
# Allowed origins from settings
# Development: http://localhost:5173 (Vite), http://localhost:3000
# Production: set ALLOWED_ORIGINS_STR env var to your domain

ALLOWED_ORIGINS_STR=http://localhost:5173,http://localhost:3000
```

For production, set `ALLOWED_ORIGINS_STR` to the deployed frontend URL. Never use `*` in production.

---

## Docker

Docker Compose is located at `docker/docker-compose.dev.yml` (not at the repo root).
