# Backend Spec: Multi-Model Embedding Storage

Files: `backend/src/docmind/dbase/psql/models/page_chunk.py`, `backend/src/docmind/dbase/psql/models/chunk_embedding.py`

See also: [[projects/docmind-vlm/specs/backend/rag]] · [[projects/docmind-vlm/specs/backend/user-providers]] · [[projects/docmind-vlm/specs/backend/services]]

---

## Problem

When a user changes their embedding provider/model, existing vectors become incompatible:
- Different models produce different vector dimensions (OpenAI: 3072d, Qwen: 1024d, bge-m3: 1024d)
- Even same-dimension vectors from different models live in different vector spaces — cosine similarity is meaningless across models
- Re-embedding is expensive (API costs per token)
- Users experiment with models and want to switch back without paying again

## Solution: Separate Chunks from Embeddings

Split the current `page_chunks` table into two:

```
page_chunks (text content — one row per chunk, immutable)
  └── chunk_embeddings (vectors — one row per model used)
```

A chunk's text never changes. Only the vector representation changes per model. This allows:
- Multiple embedding models per chunk (keep old vectors)
- Instant model switching (no re-embedding if vectors exist)
- Per-document/project indexing status
- Cost savings (only embed once per model)

---

## Data Model

### ERD

```
users
  │
  ├── user_provider_configs        (1:N — one per provider_type)
  │     provider_type, provider_name, model_name
  │
  ├── documents                    (1:N)
  │     │
  │     └── page_chunks            (1:N — text content only)
  │           │
  │           └── chunk_embeddings  (1:N — one per embedding model)
  │                 embedding (vector)
  │                 provider_name
  │                 model_name
  │                 dimensions
  │                 embedded_at
  │
  └── projects                     (1:N)
        │
        └── project_documents      (M:N join → documents)
```

### `page_chunks` (text content — unchanged except removing embedding column)

```python
class PageChunk(Base):
    __tablename__ = "page_chunks"

    id: Mapped[str]              # UUID PK
    document_id: Mapped[str]     # FK → documents.id
    project_id: Mapped[str]      # FK → projects.id (nullable for standalone docs)
    page_number: Mapped[int]
    chunk_index: Mapped[int]
    content: Mapped[str]         # Chunked text (with contextual header)
    raw_content: Mapped[str]     # Original text without header (for BM25)
    content_hash: Mapped[str]    # SHA-256 for dedup
    metadata_json: Mapped[str]   # Extra metadata (JSON)
    created_at: Mapped[datetime]
```

**Change from current:** Remove the `embedding` column. Vectors move to `chunk_embeddings`.

### `chunk_embeddings` (vectors — new table)

```python
class ChunkEmbedding(Base):
    __tablename__ = "chunk_embeddings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    chunk_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("page_chunks.id", ondelete="CASCADE"), nullable=False
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id"), nullable=False, index=True
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    dimensions: Mapped[int] = mapped_column(Integer, nullable=False)
    # The actual vector — stored as pgvector type
    # DB column: embedding vector(N) where N matches dimensions
    # In SQLAlchemy: stored as Text, cast to vector in queries
    embedding: Mapped[str] = mapped_column(Text, nullable=False)
    embedded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=_now
    )

    __table_args__ = (
        # One embedding per chunk per model
        UniqueConstraint("chunk_id", "model_name", name="uq_chunk_model"),
        # Fast lookup: all embeddings for a document with a specific model
        Index("idx_chunk_emb_doc_model", "document_id", "model_name"),
    )
```

### Relationships

```python
# In PageChunk:
embeddings: Mapped[list["ChunkEmbedding"]] = relationship(
    "ChunkEmbedding", back_populates="chunk", cascade="all, delete-orphan"
)

# In ChunkEmbedding:
chunk: Mapped["PageChunk"] = relationship("PageChunk", back_populates="embeddings")
```

---

## Query Patterns

### RAG Retrieval (find relevant chunks)

```sql
-- Get chunks matching user's current embedding model
SELECT c.id, c.content, c.page_number, c.document_id, e.embedding
FROM page_chunks c
JOIN chunk_embeddings e ON e.chunk_id = c.id
WHERE c.document_id IN (:project_doc_ids)
  AND e.model_name = :current_model
ORDER BY e.embedding <=> :query_vector
LIMIT :top_k;
```

### Document Embedding Status

```sql
-- For a document, which models have embeddings?
SELECT
    e.model_name,
    e.provider_name,
    COUNT(*) as embedded_chunks,
    (SELECT COUNT(*) FROM page_chunks WHERE document_id = :doc_id) as total_chunks,
    MAX(e.embedded_at) as last_embedded
FROM chunk_embeddings e
JOIN page_chunks c ON c.id = e.chunk_id
WHERE e.document_id = :doc_id
GROUP BY e.model_name, e.provider_name;
```

### Check if Document Needs Indexing

```sql
-- Does this document have embeddings for the user's current model?
SELECT EXISTS(
    SELECT 1 FROM chunk_embeddings
    WHERE document_id = :doc_id AND model_name = :current_model
) as is_indexed;
```

---

## Indexing Flow

### First-time Indexing

```
Upload document
  → Text extraction (PyMuPDF / VLM OCR)
  → Chunking (sentence-boundary, overlap)
  → page_chunks rows created (text only, no vectors)
  → Get user's embedding config (or system default)
  → Embed all chunks with that model
  → chunk_embeddings rows created (vectors)
```

### Add Index for New Model

```
User switches embedding model in Settings
  → Documents show "Needs indexing" status
  → User clicks "Index" on a document (or "Index All" on project)
  → page_chunks already exist (text unchanged)
  → Embed chunks with NEW model
  → INSERT into chunk_embeddings (old vectors preserved)
  → Document now has vectors for both models
```

### Switch Back to Old Model

```
User switches embedding model back to previous one
  → Check: do chunk_embeddings exist for this model?
  → YES → instant switch, no API calls needed
  → NO  → "Needs indexing" status, user can index
```

---

## Embedding Status

Each document has an embedding status relative to the user's current model:

| Status | Meaning | UI |
|--------|---------|-----|
| `indexed` | All chunks have vectors for current model | ✅ Green check |
| `partial` | Some chunks have vectors, some don't | ⚠️ Yellow, shows progress |
| `not_indexed` | No chunks have vectors for current model | ⚪ Gray, "Index" button |
| `no_chunks` | Document not yet chunked (just uploaded) | 📄 "Process first" |

### Status API

```
GET /api/v1/documents/{id}/embedding-status
Response: {
  "current_model": "qwen/qwen3-embedding-8b",
  "status": "indexed",
  "indexed_chunks": 42,
  "total_chunks": 42,
  "available_models": [
    {"model": "qwen/qwen3-embedding-8b", "chunks": 42, "last_embedded": "..."},
    {"model": "openai/text-embedding-3-large", "chunks": 42, "last_embedded": "..."}
  ]
}
```

---

## API Endpoints

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/api/v1/documents/{id}/embedding-status` | JWT/Token | Get embedding status for a document |
| `POST` | `/api/v1/documents/{id}/index` | JWT/Token | Index document with current embedding model |
| `POST` | `/api/v1/projects/{id}/index-all` | JWT/Token | Index all project documents with current model |
| `POST` | `/api/v1/documents/index-all` | JWT/Token | Index all user's documents with current model |
| `DELETE` | `/api/v1/documents/{id}/embeddings/{model}` | JWT/Token | Delete embeddings for a specific model (cleanup) |

### `POST /api/v1/documents/{id}/index`

Indexes a document with the user's current embedding model. If chunks don't exist yet, creates them first (text extraction + chunking). If chunks exist, only creates embeddings.

**Request:** No body needed (uses user's current embedding config)

**Response:**
```json
{
  "document_id": "doc-123",
  "model": "qwen/qwen3-embedding-8b",
  "chunks_indexed": 42,
  "status": "indexed"
}
```

**If already indexed:** Returns 200 with current status (idempotent).

---

## Migration

### Step 1: Create chunk_embeddings table

```sql
CREATE TABLE IF NOT EXISTS chunk_embeddings (
    id              VARCHAR(36)     PRIMARY KEY,
    chunk_id        VARCHAR(36)     NOT NULL REFERENCES page_chunks(id) ON DELETE CASCADE,
    document_id     VARCHAR(36)     NOT NULL REFERENCES documents(id),
    provider_name   VARCHAR(50)     NOT NULL,
    model_name      VARCHAR(100)    NOT NULL,
    dimensions      INTEGER         NOT NULL,
    embedding       TEXT            NOT NULL,
    embedded_at     TIMESTAMPTZ     NOT NULL DEFAULT NOW(),

    CONSTRAINT uq_chunk_model UNIQUE (chunk_id, model_name)
);

CREATE INDEX idx_chunk_emb_doc_model ON chunk_embeddings (document_id, model_name);
CREATE INDEX idx_chunk_emb_chunk_id ON chunk_embeddings (chunk_id);
```

### Step 2: Migrate existing embeddings

```sql
-- Move existing vectors from page_chunks to chunk_embeddings
INSERT INTO chunk_embeddings (id, chunk_id, document_id, provider_name, model_name, dimensions, embedding, embedded_at)
SELECT
    gen_random_uuid()::varchar,
    pc.id,
    pc.document_id,
    'system_default',       -- provider used before BYOK
    'system_default',       -- model used before BYOK
    1024,                   -- default dimension
    pc.embedding,
    pc.created_at
FROM page_chunks pc
WHERE pc.embedding IS NOT NULL;
```

### Step 3: Drop embedding column from page_chunks

```sql
ALTER TABLE page_chunks DROP COLUMN IF EXISTS embedding;
```

---

## pgvector Index Strategy

Each unique (dimensions) value needs its own pgvector index because IVFFlat/HNSW indexes are dimension-specific:

```sql
-- Create function to build pgvector index for a dimension
-- Called after first embedding of a new dimension is stored
CREATE INDEX IF NOT EXISTS idx_chunk_emb_vector_1024
    ON chunk_embeddings
    USING ivfflat ((embedding::vector(1024)) vector_cosine_ops)
    WITH (lists = 100);

CREATE INDEX IF NOT EXISTS idx_chunk_emb_vector_3072
    ON chunk_embeddings
    USING ivfflat ((embedding::vector(3072)) vector_cosine_ops)
    WITH (lists = 100);
```

For dynamic dimensions, the application should check if an index exists for the dimension and create one if needed. This can be done in the indexer service after embedding.

---

## Service Layer

### `library/rag/indexer.py` (updated)

```python
async def index_document(
    document_id: str,
    provider_name: str,
    model_name: str,
    embed_fn: Callable,      # async (texts: list[str]) -> list[list[float]]
    dimensions: int,
) -> IndexResult:
    """Index a document's chunks with a specific embedding model.

    1. Check if page_chunks exist for this document
       - If not, run text extraction + chunking first
    2. Get all chunks that don't have embeddings for this model
    3. Embed them in batches
    4. Insert chunk_embeddings rows
    5. Return result with count
    """
    ...
```

### `library/rag/retriever.py` (updated)

```python
async def retrieve_chunks(
    query_embedding: list[float],
    document_ids: list[str],
    model_name: str,           # REQUIRED — filter by model
    top_k: int = 10,
    similarity_threshold: float = 0.5,
) -> list[RetrievedChunk]:
    """Retrieve relevant chunks using pgvector similarity search.

    Only searches chunk_embeddings with matching model_name.
    """
    ...
```

---

## Frontend Indicators

### Document List (Dashboard + Project)

```
📄 invoice.pdf          ✅ Indexed
📄 contract.pdf         ⚠️ Needs indexing    [Index]
📄 report.pdf           ✅ Indexed (2 models)
```

### Document Detail / Workspace

```
Embedding Status
├── qwen/qwen3-embedding-8b    ✅ 42/42 chunks (current)
├── openai/text-embedding-3    ✅ 42/42 chunks
└── [Index with current model]  (if not indexed)
```

---

## Rules

1. **Text chunks are immutable.** Once created, `page_chunks` rows never change. Only `chunk_embeddings` are added/removed.
2. **One embedding per chunk per model.** The unique constraint `(chunk_id, model_name)` enforces this.
3. **Old embeddings are preserved.** Switching models never deletes existing vectors.
4. **Indexing is idempotent.** Calling index on an already-indexed document is a no-op.
5. **Cascade delete.** Deleting a `page_chunk` cascades to all its `chunk_embeddings`.
6. **Deleting a document** cascades to `page_chunks` → `chunk_embeddings`.
7. **User can manually delete** embeddings for a specific model to reclaim storage.
8. **Query always filters by model.** Never mix vectors from different models in one search.
