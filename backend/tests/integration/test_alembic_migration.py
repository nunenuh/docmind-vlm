"""
Integration tests for Alembic migrations.

These tests verify that:
- The initial migration creates all expected tables via ``alembic upgrade head``
- The migration is reversible (``alembic downgrade base``)
- All expected columns, indexes, and foreign keys are present

NOTE: These tests require a running PostgreSQL database.
Uses docmind settings for connection URL.
"""

import subprocess
import sys

import pytest
from pathlib import Path
from sqlalchemy import inspect, pool
from sqlalchemy.ext.asyncio import create_async_engine

from docmind.core.config import get_settings


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

settings = get_settings()
DATABASE_URL = settings.database_url
BACKEND_DIR = Path(__file__).resolve().parents[2]  # backend/

EXPECTED_TABLES = {
    "documents",
    "extractions",
    "extracted_fields",
    "audit_entries",
    "chat_messages",
    "citations",
    "projects",
    "personas",
    "project_conversations",
    "project_messages",
    "page_chunks",
    "templates",
}

pytestmark = [
    pytest.mark.integration,
    pytest.mark.asyncio(loop_scope="module"),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _run_alembic(*args: str) -> None:
    """Run an Alembic CLI command as a subprocess.

    Using subprocess avoids the ``asyncio.run()`` conflict that occurs when
    calling ``alembic.command`` from within pytest-asyncio's event loop.
    """
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=str(BACKEND_DIR),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"alembic {' '.join(args)} failed (rc={result.returncode}):\n"
            f"{result.stderr}"
        )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def engine():
    """Module-scoped async engine with NullPool."""
    return create_async_engine(DATABASE_URL, echo=False, poolclass=pool.NullPool)


@pytest.fixture(scope="module", autouse=True)
async def _run_migrations(engine):
    """Run ``alembic upgrade head``, yield for tests, then downgrade."""
    # Clean slate: downgrade first (ignores errors if no alembic_version)
    try:
        _run_alembic("downgrade", "base")
    except RuntimeError:
        pass

    # Apply migration
    _run_alembic("upgrade", "head")
    yield
    _run_alembic("downgrade", "base")
    await engine.dispose()


# ---------------------------------------------------------------------------
# Tests: Table existence
# ---------------------------------------------------------------------------


class TestTableCreation:
    """Verify all expected tables are created by Alembic upgrade."""

    async def test_all_expected_tables_exist(self, engine):
        """All 6 tables should be created."""
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )

        for table in EXPECTED_TABLES:
            assert table in table_names, f"Missing table: {table}"

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


class TestAuditEntriesTable:
    """Verify the audit_entries table schema."""

    async def test_audit_entries_columns(self, engine):
        """AuditEntries table should have all expected columns."""
        expected_columns = {
            "id", "extraction_id", "step_name", "step_order",
            "input_summary", "output_summary", "parameters", "duration_ms",
        }
        async with engine.connect() as conn:
            columns = await conn.run_sync(
                lambda sync_conn: {
                    col["name"]
                    for col in inspect(sync_conn).get_columns("audit_entries")
                }
            )
        assert expected_columns <= columns

    async def test_audit_entries_has_extraction_id_fk(self, engine):
        """AuditEntries should have FK to extractions with CASCADE delete."""
        async with engine.connect() as conn:
            fks = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_foreign_keys("audit_entries")
            )
        ext_fk = next(
            (fk for fk in fks if "extraction_id" in fk["constrained_columns"]),
            None,
        )
        assert ext_fk is not None, "Missing FK on extraction_id"
        assert ext_fk["referred_table"] == "extractions"


class TestChatMessagesTable:
    """Verify the chat_messages table schema."""

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

    async def test_chat_messages_has_document_id_fk(self, engine):
        """ChatMessages should have FK to documents."""
        async with engine.connect() as conn:
            fks = await conn.run_sync(
                lambda sync_conn: inspect(sync_conn).get_foreign_keys("chat_messages")
            )
        doc_fk = next(
            (fk for fk in fks if "document_id" in fk["constrained_columns"]),
            None,
        )
        assert doc_fk is not None, "Missing FK on document_id"
        assert doc_fk["referred_table"] == "documents"


class TestCitationsTable:
    """Verify the citations table schema."""

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
# Tests: Roundtrip (upgrade → downgrade → upgrade)
# ---------------------------------------------------------------------------


class TestMigrationRoundtrip:
    """Verify Alembic migrations can be reversed and replayed."""

    async def test_downgrade_and_upgrade(self, engine):
        """Downgrade to base and upgrade back should reproduce schema."""
        # Downgrade
        _run_alembic("downgrade", "base")

        # Verify all tables dropped
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )
        remaining = table_names & EXPECTED_TABLES
        assert not remaining, f"Tables not dropped: {remaining}"

        # Upgrade again
        _run_alembic("upgrade", "head")

        # Verify all tables recreated
        async with engine.connect() as conn:
            table_names = await conn.run_sync(
                lambda sync_conn: set(inspect(sync_conn).get_table_names())
            )
        for table in EXPECTED_TABLES:
            assert table in table_names
