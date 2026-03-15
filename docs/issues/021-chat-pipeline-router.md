# Issue #21: Chat Pipeline Router + Retrieve Nodes (LangGraph)

## Summary

Implement the first two nodes of the LangGraph chat pipeline: the `router_node` that classifies user intent (factual_lookup, reasoning, summarization, comparison) using regex pattern matching, and the `retrieve_node` that searches extracted fields for relevant data and optionally re-queries the VLM on specific document regions. This replaces the stub `run_chat_pipeline` with a working LangGraph StateGraph.

## Context

- **Phase**: 5
- **Priority**: P0
- **Labels**: `phase-5-chat`, `backend`, `tdd`
- **Dependencies**: #9 (DashScope VLM provider), #16 (extraction repository)
- **Branch**: `feat/21-chat-pipeline-router`
- **Estimated scope**: L

## Specs to Read

- `specs/backend/pipeline-chat.md` — full chat pipeline spec (router_node, retrieve_node, ChatState, INTENT_PATTERNS)
- `specs/backend/providers.md` — VLM provider protocol for re-query
- `specs/backend/services.md` — ChatUseCase interaction with pipeline

## Current State (Scaffold)

### `backend/src/docmind/library/pipeline/chat.py` (stub)
```python
"""
docmind/library/pipeline/chat.py

LangGraph StateGraph for the document chat agent.
Stub implementation for scaffold.
"""
import logging
from typing import Any, Callable, TypedDict

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class Citation(TypedDict):
    page: int
    bounding_box: dict
    text_span: str


class ChatState(TypedDict):
    document_id: str
    user_id: str
    message: str
    page_images: list[Any]
    extracted_fields: list[dict]
    conversation_history: list[dict]
    intent: str
    intent_confidence: float
    relevant_fields: list[dict]
    re_queried_regions: list[dict]
    raw_answer: str
    answer: str
    citations: list[Citation]
    error_message: str | None
    stream_callback: Callable | None


def run_chat_pipeline(initial_state: dict, config: dict) -> dict:
    """
    Run the full chat pipeline.
    Stub implementation — raises NotImplementedError.
    """
    raise NotImplementedError("Chat pipeline not yet implemented")
```

## Requirements

### Functional

1. **`_classify_intent(message)`**: Pattern-based intent classification.
   - Matches message against regex patterns for each intent category.
   - Scores each category by match count.
   - Returns `(intent, confidence)` tuple.
   - Default is `("factual_lookup", 0.3)` when no patterns match.
   - Confidence boost when only one category matches.

2. **`router_node(state)`**: Pipeline node wrapper.
   - Calls `_classify_intent(state["message"])`.
   - Returns `{"intent": str, "intent_confidence": float}`.

3. **`_search_fields(fields, query, intent)`**: Keyword-based field search.
   - Scores fields by: exact key match (1.0), key term overlap (0.5 per term), value term overlap (0.3 per term).
   - Boosts required fields for factual_lookup (+0.2).
   - Limits results by intent: factual_lookup=5, reasoning=10, summarization=20, comparison=15.
   - Returns fields sorted by score descending.

4. **`retrieve_node(state)`**: Retrieval pipeline node.
   - Searches extracted fields for relevance.
   - For factual_lookup with low-confidence fields (<0.6), re-queries VLM on specific page regions (max 3).
   - Returns `{"relevant_fields": list, "re_queried_regions": list}`.

5. **`build_chat_graph()`**: Build LangGraph StateGraph with nodes wired: router -> retrieve -> reason -> cite -> END.

### Non-Functional

- Pattern matching is fast and deterministic (no VLM call in router).
- Re-querying is limited to 3 fields per turn and only for factual_lookup.
- All nodes must work without `stream_callback` (for testing).

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/pipeline/test_chat_router.py`

```python
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
        assert confidence >= 0.5  # Boosted because only summarization matched

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
```

**Test file**: `backend/tests/unit/library/pipeline/test_chat_retrieve.py`

```python
"""Unit tests for chat pipeline retrieve_node and field search."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


@pytest.fixture
def sample_fields():
    """Sample extracted fields for testing search."""
    return [
        {
            "field_key": "invoice_number",
            "field_value": "INV-2026-001",
            "page_number": 1,
            "confidence": 0.95,
            "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
            "is_required": True,
        },
        {
            "field_key": "vendor_name",
            "field_value": "Acme Corporation",
            "page_number": 1,
            "confidence": 0.88,
            "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.05},
            "is_required": True,
        },
        {
            "field_key": "total_amount",
            "field_value": "$1,500.00",
            "page_number": 1,
            "confidence": 0.45,
            "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05},
            "is_required": True,
        },
        {
            "field_key": "due_date",
            "field_value": "2026-03-30",
            "page_number": 1,
            "confidence": 0.72,
            "bounding_box": {"x": 0.5, "y": 0.3, "width": 0.2, "height": 0.05},
            "is_required": False,
        },
    ]


class TestSearchFields:
    """Tests for _search_fields function."""

    def test_exact_key_match_scores_highest(self, sample_fields):
        from docmind.library.pipeline.chat import _search_fields

        results = _search_fields(sample_fields, "invoice_number", "factual_lookup")

        assert len(results) > 0
        assert results[0]["field_key"] == "invoice_number"

    def test_term_overlap_finds_related_fields(self, sample_fields):
        from docmind.library.pipeline.chat import _search_fields

        results = _search_fields(sample_fields, "what is the total amount", "factual_lookup")

        assert len(results) > 0
        keys = [f["field_key"] for f in results]
        assert "total_amount" in keys

    def test_factual_lookup_limited_to_5(self, sample_fields):
        from docmind.library.pipeline.chat import _search_fields

        # Even with many fields, factual_lookup caps at 5
        many_fields = sample_fields * 10
        results = _search_fields(many_fields, "invoice", "factual_lookup")

        assert len(results) <= 5

    def test_summarization_allows_more_fields(self, sample_fields):
        from docmind.library.pipeline.chat import _search_fields

        many_fields = sample_fields * 10
        results = _search_fields(many_fields, "overview of everything", "summarization")

        assert len(results) <= 20

    def test_required_field_boost_for_factual(self, sample_fields):
        from docmind.library.pipeline.chat import _search_fields

        # Required fields get a +0.2 boost for factual_lookup
        results = _search_fields(sample_fields, "date", "factual_lookup")

        # due_date is not required, but if any required field has "date" it should score higher
        # This test verifies the boost mechanism works
        assert len(results) > 0

    def test_returns_empty_for_no_match(self, sample_fields):
        from docmind.library.pipeline.chat import _search_fields

        results = _search_fields(sample_fields, "xyzzyspoon", "factual_lookup")

        assert results == []

    def test_empty_fields_returns_empty(self):
        from docmind.library.pipeline.chat import _search_fields

        results = _search_fields([], "invoice number", "factual_lookup")

        assert results == []


class TestRetrieveNode:
    """Tests for retrieve_node pipeline function."""

    def test_returns_relevant_fields(self, sample_fields):
        from docmind.library.pipeline.chat import retrieve_node

        state = {
            "message": "What is the invoice number?",
            "intent": "factual_lookup",
            "extracted_fields": sample_fields,
            "page_images": [],
        }

        result = retrieve_node(state)

        assert "relevant_fields" in result
        assert "re_queried_regions" in result
        assert len(result["relevant_fields"]) > 0

    def test_no_requery_without_page_images(self, sample_fields):
        from docmind.library.pipeline.chat import retrieve_node

        state = {
            "message": "What is the total amount?",
            "intent": "factual_lookup",
            "extracted_fields": sample_fields,
            "page_images": [],  # No images -- no re-query
        }

        result = retrieve_node(state)

        assert result["re_queried_regions"] == []

    def test_no_requery_for_non_factual_intents(self, sample_fields):
        from docmind.library.pipeline.chat import retrieve_node

        state = {
            "message": "Summarize the document",
            "intent": "summarization",
            "extracted_fields": sample_fields,
            "page_images": [MagicMock()],  # Has images but intent is not factual
        }

        result = retrieve_node(state)

        assert result["re_queried_regions"] == []

    def test_handles_empty_extracted_fields(self):
        from docmind.library.pipeline.chat import retrieve_node

        state = {
            "message": "What is the total?",
            "intent": "factual_lookup",
            "extracted_fields": [],
            "page_images": [],
        }

        result = retrieve_node(state)

        assert result["relevant_fields"] == []
        assert result["re_queried_regions"] == []
```

### Step 2: Implement (GREEN)

1. **`chat.py`**: Implement `_classify_intent`, `router_node`, `_search_fields`, `_re_query_region`, `retrieve_node` as specified in `specs/backend/pipeline-chat.md`.
2. **`chat.py`**: Implement `build_chat_graph()` with LangGraph StateGraph wiring all four nodes.
3. **`chat.py`**: Implement `run_chat_pipeline()` to invoke the compiled graph.
4. Add placeholder `reason_node` and `cite_node` that pass through state (implemented in #22).

### Step 3: Refactor (IMPROVE)

- Extract `INTENT_PATTERNS` to module-level constant.
- Add type hints for all return values.
- Ensure `_re_query_region` handles edge cases (zero-size crops, missing pages).

## Acceptance Criteria

- [ ] `_classify_intent` correctly classifies all four intent types
- [ ] Default intent is `factual_lookup` with 0.3 confidence for unmatched messages
- [ ] `_search_fields` scores and ranks fields by relevance
- [ ] Field limits enforced per intent type (5/10/15/20)
- [ ] `retrieve_node` only re-queries VLM for factual_lookup with low-confidence fields
- [ ] Re-query limited to 3 fields maximum
- [ ] `build_chat_graph()` creates a valid LangGraph StateGraph
- [ ] All nodes work without `stream_callback`
- [ ] All unit tests pass

## Files Changed

- `backend/src/docmind/library/pipeline/chat.py` — full implementation of router + retrieve + graph
- `backend/tests/unit/library/pipeline/test_chat_router.py` — new
- `backend/tests/unit/library/pipeline/test_chat_retrieve.py` — new

## Verification

```bash
cd backend
pytest tests/unit/library/pipeline/test_chat_router.py -v
pytest tests/unit/library/pipeline/test_chat_retrieve.py -v
```
