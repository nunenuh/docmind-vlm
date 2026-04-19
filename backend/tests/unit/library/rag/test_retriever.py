"""Tests for docmind.library.rag.retriever."""

import json
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
    """Tests for retrieve_similar_chunks with model_name parameter."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retrieve_filters_by_threshold(self, mock_session_cls):
        # Create mock rows: (PageChunk, embedding_str)
        chunk_high = MagicMock()
        chunk_high.id = "chunk-1"
        chunk_high.document_id = "doc-1"
        chunk_high.page_number = 1
        chunk_high.content = "Relevant content"
        chunk_high.raw_content = "Relevant content"

        chunk_low = MagicMock()
        chunk_low.id = "chunk-2"
        chunk_low.document_id = "doc-1"
        chunk_low.page_number = 2
        chunk_low.content = "Irrelevant content"
        chunk_low.raw_content = "Irrelevant content"

        mock_result = MagicMock()
        mock_result.all.return_value = [
            (chunk_high, json.dumps([1.0, 0.0, 0.0])),
            (chunk_low, json.dumps([0.0, 1.0, 0.0])),
        ]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        query_embedding = [1.0, 0.0, 0.0]  # Similar to chunk_high only
        results = await retrieve_similar_chunks(
            query_embedding,
            project_id="proj-1",
            model_name="test-model",
            top_k=5,
            threshold=0.7,
        )

        assert len(results) == 1
        assert results[0]["chunk_id"] == "chunk-1"
        assert results[0]["similarity"] == pytest.approx(1.0)

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retrieve_returns_top_k(self, mock_session_cls):
        # Create 3 rows with varying similarity
        rows = []
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
            chunk.raw_content = f"Content {i}"
            rows.append((chunk, json.dumps(emb)))

        mock_result = MagicMock()
        mock_result.all.return_value = rows

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        query_embedding = [1.0, 0.0, 0.0]
        results = await retrieve_similar_chunks(
            query_embedding,
            project_id="proj-1",
            model_name="test-model",
            top_k=2,
            threshold=0.0,
        )

        assert len(results) == 2
        # Should be sorted by similarity descending
        assert results[0]["similarity"] >= results[1]["similarity"]

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retrieve_empty_project(self, mock_session_cls):
        mock_result = MagicMock()
        mock_result.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        results = await retrieve_similar_chunks(
            [1.0, 0.0],
            project_id="proj-empty",
            model_name="test-model",
            top_k=5,
            threshold=0.7,
        )

        assert results == []


class TestRetrieveJoinsDocument:
    """Verify retriever JOINs Document table so orphaned chunks are excluded.

    Issue #104: Deleted documents can leave orphaned PageChunk rows. Retrieval
    MUST JOIN Document to filter them out as defense-in-depth.
    """

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_vector_retrieval_joins_documents(self, mock_session_cls):
        """Vector-only retrieval must include Document in its JOIN chain."""
        from docmind.library.rag.retriever import _retrieve_vector_only

        executed_stmts: list[object] = []

        async def capture_execute(stmt):
            executed_stmts.append(stmt)
            result = MagicMock()
            result.all.return_value = []
            return result

        mock_session = AsyncMock()
        mock_session.execute = capture_execute
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        await _retrieve_vector_only(
            query_embedding=[1.0, 0.0],
            project_id="proj-x",
            model_name="test-model",
            top_k=5,
            threshold=0.7,
        )

        assert executed_stmts, "No SQL statement was executed"
        compiled = str(executed_stmts[0].compile())
        assert "documents" in compiled.lower(), (
            f"Expected JOIN with documents table. Got:\n{compiled}"
        )

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_hybrid_retrieval_joins_documents(self, mock_session_cls):
        """Hybrid retrieval must also include Document in its JOIN chain."""
        from docmind.library.rag.retriever import _retrieve_hybrid

        executed_stmts: list[object] = []

        async def capture_execute(stmt):
            executed_stmts.append(stmt)
            result = MagicMock()
            result.all.return_value = []
            return result

        mock_session = AsyncMock()
        mock_session.execute = capture_execute
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        await _retrieve_hybrid(
            query_embedding=[1.0, 0.0],
            project_id="proj-x",
            model_name="test-model",
            query_text="some query",
            top_k=5,
            threshold=0.7,
        )

        assert executed_stmts, "No SQL statement was executed"
        compiled = str(executed_stmts[0].compile())
        assert "documents" in compiled.lower(), (
            f"Expected JOIN with documents table. Got:\n{compiled}"
        )
