---
created: 2026-03-11
---

# Python Module Structure Conventions

> **Project Mapping**: In DocMind-VLM, all Python source lives in `backend/src/docmind/`.
> The architecture follows a **module-per-feature** layered pattern: Handler → UseCase → Service → Repository.
> Each feature module is a self-contained directory with its own schemas, services, repositories, usecase, and API handler.

---

## How These Conventions Apply to DocMind-VLM

| Architectural Layer | Location                     | Responsibility                                                          |
| ------------------- | ---------------------------- | ----------------------------------------------------------------------- |
| HTTP Handlers       | `modules/*/apiv1/handler.py` | Thin route handlers — validate input, authenticate, delegate to usecase |
| Use Cases           | `modules/*/usecase.py`       | Orchestrate service + repository calls for a use case                   |
| Services            | `modules/*/services.py`      | Business logic — calls library functions (CV, providers, pipeline)      |
| Repositories        | `modules/*/repositories.py`  | Database operations — Supabase queries, always filter by user_id        |
| Schemas             | `modules/*/schemas.py`       | Pydantic request/response models for the module                         |
| Library             | `library/`                   | Reusable logic — CV, VLM providers, LangGraph pipelines                 |
| Database            | `dbase/supabase/`            | Supabase client init + storage helpers                                  |
| Core                | `core/`                      | Config, auth, dependencies, logging                                     |
| Shared              | `shared/`                    | Exception hierarchy, shared utilities, cross-module services/repos      |

**Backend `src/docmind/` structure:**

```
backend/src/docmind/         # Python package root
├── __init__.py
├── main.py                          # FastAPI app factory (create_app)
├── router.py                        # Aggregates module routers under /api/v1/
│
├── core/                            # Cross-cutting concerns
│   ├── __init__.py
│   ├── config.py                    # Pydantic BaseSettings + get_settings() with @lru_cache
│   ├── auth.py                      # Supabase JWT verification → get_current_user
│   ├── dependencies.py              # FastAPI deps (get_current_user, get_supabase_client)
│   └── logging.py                   # structlog setup + get_logger(__name__)
│
├── dbase/                           # Database layer
│   ├── __init__.py
│   ├── supabase/
│   │   ├── __init__.py
│   │   ├── client.py                # Supabase client init (Auth + Storage only)
│   │   └── storage.py               # File upload, download, signed-URL helpers
│   └── sqlalchemy/
│       ├── __init__.py
│       ├── engine.py                # Async engine + session factory
│       ├── base.py                  # DeclarativeBase
│       └── models.py                # ORM models (Document, Extraction, ChatMessage, etc.)
│
├── library/                         # Reusable logic (NOT tied to modules/DB)
│   ├── __init__.py
│   ├── cv/                          # Classical computer vision (pure functions)
│   │   ├── __init__.py
│   │   ├── deskew.py
│   │   ├── quality.py
│   │   └── preprocessing.py
│   ├── providers/                   # VLM provider abstraction (provider-agnostic)
│   │   ├── __init__.py
│   │   ├── protocol.py
│   │   ├── factory.py
│   │   ├── dashscope.py
│   │   ├── openai.py
│   │   ├── google.py
│   │   └── ollama.py
│   └── pipeline/                    # LangGraph workflow definitions
│       ├── __init__.py
│       ├── processing.py
│       └── chat.py
│
├── modules/                         # Feature modules (Handler → UseCase → Service → Repo)
│   ├── __init__.py
│   ├── health/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   ├── usecase.py
│   │   └── apiv1/
│   │       ├── __init__.py
│   │       └── handler.py
│   ├── documents/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   ├── repositories.py
│   │   ├── usecase.py
│   │   └── apiv1/
│   │       ├── __init__.py
│   │       └── handler.py
│   ├── extractions/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   ├── repositories.py
│   │   ├── usecase.py
│   │   └── apiv1/
│   │       ├── __init__.py
│   │       └── handler.py
│   ├── chat/
│   │   ├── __init__.py
│   │   ├── schemas.py
│   │   ├── services.py
│   │   ├── repositories.py
│   │   ├── usecase.py
│   │   └── apiv1/
│   │       ├── __init__.py
│   │       └── handler.py
│   └── templates/
│       ├── __init__.py
│       ├── schemas.py
│       ├── services.py
│       ├── usecase.py
│       └── apiv1/
│           ├── __init__.py
│           └── handler.py
│
└── shared/                          # Cross-module concerns
    ├── __init__.py
    ├── exceptions.py                # Exception hierarchy
    ├── utils/                       # Shared utility functions
    ├── services/                    # Shared services (used by multiple modules)
    └── repositories/                # Shared repositories (used by multiple modules)
```

**Imports always resolve from `docmind/` (configured via `packages = [{include = "docmind", from = "src"}]` and `pythonpath = ["src"]` in `pyproject.toml`):**

```python
from docmind.core.config import get_settings              # core/config.py
from docmind.core.auth import get_current_user             # core/auth.py
from docmind.core.logging import get_logger                # core/logging.py
from docmind.library.providers import get_vlm_provider     # library/providers/__init__.py
from docmind.library.cv import deskew_image                # library/cv/__init__.py
from docmind.library.pipeline import run_processing_pipeline  # library/pipeline/__init__.py
from docmind.modules.documents.schemas import DocumentResponse  # modules/documents/schemas.py
from docmind.modules.documents.services import DocumentService  # modules/documents/services.py
from docmind.shared.exceptions import ServiceException     # shared/exceptions.py
```

---

## Module Layering Pattern

Each feature module follows a strict layered architecture:

```
modules/documents/apiv1/handler.py   ← HTTP layer (thin)
    ↓ calls
modules/documents/usecase.py         ← Orchestration
    ↓ calls
modules/documents/services.py        ← Business logic
    ↓ calls                ↓ calls
library/                   modules/documents/repositories.py
  ├── pipeline/              ↓ queries
  ├── providers/           dbase/sqlalchemy/ (ORM models + async sessions)
  └── cv/
```

### Dependency Rules

| Layer | Can Import From | Cannot Import From |
| --- | --- | --- |
| `handler.py` | `usecase.py`, `schemas.py`, `core/` | `services.py`, `repositories.py`, `library/`, `dbase/` |
| `usecase.py` | `services.py`, `repositories.py`, `schemas.py`, `core/`, `shared/` | `handler.py`, `library/` (use services) |
| `services.py` | `library/`, `schemas.py`, `core/`, `shared/` | `handler.py`, `usecase.py`, `repositories.py`, `dbase/` |
| `repositories.py` | `dbase/sqlalchemy/`, `schemas.py`, `core/` | Everything else |
| `library/` | `core/`, `dbase/` (for pipeline store node) | `modules/`, `shared/` |

**Key principle:** Handlers know about usecases. Usecases know about services and repositories. Services know about library. Repositories know about database. No layer reaches upward.

---

## Example Flow: Document Processing

```
POST /api/v1/documents/{id}/process
    → modules/documents/apiv1/handler.py (validates JWT, extracts user_id)
    → modules/documents/usecase.py (orchestrates the flow)
        → modules/documents/repositories.py (get document from Supabase)
        → modules/documents/services.py (coordinate processing)
            → library/pipeline/processing.py (LangGraph StateGraph)
                → library/cv/ (preprocess: deskew, quality)
                → library/providers/ (extract: VLM call)
                → dbase/supabase/ (store: persist results)
    → SSE progress events streamed back to client
```

### Step-by-step with code:

### 1. `modules/documents/apiv1/handler.py` — Route Handler

```python
"""
Document API handler — upload, retrieve, and trigger processing.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.modules.documents.schemas import ProcessingRequest, ProcessingResponse
from docmind.modules.documents.usecase import DocumentUseCase

logger = get_logger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


def _get_usecase() -> DocumentUseCase:
    """Dependency injection for DocumentUseCase."""
    return DocumentUseCase()


@router.post(
    "/{document_id}/process",
    response_model=ProcessingResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def trigger_processing(
    document_id: str,
    request: ProcessingRequest,
    user: dict = Depends(get_current_user),
    usecase: DocumentUseCase = Depends(_get_usecase),
) -> ProcessingResponse:
    """Trigger document extraction processing."""
    result = await usecase.trigger_processing(
        document_id=document_id,
        template_type=request.template_type,
        user_id=user["user_id"],
        provider_name=request.provider,
    )
    return result
```

### 2. `modules/documents/usecase.py` — Use Case Orchestration

```python
"""
Document use case — orchestrates service + repository calls.
"""
from docmind.core.logging import get_logger
from docmind.modules.documents.repositories import DocumentRepository
from docmind.modules.documents.schemas import ProcessingResponse
from docmind.modules.documents.services import DocumentService

logger = get_logger(__name__)


class DocumentUseCase:
    """Orchestrates document operations across service and repository layers."""

    def __init__(self) -> None:
        self._repository = DocumentRepository()
        self._service = DocumentService()

    async def trigger_processing(
        self,
        document_id: str,
        template_type: str,
        user_id: str,
        provider_name: str | None = None,
    ) -> ProcessingResponse:
        """Trigger extraction processing for a document."""
        document = await self._repository.get_by_id(document_id, user_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")

        await self._repository.update_status(document_id, "processing")

        result = await self._service.process_document(
            document=document,
            template_type=template_type,
            provider_name=provider_name,
        )

        return ProcessingResponse(
            document_id=document_id,
            status="completed",
            extraction_id=result.extraction_id,
        )
```

### 3. `modules/documents/services.py` — Business Logic

```python
"""
Document service — business logic for document processing.

Calls into library/ for pipeline execution.
"""
from docmind.core.logging import get_logger
from docmind.library.pipeline import run_processing_pipeline
from docmind.library.providers import get_vlm_provider

logger = get_logger(__name__)


class DocumentService:
    """Business logic for document operations."""

    async def process_document(
        self,
        document: dict,
        template_type: str,
        provider_name: str | None = None,
    ) -> dict:
        """Run the processing pipeline on a document."""
        provider = get_vlm_provider()
        result = await run_processing_pipeline(
            document=document,
            template_type=template_type,
            provider=provider,
        )
        return result
```

### 4. `modules/documents/repositories.py` — Data Access

```python
"""
Document repository — SQLAlchemy data access for documents.

All queries filter by user_id for ownership enforcement.
"""
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from docmind.core.logging import get_logger
from docmind.dbase.sqlalchemy.engine import async_session
from docmind.dbase.sqlalchemy.models import Document

logger = get_logger(__name__)


class DocumentRepository:
    """Data access layer for documents."""

    async def get_by_id(self, document_id: str, user_id: str) -> Document | None:
        """Get document by ID, scoped to user."""
        async with async_session() as session:
            stmt = select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def update_status(self, document_id: str, status: str) -> None:
        """Update document processing status."""
        async with async_session() as session:
            stmt = (
                update(Document)
                .where(Document.id == document_id)
                .values(status=status)
            )
            await session.execute(stmt)
            await session.commit()
```

### 5. `modules/documents/schemas.py` — Pydantic Models

```python
"""
Document schemas — Pydantic request/response models.
"""
from datetime import datetime

from pydantic import BaseModel, Field


class ProcessingRequest(BaseModel):
    template_type: str = Field(..., min_length=1, description="Template to use for extraction")
    provider: str | None = Field(default=None, description="VLM provider override")


class ProcessingResponse(BaseModel):
    document_id: str
    status: str
    extraction_id: str


class DocumentResponse(BaseModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: str
    document_type: str | None
    page_count: int
    created_at: datetime
    updated_at: datetime
```

---

## Layer Rules

### `modules/*/apiv1/handler.py` — Route Handlers

- **Thin**: validate input, authenticate, delegate to usecase, return response
- One handler file per feature module
- Never contain business logic or database queries
- Always use `Depends(get_current_user)` on protected routes
- Import schemas from own module's `schemas.py`
- Delegate all work to `usecase.py`

### `modules/*/usecase.py` — Use Cases

- Orchestrate between services and repositories
- One usecase class per module
- Coordinate multi-step flows (e.g., check document exists → update status → run processing)
- Handle error mapping (ValueError → appropriate HTTP response via handler)
- Never call library/ directly — use services for that

### `modules/*/services.py` — Business Logic

- Business logic that calls library/ functions (CV, providers, pipeline)
- Enforce business rules (ownership checks, status transitions, validation)
- One service class per module
- Never import from handler or usecase layers
- Never import from repositories or dbase — that's the usecase's job

### `modules/*/repositories.py` — Data Access

- All SQLAlchemy queries for the module's domain
- Always filter by `user_id` for ownership enforcement
- Return ORM model instances (or None)
- One repository class per module
- Never contain business logic
- Use `async with async_session() as session:` for each operation

### `modules/*/schemas.py` — Pydantic Models

- Request/response models for the module
- `Field(...)` for required fields with constraints
- `Field(default_factory=dict)` for optional dict/list — never `= {}` or `= []`
- Separate from other modules — each module owns its schemas

### `library/` — Reusable Logic

- **Pipeline**: LangGraph `StateGraph` definitions (processing, chat)
- **Providers**: VLM provider protocol + concrete implementations
- **CV**: Pure stateless OpenCV functions (deskew, quality, preprocessing)
- Never imports from `modules/` — communicates through state and callbacks
- Can import from `core/` and `dbase/` (for pipeline store node)

### `dbase/sqlalchemy/` — Database Layer (SQL)

- `engine.py`: Async engine + session factory (`async_session`)
- `base.py`: `DeclarativeBase` for all ORM models
- `models.py`: ORM model definitions (Document, Extraction, ExtractedField, AuditEntry, ChatMessage)
- Used by all repositories and the pipeline store node
- Alembic migrations live at `backend/alembic/`

### `dbase/supabase/` — Auth + Storage Layer

- `client.py`: Supabase client init (for Auth token verification + Storage operations only)
- `storage.py`: File upload, download, signed-URL helpers
- **Not used for database queries** — all DB access goes through SQLAlchemy

### `core/` — Cross-cutting

- `config.py`: Pydantic BaseSettings + `get_settings()` with `@lru_cache`
- `auth.py`: Supabase JWT validation dependency → `get_current_user`
- `dependencies.py`: Shared FastAPI dependencies
- `logging.py`: structlog setup + `get_logger(__name__)`

### `shared/` — Cross-module Concerns

- `exceptions.py`: Custom exception hierarchy for typed error handling
- `utils/`: Shared utility functions
- `services/`: Services used by multiple modules
- `repositories/`: Repositories used by multiple modules

---

## Register Routes in `router.py`

```python
"""
docmind/router.py

Aggregates all module routers under /api/v1/.
"""
from fastapi import APIRouter

from docmind.modules.health.apiv1.handler import router as health_router
from docmind.modules.templates.apiv1.handler import router as templates_router
from docmind.modules.documents.apiv1.handler import router as documents_router
from docmind.modules.extractions.apiv1.handler import router as extractions_router
from docmind.modules.chat.apiv1.handler import router as chat_router

api_router = APIRouter(prefix="/api/v1")

# Public routes (no auth)
api_router.include_router(health_router)
api_router.include_router(templates_router)

# Protected routes (auth applied at handler level via Depends)
api_router.include_router(documents_router)
api_router.include_router(extractions_router)
api_router.include_router(chat_router)
```

## App Factory in `main.py`

```python
"""
docmind/main.py

FastAPI app factory. Configures CORS, registers router, sets up lifespan.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.router import api_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    logger.info("Starting DocMind-VLM")
    yield
    logger.info("Shutting down DocMind-VLM")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="DocMind-VLM",
        description="Intelligent document extraction powered by Vision Language Models",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
    )

    app.include_router(api_router)
    return app
```

---

## File Organization Checklist

When adding a new feature module:

- [ ] Create module directory under `modules/` with `__init__.py`
- [ ] `schemas.py`: Pydantic request/response models
- [ ] `repositories.py`: Supabase data access (filter by user_id)
- [ ] `services.py`: Business logic (calls library/ functions)
- [ ] `usecase.py`: Orchestrate service + repository calls
- [ ] `apiv1/handler.py`: Thin HTTP handler (validate, auth, delegate to usecase)
- [ ] Register router in `router.py`
- [ ] Tests mirroring the module structure in `tests/`

When adding reusable logic (not tied to a module):

- [ ] Add to `library/` (CV, providers, pipeline)
- [ ] Never import from `modules/`
- [ ] Re-export from `library/*/__init__.py` for clean API

---

## Related Conventions

- [[projects/docmind-vlm/specs/conventions/repository-overview]] — Full project structure and tech stack
- [[projects/docmind-vlm/specs/conventions/python-conventions]] — Code style, types, async patterns
- [[projects/docmind-vlm/specs/conventions/testing]] — Test structure and VLM mocking
- [[projects/docmind-vlm/specs/conventions/security]] — Supabase JWT auth flow
