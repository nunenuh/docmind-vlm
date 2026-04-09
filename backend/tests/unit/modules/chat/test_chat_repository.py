"""Unit tests for ChatRepository with mocked async session."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_chat_message():
    msg = MagicMock()
    msg.id = "msg-001"
    msg.document_id = "doc-001"
    msg.user_id = "user-001"
    msg.role = "user"
    msg.content = "What is the invoice number?"
    msg.created_at = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    msg.citations = []
    return msg


@pytest.fixture
def mock_assistant_message():
    msg = MagicMock()
    msg.id = "msg-002"
    msg.document_id = "doc-001"
    msg.user_id = "user-001"
    msg.role = "assistant"
    msg.content = "The invoice number is INV-2026-001."
    msg.created_at = datetime(2026, 3, 15, 10, 0, 1, tzinfo=timezone.utc)
    msg.citations = [MagicMock(page=1, text_span="INV-2026-001")]
    return msg


class TestChatRepositorySaveMessage:

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_saves_user_message(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        result = await repo.save_message(
            document_id="doc-001",
            user_id="user-001",
            role="user",
            content="What is the total?",
        )

        mock_session.add.assert_called()
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
            {"page": 1, "bounding_box": {"x": 0.1}, "text_span": "INV-001"},
            {"page": 2, "bounding_box": {"x": 0.5}, "text_span": "$1500"},
        ]

        repo = ChatRepository()
        result = await repo.save_message(
            document_id="doc-001",
            user_id="user-001",
            role="assistant",
            content="The invoice is INV-001 with total $1500.",
            citations=citations,
        )

        assert mock_session.add.call_count >= 1
        mock_session.commit.assert_called_once()


class TestChatRepositoryGetHistory:

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_returns_paginated_messages(self, mock_session_factory, mock_chat_message, mock_assistant_message):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()
        mock_count_result = MagicMock()
        mock_count_result.scalar.return_value = 2

        mock_items_result = MagicMock()
        mock_items_result.scalars.return_value.all.return_value = [mock_chat_message, mock_assistant_message]

        mock_session.execute = AsyncMock(side_effect=[mock_count_result, mock_items_result])
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        items, total = await repo.get_history("doc-001", "user-001", page=1, limit=50)

        assert total == 2
        assert len(items) == 2

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


class TestChatRepositoryGetExtractedFields:

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.repositories.AsyncSessionLocal")
    async def test_returns_fields_for_latest_extraction(self, mock_session_factory):
        from docmind.modules.chat.repositories import ChatRepository

        mock_session = AsyncMock()

        mock_ext_result = MagicMock()
        mock_ext_result.scalar_one_or_none.return_value = "ext-001"

        mock_field = MagicMock()
        mock_field.field_key = "invoice_number"
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
        mock_ext_result.scalar_one_or_none.return_value = None

        mock_session.execute = AsyncMock(return_value=mock_ext_result)
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        repo = ChatRepository()
        fields = await repo.get_extracted_fields("doc-001")

        assert fields == []
