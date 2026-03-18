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
            {"field_key": "invoice_number", "field_value": "INV-2026-001",
             "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
             "confidence": 0.95},
            {"field_key": "vendor_name", "field_value": "Acme Corp",
             "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.1, "width": 0.4, "height": 0.05},
             "confidence": 0.90},
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
            {"field_key": "code", "field_value": "A",
             "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.1, "height": 0.05},
             "confidence": 0.9},
        ]

        citations = _match_citations(answer, fields)
        assert len(citations) == 0

    def test_deduplicates_citations(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "The vendor Acme Corp is also known as Acme Corp."
        fields = [
            {"field_key": "vendor", "field_value": "Acme Corp",
             "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
             "confidence": 0.9},
        ]

        citations = _match_citations(answer, fields)
        assert len(citations) == 1

    def test_case_insensitive_matching(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "The vendor is acme corp."
        fields = [
            {"field_key": "vendor", "field_value": "Acme Corp",
             "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
             "confidence": 0.9},
        ]

        citations = _match_citations(answer, fields)
        assert len(citations) == 1

    def test_adds_page_reference_citations(self):
        from docmind.library.pipeline.chat import _match_citations

        answer = "On page 2, the amount is shown."
        fields = [
            {"field_key": "amount", "field_value": "$500",
             "page_number": 2, "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05},
             "confidence": 0.85},
        ]

        citations = _match_citations(answer, fields)
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
                {"field_key": "invoice_number", "field_value": "INV-2026-001",
                 "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                 "confidence": 0.95},
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

        def callback(event_type, **kwargs):
            streamed.append({"type": event_type, **kwargs})

        state = {
            "raw_answer": "The vendor is Acme Corp.",
            "relevant_fields": [
                {"field_key": "vendor", "field_value": "Acme Corp",
                 "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                 "confidence": 0.9},
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
                {"field_key": "vendor", "field_value": "Acme Corp",
                 "page_number": 1, "bounding_box": {"x": 0.1, "y": 0.2, "width": 0.3, "height": 0.05},
                 "confidence": 0.9},
            ],
            "stream_callback": None,
        }

        result = cite_node(state)

        for citation in result["citations"]:
            assert "page" in citation
            assert "bounding_box" in citation
            assert "text_span" in citation
            assert isinstance(citation["page"], int)
