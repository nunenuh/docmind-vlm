# Issue #23: Chat Repository + Persistence

## Summary

Implement `ChatRepository` with real SQLAlchemy async queries to store and retrieve `ChatMessage` records. Each message has role, content, citations (via related `Citation` ORM records), document_id, user_id, and created_at. The repository supports creating messages with citations, listing paginated history ordered by created_at, fetching recent messages for conversation context, and loading extracted fields for chat context.

## Context

- **Phase**: 5
- **Priority**: P0
- **Labels**: `phase-5-chat`, `backend`, `tdd`
- **Dependencies**: #2 (Alembic migration)
- **Branch**: `feat/23-chat-repository`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/services.md` — ChatRepository spec
- `specs/backend/api.md` — ChatMessage ORM model, Citation ORM model

## Current State (Scaffold)

### `backend/src/docmind/modules/chat/repositories.py` (stub)
```python
"""docmind/modules/chat/repositories.py — Stub."""
from docmind.core.logging import get_logger

logger = get_logger(__name__)


class ChatRepository:
    async def save_message(self, document_id: str, user_id: str, role: str, content: str, citations: list[dict] | None = None) -> str:
        raise NotImplementedError

    async def get_history(self, document_id: str, user_id: str, page: int, limit: int):
        raise NotImplementedError

    async def get_recent_messages(self, document_id: str, user_id: str, limit: int = 20):
        raise NotImplementedError

    async def get_extracted_fields(self, document_id: str):
        raise NotImplementedError
```

### `backend/src/docmind/dbase/psql/models/` (ChatMessage + Citation -- already exist)
```python
class ChatMessage(Base):
    __tablename__ = "chat_messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    role: Mapped[str] = mapped_column(String(10), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    document: Mapped["Document"] = relationship(back_populates="chat_messages")
    citations: Mapped[list["Citation"]] = relationship(back_populates="message", cascade="all, delete-orphan")

class Citation(Base):
    __tablename__ = "citations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    message_id: Mapped[str] = mapped_column(String(36), ForeignKey("chat_messages.id", ondelete="CASCADE"), nullable=False, index=True)
    page: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    bounding_box: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    text_span: Mapped[str] = mapped_column(Text, nullable=False, default="")
    message: Mapped["ChatMessage"] = relationship(back_populates="citations")
```

## Requirements

### Functional

1. **`save_message(document_id, user_id, role, content, citations)`**:
   - Creates a `ChatMessage` record.
   - If `citations` list is provided, creates associated `Citation` records.
   - Returns the message ID (str).
2. **`get_history(document_id, user_id, page, limit)`**:
   - Returns `(items, total_count)` tuple.
   - Items are `ChatMessage` ORM objects ordered by `created_at ASC`.
   - Filtered by both `document_id` AND `user_id`.
   - Paginated with offset calculation: `(page - 1) * limit`.
3. **`get_recent_messages(document_id, user_id, limit=20)`**:
   - Returns the most recent `limit` messages ordered by `created_at ASC`.
   - Used for building conversation context for the chat pipeline.
4. **`get_extracted_fields(document_id)`**:
   - Finds the latest extraction for the document.
   - Returns its `ExtractedField` records ordered by `page_number`.
   - Returns empty list if no extraction exists.

### Non-Functional

- All methods are `async` and use `AsyncSessionLocal()`.
- Citations are created in the same transaction as the message.
- Messages always filtered by `user_id` for data isolation.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/chat/test_chat_repository.py`

```python
"""Unit tests for ChatRepository with mocked async session."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from datetime import datetime, UTC


@pytest.fixture
def mock_chat_message():
    """Create a mock ChatMessage ORM object."""
    msg = MagicMock()
    msg.id = "msg-001"
    msg.document_id = "doc-001"
    msg.user_id = "user-001"
    msg.role = "user"
    msg.content = "What is the invoice number?"
    msg.created_at = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)
    msg.citations = []
    return msg


@pytest.fixture
def mock_assistant_message():
    """Create a mock assistant ChatMessage with citations."""
    msg = MagicMock()
    msg.id = "msg-002"
    msg.document_id = "doc-001"
    msg.user_id = "user-001"
    msg.role = "assistant"
    msg.content = "The invoice number is INV-2026-001."
    msg.created_at = datetime(2026, 3, 15, 10, 0, 1, tzinfo=UTC)

    citation = MagicMock()
    citation.id = "cit-001"
    citation.message_id = "msg-002"
    citation.page = 1
    citation.bounding_box = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}
    citation.text_span = "INV-2026-001"
    msg.citations = [citation]
    return msg


class TestChatRepositorySaveMessage:
    """Tests for ChatRepository.save_message."""

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_saves_user_message(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_msg = MagicMock()
        mock_msg.id = "msg-new"

        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        result = await repo.save_message(
            document_id="doc-001",
            user_id="user-001",
            role="user",
            content="What is the total?",
        )

        mock_session.add.assert_called_once()
        mock_session.commit.assert_called_once()
        assert isinstance(result, str)

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_saves_message_with_citations(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        citations = [
            {"page": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}, "text_span": "INV-001"},
            {"page": 2, "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05}, "text_span": "$1500"},
        ]

        repo = ChatRepository()
        result = await repo.save_message(
            document_id="doc-001",
            user_id="user-001",
            role="assistant",
            content="The invoice is INV-001 with total $1500.",
            citations=citations,
        )

        # Message + 2 citations = 3 add calls (or message first then citations)
        assert mock_session.add.call_count >= 1
        mock_session.commit.assert_called_once()


class TestChatRepositoryGetHistory:
    """Tests for ChatRepository.get_history."""

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_returns_paginated_messages(self, mock_session_factory, mock_chat_message, mock_assistant_message):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()

        # First call: count query
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        # Second call: items query
        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = [mock_chat_message, mock_assistant_message]

        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        items, total = await repo.get_history("doc-001", "user-001", page=1, limit=50)

        assert total == 2
        assert len(items) == 2
        assert items[0].role == "user"
        assert items[1].role == "assistant"

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_returns_empty_for_no_messages(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 0

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = []

        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        items, total = await repo.get_history("doc-001", "user-001", page=1, limit=50)

        assert total == 0
        assert items == []


class TestChatRepositoryGetRecentMessages:
    """Tests for ChatRepository.get_recent_messages."""

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_returns_recent_messages(self, mock_session_factory, mock_chat_message, mock_assistant_message):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_chat_message, mock_assistant_message]
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        messages = await repo.get_recent_messages("doc-001", "user-001", limit=20)

        assert len(messages) == 2

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_respects_limit_parameter(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        await repo.get_recent_messages("doc-001", "user-001", limit=5)

        # Verify execute was called (query contains limit)
        mock_session.execute.assert_called_once()


class TestChatRepositoryGetExtractedFields:
    """Tests for ChatRepository.get_extracted_fields."""

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_returns_fields_for_latest_extraction(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()

        # First query: get extraction ID
        mock_ext_result = MagicMock()
        mock_ext_row = MagicMock()
        mock_ext_row.__getitem__ = lambda self, i: "ext-001" if i == 0 else None
        mock_ext_result.first.return_value = mock_ext_row

        # Second query: get fields
        mock_field = MagicMock()
        mock_field.field_key = "invoice_number"
        mock_field.field_value = "INV-001"
        mock_fields_result = MagicMock()
        mock_fields_result.scalars.return_value.all.return_value = [mock_field]

        mock_session.execute = AsyncMock(side_effect=[mock_ext_result, mock_fields_result])
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        fields = await repo.get_extracted_fields("doc-001")

        assert len(fields) == 1
        assert fields[0].field_key == "invoice_number"

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_returns_empty_when_no_extraction(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_ext_result = MagicMock()
        mock_ext_result.first.return_value = None

        mock_session.execute = AsyncMock(return_value=mock_ext_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        fields = await repo.get_extracted_fields("doc-001")

        assert fields == []
```

### Step 2: Implement (GREEN)

1. **`repositories.py`**: Replace stubs with real SQLAlchemy queries:
   - `save_message`: Create `ChatMessage`, optionally create `Citation` records, commit in single transaction.
   - `get_history`: Count + paginated select, ordered by `created_at ASC`.
   - `get_recent_messages`: Simple select with limit, ordered by `created_at ASC`.
   - `get_extracted_fields`: Two-step query (latest extraction ID, then fields).

### Step 3: Refactor (IMPROVE)

- Use `selectinload` for eager-loading citations in `get_history` to avoid N+1 queries.
- Add structlog context with `document_id` and `user_id`.

## Acceptance Criteria

- [ ] `save_message` creates ChatMessage with optional Citation records
- [ ] `save_message` returns message ID string
- [ ] `get_history` returns paginated messages ordered by created_at ASC
- [ ] `get_history` filters by both document_id AND user_id
- [ ] `get_recent_messages` returns capped list for conversation context
- [ ] `get_extracted_fields` finds latest extraction's fields
- [ ] `get_extracted_fields` returns empty list when no extraction
- [ ] All unit tests pass

## Files Changed

- `backend/src/docmind/modules/chat/repositories.py` — full implementation
- `backend/tests/unit/modules/chat/test_chat_repository.py` — new

## Verification

```bash
cd backend
pytest tests/unit/modules/chat/test_chat_repository.py -v
```
