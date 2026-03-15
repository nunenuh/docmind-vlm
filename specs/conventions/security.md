---
created: 2026-03-11
---

# Security Conventions — DocMind-VLM

Security guidelines for DocMind-VLM backend using Supabase JWT authentication.

---

## Overview

DocMind-VLM uses **Supabase Auth** for authentication. Supabase issues JWTs via Google/GitHub OAuth. The backend validates the JWT on every protected request, extracts the `user_id`, and passes it through the module layers for row-level security (RLS) enforcement.

```
User → Supabase Auth (Google/GitHub OAuth) → JWT issued
Frontend → stores JWT via Supabase JS SDK
Frontend → API request with Authorization: Bearer <token>
Backend → core/auth.py validates JWT, extracts user_id
Backend → handler → usecase → service/repository (user_id for RLS)
```

---

## Authentication Flow

```
┌──────────┐     ┌─────────────────┐     ┌──────────────┐
│  Browser  │────▶│  Supabase Auth  │────▶│  OAuth       │
│           │◀────│  (hosted)       │◀────│  (Google/    │
│           │     │                 │     │   GitHub)    │
└─────┬─────┘     └─────────────────┘     └──────────────┘
      │ JWT stored via
      │ Supabase JS SDK
      │
      ▼
┌──────────┐     Authorization: Bearer <jwt>     ┌──────────────┐
│ Frontend  │───────────────────────────────────▶│  Backend API  │
│ (React)   │◀───────────────────────────────────│  (FastAPI)    │
└──────────┘     200 / 401 / 403                 └──────┬───────┘
                                                        │
                                                        │ JWT validated
                                                        │ user_id extracted
                                                        ▼
                                                 ┌──────────────┐
                                                 │  Handler →    │
                                                 │  UseCase →    │
                                                 │  Repository   │
                                                 │  (user_id     │
                                                 │   for RLS)    │
                                                 └──────────────┘
```

---

## Backend JWT Validation

### `core/auth.py` Implementation

```python
"""
docmind/core/auth.py

FastAPI dependency for Supabase JWT validation.
Attach to routes or routers that require authentication.
"""
import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from docmind.core.config import get_settings
from docmind.core.logging import get_logger

logger = get_logger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate Supabase JWT and extract user info.

    Returns:
        Dict with user_id and email extracted from JWT claims.

    Raises:
        HTTPException 401: If token is missing, expired, or invalid.

    Usage:
        @router.post("/documents", dependencies=[Depends(get_current_user)])
        async def create_document(user: dict = Depends(get_current_user)):
            user_id = user["user_id"]
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return {"user_id": payload["sub"], "email": payload.get("email")}
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
```

### `core/config.py` — Supabase Settings

```python
# docmind/core/config.py
from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Supabase
    supabase_url: str
    supabase_jwt_secret: str                    # Used for JWT validation
    supabase_service_key: str = ""              # Server-side storage operations

    # VLM Providers
    vlm_provider: str = "dashscope"
    dashscope_api_key: str = ""                 # Qwen3-VL (default)
    openai_api_key: str = ""                    # GPT-4o (optional)
    google_api_key: str = ""                    # Gemini (optional)
    ollama_base_url: str = "http://localhost:11434"  # Ollama (optional)

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

---

## Applying to Routes

### Option A: Per-handler (recommended for DocMind-VLM)

```python
# modules/documents/apiv1/handler.py
from docmind.core.auth import get_current_user

@router.post("/documents/{doc_id}/process")
async def trigger_processing(
    doc_id: str,
    user: dict = Depends(get_current_user),  # Extracts user info
    usecase: DocumentUseCase = Depends(_get_usecase),
) -> ProcessingResponse:
    result = await usecase.trigger_processing(doc_id, user["user_id"])
    return result
```

### Option B: Per-router (protects all routes at once)

```python
# router.py — mount protected routers with auth dependency
from docmind.core.auth import get_current_user

api_router.include_router(
    documents_router,
    dependencies=[Depends(get_current_user)],
)
```

### Public Endpoints (no auth required)

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/health` | Health check for monitoring |
| `GET /api/v1/templates` | Read-only template definitions |

---

## Ownership Enforcement (Application-Level RLS)

The `user_id` from the JWT is the **sole source of truth** for data ownership. Never trust client-provided user IDs.

**Note:** Supabase RLS policies work at the Postgres level, but the backend connects as `postgres` (superuser via `DATABASE_URL`), which **bypasses RLS**. Ownership is enforced in the repository layer by always filtering on `user_id`.

### Rules

1. Every repository method that touches user data **must** accept and filter by `user_id`
2. `user_id` comes from the JWT payload (`payload["sub"]`), passed through handler → usecase → repository
3. If a document belongs to another user, return `404 Not Found` (not `403 Forbidden`) to avoid leaking existence

```python
# ✅ Ownership enforced — user_id from JWT flows through layers
# modules/documents/repositories.py
from sqlalchemy import select
from docmind.dbase.sqlalchemy.engine import async_session
from docmind.dbase.sqlalchemy.models import Document

class DocumentRepository:
    async def get_by_id(self, document_id: str, user_id: str) -> Document | None:
        async with async_session() as session:
            stmt = select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,  # ← ownership filter
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

# ❌ No ownership check — any user can access any document
    async def get_by_id(self, document_id: str) -> Document | None:
        async with async_session() as session:
            stmt = select(Document).where(Document.id == document_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
```

### UseCase layer pattern

```python
# modules/documents/usecase.py
class DocumentUseCase:
    async def get_document(self, doc_id: str, user_id: str) -> dict:
        """Get document owned by user, or raise."""
        document = await self._repository.get_by_id(doc_id, user_id)
        if not document:
            raise ValueError(f"Document {doc_id} not found")  # 404, not 403
        return document
```

---

## File Upload Validation

### MIME Type Check

Only allow known safe document/image types:

```python
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/png",
    "image/tiff",
    "image/webp",
    "application/pdf",
}

def validate_upload(file: UploadFile) -> None:
    """Validate uploaded file before storage."""
    settings = get_settings()

    # MIME type check
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file type: {file.content_type}. "
                   f"Allowed: {', '.join(sorted(ALLOWED_MIME_TYPES))}",
        )

    # Size check
    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file.size and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File too large. Maximum size: {settings.max_upload_size_mb}MB",
        )
```

### Filename Sanitization

Never use the original filename for storage paths:

```python
import uuid
from pathlib import PurePosixPath


def safe_storage_path(user_id: str, original_filename: str) -> str:
    """Generate a safe storage path using UUID — never trust original filename."""
    ext = PurePosixPath(original_filename).suffix.lower()
    if ext not in {".jpg", ".jpeg", ".png", ".tiff", ".webp", ".pdf"}:
        ext = ""
    unique_name = f"{uuid.uuid4().hex}{ext}"
    return f"documents/{user_id}/{unique_name}"
```

---

## Secret Management

### Rules

| Rule | Detail |
| --- | --- |
| Never hardcode secrets | Always use `.env` → `get_settings().supabase_jwt_secret` |
| `.env` in `.gitignore` | Never commit `.env` with real secrets |
| `.env.example` committed | Template with placeholder values |
| Never log tokens | Log only metadata (user_id, token prefix for debugging) |
| Rotate on exposure | If JWT secret is committed to git, rotate in Supabase dashboard immediately |

### `.env.example`

```bash
# .env.example — commit this (no real values)

# Supabase (Auth + Storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_JWT_SECRET=your-jwt-secret-from-supabase-dashboard
SUPABASE_SERVICE_KEY=your-service-role-key

# Database (Supabase Postgres via SQLAlchemy)
DATABASE_URL=postgresql+asyncpg://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres

# VLM Providers (at least one required)
VLM_PROVIDER=dashscope
DASHSCOPE_API_KEY=sk-your-dashscope-key
OPENAI_API_KEY=sk-your-openai-key
GOOGLE_API_KEY=your-google-ai-key
OLLAMA_BASE_URL=http://localhost:11434

# Application
APP_ENV=development
LOG_LEVEL=INFO
ALLOWED_ORIGINS=http://localhost:5173
MAX_UPLOAD_SIZE_MB=20
```

### `.gitignore`

```bash
.env
*.env.local
```

---

## CORS Configuration

```python
# main.py — inside create_app()
settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,      # ["http://localhost:5173"] in dev
    allow_credentials=True,                       # Required for cookies/auth headers
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],  # Explicit > wildcard
)
```

**Rules:**
- Never use `allow_origins=["*"]` in production
- Always list specific origins: `["https://docmind.yourdomain.com"]`
- `allow_credentials=True` is required for the `Authorization` header to pass through
- Explicitly list allowed headers rather than using wildcard

---

## Error Response Rules

| Scenario | Status | Response Body |
| --- | --- | --- |
| Missing `Authorization` header | 401 | `{"detail": "Not authenticated"}` |
| Expired JWT token | 401 | `{"detail": "Token expired"}` |
| Invalid JWT token | 401 | `{"detail": "Invalid token"}` |
| Valid token, resource owned by another user | 404 | `{"detail": "Document not found"}` |
| Valid token, unsupported file type | 400 | `{"detail": "Unsupported file type: ..."}` |
| Valid token, file too large | 413 | `{"detail": "File too large. Maximum size: 20MB"}` |

**Never reveal in error responses:**
- Whether a resource exists but belongs to another user (use 404, not 403)
- Internal error details or stack traces
- JWT secret or token validation internals
- Database query details

---

## Testing with JWT

### Mock JWT fixture

```python
# tests/conftest.py
import pytest
import jwt as pyjwt

TEST_JWT_SECRET = "test-jwt-secret"


@pytest.fixture(autouse=True)
def mock_jwt_secret(monkeypatch):
    """Set test JWT secret for all tests."""
    monkeypatch.setattr(
        "docmind.core.config.Settings.supabase_jwt_secret",
        TEST_JWT_SECRET,
    )


@pytest.fixture
def make_jwt():
    """Factory fixture for creating test JWTs with custom claims."""
    def _make(
        user_id: str = "user-abc-123",
        email: str = "test@example.com",
        exp: int = 9999999999,
        **extra_claims,
    ) -> str:
        payload = {
            "sub": user_id,
            "email": email,
            "aud": "authenticated",
            "exp": exp,
            **extra_claims,
        }
        return pyjwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
    return _make


@pytest.fixture
def auth_headers(make_jwt) -> dict:
    """Authorization headers with a valid test JWT."""
    return {"Authorization": f"Bearer {make_jwt()}"}
```

### Auth test cases

```python
# tests/unit/core/test_auth.py
"""Unit tests for docmind/core/auth.py — JWT validation."""
import pytest
import time
from httpx import AsyncClient, ASGITransport

from docmind.main import create_app


@pytest.fixture
def app():
    return create_app()


@pytest.fixture
def client(app):
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_protected_route_with_valid_token_returns_200(client, auth_headers):
    """Valid JWT grants access to protected routes."""
    response = await client.get("/api/v1/documents", headers=auth_headers)
    assert response.status_code != 401


@pytest.mark.asyncio
async def test_protected_route_without_token_returns_401(client):
    """Missing Authorization header returns 401."""
    response = await client.get("/api/v1/documents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_protected_route_with_invalid_token_returns_401(client):
    """Malformed JWT returns 401."""
    headers = {"Authorization": "Bearer invalid-token-here"}
    response = await client.get("/api/v1/documents", headers=headers)
    assert response.status_code == 401
    assert "Invalid token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_protected_route_with_expired_token_returns_401(client, make_jwt):
    """Expired JWT returns 401 with 'Token expired' message."""
    expired_token = make_jwt(exp=int(time.time()) - 3600)  # 1 hour ago
    headers = {"Authorization": f"Bearer {expired_token}"}
    response = await client.get("/api/v1/documents", headers=headers)
    assert response.status_code == 401
    assert "Token expired" in response.json()["detail"]


@pytest.mark.asyncio
async def test_public_health_endpoint_requires_no_auth(client):
    """GET /api/v1/health returns 200 without any auth."""
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
```

---

## Frontend: Supabase Auth Integration

```typescript
// frontend/src/lib/supabase.ts
import { createClient } from "@supabase/supabase-js";

const supabaseUrl = import.meta.env.VITE_SUPABASE_URL;
const supabaseAnonKey = import.meta.env.VITE_SUPABASE_ANON_KEY;

export const supabase = createClient(supabaseUrl, supabaseAnonKey);
```

```typescript
// frontend/src/lib/api.ts
import { supabase } from "./supabase";

const BASE_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const { data: { session } } = await supabase.auth.getSession();

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  if (session?.access_token) {
    headers["Authorization"] = `Bearer ${session.access_token}`;
  }

  const response = await fetch(`${BASE_URL}${path}`, { ...options, headers });

  if (response.status === 401) {
    await supabase.auth.signOut();
    window.location.href = "/login";
    throw new Error("Session expired");
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(error.detail || `HTTP ${response.status}`);
  }

  return response.json();
}
```

---

## Docker Compose Secret Injection

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    env_file: .env
    environment:
      - APP_ENV=production

  frontend:
    build:
      context: ./frontend
      args:
        VITE_SUPABASE_URL: ${SUPABASE_URL}
        VITE_SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}
        VITE_API_URL: http://localhost:8000
```

**Never commit `.env`** with real keys. Only commit `.env.example`.

---

## Security Checklist

Before every PR:

- [ ] No hardcoded secrets (API keys, JWT secrets, tokens) in source code
- [ ] All protected handler routes use `Depends(get_current_user)`
- [ ] All repository queries filter by `user_id` from JWT
- [ ] File uploads validated (MIME type, size, filename sanitized)
- [ ] Error responses do not leak internal details
- [ ] CORS origins are explicit (no wildcards in production)
- [ ] `.env` is in `.gitignore`
- [ ] New env vars are documented in `.env.example`

---

## Related Conventions

- [[projects/docmind-vlm/specs/conventions/python-conventions]] — Error handling, HTTP status codes
- [[projects/docmind-vlm/specs/conventions/python-module-structure]] — Where auth fits in the architecture
- [[projects/docmind-vlm/specs/conventions/testing]] — JWT test fixtures and auth test patterns
