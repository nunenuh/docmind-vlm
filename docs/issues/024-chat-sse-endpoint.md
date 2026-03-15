# Issue #24: Chat SSE Endpoint

## Summary

Wire the chat pipeline to the `POST /api/v1/chat/{document_id}` SSE endpoint and implement the `GET /api/v1/chat/{document_id}/history` endpoint. The SSE endpoint streams events (thinking, chunk/token, citation, done/error) from the LangGraph chat pipeline. The history endpoint returns paginated chat messages with citations. This issue implements `ChatUseCase` which orchestrates context loading, pipeline execution, message persistence, and SSE streaming.

## Context

- **Phase**: 5
- **Priority**: P0
- **Labels**: `phase-5-chat`, `backend`, `tdd`
- **Dependencies**: #22 (chat pipeline reason + cite), #23 (chat repository)
- **Branch**: `feat/24-chat-sse-endpoint`
- **Estimated scope**: L

## Specs to Read

- `specs/backend/pipeline-chat.md` — SSE streaming pattern, event types
- `specs/backend/services.md` — ChatUseCase spec
- `specs/backend/api.md` — chat handler, ChatHistoryResponse

## Current State (Scaffold)

### `backend/src/docmind/modules/chat/usecase.py` (stub)
```python
"""docmind/modules/chat/usecase.py — Stub."""
import json
from typing import AsyncGenerator
from docmind.core.logging import get_logger
from .schemas import ChatHistoryResponse

logger = get_logger(__name__)


class ChatUseCase:
    def send_message(self, document_id: str, user_id: str, message: str) -> AsyncGenerator[str, None]:
        return self._chat_stream(document_id, user_id, message)

    async def _chat_stream(self, document_id: str, user_id: str, message: str) -> AsyncGenerator[str, None]:
        yield f"data: {json.dumps({'type': 'done', 'message_id': 'stub'})}\n\n"

    def get_history(self, document_id: str, user_id: str, page: int, limit: int) -> ChatHistoryResponse:
        return ChatHistoryResponse(items=[], total=0, page=page, limit=limit)
```

### `backend/src/docmind/modules/chat/apiv1/handler.py` (already wired)
```python
@router.post("/{document_id}")
async def send_message(document_id: str, body: ChatMessageRequest, current_user: dict = Depends(get_current_user)):
    doc_usecase = DocumentUseCase()
    document = doc_usecase.get_document(user_id=current_user["id"], document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")

    chat_usecase = ChatUseCase()
    event_stream = chat_usecase.send_message(document_id=document_id, user_id=current_user["id"], message=body.message)
    return StreamingResponse(event_stream, media_type="text/event-stream", ...)

@router.get("/{document_id}/history", response_model=ChatHistoryResponse)
async def get_chat_history(document_id: str, page: int = Query(default=1, ge=1), limit: int = Query(default=50, ge=1, le=100), current_user: dict = Depends(get_current_user)):
    chat_usecase = ChatUseCase()
    return chat_usecase.get_history(document_id=document_id, user_id=current_user["id"], page=page, limit=limit)
```

## Requirements

### Functional

1. **`ChatUseCase.__init__`**: Instantiates `ChatRepository` and `ChatService`.
2. **`ChatUseCase.send_message(document_id, user_id, message)`**: Returns an async generator for SSE streaming.
3. **`ChatUseCase._chat_stream(document_id, user_id, message)`**:
   - Step 1: Persist user message via `repo.save_message`.
   - Step 2: Load context via `_load_context` (page images, extracted fields, conversation history).
   - Step 3: Set up `stream_callback` that pushes events to an `asyncio.Queue`.
   - Step 4: Build initial state and run `run_chat_pipeline` in background thread.
   - Step 5: Yield SSE events from the queue. Heartbeat every 30s on timeout.
   - Step 6: Persist assistant response via `repo.save_message` with citations.
   - Step 7: Yield final `done` event with `message_id`.
4. **`ChatUseCase._load_context(document_id, user_id)`**:
   - Loads document metadata from DB.
   - Loads page images from Supabase Storage via `ChatService`.
   - Loads extracted fields via `repo.get_extracted_fields`.
   - Loads conversation history via `repo.get_recent_messages`.
   - Returns `(page_images, extracted_fields, conversation_history)`.
5. **`ChatUseCase.get_history(document_id, user_id, page, limit)`**:
   - Calls `repo.get_history`.
   - Maps ORM objects to `ChatMessageResponse` schemas with citations.
   - Returns `ChatHistoryResponse`.
6. **SSE Event Types**:
   - `{"type": "token", "content": "..."}` — answer token
   - `{"type": "citation", "citation": {...}}` — citation data
   - `{"type": "done", "message_id": "uuid"}` — pipeline complete
   - `{"type": "heartbeat"}` — keep-alive
   - `{"type": "error", "message": "..."}` — on failure

### Non-Functional

- Context loading failure yields an error SSE event (does not crash).
- Heartbeats every 30 seconds prevent proxy timeouts.
- Pipeline runs in background thread via `asyncio.to_thread`.
- SSE format: `data: {json}\n\n`.

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/modules/chat/test_chat_usecase.py`

```python
"""Unit tests for ChatUseCase."""
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, UTC

from docmind.modules.chat.schemas import ChatHistoryResponse, ChatMessageResponse, Citation


@pytest.fixture
def mock_chat_message_orm():
    """Mock ChatMessage ORM with citations."""
    msg = MagicMock()
    msg.id = "msg-001"
    msg.role = "user"
    msg.content = "What is the invoice number?"
    msg.created_at = datetime(2026, 3, 15, 10, 0, 0, tzinfo=UTC)

    msg.citations = []
    return msg


@pytest.fixture
def mock_assistant_orm():
    """Mock assistant ChatMessage with citations."""
    msg = MagicMock()
    msg.id = "msg-002"
    msg.role = "assistant"
    msg.content = "The invoice number is INV-001."
    msg.created_at = datetime(2026, 3, 15, 10, 0, 1, tzinfo=UTC)

    cit = MagicMock()
    cit.page = 1
    cit.bounding_box = {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05}
    cit.text_span = "INV-001"
    msg.citations = [cit]
    return msg


class TestChatUseCaseGetHistory:
    """Tests for ChatUseCase.get_history."""

    @pytest.mark.asyncio
    async def test_returns_chat_history_response(self, mock_chat_message_orm, mock_assistant_orm):
        from docmind.modules.chat.usecase import ChatUseCase

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.get_history.return_value = (
            [mock_chat_message_orm, mock_assistant_orm],
            2,
        )

        result = await usecase.get_history("doc-001", "user-001", page=1, limit=50)

        assert isinstance(result, ChatHistoryResponse)
        assert result.total == 2
        assert result.page == 1
        assert result.limit == 50
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
    """Tests for ChatUseCase.send_message SSE stream."""

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.usecase.run_chat_pipeline")
    async def test_yields_sse_events(self, mock_pipeline):
        from docmind.modules.chat.usecase import ChatUseCase

        mock_pipeline.return_value = {
            "answer": "The total is $1,500.",
            "citations": [
                {"page": 1, "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05}, "text_span": "$1,500"},
            ],
        }

        usecase = ChatUseCase()
        usecase.repo = AsyncMock()
        usecase.repo.save_message.return_value = "msg-new"
        usecase.repo.get_extracted_fields.return_value = []
        usecase.repo.get_recent_messages.return_value = []
        usecase.service = MagicMock()
        usecase.service.load_page_images.return_value = []

        # Mock _load_context to avoid DB calls
        usecase._load_context = AsyncMock(return_value=([], [], []))

        events = []
        async for event_str in usecase._chat_stream("doc-001", "user-001", "What is the total?"):
            events.append(event_str)

        # Should have at least a done event
        assert len(events) >= 1

        # Parse last event -- should be done
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

        # Should have an error event
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

        events = []
        async for event_str in usecase._chat_stream("doc-001", "user-001", "Hello"):
            events.append(event_str)

        # User message should be persisted before anything else
        usecase.repo.save_message.assert_any_call("doc-001", "user-001", "user", "Hello")


class TestChatUseCaseLoadContext:
    """Tests for ChatUseCase._load_context."""

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.usecase.async_session")
    async def test_loads_document_and_context(self, mock_session_factory):
        from docmind.modules.chat.usecase import ChatUseCase

        mock_doc = MagicMock()
        mock_doc.storage_path = "user/doc/file.pdf"
        mock_doc.file_type = "pdf"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        usecase = ChatUseCase()
        usecase.service = MagicMock()
        usecase.service.load_page_images.return_value = ["img1", "img2"]
        usecase.repo = AsyncMock()
        usecase.repo.get_extracted_fields.return_value = []
        usecase.repo.get_recent_messages.return_value = []

        page_images, fields, history = await usecase._load_context("doc-001", "user-001")

        assert page_images == ["img1", "img2"]
        assert fields == []
        assert history == []
        usecase.service.load_page_images.assert_called_once_with("user/doc/file.pdf", "pdf")

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.usecase.async_session")
    async def test_raises_when_document_not_found(self, mock_session_factory):
        from docmind.modules.chat.usecase import ChatUseCase

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        usecase = ChatUseCase()
        usecase.service = MagicMock()
        usecase.repo = AsyncMock()

        with pytest.raises(ValueError, match="Document not found"):
            await usecase._load_context("nonexistent", "user-001")

    @pytest.mark.asyncio
    @patch("docmind.modules.chat.usecase.async_session")
    async def test_builds_conversation_history_from_messages(self, mock_session_factory):
        from docmind.modules.chat.usecase import ChatUseCase

        mock_doc = MagicMock()
        mock_doc.storage_path = "path/file.pdf"
        mock_doc.file_type = "pdf"

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_doc
        mock_session.execute.return_value = mock_result
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_msg1 = MagicMock()
        mock_msg1.role = "user"
        mock_msg1.content = "Hello"
        mock_msg2 = MagicMock()
        mock_msg2.role = "assistant"
        mock_msg2.content = "Hi there"

        usecase = ChatUseCase()
        usecase.service = MagicMock()
        usecase.service.load_page_images.return_value = []
        usecase.repo = AsyncMock()
        usecase.repo.get_extracted_fields.return_value = []
        usecase.repo.get_recent_messages.return_value = [mock_msg1, mock_msg2]

        _, _, history = await usecase._load_context("doc-001", "user-001")

        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "assistant", "content": "Hi there"}
```

**Test file**: `backend/tests/unit/modules/chat/test_chat_sse_format.py`

```python
"""Unit tests for SSE event formatting."""
import json
import pytest


class TestSSEEventFormat:
    """Tests for SSE event string format."""

    def test_token_event_format(self):
        event = {"type": "token", "content": "The "}
        sse_str = f"data: {json.dumps(event)}\n\n"

        assert sse_str.startswith("data: ")
        assert sse_str.endswith("\n\n")
        parsed = json.loads(sse_str[len("data: "):].strip())
        assert parsed["type"] == "token"
        assert parsed["content"] == "The "

    def test_citation_event_format(self):
        citation = {
            "page": 1,
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            "text_span": "INV-001",
        }
        event = {"type": "citation", "citation": citation}
        sse_str = f"data: {json.dumps(event)}\n\n"

        parsed = json.loads(sse_str[len("data: "):].strip())
        assert parsed["type"] == "citation"
        assert parsed["citation"]["page"] == 1
        assert parsed["citation"]["text_span"] == "INV-001"

    def test_done_event_format(self):
        event = {"type": "done", "message_id": "msg-uuid-001"}
        sse_str = f"data: {json.dumps(event)}\n\n"

        parsed = json.loads(sse_str[len("data: "):].strip())
        assert parsed["type"] == "done"
        assert parsed["message_id"] == "msg-uuid-001"

    def test_error_event_format(self):
        event = {"type": "error", "message": "Failed to load context"}
        sse_str = f"data: {json.dumps(event)}\n\n"

        parsed = json.loads(sse_str[len("data: "):].strip())
        assert parsed["type"] == "error"
        assert "Failed" in parsed["message"]

    def test_heartbeat_event_format(self):
        event = {"type": "heartbeat"}
        sse_str = f"data: {json.dumps(event)}\n\n"

        parsed = json.loads(sse_str[len("data: "):].strip())
        assert parsed["type"] == "heartbeat"
```

### Step 2: Implement (GREEN)

1. **`usecase.py`**: Full implementation of `ChatUseCase`:
   - `__init__`: Create `ChatRepository` and `ChatService`.
   - `send_message`: Return `_chat_stream` generator.
   - `_chat_stream`: Persist user message, load context, set up queue + callback, run pipeline in background, yield SSE events.
   - `_load_context`: Load document, page images, extracted fields, conversation history.
   - `get_history`: Fetch from repo, map to response schemas.
2. **`services.py`**: Implement `ChatService.load_page_images` using `get_file_bytes` + `convert_to_page_images`.

### Step 3: Refactor (IMPROVE)

- Extract SSE event formatting to a shared helper.
- Add timeout handling for pipeline execution.
- Ensure all exceptions in `_chat_stream` yield error events (never crash the stream).

## Acceptance Criteria

- [ ] `POST /chat/{document_id}` streams SSE events with correct format
- [ ] SSE event types: token, citation, done, error, heartbeat
- [ ] User message persisted before pipeline starts
- [ ] Assistant response + citations persisted after pipeline completes
- [ ] Context load failure yields error SSE event (no crash)
- [ ] `GET /chat/{document_id}/history` returns paginated messages with citations
- [ ] Heartbeats sent every 30s during pipeline execution
- [ ] All unit tests pass

## Files Changed

- `backend/src/docmind/modules/chat/usecase.py` — full implementation
- `backend/src/docmind/modules/chat/services.py` — implement load_page_images
- `backend/tests/unit/modules/chat/test_chat_usecase.py` — new
- `backend/tests/unit/modules/chat/test_chat_sse_format.py` — new

## Verification

```bash
cd backend
pytest tests/unit/modules/chat/test_chat_usecase.py -v
pytest tests/unit/modules/chat/test_chat_sse_format.py -v
pytest tests/unit/modules/chat/ -v
```
