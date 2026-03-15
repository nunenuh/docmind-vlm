---
created: 2026-03-11
---

# Python Conventions

Complete Python coding conventions for DocMind-VLM backend.

---

## Code Style

### PEP 8 Compliance

- Follow PEP 8 Python style guide
- Use **Black** for code formatting (line length: 88)
- Use **isort** for import sorting (profile: black)
- Use **ruff** for linting (replaces flake8)
- Use **mypy** for type checking (strict mode)

Configure in `pyproject.toml`:

```toml
[tool.black]
line-length = 88

[tool.isort]
profile = "black"

[tool.mypy]
strict = true
python_version = "3.11"

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I"]
```

### Type Hints

- **Required** on all function signatures — no exceptions
- Prefer built-in generic types (Python 3.11+): `list[str]`, `dict[str, float]`
- Use `T | None` instead of `Optional[T]` (Python 3.11+)
- Avoid `Any` — define proper types

```python
# ✅ Python 3.11 style
def extract_fields(image: bytes, template: str) -> dict[str, str]: ...
def get_document(doc_id: str) -> Document | None: ...

# ✅ Union types
def get_provider(name: str) -> DashScopeProvider | OpenAIProvider | GoogleProvider: ...

# ❌ No Any
def process(data: Any) -> Any: ...
```

### Async / Await

- FastAPI route handlers must be `async def`
- I/O operations (VLM API calls, database) should use async clients
- Pure functions (CV operations, data transforms) should be `sync`
- Use `asyncio.to_thread()` for blocking calls (OpenCV, heavy computation)

```python
# ✅ Route handler — always async
@router.post("/documents/{doc_id}/process")
async def trigger_processing(
    doc_id: str,
    user: dict = Depends(get_current_user),
) -> ProcessingResponse:
    result = await usecase.trigger_processing(doc_id, user["user_id"])
    return result

# ✅ Blocking CV call — wrap with asyncio.to_thread
async def preprocess_image(image_bytes: bytes) -> bytes:
    return await asyncio.to_thread(_run_cv_pipeline, image_bytes)

# ✅ Pure function — sync is fine
def correct_skew(image: np.ndarray) -> np.ndarray:
    angle = _detect_skew_angle(image)
    return _rotate_image(image, -angle)
```

---

## Naming Conventions

### Files & Packages

| Thing | Convention | Example |
| --- | --- | --- |
| Modules | `snake_case.py` | `deskew.py`, `factory.py` |
| Packages | `snake_case/` | `library/pipeline/`, `library/providers/`, `library/cv/` |
| Test files | `test_*.py` | `test_deskew.py`, `test_factory.py` |
| Module dirs | `snake_case/` | `modules/documents/`, `modules/extractions/` |

### Code Elements

| Thing | Convention | Example |
| --- | --- | --- |
| Classes | `PascalCase` | `DashScopeProvider`, `DocumentService` |
| Functions / methods | `snake_case` | `correct_skew()`, `get_vlm_provider()` |
| Constants | `UPPER_SNAKE_CASE` | `MAX_FILE_SIZE`, `DEFAULT_PROVIDER` |
| Variables | `snake_case` | `extraction_result`, `skew_angle` |
| Private methods | `_snake_case` | `_detect_skew_angle()`, `_validate_template()` |
| Boolean variables | `is_*`, `has_*` | `is_processed`, `has_extraction` |
| Protocols / ABCs | `PascalCase` | `VLMProvider` (Protocol class) |

---

## Imports

Group in this order, separated by blank lines:

```python
# 1. Standard library
import asyncio
from pathlib import Path
from typing import Protocol

# 2. Third-party
import cv2
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

# 3. Local (from docmind/)
from docmind.core.config import get_settings
from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.library.providers import get_vlm_provider
from docmind.library.cv import deskew_image
from docmind.modules.documents.schemas import DocumentResponse
```

**Rules:**
- Use **absolute imports** from the `docmind` package root
- Relative imports (`from .schemas import ...`) only within the same module directory
- Sort with `isort --profile black`
- No star imports (`from module import *`)

---

## Function Design

### Size limit: 50 lines per function

If a function grows past 50 lines, extract a helper.

### Single responsibility

One function, one purpose:

```python
# ✅ Single responsibility
def score_image_quality(image: np.ndarray) -> float:
    """Return quality score 0.0-1.0 based on blur and noise metrics."""
    blur_score = _measure_blur(image)
    noise_score = _measure_noise(image)
    return (blur_score + noise_score) / 2.0

def correct_skew(image: np.ndarray) -> np.ndarray:
    """Return deskewed copy of image."""
    angle = _detect_skew_angle(image)
    return _rotate_image(image, -angle)

# ❌ Mixed concerns
def preprocess_and_extract(image: bytes, provider: VLMProvider) -> dict:
    # deskew, score quality, extract fields, store results — all in one function
```

### Docstrings

Google-style for all public functions:

```python
def extract_fields(
    image_bytes: bytes,
    template_type: str,
    provider: VLMProvider,
) -> ExtractionResult:
    """
    Extract structured fields from a document image using a VLM provider.

    Args:
        image_bytes: Raw image bytes (JPEG or PNG).
        template_type: Template identifier (e.g., "invoice", "receipt").
        provider: VLM provider instance to use for extraction.

    Returns:
        ExtractionResult with extracted fields and confidence scores.

    Raises:
        ProviderError: If the VLM API call fails after retries.
        TemplateError: If template_type is not recognized.
    """
```

Private helpers need at minimum a one-line docstring:

```python
def _detect_skew_angle(image: np.ndarray) -> float:
    """Return detected skew angle in degrees (immutable — does not modify image)."""
```

---

## Immutability (CRITICAL)

**Always return new objects. Never mutate inputs.**

```python
# ✅ Immutable — returns new dict
def enrich_extraction(result: dict, confidence: float) -> dict:
    return {**result, "confidence": confidence}

# ✅ Immutable — OpenCV returns new array
def correct_skew(image: np.ndarray) -> np.ndarray:
    angle = _detect_skew_angle(image)
    rotated = _rotate_image(image, -angle)  # New array
    return rotated

# ✅ Immutable list comprehension
def add_scores(fields: list[dict], scores: list[float]) -> list[dict]:
    return [{**f, "score": s} for f, s in zip(fields, scores)]

# ❌ Mutates input
def enrich_extraction(result: dict, confidence: float) -> dict:
    result["confidence"] = confidence  # ❌ side effect
    return result
```

---

## Pydantic Models

### Request/Response models

```python
from pydantic import BaseModel, Field


class DocumentUploadResponse(BaseModel):
    id: str
    filename: str
    status: str = "uploaded"
    created_at: str


class ExtractionResult(BaseModel):
    document_id: str
    template_type: str
    fields: dict[str, str | None] = Field(default_factory=dict)
    confidence: float = Field(..., ge=0.0, le=1.0)
    provider: str


class ProcessingRequest(BaseModel):
    template_type: str = Field(..., min_length=1, description="Template to use for extraction")
    provider: str | None = Field(default=None, description="VLM provider override (default: config)")
```

### Rules

- `Field(...)` for required fields with constraints
- `Field(default_factory=dict)` for optional dict/list — never `= {}` or `= []`
- `from_attributes = True` in `model_config` when converting from Supabase responses
- Each module owns its schemas in `modules/*/schemas.py`

---

## Error Handling

### Always explicit, never silent

```python
# ✅ Explicit — typed exceptions, meaningful messages
try:
    result = await provider.extract(image_bytes, prompt)
except ProviderTimeoutError as e:
    logger.error("VLM provider timeout", provider=provider.name, error=str(e))
    raise HTTPException(status_code=504, detail="VLM provider timed out")
except ProviderError as e:
    logger.error("VLM extraction failed", provider=provider.name, error=str(e))
    raise HTTPException(status_code=502, detail="Extraction failed")
except Exception as e:
    logger.error("Unexpected extraction error", error=str(e))
    raise

# ❌ Silent swallow — never do this
try:
    result = await provider.extract(image_bytes, prompt)
except:
    return {}
```

### HTTP Status Codes

| Code | When |
| --- | --- |
| `200 OK` | Successful GET, successful processing |
| `201 Created` | Successful POST that creates a resource (upload, extraction) |
| `400 Bad Request` | Validation error (unsupported file type, bad template) |
| `401 Unauthorized` | Missing or invalid JWT token |
| `403 Forbidden` | Valid token but user lacks access to resource (RLS violation) |
| `404 Not Found` | Document or extraction not found |
| `413 Content Too Large` | File exceeds size limit (20MB) |
| `422 Unprocessable Entity` | Pydantic validation failure (auto) |
| `500 Internal Server Error` | Backend crash |
| `502 Bad Gateway` | VLM provider returned an error |
| `503 Service Unavailable` | Database or storage unreachable |
| `504 Gateway Timeout` | VLM provider timed out |

### Custom exception hierarchy

```python
# shared/exceptions.py
class DocMindException(Exception):
    """Base exception for DocMind-VLM."""

class ProviderError(DocMindException):
    """VLM provider call failed."""

class ProviderTimeoutError(ProviderError):
    """VLM provider call timed out."""

class PipelineError(DocMindException):
    """Processing pipeline failed."""

class TemplateError(DocMindException):
    """Unknown or invalid template type."""

class StorageError(DocMindException):
    """Supabase Storage operation failed."""

class AuthError(DocMindException):
    """Authentication or authorization failed."""
```

---

## Logging

Use **structlog** via `get_logger(__name__)` from `core/logging.py`.

```python
from docmind.core.logging import get_logger

logger = get_logger(__name__)  # Module-level logger

# Structured key-value context — not f-strings in messages
logger.info("Extraction complete", document_id=doc_id, provider=provider_name, field_count=len(fields))
logger.warning("Low quality image", document_id=doc_id, quality_score=score)
logger.error("Provider failed", provider=provider_name, error=str(e), retries=attempt)
```

**Rules:**
- One `logger = get_logger(__name__)` per file
- Use keyword arguments for structured context — not f-string interpolation in messages
- Never log secrets (API keys, JWT tokens, passwords)
- Log at entry and error points of significant operations

---

## Config Pattern

Use `get_settings()` with `@lru_cache` — not a module-level singleton:

```python
# core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_jwt_secret: str
    supabase_service_key: str = ""

    # VLM Providers
    vlm_provider: str = "dashscope"
    dashscope_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    ollama_base_url: str = "http://localhost:11434"

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    allowed_origins: list[str] = ["http://localhost:5173"]
    max_upload_size_mb: int = 20

    model_config = {"env_file": ".env"}


@lru_cache
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()
```

**Usage:**
```python
# ✅ Always call the function
settings = get_settings()
api_key = settings.dashscope_api_key

# ❌ Never import a module-level singleton
from docmind.core.config import settings  # Wrong
```

---

## Database Patterns

### SQLAlchemy + Supabase Hybrid

Database queries use SQLAlchemy async sessions. Supabase is only for Auth (JWT) and file Storage.

```python
# ✅ Use SQLAlchemy async sessions for all DB queries
from sqlalchemy import select
from docmind.dbase.sqlalchemy.engine import async_session
from docmind.dbase.sqlalchemy.models import Document

async def get_by_id(document_id: str, user_id: str) -> Document | None:
    async with async_session() as session:
        stmt = select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

# ✅ Use Supabase client for file storage only
from docmind.dbase.supabase.storage import get_file_bytes, delete_file

# ❌ Never construct raw SQL with string interpolation
# ❌ Never use Supabase client for database queries
```

### Ownership enforcement

Always filter by `user_id` from JWT — never trust client-provided user IDs:

```python
# ✅ user_id from JWT, not from request body
async def list_documents(user_id: str) -> list[Document]:
    async with async_session() as session:
        stmt = (
            select(Document)
            .where(Document.user_id == user_id)
            .order_by(Document.created_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())
```

### ORM Models

All models inherit from `Base` in `dbase/sqlalchemy/base.py`:

```python
# dbase/sqlalchemy/models.py
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    storage_path: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="uploaded")
    document_type: Mapped[str | None] = mapped_column(String(50))
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
```

### Alembic Migrations

Schema changes are version-controlled via Alembic:

```bash
# Create a new migration after modifying models
cd backend && poetry run alembic revision --autogenerate -m "description"

# Apply migrations
poetry run alembic upgrade head
```

---

## Related Conventions

- [[projects/docmind-vlm/specs/conventions/python-module-structure]] — Layered architecture (Handler → UseCase → Service → Repository)
- [[projects/docmind-vlm/specs/conventions/testing]] — Test structure, VLM mocking strategy
- [[projects/docmind-vlm/specs/conventions/security]] — Supabase JWT authentication

## External References

- [PEP 8](https://pep8.org/) — Python style guide
- [Black](https://black.readthedocs.io/) — Code formatter
- [isort](https://pycqa.github.io/isort/) — Import sorter
- [Pydantic v2](https://docs.pydantic.dev/) — Data validation
- [FastAPI](https://fastapi.tiangolo.com/) — Web framework
- [structlog](https://www.structlog.org/) — Structured logging
- [LangGraph](https://python.langchain.com/docs/langgraph) — Pipeline orchestration
