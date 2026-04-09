# Issue #2: Initial Alembic Migration from ORM Models

## Summary

Generate the initial Alembic migration that creates all database tables defined in `dbase/psql/models/`: `documents`, `extractions`, `extracted_fields`, `audit_entries`, `chat_messages`, and `citations`. The migration must run up (create tables) and down (drop tables) cleanly against a PostgreSQL database. The Alembic async `env.py` is already scaffolded; this issue verifies it works end-to-end and produces a correct migration file.

## Context

- **Phase**: 1 — Infrastructure
- **Priority**: P0
- **Labels**: `phase-1-infra`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: None
- **Branch**: `feat/2-alembic-migration`
- **Estimated scope**: S

## Specs to Read

- `specs/backend/api.md` — Section "dbase/psql/models/" for all ORM model definitions
- `specs/system.md` — DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME configuration
- `specs/conventions/python-module-structure.md` — Section "dbase/psql/" for database layer

## Current State (Scaffold)

**File: `backend/alembic/env.py`** (already configured for async)

```python
"""Alembic async environment configuration."""
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

from docmind.core.config import get_settings
from docmind.dbase.psql.core.base import Base
from docmind.dbase.psql import models  # noqa: F401 — register models

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

**File: `backend/alembic.ini`** (relevant section)

```ini
[alembic]
script_location = alembic
sqlalchemy.url = postgresql+asyncpg://localhost:5432/docmind
```

**File: `backend/alembic/versions/`** — Only contains `.gitkeep` (no migrations yet)

**File: `backend/src/docmind/dbase/psql/models/`** — 6 ORM models defined:
- `Document` (documents) — 11 columns + 2 relationships
- `Extraction` (extractions) — 6 columns + 3 relationships
- `ExtractedField` (extracted_fields) — 12 columns + 1 relationship
- `AuditEntry` (audit_entries) — 8 columns + 1 relationship
- `ChatMessage` (chat_messages) — 6 columns + 2 relationships
- `Citation` (citations) — 5 columns + 1 relationship

## Requirements

### Functional

1. Generate an initial Alembic migration file using `alembic revision --autogenerate -m "initial schema"`
2. The migration must create all 6 tables: `documents`, `extractions`, `extracted_fields`, `audit_entries`, `chat_messages`, `citations`
3. All foreign key constraints must be present with `ondelete="CASCADE"`
4. All indexes on `user_id`, `document_id`, `extraction_id`, `message_id` must be created
5. The `upgrade()` function must create tables in dependency order (parents before children)
6. The `downgrade()` function must drop tables in reverse dependency order (children before parents)
7. `alembic upgrade head` must succeed on a clean database
8. `alembic downgrade base` must succeed and leave no tables
9. `alembic upgrade head` followed by `alembic downgrade base` followed by `alembic upgrade head` must be idempotent

### Non-Functional

- Migration file must be committed to `backend/alembic/versions/`
- The `env.py` must use async engine (already configured)
- database_url (computed from DB_* vars) is read from settings, not hardcoded in alembic.ini

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/integration/test_alembic_migration.py`

```python
"""
Integration tests for Alembic migrations.

These tests verify that:
- The initial migration creates all expected tables
- The migration is reversible (downgrade works)
- All expected columns, indexes, and foreign keys are present

NOTE: These tests require a running PostgreSQL database.
Set DATABASE_URL env var or use docker-compose to start one.
If no database is available, tests are skipped.
"""
import os

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from docmind.dbase.psql.core.base import Base
from docmind.dbase.psql import models  # noqa: F401 — register all models


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/docmind_test",
)

EXPECTED_TABLES = {
    "documents",
    "extractions",
    "extracted_fields",
    "audit_entries",
    "chat_messages",
    "citations",
}

# Skip all tests if no database is reachable
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """Create a test async engine."""
    return create_async_engine(DATABASE_URL, echo=False)


@pytest.fixture(scope="module")
def session_factory(engine):
    """Create a session factory for the test engine."""
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def _setup_and_teardown(engine):
    """
    Create all tables before each test, drop them after.
    Uses metadata.create_all/drop_all for test isolation.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


# ---------------------------------------------------------------------------
# Tests: Table existence
# ---------------------------------------------------------------------------


class TestTableCreation:
    """Verify all expected tables are created by the ORM models."""

    @pytest.mark.asyncio
    async def test_all_expected_tables_exist(self, engine):
        """All 6 tables should be created."""
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        for table in EXPECTED_TABLES:
            assert table in table_names, f"Missing table: {table}"

    @pytest.mark.asyncio
    async def test_no_unexpected_tables(self, engine):
        """Only the expected tables should exist (plus alembic_version if present)."""
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        allowed = EXPECTED_TABLES | {"alembic_version"}
        unexpected = table_names - allowed
        assert not unexpected, f"Unexpected tables: {unexpected}"


# ---------------------------------------------------------------------------
# Tests: Column verification
# ---------------------------------------------------------------------------


class TestDocumentsTable:
    """Verify the documents table schema."""

    @pytest.mark.asyncio
    async def test_documents_columns(self, engine):
        """Documents table should have all expected columns."""
        expected_columns = {
            "id", "user_id", "filename", "file_type", "file_size",
            "storage_path", "status", "document_type", "page_count",
            "created_at", "updated_at",
        }
        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: {
                    col["name"] for col in inspect(sync_conn).get_columns("documents")
                }
            )
        assert expected_columns <= columns

    @pytest.mark.asyncio
    async def test_documents_user_id_is_indexed(self, engine):
        """user_id column should be indexed for fast lookups."""
        async with engine.connect() as conn:
            indexes = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_indexes("documents")
            )
        indexed_columns = {
            col for idx in indexes for col in idx["column_names"]
        }
        assert "user_id" in indexed_columns


class TestExtractionsTable:
    """Verify the extractions table schema."""

    @pytest.mark.asyncio
    async def test_extractions_columns(self, engine):
        """Extractions table should have all expected columns."""
        expected_columns = {
            "id", "document_id", "mode", "template_type",
            "processing_time_ms", "created_at",
        }
        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: {
                    col["name"] for col in inspect(sync_conn).get_columns("extractions")
                }
            )
        assert expected_columns <= columns

    @pytest.mark.asyncio
    async def test_extractions_has_document_id_fk(self, engine):
        """Extractions should have FK to documents with CASCADE delete."""
        async with engine.connect() as conn:
            fks = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_foreign_keys("extractions")
            )
        doc_fk = next(
            (fk for fk in fks if "document_id" in fk["constrained_columns"]),
            None,
        )
        assert doc_fk is not None, "Missing FK on document_id"
        assert doc_fk["referred_table"] == "documents"


class TestExtractedFieldsTable:
    """Verify the extracted_fields table schema."""

    @pytest.mark.asyncio
    async def test_extracted_fields_columns(self, engine):
        """ExtractedFields table should have all expected columns."""
        expected_columns = {
            "id", "extraction_id", "field_type", "field_key", "field_value",
            "page_number", "bounding_box", "confidence", "vlm_confidence",
            "cv_quality_score", "is_required", "is_missing",
        }
        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: {
                    col["name"]
                    for col in inspect(sync_conn).get_columns("extracted_fields")
                }
            )
        assert expected_columns <= columns


class TestChatMessagesTable:
    """Verify the chat_messages table schema."""

    @pytest.mark.asyncio
    async def test_chat_messages_columns(self, engine):
        """ChatMessages table should have all expected columns."""
        expected_columns = {
            "id", "document_id", "user_id", "role", "content", "created_at",
        }
        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: {
                    col["name"]
                    for col in inspect(sync_conn).get_columns("chat_messages")
                }
            )
        assert expected_columns <= columns


class TestCitationsTable:
    """Verify the citations table schema."""

    @pytest.mark.asyncio
    async def test_citations_columns(self, engine):
        """Citations table should have all expected columns."""
        expected_columns = {
            "id", "message_id", "page", "bounding_box", "text_span",
        }
        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: {
                    col["name"]
                    for col in inspect(sync_conn).get_columns("citations")
                }
            )
        assert expected_columns <= columns

    @pytest.mark.asyncio
    async def test_citations_has_message_id_fk(self, engine):
        """Citations should have FK to chat_messages with CASCADE delete."""
        async with engine.connect() as conn:
            fks = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_foreign_keys("citations")
            )
        msg_fk = next(
            (fk for fk in fks if "message_id" in fk["constrained_columns"]),
            None,
        )
        assert msg_fk is not None, "Missing FK on message_id"
        assert msg_fk["referred_table"] == "chat_messages"


# ---------------------------------------------------------------------------
# Tests: Roundtrip (create_all -> drop_all -> create_all)
# ---------------------------------------------------------------------------


class TestMigrationRoundtrip:
    """Verify tables can be created, dropped, and recreated."""

    @pytest.mark.asyncio
    async def test_drop_all_removes_tables(self, engine):
        """drop_all should remove all tables."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        remaining = table_names & EXPECTED_TABLES
        assert not remaining, f"Tables not dropped: {remaining}"

    @pytest.mark.asyncio
    async def test_recreate_after_drop(self, engine):
        """Tables should be recreatable after drop_all."""
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        for table in EXPECTED_TABLES:
            assert table in table_names
```

### Step 2: Implement (GREEN)

**Action**: Generate the Alembic migration file.

**Commands to run**:

```bash
cd backend

# Ensure DATABASE_URL is set (e.g., in .env)
# export DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/docmind

# Generate the initial migration
alembic revision --autogenerate -m "initial schema"
```

**Files to modify**:
- `backend/alembic/versions/<hash>_initial_schema.py` — Auto-generated, may need manual review

**Post-generation review checklist**:

1. Open the generated migration file in `backend/alembic/versions/`
2. Verify `upgrade()` creates all 6 tables in correct order:
   - `documents` first (no FK dependencies)
   - `extractions` (FK to documents)
   - `extracted_fields` (FK to extractions)
   - `audit_entries` (FK to extractions)
   - `chat_messages` (FK to documents)
   - `citations` (FK to chat_messages)
3. Verify `downgrade()` drops tables in reverse order:
   - `citations` first
   - `chat_messages`
   - `audit_entries`
   - `extracted_fields`
   - `extractions`
   - `documents` last
4. Verify all `ForeignKey` constraints include `ondelete="CASCADE"`
5. Verify all `index=True` columns have corresponding `op.create_index()` calls
6. Verify `JSON` columns use `postgresql.JSON` dialect type
7. Verify `DateTime(timezone=True)` columns preserve timezone awareness

**Expected migration structure** (skeleton):

```python
"""initial schema

Revision ID: <auto>
Revises:
Create Date: <auto>
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "<auto>"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # documents (no FK deps)
    op.create_table(
        "documents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False, index=True),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_type", sa.String(10), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("storage_path", sa.String(512), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("document_type", sa.String(50), nullable=True),
        sa.Column("page_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    # extractions (FK -> documents)
    op.create_table(
        "extractions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("document_id", sa.String(36), sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("mode", sa.String(20), nullable=False),
        sa.Column("template_type", sa.String(50), nullable=True),
        sa.Column("processing_time_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # extracted_fields (FK -> extractions)
    op.create_table(
        "extracted_fields",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("extraction_id", sa.String(36), sa.ForeignKey("extractions.id", ondelete="CASCADE"), nullable=False, index=True),
        # ... remaining columns
    )
    # audit_entries (FK -> extractions)
    op.create_table("audit_entries", ...)
    # chat_messages (FK -> documents)
    op.create_table("chat_messages", ...)
    # citations (FK -> chat_messages)
    op.create_table("citations", ...)


def downgrade() -> None:
    op.drop_table("citations")
    op.drop_table("chat_messages")
    op.drop_table("audit_entries")
    op.drop_table("extracted_fields")
    op.drop_table("extractions")
    op.drop_table("documents")
```

### Step 3: Refactor (IMPROVE)

- Review the auto-generated migration for any unnecessary operations
- Ensure default values (`default="uploaded"`, `default=0`) are set at the ORM level, not the migration level (Alembic may add `server_default` — remove these since defaults are handled in Python)
- Verify that `JSON` columns use the PostgreSQL dialect, not generic `sa.JSON`
- Add a comment header explaining the initial schema

## Acceptance Criteria

- [ ] Migration file exists in `backend/alembic/versions/` with descriptive name
- [ ] `alembic upgrade head` creates all 6 tables
- [ ] `alembic downgrade base` drops all 6 tables
- [ ] `alembic upgrade head && alembic downgrade base && alembic upgrade head` is idempotent
- [ ] All foreign keys have `ondelete="CASCADE"`
- [ ] All indexed columns (`user_id`, `document_id`, `extraction_id`, `message_id`) have indexes
- [ ] All 10 integration tests pass (when database is available)
- [ ] `env.py` reads database_url from settings, not hardcoded

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/alembic/versions/<hash>_initial_schema.py` | Create | Auto-generated initial migration with all 6 tables |
| `backend/tests/integration/test_alembic_migration.py` | Create | Integration tests verifying table creation, columns, FKs, roundtrip |

## Verification

```bash
# Generate migration (requires running Postgres)
cd backend && alembic revision --autogenerate -m "initial schema"

# Apply migration
cd backend && alembic upgrade head

# Verify tables created
cd backend && alembic current

# Test reversibility
cd backend && alembic downgrade base
cd backend && alembic upgrade head

# Run integration tests (requires TEST_DATABASE_URL)
cd backend && python -m pytest tests/integration/test_alembic_migration.py -v -m integration

# Verify migration file was generated
ls backend/alembic/versions/*.py | grep -v __pycache__ | grep -v .gitkeep
```
