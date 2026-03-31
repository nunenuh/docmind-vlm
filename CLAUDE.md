# CLAUDE.md — docmind-vlm

## Project

Dual-mode **intelligent document platform** powered by Vision Language Models and RAG.

**Mode 1 — Document Extraction:** Upload PDFs/images → VLM extracts structured fields with confidence scores and bounding boxes → chat with the document.
**Mode 2 — Knowledge Base:** Create projects → upload multiple docs → RAG indexes everything (pgvector) → chat with a configurable AI persona across all documents.

```
Mode 1: Upload → CV Preprocess → VLM Extract → Structured Fields + Confidence → Per-Doc Chat
Mode 2: Project → Upload Docs → Text Extract → Chunk → Embed → pgvector → Persona RAG Chat
```

## Current State

- **Phase**: Core extraction pipeline complete. Knowledge Base + RAG in progress.
- **Branch**: `main` (default); `dev` for integration
- **Backend**: Extraction pipeline working end-to-end (preprocess → extract → postprocess → store). RAG pipeline in design.
- **Frontend**: Dashboard, extraction workspace, chat working. Project workspace in design.
- **Tests**: 400+ unit tests, ~88% coverage
- **Data**: Template JSONs for 5 document types + demo placeholders

## Architecture

```
Handler (FastAPI) → UseCase → Service → Repository → SQLAlchemy/Supabase
                                  ↓
                             Library (CV, Providers, Pipeline, RAG)
```

Each module in `backend/src/docmind/modules/{name}/` follows this layering.

### Two Pipeline Architectures
```
Processing Pipeline (per-doc extraction):
  preprocess (CV) → extract (VLM) → postprocess → store

RAG Chat Pipeline (project-level):
  embed_query → retrieve (pgvector) → reason (LLM + persona) → cite
```

## Key Paths

| Path | What |
|------|------|
| `backend/src/docmind/` | All backend Python source |
| `backend/tests/` | All tests (unit/integration/e2e) |
| `frontend/src/` | React + Vite app |
| `data/templates/` | Built-in extraction templates (invoice, receipt, etc.) |
| `data/demo/` | Sample documents for portfolio demo |
| `.env.example` | Environment variable template |
| `Makefile` | All project commands (`make help`) |

## Specs (read before implementing)

| Spec | When to Read |
|------|-------------|
| `specs/system.md` | Env vars, Docker, project layout, shared patterns |
| `specs/conventions/repository-overview.md` | Full repo structure, tech stack, architecture pattern |
| `specs/conventions/python-conventions.md` | Python style: PEP 8, type hints, naming, imports |
| `specs/conventions/python-module-structure.md` | Module layering: Handler → UseCase → Service → Repo |
| `specs/conventions/testing.md` | Test structure: unit / integration / e2e |
| `specs/conventions/security.md` | Supabase JWT auth, file validation |
| `specs/conventions/git-workflow.md` | Git branch/commit/PR workflow (issue-driven) |
| `specs/backend/api.md` | FastAPI routes, Pydantic models, error handling |
| `specs/backend/services.md` | Per-module services, repositories, use cases |
| `specs/backend/cv.md` | Classical CV module: deskew, quality, preprocessing |
| `specs/backend/providers.md` | VLM provider protocol, factory, 4 providers |
| `specs/backend/pipeline-processing.md` | LangGraph document processing pipeline |
| `specs/backend/pipeline-chat.md` | LangGraph chat agent pipeline + RAG chat pipeline |
| `specs/backend/projects.md` | Project + Persona data model, CRUD, API |
| `specs/backend/rag.md` | RAG pipeline v1: basic chunking, embedding, pgvector retrieval |
| `specs/backend/rag-v2.md` | RAG pipeline v2: contextual chunking, hybrid search (BM25+vector), RRF |
| `specs/backend/streaming-thinking.md` | DashScope SSE streaming with thinking/reasoning |
| `specs/frontend/components.md` | React components, shadcn/ui, TypeScript props |
| `specs/frontend/state.md` | State management: React Query + Zustand |
| `specs/frontend/api-client.md` | API client layer: fetch wrapper, types, errors (no Supabase) |
| `specs/backend/auth.md` | Auth proxy module: endpoints, GoTrue integration, JWT strategy |
| `specs/conventions/deployment.md` | Docker, GHCR, ThinkCentre deployment, Cloudflare tunnels |
| `specs/conventions/solid-refactor.md` | SOLID refactor: split usecases, protocols, DI factories |
| `specs/backend/documents-extractions-refactor.md` | Document/extraction module separation |

## Git Workflow

**All work is issue-driven.** See `specs/conventions/git-workflow.md` for full details.

```
1. Pick issue
2. git checkout dev && git pull && git checkout -b feat/<issue-id>-<slug>
3. git push -u origin feat/<issue-id>-<slug>
4. Do the work (code → tests; frontend: code → review → agree → tests)
5. Create PR targeting dev
6. Review → merge → git checkout dev && git pull && git fetch --all
```

**Commit format**: `<type>(<scope>): <description> #<issue-id>`

Types: `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `ci`

## Hard Rules

### Python Package Root
```
backend/src/docmind/    ← ALL Python source lives here
```
Poetry: `packages = [{include = "docmind", from = "src"}]`. Pytest: `pythonpath = ["src"]`.

**All imports use the full package path:**
```python
from docmind.core.config import get_settings        # CORRECT
from core.config import get_settings                # WRONG
from .config import get_settings                    # WRONG (except within same package)
```

### API Routes
All endpoints under `/api/v1/`. Prefix is split:
- `main.py` mounts the aggregated router at `/api`
- `router.py` registers each module router at `/v1/{module}`

### SSE Endpoints Are POST
`/documents/{id}/process` and `/chat/{document_id}` are **POST** with `StreamingResponse`. Never GET.

### Module Layer — Strict Separation
```
handler.py      → validates HTTP, calls usecase, serializes response. NO business logic.
usecase.py      → orchestrates service + repository calls. NO direct DB queries.
services.py     → business logic, calls library. NO direct DB access.
repositories.py → SQLAlchemy queries ONLY. Always filter by user_id.
```

### Settings
Always use `get_settings()` (cached via `@lru_cache`). Never instantiate `Settings()` directly.

### Supabase Client Scope
Supabase client is **Auth + Storage ONLY**. All DB queries go through SQLAlchemy async sessions.

### Error Handling
Never expose stack traces in HTTP responses. Log server-side with structlog, return generic message to client.

## API Endpoints

| Method | Path | Auth |
|--------|------|------|
| `GET` | `/api/v1/health/ping` | No |
| `GET` | `/api/v1/health/status` | No |
| `POST` | `/api/v1/documents` | JWT |
| `GET` | `/api/v1/documents` | JWT |
| `GET` | `/api/v1/documents/{id}` | JWT |
| `DELETE` | `/api/v1/documents/{id}` | JWT |
| `POST` | `/api/v1/documents/{id}/process` | JWT (SSE) |
| `GET` | `/api/v1/extractions/{document_id}` | JWT |
| `GET` | `/api/v1/extractions/{document_id}/audit` | JWT |
| `GET` | `/api/v1/extractions/{document_id}/overlay` | JWT |
| `GET` | `/api/v1/extractions/{document_id}/comparison` | JWT |
| `POST` | `/api/v1/chat/{document_id}` | JWT (SSE) |
| `GET` | `/api/v1/chat/{document_id}/history` | JWT |
| `GET` | `/api/v1/templates` | No |
| `POST` | `/api/v1/projects` | JWT |
| `GET` | `/api/v1/projects` | JWT |
| `GET` | `/api/v1/projects/{id}` | JWT |
| `PUT` | `/api/v1/projects/{id}` | JWT |
| `DELETE` | `/api/v1/projects/{id}` | JWT |
| `POST` | `/api/v1/projects/{id}/documents` | JWT |
| `GET` | `/api/v1/projects/{id}/documents` | JWT |
| `DELETE` | `/api/v1/projects/{id}/documents/{doc_id}` | JWT |
| `POST` | `/api/v1/projects/{id}/chat` | JWT (SSE) |
| `GET` | `/api/v1/projects/{id}/conversations` | JWT |
| `GET` | `/api/v1/projects/{id}/conversations/{conv_id}` | JWT |
| `DELETE` | `/api/v1/projects/{id}/conversations/{conv_id}` | JWT |
| `GET` | `/api/v1/personas` | JWT |
| `POST` | `/api/v1/personas` | JWT |
| `PUT` | `/api/v1/personas/{id}` | JWT |
| `DELETE` | `/api/v1/personas/{id}` | JWT |
| `POST` | `/api/v1/auth/signup` | No |
| `POST` | `/api/v1/auth/login` | No |
| `POST` | `/api/v1/auth/logout` | JWT |
| `GET` | `/api/v1/auth/session` | JWT |
| `POST` | `/api/v1/auth/refresh` | No |
| `POST` | `/api/v1/rag/search` | JWT |
| `GET` | `/api/v1/rag/chunks` | JWT |
| `GET` | `/api/v1/rag/chunks/{chunk_id}` | JWT |
| `GET` | `/api/v1/rag/stats` | JWT |
| `GET` | `/api/v1/analytics/summary` | JWT |
| `GET` | `/api/v1/documents/{id}/file` | JWT |
| `GET` | `/api/v1/documents/search` | JWT |
| `POST` | `/api/v1/extractions/{document_id}/process` | JWT (SSE) |
| `POST` | `/api/v1/extractions/classify` | JWT |
| `GET` | `/api/v1/extractions/{document_id}/export` | JWT |

## Commands

```bash
make help              # Show all commands
make setup             # First-time setup (env + deps)
make dev               # Start backend (8000) + frontend (5173)
make backend           # FastAPI dev server only
make frontend          # Vite dev server only
make docker-up         # Start Docker stack
make docker-build      # Build and start Docker stack
make docker-down       # Stop Docker stack
make test              # Run all tests
make test-unit         # Unit tests only
make test-integration  # Integration tests
make test-coverage     # Tests with coverage report
make lint              # Lint checks (ruff)
make format            # Auto-format (black + isort)
```

## Tech Stack

| Layer | Tech |
|-------|------|
| Backend | FastAPI + Python 3.11 + LangGraph + LangChain |
| Database | Supabase Postgres (via SQLAlchemy 2.x async + asyncpg) |
| Auth + Storage | Supabase (Auth + Storage client) |
| VLM | Qwen-VL via DashScope (primary); OpenAI, Google, Ollama supported |
| CV | OpenCV + PyMuPDF |
| Cache | Redis |
| Frontend | React 18 + Vite + TypeScript 5 + Tailwind + shadcn/ui |
| Server State | React Query (TanStack Query) |
| UI State | Zustand |
| Infra | Docker Compose |

## Spec Priority

When specs conflict, this order wins:

1. `specs/backend/api.md` — endpoint paths, Pydantic schemas, ORM models
2. `specs/system.md` — file layout, env vars, config
3. `specs/conventions/python-module-structure.md` — layer rules
4. Other specs — fill in details

## What's Next

1. **Backend business logic** — implement services, repositories, pipelines
2. **VLM provider integration** — DashScope provider first
3. **Frontend implementation** — build React app per `specs/frontend/` specs
4. **Tests** — unit, integration, e2e
5. **Alembic migrations** — database schema
