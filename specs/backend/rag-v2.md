# Backend Spec: RAG Pipeline v2 — Contextual Chunking + Hybrid Search

Files: `backend/src/docmind/library/rag/` · `backend/src/docmind/library/pipeline/rag.py`

See also: `specs/backend/rag.md` (v1, superseded by this spec)

---

## Problem Statement

RAG v1 uses fixed-size character splitting (512 chars) which causes:
1. **Context loss at boundaries** — "Full Stack Web Developer, CV. Bima Jaya" splits into two chunks, causing the LLM to hallucinate "Bima Jaya" as a person's name instead of a company
2. **No document-level context** — each chunk is isolated with no knowledge of what document it belongs to or what section it's in
3. **Vector-only retrieval** — misses exact keyword matches (names, IDs, dates) that BM25 full-text search would catch
4. **Small chunks lose semantic coherence** — 200-500 char chunks don't carry enough context for the LLM to reason accurately

---

## Research Basis

| Source | Finding | Impact |
|--------|---------|--------|
| [NVIDIA FinanceBench 2025](https://developer.nvidia.com/blog/finding-the-best-chunking-strategy-for-accurate-ai-responses/) | Page-level chunking scored 64.8% accuracy — highest across all strategies | Page-first, split only if needed |
| [Anthropic Contextual Retrieval](https://www.anthropic.com/news/contextual-retrieval) | Prepending context to chunks reduces retrieval failures by 49%, 67% with reranking | Contextual headers on every chunk |
| [Firecrawl 2026 Benchmark](https://www.firecrawl.dev/blog/best-chunking-strategies-rag) | RecursiveCharacterTextSplitter at 512 tokens with 10-20% overlap is the reliable baseline | 1000-1500 char chunks, 200 char overlap |
| [Vectara NAACL 2025](https://blog.premai.io/rag-chunking-strategies-the-2026-benchmark-guide/) | Chunking config has as much influence on retrieval quality as embedding model choice | Invest in chunking strategy, not just embeddings |
| [ParadeDB Hybrid Search](https://www.paradedb.com/blog/hybrid-search-in-postgresql-the-missing-manual) | BM25 + vector hybrid search catches keyword queries that vector search misses | Add BM25 via PostgreSQL ts_vector |
| [Cross-Encoder Reranking](https://app.ailog.fr/en/blog/guides/reranking) | Reranking adds 10-25% accuracy on top of retrieval | Phase 2 improvement |

---

## Architecture v2

```
Upload PDF to Project
  → pymupdf4llm.to_markdown(page_chunks=True)        # page-level markdown
  → For each page:
      1. Keep page whole if ≤ 1500 chars
      2. Split with RecursiveCharacterTextSplitter if > 1500 chars
         (chunk_size=1200, overlap=200, sentence-boundary aware)
      3. Generate contextual header per chunk:
         "[Document: {filename}]
          [Page: {page_number}/{total_pages}]
          [Section: {nearest_header}]"
      4. Prepend header to chunk content
      5. Embed with DashScope text-embedding-v4
      6. Store in page_chunks with:
         - content (with header prepended)
         - raw_content (original text without header, for BM25)
         - ts_vector column (PostgreSQL full-text search)
         - embedding column (pgvector)
         - metadata (headers, filename, section path)

Query
  → Embed query → pgvector cosine search (top 20)
  → BM25 text search via ts_vector (top 20)
  → Reciprocal Rank Fusion (RRF) to merge results
  → Return top 5 to LLM with persona prompt
```

---

## Responsibility (updated)

| Component | Does |
|-----------|------|
| `rag/text_extract.py` | Extract markdown text from PDF pages via pymupdf4llm; VLM OCR fallback for scanned pages |
| `rag/chunker.py` | Page-level-first chunking with contextual headers; split only if page > threshold |
| `rag/embedder.py` | Embedding provider abstraction — DashScope text-embedding-v4 (unchanged) |
| `rag/retriever.py` | Hybrid search: pgvector cosine + BM25 ts_vector, merged via RRF |
| `rag/indexer.py` | Orchestrates extract → chunk → embed → store pipeline |

---

## Settings (`config.py` updates)

```python
# --- RAG v2 ---
EMBEDDING_PROVIDER: str = "dashscope"
EMBEDDING_MODEL: str = "text-embedding-v4"
EMBEDDING_DIMENSIONS: int = 1024
RAG_CHUNK_SIZE: int = 1200             # characters (was 512)
RAG_CHUNK_OVERLAP: int = 200           # characters (was 64)
RAG_PAGE_CHUNK_THRESHOLD: int = 1500   # NEW: pages under this size stay whole
RAG_TOP_K: int = 5                     # final chunks returned to LLM
RAG_RETRIEVAL_K: int = 20              # NEW: initial retrieval pool before fusion
RAG_SIMILARITY_THRESHOLD: float = 0.1  # minimum cosine similarity
RAG_BM25_WEIGHT: float = 0.4          # NEW: weight for BM25 in RRF fusion
RAG_VECTOR_WEIGHT: float = 0.6        # NEW: weight for vector in RRF fusion
```

---

## Data Model Updates

### `page_chunks` table — add `raw_content` and `ts_vector` columns

```sql
-- Migration: add BM25 support to page_chunks
ALTER TABLE page_chunks ADD COLUMN raw_content TEXT;
ALTER TABLE page_chunks ADD COLUMN search_vector TSVECTOR;

-- Populate search_vector from raw_content
UPDATE page_chunks SET raw_content = content WHERE raw_content IS NULL;
CREATE INDEX idx_page_chunks_search_vector ON page_chunks USING GIN(search_vector);

-- Trigger to auto-update search_vector on insert/update
CREATE OR REPLACE FUNCTION page_chunks_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.raw_content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_page_chunks_search_vector
    BEFORE INSERT OR UPDATE ON page_chunks
    FOR EACH ROW EXECUTE FUNCTION page_chunks_search_vector_update();
```

### Updated PageChunk model

```python
class PageChunk(Base):
    __tablename__ = "page_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(String, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    project_id = Column(String, ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True)
    page_number = Column(Integer, nullable=False)
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)           # WITH contextual header (for embedding)
    raw_content = Column(Text, nullable=False)        # WITHOUT header (for BM25 display)
    embedding = Column(Vector(1024))
    search_vector = Column(TSVector)                  # PostgreSQL full-text search
    metadata_ = Column("metadata", JSONB, default=dict)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
```

---

## `rag/text_extract.py` — Updated to use pymupdf4llm

```python
"""
Extract markdown text from PDF pages using pymupdf4llm.

pymupdf4llm produces cleaner markdown than raw PyMuPDF text extraction,
preserving headers, tables, and lists in a format optimized for LLMs.
It runs 100% locally — no API calls, no cost.
"""
import logging
import pymupdf4llm

logger = logging.getLogger(__name__)


def extract_pages_as_markdown(file_bytes: bytes) -> list[dict]:
    """
    Extract per-page markdown from a PDF using pymupdf4llm.

    Args:
        file_bytes: Raw PDF bytes.

    Returns:
        List of dicts, one per page:
        [
            {
                "page_number": int,          # 1-indexed
                "text": str,                 # markdown text
                "headers": list[str],        # detected headers on this page
                "has_text": bool,            # False for scanned/image-only pages
                "metadata": {
                    "images": int,           # number of images on page
                    "tables": int,           # number of tables detected
                },
            },
        ]
    """
    pages_data = pymupdf4llm.to_markdown(
        doc=file_bytes,
        page_chunks=True,       # one dict per page
        write_images=False,     # don't extract images to disk
        show_progress=False,
    )

    pages = []
    for page_data in pages_data:
        text = page_data.get("text", "").strip()
        metadata = page_data.get("metadata", {})

        # Extract headers from markdown (## lines)
        headers = []
        for line in text.split("\n"):
            stripped = line.strip()
            if stripped.startswith("#"):
                header_text = stripped.lstrip("#").strip()
                if header_text:
                    headers.append(header_text)

        pages.append({
            "page_number": metadata.get("page", 0) + 1,  # 0-indexed → 1-indexed
            "text": text,
            "headers": headers,
            "has_text": len(text) > 20,
            "metadata": {
                "images": metadata.get("images", 0),
                "tables": metadata.get("tables", 0),
            },
        })

    return pages
```

---

## `rag/chunker.py` — Page-Level-First with Contextual Headers

```python
"""
Page-level-first chunking with contextual headers.

Strategy (based on NVIDIA FinanceBench + Anthropic Contextual Retrieval):
1. Start with page-level chunks from pymupdf4llm
2. If a page is under RAG_PAGE_CHUNK_THRESHOLD chars, keep it whole
3. If a page exceeds the threshold, split using RecursiveCharacterTextSplitter
4. Prepend a contextual header to every chunk before embedding

The contextual header makes each chunk self-contained:
  [Document: resume.pdf]
  [Page: 1/3]
  [Section: Work Experience]

This prevents the "Bima Jaya" problem where split context causes hallucinations.
"""
import re
import logging
from docmind.core.config import get_settings

logger = logging.getLogger(__name__)


def _extract_nearest_header(text: str) -> str:
    """Find the most recent markdown header in text."""
    headers = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped.startswith("#"):
            header_text = stripped.lstrip("#").strip()
            if header_text:
                headers.append(header_text)
    return headers[-1] if headers else ""


def _split_sentences(text: str) -> list[str]:
    """Split text into sentences using regex with abbreviation awareness."""
    pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def _recursive_split(
    text: str,
    chunk_size: int,
    overlap: int,
) -> list[str]:
    """
    Split text into chunks at sentence boundaries with overlap.

    Falls back to character splitting if no sentence boundaries found.
    """
    sentences = _split_sentences(text)
    if not sentences:
        # Fallback: split by newlines then by chars
        if "\n" in text:
            sentences = [s.strip() for s in text.split("\n") if s.strip()]
        else:
            # Hard character split as last resort
            chunks = []
            for i in range(0, len(text), chunk_size - overlap):
                chunks.append(text[i:i + chunk_size])
            return chunks

    chunks: list[str] = []
    current: list[str] = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > chunk_size and current:
            chunk_text = " ".join(current)
            chunks.append(chunk_text)

            # Keep overlap from end of current chunk
            overlap_text = chunk_text[-overlap:] if len(chunk_text) > overlap else chunk_text
            current = [overlap_text]
            current_len = len(overlap_text)

        current.append(sentence)
        current_len += len(sentence) + 1

    if current:
        chunks.append(" ".join(current))

    return chunks


def build_contextual_header(
    filename: str,
    page_number: int,
    total_pages: int,
    section_header: str = "",
) -> str:
    """
    Build a contextual header to prepend to each chunk.

    This makes each chunk self-contained per Anthropic's Contextual Retrieval:
    the chunk knows what document it's from, what page, and what section.
    """
    parts = [f"[Document: {filename}]"]
    parts.append(f"[Page: {page_number}/{total_pages}]")
    if section_header:
        parts.append(f"[Section: {section_header}]")
    return "\n".join(parts)


def chunk_pages(
    pages: list[dict],
    filename: str,
) -> list[dict]:
    """
    Chunk extracted pages using page-level-first strategy.

    For each page:
    - If page text ≤ RAG_PAGE_CHUNK_THRESHOLD: keep as single chunk
    - If page text > threshold: split with recursive character splitter
    - Prepend contextual header to every chunk

    Args:
        pages: Output from extract_pages_as_markdown().
        filename: Document filename for contextual header.

    Returns:
        List of chunk dicts ready for embedding:
        [
            {
                "page_number": int,
                "chunk_index": int,
                "content": str,         # WITH header (for embedding)
                "raw_content": str,      # WITHOUT header (for BM25/display)
                "metadata": {
                    "section_header": str,
                    "filename": str,
                    "file_type": str,
                    "is_full_page": bool,
                },
            },
        ]
    """
    settings = get_settings()
    threshold = settings.RAG_PAGE_CHUNK_THRESHOLD
    chunk_size = settings.RAG_CHUNK_SIZE
    overlap = settings.RAG_CHUNK_OVERLAP
    total_pages = len(pages)

    all_chunks: list[dict] = []

    for page in pages:
        if not page.get("has_text"):
            continue

        text = page["text"]
        page_number = page["page_number"]
        headers = page.get("headers", [])
        nearest_header = headers[-1] if headers else ""

        header = build_contextual_header(
            filename=filename,
            page_number=page_number,
            total_pages=total_pages,
            section_header=nearest_header,
        )

        if len(text) <= threshold:
            # Keep page as a single chunk
            all_chunks.append({
                "page_number": page_number,
                "chunk_index": 0,
                "content": f"{header}\n{text}",
                "raw_content": text,
                "metadata": {
                    "section_header": nearest_header,
                    "filename": filename,
                    "file_type": "pdf",
                    "is_full_page": True,
                },
            })
        else:
            # Split page into sub-chunks
            sub_texts = _recursive_split(text, chunk_size, overlap)
            for idx, sub_text in enumerate(sub_texts):
                sub_header = _extract_nearest_header(sub_text) or nearest_header
                chunk_header = build_contextual_header(
                    filename=filename,
                    page_number=page_number,
                    total_pages=total_pages,
                    section_header=sub_header,
                )
                all_chunks.append({
                    "page_number": page_number,
                    "chunk_index": idx,
                    "content": f"{chunk_header}\n{sub_text}",
                    "raw_content": sub_text,
                    "metadata": {
                        "section_header": sub_header,
                        "filename": filename,
                        "file_type": "pdf",
                        "is_full_page": False,
                    },
                })

    return all_chunks
```

---

## `rag/retriever.py` — Hybrid Search (Vector + BM25 via RRF)

```python
"""
Hybrid retrieval: pgvector cosine similarity + PostgreSQL BM25 full-text search.

Combines both methods using Reciprocal Rank Fusion (RRF):
  score = vector_weight / (k + vector_rank) + bm25_weight / (k + bm25_rank)

This catches both semantic matches (vector) and keyword matches (BM25).
A query like "Lalu Erfandi" will be caught by BM25 even if the vector
embedding doesn't rank it highly.
"""
import logging
from sqlalchemy import text as sql_text
from docmind.core.config import get_settings
from docmind.dbase.psql.core.session import AsyncSessionLocal

logger = logging.getLogger(__name__)

RRF_K = 60  # Reciprocal Rank Fusion constant (standard value)


async def retrieve_hybrid(
    project_id: str,
    query_embedding: list[float],
    query_text: str,
    top_k: int | None = None,
) -> list[dict]:
    """
    Hybrid search: vector similarity + BM25 full-text, merged via RRF.

    Args:
        project_id: Project to search within.
        query_embedding: Embedding vector of the user's query.
        query_text: Raw query text for BM25 search.
        top_k: Number of final results. Defaults to RAG_TOP_K.

    Returns:
        List of result dicts sorted by RRF score (descending).
    """
    settings = get_settings()
    top_k = top_k or settings.RAG_TOP_K
    retrieval_k = settings.RAG_RETRIEVAL_K
    vector_weight = settings.RAG_VECTOR_WEIGHT
    bm25_weight = settings.RAG_BM25_WEIGHT

    query = sql_text("""
        WITH vector_results AS (
            SELECT
                pc.id AS chunk_id,
                pc.document_id,
                d.filename AS document_name,
                pc.page_number,
                pc.chunk_index,
                pc.raw_content AS content,
                1 - (pc.embedding <=> :embedding) AS similarity,
                ROW_NUMBER() OVER (ORDER BY pc.embedding <=> :embedding) AS vector_rank
            FROM page_chunks pc
            JOIN documents d ON d.id = pc.document_id
            WHERE pc.project_id = :project_id
            LIMIT :retrieval_k
        ),
        bm25_results AS (
            SELECT
                pc.id AS chunk_id,
                pc.document_id,
                d.filename AS document_name,
                pc.page_number,
                pc.chunk_index,
                pc.raw_content AS content,
                ts_rank_cd(pc.search_vector, plainto_tsquery('english', :query_text)) AS bm25_score,
                ROW_NUMBER() OVER (
                    ORDER BY ts_rank_cd(pc.search_vector, plainto_tsquery('english', :query_text)) DESC
                ) AS bm25_rank
            FROM page_chunks pc
            JOIN documents d ON d.id = pc.document_id
            WHERE pc.project_id = :project_id
              AND pc.search_vector @@ plainto_tsquery('english', :query_text)
            LIMIT :retrieval_k
        ),
        fused AS (
            SELECT
                COALESCE(v.chunk_id, b.chunk_id) AS chunk_id,
                COALESCE(v.document_id, b.document_id) AS document_id,
                COALESCE(v.document_name, b.document_name) AS document_name,
                COALESCE(v.page_number, b.page_number) AS page_number,
                COALESCE(v.chunk_index, b.chunk_index) AS chunk_index,
                COALESCE(v.content, b.content) AS content,
                COALESCE(v.similarity, 0) AS similarity,
                COALESCE(v.vector_rank, 9999) AS vector_rank,
                COALESCE(b.bm25_rank, 9999) AS bm25_rank,
                -- RRF score
                (:vector_weight / (:rrf_k + COALESCE(v.vector_rank, 9999)))
                + (:bm25_weight / (:rrf_k + COALESCE(b.bm25_rank, 9999))) AS rrf_score
            FROM vector_results v
            FULL OUTER JOIN bm25_results b ON v.chunk_id = b.chunk_id
        )
        SELECT * FROM fused
        ORDER BY rrf_score DESC
        LIMIT :top_k
    """)

    async with AsyncSessionLocal() as session:
        result = await session.execute(
            query,
            {
                "project_id": project_id,
                "embedding": str(query_embedding),
                "query_text": query_text,
                "retrieval_k": retrieval_k,
                "top_k": top_k,
                "vector_weight": vector_weight,
                "bm25_weight": bm25_weight,
                "rrf_k": RRF_K,
            },
        )
        rows = result.mappings().all()

    return [
        {
            "chunk_id": row["chunk_id"],
            "document_id": row["document_id"],
            "document_name": row["document_name"],
            "page_number": row["page_number"],
            "chunk_index": row["chunk_index"],
            "content": row["content"],
            "similarity": float(row["similarity"]),
            "rrf_score": float(row["rrf_score"]),
        }
        for row in rows
    ]
```

---

## `rag/indexer.py` — Updated Indexing Flow

Key changes from v1:
1. Uses `pymupdf4llm` instead of raw `fitz` for text extraction
2. Uses `chunk_pages()` instead of `chunk_text()` for page-level-first chunking
3. Stores both `content` (with header) and `raw_content` (without) for hybrid search
4. `search_vector` auto-populated by PostgreSQL trigger

```python
async def index_document_for_rag(
    document_id: str,
    project_id: str,
    file_bytes: bytes,
    file_type: str,
    filename: str,
) -> int:
    """
    Index a document for RAG retrieval using v2 strategy.

    Steps:
    1. Extract per-page markdown via pymupdf4llm
    2. Chunk with page-level-first strategy + contextual headers
    3. Embed all chunks via DashScope text-embedding-v4
    4. Store in page_chunks (search_vector auto-populated by trigger)

    Args:
        document_id: Document UUID.
        project_id: Project UUID.
        file_bytes: Raw file bytes.
        file_type: "pdf", "png", "jpg", etc.
        filename: Original filename (used in contextual headers).

    Returns:
        Number of chunks stored.
    """
    settings = get_settings()
    embedder = get_embedder()

    # Step 1: Extract pages
    if file_type.lower() in ("pdf", "application/pdf"):
        pages = extract_pages_as_markdown(file_bytes)
    else:
        # Image: single page, use VLM OCR
        pages = await _extract_image_pages(file_bytes, file_type)

    # Step 2: Chunk with contextual headers
    chunks = chunk_pages(pages, filename=filename)

    if not chunks:
        logger.warning("No chunks extracted", document_id=document_id)
        return 0

    # Step 3: Embed (use content WITH headers for richer embeddings)
    texts = [c["content"] for c in chunks]
    embeddings = await embedder.embed(texts)

    # Step 4: Store
    async with AsyncSessionLocal() as session:
        for chunk, embedding in zip(chunks, embeddings):
            record = PageChunk(
                id=str(uuid.uuid4()),
                document_id=document_id,
                project_id=project_id,
                page_number=chunk["page_number"],
                chunk_index=chunk["chunk_index"],
                content=chunk["content"],
                raw_content=chunk["raw_content"],  # NEW: for BM25
                embedding=embedding,
                metadata_=chunk["metadata"],
            )
            session.add(record)
        await session.commit()

    return len(chunks)
```

---

## Example: How Contextual Headers Fix the "Bima Jaya" Problem

### Before (v1 — fixed-size splitting)

```
Chunk 20: "Full Stack Web Developer, CV."
Chunk 21: "Bima Jaya 2015 — MAR 2018 • Build CMS from scratch..."
```

LLM sees "Bima Jaya" in isolation → hallucinates it as the person's name.

### After (v2 — page-level with contextual header)

```
Chunk (page 3, full page):
"[Document: resume.pdf]
[Page: 3/3]
[Section: Work Experience]
Full Stack Web Developer, CV. Bima Jaya
2015 — MAR 2018
• Build CMS from scratch with Django and AngularJs...
• Created a web service for patient queue registration...
...
B.Sc in Information Technology, STMIK Bumigora (2006-2013)
..."
```

The entire page stays together. "CV. Bima Jaya" is clearly a company name in context.
The header tells the LLM this is page 3 of resume.pdf, section "Work Experience".

---

## Implementation Priority

| Phase | Change | Impact | Effort |
|-------|--------|--------|--------|
| **Phase 1** | Contextual headers + page-level chunking | High | Medium |
| **Phase 1** | Larger chunks (1200 chars) + overlap (200) | Medium | Done |
| **Phase 2** | BM25 hybrid search (ts_vector + RRF) | High | Medium |
| **Phase 2** | Database migration (raw_content + search_vector) | Medium | Low |
| **Phase 3** | Cross-encoder reranking | Medium | Medium |
| **Phase 3** | Full contextual retrieval (LLM summary per chunk) | Highest | High (API cost) |

---

## Migration Plan

```sql
-- Phase 1: No schema changes needed (contextual header goes in existing content column)

-- Phase 2: Add BM25 support
ALTER TABLE page_chunks ADD COLUMN IF NOT EXISTS raw_content TEXT;
ALTER TABLE page_chunks ADD COLUMN IF NOT EXISTS search_vector TSVECTOR;

CREATE INDEX IF NOT EXISTS idx_page_chunks_search_vector
    ON page_chunks USING GIN(search_vector);

CREATE OR REPLACE FUNCTION page_chunks_search_vector_update() RETURNS trigger AS $$
BEGIN
    NEW.search_vector := to_tsvector('english', COALESCE(NEW.raw_content, ''));
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_page_chunks_search_vector ON page_chunks;
CREATE TRIGGER trg_page_chunks_search_vector
    BEFORE INSERT OR UPDATE ON page_chunks
    FOR EACH ROW EXECUTE FUNCTION page_chunks_search_vector_update();

-- Backfill existing chunks
UPDATE page_chunks SET raw_content = content WHERE raw_content IS NULL;
```

---

## Rules

- All settings come from `get_settings()`. No hardcoded values.
- `rag/` never imports from `docmind/modules/`.
- Chunks are **immutable** — re-indexing deletes old chunks then inserts new ones.
- `content` column always has the contextual header prepended (used for embedding).
- `raw_content` column has the original text without header (used for BM25 and display).
- The BM25 `search_vector` is auto-maintained by the PostgreSQL trigger — no application code needed.
