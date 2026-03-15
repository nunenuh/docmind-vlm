# Issue #22: Chat Pipeline Reason + Cite Nodes

## Summary

Implement the `reason_node` and `cite_node` of the LangGraph chat pipeline. The reason node generates a grounded answer from document data only (no hallucination), using a strict system prompt that constrains the VLM to extracted field data. The cite node extracts citations with page number, bounding box, and text span by matching answer content to extracted fields. Together these complete the chat pipeline started in #21.

## Context

- **Phase**: 5
- **Priority**: P0
- **Labels**: `phase-5-chat`, `backend`, `tdd`
- **Dependencies**: #21 (chat pipeline router + retrieve)
- **Branch**: `feat/22-chat-pipeline-reason`
- **Estimated scope**: L

## Specs to Read

- `specs/backend/pipeline-chat.md` — reason_node, cite_node, GROUNDING_SYSTEM_PROMPT
- `specs/backend/providers.md` — VLM provider `chat()` method

## Current State (Scaffold)

The `chat.py` file currently has only the `ChatState` TypedDict and a stub `run_chat_pipeline`. After #21, the router and retrieve nodes will be implemented. This issue adds the remaining two nodes.

### Key types from pipeline spec:
```python
class Citation(TypedDict):
    page: int
    bounding_box: dict  # {x, y, width, height}
    text_span: str
```

### Expected reason_node behavior:
- Constructs context from `relevant_fields` and `re_queried_regions`
- Calls VLM provider with `GROUNDING_SYSTEM_PROMPT` + document context
- Streams tokens via `stream_callback` if provided
- Returns `{"raw_answer": str}`

### Expected cite_node behavior:
- Matches field values in the answer text
- Extracts page references from answer text
- Returns `{"answer": str, "citations": list[Citation]}`

## Requirements

### Functional

1. **`_build_context(state)`**: Build document context string from relevant_fields and re_queried_regions. Format each field as `- [key] = "value" (page N, confidence: high/medium/LOW)`.
2. **`_get_reasoning_instruction(intent)`**: Return intent-specific reasoning instructions (factual=precise, reasoning=step-by-step, summarization=synthesize, comparison=side-by-side).
3. **`reason_node(state)`**:
   - Constructs prompt from context + reasoning instruction + user message.
   - Calls VLM provider `chat()` with system prompt, images (max 4 pages), and conversation history.
   - Streams tokens via `stream_callback` if present.
   - Returns `{"raw_answer": str}`.
   - On error, returns error message string (does not raise).
4. **`_extract_page_references(answer)`**: Parse "page N", "p.N", "pN" references from answer text.
5. **`_match_citations(answer, relevant_fields)`**: Match field values in answer to generate citations. Deduplicate by `page:value`.
6. **`cite_node(state)`**:
   - Extracts citations from answer + relevant_fields.
   - Streams citation events via `stream_callback`.
   - Sends `done` event.
   - Returns `{"answer": str, "citations": list[Citation]}`.

### Non-Functional

- Grounding system prompt strictly forbids hallucination.
- Conversation history capped at 6 messages in context.
- Page images capped at 4 for token efficiency.
- All nodes work without `stream_callback` (callback is optional).

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/pipeline/test_chat_reason.py`

```python
"""Unit tests for chat pipeline reason_node."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestBuildContext:
    """Tests for _build_context helper."""

    def test_builds_context_from_relevant_fields(self):
        from docmind.library.pipeline.chat import _build_context

        state = {
            "relevant_fields": [
                {
                    "field_key": "vendor_name",
                    "field_value": "Acme Corp",
                    "page_number": 1,
                    "confidence": 0.92,
                },
                {
                    "field_key": "total_amount",
                    "field_value": "$1,500.00",
                    "page_number": 1,
                    "confidence": 0.45,
                },
            ],
            "re_queried_regions": [],
            "conversation_history": [],
        }

        context = _build_context(state)

        assert "vendor_name" in context
        assert "Acme Corp" in context
        assert "high" in context.lower()  # 0.92 = high confidence
        assert "low" in context.lower()   # 0.45 = LOW confidence

    def test_includes_re_queried_regions(self):
        from docmind.library.pipeline.chat import _build_context

        state = {
            "relevant_fields": [],
            "re_queried_regions": [
                {
                    "field_key": "total",
                    "detailed_value": "The total is $1,500.00 including tax",
                    "page_number": 1,
                },
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

        # Should only include last 6
        assert "Message 4" in context
        assert "Message 9" in context
        # Message 0 through 3 should be excluded
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
        def mock_callback(type, **kwargs):
            streamed_events.append({"type": type, **kwargs})

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

        # Should not raise, should return error message
        assert "raw_answer" in result
        assert "error" in result["raw_answer"].lower() or "error_message" in result

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

        # Check that only 4 images were passed to provider.chat
        call_kwargs = mock_provider.chat.call_args
        images_arg = call_kwargs.kwargs.get("images") or call_kwargs[1].get("images", [])
        assert len(images_arg) <= 4
```

**Test file**: `backend/tests/unit/library/pipeline/test_chat_cite.py`

```python
"""Unit tests for chat pipeline cite_node and citation extraction."""
import pytest


class TestExtractPageReferences:
    """Tests for _extract_page_references helper."""

    def test_extracts_page_N_format(self):
        from docmind.library.pipeline.chat import _extract_page_references

        pages = _extract_page_references("The total on page 1 is $1,500. See page 3 for details.")

        assert 1 in pages
        assert 3 in pages

    def test_extracts_p_dot_N_format(self):
        from docmind.library.pipeline.chat import _extract_page_references

        pages = _extract_page_references("As shown on p. 2, the vendor is Acme.")

        assert 2 in pages

    def test_returns_empty_for_no_references(self):
        from docmind.library.pipeline.chat import _extract_page_references

        pages = _extract_page_references("The invoice total is $1,500.")

        assert pages == []

    def test_deduplicates_page_numbers(self):
        from docmind.library.pipeline.chat import _extract_page_references

        pages = _extract_page_references("Page 1 shows the header. Also on page 1 is the date.")

        assert pages == [1]

    def test_returns_sorted_pages(self):
        from docmind.library.pipeline.chat import _extract_page_references

        pages = _extract_page_references("See page 3, then page 1, then page 2.")

        assert pages == [1, 2, 3]


class TestMatchCitations:
    """Tests for _match_citations helper."""

    def test_matches_field_values_in_answer(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "The invoice number is INV-2026-001 and the vendor is Acme Corp."
        fields = [
            {
                "field_key": "invoice_number",
                "field_value": "INV-2026-001",
                "page_number": 1,
                "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                "confidence": 0.95,
            },
            {
                "field_key": "vendor_name",
                "field_value": "Acme Corp",
                "page_number": 1,
                "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.05},
                "confidence": 0.90,
            },
        ]

        citations = _match_citations(answer, fields)

        assert len(citations) == 2
        text_spans = [c["text_span"] for c in citations]
        assert "INV-2026-001" in text_spans
        assert "Acme Corp" in text_spans

    def test_skips_short_field_values(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "The value is A."
        fields = [
            {
                "field_key": "code",
                "field_value": "A",  # Too short (< 2 chars)
                "page_number": 1,
                "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.1, "height": 0.05},
                "confidence": 0.9,
            },
        ]

        citations = _match_citations(answer, fields)

        assert len(citations) == 0

    def test_deduplicates_citations(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "The vendor Acme Corp is also known as Acme Corp."
        fields = [
            {
                "field_key": "vendor",
                "field_value": "Acme Corp",
                "page_number": 1,
                "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                "confidence": 0.9,
            },
        ]

        citations = _match_citations(answer, fields)

        # Same page:value should only produce one citation
        assert len(citations) == 1

    def test_case_insensitive_matching(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "The vendor is acme corp."
        fields = [
            {
                "field_key": "vendor",
                "field_value": "Acme Corp",
                "page_number": 1,
                "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                "confidence": 0.9,
            },
        ]

        citations = _match_citations(answer, fields)

        assert len(citations) == 1

    def test_adds_page_reference_citations(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "On page 2, the amount is shown."
        fields = [
            {
                "field_key": "amount",
                "field_value": "$500",
                "page_number": 2,
                "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05},
                "confidence": 0.85,
            },
        ]

        citations = _match_citations(answer, fields)

        # Should have a citation for page 2 even though "$500" doesn't appear in answer
        page_nums = [c["page"] for c in citations]
        assert 2 in page_nums

    def test_empty_answer_returns_empty(self):
        from docmind.library.pipeline.chat import _match_citations

        citations = _match_citations("", [])

        assert citations == []


class TestCiteNode:
    """Tests for cite_node pipeline function."""

    def test_returns_answer_and_citations(self):
        from docmind.library.pipeline.chat import cite_node

        state = {
            "raw_answer": "The invoice number is INV-2026-001.",
            "relevant_fields": [
                {
                    "field_key": "invoice_number",
                    "field_value": "INV-2026-001",
                    "page_number": 1,
                    "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                    "confidence": 0.95,
                },
            ],
            "stream_callback": None,
        }

        result = cite_node(state)

        assert "answer" in result
        assert "citations" in result
        assert result["answer"] == "The invoice number is INV-2026-001."
        assert len(result["citations"]) > 0

    def test_streams_citations_when_callback(self):
        from docmind.library.pipeline.chat import cite_node

        streamed = []
        def callback(type, **kwargs):
            streamed.append({"type": type, **kwargs})

        state = {
            "raw_answer": "The vendor is Acme Corp.",
            "relevant_fields": [
                {
                    "field_key": "vendor",
                    "field_value": "Acme Corp",
                    "page_number": 1,
                    "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                    "confidence": 0.9,
                },
            ],
            "stream_callback": callback,
        }

        cite_node(state)

        citation_events = [e for e in streamed if e["type"] == "citation"]
        done_events = [e for e in streamed if e["type"] == "done"]

        assert len(citation_events) >= 1
        assert len(done_events) == 1

    def test_works_without_callback(self):
        from docmind.library.pipeline.chat import cite_node

        state = {
            "raw_answer": "The total is $1,500.",
            "relevant_fields": [],
            "stream_callback": None,
        }

        result = cite_node(state)

        assert result["answer"] == "The total is $1,500."
        assert result["citations"] == []

    def test_citation_has_correct_structure(self):
        from docmind.library.pipeline.chat import cite_node

        state = {
            "raw_answer": "The vendor is Acme Corp on page 1.",
            "relevant_fields": [
                {
                    "field_key": "vendor",
                    "field_value": "Acme Corp",
                    "page_number": 1,
                    "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                    "confidence": 0.9,
                },
            ],
            "stream_callback": None,
        }

        result = cite_node(state)

        for citation in result["citations"]:
            assert "page" in citation
            assert "bounding_box" in citation
            assert "text_span" in citation
            assert isinstance(citation["page"], int)
```

### Step 2: Implement (GREEN)

1. **`chat.py`**: Implement `_build_context`, `_get_reasoning_instruction`, `reason_node`, `_extract_page_references`, `_match_citations`, `cite_node` exactly as specified in `specs/backend/pipeline-chat.md`.
2. Import `get_vlm_provider` from `docmind.library.providers`.
3. Handle VLM provider errors gracefully in `reason_node`.

### Step 3: Refactor (IMPROVE)

- Extract the grounding system prompt to a module-level constant.
- Add comprehensive logging in each node.
- Ensure all citation bounding boxes are valid dicts (not empty).

## Acceptance Criteria

- [ ] `reason_node` calls VLM with grounding system prompt
- [ ] `reason_node` limits page images to 4 and conversation history to 6
- [ ] `reason_node` streams tokens via callback when provided
- [ ] `reason_node` handles VLM errors gracefully (no raise)
- [ ] `cite_node` matches field values in answer text
- [ ] `cite_node` extracts page references from answer
- [ ] `cite_node` deduplicates citations
- [ ] `cite_node` streams citation events when callback provided
- [ ] All nodes work without `stream_callback`
- [ ] All unit tests pass

## Files Changed

- `backend/src/docmind/library/pipeline/chat.py` — add reason_node + cite_node
- `backend/tests/unit/library/pipeline/test_chat_reason.py` — new
- `backend/tests/unit/library/pipeline/test_chat_cite.py` — new

## Verification

```bash
cd backend
pytest tests/unit/library/pipeline/test_chat_reason.py -v
pytest tests/unit/library/pipeline/test_chat_cite.py -v
```
