"""Tests for retrieval diversity (issue #105).

Scenario that motivated this work: a project with 2 documents where one
document's chunks dominate vector similarity. Without per-document quota
enforcement, aggregate questions ("where does this come from?") return an
answer from only one document.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from docmind.library.rag.retriever import _diversify_results


def _chunk(
    chunk_id: str,
    document_id: str,
    page: int = 1,
    similarity: float = 0.9,
    content: str = "text",
) -> dict:
    return {
        "chunk_id": chunk_id,
        "document_id": document_id,
        "page_number": page,
        "content": content,
        "raw_content": content,
        "similarity": similarity,
    }


class TestDiversifyResults:
    """Direct tests on _diversify_results for per-document fairness."""

    def test_single_document_keeps_order(self):
        results = [_chunk(f"c{i}", "doc-A", similarity=1.0 - i * 0.1) for i in range(5)]
        out = _diversify_results(results, top_k=3)
        assert [c["chunk_id"] for c in out] == ["c0", "c1", "c2"]

    def test_round_robin_across_two_docs_at_top_k_equal_to_one_per_doc(self):
        """At top_k=2 with two docs, each must appear exactly once."""
        results = [
            _chunk("a1", "doc-A", similarity=0.95),
            _chunk("a2", "doc-A", similarity=0.90),
            _chunk("a3", "doc-A", similarity=0.80),
            _chunk("b1", "doc-B", similarity=0.70),
        ]
        out = _diversify_results(results, top_k=2)
        doc_ids = {c["document_id"] for c in out}
        assert doc_ids == {"doc-A", "doc-B"}, (
            f"Expected both docs represented, got {doc_ids}"
        )

    def test_top_k_5_with_two_docs_at_least_one_per_doc(self):
        """Mas AAN's scenario: top_k=5, doc-A dominates — doc-B must still appear."""
        results = (
            [_chunk(f"a{i}", "doc-A", similarity=0.95 - i * 0.01) for i in range(10)]
            + [_chunk("b1", "doc-B", similarity=0.5)]
        )
        out = _diversify_results(results, top_k=5)
        doc_ids = {c["document_id"] for c in out}
        assert "doc-B" in doc_ids, (
            f"Doc B must appear in top-5 even when Doc A has many strong matches; "
            f"got {doc_ids}"
        )

    def test_fewer_results_than_top_k_returns_all(self):
        results = [
            _chunk("a1", "doc-A", similarity=0.9),
            _chunk("b1", "doc-B", similarity=0.8),
        ]
        out = _diversify_results(results, top_k=10)
        assert len(out) == 2

    def test_strongest_document_wins_round_zero_slot(self):
        """The globally best chunk must appear first regardless of its document."""
        results = [
            _chunk("b0", "doc-B", similarity=0.99),  # Globally best
            _chunk("a0", "doc-A", similarity=0.95),
            _chunk("a1", "doc-A", similarity=0.90),
            _chunk("b1", "doc-B", similarity=0.80),
        ]
        out = _diversify_results(results, top_k=2)
        assert out[0]["chunk_id"] == "b0", (
            "Position 0 must be the globally highest-similarity chunk"
        )

    def test_three_docs_round_robin(self):
        results = (
            [_chunk(f"a{i}", "doc-A", similarity=0.9 - i * 0.01) for i in range(3)]
            + [_chunk(f"b{i}", "doc-B", similarity=0.7 - i * 0.01) for i in range(3)]
            + [_chunk(f"c{i}", "doc-C", similarity=0.5 - i * 0.01) for i in range(3)]
        )
        out = _diversify_results(results, top_k=6)
        # First 3 should be one from each doc (round 0), then one from each (round 1)
        first_three_docs = {c["document_id"] for c in out[:3]}
        assert first_three_docs == {"doc-A", "doc-B", "doc-C"}


class TestVectorOnlyDiversifies:
    """Vector-only retrieval must also diversify (issue #105).

    Previously, _retrieve_vector_only returned top-K by similarity only,
    so one document could monopolise the results.
    """

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_vector_only_returns_both_documents(self, mock_session_cls):
        from docmind.library.rag.retriever import _retrieve_vector_only

        # doc-A has 4 high-similarity chunks, doc-B has 1 lower chunk
        chunks: list[tuple[MagicMock, str]] = []
        for i in range(4):
            c = MagicMock()
            c.id = f"a{i}"
            c.document_id = "doc-A"
            c.page_number = i + 1
            c.content = f"Ngaglik content {i}"
            c.raw_content = f"Ngaglik content {i}"
            chunks.append((c, json.dumps([1.0 - i * 0.01, 0.0])))
        b = MagicMock()
        b.id = "b1"
        b.document_id = "doc-B"
        b.page_number = 1
        b.content = "Other Polsek content"
        b.raw_content = "Other Polsek content"
        chunks.append((b, json.dumps([0.8, 0.2])))

        mock_result = MagicMock()
        mock_result.all.return_value = chunks

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        out = await _retrieve_vector_only(
            query_embedding=[1.0, 0.0],
            project_id="proj-1",
            model_name="m",
            top_k=3,
            threshold=0.5,
        )

        doc_ids = {c["document_id"] for c in out}
        assert "doc-B" in doc_ids, (
            f"doc-B must appear even when doc-A has many strong matches; got {doc_ids}"
        )


class TestRetrieveSimilarChunksReturnsDiagnostics:
    """Top-level API should expose max_similarity so refusal logic can act on it."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_retrieve_returns_dict_with_chunks_and_max_similarity(
        self, mock_session_cls,
    ):
        """retrieve_similar_chunks should expose aggregate diagnostics."""
        from docmind.library.rag.retriever import retrieve_similar_chunks_with_stats

        chunk = MagicMock()
        chunk.id = "c1"
        chunk.document_id = "doc-A"
        chunk.page_number = 1
        chunk.content = "hi"
        chunk.raw_content = "hi"

        mock_result = MagicMock()
        mock_result.all.return_value = [(chunk, json.dumps([1.0, 0.0]))]

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        stats = await retrieve_similar_chunks_with_stats(
            query_embedding=[1.0, 0.0],
            project_id="proj-1",
            model_name="m",
            top_k=5,
            threshold=0.0,
        )

        assert "chunks" in stats
        assert "max_similarity" in stats
        assert "per_document_counts" in stats
        assert stats["max_similarity"] == pytest.approx(1.0, abs=0.01)
        assert stats["per_document_counts"] == {"doc-A": 1}

    @pytest.mark.asyncio
    @patch("docmind.library.rag.retriever.AsyncSessionLocal")
    async def test_empty_retrieval_returns_zero_max_similarity(
        self, mock_session_cls,
    ):
        from docmind.library.rag.retriever import retrieve_similar_chunks_with_stats

        mock_result = MagicMock()
        mock_result.all.return_value = []

        mock_session = AsyncMock()
        mock_session.execute.return_value = mock_result
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)
        mock_session_cls.return_value = mock_session

        stats = await retrieve_similar_chunks_with_stats(
            query_embedding=[1.0, 0.0],
            project_id="proj-empty",
            model_name="m",
            top_k=5,
            threshold=0.0,
        )

        assert stats["chunks"] == []
        assert stats["max_similarity"] == 0.0
        assert stats["per_document_counts"] == {}
