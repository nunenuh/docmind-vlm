"""Tests for docmind.library.rag.indexer."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.library.rag.indexer import (
    delete_document_chunks,
    index_document,
    index_existing_chunks,
)


class TestIndexDocument:
    """Tests for index_document."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.indexer._get_existing_hashes", new_callable=AsyncMock, return_value=set())
    @patch("docmind.library.rag.indexer.AsyncSessionLocal")
    @patch("docmind.library.rag.indexer.embed_texts")
    @patch("docmind.library.rag.indexer.extract_text")
    @patch("docmind.library.rag.indexer.get_settings")
    async def test_index_document_full_pipeline(
        self,
        mock_get_settings,
        mock_extract_text,
        mock_embed_texts,
        mock_session_cls,
        mock_get_hashes,
    ):
        settings = MagicMock()
        settings.RAG_CHUNK_SIZE = 512
        settings.RAG_CHUNK_OVERLAP = 64
        settings.RAG_MAX_EMBEDDING_TOKENS = 7500
        settings.EMBEDDING_PROVIDER = "openrouter"
        settings.EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
        settings.EMBEDDING_DIMENSIONS = 1024
        mock_get_settings.return_value = settings

        mock_extract_text.return_value = [
            {"page_number": 1, "text": "Hello world. This is a test document."},
        ]

        mock_embed_texts.return_value = [[0.1, 0.2, 0.3]]

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        result = await index_document(
            document_id="doc-1",
            project_id="proj-1",
            file_bytes=b"fake pdf",
            file_type="pdf",
        )

        assert result == 1
        mock_extract_text.assert_called_once_with(b"fake pdf", "pdf")
        mock_embed_texts.assert_called_once()
        # Should add PageChunk + ChunkEmbedding (2 adds per chunk)
        assert mock_session.add.call_count == 2
        mock_session.flush.assert_called_once()
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("docmind.library.rag.indexer.extract_text")
    @patch("docmind.library.rag.indexer.get_settings")
    async def test_index_document_empty_text(
        self, mock_get_settings, mock_extract_text
    ):
        settings = MagicMock()
        settings.RAG_CHUNK_SIZE = 512
        settings.RAG_CHUNK_OVERLAP = 64
        settings.EMBEDDING_PROVIDER = "openrouter"
        settings.EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
        settings.EMBEDDING_DIMENSIONS = 1024
        mock_get_settings.return_value = settings

        mock_extract_text.return_value = [
            {"page_number": 1, "text": ""},
        ]

        result = await index_document(
            document_id="doc-1",
            project_id="proj-1",
            file_bytes=b"empty pdf",
            file_type="pdf",
        )

        assert result == 0


class TestIndexExistingChunks:
    """Tests for index_existing_chunks."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.indexer.AsyncSessionLocal")
    @patch("docmind.library.rag.indexer.embed_texts")
    @patch("docmind.library.rag.indexer.get_settings")
    async def test_skips_already_embedded_chunks(
        self, mock_get_settings, mock_embed_texts, mock_session_cls
    ):
        settings = MagicMock()
        settings.EMBEDDING_PROVIDER = "openrouter"
        settings.EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
        settings.EMBEDDING_DIMENSIONS = 1024
        mock_get_settings.return_value = settings

        # First call: get all chunks
        chunk = MagicMock()
        chunk.id = "chunk-1"
        chunk.content = "Some text"
        mock_result_chunks = MagicMock()
        mock_result_chunks.scalars.return_value.all.return_value = [chunk]

        # Second call: get existing embeddings — chunk-1 already has embedding
        mock_result_existing = MagicMock()
        mock_result_existing.all.return_value = [("chunk-1",)]

        mock_session = AsyncMock()
        mock_session.execute.side_effect = [mock_result_chunks, mock_result_existing]
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        result = await index_existing_chunks(document_id="doc-1")

        assert result == 0
        mock_embed_texts.assert_not_called()

    @pytest.mark.asyncio
    @patch("docmind.library.rag.indexer.AsyncSessionLocal")
    @patch("docmind.library.rag.indexer.get_settings")
    async def test_returns_zero_when_no_chunks(
        self, mock_get_settings, mock_session_cls
    ):
        settings = MagicMock()
        settings.EMBEDDING_PROVIDER = "openrouter"
        settings.EMBEDDING_MODEL = "qwen/qwen3-embedding-8b"
        settings.EMBEDDING_DIMENSIONS = 1024
        mock_get_settings.return_value = settings

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        result = await index_existing_chunks(document_id="doc-1")

        assert result == 0


class TestDeleteDocumentChunks:
    """Tests for delete_document_chunks."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.indexer.AsyncSessionLocal")
    async def test_delete_document_chunks(self, mock_session_cls):
        mock_result = MagicMock()
        mock_result.rowcount = 5

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        result = await delete_document_chunks("doc-1")

        assert result == 5
        mock_session.execute.assert_called_once()
        mock_session.commit.assert_called_once()
