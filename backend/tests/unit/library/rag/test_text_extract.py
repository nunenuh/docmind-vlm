"""Tests for docmind.library.rag.text_extract."""

from unittest.mock import MagicMock, patch

from docmind.library.rag.text_extract import (
    extract_text,
    extract_text_from_image,
    extract_text_from_pdf,
)


class TestExtractTextFromPdf:
    """Tests for extract_text_from_pdf."""

    @patch("docmind.library.rag.text_extract.fitz")
    def test_extract_text_from_pdf_returns_pages(self, mock_fitz):
        mock_page_1 = MagicMock()
        mock_page_1.get_text.return_value = "Page one text."
        mock_page_2 = MagicMock()
        mock_page_2.get_text.return_value = "Page two text."

        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page_1, mock_page_2])
        mock_doc.__len__ = lambda self: 2
        mock_fitz.open.return_value = mock_doc

        result = extract_text_from_pdf(b"fake pdf bytes")

        assert len(result) == 2
        assert result[0] == {"page_number": 1, "text": "Page one text."}
        assert result[1] == {"page_number": 2, "text": "Page two text."}
        mock_fitz.open.assert_called_once_with(stream=b"fake pdf bytes", filetype="pdf")
        mock_doc.close.assert_called_once()


class TestExtractTextFromImage:
    """Tests for extract_text_from_image."""

    def test_extract_text_from_image_returns_empty(self):
        result = extract_text_from_image(b"fake image bytes")

        assert len(result) == 1
        assert result[0] == {"page_number": 1, "text": ""}


class TestExtractText:
    """Tests for extract_text routing."""

    @patch("docmind.library.rag.text_extract.fitz")
    def test_extract_text_routes_pdf(self, mock_fitz):
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Hello"
        mock_doc = MagicMock()
        mock_doc.__iter__ = lambda self: iter([mock_page])
        mock_fitz.open.return_value = mock_doc

        result = extract_text(b"pdf bytes", "pdf")

        assert len(result) == 1
        assert result[0]["page_number"] == 1
        mock_fitz.open.assert_called_once()

    def test_extract_text_routes_image(self):
        result = extract_text(b"img bytes", "png")

        assert len(result) == 1
        assert result[0]["text"] == ""

    def test_extract_text_routes_jpg(self):
        result = extract_text(b"img bytes", "jpg")

        assert len(result) == 1
        assert result[0]["text"] == ""
