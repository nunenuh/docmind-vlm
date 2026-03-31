# System Spec — DocMind-VLM

Overall conventions that apply across the entire project.

---

## Project Layout

Root is minimal — only infrastructure files. Each service is fully independent.

```
docmind-vlm/                        # Repo root
├── Makefile                         # Project commands (make help)
├── docker-compose.yml               # Dev stack (backend + frontend + redis)
├── .env.example                     # Template for secrets
├── .env                             # NOT committed — copy from .env.example
├── .gitignore
├── README.md
├── LICENSE
├── data/                            # Static data — mounted into backend container
│   ├── templates/                   # Built-in extraction templates
│   │   ├── invoice.json
│   │   ├── receipt.json
│   │   ├── contract.json
│   │   └── certificate.json
│   └── demo/                        # Sample documents for portfolio demo
│       ├── documents/               # Sample PDFs/images
│       └── baselines/               # Expected extraction outputs
└── docs/
    └── blueprint/                   # PRD, SRS, ADRs, architecture docs

backend/                             # Independent Python service
├── pyproject.toml                   # Poetry: deps + tool config
├── poetry.toml                      # Poetry local config (in-project venv)
├── poetry.lock
├── Dockerfile
│
├── src/                             # Python source root
│   └── docmind/             # ← Main package (Poetry: packages = [{include = "docmind", from = "src"}])
│       ├── __init__.py
│       ├── main.py                  # FastAPI app factory (create_app)
│       ├── router.py                # Aggregates module routers under /api/v1/
│       ├── core/
│       │   ├── __init__.py
│       │   ├── config.py            # Pydantic BaseSettings + get_settings() with lru_cache
│       │   ├── auth.py              # Supabase JWT verification dependency
│       │   ├── dependencies.py      # FastAPI deps (get_current_user, get_supabase_client)
│       │   └── logging.py           # structlog setup + get_logger(__name__)
│       ├── dbase/
│       │   ├── __init__.py
│       │   ├── supabase/
│       │   │   ├── __init__.py
│       │   │   ├── client.py        # Supabase client init (Auth + Storage only)
│       │   │   └── storage.py       # File upload, download, signed-URL helpers
│       │   └── psql/
│       │       ├── __init__.py      # Re-exports: Base, engine, session, models
│       │       ├── core/
│       │       │   ├── __init__.py   # Re-exports: Base, engine, session, init_db
│       │       │   ├── base.py       # DeclarativeBase
│       │       │   ├── engine.py     # Async engine (NullPool) + lru_cache factory
│       │       │   ├── session.py    # async_sessionmaker + get_async_db_session()
│       │       │   └── init_db.py    # Programmatic create_all / drop_all
│       │       ├── models/
│       │       │   ├── __init__.py   # Re-exports all 6 ORM models
│       │       │   ├── document.py
│       │       │   ├── extraction.py
│       │       │   ├── extracted_field.py
│       │       │   ├── audit_entry.py
│       │       │   ├── chat_message.py
│       │       │   ├── citation.py
│       │       │   ├── project.py
│       │       │   ├── persona.py
│       │       │   ├── project_conversation.py
│       │       │   ├── project_message.py
│       │       │   └── page_chunk.py
│       │       ├── services/
│       │       │   ├── __init__.py
│       │       │   └── migrate.py    # Programmatic Alembic runner (upgrade/downgrade/generate CLI)
│       │       └── langgraph/
│       │           └── __init__.py   # Placeholder for LangGraph checkpointer
│       ├── library/                 # Reusable logic (can use frameworks, NOT tied to modules/DB)
│       │   ├── __init__.py
│       │   ├── cv/                  # Classical computer vision (pure functions)
│       │   │   ├── __init__.py      # Re-exports: deskew_image, assess_quality, convert_to_page_images
│       │   │   ├── deskew.py        # Hough line skew detection + correction
│       │   │   ├── quality.py       # Region-based blur/noise/contrast assessment
│       │   │   └── preprocessing.py # PDF→image (PyMuPDF), normalize, denoise
│       │   ├── providers/           # VLM provider abstraction (provider-agnostic)
│       │   │   ├── __init__.py      # Re-exports: get_vlm_provider, VLMProvider, VLMResponse
│       │   │   ├── protocol.py      # VLMProvider Protocol (extract, classify, chat)
│       │   │   ├── factory.py       # VLM_PROVIDER env var → concrete provider instance
│       │   │   ├── dashscope.py     # Qwen-VL via DashScope API
│       │   │   ├── openai.py        # GPT-4o via OpenAI API
│       │   │   ├── google.py        # Gemini via Google AI API
│       │   │   └── ollama.py        # Local models via Ollama
│       │   ├── rag/                 # RAG pipeline (text extraction, chunking, embedding, retrieval)
│       │   │   ├── __init__.py      # Re-exports: index_document_for_rag, retrieve_chunks
│       │   │   ├── text_extract.py  # extract_text_from_pdf(), extract_text_from_image()
│       │   │   ├── chunker.py       # chunk_text() — recursive character splitting
│       │   │   ├── embedder.py      # EmbeddingProvider protocol, DashScopeEmbedder, get_embedder()
│       │   │   ├── retriever.py     # retrieve_chunks() — cosine similarity search
│       │   │   └── indexer.py       # index_document_for_rag() — orchestrates extract → chunk → embed → store
│       │   └── pipeline/            # LangGraph workflow definitions
│       │       ├── __init__.py      # Re-exports: run_processing_pipeline, run_chat_pipeline
│       │       ├── processing.py    # Document processing StateGraph
│       │       │                    #   nodes: preprocess → extract → postprocess → store
│       │       └── chat.py          # Chat agent StateGraph
│       │                            #   nodes: router → retrieve → reason → cite
│       ├── modules/                 # Feature modules — SOLID architecture
│       │   │                        # Each module has: protocols.py, dependencies.py,
│       │   │                        # schemas.py, usecase.py (or usecases/), services/,
│       │   │                        # repositories.py (or repositories/), apiv1/handler.py
│       │   ├── __init__.py
│       │   ├── auth/                # Authentication (proxies GoTrue REST)
│       │   ├── health/              # Health checks
│       │   ├── documents/           # Document CRUD + file serving
│       │   ├── extractions/         # Extraction pipeline trigger + results (usecases/ split)
│       │   ├── chat/                # Per-document VLM chat
│       │   ├── templates/           # Extraction template CRUD (seeded from JSON)
│       │   ├── projects/            # Knowledge base projects (usecases/ split into 4)
│       │   ├── personas/            # AI persona CRUD (seeded from JSON)
│       │   ├── rag/                 # Independent RAG module (indexing, retrieval, search)
│       │   └── analytics/           # Dashboard stats
│       └── shared/
│           ├── __init__.py
│           ├── exceptions.py        # Exception hierarchy
│           ├── utils/
│           │   └── __init__.py
│           ├── services/            # Shared services (used by multiple modules)
│           │   └── __init__.py
│           └── repositories/        # Shared repositories (used by multiple modules)
│               └── __init__.py
│
├── alembic/                         # Database migrations
│   ├── alembic.ini
│   ├── env.py
│   └── versions/                    # Migration scripts
│
└── tests/                           # All Python tests — inside backend/
    ├── conftest.py                  # Shared fixtures: mock_vlm_provider, mock_supabase, sample_document
    ├── fixtures/
    │   ├── documents/               # Test PDFs/images
    │   └── provider_responses/      # Mock VLM responses per provider
    │       ├── dashscope/
    │       ├── openai/
    │       └── google/
    ├── unit/
    │   ├── conftest.py
    │   ├── library/
    │   │   ├── cv/
    │   │   ├── providers/
    │   │   └── pipeline/
    │   ├── modules/
    │   │   ├── documents/
    │   │   ├── extractions/
    │   │   ├── chat/
    │   │   └── templates/
    │   └── core/
    ├── integration/
    │   └── modules/
    │       ├── documents/
    │       ├── extractions/
    │       ├── chat/
    │       └── health/
    └── e2e/
        ├── processing/
        └── chat/

frontend/                            # Independent React app
├── package.json
├── package-lock.json
├── Dockerfile
├── .env                             # VITE_* vars (NOT committed)
├── .env.example                     # Template (committed)
├── index.html
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.ts
├── postcss.config.js
└── src/
    ├── App.tsx                      # Router setup (landing vs workspace)
    ├── main.tsx                     # React entry point
    ├── index.css                    # Tailwind + CSS variables (light/dark themes)
    ├── components/
    │   ├── ui/                      # shadcn/ui generated components
    │   ├── project/                 # Project dashboard, document list, persona selector
    │   ├── workspace/               # Document viewer, extraction panel, chat
    │   │   ├── UploadArea.tsx
    │   │   ├── DocumentViewer.tsx
    │   │   ├── ExtractionPanel.tsx
    │   │   ├── ChatPanel.tsx
    │   │   ├── ProcessingProgress.tsx
    │   │   ├── ComparePanel.tsx
    │   │   ├── ConfidenceBadge.tsx
    │   │   ├── CitationBlock.tsx
    │   │   └── AuthGuard.tsx
    │   └── landing/                 # Landing page sections
    │       ├── Hero.tsx
    │       ├── Features.tsx
    │       ├── Demo.tsx
    │       └── Footer.tsx
    ├── pages/
    │   ├── LandingPage.tsx
    │   ├── Dashboard.tsx
    │   ├── Workspace.tsx
    │   ├── ProjectDashboard.tsx
    │   └── ProjectWorkspace.tsx
    ├── hooks/                       # React Query hooks
    │   ├── useDocuments.ts
    │   ├── useExtraction.ts
    │   ├── useChat.ts
    │   ├── useTemplates.ts
    │   ├── useProjects.ts
    │   └── usePersonas.ts
    ├── lib/
    │   ├── supabase.ts              # Supabase client init + OAuth helpers
    │   ├── api.ts                   # Backend API client (JWT-attached fetch + SSE)
    │   └── utils.ts                 # Shared utilities
    ├── stores/                      # Zustand stores
    │   ├── workspace-store.ts       # Active tab, overlay mode, selected field, zoom
    │   └── auth-store.ts            # Session, user
    └── types/
        └── api.ts                   # TypeScript interfaces mirroring backend schemas
```

---

## Environment Variables

**Two env files — root `.env` serves Docker and backend, frontend has its own.**

| File | Where | Purpose | Committed? |
|------|-------|---------|-----------|
| `.env.example` | repo root | Template with placeholder values | Yes |
| `.env` | repo root | Secrets for local dev + Docker Compose | No |
| `frontend/.env` | `frontend/` | Frontend vars (`VITE_*`) | No |
| `frontend/.env.example` | `frontend/` | Template for frontend vars | Yes |

### Root `.env.example` → copy to `.env`

Used by Docker Compose (`env_file: ./.env`) and by the backend running locally.

```bash
# .env  (copy from .env.example, fill in values)

# VLM Provider Selection
VLM_PROVIDER=dashscope              # One of: dashscope, openai, google, ollama

# DashScope (Qwen-VL)
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_MODEL=qwen-vl-max

# OpenAI (GPT-4o)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Google (Gemini)
GOOGLE_API_KEY=AI...
GOOGLE_MODEL=gemini-2.0-flash

# Ollama (local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llava

# Supabase (Auth + Storage)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Database (Supabase Postgres via SQLAlchemy — individual vars)
DB_HOST=aws-0-[region].pooler.supabase.com
DB_PORT=6543
DB_USER=postgres.[project-ref]
DB_PASSWORD=your-password
DB_NAME=postgres

# Redis (optional — for job queue)
REDIS_URL=redis://redis:6379/0

# App
APP_NAME="DocMind-VLM"
APP_VERSION="0.1.0"
APP_ENVIRONMENT=development
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=true
LOG_LEVEL=INFO

# CORS
ALLOWED_ORIGINS_STR=http://localhost:5173,http://localhost:3000

# Data
DATA_DIR=data

# RAG
EMBEDDING_PROVIDER=dashscope
EMBEDDING_MODEL=text-embedding-v3
EMBEDDING_DIMENSIONS=1024
RAG_CHUNK_SIZE=512
RAG_CHUNK_OVERLAP=64
RAG_TOP_K=8
RAG_SIMILARITY_THRESHOLD=0.3
```

### `frontend/.env`

Only Vite-prefixed vars. These are embedded into the JS bundle at build time.

```bash
# frontend/.env
VITE_API_URL=http://localhost:8000
VITE_SUPABASE_URL=https://your-project.supabase.co
VITE_SUPABASE_ANON_KEY=eyJ...
```

Access in code: `import.meta.env.VITE_API_URL`
**NOT** `process.env.*` — this is Vite, not Node/Next.js.

### `docmind/core/config.py`

```python
from functools import lru_cache
from pydantic import ConfigDict, Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")

    # App
    APP_NAME: str = Field(default="DocMind-VLM")
    APP_VERSION: str = Field(default="0.1.0")
    APP_ENVIRONMENT: str = Field(default="development")
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    APP_DEBUG: bool = Field(default=False)
    LOG_LEVEL: str = Field(default="INFO")
    ALLOWED_ORIGINS_STR: str = Field(default="http://localhost:5173,http://localhost:3000")

    # VLM Provider
    VLM_PROVIDER: str = Field(default="dashscope")

    # DashScope
    DASHSCOPE_API_KEY: str = Field(default="")
    DASHSCOPE_MODEL: str = Field(default="qwen-vl-max")

    # OpenAI
    OPENAI_API_KEY: str = Field(default="")
    OPENAI_MODEL: str = Field(default="gpt-4o")

    # Google
    GOOGLE_API_KEY: str = Field(default="")
    GOOGLE_MODEL: str = Field(default="gemini-2.0-flash")

    # Ollama
    OLLAMA_BASE_URL: str = Field(default="http://localhost:11434")
    OLLAMA_MODEL: str = Field(default="llava")

    # Supabase (Auth + Storage)
    SUPABASE_URL: str = Field(default="")
    SUPABASE_PUBLISHABLE_KEY: str = Field(default="")
    SUPABASE_SECRET_KEY: str = Field(default="")

    # Database (Supabase Postgres via SQLAlchemy — individual vars)
    DB_HOST: str = Field(default="localhost")
    DB_PORT: int = Field(default=5432)
    DB_USER: str = Field(default="postgres")
    DB_PASSWORD: str = Field(default="")
    DB_NAME: str = Field(default="postgres")

    @property
    def database_url(self) -> str:
        """Build async database URL from individual components."""
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    # Redis
    REDIS_URL: str = Field(default="redis://localhost:6379/0")

    # Data
    DATA_DIR: str = Field(default="data")

    # RAG
    EMBEDDING_PROVIDER: str = Field(default="dashscope")
    EMBEDDING_MODEL: str = Field(default="text-embedding-v3")
    EMBEDDING_DIMENSIONS: int = Field(default=1024)
    RAG_CHUNK_SIZE: int = Field(default=512)
    RAG_CHUNK_OVERLAP: int = Field(default=64)
    RAG_TOP_K: int = Field(default=8)
    RAG_SIMILARITY_THRESHOLD: float = Field(default=0.3)

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS_STR.split(",")]


@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

**Rule**: Import `get_settings` from `docmind.core.config` everywhere. Never use `os.environ` directly.

**Rule**: Only the active provider's API key is required. If `VLM_PROVIDER=dashscope`, only `DASHSCOPE_API_KEY` must be set. The factory validates this at startup.

---

## Docker Compose

Each service builds from its own directory. Env vars come from root `.env`.

```yaml
# docker-compose.yml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: docmind-backend
    ports:
      - "8000:8000"
    env_file:
      - ./.env
    volumes:
      - ./backend/src:/app/src
      - ./data:/app/data
    depends_on:
      - redis
    networks:
      - docmind-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: docmind-frontend
    ports:
      - "5173:5173"
    environment:
      VITE_API_URL: http://localhost:8000
    depends_on:
      - backend
    networks:
      - docmind-network

  redis:
    image: redis:7-alpine
    container_name: docmind-redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    networks:
      - docmind-network

# Note: Supabase is external (cloud-hosted). Not included in Docker Compose.

networks:
  docmind-network:
    driver: bridge

volumes:
  redis_data:
```

**`backend/Dockerfile` — key lines:**
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml poetry.lock* ./
RUN pip install --no-cache-dir poetry && poetry install --only main --no-root --no-cache
COPY . .
EXPOSE 8000
CMD ["poetry", "run", "start"]
```

**Setup and daily commands via Makefile (run from repo root):**

```bash
# First-time setup
make setup              # Creates .env + installs deps
make docker-up          # Start all services (backend + frontend + redis)

# Daily development
make backend            # FastAPI dev server on port 8000
make frontend           # Vite dev server on port 5173
make dev                # Both in parallel

# Docker (full stack)
make docker-up          # Start all services
make docker-build       # Build and start all services
make docker-down        # Stop all services

# Testing
make test               # All tests
make test-unit          # Unit tests only
make test-integration   # Integration tests (requires Supabase)
make test-coverage      # Tests with coverage report
```

---

## Shared Patterns

### Error Handling

All Python functions must raise typed exceptions from `shared/exceptions.py`.

```python
# Exception hierarchy
BaseServiceException
├── ValidationException
├── RepositoryException
│   └── SupabaseConnectionException
├── ServiceException
│   └── ProviderException
├── PipelineException
└── BaseHTTPException (extends FastAPI HTTPException)
```

```python
# Good
try:
    result = await provider.extract(image, template)
except ProviderError as e:
    raise ProviderException(f"VLM extraction failed: {e}")

# Bad — never do this
try:
    result = await provider.extract(image, template)
except:
    return None
```

### Logging

Uses **structlog** configured in `core/logging.py`. Get logger via `get_logger(__name__)`.

```python
from docmind.core.logging import get_logger
logger = get_logger(__name__)

# Structured context via keyword args
logger.info("Processing document", doc_id=doc_id, provider=provider_name)
logger.error("Provider call failed", error=str(e), provider=provider_name)
```

### Database Access (SQLAlchemy + Supabase Hybrid)

| Concern | Tool |
|---------|------|
| Database schema & queries | SQLAlchemy + Alembic |
| Auth (JWT) | Supabase Auth |
| File storage | Supabase Storage SDK |
| Connection | `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` → computed `database_url` property → async SQLAlchemy engine |

**Supabase is the managed Postgres host.** SQLAlchemy connects to it via a URL built from individual `DB_*` env vars. Supabase RLS is bypassed because the backend connects as `postgres` (superuser) — ownership is enforced in the repository layer by filtering on `user_id`.

```python
# dbase/psql/core/engine.py
from functools import lru_cache
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine as sa_create
from sqlalchemy.pool import NullPool
from docmind.core.config import get_settings

def create_async_engine() -> AsyncEngine:
    settings = get_settings()
    return sa_create(settings.database_url, poolclass=NullPool, echo=settings.APP_DEBUG)

@lru_cache()
def get_async_engine() -> AsyncEngine:
    return create_async_engine()
```

```python
# dbase/psql/core/session.py
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from .engine import get_async_engine

AsyncSessionLocal = async_sessionmaker(
    bind=get_async_engine(), class_=AsyncSession,
    expire_on_commit=False, autocommit=False, autoflush=False,
)

async def get_async_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
```

```python
# dbase/psql/core/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

```python
# Repository usage
from docmind.dbase.psql.core.session import get_async_db_session

class DocumentRepository:
    async def get_by_id(self, document_id: str, user_id: str) -> Document | None:
        async with AsyncSessionLocal() as session:
            stmt = select(Document).where(
                Document.id == document_id,
                Document.user_id == user_id,  # ownership enforcement
            )
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
```

### Immutability

Always return new objects, never mutate in place:

```python
# Good
def normalize_extraction(raw: dict, template: dict) -> dict:
    return {
        "fields": {k: raw.get(k, "") for k in template["fields"]},
        "confidence": raw.get("confidence", 0.0),
        "provider": raw["provider"],
    }

# Bad — mutates input
def normalize_extraction(raw: dict, template: dict) -> dict:
    raw["fields"] = {k: raw.get(k, "") for k in template["fields"]}
    return raw
```

### Type Hints

All functions require type hints. No exceptions.

```python
# Good
async def extract_document(image: bytes, template: dict) -> ExtractionResult:
    ...

def assess_quality(image: np.ndarray) -> RegionQuality:
    ...

# Bad
def extract_document(image, template):
    ...
```

### File Size Limits

- Max 400 lines per file
- Max 50 lines per function
- If a file grows beyond 400 lines, split by responsibility

---

## Testing

Tests live **inside each service** — not at repo root.

| Service | Test dir | Runner | Coverage |
|---------|---------|--------|---------|
| Backend | `backend/tests/` | `poetry run pytest` | >= 80% |
| Frontend | `frontend/src/` (co-located or `__tests__/`) | `npm run test` (vitest) | >= 80% |

```bash
# Backend tests (from repo root via Makefile)
make test                  # All tests
make test-unit             # Unit tests only
make test-integration      # Integration tests (requires Supabase)
make test-coverage         # Tests with coverage report

# Or from backend/
cd backend
poetry run pytest tests/ -v
poetry run pytest tests/ --cov=docmind --cov-report=term-missing --cov-fail-under=80
```

Test file mirrors source file (from `docmind/` perspective):
```
backend/src/docmind/library/cv/deskew.py             ↔  backend/tests/unit/library/cv/test_deskew.py
backend/src/docmind/library/providers/dashscope.py   ↔  backend/tests/unit/library/providers/test_dashscope.py
backend/src/docmind/modules/documents/services.py    ↔  backend/tests/unit/modules/documents/test_services.py
backend/src/docmind/modules/extractions/services.py  ↔  backend/tests/unit/modules/extractions/test_services.py
backend/src/docmind/modules/documents/apiv1/handler.py ↔  backend/tests/integration/modules/documents/test_handler.py
```

Note: `--cov=docmind` measures coverage of the package.

**Alembic migrations (from `backend/`):**
```bash
# Via programmatic CLI (preferred — uses docmind.dbase.psql.services.migrate)
poetry run python -m docmind.dbase.psql.services.migrate upgrade
poetry run python -m docmind.dbase.psql.services.migrate downgrade
poetry run python -m docmind.dbase.psql.services.migrate generate "add new column"
poetry run python -m docmind.dbase.psql.services.migrate current
poetry run python -m docmind.dbase.psql.services.migrate history

# Or via Alembic directly
cd backend && poetry run alembic revision --autogenerate -m "add documents table"
poetry run alembic upgrade head
poetry run alembic downgrade -1
```

---

## Code Style

### Python (`backend/pyproject.toml`)

```toml
[tool.poetry]
name = "docmind-vlm-backend"
version = "0.1.0"
description = "VLM-powered document intelligence backend"
packages = [{include = "docmind", from = "src"}]

[tool.poetry.scripts]
start = "docmind.main:main"
dev = "docmind.main:dev"

[tool.poetry.dependencies]
python = "^3.11"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.30"}
pydantic = "^2.7"
pydantic-settings = "^2.4"
structlog = "^24.1"
supabase = "^2.0"
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
asyncpg = "^0.30"
alembic = "^1.13"
langgraph = "^0.3"
langchain-core = "^0.3"
openai = "^1.40"
dashscope = "^1.20"
google-generativeai = "^0.8"
opencv-python-headless = "^4.10"
numpy = "^1.26"
pymupdf = "^1.24"
redis = "^5.0"

[tool.poetry.group.dev.dependencies]
black = "^24.0"
ruff = "^0.4"
mypy = "^1.10"
isort = "^5.13"

[tool.poetry.group.test.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.23"
pytest-cov = "^5.0"
pytest-mock = "^3.12"
httpx = "^0.27"
factory-boy = "^3.3"

[tool.black]
line-length = 88

[tool.ruff]
line-length = 88
select = ["E", "F", "W", "I"]

[tool.isort]
profile = "black"
known_first_party = ["docmind"]

[tool.mypy]
strict = true
python_version = "3.11"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]
asyncio_mode = "auto"
```

**`pythonpath = ["src"]`** means pytest resolves imports from `src/`:
```python
from docmind.core.config import get_settings      # resolves → src/docmind/core/config.py
from docmind.modules.documents.services import DocumentService  # resolves → src/docmind/modules/documents/services.py
from docmind.library.cv import deskew_image        # resolves → src/docmind/library/cv/__init__.py
```

- **Formatter**: `poetry run black src/ tests/`
- **Linter**: `poetry run ruff check src/ tests/`
- **Imports**: `poetry run isort src/ tests/`
- **Type checker**: `poetry run mypy src/`

### TypeScript / React (`frontend/package.json` scripts)

```json
{
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:e2e": "playwright test",
    "lint": "eslint src --ext ts,tsx",
    "format": "prettier --write src"
  }
}
```

- **Formatter**: `prettier` — `npm run format`
- **Linter**: `eslint` with TypeScript rules — `npm run lint`
- Strict TypeScript (`"strict": true` in `tsconfig.json`)
- No `any` types — define proper interfaces

---

## Git Commit Format

```
<type>: <description>

Types: feat, fix, refactor, docs, test, chore, perf
```

Examples:
```
feat: add DashScope VLM provider with structured extraction
fix: handle rotated images in deskew preprocessing
test: add provider factory unit tests for all 4 backends
chore: update docker compose redis to 7-alpine
```
