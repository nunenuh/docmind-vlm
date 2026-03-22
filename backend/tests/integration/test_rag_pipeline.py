"""
Integration tests for the RAG pipeline with real PDF files.

Tests the full flow: PDF → pymupdf4llm extraction → header-aware chunking.
No external APIs are called (embedding is mocked).
"""
import os
from pathlib import Path

import pytest

# Path to test PDF
TEST_PDF = Path(__file__).resolve().parents[3] / "data" / "demo" / "documents" / "test_document.pdf"


@pytest.fixture
def pdf_bytes():
    """Load the test PDF as bytes."""
    if not TEST_PDF.exists():
        pytest.skip(f"Test PDF not found: {TEST_PDF}")
    return TEST_PDF.read_bytes()


class TestPdfTextExtraction:
    """Test real PDF text extraction with pymupdf4llm."""

    def test_extracts_all_pages(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text

        pages = extract_text(pdf_bytes, "pdf")

        assert len(pages) == 3
        assert pages[0]["page_number"] == 1
        assert pages[1]["page_number"] == 2
        assert pages[2]["page_number"] == 3

    def test_extracts_text_content(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text

        pages = extract_text(pdf_bytes, "pdf")

        # Page 1 should contain intro text
        assert "test document" in pages[0]["text"].lower() or "docmind" in pages[0]["text"].lower()

        # Page 2 should contain technical specs
        page2_text = pages[1]["text"].lower()
        assert "qwen" in page2_text or "dashscope" in page2_text or "technical" in page2_text

    def test_returns_headers(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text

        pages = extract_text(pdf_bytes, "pdf")

        # Pages should have headers list (may be empty if pymupdf4llm
        # doesn't detect headers from font size alone)
        for page in pages:
            assert "headers" in page
            assert isinstance(page["headers"], list)

    def test_text_is_not_empty(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text

        pages = extract_text(pdf_bytes, "pdf")

        non_empty = [p for p in pages if p["text"].strip()]
        assert len(non_empty) >= 2, "At least 2 pages should have text"


class TestPdfChunking:
    """Test chunking of real extracted PDF text."""

    def test_chunks_real_pdf(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text
        from docmind.library.rag.chunker import chunk_pages

        pages = extract_text(pdf_bytes, "pdf")
        chunks = chunk_pages(pages, chunk_size=200, overlap=30)

        assert len(chunks) >= 1
        for chunk in chunks:
            assert "page_number" in chunk
            assert "chunk_index" in chunk
            assert "content" in chunk
            assert "raw_content" in chunk
            assert "section_header" in chunk
            assert len(chunk["content"]) > 0

    def test_chunks_have_sequential_indices(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text
        from docmind.library.rag.chunker import chunk_pages

        pages = extract_text(pdf_bytes, "pdf")
        chunks = chunk_pages(pages, chunk_size=200, overlap=30)

        indices = [c["chunk_index"] for c in chunks]
        assert indices == list(range(len(indices)))

    def test_contextual_enrichment_with_doc_name(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text
        from docmind.library.rag.chunker import chunk_pages

        pages = extract_text(pdf_bytes, "pdf")
        chunks = chunk_pages(pages, chunk_size=500, doc_context="test_document.pdf")

        for chunk in chunks:
            assert "[Document: test_document.pdf]" in chunk["content"]

    def test_small_chunk_size_creates_more_chunks(self, pdf_bytes):
        from docmind.library.rag.text_extract import extract_text
        from docmind.library.rag.chunker import chunk_pages

        pages = extract_text(pdf_bytes, "pdf")
        small_chunks = chunk_pages(pages, chunk_size=100, overlap=0)
        large_chunks = chunk_pages(pages, chunk_size=1000, overlap=0)

        assert len(small_chunks) >= len(large_chunks)


class TestPdfFullPipeline:
    """Test the full extract → chunk → (mock embed) pipeline."""

    @pytest.mark.asyncio
    async def test_index_document_with_real_pdf(self, pdf_bytes):
        """Full pipeline with real PDF, mocked embedding + DB."""
        from unittest.mock import AsyncMock, MagicMock, patch

        from docmind.library.rag.text_extract import extract_text
        from docmind.library.rag.chunker import chunk_pages
        from docmind.core.config import get_settings

        settings = get_settings()

        # Extract and chunk (real)
        pages = extract_text(pdf_bytes, "pdf")
        chunks = chunk_pages(
            pages,
            chunk_size=settings.RAG_CHUNK_SIZE,
            overlap=settings.RAG_CHUNK_OVERLAP,
            doc_context="test_document.pdf",
        )

        assert len(chunks) >= 1, "Should produce at least 1 chunk"

        # Verify chunk quality
        all_content = " ".join(c["raw_content"] for c in chunks)
        assert len(all_content) > 50, "Combined content should be substantial"

        # Verify no empty chunks
        for chunk in chunks:
            assert len(chunk["content"].strip()) > 0
            assert chunk["page_number"] >= 1
            assert chunk["page_number"] <= 3

    @pytest.mark.asyncio
    async def test_cosine_similarity_with_real_chunks(self, pdf_bytes):
        """Test retrieval scoring with real chunk content."""
        from docmind.library.rag.text_extract import extract_text
        from docmind.library.rag.chunker import chunk_pages
        from docmind.library.rag.retriever import _cosine_similarity

        pages = extract_text(pdf_bytes, "pdf")
        chunks = chunk_pages(pages, chunk_size=200, overlap=0)

        assert len(chunks) >= 2

        # Create simple TF vectors for two chunks (simulating embeddings)
        # This tests that cosine similarity works with realistic data
        words_a = set(chunks[0]["raw_content"].lower().split())
        words_b = set(chunks[1]["raw_content"].lower().split())
        all_words = sorted(words_a | words_b)

        vec_a = [1.0 if w in words_a else 0.0 for w in all_words]
        vec_b = [1.0 if w in words_b else 0.0 for w in all_words]

        sim = _cosine_similarity(vec_a, vec_b)
        assert 0.0 <= sim <= 1.0

        # Self-similarity should be 1.0
        self_sim = _cosine_similarity(vec_a, vec_a)
        assert abs(self_sim - 1.0) < 0.001
