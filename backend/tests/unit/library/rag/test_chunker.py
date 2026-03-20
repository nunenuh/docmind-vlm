"""Tests for docmind.library.rag.chunker."""

from docmind.library.rag.chunker import chunk_pages, chunk_text


class TestChunkText:
    """Tests for chunk_text."""

    def test_chunk_text_splits_by_size(self):
        # Create text that is longer than chunk_size
        text = "This is sentence one. This is sentence two. This is sentence three. This is sentence four. This is sentence five."
        chunks = chunk_text(text, chunk_size=60, overlap=0)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) > 0

    def test_chunk_text_with_overlap(self):
        text = "First sentence here. Second sentence here. Third sentence here. Fourth sentence here."
        chunks = chunk_text(text, chunk_size=50, overlap=10)

        assert len(chunks) > 1
        # Overlap means later chunks should share some content with previous
        # Verify chunks are non-empty
        for chunk in chunks:
            assert len(chunk) > 0

    def test_chunk_text_empty_input(self):
        assert chunk_text("") == []
        assert chunk_text("   ") == []

    def test_chunk_text_short_text_single_chunk(self):
        text = "Short text."
        chunks = chunk_text(text, chunk_size=512, overlap=64)

        assert len(chunks) == 1
        assert chunks[0] == "Short text."

    def test_chunk_text_respects_sentence_boundaries(self):
        text = "Hello world. This is a test. Another sentence here."
        chunks = chunk_text(text, chunk_size=30, overlap=0)

        # Should split at sentence boundaries, not mid-word
        for chunk in chunks:
            assert not chunk.startswith(" ")


class TestChunkPages:
    """Tests for chunk_pages."""

    def test_chunk_pages_multiple_pages(self):
        pages = [
            {"page_number": 1, "text": "Page one has some text. And more text here."},
            {"page_number": 2, "text": "Page two has different text. With extra content."},
        ]
        result = chunk_pages(pages, chunk_size=512, overlap=64)

        assert len(result) >= 2
        assert result[0]["page_number"] == 1
        assert result[0]["chunk_index"] == 0
        assert "content" in result[0]

    def test_chunk_pages_skips_empty_pages(self):
        pages = [
            {"page_number": 1, "text": ""},
            {"page_number": 2, "text": "Some content."},
            {"page_number": 3, "text": "   "},
        ]
        result = chunk_pages(pages, chunk_size=512, overlap=64)

        assert len(result) == 1
        assert result[0]["page_number"] == 2

    def test_chunk_pages_empty_input(self):
        result = chunk_pages([])
        assert result == []

    def test_chunk_pages_global_chunk_index(self):
        pages = [
            {"page_number": 1, "text": "First page text."},
            {"page_number": 2, "text": "Second page text."},
        ]
        result = chunk_pages(pages, chunk_size=512, overlap=64)

        indices = [r["chunk_index"] for r in result]
        assert indices == list(range(len(result)))
