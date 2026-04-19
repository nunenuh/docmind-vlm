"""Unit tests for ProjectChatUseCase grounded refusal (issue #105).

Focus: the chat stream must return a deterministic refusal without calling
the VLM when retrieval is empty or when the best match is below the
`RAG_REFUSAL_THRESHOLD`.
"""

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from docmind.modules.projects.usecases.project_chat import ProjectChatUseCase


PROJECT_ID = "proj-1"
USER_ID = "user-1"
CONV_ID = "conv-1"


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=MagicMock(
        id=PROJECT_ID, user_id=USER_ID, persona_id=None,
    ))
    repo.list_documents = AsyncMock(return_value=[])
    return repo


@pytest.fixture
def mock_conv_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=MagicMock(id=CONV_ID))
    repo.list_messages = AsyncMock(return_value=[])
    repo.list_messages_for_conversation = AsyncMock(return_value=[])
    repo.get_conversation_by_id = AsyncMock(return_value=MagicMock(id=CONV_ID))
    repo.add_message = AsyncMock()
    repo.create = AsyncMock(return_value=MagicMock(id=CONV_ID))
    repo.create_conversation = AsyncMock(return_value=MagicMock(id=CONV_ID))
    return repo


@pytest.fixture
def mock_rag_service_empty():
    service = MagicMock()
    service.embed_query = AsyncMock(return_value=[0.1, 0.2])
    service.rewrite_query = AsyncMock(return_value="")
    service.retrieve_chunks = AsyncMock(return_value=[])
    service.retrieve_chunks_with_stats = AsyncMock(
        return_value={"chunks": [], "max_similarity": 0.0, "per_document_counts": {}}
    )
    return service


@pytest.fixture
def mock_rag_service_weak():
    """Retrieval returns chunks but similarity is below the refusal threshold."""
    service = MagicMock()
    service.embed_query = AsyncMock(return_value=[0.1, 0.2])
    service.rewrite_query = AsyncMock(return_value="")
    chunks = [
        {
            "chunk_id": "c1",
            "document_id": "doc-A",
            "page_number": 1,
            "content": "unrelated content",
            "similarity": 0.05,
        },
    ]
    service.retrieve_chunks = AsyncMock(return_value=chunks)
    service.retrieve_chunks_with_stats = AsyncMock(
        return_value={
            "chunks": chunks,
            "max_similarity": 0.05,
            "per_document_counts": {"doc-A": 1},
        },
    )
    return service


@pytest.fixture
def mock_vlm_service():
    service = MagicMock()

    async def _never_call(*_a, **_kw):
        if False:
            yield {}
        raise AssertionError("VLM must not be called when refusing")

    service.stream_chat = _never_call
    return service


@pytest.fixture
def mock_persona_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=None)
    return repo


async def _collect(stream) -> list[str]:
    return [evt async for evt in stream]


def _parse_sse(event: str) -> tuple[str, dict]:
    """Return (event_name, payload_dict) from an SSE string.

    The usecase emits events as ``data: {"event": NAME, ...fields}\\n\\n``.
    """
    for line in event.splitlines():
        if line.startswith("data: "):
            payload = json.loads(line[len("data: "):])
            return payload.get("event", ""), payload
    return "", {}


class TestEmptyRetrievalRefusal:
    """When retrieval returns zero chunks, yield grounded refusal without VLM."""

    @pytest.mark.asyncio
    async def test_refuses_and_does_not_call_vlm(
        self,
        mock_repo,
        mock_conv_repo,
        mock_rag_service_empty,
        mock_vlm_service,
        mock_persona_repo,
    ):
        usecase = ProjectChatUseCase(
            repo=mock_repo,
            conv_repo=mock_conv_repo,
            rag_service=mock_rag_service_empty,
            vlm_service=mock_vlm_service,
            persona_repo=mock_persona_repo,
        )

        events = await _collect(
            usecase.project_chat_stream(
                project_id=PROJECT_ID,
                user_id=USER_ID,
                message="What is the weather today?",
                conversation_id=CONV_ID,
            )
        )

        answer_events = [e for e in events if '"event": "answer"' in e]
        assert answer_events, "Expected an answer SSE event"
        _, payload = _parse_sse(answer_events[-1])
        assert payload.get("refusal") is True, (
            f"Expected refusal flag in answer payload; got {payload}"
        )
        assert "cannot find" in payload["content"].lower() or (
            "tidak menemukan" in payload["content"].lower()
        )

    @pytest.mark.asyncio
    async def test_indonesian_message_gets_indonesian_refusal(
        self,
        mock_repo,
        mock_conv_repo,
        mock_rag_service_empty,
        mock_vlm_service,
        mock_persona_repo,
    ):
        usecase = ProjectChatUseCase(
            repo=mock_repo,
            conv_repo=mock_conv_repo,
            rag_service=mock_rag_service_empty,
            vlm_service=mock_vlm_service,
            persona_repo=mock_persona_repo,
        )

        events = await _collect(
            usecase.project_chat_stream(
                project_id=PROJECT_ID,
                user_id=USER_ID,
                message="Apa yang ada di dokumen ini?",
                conversation_id=CONV_ID,
            )
        )

        answer_events = [e for e in events if '"event": "answer"' in e]
        _, payload = _parse_sse(answer_events[-1])
        assert "tidak menemukan" in payload["content"].lower(), (
            f"Expected Indonesian refusal; got {payload.get('content')!r}"
        )


class TestStrongMatchCallsVLM:
    """Regression guard: when similarity is above threshold, stream via VLM."""

    @pytest.fixture
    def mock_rag_service_strong(self):
        service = MagicMock()
        service.embed_query = AsyncMock(return_value=[0.1, 0.2])
        service.rewrite_query = AsyncMock(return_value="")
        chunks = [
            {
                "chunk_id": "c1",
                "document_id": "doc-A",
                "page_number": 1,
                "content": "Invoice total is $500.",
                "similarity": 0.88,
            },
        ]
        service.retrieve_chunks = AsyncMock(return_value=chunks)
        service.retrieve_chunks_with_stats = AsyncMock(
            return_value={
                "chunks": chunks,
                "max_similarity": 0.88,
                "per_document_counts": {"doc-A": 1},
            },
        )
        return service

    @pytest.fixture
    def mock_vlm_service_streaming(self):
        """Yields a short streamed answer."""
        service = MagicMock()

        async def _stream(*_a, **_kw):
            yield {"type": "answer", "content": "Total is $500."}
            yield {"type": "done"}

        service.stream_chat = _stream
        return service

    @pytest.mark.asyncio
    async def test_vlm_is_called_and_answer_has_no_refusal_flag(
        self,
        mock_repo,
        mock_conv_repo,
        mock_rag_service_strong,
        mock_vlm_service_streaming,
        mock_persona_repo,
    ):
        usecase = ProjectChatUseCase(
            repo=mock_repo,
            conv_repo=mock_conv_repo,
            rag_service=mock_rag_service_strong,
            vlm_service=mock_vlm_service_streaming,
            persona_repo=mock_persona_repo,
        )

        events = await _collect(
            usecase.project_chat_stream(
                project_id=PROJECT_ID,
                user_id=USER_ID,
                message="What is the invoice total?",
                conversation_id=CONV_ID,
            )
        )

        answer_events = [e for e in events if '"event": "answer"' in e]
        assert answer_events, "Expected an answer event"
        _, payload = _parse_sse(answer_events[-1])
        assert payload.get("refusal") is not True, (
            f"Expected non-refusal answer; got {payload}"
        )
        assert payload.get("content") == "Total is $500."
        assert payload.get("citations"), "Citations must be present on strong-match answers"


class TestBelowThresholdRefusal:
    """Weak retrieval (max_similarity below threshold) also triggers refusal."""

    @pytest.mark.asyncio
    async def test_refuses_on_weak_match(
        self,
        mock_repo,
        mock_conv_repo,
        mock_rag_service_weak,
        mock_vlm_service,
        mock_persona_repo,
    ):
        usecase = ProjectChatUseCase(
            repo=mock_repo,
            conv_repo=mock_conv_repo,
            rag_service=mock_rag_service_weak,
            vlm_service=mock_vlm_service,
            persona_repo=mock_persona_repo,
        )

        events = await _collect(
            usecase.project_chat_stream(
                project_id=PROJECT_ID,
                user_id=USER_ID,
                message="Off-topic question",
                conversation_id=CONV_ID,
            )
        )

        answer_events = [e for e in events if '"event": "answer"' in e]
        _, payload = _parse_sse(answer_events[-1])
        assert payload.get("refusal") is True
        assert payload.get("max_similarity") == pytest.approx(0.05, abs=0.01)
