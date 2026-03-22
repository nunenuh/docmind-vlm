"""Unit tests for chat pipeline retrieve_node and field search."""
import pytest
from unittest.mock import MagicMock


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

        many_fields = sample_fields * 10
        results = _search_fields(many_fields, "invoice", "factual_lookup")

        assert len(results) <= 5

    def test_summarization_allows_more_fields(self, sample_fields):
        from docmind.library.pipeline.chat import _search_fields

        many_fields = sample_fields * 10
        results = _search_fields(many_fields, "overview of everything", "summarization")

        assert len(results) <= 20

    def test_falls_back_to_all_fields_for_no_keyword_match(self, sample_fields):
        """When no keywords match, falls back to all fields for broad context."""
        from docmind.library.pipeline.chat import _search_fields

        results = _search_fields(sample_fields, "xyzzyspoon", "factual_lookup")

        # Fallback: returns all fields so VLM has context for generic queries
        assert len(results) > 0

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
            "page_images": [],
        }

        result = retrieve_node(state)

        assert result["re_queried_regions"] == []

    def test_no_requery_for_non_factual_intents(self, sample_fields):
        from docmind.library.pipeline.chat import retrieve_node

        state = {
            "message": "Summarize the document",
            "intent": "summarization",
            "extracted_fields": sample_fields,
            "page_images": [MagicMock()],
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
