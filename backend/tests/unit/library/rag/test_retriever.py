"""Tests for docmind.library.rag.retriever."""

import json
import math
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.library.rag.retriever import _cosine_similarity, retrieve_similar_chunks


class TestCosineSimilarity:
    """Tests for _cosine_similarity."""

    def test_cosine_similarity_identical_vectors(self):
        vec = [1.0, 2.0, 3.0]
        sim = _cosine_similarity(vec, vec)
        assert abs(sim - 1.0) < 1e-9

    def test_cosine_similarity_orthogonal_vectors(self):
        a = [1.0, 0.0]
        b = [0.0, 1.0]
        sim = _cosine_similarity(a, b)
        assert abs(sim) < 1e-9

    def test_cosine_similarity_opposite_vectors(self):
        a = [1.0, 0.0]
        b = [-1.0, 0.0]
        sim = _cosine_similarity(a, b)
        assert abs(sim - (-1.0)) < 1e-9

    def test_cosine_similarity_zero_vector(self):
        a = [0.0, 0.0]
        b = [1.0, 2.0]
        assert _cosine_similarity(a, b) == 0.0
        assert _cosine_similarity(b, a) == 0.0


class TestRetrieveSimilarChunks:
    """Tests for retrieve_similar_chunks."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retrieve_filters_by_threshold(self, mock_session_cls):
        # Create mock chunks: one similar, one not
        chunk_high = MagicMock()
        chunk_high.id = "chunk-1"
        chunk_high.document_id = "doc-1"
        chunk_high.page_number = 1
        chunk_high.content = "Relevant content"
        chunk_high.embedding = json.dumps([1.0, 0.0, 0.0])

        chunk_low = MagicMock()
        chunk_low.id = "chunk-2"
        chunk_low.document_id = "doc-1"
        chunk_low.page_number = 2
        chunk_low.content = "Irrelevant content"
        chunk_low.embedding = json.dumps([0.0, 1.0, 0.0])

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [chunk_high, chunk_low]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        query_embedding = [1.0, 0.0, 0.0]  # Similar to chunk_high only
        results = await retrieve_similar_chunks(
            query_embedding, project_id="proj-1", top_k=5, threshold=0.7
        )

        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-1"
        assert results[0]["similarity"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retrieve_returns_top_k(self, mock_session_cls):
        # Create 3 chunks with varying similarity
        chunks = []
        embeddings = [
            [1.0, 0.0, 0.0],
            [0.9, 0.1, 0.0],
            [0.8, 0.2, 0.0],
        ]
        for i, emb in enumerate(embeddings):
            chunk = MagicMock()
            chunk.id = f"chunk-{i}"
            chunk.document_id = "doc-1"
            chunk.page_number = i + 1
            chunk.content = f"Content {i}"
            chunk.embedding = json.dumps(emb)
            chunks.append(chunk)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = chunks

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        query_embedding = [1.0, 0.0, 0.0]
        results = await retrieve_similar_chunks(
            query_embedding, project_id="proj-1", top_k=2, threshold=0.0
        )

        assert len(results) == 2
        # Should be sorted by similarity descending
        assert results[0]["similarity"] >= results[1]["similarity"]

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retrieve_empty_project(self, mock_session_cls):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        results = await retrieve_similar_chunks(
            [1.0, 0.0], project_id="proj-empty", top_k=5, threshold=0.7
        )

        assert results == []
