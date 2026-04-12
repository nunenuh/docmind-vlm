"""Tests for multi-model retriever — model_name filtering in retrieve_similar_chunks."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.library.rag.retriever import retrieve_similar_chunks


class TestRetrieverModelFiltering:
    """Tests for model_name filtering in retriever."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retriever_filters_by_model_name(self, mock_session_cls):
        """Only chunks with matching model_name should be returned."""
        # Create mock row: (PageChunk, embedding_str)
        chunk = MagicMock()
        chunk.id = "chunk-1"
        chunk.document_id = "doc-1"
        chunk.page_number = 1
        chunk.content = "Relevant content"
        chunk.raw_content = "Relevant content"

        embedding = json.dumps([1.0, 0.0, 0.0])

        mock_result = MagicMock()
        mock_result.all.return_value = [(chunk, embedding)]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        query_embedding = [1.0, 0.0, 0.0]
        results = await retrieve_similar_chunks(
            query_embedding,
            project_id="proj-1",
            model_name="qwen/qwen3-embedding-8b",
            top_k=5,
            threshold=0.5,
        )

        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-1"
        assert results[0]["similarity"] == pytest.approx(1.0)

        # Verify the query was executed (model_name filtering happens in SQL)
        mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retriever_returns_empty_when_no_embeddings_for_model(
        self, mock_session_cls
    ):
        """Should return empty list when no embeddings exist for the model."""
        mock_result = MagicMock()
        mock_result.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        results = await retrieve_similar_chunks(
            [1.0, 0.0],
            project_id="proj-1",
            model_name="nonexistent-model",
            top_k=5,
            threshold=0.0,
        )

        assert results == []

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retriever_respects_threshold(self, mock_session_cls):
        """Chunks below threshold should be excluded."""
        chunk_high = MagicMock()
        chunk_high.id = "chunk-1"
        chunk_high.document_id = "doc-1"
        chunk_high.page_number = 1
        chunk_high.content = "High sim"
        chunk_high.raw_content = "High sim"
        emb_high = json.dumps([1.0, 0.0, 0.0])

        chunk_low = MagicMock()
        chunk_low.id = "chunk-2"
        chunk_low.document_id = "doc-1"
        chunk_low.page_number = 2
        chunk_low.content = "Low sim"
        chunk_low.raw_content = "Low sim"
        emb_low = json.dumps([0.0, 1.0, 0.0])  # orthogonal = 0 similarity

        mock_result = MagicMock()
        mock_result.all.return_value = [(chunk_high, emb_high), (chunk_low, emb_low)]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        results = await retrieve_similar_chunks(
            [1.0, 0.0, 0.0],
            project_id="proj-1",
            model_name="test-model",
            top_k=10,
            threshold=0.5,
        )

        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-1"

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retriever_sorts_by_similarity(self, mock_session_cls):
        """Results should be sorted by similarity descending."""
        chunks_data = [
            ("chunk-1", [0.8, 0.2, 0.0]),
            ("chunk-2", [1.0, 0.0, 0.0]),
            ("chunk-3", [0.6, 0.4, 0.0]),
        ]

        rows = []
        for cid, emb in chunks_data:
            chunk = MagicMock()
            chunk.id = cid
            chunk.document_id = "doc-1"
            chunk.page_number = 1
            chunk.content = f"Content {cid}"
            chunk.raw_content = f"Content {cid}"
            rows.append((chunk, json.dumps(emb)))

        mock_result = MagicMock()
        mock_result.all.return_value = rows

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        results = await retrieve_similar_chunks(
            [1.0, 0.0, 0.0],
            project_id="proj-1",
            model_name="test-model",
            top_k=10,
            threshold=0.0,
        )

        assert len(results) == 3
        # chunk-2 has [1,0,0] = perfect match, should be first
        assert results[0]["chunk_id"] == "chunk-2"
        # Verify descending order
        for i in range(len(results) - 1):
            assert results[i]["similarity"] >= results[i + 1]["similarity"]
