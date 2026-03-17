# Issue #33: Integration Tests — API Endpoints + Frontend Page Rendering

## Summary

Write integration tests for the backend API endpoints using httpx AsyncClient with ASGI transport (no real server needed) and an in-memory SQLite database for async DB operations. VLM providers remain mocked. Test the full request-response cycle: HTTP method, route, auth headers, request body, response status, response schema. For the frontend, test page rendering with mocked API responses using React Testing Library. Also test the document processing pipeline end-to-end with mocked VLM to verify the full LangGraph graph execution.

## Context

- **Phase**: 7 — Testing + Polish
- **Priority**: P0
- **Labels**: `phase-7-testing`, `backend`, `frontend`, `tdd`
- **Dependencies**: #32 (unit tests provide base fixtures), all implementation issues
- **Branch**: `feat/33-integration-tests`
- **Estimated scope**: L

## Specs to Read

- `specs/conventions/testing.md` — Integration test setup, conftest fixtures, CI strategy
- `specs/backend/api.md` — All API endpoints, request/response schemas, error codes
- `specs/conventions/security.md` — JWT auth flow for testing
- `specs/frontend/components.md` — Component structure for rendering tests

## Current State (Scaffold)

**Backend integration test directories exist but are empty:**
```
backend/tests/integration/
├── modules/
│   ├── chat/                    # Empty
│   ├── documents/               # Empty
│   ├── extractions/             # Empty
│   └── health/                  # Empty
```

**No integration conftest.py exists.**

**Frontend: no test infrastructure set up.**

## Requirements

### Functional

1. **Backend API integration tests** for every endpoint:
   - `GET /api/v1/health/ping` — returns 200, no auth
   - `GET /api/v1/health/status` — returns 200 with component statuses, no auth
   - `POST /api/v1/documents` — creates document, returns 201 with document schema
   - `GET /api/v1/documents` — returns paginated list for authenticated user
   - `GET /api/v1/documents/{id}` — returns 200 for own document, 404 for other user's
   - `DELETE /api/v1/documents/{id}` — returns 204, document removed
   - `POST /api/v1/documents/{id}/process` — returns SSE stream (202)
   - `GET /api/v1/extractions/{document_id}` — returns extraction data
   - `GET /api/v1/extractions/{document_id}/audit` — returns audit trail
   - `GET /api/v1/extractions/{document_id}/overlay` — returns overlay regions
   - `GET /api/v1/extractions/{document_id}/comparison` — returns comparison data
   - `POST /api/v1/chat/{document_id}` — returns SSE chat stream
   - `GET /api/v1/chat/{document_id}/history` — returns paginated chat history
   - `GET /api/v1/templates` — returns template list, no auth
2. **Auth integration tests**:
   - Requests without Authorization header return 401
   - Requests with expired token return 401
   - Requests with valid token return expected data
   - User A cannot access User B's documents (404, not 403)
3. **Pipeline integration test**:
   - Upload document -> trigger processing -> verify extraction created
   - Full LangGraph graph execution with mocked VLM provider
   - Audit trail created with correct steps
4. **Frontend page rendering tests**:
   - LandingPage renders all sections
   - Dashboard renders document grid (with mocked API)
   - Workspace renders split layout (with mocked API)

### Non-Functional

- Integration tests run in < 60 seconds
- Use in-memory SQLite via aiosqlite for database (no real Postgres needed)
- VLM providers always mocked (no external API calls)
- Frontend tests use `@testing-library/react` with `msw` for API mocking

## Implementation Plan

### Backend Integration Test Setup

**`backend/tests/integration/conftest.py`** (new file):
```python
"""Integration test fixtures — async test client with in-memory DB."""
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from unittest.mock import patch

from docmind.main import create_app
from docmind.dbase.psql.core.base import Base
from docmind.core.dependencies import get_db_session


@pytest.fixture
async def test_engine():
    """In-memory SQLite engine for tests."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest.fixture
async def test_session(test_engine):
    """Async session bound to in-memory DB."""
    session_factory = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest.fixture
def app(test_session):
    """FastAPI app with overridden DB dependency."""
    application = create_app()

    async def override_get_db():
        yield test_session

    application.dependency_overrides[get_db_session] = override_get_db
    return application


@pytest.fixture
async def client(app, auth_headers):
    """Authenticated async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers=auth_headers,
    ) as c:
        yield c


@pytest.fixture
async def unauth_client(app):
    """Unauthenticated async test client."""
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as c:
        yield c
```

### Backend Test Files

**`backend/tests/integration/modules/health/test_handler.py`**:
```python
"""Integration tests for health endpoints."""
import pytest


@pytest.mark.asyncio
async def test_health_ping_returns_200(unauth_client):
    """GET /api/v1/health/ping returns 200 without auth."""
    response = await unauth_client.get("/api/v1/health/ping")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_health_status_returns_components(unauth_client):
    """GET /api/v1/health/status returns component status list."""
    response = await unauth_client.get("/api/v1/health/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "components" in data
```

**`backend/tests/integration/modules/documents/test_handler.py`**:
```python
"""Integration tests for document API endpoints."""
import pytest


@pytest.mark.asyncio
async def test_create_document_returns_201(client, sample_document_data):
    """POST /api/v1/documents creates a document record."""
    response = await client.post("/api/v1/documents", json=sample_document_data)
    assert response.status_code == 201
    data = response.json()
    assert data["filename"] == sample_document_data["filename"]
    assert data["status"] == "uploaded"
    assert "id" in data


@pytest.mark.asyncio
async def test_list_documents_returns_paginated(client):
    """GET /api/v1/documents returns paginated list."""
    response = await client.get("/api/v1/documents?page=1&limit=20")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data


@pytest.mark.asyncio
async def test_get_document_not_found_returns_404(client):
    """GET /api/v1/documents/{id} returns 404 for nonexistent document."""
    response = await client.get("/api/v1/documents/nonexistent-id")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_create_and_get_document(client, sample_document_data):
    """Create then retrieve a document."""
    create_resp = await client.post("/api/v1/documents", json=sample_document_data)
    doc_id = create_resp.json()["id"]
    get_resp = await client.get(f"/api/v1/documents/{doc_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == doc_id


@pytest.mark.asyncio
async def test_delete_document_returns_204(client, sample_document_data):
    """DELETE /api/v1/documents/{id} removes the document."""
    create_resp = await client.post("/api/v1/documents", json=sample_document_data)
    doc_id = create_resp.json()["id"]
    delete_resp = await client.delete(f"/api/v1/documents/{doc_id}")
    assert delete_resp.status_code == 204


@pytest.mark.asyncio
async def test_unauthenticated_request_returns_401(unauth_client):
    """POST /api/v1/documents without auth returns 401."""
    response = await unauth_client.post("/api/v1/documents", json={})
    assert response.status_code == 401
```

**`backend/tests/integration/modules/extractions/test_handler.py`**:
```python
"""Integration tests for extraction endpoints."""
import pytest


@pytest.mark.asyncio
async def test_get_extraction_returns_fields(client):
    """GET /api/v1/extractions/{document_id} returns extraction with fields."""
    # Requires a processed document — create + process first
    ...


@pytest.mark.asyncio
async def test_get_audit_trail(client):
    """GET /api/v1/extractions/{document_id}/audit returns step timeline."""
    ...


@pytest.mark.asyncio
async def test_get_comparison(client):
    """GET /api/v1/extractions/{document_id}/comparison returns diff data."""
    ...
```

**`backend/tests/integration/modules/chat/test_handler.py`**:
```python
"""Integration tests for chat endpoints."""
import pytest


@pytest.mark.asyncio
async def test_get_chat_history_empty(client):
    """GET /api/v1/chat/{document_id}/history returns empty list initially."""
    ...


@pytest.mark.asyncio
async def test_chat_requires_auth(unauth_client):
    """POST /api/v1/chat/{document_id} without auth returns 401."""
    response = await unauth_client.post("/api/v1/chat/some-doc-id", json={"message": "hi"})
    assert response.status_code == 401
```

### Pipeline Integration Test

**`backend/tests/integration/test_pipeline.py`** (new file):
```python
"""Integration test for full document processing pipeline."""
import pytest
from unittest.mock import patch


@pytest.mark.asyncio
async def test_full_processing_pipeline(client, sample_document_data, mock_vlm_provider):
    """Upload → process → verify extraction created with fields."""
    # 1. Create document
    create_resp = await client.post("/api/v1/documents", json=sample_document_data)
    assert create_resp.status_code == 201
    doc_id = create_resp.json()["id"]

    # 2. Process document (mock VLM provider)
    with patch("docmind.library.providers.factory.get_vlm_provider", return_value=mock_vlm_provider):
        process_resp = await client.post(f"/api/v1/documents/{doc_id}/process", json={})
        # SSE endpoint — may return 200 with streaming response
        assert process_resp.status_code in (200, 202)

    # 3. Verify extraction was created
    ext_resp = await client.get(f"/api/v1/extractions/{doc_id}")
    assert ext_resp.status_code == 200
    data = ext_resp.json()
    assert len(data["fields"]) > 0

    # 4. Verify audit trail exists
    audit_resp = await client.get(f"/api/v1/extractions/{doc_id}/audit")
    assert audit_resp.status_code == 200
```

### Frontend Integration Tests

**`frontend/src/__tests__/pages/LandingPage.test.tsx`**:
```typescript
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { LandingPage } from "@/pages/LandingPage";

describe("LandingPage", () => {
  it("renders hero headline", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/Chat with any document/i)).toBeInTheDocument();
  });

  it("renders CTA buttons", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/Try it Free/i)).toBeInTheDocument();
  });

  it("renders feature sections", () => {
    render(
      <MemoryRouter>
        <LandingPage />
      </MemoryRouter>
    );
    expect(screen.getByText(/Extract/i)).toBeInTheDocument();
    expect(screen.getByText(/Compare/i)).toBeInTheDocument();
  });
});
```

**`frontend/src/__tests__/pages/Dashboard.test.tsx`**:
```typescript
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { queryClient } from "@/lib/query-client";
import { Dashboard } from "@/pages/Dashboard";
import { rest } from "msw";
import { setupServer } from "msw/node";

const server = setupServer(
  rest.get("http://localhost:8000/api/v1/documents", (req, res, ctx) => {
    return res(ctx.json({ items: [], total: 0, page: 1, limit: 20 }));
  }),
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

describe("Dashboard", () => {
  it("renders empty state when no documents", async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>
          <Dashboard />
        </MemoryRouter>
      </QueryClientProvider>
    );
    await waitFor(() => {
      expect(screen.getByText(/no documents/i)).toBeInTheDocument();
    });
  });
});
```

### Frontend Test Setup

```bash
cd frontend
npm install -D @testing-library/react @testing-library/jest-dom @testing-library/user-event
npm install -D vitest jsdom msw
```

**`frontend/vitest.config.ts`** (if not exists):
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test-setup.ts"],
  },
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
});
```

**`frontend/src/test-setup.ts`**:
```typescript
import "@testing-library/jest-dom";
```

## Acceptance Criteria

- [ ] All health endpoints tested (200, no auth required)
- [ ] Document CRUD endpoints tested (201, 200, 204, 404)
- [ ] Auth enforcement tested (401 for missing/expired tokens)
- [ ] User isolation tested (User A cannot see User B's docs)
- [ ] Pipeline integration test: upload -> process -> extraction created
- [ ] Chat endpoint auth tested
- [ ] Templates endpoint tested (no auth required)
- [ ] Frontend LandingPage renders all sections
- [ ] Frontend Dashboard renders with mocked API
- [ ] All integration tests pass with `pytest tests/integration/ -v`
- [ ] Frontend integration tests pass with `npm run test`
- [ ] No external service calls (DB is in-memory, VLM is mocked)

## Files Changed

### Backend:
- `backend/tests/integration/conftest.py` — new file, test client + DB setup
- `backend/tests/integration/modules/health/test_handler.py` — new
- `backend/tests/integration/modules/documents/test_handler.py` — new
- `backend/tests/integration/modules/extractions/test_handler.py` — new
- `backend/tests/integration/modules/chat/test_handler.py` — new
- `backend/tests/integration/test_pipeline.py` — new

### Frontend:
- `frontend/vitest.config.ts` — new (if not exists)
- `frontend/src/test-setup.ts` — new
- `frontend/src/__tests__/pages/LandingPage.test.tsx` — new
- `frontend/src/__tests__/pages/Dashboard.test.tsx` — new
- `frontend/src/__tests__/pages/Workspace.test.tsx` — new

## Verification

```bash
# Backend integration tests
cd backend
poetry run pytest tests/integration/ -v

# Frontend integration tests
cd frontend
npm run test

# Full test suite with coverage
cd backend
poetry run pytest tests/unit/ tests/integration/ --cov=src --cov-report=term-missing --cov-fail-under=80
```
