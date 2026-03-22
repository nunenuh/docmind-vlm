"""Tests for text extraction with pymupdf4llm."""
from docmind.library.rag.text_extract import (
    extract_text,
    extract_text_from_image,
    _extract_headers,
)


class TestExtractHeaders:
    def test_extracts_markdown_headers(self):
        text = "# Title\nSome text\n## Subtitle\nMore text"
        headers = _extract_headers(text)
        assert headers == ["Title", "Subtitle"]

    def test_no_headers(self):
        assert _extract_headers("Just plain text") == []

    def test_various_levels(self):
        text = "# H1\n## H2\n### H3\n#### H4"
        headers = _extract_headers(text)
        assert len(headers) == 4

    def test_empty_text(self):
        assert _extract_headers("") == []


class TestExtractTextFromImage:
    def test_returns_empty_with_headers(self):
        result = extract_text_from_image(b"image bytes")
        assert len(result) == 1
        assert result[0]["text"] == ""
        assert result[0]["headers"] == []


class TestExtractText:
    def test_routes_image_types(self):
        for ft in ["png", "jpg", "jpeg", "tiff", "webp"]:
            result = extract_text(b"img", ft)
            assert result[0]["text"] == ""
            assert result[0]["headers"] == []

    def test_image_returns_page_number_1(self):
        result = extract_text(b"img", "png")
        assert result[0]["page_number"] == 1
