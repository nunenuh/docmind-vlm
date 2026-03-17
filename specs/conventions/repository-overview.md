# Repository Overview

> **Project**: DocMind-VLM — intelligent document extraction and chat platform powered by Vision Language Models.

---

## DocMind-VLM Repository Structure

Root is minimal — only infrastructure files. Each service (`backend/`, `frontend/`) is **fully independent** with its own dependency manager, Dockerfile, and `.env`.

```
docmind-vlm/                         # Root — GitHub repo root
├── Makefile                         # Project commands (make help)
├── docker-compose.yml               # Dev stack (backend + frontend + redis)
├── .env.example                     # Template for secrets
├── .gitignore
├── README.md
├── LICENSE
├── data/                            # Static data — mounted into backend container
│   ├── templates/                   # Built-in extraction templates (invoice, receipt, etc.)
│   └── demo/                        # Sample documents + expected baselines
├── docs/
│   └── blueprint/                   # PRD, SRS, ADRs, architecture docs
└── specs/                           # Implementation guide ("how to build it")
    ├── conventions/
    ├── backend/
    └── frontend/
```

### `backend/` — Independent Python Service

Has its own Poetry setup, Dockerfile, and tests. All Python source lives in `backend/src/docmind/`. No Python tooling at repo root.

```
backend/
├── pyproject.toml               # Poetry: deps + tool config
├── poetry.toml                  # Poetry local config (in-project venv)
├── poetry.lock
├── Dockerfile
│
├── src/                         # Python source root
│   └── docmind/         # ← Main package (Poetry: packages = [{include = "docmind", from = "src"}])
│       ├── __init__.py
│       ├── main.py              # FastAPI app factory (create_app)
│       ├── router.py            # Aggregates module routers under /api/v1/
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py        # Pydantic BaseSettings + get_settings() with lru_cache
│       │   ├── auth.py          # Supabase JWT verification dependency
│       │   ├── dependencies.py  # FastAPI deps (get_current_user, get_supabase_client)
│       │   └── logging.py       # structlog setup + get_logger(__name__)
│       ├── dbase/
│       │   ├── __init__.py
│       │   ├── supabase/
│       │   │   ├── __init__.py
│       │   │   ├── client.py    # Supabase client init (Auth + Storage only)
│       │   │   └── storage.py   # File upload, download, signed-URL helpers
│       │   └── psql/
│       │       ├── __init__.py   # Re-exports: Base, engine, session, models
│       │       ├── core/
│       │       │   ├── __init__.py
│       │       │   ├── base.py       # DeclarativeBase
│       │       │   ├── engine.py     # Async engine (NullPool) + lru_cache
│       │       │   ├── session.py    # async_sessionmaker + get_async_db_session()
│       │       │   └── init_db.py    # Programmatic create_all / drop_all
│       │       ├── models/           # One file per ORM model
│       │       │   ├── __init__.py
│       │       │   ├── document.py
│       │       │   ├── extraction.py
│       │       │   ├── extracted_field.py
│       │       │   ├── audit_entry.py
│       │       │   ├── chat_message.py
│       │       │   └── citation.py
│       │       ├── services/
│       │       │   └── migrate.py    # Programmatic Alembic runner CLI
│       │       └── langgraph/
│       │           └── __init__.py   # Placeholder for LangGraph checkpointer
│       ├── library/             # Reusable logic (can use frameworks, NOT tied to modules/DB)
│       │   ├── __init__.py
│       │   ├── cv/              # Classical computer vision (pure functions)
│       │   │   ├── __init__.py
│       │   │   ├── deskew.py
│       │   │   ├── quality.py
│       │   │   └── preprocessing.py
│       │   ├── providers/       # VLM provider abstraction (provider-agnostic)
│       │   │   ├── __init__.py
│       │   │   ├── protocol.py
│       │   │   ├── factory.py
│       │   │   ├── dashscope.py
│       │   │   ├── openai.py
│       │   │   ├── google.py
│       │   │   └── ollama.py
│       │   └── pipeline/        # LangGraph workflow definitions
│       │       ├── __init__.py
│       │       ├── processing.py
│       │       └── chat.py
│       ├── modules/             # Feature modules (Handler → UseCase → Service → Repository)
│       │   ├── __init__.py
│       │   ├── health/          (schemas, services, usecase, apiv1/handler)
│       │   ├── documents/       (schemas, services, repositories, usecase, apiv1/handler)
│       │   ├── extractions/     (schemas, services, repositories, usecase, apiv1/handler)
│       │   ├── chat/            (schemas, services, repositories, usecase, apiv1/handler)
│       │   └── templates/       (schemas, services, usecase, apiv1/handler)
│       └── shared/
│           ├── __init__.py
│           ├── exceptions.py    # Exception hierarchy
│           ├── utils/
│           ├── services/        # Shared services (used by multiple modules)
│           └── repositories/    # Shared repositories (used by multiple modules)
│
├── alembic/                     # Database migrations (SQLAlchemy + Alembic)
│   ├── alembic.ini
│   ├── env.py
│   └── versions/
│
└── tests/                       # All Python tests — inside backend/
    ├── conftest.py              # Shared fixtures (mock providers, mock DB session)
    ├── fixtures/
    │   ├── documents/           # Test PDFs/images
    │   └── provider_responses/  # Mock VLM responses per provider
    ├── unit/
    │   ├── library/             # cv/, providers/, pipeline/
    │   ├── modules/             # documents/, extractions/, chat/, templates/
    │   └── core/
    ├── integration/
    │   └── modules/             # documents/, extractions/, chat/, health/
    └── e2e/
        ├── processing/
        └── chat/
```

**`src/docmind/` is the Python package root.** Poetry is configured with `packages = [{include = "docmind", from = "src"}]` and pytest with `pythonpath = ["src"]`. All imports use the full package path:

```python
from docmind.core.config import get_settings           # src/docmind/core/config.py
from docmind.core.auth import get_current_user          # src/docmind/core/auth.py
from docmind.library.providers import get_vlm_provider  # src/docmind/library/providers/__init__.py
from docmind.library.cv import deskew_image             # src/docmind/library/cv/__init__.py
from docmind.library.pipeline import run_processing_pipeline  # src/docmind/library/pipeline/__init__.py
from docmind.modules.documents.services import DocumentService  # src/docmind/modules/documents/services.py
from docmind.shared.exceptions import ServiceException  # src/docmind/shared/exceptions.py
```

### `frontend/` — Independent React App

Has its own npm setup and Dockerfile. No Node tooling at root.

```
frontend/
├── package.json
├── package-lock.json
├── Dockerfile
├── .env                         # VITE_* vars (NOT committed)
├── .env.example                 # Template (committed)
├── index.html
├── vite.config.ts               # Vite config + @ path alias
├── tsconfig.json                # Strict TypeScript
├── tailwind.config.ts
├── postcss.config.js
└── src/
    ├── App.tsx                  # Router setup (landing vs workspace)
    ├── main.tsx                 # React entry point
    ├── index.css                # Tailwind + CSS variables
    ├── components/
    │   ├── ui/                  # shadcn/ui generated primitives
    │   ├── workspace/           # Document viewer, extraction, chat
    │   └── landing/             # Landing page sections
    ├── pages/
    │   ├── LandingPage.tsx
    │   ├── Dashboard.tsx
    │   └── Workspace.tsx
    ├── hooks/                   # React Query hooks
    ├── lib/
    │   ├── supabase.ts          # Supabase client init + OAuth
    │   ├── api.ts               # Backend API client (JWT-attached fetch + SSE)
    │   └── utils.ts
    ├── stores/                  # Zustand stores
    └── types/
        └── api.ts               # TypeScript interfaces mirroring backend schemas
```

---

## Tech Stack

| Layer | Technology |
| --- | --- |
| Runtime | Python 3.11+ |
| Framework | FastAPI + Uvicorn |
| Pipeline | LangGraph |
| Classical CV | OpenCV 4.x + PyMuPDF |
| VLM (default) | Qwen-VL via DashScope API |
| VLM (optional) | OpenAI GPT-4o, Google Gemini, Ollama |
| Auth | Supabase Auth (JWT) |
| ORM | SQLAlchemy 2.x (async) + Alembic |
| Database | Supabase Postgres (managed host, queried via SQLAlchemy) |
| Storage | Supabase Storage |
| Frontend | Vite + React 18+ + TypeScript 5.x |
| UI Components | shadcn/ui + Tailwind CSS |
| Server State | @tanstack/react-query 5.x |
| Local State | Zustand |
| Infra | Docker Compose |
| CI/CD | GitHub Actions |

---

## Architecture Pattern

DocMind-VLM follows a **module-based layered architecture**:

```
Handler (modules/*/apiv1/handler.py)
    ↓
UseCase (modules/*/usecase.py)
    ↓
Service (modules/*/services.py)
    ↓                   ↓
Library                 Repository (modules/*/repositories.py)
  ├── Pipeline            ↓
  ├── Providers         SQLAlchemy (dbase/psql/)
  └── CV                Supabase Storage (dbase/supabase/)
```

| Layer | Location | Responsibility |
| --- | --- | --- |
| Handler | `modules/*/apiv1/handler.py` | Thin HTTP layer — validate, authenticate, delegate to usecase |
| UseCase | `modules/*/usecase.py` | Orchestrate service + repository calls |
| Service | `modules/*/services.py` | Business logic — calls library functions (CV, providers, pipeline) |
| Repository | `modules/*/repositories.py` | Database operations — SQLAlchemy queries, always filter by user_id |
| Library | `library/` | Reusable logic — CV, VLM providers, LangGraph pipelines |
| Database (SQL) | `dbase/psql/` | Async engine (core/), ORM models (models/), Alembic migrations (services/migrate.py) |
| Database (Auth+Storage) | `dbase/supabase/` | Supabase client for JWT auth + file storage only |
| Core | `core/` | Config, auth, dependencies, logging |
| Shared | `shared/` | Exception hierarchy, shared utilities |

---

## Entry Points

| Entry Point | Run From | Command | Purpose |
| --- | --- | --- | --- |
| `backend/src/docmind/main.py` | `backend/` | `poetry run start` | FastAPI server |
| `frontend/` | `frontend/` | `npm run dev` | Vite dev server |
| `docker-compose.yml` | repo root | `docker compose up --build` | Full stack via Docker |

---

## Development Workflow

### First-time setup

```bash
# 1. Copy and fill env files
cp .env.example .env                      # Fill: VLM_PROVIDER, API keys, Supabase credentials
cp frontend/.env.example frontend/.env    # Fill: VITE_SUPABASE_URL, VITE_SUPABASE_ANON_KEY

# 2. Install backend deps
cd backend && poetry install

# 3. Run database migrations
cd backend && poetry run alembic upgrade head

# 4. Install frontend deps
cd ../frontend && npm install

# 5. Start via Docker or local
make dev                                  # Local: backend + frontend in parallel
# OR
make docker-up                            # Docker: full stack
```

### Daily development

```bash
make backend            # FastAPI dev server on port 8000
make frontend           # Vite dev server on port 5173
make dev                # Both in parallel
make test               # Run all tests
make test-unit          # Unit tests only
make test-coverage      # Tests with coverage report
```

---

## Related Conventions

- [[projects/docmind-vlm/specs/conventions/python-conventions]] — Python coding style, types, async patterns
- [[projects/docmind-vlm/specs/conventions/python-module-structure]] — Module layering detail
- [[projects/docmind-vlm/specs/conventions/testing]] — Test structure, fixtures, coverage
- [[projects/docmind-vlm/specs/conventions/security]] — Supabase JWT auth, RLS, file upload validation
