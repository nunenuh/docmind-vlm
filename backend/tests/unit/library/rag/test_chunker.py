"""Tests for page-level contextual chunking (RAG v2)."""
from docmind.library.rag.chunker import (
    chunk_text,
    chunk_pages,
    detect_document_profile,
    _split_by_headers,
    _build_contextual_header,
    _content_hash,
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


class TestBuildContextualHeader:
    def test_includes_document_and_page(self):
        result = _build_contextual_header("report.pdf", 3, 10, "")
        assert "[Document: report.pdf]" in result
        assert "[Page: 3/10]" in result

    def test_includes_section_when_present(self):
        result = _build_contextual_header("doc.pdf", 1, 5, "Introduction")
        assert "[Section: Introduction]" in result

    def test_no_section_when_empty(self):
        result = _build_contextual_header("doc.pdf", 1, 5, "")
        assert "[Section:" not in result


class TestContentHash:
    def test_consistent_hashing(self):
        h1 = _content_hash("Hello World")
        h2 = _content_hash("Hello World")
        assert h1 == h2

    def test_normalized_whitespace(self):
        h1 = _content_hash("Hello  World")
        h2 = _content_hash("Hello World")
        assert h1 == h2

    def test_case_insensitive(self):
        h1 = _content_hash("Hello World")
        h2 = _content_hash("hello world")
        assert h1 == h2

    def test_different_content_different_hash(self):
        h1 = _content_hash("Hello")
        h2 = _content_hash("World")
        assert h1 != h2


class TestDetectDocumentProfile:
    def test_resume_by_filename(self):
        assert detect_document_profile([], "John_Resume_2024.pdf") == "resume"
        assert detect_document_profile([], "CV_Smith.pdf") == "resume"

    def test_contract_by_filename(self):
        assert detect_document_profile([], "NDA_Agreement.pdf") == "contract"

    def test_report_by_filename(self):
        assert detect_document_profile([], "Q3_Analysis_Report.pdf") == "report"

    def test_resume_by_content(self):
        pages = [{"text": "Experience\nEducation\nSkills\nObjective", "headers": []}]
        assert detect_document_profile(pages, "unknown.pdf") == "resume"

    def test_contract_by_content(self):
        pages = [{"text": "WHEREAS the parties hereby agree to the following clause", "headers": []}]
        assert detect_document_profile(pages, "document.pdf") == "contract"

    def test_default_for_unknown(self):
        assert detect_document_profile([], "random_file.pdf") == "default"


class TestChunkPages:
    def test_short_page_kept_whole(self):
        """Pages under threshold stay as one chunk."""
        pages = [{"page_number": 1, "text": "Hello world. This is a test.", "headers": []}]
        result = chunk_pages(pages, page_chunk_threshold=5000, doc_context="test.pdf")
        assert len(result) == 1
        assert result[0]["page_number"] == 1
        assert "[Document: test.pdf]" in result[0]["content"]
        assert "[Page: 1/1]" in result[0]["content"]

    def test_long_page_split_by_headers(self):
        """Pages over threshold are split by headers then sentences."""
        long_text = "# Section A\n" + "Word " * 500 + "\n# Section B\n" + "Word " * 500
        pages = [{"page_number": 1, "text": long_text, "headers": ["Section A", "Section B"]}]
        result = chunk_pages(pages, page_chunk_threshold=100, doc_context="big.pdf")
        assert len(result) >= 2

    def test_contextual_header_in_content(self):
        pages = [{"page_number": 2, "text": "## Title\nContent here", "headers": ["Title"]}]
        result = chunk_pages(pages, page_chunk_threshold=5000, doc_context="test.pdf")
        assert "[Document: test.pdf]" in result[0]["content"]
        assert "[Page: 2/1]" in result[0]["content"]

    def test_raw_content_without_header(self):
        pages = [{"page_number": 1, "text": "Raw text here.", "headers": []}]
        result = chunk_pages(pages, page_chunk_threshold=5000, doc_context="doc.pdf")
        assert result[0]["raw_content"] == "Raw text here."
        assert "[Document:" not in result[0]["raw_content"]

    def test_content_hash_present(self):
        pages = [{"page_number": 1, "text": "Some content.", "headers": []}]
        result = chunk_pages(pages, page_chunk_threshold=5000)
        assert "content_hash" in result[0]
        assert len(result[0]["content_hash"]) == 64

    def test_empty_pages_skipped(self):
        pages = [
            {"page_number": 1, "text": "", "headers": []},
            {"page_number": 2, "text": "Content", "headers": []},
        ]
        result = chunk_pages(pages, page_chunk_threshold=5000)
        assert len(result) == 1
        assert result[0]["page_number"] == 2

    def test_multi_page_global_index(self):
        pages = [
            {"page_number": 1, "text": "Page one.", "headers": []},
            {"page_number": 2, "text": "Page two.", "headers": []},
        ]
        result = chunk_pages(pages, page_chunk_threshold=5000)
        assert result[0]["chunk_index"] == 0
        assert result[1]["chunk_index"] == 1

    def test_empty_input(self):
        assert chunk_pages([]) == []

    def test_duplicate_content_same_hash(self):
        pages = [
            {"page_number": 1, "text": "Same content here.", "headers": []},
            {"page_number": 2, "text": "Same content here.", "headers": []},
        ]
        result = chunk_pages(pages, page_chunk_threshold=5000)
        assert result[0]["content_hash"] == result[1]["content_hash"]
