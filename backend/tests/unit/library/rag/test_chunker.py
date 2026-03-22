"""Tests for header-aware contextual chunking."""
from docmind.library.rag.chunker import (
    chunk_text,
    chunk_pages,
    _split_by_headers,
    _contextualize_chunk,
)


class TestChunkText:
    def test_empty_returns_empty(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_short_text_single_chunk(self):
        result = chunk_text("Hello world.", chunk_size=100)
        assert result == ["Hello world."]

    def test_splits_by_sentences(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        result = chunk_text(text, chunk_size=40, overlap=0)
        assert len(result) >= 2
        assert "First sentence." in result[0]

    def test_overlap_includes_context(self):
        text = "A" * 100 + ". " + "B" * 100 + ". " + "C" * 100
        result = chunk_text(text, chunk_size=120, overlap=20)
        assert len(result) >= 2

    def test_respects_sentence_boundaries(self):
        text = "Hello world. This is a test. Another sentence here."
        chunks = chunk_text(text, chunk_size=30, overlap=0)
        for chunk in chunks:
            assert not chunk.startswith(" ")


class TestSplitByHeaders:
    def test_splits_on_headers(self):
        text = "# Title\nSome intro.\n## Section 1\nContent one.\n## Section 2\nContent two."
        sections = _split_by_headers(text)
        assert len(sections) == 3
        assert sections[0]["header"] == "Title"
        assert sections[1]["header"] == "Section 1"
        assert sections[2]["header"] == "Section 2"

    def test_no_headers_returns_single_section(self):
        text = "Just plain text without any headers."
        sections = _split_by_headers(text)
        assert len(sections) == 1
        assert sections[0]["header"] == ""
        assert "plain text" in sections[0]["content"]

    def test_preserves_content(self):
        text = "## Header\nLine 1.\nLine 2.\nLine 3."
        sections = _split_by_headers(text)
        assert "Line 1." in sections[0]["content"]
        assert "Line 3." in sections[0]["content"]

    def test_header_levels(self):
        text = "# H1\nA\n## H2\nB\n### H3\nC"
        sections = _split_by_headers(text)
        assert sections[0]["level"] == 1
        assert sections[1]["level"] == 2
        assert sections[2]["level"] == 3

    def test_empty_text(self):
        assert _split_by_headers("") == []
        assert _split_by_headers("   ") == []


class TestContextualizeChunk:
    def test_adds_section_header(self):
        result = _contextualize_chunk("Some text", "Introduction")
        assert "[Section: Introduction]" in result
        assert "Some text" in result

    def test_adds_doc_context(self):
        result = _contextualize_chunk("Text", "Header", "report.pdf")
        assert "[Document: report.pdf]" in result
        assert "[Section: Header]" in result

    def test_no_context_returns_text_only(self):
        result = _contextualize_chunk("Just text", "")
        assert result == "Just text"

    def test_doc_context_without_header(self):
        result = _contextualize_chunk("Text", "", "file.pdf")
        assert "[Document: file.pdf]" in result
        assert "[Section:" not in result


class TestChunkPages:
    def test_basic_chunking(self):
        pages = [{"page_number": 1, "text": "Hello world. This is a test.", "headers": []}]
        result = chunk_pages(pages, chunk_size=500)
        assert len(result) >= 1
        assert result[0]["page_number"] == 1
        assert result[0]["chunk_index"] == 0

    def test_header_aware_splitting(self):
        pages = [{
            "page_number": 1,
            "text": "# Intro\nSome intro text.\n## Details\nDetailed content here.",
            "headers": ["Intro", "Details"],
        }]
        result = chunk_pages(pages, chunk_size=500)
        assert len(result) == 2
        assert result[0]["section_header"] == "Intro"
        assert result[1]["section_header"] == "Details"

    def test_contextual_enrichment(self):
        pages = [{"page_number": 1, "text": "## Title\nContent", "headers": ["Title"]}]
        result = chunk_pages(pages, chunk_size=500, doc_context="test.pdf")
        assert "[Document: test.pdf]" in result[0]["content"]
        assert "[Section: Title]" in result[0]["content"]

    def test_raw_content_preserved(self):
        pages = [{"page_number": 1, "text": "## Header\nRaw text here", "headers": []}]
        result = chunk_pages(pages, chunk_size=500, doc_context="doc.pdf")
        assert result[0]["raw_content"] == "Raw text here"
        assert "[Document:" in result[0]["content"]

    def test_empty_pages_skipped(self):
        pages = [
            {"page_number": 1, "text": "", "headers": []},
            {"page_number": 2, "text": "Content here", "headers": []},
        ]
        result = chunk_pages(pages, chunk_size=500)
        assert len(result) == 1
        assert result[0]["page_number"] == 2

    def test_multi_page_global_index(self):
        pages = [
            {"page_number": 1, "text": "Page one text.", "headers": []},
            {"page_number": 2, "text": "Page two text.", "headers": []},
        ]
        result = chunk_pages(pages, chunk_size=500)
        assert len(result) == 2
        assert result[0]["chunk_index"] == 0
        assert result[1]["chunk_index"] == 1

    def test_empty_input(self):
        assert chunk_pages([]) == []
