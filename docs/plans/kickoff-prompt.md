# DocMind-VLM — Kickoff Prompt

> **Purpose:** Copy-paste this prompt into a new Claude Code session to start building DocMind-VLM from scratch. It contains all essential context so the agent can work autonomously.

---

## Project Overview

**DocMind-VLM** is an intelligent document extraction and chat platform powered by Vision Language Models (VLMs). Users upload documents (PDFs, images), the system extracts structured data using classical CV preprocessing + VLM inference, and provides a document-aware chat interface.

**This is a portfolio/product project** — not a client deliverable. Build it clean, tested, and production-shaped.

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.11+, FastAPI, Uvicorn |
| **Pipeline** | LangGraph (StateGraph workflows) |
| **Classical CV** | OpenCV 4.x + PyMuPDF |
| **VLM (default)** | Qwen-VL via DashScope API |
| **VLM (optional)** | OpenAI GPT-4o, Google Gemini, Ollama |
| **Auth** | Supabase Auth (JWT) |
| **ORM** | SQLAlchemy 2.x (async) + Alembic |
| **Database** | Supabase Postgres (managed host, queried via SQLAlchemy) |
| **Storage** | Supabase Storage |
| **Frontend** | Vite + React 18+ + TypeScript 5.x |
| **UI** | shadcn/ui + Tailwind CSS |
| **Server State** | @tanstack/react-query 5.x |
| **Local State** | Zustand |
| **Infra** | Docker Compose |

---

## Repository Structure

```
docmind-vlm/                         # Repo root
├── Makefile
├── docker-compose.yml
├── .env.example
├── .gitignore
├── README.md
├── data/
│   ├── templates/                   # Built-in extraction templates (invoice.json, receipt.json, etc.)
│   └── demo/                        # Sample documents + expected baselines
├── docs/
│   └── blueprint/                   # PRD, SRS, ADRs, architecture (READ-ONLY reference)
├── specs/                           # Implementation specs (HOW to build — your primary reference)
│
├── backend/                         # Independent Python service
│   ├── pyproject.toml               # Poetry config
│   ├── poetry.toml
│   ├── Dockerfile
│   ├── alembic/                     # Database migrations
│   │   ├── alembic.ini
│   │   ├── env.py
│   │   └── versions/
│   ├── src/
│   │   └── docmind/                 # ← Python package root
│   │       ├── __init__.py
│   │       ├── main.py              # FastAPI app factory (create_app)
│   │       ├── router.py            # Aggregates module routers under /api/v1/
│   │       ├── core/                # Config, auth, dependencies, logging
│   │       ├── dbase/
│   │       │   ├── sqlalchemy/      # engine.py, base.py, models.py (DB queries)
│   │       │   └── supabase/        # client.py (Auth + Storage ONLY)
│   │       ├── library/             # Reusable logic (NOT tied to modules)
│   │       │   ├── cv/              # Classical CV (deskew, quality, preprocessing)
│   │       │   ├── providers/       # VLM provider protocol + 4 implementations
│   │       │   └── pipeline/        # LangGraph workflows (processing, chat)
│   │       ├── modules/             # Feature modules (Handler → UseCase → Service → Repo)
│   │       │   ├── health/
│   │       │   ├── documents/
│   │       │   ├── extractions/
│   │       │   ├── chat/
│   │       │   └── templates/
│   │       └── shared/              # Exceptions, shared utils/services/repos
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── e2e/
│
└── frontend/                        # Independent React app
    ├── package.json
    ├── Dockerfile
    └── src/
        ├── components/              # ui/ (shadcn), workspace/, landing/
        ├── pages/                   # LandingPage, Dashboard, Workspace
        ├── hooks/                   # React Query hooks
        ├── lib/                     # supabase.ts, api.ts, utils.ts
        ├── stores/                  # Zustand stores
        └── types/                   # TypeScript interfaces mirroring backend schemas
```

---

## Architecture: Module-per-Feature Layered Pattern

```
Handler (modules/*/apiv1/handler.py)    ← Thin HTTP: validate, auth, delegate
    ↓
UseCase (modules/*/usecase.py)          ← Orchestrate service + repository
    ↓
Service (modules/*/services.py)         ← Business logic, calls library/
    ↓                   ↓
Library                 Repository (modules/*/repositories.py)
  ├── Pipeline            ↓
  ├── Providers         SQLAlchemy (dbase/psql/)
  └── CV
```

**Dependency rules:**
- Handlers → UseCases only (never services/repos directly)
- UseCases → Services + Repositories
- Services → Library only (never repos/dbase)
- Repositories → dbase/psql only
- Library → core/ + dbase/ (for pipeline store node); NEVER imports from modules/

**All imports use full package path:**
```python
from docmind.core.config import get_settings
from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.library.providers import get_vlm_provider
from docmind.library.cv import deskew_image
from docmind.library.pipeline import run_processing_pipeline
from docmind.modules.documents.services import DocumentService
from docmind.shared.exceptions import ServiceException
```

---

## Key Patterns & Conventions

### Python
- **Package**: `backend/src/docmind/` — Poetry: `packages = [{include = "docmind", from = "src"}]`
- **Config**: Pydantic `BaseSettings` + `get_settings()` with `@lru_cache`. Never use `os.environ`.
- **Logging**: `structlog` via `get_logger(__name__)`. Keyword args only: `logger.info("msg", key=val)`. NO printf-style.
- **Errors**: Typed exception hierarchy from `shared/exceptions.py`. Never bare `except:`.
- **Immutability**: Always return new objects, never mutate in place.
- **Type hints**: Required on all functions. No exceptions.
- **File limits**: Max 400 lines/file, 50 lines/function.
- **Async**: All handler/usecase/service/repository methods are `async`.
- **DB access**: SQLAlchemy async sessions for all queries. Always filter by `user_id` for ownership enforcement. Supabase client for Auth + Storage only.

### Auth
- Supabase JWT tokens. Backend verifies via `core/auth.py` → `get_current_user` dependency.
- Frontend handles OAuth flow via Supabase JS client.
- All protected routes use `Depends(get_current_user)`.

### VLM Providers
- Protocol-based abstraction in `library/providers/protocol.py`.
- Factory in `library/providers/factory.py` reads `VLM_PROVIDER` env var.
- 4 implementations: DashScope (default), OpenAI, Google, Ollama.
- Only the active provider's API key is required.

### Testing
- pytest + pytest-asyncio. `pythonpath = ["src"]` in pyproject.toml.
- Coverage target: ≥ 80%. Command: `poetry run pytest tests/ --cov=docmind --cov-report=term-missing`
- Test file mirrors source: `src/docmind/library/cv/deskew.py` → `tests/unit/library/cv/test_deskew.py`
- Mock VLM providers in tests — never make real API calls in unit tests.

---

## Implementation Spec Files (Your Primary Reference)

Read these specs BEFORE implementing each layer. They contain exact code examples, schemas, and patterns:

| Spec | What It Covers |
|------|---------------|
| `specs/system.md` | Env vars, Docker Compose, pyproject.toml, shared patterns, file layout |
| `specs/conventions/repository-overview.md` | Full project structure, tech stack, dev workflow |
| `specs/conventions/python-conventions.md` | PEP 8, type hints, naming, imports, error handling |
| `specs/conventions/python-module-structure.md` | Module layering (Handler → UseCase → Service → Repo) with full code examples |
| `specs/conventions/testing.md` | Test structure, fixtures, mocking, CI workflow |
| `specs/conventions/security.md` | Supabase JWT auth, RLS policies, file upload validation |
| `specs/backend/api.md` | FastAPI routes, Pydantic schemas, error handling, CORS, main.py, router.py |
| `specs/backend/cv.md` | Classical CV: deskew, quality assessment, PDF preprocessing |
| `specs/backend/providers.md` | VLM provider protocol, factory, all 4 provider implementations |
| `specs/backend/pipeline-processing.md` | LangGraph document processing pipeline (preprocess → extract → postprocess → store) |
| `specs/backend/pipeline-chat.md` | LangGraph chat agent pipeline (router → retrieve → reason → cite) |
| `specs/backend/services.md` | Per-module services, repositories, use cases for all 5 modules |
| `specs/frontend/components.md` | React component tree, shadcn/ui usage |
| `specs/frontend/state.md` | React Query + Zustand state management |
| `specs/frontend/api-client.md` | Supabase client + backend API client layer |

**Blueprint docs** (`docs/blueprint/`) are READ-ONLY design references — PRD, SRS, ADRs, architecture. Consult when you need "why" decisions, not "how to build."

---

## Suggested Build Order

### Phase 1: Foundation
1. **Repo scaffolding** — Makefile, docker-compose.yml, .env.example, .gitignore, README.md
2. **Backend skeleton** — pyproject.toml, poetry.toml, Dockerfile, `src/docmind/__init__.py`
3. **Core layer** — config.py, logging.py, auth.py, dependencies.py
4. **Shared layer** — exceptions.py hierarchy
5. **Database layer** — dbase/psql/ (engine.py, base.py, models.py) + dbase/supabase/ (client.py for Auth+Storage)
6. **Alembic setup** — alembic.ini, env.py, initial migration
7. **Health module** — First complete module end-to-end (schemas → service → usecase → handler)
8. **main.py + router.py** — App factory, mount health router, verify Docker Compose boots

### Phase 2: Library Layer
9. **CV library** — preprocessing.py (PDF→images), deskew.py, quality.py
10. **Provider protocol** — protocol.py (VLMProvider Protocol), factory.py
11. **DashScope provider** — First concrete VLM provider implementation
12. **Other providers** — OpenAI, Google, Ollama (same interface)

### Phase 3: Document Processing
13. **Documents module** — schemas, repository, service, usecase, handler (upload, list, get, delete)
14. **Templates module** — Load from data/templates/*.json, list/get endpoints
15. **Processing pipeline** — LangGraph StateGraph (preprocess → extract → postprocess → store)
16. **Extractions module** — Results, audit trail, overlay, comparison endpoints

### Phase 4: Chat
17. **Chat pipeline** — LangGraph StateGraph (router → retrieve → reason → cite)
18. **Chat module** — SSE streaming endpoint, message history, citations

### Phase 5: Frontend
19. **Frontend skeleton** — Vite + React + TypeScript + Tailwind + shadcn/ui
20. **Auth flow** — Supabase OAuth, AuthGuard, auth store
21. **Landing page** — Hero, Features, Demo, Footer
22. **API client layer** — JWT-attached fetch, SSE helper, React Query hooks
23. **Dashboard** — Document list, upload area
24. **Workspace** — Document viewer, extraction panel, chat panel, processing progress

### Phase 6: Polish
25. **Compare panel** — Side-by-side extraction comparison
26. **Dark mode** — CSS variable theming
27. **Docker optimization** — Multi-stage builds, health checks
28. **CI/CD** — GitHub Actions (lint, test, build)

---

## Critical Warnings

1. **IGNORE `docs/plans/2026-03-11-chunks-4-7.md`** — This file is OUTDATED. It uses the old flat `app/` structure. The correct architecture is `backend/src/docmind/`. Follow the specs, not the plans file.

2. **SQLAlchemy + Supabase hybrid** — SQLAlchemy (async) for all database queries. Supabase Python client for Auth (JWT) + Storage ONLY. Never use the Supabase client for database queries.

3. **Ownership enforcement in repositories** — Backend connects to Supabase Postgres as `postgres` superuser, bypassing Supabase RLS. All repositories MUST filter by `user_id` to enforce ownership at the application level.

4. **structlog, not stdlib logging** — Always `from docmind.core.logging import get_logger`. Never `import logging`.

5. **Keyword args in logging** — `logger.info("Processing", doc_id=doc_id)`. NEVER `logger.info("Processing %s", doc_id)`.

6. **Package name is `docmind`** — Not `docmind_service`, not `app`, not `backend`. Import as `from docmind.xxx import yyy`.

---

## Environment Setup

```bash
# 1. Create repo
mkdir docmind-vlm && cd docmind-vlm
git init

# 2. Backend setup
mkdir -p backend/src/docmind backend/tests
cd backend
poetry init  # Configure per specs/system.md pyproject.toml section
poetry install

# 3. Frontend setup
cd ../frontend
npm create vite@latest . -- --template react-ts
npm install

# 4. Supabase
# Create project at supabase.com
# Get URL, anon key, service role key, DATABASE_URL (connection string)
# Tables are managed via Alembic migrations (NOT Supabase dashboard)

# 5. Alembic migrations
cd backend
poetry run alembic upgrade head  # Apply all migrations

# 6. Environment
cp .env.example .env  # Fill in DATABASE_URL, Supabase keys, VLM provider keys
cp frontend/.env.example frontend/.env

# 7. Run
make dev  # or docker compose up --build
```

---

## When Starting Each Task

1. **Read the relevant spec file first** — e.g., before building providers, read `specs/backend/providers.md`
2. **Follow TDD** — Write test first (RED), implement (GREEN), refactor (IMPROVE)
3. **Stay within layer boundaries** — Handlers don't call services directly. Services don't touch the database.
4. **One module at a time** — Complete schemas → repo → service → usecase → handler → tests before moving on.
