"""Unit tests for ChatUseCase."""
import json

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from docmind.modules.chat.schemas import ChatHistoryResponse


@pytest.fixture
def mock_chat_message_orm():
    msg = MagicMock()
    msg.id = "msg-001"
    msg.role = "user"
    msg.content = "What is the invoice number?"
    msg.created_at = datetime(2026, 3, 15, 10, 0, 0, tzinfo=timezone.utc)
    msg.citations = []
    return msg


@pytest.fixture
def mock_assistant_orm():
    msg = MagicMock()
    msg.id = "msg-002"
    msg.role = "assistant"
    msg.content = "The invoice number is INV-001."
    msg.created_at = datetime(2026, 3, 15, 10, 0, 1, tzinfo=timezone.utc)

    cit = MagicMock()
    cit.page = 1
    cit.bounding_box = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}
    cit.text_span = "INV-001"
    msg.citations = [cit]
    return msg


class TestChatUseCaseGetHistory:

    @pytest.mark.asyncio
    async def test_returns_chat_history_response(self, mock_chat_message_orm, mock_assistant_orm):
        from docmind.modules.chat.usecase import ChatUseCase

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_history.return_value = (
            [mock_chat_message_orm, mock_assistant_orm], 2,
        )

        result = await usecase.get_history("doc-001", "user-001", page=1, limit=50)

        assert isinstance(result, ChatHistoryResponse)
        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0].role == "user"
        assert result.items[1].role == "assistant"

    @pytest.mark.asyncio
    async def test_maps_citations_correctly(self, mock_assistant_orm):
        from docmind.modules.chat.usecase import ChatUseCase

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_history.return_value = ([mock_assistant_orm], 1)

        result = await usecase.get_history("doc-001", "user-001", page=1, limit=50)

        msg = result.items[0]
        assert len(msg.citations) == 1
        assert msg.citations[0].page == 1
        assert msg.citations[0].text_span == "INV-001"

    @pytest.mark.asyncio
    async def test_returns_empty_history(self):
        from docmind.modules.chat.usecase import ChatUseCase

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_history.return_value = ([], 0)

        result = await usecase.get_history("doc-001", "user-001", page=1, limit=50)

        assert result.total == 0
        assert result.items == []


class TestChatUseCaseSendMessage:

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.usecase.run_chat_pipeline")
    async def test_yields_sse_events(self, mock_pipeline):
        from docmind.modules.chat.usecase import ChatUseCase

        mock_pipeline.return_value = {
            "answer": "The total is $1,500.",
            "citations": [
                {"page": 1, "bounding_box": {"x": 0.5}, "text_span": "$1,500"},
            ],
        }

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.save_message.return_value = "msg-new"
        usecase._load_context = AsyncMock(return_value=([], [], []))

        events = []
        async for event_str in usecase._chat_stream("doc-001", "user-001", "What is the total?"):
            events.append(event_str)

        assert len(events) >= 1
        all_data = []
        for e in events:
            if e.startswith("data: "):
                data = json.loads(e[len("data: "):].strip())
                all_data.append(data)

        done_events = [d for d in all_data if d.get("type") == "done"]
        assert len(done_events) >= 1

    @pytest.mark.asyncio
    async def test_yields_error_on_context_load_failure(self):
        from docmind.modules.chat.usecase import ChatUseCase

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.save_message.return_value = "msg-new"
        usecase._load_context = AsyncMock(side_effect=Exception("DB connection lost"))

        events = []
        async for event_str in usecase._chat_stream("doc-001", "user-001", "Hello"):
            events.append(event_str)

        all_data = []
        for e in events:
            if e.startswith("data: "):
                data = json.loads(e[len("data: "):].strip())
                all_data.append(data)

        error_events = [d for d in all_data if d.get("type") == "error"]
        assert len(error_events) >= 1

    @pytest.mark.asyncio
    async def test_persists_user_message(self):
        from docmind.modules.chat.usecase import ChatUseCase

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.save_message.return_value = "msg-new"
        usecase._load_context = AsyncMock(side_effect=Exception("fail"))

        async for _ in usecase._chat_stream("doc-001", "user-001", "Hello"):
            pass

        usecase.repo.save_message.assert_any_call("doc-001", "user-001", "user", "Hello")
