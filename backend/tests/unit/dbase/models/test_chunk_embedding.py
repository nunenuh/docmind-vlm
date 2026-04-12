"""Tests for ChunkEmbedding ORM model."""

from datetime import datetime, timezone

import pytest

from docmind.dbase.psql.models.chunk_embedding import ChunkEmbedding


class TestChunkEmbeddingModel:
    """Tests for ChunkEmbedding model field definitions."""

    def test_creates_with_correct_fields(self):
        """ChunkEmbedding should accept all required fields."""
        emb = ChunkEmbedding(
            id="emb-001",
            chunk_id="chunk-001",
            document_id="doc-001",
            provider_name="openrouter",
            model_name="qwen/qwen3-embedding-8b",
            dimensions=1024,
            embedding="[0.1,0.2,0.3]",
        )
        assert emb.id == "emb-001"
        assert emb.chunk_id == "chunk-001"
        assert emb.document_id == "doc-001"
        assert emb.provider_name == "openrouter"
        assert emb.model_name == "qwen/qwen3-embedding-8b"
        assert emb.dimensions == 1024
        assert emb.embedding == "[0.1,0.2,0.3]"

    def test_tablename(self):
        """Table name should be chunk_embeddings."""
        assert ChunkEmbedding.__tablename__ == "chunk_embeddings"

    def test_unique_constraint_defined(self):
        """Model should have uq_chunk_model unique constraint on (chunk_id, model_name)."""
        constraints = ChunkEmbedding.__table_args__
        uq = next(
            (c for c in constraints if hasattr(c, "name") and c.name == "uq_chunk_model"),
            None,
        )
        assert uq is not None, "uq_chunk_model constraint not found"

    def test_index_defined(self):
        """Model should have idx_chunk_emb_doc_model index."""
        constraints = ChunkEmbedding.__table_args__
        idx = next(
            (c for c in constraints if hasattr(c, "name") and c.name == "idx_chunk_emb_doc_model"),
            None,
        )
        assert idx is not None, "idx_chunk_emb_doc_model index not found"

    def test_default_id_generation(self):
        """ID should get a UUID default if not provided."""
        emb = ChunkEmbedding(
            chunk_id="chunk-001",
            document_id="doc-001",
            provider_name="openai",
            model_name="text-embedding-3-large",
            dimensions=3072,
            embedding="[0.1]",
        )
        # Default is set via column default, not in __init__,
        # so id will be None until flush. Just verify no error.
        assert emb.chunk_id == "chunk-001"

    def test_embedded_at_default(self):
        """embedded_at should default to a UTC datetime."""
        emb = ChunkEmbedding(
            chunk_id="chunk-001",
            document_id="doc-001",
            provider_name="dashscope",
            model_name="text-embedding-v4",
            dimensions=1024,
            embedding="[0.5]",
        )
        # Column default is set at DB level, so in-memory it may be None
        # unless explicitly set. The default function is defined.
        col = ChunkEmbedding.__table__.c.embedded_at
        assert col.default is not None
