"""Unit tests for RAG chat pipeline."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestEmbedQueryNode:
    """Tests for embed_query_node."""

    @patch("docmind.library.pipeline.rag.embed_texts")
    def test_calls_embed_texts_with_message(self, mock_embed):
        from docmind.library.pipeline.rag import embed_query_node

        mock_embed.return_value = [[0.1, 0.2, 0.3]]

        state = {"message": "What is the total revenue?"}
        result = embed_query_node(state)

        mock_embed.assert_called_once_with(["What is the total revenue?"])
        assert result["query_embedding"] == [0.1, 0.2, 0.3]

    @patch("docmind.library.pipeline.rag.embed_texts")
    def test_handles_empty_message(self, mock_embed):
        from docmind.library.pipeline.rag import embed_query_node

        mock_embed.return_value = [[0.0, 0.0]]

        state = {"message": ""}
        result = embed_query_node(state)

        mock_embed.assert_called_once_with([""])
        assert "query_embedding" in result


class TestRetrieveNode:
    """Tests for retrieve_node."""

    @patch("docmind.library.pipeline.rag.get_settings")
    @patch("docmind.library.pipeline.rag.retrieve_similar_chunks")
    def test_calls_retriever_with_correct_params(self, mock_retrieve, mock_settings):
        from docmind.library.pipeline.rag import retrieve_node

        mock_settings.return_value = MagicMock(
            RAG_TOP_K=5, RAG_SIMILARITY_THRESHOLD=0.7
        )
        mock_retrieve.return_value = [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "page_number": 1,
                "content": "Revenue was $1M",
                "similarity": 0.85,
            }
        ]

        state = {
            "query_embedding": [0.1, 0.2, 0.3],
            "project_id": "proj-123",
        }
        result = retrieve_node(state)

        mock_retrieve.assert_called_once_with(
            query_embedding=[0.1, 0.2, 0.3],
            project_id="proj-123",
            top_k=5,
            threshold=0.7,
        )
        assert len(result["retrieved_chunks"]) == 1
        assert result["retrieved_chunks"][0]["content"] == "Revenue was $1M"

    @patch("docmind.library.pipeline.rag.get_settings")
    @patch("docmind.library.pipeline.rag.retrieve_similar_chunks")
    def test_returns_empty_when_no_chunks_found(self, mock_retrieve, mock_settings):
        from docmind.library.pipeline.rag import retrieve_node

        mock_settings.return_value = MagicMock(
            RAG_TOP_K=5, RAG_SIMILARITY_THRESHOLD=0.7
        )
        mock_retrieve.return_value = []

        state = {"query_embedding": [0.1], "project_id": "proj-123"}
        result = retrieve_node(state)

        assert result["retrieved_chunks"] == []


class TestReasonNode:
    """Tests for reason_node."""

    @patch("docmind.library.pipeline.rag.get_vlm_provider")
    def test_builds_prompt_with_persona(self, mock_get_provider):
        from docmind.library.pipeline.rag import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(
            return_value={"content": "Based on [Source 1], revenue was $1M."}
        )
        mock_get_provider.return_value = mock_provider

        state = {
            "message": "What is the revenue?",
            "retrieved_chunks": [
                {
                    "document_id": "d1",
                    "page_number": 1,
                    "content": "Revenue was $1M in 2025.",
                    "similarity": 0.9,
                }
            ],
            "persona": {
                "name": "Finance Expert",
                "system_prompt": "You are a financial analyst.",
                "tone": "formal",
                "rules": "Always cite numbers precisely.",
                "boundaries": "Do not give investment advice.",
            },
            "conversation_history": [],
            "stream_callback": None,
        }

        result = reason_node(state)

        assert "raw_answer" in result
        assert "revenue" in result["raw_answer"].lower()

        # Verify persona was included in system prompt
        call_kwargs = mock_provider.chat.call_args
        system_prompt = call_kwargs.kwargs.get("system_prompt", "")
        assert "Finance Expert" in system_prompt
        assert "formal" in system_prompt

    @patch("docmind.library.pipeline.rag.get_vlm_provider")
    def test_uses_default_prompt_without_persona(self, mock_get_provider):
        from docmind.library.pipeline.rag import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value={"content": "The answer is 42."})
        mock_get_provider.return_value = mock_provider

        state = {
            "message": "What is the answer?",
            "retrieved_chunks": [],
            "persona": None,
            "conversation_history": [],
            "stream_callback": None,
        }

        reason_node(state)

        call_kwargs = mock_provider.chat.call_args
        system_prompt = call_kwargs.kwargs.get("system_prompt", "")
        assert "helpful document assistant" in system_prompt

    @patch("docmind.library.pipeline.rag.get_vlm_provider")
    def test_streams_tokens_when_callback_provided(self, mock_get_provider):
        from docmind.library.pipeline.rag import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value={"content": "The total is $500"})
        mock_get_provider.return_value = mock_provider

        streamed_events = []

        def mock_callback(event_type, **kwargs):
            streamed_events.append({"type": event_type, **kwargs})

        state = {
            "message": "How much?",
            "retrieved_chunks": [],
            "persona": None,
            "conversation_history": [],
            "stream_callback": mock_callback,
        }

        reason_node(state)

        token_events = [e for e in streamed_events if e["type"] == "token"]
        assert len(token_events) > 0

    @patch("docmind.library.pipeline.rag.get_vlm_provider")
    def test_includes_chunks_in_context(self, mock_get_provider):
        from docmind.library.pipeline.rag import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value={"content": "Answer"})
        mock_get_provider.return_value = mock_provider

        state = {
            "message": "Tell me about revenue",
            "retrieved_chunks": [
                {
                    "document_id": "doc-1",
                    "page_number": 3,
                    "content": "Revenue hit $5M in Q4.",
                    "similarity": 0.92,
                },
                {
                    "document_id": "doc-2",
                    "page_number": 1,
                    "content": "Expenses were $2M.",
                    "similarity": 0.80,
                },
            ],
            "persona": None,
            "conversation_history": [],
            "stream_callback": None,
        }

        reason_node(state)

        call_kwargs = mock_provider.chat.call_args
        full_message = call_kwargs.kwargs.get("message", "")
        assert "[Source 1:" in full_message
        assert "[Source 2:" in full_message
        assert "Revenue hit $5M" in full_message


class TestCiteNode:
    """Tests for cite_node."""

    def test_extracts_citations_from_answer(self):
        from docmind.library.pipeline.rag import cite_node

        state = {
            "raw_answer": "Based on [Source 1], the revenue was $1M. As noted in [Source 2], expenses were $500K.",
            "retrieved_chunks": [
                {
                    "document_id": "d1",
                    "page_number": 1,
                    "content": "Revenue was $1M in 2025.",
                    "similarity": 0.9,
                },
                {
                    "document_id": "d2",
                    "page_number": 3,
                    "content": "Expenses were $500K.",
                    "similarity": 0.85,
                },
            ],
        }

        result = cite_node(state)

        assert result["answer"] == state["raw_answer"]
        assert len(result["citations"]) == 2
        assert result["citations"][0]["source_index"] == 1
        assert result["citations"][0]["document_id"] == "d1"
        assert result["citations"][1]["source_index"] == 2
        assert result["citations"][1]["document_id"] == "d2"

    def test_no_citations_when_none_referenced(self):
        from docmind.library.pipeline.rag import cite_node

        state = {
            "raw_answer": "I could not find relevant information in the documents.",
            "retrieved_chunks": [
                {
                    "document_id": "d1",
                    "page_number": 1,
                    "content": "Some text",
                    "similarity": 0.75,
                },
            ],
        }

        result = cite_node(state)

        assert result["answer"] == state["raw_answer"]
        assert result["citations"] == []

    def test_partial_citations(self):
        from docmind.library.pipeline.rag import cite_node

        state = {
            "raw_answer": "According to [Source 2], the profit was high.",
            "retrieved_chunks": [
                {
                    "document_id": "d1",
                    "page_number": 1,
                    "content": "Revenue data",
                    "similarity": 0.9,
                },
                {
                    "document_id": "d2",
                    "page_number": 5,
                    "content": "Profit was very high this quarter.",
                    "similarity": 0.88,
                },
            ],
        }

        result = cite_node(state)

        assert len(result["citations"]) == 1
        assert result["citations"][0]["source_index"] == 2
        assert result["citations"][0]["page_number"] == 5

    def test_citations_include_content_preview(self):
        from docmind.library.pipeline.rag import cite_node

        long_content = "A" * 200
        state = {
            "raw_answer": "See [Source 1] for details.",
            "retrieved_chunks": [
                {
                    "document_id": "d1",
                    "page_number": 1,
                    "content": long_content,
                    "similarity": 0.9,
                },
            ],
        }

        result = cite_node(state)

        assert len(result["citations"]) == 1
        assert len(result["citations"][0]["content_preview"]) == 100


class TestRunRagChatPipeline:
    """Tests for run_rag_chat_pipeline full flow."""

    @patch("docmind.library.pipeline.rag.get_vlm_provider")
    @patch("docmind.library.pipeline.rag.retrieve_similar_chunks")
    @patch("docmind.library.pipeline.rag.embed_texts")
    @patch("docmind.library.pipeline.rag.get_settings")
    def test_full_flow(
        self, mock_settings, mock_embed, mock_retrieve, mock_get_provider
    ):
        from docmind.library.pipeline.rag import run_rag_chat_pipeline

        mock_settings.return_value = MagicMock(
            RAG_TOP_K=5, RAG_SIMILARITY_THRESHOLD=0.7
        )
        mock_embed.return_value = [[0.1, 0.2, 0.3]]
        mock_retrieve.return_value = [
            {
                "chunk_id": "c1",
                "document_id": "d1",
                "page_number": 1,
                "content": "Revenue was $1M.",
                "similarity": 0.9,
            }
        ]
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(
            return_value={"content": "Based on [Source 1], revenue was $1M."}
        )
        mock_get_provider.return_value = mock_provider

        initial_state = {
            "project_id": "proj-123",
            "user_id": "user-1",
            "message": "What is the revenue?",
            "persona": None,
            "conversation_history": [],
            "stream_callback": None,
        }

        result = run_rag_chat_pipeline(initial_state)

        assert "answer" in result
        assert "citations" in result
        assert len(result["citations"]) == 1
        assert result["citations"][0]["document_id"] == "d1"
        mock_embed.assert_called_once()
        mock_retrieve.assert_called_once()

    @patch("docmind.library.pipeline.rag.embed_texts")
    def test_handles_error_gracefully(self, mock_embed):
        from docmind.library.pipeline.rag import run_rag_chat_pipeline

        mock_embed.side_effect = RuntimeError("Embedding API down")

        initial_state = {
            "project_id": "proj-123",
            "user_id": "user-1",
            "message": "What is the revenue?",
            "persona": None,
            "conversation_history": [],
            "stream_callback": None,
        }

        result = run_rag_chat_pipeline(initial_state)

        assert "error" in result
        assert "answer" in result
        assert result["citations"] == []

    @patch("docmind.library.pipeline.rag.get_vlm_provider")
    @patch("docmind.library.pipeline.rag.retrieve_similar_chunks")
    @patch("docmind.library.pipeline.rag.embed_texts")
    @patch("docmind.library.pipeline.rag.get_settings")
    def test_invokes_stream_callback(
        self, mock_settings, mock_embed, mock_retrieve, mock_get_provider
    ):
        from docmind.library.pipeline.rag import run_rag_chat_pipeline

        mock_settings.return_value = MagicMock(
            RAG_TOP_K=5, RAG_SIMILARITY_THRESHOLD=0.7
        )
        mock_embed.return_value = [[0.1]]
        mock_retrieve.return_value = []
        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value={"content": "No data found."})
        mock_get_provider.return_value = mock_provider

        events = []

        def callback(event_type, content="", **kwargs):
            events.append(event_type)

        initial_state = {
            "project_id": "proj-1",
            "user_id": "u-1",
            "message": "Hello?",
            "persona": None,
            "conversation_history": [],
            "stream_callback": callback,
        }

        run_rag_chat_pipeline(initial_state)

        assert "intent" in events
        assert "retrieval" in events
        assert "reasoning" in events
        assert "done" in events


class TestFormatHistory:
    """Tests for _format_history helper."""

    def test_empty_history(self):
        from docmind.library.pipeline.rag import _format_history

        result = _format_history([])
        assert result == "No previous conversation."

    def test_with_messages(self):
        from docmind.library.pipeline.rag import _format_history

        history = [
            {"role": "user", "content": "What is the total?"},
            {"role": "assistant", "content": "The total is $500."},
        ]
        result = _format_history(history)

        assert "USER: What is the total?" in result
        assert "ASSISTANT: The total is $500." in result

    def test_defaults_role_to_user(self):
        from docmind.library.pipeline.rag import _format_history

        history = [{"content": "Hello"}]
        result = _format_history(history)

        assert "USER: Hello" in result
