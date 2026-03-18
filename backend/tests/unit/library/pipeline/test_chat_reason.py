"""Unit tests for chat pipeline reason_node."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBuildContext:
    """Tests for _build_context helper."""

    def test_builds_context_from_relevant_fields(self):
        from docmind.library.pipeline.chat import _build_context

        state = {
            "relevant_fields": [
                {"field_key": "vendor_name", "field_value": "Acme Corp",
                 "page_number": 1, "confidence": 0.92},
                {"field_key": "total_amount", "field_value": "$1,500.00",
                 "page_number": 1, "confidence": 0.45},
            ],
            "re_queried_regions": [],
            "conversation_history": [],
        }

        context = _build_context(state)

        assert "vendor_name" in context
        assert "Acme Corp" in context
        assert "high" in context.lower()
        assert "low" in context.lower()

    def test_includes_re_queried_regions(self):
        from docmind.library.pipeline.chat import _build_context

        state = {
            "relevant_fields": [],
            "re_queried_regions": [
                {"field_key": "total", "detailed_value": "The total is $1,500.00",
                 "page_number": 1},
            ],
            "conversation_history": [],
        }

        context = _build_context(state)

        assert "DETAILED RE-ANALYSIS" in context
        assert "total" in context.lower()

    def test_includes_conversation_history(self):
        from docmind.library.pipeline.chat import _build_context

        state = {
            "relevant_fields": [],
            "re_queried_regions": [],
            "conversation_history": [
                {"role": "user", "content": "What is the total?"},
                {"role": "assistant", "content": "The total is $1,500."},
            ],
        }

        context = _build_context(state)

        assert "CONVERSATION HISTORY" in context
        assert "USER" in context
        assert "ASSISTANT" in context

    def test_caps_conversation_history_at_6(self):
        from docmind.library.pipeline.chat import _build_context

        state = {
            "relevant_fields": [],
            "re_queried_regions": [],
            "conversation_history": [
                {"role": "user", "content": f"Message {i}"}
                for i in range(10)
            ],
        }

        context = _build_context(state)

        assert "Message 4" in context
        assert "Message 9" in context
        assert "Message 0" not in context


class TestGetReasoningInstruction:
    """Tests for _get_reasoning_instruction helper."""

    def test_factual_lookup_instruction(self):
        from docmind.library.pipeline.chat import _get_reasoning_instruction

        instruction = _get_reasoning_instruction("factual_lookup")
        assert "precise" in instruction.lower() or "exact" in instruction.lower()

    def test_reasoning_instruction(self):
        from docmind.library.pipeline.chat import _get_reasoning_instruction

        instruction = _get_reasoning_instruction("reasoning")
        assert "step" in instruction.lower()

    def test_summarization_instruction(self):
        from docmind.library.pipeline.chat import _get_reasoning_instruction

        instruction = _get_reasoning_instruction("summarization")
        assert "summar" in instruction.lower() or "synthe" in instruction.lower()

    def test_comparison_instruction(self):
        from docmind.library.pipeline.chat import _get_reasoning_instruction

        instruction = _get_reasoning_instruction("comparison")
        assert "compar" in instruction.lower() or "side" in instruction.lower()

    def test_unknown_intent_returns_factual(self):
        from docmind.library.pipeline.chat import _get_reasoning_instruction

        instruction = _get_reasoning_instruction("unknown")
        factual = _get_reasoning_instruction("factual_lookup")
        assert instruction == factual


class TestReasonNode:
    """Tests for reason_node pipeline function."""

    @patch("docmind.library.pipeline.chat.get_vlm_provider")
    def test_returns_raw_answer(self, mock_get_provider):
        from docmind.library.pipeline.chat import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value={"content": "The invoice number is INV-2026-001."})
        mock_get_provider.return_value = mock_provider

        state = {
            "message": "What is the invoice number?",
            "intent": "factual_lookup",
            "page_images": [],
            "conversation_history": [],
            "relevant_fields": [
                {"field_key": "invoice_number", "field_value": "INV-2026-001",
                 "page_number": 1, "confidence": 0.95},
            ],
            "re_queried_regions": [],
            "stream_callback": None,
        }

        result = reason_node(state)

        assert "raw_answer" in result
        assert "INV-2026-001" in result["raw_answer"]

    @patch("docmind.library.pipeline.chat.get_vlm_provider")
    def test_streams_tokens_when_callback_provided(self, mock_get_provider):
        from docmind.library.pipeline.chat import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value={"content": "The total is $1500"})
        mock_get_provider.return_value = mock_provider

        streamed_events = []

        def mock_callback(event_type, **kwargs):
            streamed_events.append({"type": event_type, **kwargs})

        state = {
            "message": "How much?",
            "intent": "factual_lookup",
            "page_images": [],
            "conversation_history": [],
            "relevant_fields": [],
            "re_queried_regions": [],
            "stream_callback": mock_callback,
        }

        reason_node(state)

        token_events = [e for e in streamed_events if e["type"] == "token"]
        assert len(token_events) > 0

    @patch("docmind.library.pipeline.chat.get_vlm_provider")
    def test_handles_provider_error_gracefully(self, mock_get_provider):
        from docmind.library.pipeline.chat import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(side_effect=Exception("API timeout"))
        mock_get_provider.return_value = mock_provider

        state = {
            "message": "What is the total?",
            "intent": "factual_lookup",
            "page_images": [],
            "conversation_history": [],
            "relevant_fields": [],
            "re_queried_regions": [],
            "stream_callback": None,
        }

        result = reason_node(state)

        assert "raw_answer" in result

    @patch("docmind.library.pipeline.chat.get_vlm_provider")
    def test_limits_page_images_to_4(self, mock_get_provider):
        from docmind.library.pipeline.chat import reason_node

        mock_provider = MagicMock()
        mock_provider.chat = AsyncMock(return_value={"content": "Answer"})
        mock_get_provider.return_value = mock_provider

        state = {
            "message": "Summarize",
            "intent": "summarization",
            "page_images": [MagicMock() for _ in range(10)],
            "conversation_history": [],
            "relevant_fields": [],
            "re_queried_regions": [],
            "stream_callback": None,
        }

        reason_node(state)

        call_kwargs = mock_provider.chat.call_args
        images_arg = call_kwargs.kwargs.get("images") or call_kwargs[1].get("images", [])
        assert len(images_arg) <= 4
