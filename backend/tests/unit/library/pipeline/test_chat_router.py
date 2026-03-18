"""Unit tests for chat pipeline router_node and intent classification."""
import pytest


class TestClassifyIntent:
    """Tests for _classify_intent function."""

    def test_factual_lookup_what_is(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, confidence = _classify_intent("What is the invoice number?")
        assert intent == "factual_lookup"
        assert confidence > 0.3

    def test_factual_lookup_how_much(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("How much is the total amount?")
        assert intent == "factual_lookup"

    def test_reasoning_why(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("Why is the tax amount different from the subtotal?")
        assert intent == "reasoning"

    def test_reasoning_explain(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("Explain the payment terms")
        assert intent == "reasoning"

    def test_summarization_summarize(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("Summarize this document")
        assert intent == "summarization"

    def test_summarization_overview(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("Give me an overview of the contract")
        assert intent == "summarization"

    def test_comparison_compare(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("Compare the subtotal and total amount")
        assert intent == "comparison"

    def test_comparison_difference(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("What is the difference between gross and net?")
        assert intent == "comparison"

    def test_default_intent_for_ambiguous_message(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, confidence = _classify_intent("hello there")
        assert intent == "factual_lookup"
        assert confidence == 0.3

    def test_confidence_boost_single_category(self):
        from docmind.library.pipeline.chat import _classify_intent

        _, confidence = _classify_intent("Summarize this document please")
        assert confidence >= 0.5

    def test_case_insensitive(self):
        from docmind.library.pipeline.chat import _classify_intent

        intent, _ = _classify_intent("WHAT IS THE TOTAL?")
        assert intent == "factual_lookup"


class TestRouterNode:
    """Tests for router_node pipeline function."""

    def test_returns_intent_and_confidence(self):
        from docmind.library.pipeline.chat import router_node

        state = {
            "message": "What is the invoice number?",
            "document_id": "doc-001",
            "user_id": "user-001",
        }
        result = router_node(state)

        assert "intent" in result
        assert "intent_confidence" in result
        assert result["intent"] in ["factual_lookup", "reasoning", "summarization", "comparison"]
        assert 0.0 <= result["intent_confidence"] <= 1.0

    def test_empty_message_returns_default(self):
        from docmind.library.pipeline.chat import router_node

        state = {"message": ""}
        result = router_node(state)

        assert result["intent"] == "factual_lookup"
        assert result["intent_confidence"] == 0.3
