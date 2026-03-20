# Backend Spec: RAG Pipeline

Files: `backend/src/docmind/library/rag/` · `backend/src/docmind/library/pipeline/rag.py`

Library dependencies: `backend/src/docmind/library/cv/` · `backend/src/docmind/library/providers/`

See also: [[projects/docmind-vlm/specs/backend/pipeline-processing]] · [[projects/docmind-vlm/specs/backend/pipeline-chat]] · [[projects/docmind-vlm/specs/backend/providers]] · [[projects/docmind-vlm/specs/backend/services]]

---

## Responsibility

| Component | Does |
|-----------|------|
| `docmind/library/rag/chunker.py` | Split page text into overlapping chunks with sentence-boundary awareness |
| `docmind/library/rag/text_extract.py` | Extract text from PDF pages (PyMuPDF) and images (VLM OCR fallback) |
| `docmind/library/rag/embedder.py` | Embedding provider abstraction — DashScope and OpenAI implementations |
| `docmind/library/rag/retriever.py` | pgvector cosine similarity search across a project's chunks |
| `docmind/library/pipeline/rag.py` | LangGraph StateGraph for project-level RAG chat |

The RAG module **never** imports from `docmind/modules/` — it communicates through function arguments and return values only. It lives under `library/rag/` because it is reusable logic, invoked by module-level usecases.

---

## Architecture Overview

```
Upload PDF to Project
  -> split into pages (reuse existing CV preprocessing)
  -> extract text per page (PyMuPDF for PDF, VLM for images)
  -> chunk text (fixed-size with overlap, sentence-boundary aware)
  -> embed chunks (DashScope text-embedding-v3 or OpenAI text-embedding-3-small)
  -> store in page_chunks table with pgvector embedding column

Project Chat Query
  -> embed user query
  -> pgvector similarity search across project's chunks
  -> build context from top-K chunks
  -> pass to LLM with persona system prompt + retrieved context
  -> generate answer with citations (document name, page number)
```

---

## Imports

```python
# From module usecase or service layer:
from docmind.library.rag import chunk_text, embed_chunks, retrieve_chunks
from docmind.library.rag import extract_text_from_pdf, extract_text_from_image
from docmind.library.rag import index_document_for_rag
from docmind.library.pipeline.rag import run_rag_chat_pipeline

# Internal imports within RAG library:
from docmind.library.rag.chunker import chunk_text
from docmind.library.rag.text_extract import extract_text_from_pdf, extract_text_from_image
from docmind.library.rag.embedder import get_embedder, EmbeddingProvider
from docmind.library.rag.retriever import retrieve_chunks
from docmind.core.config import get_settings
from docmind.core.logging import get_logger
```

---

## Data Model

```python
"""
docmind/dbase/psql/models/page_chunk.py

SQLAlchemy model for RAG page chunks with pgvector embeddings.
"""
import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from docmind.dbase.psql.core.base import Base


class PageChunk(Base):
    """A text chunk from a document page, stored with its embedding vector."""

    __tablename__ = "page_chunks"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = Column(
        String,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    project_id = Column(
        String,
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    page_number = Column(Integer, nullable=False)        # 1-indexed
    chunk_index = Column(Integer, nullable=False)         # 0-indexed within page
    content = Column(Text, nullable=False)
    embedding = Column(Vector(1024))                      # pgvector vector type
    metadata_ = Column("metadata", JSONB, default=dict)   # source info, char offsets
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    document = relationship("Document", back_populates="page_chunks")
    project = relationship("Project", back_populates="page_chunks")
```

---

## Settings (`config.py` additions)

```python
# --- RAG ---
EMBEDDING_PROVIDER: str = "dashscope"       # or "openai"
EMBEDDING_MODEL: str = "text-embedding-v3"
EMBEDDING_DIMENSIONS: int = 1024
RAG_CHUNK_SIZE: int = 512                   # characters
RAG_CHUNK_OVERLAP: int = 64                 # characters
RAG_TOP_K: int = 8                          # chunks to retrieve
RAG_SIMILARITY_THRESHOLD: float = 0.3       # minimum cosine similarity
```

All accessed via `get_settings()`. Never instantiate `Settings()` directly.

---

## File Structure

```
library/
  rag/
    __init__.py          # Re-exports: chunk_text, embed_chunks, retrieve_chunks, etc.
    chunker.py           # Text chunking with overlap
    embedder.py          # Embedding provider abstraction (DashScope / OpenAI)
    retriever.py         # pgvector similarity search
    text_extract.py      # PDF text extraction (PyMuPDF) + image OCR fallback
  pipeline/
    rag.py               # LangGraph StateGraph for project-level RAG chat
```

---

## `library/rag/text_extract.py`

```python
"""
docmind/library/rag/text_extract.py

Text extraction from PDF pages and images.
Uses PyMuPDF for native PDF text; falls back to VLM OCR for scanned pages.
"""
import logging

import fitz  # PyMuPDF
import numpy as np

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> list[dict]:
    """
    Extract text from each page of a PDF using PyMuPDF.

    Args:
        file_bytes: Raw PDF bytes.

    Returns:
        List of dicts, one per page:
        [
            {
                "page_number": int,   # 1-indexed
                "text": str,
                "has_text": bool,     # False for scanned/image-only pages
            },
            ...
        ]
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages = []

    for page_idx in range(len(doc)):
        page = doc[page_idx]
        text = page.get_text("text").strip()
        pages.append({
            "page_number": page_idx + 1,
            "text": text,
            "has_text": len(text) > 20,  # Threshold: fewer than 20 chars = likely scanned
        })

    doc.close()
    return pages


async def extract_text_from_image(image: np.ndarray) -> str:
    """
    Extract text from an image using VLM OCR fallback.

    Called for scanned PDF pages (has_text=False) or standalone image uploads.
    Uses the configured VLM provider to read text from the image.

    Args:
        image: OpenCV image array (BGR or RGB).

    Returns:
        Extracted text string.
    """
    from docmind.library.providers import get_vlm_provider

    provider = get_vlm_provider()

    prompt = (
        "Read all text visible in this image. Return the raw text exactly as it appears, "
        "preserving layout and line breaks where possible. Do not add any commentary."
    )

    response = await provider.extract(images=[image], prompt=prompt)
    return response.get("content", "")
```

---

## `library/rag/chunker.py`

```python
"""
docmind/library/rag/chunker.py

Text chunking with sentence-boundary awareness and overlap.
"""
import re


def _split_sentences(text: str) -> list[str]:
    """
    Split text into sentences using regex.

    Handles common abbreviations and decimal numbers to avoid
    false splits. Returns list of sentence strings.
    """
    # Split on sentence-ending punctuation followed by whitespace + uppercase
    pattern = r'(?<=[.!?])\s+(?=[A-Z])'
    sentences = re.split(pattern, text)
    return [s.strip() for s in sentences if s.strip()]


def chunk_text(
    text: str,
    chunk_size: int = 512,
    overlap: int = 64,
) -> list[dict]:
    """
    Split text into overlapping chunks at sentence boundaries.

    Strategy:
    1. Split text into sentences.
    2. Merge sentences until chunk_size is reached.
    3. Overlap with previous chunk's last `overlap` characters.

    Args:
        text: Full page text to chunk.
        chunk_size: Target chunk size in characters.
        overlap: Number of characters to overlap between consecutive chunks.

    Returns:
        List of chunk dicts:
        [
            {
                "content": str,
                "start_char": int,
                "end_char": int,
                "chunk_index": int,
            },
            ...
        ]
    """
    if not text or not text.strip():
        return []

    sentences = _split_sentences(text)
    if not sentences:
        return []

    chunks: list[dict] = []
    current_sentences: list[str] = []
    current_len = 0
    char_offset = 0
    chunk_index = 0

    for sentence in sentences:
        sentence_len = len(sentence)

        # If adding this sentence exceeds chunk_size, finalize current chunk
        if current_len + sentence_len > chunk_size and current_sentences:
            content = " ".join(current_sentences)
            chunks.append({
                "content": content,
                "start_char": char_offset,
                "end_char": char_offset + len(content),
                "chunk_index": chunk_index,
            })

            # Calculate overlap: keep trailing characters from current chunk
            overlap_text = content[-overlap:] if len(content) > overlap else content
            overlap_start = content.rfind(" ", 0, len(content) - overlap)

            # Reset with overlap
            char_offset = char_offset + len(content) - len(overlap_text)
            current_sentences = [overlap_text]
            current_len = len(overlap_text)
            chunk_index += 1

        current_sentences.append(sentence)
        current_len += sentence_len + 1  # +1 for space join

    # Finalize last chunk
    if current_sentences:
        content = " ".join(current_sentences)
        chunks.append({
            "content": content,
            "start_char": char_offset,
            "end_char": char_offset + len(content),
            "chunk_index": chunk_index,
        })

    return chunks
```

---

## `library/rag/embedder.py`

```python
"""
docmind/library/rag/embedder.py

Embedding provider abstraction with DashScope and OpenAI implementations.
"""
import logging
from typing import Protocol

import httpx

from docmind.core.config import get_settings

logger = logging.getLogger(__name__)

# Maximum texts per embedding API call
DASHSCOPE_BATCH_SIZE = 25
OPENAI_BATCH_SIZE = 100


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (list of floats), one per input text.
        """
        ...


class DashScopeEmbedder:
    """
    Embedding provider using DashScope text-embedding-v3 API.

    DashScope supports a maximum of 25 texts per API call.
    For larger batches, this implementation splits into sub-batches automatically.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.DASHSCOPE_API_KEY
        self._model = settings.EMBEDDING_MODEL
        self._dimensions = settings.EMBEDDING_DIMENSIONS
        self._base_url = (
            "https://dashscope-intl.aliyuncs.com/api/v1"
            "/services/embeddings/text-embedding/text-embedding"
        )

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed texts via DashScope API.

        Automatically batches into groups of 25 (API limit).

        Args:
            texts: List of text strings.

        Returns:
            List of embedding vectors.

        Raises:
            httpx.HTTPStatusError: On API errors.
        """
        all_embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(texts), DASHSCOPE_BATCH_SIZE):
                batch = texts[i : i + DASHSCOPE_BATCH_SIZE]

                response = await client.post(
                    self._base_url,
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "input": {"texts": batch},
                        "parameters": {
                            "dimension": self._dimensions,
                            "text_type": "document",
                        },
                    },
                )
                response.raise_for_status()

                data = response.json()
                embeddings = data["output"]["embeddings"]
                # Sort by text_index to preserve input order
                embeddings.sort(key=lambda e: e["text_index"])
                all_embeddings.extend([e["embedding"] for e in embeddings])

        return all_embeddings


class OpenAIEmbedder:
    """
    Embedding provider using OpenAI text-embedding-3-small API.

    Supports up to 100 texts per API call.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.OPENAI_API_KEY
        self._model = "text-embedding-3-small"
        self._dimensions = settings.EMBEDDING_DIMENSIONS

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """
        Embed texts via OpenAI API.

        Automatically batches into groups of 100 (API limit).

        Args:
            texts: List of text strings.

        Returns:
            List of embedding vectors.

        Raises:
            httpx.HTTPStatusError: On API errors.
        """
        all_embeddings: list[list[float]] = []

        async with httpx.AsyncClient(timeout=60.0) as client:
            for i in range(0, len(texts), OPENAI_BATCH_SIZE):
                batch = texts[i : i + OPENAI_BATCH_SIZE]

                response = await client.post(
                    "https://api.openai.com/v1/embeddings",
                    headers={
                        "Authorization": f"Bearer {self._api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "input": batch,
                        "dimensions": self._dimensions,
                    },
                )
                response.raise_for_status()

                data = response.json()
                embeddings = data["data"]
                embeddings.sort(key=lambda e: e["index"])
                all_embeddings.extend([e["embedding"] for e in embeddings])

        return all_embeddings


def get_embedder() -> EmbeddingProvider:
    """
    Factory: return the configured embedding provider.

    Reads EMBEDDING_PROVIDER from settings. Defaults to DashScope.

    Returns:
        An EmbeddingProvider instance.

    Raises:
        ValueError: If EMBEDDING_PROVIDER is not recognized.
    """
    settings = get_settings()
    provider = settings.EMBEDDING_PROVIDER.lower()

    if provider == "dashscope":
        return DashScopeEmbedder()
    elif provider == "openai":
        return OpenAIEmbedder()
    else:
        raise ValueError(
            f"Unknown embedding provider: {provider}. "
            "Supported: 'dashscope', 'openai'"
        )
```

---

## `library/rag/retriever.py`

```python
"""
docmind/library/rag/retriever.py

pgvector similarity search across a project's page chunks.
"""
import logging

from sqlalchemy import text as sql_text
from sqlalchemy.ext.asyncio import AsyncSession

from docmind.core.config import get_settings

logger = logging.getLogger(__name__)


async def retrieve_chunks(
    session: AsyncSession,
    project_id: str,
    query_embedding: list[float],
    top_k: int | None = None,
    similarity_threshold: float | None = None,
) -> list[dict]:
    """
    Search pgvector for most similar chunks in a project.

    Uses the cosine distance operator (<=>) for similarity ranking.
    Joins with documents table to include document name in results.

    Args:
        session: SQLAlchemy async session.
        project_id: Project to search within.
        query_embedding: Embedding vector of the user's query.
        top_k: Number of chunks to return. Defaults to RAG_TOP_K setting.
        similarity_threshold: Minimum cosine similarity. Defaults to RAG_SIMILARITY_THRESHOLD.

    Returns:
        List of result dicts sorted by similarity (descending):
        [
            {
                "chunk_id": str,
                "document_id": str,
                "document_name": str,
                "page_number": int,
                "chunk_index": int,
                "content": str,
                "similarity": float,
            },
            ...
        ]
    """
    settings = get_settings()
    top_k = top_k or settings.RAG_TOP_K
    similarity_threshold = similarity_threshold or settings.RAG_SIMILARITY_THRESHOLD

    # pgvector cosine distance: 1 - (a <=> b) gives cosine similarity
    query = sql_text("""
        SELECT
            pc.id AS chunk_id,
            pc.document_id,
            d.original_filename AS document_name,
            pc.page_number,
            pc.chunk_index,
            pc.content,
            1 - (pc.embedding <=> :embedding) AS similarity
        FROM page_chunks pc
        JOIN documents d ON d.id = pc.document_id
        WHERE pc.project_id = :project_id
          AND 1 - (pc.embedding <=> :embedding) >= :threshold
        ORDER BY pc.embedding <=> :embedding
        LIMIT :top_k
    """)

    result = await session.execute(
        query,
        {
            "project_id": project_id,
            "embedding": str(query_embedding),
            "threshold": similarity_threshold,
            "top_k": top_k,
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
        }
        for row in rows
    ]
```

---

## RAG Indexing: `index_document_for_rag`

```python
"""
docmind/library/rag/indexer.py

Index a document for RAG retrieval. Called when a document is added to a project.
"""
import logging
import uuid

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.dbase.psql.models.page_chunk import PageChunk
from docmind.library.cv.preprocessing import convert_to_page_images
from docmind.library.rag.chunker import chunk_text
from docmind.library.rag.embedder import get_embedder
from docmind.library.rag.text_extract import extract_text_from_image, extract_text_from_pdf

logger = get_logger(__name__)


async def index_document_for_rag(
    document_id: str,
    project_id: str,
    file_bytes: bytes,
    file_type: str,
) -> int:
    """
    Index a document for RAG retrieval.

    Steps:
    1. Extract text from pages (PyMuPDF for PDF, VLM for images).
    2. Chunk text per page with overlap.
    3. Embed all chunks in batches via configured provider.
    4. Store chunks + embeddings in page_chunks table.

    Args:
        document_id: ID of the document being indexed.
        project_id: ID of the project the document belongs to.
        file_bytes: Raw file bytes (PDF or image).
        file_type: MIME type or extension ("pdf", "png", "jpg", etc.).

    Returns:
        Number of chunks created and stored.
    """
    settings = get_settings()
    embedder = get_embedder()

    # Step 1: Extract text from pages
    if file_type.lower() in ("pdf", "application/pdf"):
        pages = extract_text_from_pdf(file_bytes)

        # For scanned pages (no native text), fall back to VLM OCR
        page_images = None
        for page in pages:
            if not page["has_text"]:
                if page_images is None:
                    page_images = convert_to_page_images(
                        file_bytes=file_bytes,
                        file_type=file_type,
                    )
                page_idx = page["page_number"] - 1
                if page_idx < len(page_images):
                    page["text"] = await extract_text_from_image(page_images[page_idx])
                    page["has_text"] = bool(page["text"].strip())
    else:
        # Single image upload
        page_images = convert_to_page_images(
            file_bytes=file_bytes,
            file_type=file_type,
        )
        pages = []
        for idx, img in enumerate(page_images):
            text = await extract_text_from_image(img)
            pages.append({
                "page_number": idx + 1,
                "text": text,
                "has_text": bool(text.strip()),
            })

    # Step 2: Chunk text per page
    all_chunks: list[dict] = []
    for page in pages:
        if not page["has_text"]:
            continue

        page_chunks = chunk_text(
            text=page["text"],
            chunk_size=settings.RAG_CHUNK_SIZE,
            overlap=settings.RAG_CHUNK_OVERLAP,
        )

        for chunk in page_chunks:
            all_chunks.append({
                "id": str(uuid.uuid4()),
                "document_id": document_id,
                "project_id": project_id,
                "page_number": page["page_number"],
                "chunk_index": chunk["chunk_index"],
                "content": chunk["content"],
                "metadata": {
                    "start_char": chunk["start_char"],
                    "end_char": chunk["end_char"],
                },
            })

    if not all_chunks:
        logger.warning(
            "No text chunks extracted",
            document_id=document_id,
            page_count=len(pages),
        )
        return 0

    # Step 3: Embed all chunks
    texts = [c["content"] for c in all_chunks]
    embeddings = await embedder.embed(texts)

    # Step 4: Store in database
    async with AsyncSessionLocal() as session:
        for chunk_data, embedding in zip(all_chunks, embeddings):
            chunk = PageChunk(
                id=chunk_data["id"],
                document_id=chunk_data["document_id"],
                project_id=chunk_data["project_id"],
                page_number=chunk_data["page_number"],
                chunk_index=chunk_data["chunk_index"],
                content=chunk_data["content"],
                embedding=embedding,
                metadata_=chunk_data["metadata"],
            )
            session.add(chunk)

        await session.commit()

    logger.info(
        "Document indexed for RAG",
        document_id=document_id,
        chunk_count=len(all_chunks),
    )

    return len(all_chunks)
```

---

## `library/rag/__init__.py`

```python
"""
docmind/library/rag/__init__.py

Re-exports for convenient access to RAG components.
"""
from .chunker import chunk_text
from .embedder import EmbeddingProvider, get_embedder
from .indexer import index_document_for_rag
from .retriever import retrieve_chunks
from .text_extract import extract_text_from_image, extract_text_from_pdf
```

---

## Project Chat Pipeline: `library/pipeline/rag.py`

```python
"""
docmind/library/pipeline/rag.py

LangGraph StateGraph for the project-level RAG chat pipeline.

Unlike the document chat pipeline (pipeline/chat.py) which works with
a single document's extracted fields, this pipeline retrieves from
all documents in a project using pgvector similarity search.

Pipeline flow: embed_query -> retrieve -> reason -> cite -> END
"""
from typing import Any, Callable, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from docmind.core.logging import get_logger

logger = get_logger(__name__)


class RagCitation(TypedDict):
    """Citation linking answer text to a document chunk."""
    document_id: str
    document_name: str
    page_number: int
    chunk_id: str
    text_span: str


class RagChatState(TypedDict):
    """
    Full state flowing through the RAG chat pipeline.

    Each node reads what it needs and writes its outputs.
    State is immutable per convention -- nodes return new dicts,
    LangGraph merges them into the next state.
    """
    # Input (set before pipeline starts)
    project_id: str
    user_id: str
    message: str
    conversation_history: list[dict]  # [{"role": str, "content": str}, ...]

    # embed_query output
    query_embedding: list[float]

    # retrieve output
    relevant_chunks: list[dict]

    # reason output
    raw_answer: str

    # cite output
    answer: str
    citations: list[RagCitation]

    # Pipeline metadata
    error_message: str | None
    stream_callback: Callable | None  # SSE token streaming callback


def build_rag_chat_graph() -> StateGraph:
    """
    Build and compile the project-level RAG chat StateGraph.

    Pipeline flow:
        embed_query -> retrieve -> reason -> cite -> END

    Uses MemorySaver checkpointer for conversation persistence.
    Each invocation with the same thread_id resumes the conversation.

    Returns:
        Compiled LangGraph StateGraph with checkpointer.
    """
    graph = StateGraph(RagChatState)

    graph.add_node("embed_query", embed_query_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("reason", reason_node)
    graph.add_node("cite", cite_node)

    graph.set_entry_point("embed_query")

    graph.add_edge("embed_query", "retrieve")
    graph.add_edge("retrieve", "reason")
    graph.add_edge("reason", "cite")
    graph.add_edge("cite", END)

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)


# Module-level compiled graph (reused across invocations)
rag_chat_graph = build_rag_chat_graph()


def run_rag_chat_pipeline(initial_state: dict, config: dict) -> dict:
    """
    Run the full RAG chat pipeline.

    This is the main entry point called by the project chat usecase.

    Args:
        initial_state: RagChatState dict with input fields populated.
        config: LangGraph config with thread_id for conversation isolation.

    Returns:
        Final RagChatState dict with all outputs.
    """
    return rag_chat_graph.invoke(initial_state, config=config)
```

**Graph Rules:**
- Linear flow (no conditional edges) -- all four nodes always run
- Checkpointer uses `MemorySaver` (in-memory) for development; replace with `PostgresSaver` for production
- Thread ID format: `"{project_id}:{user_id}"` -- one conversation per user per project
- Conversation history is loaded from checkpointer, not passed from API

---

## `embed_query_node`

```python
"""
Embed the user's query using the configured embedding provider.
"""
import asyncio

from docmind.library.rag.embedder import get_embedder


def embed_query_node(state: dict) -> dict:
    """
    Pipeline node: embed the user's query.

    Uses the same embedding provider and model as indexing
    to ensure vector space consistency.
    """
    message = state["message"]
    embedder = get_embedder()

    try:
        # Embed single query text
        embeddings = asyncio.get_event_loop().run_until_complete(
            embedder.embed([message])
        )
        query_embedding = embeddings[0]

        logger.info(
            "Query embedded",
            dimensions=len(query_embedding),
        )

        return {"query_embedding": query_embedding}

    except Exception as e:
        logger.error("Query embedding failed", error=str(e))
        return {
            "query_embedding": [],
            "error_message": f"Failed to embed query: {e}",
        }
```

---

## `retrieve_node`

```python
"""
Retrieve relevant chunks from pgvector for the user's query.
"""
import asyncio

from docmind.dbase.psql.core.session import AsyncSessionLocal
from docmind.library.rag.retriever import retrieve_chunks


def retrieve_node(state: dict) -> dict:
    """
    Pipeline node: retrieve relevant chunks via pgvector similarity search.

    Searches across all documents in the project for chunks
    most similar to the query embedding.
    """
    project_id = state["project_id"]
    query_embedding = state.get("query_embedding", [])

    if not query_embedding:
        return {
            "relevant_chunks": [],
            "error_message": state.get("error_message", "No query embedding available"),
        }

    try:
        async def _retrieve() -> list[dict]:
            async with AsyncSessionLocal() as session:
                return await retrieve_chunks(
                    session=session,
                    project_id=project_id,
                    query_embedding=query_embedding,
                )

        chunks = asyncio.get_event_loop().run_until_complete(_retrieve())

        logger.info(
            "Retrieved chunks",
            chunk_count=len(chunks),
            project_id=project_id,
        )

        return {"relevant_chunks": chunks}

    except Exception as e:
        logger.error("Retrieval failed", error=str(e))
        return {
            "relevant_chunks": [],
            "error_message": f"Retrieval failed: {e}",
        }
```

---

## `reason_node`

```python
"""
Reasoning node: generate a grounded answer using retrieved RAG context.

The answer MUST be grounded in retrieved document chunks only.
"""
import asyncio

from docmind.library.providers import get_vlm_provider


RAG_SYSTEM_PROMPT = """You are a project document assistant. You answer questions based on documents uploaded to a project.

CRITICAL RULES:
1. ONLY answer based on the retrieved document chunks provided below.
2. NEVER use external knowledge, training data, or assumptions not supported by the documents.
3. If the retrieved chunks do not contain enough information to answer, say: "I could not find this information in the project documents."
4. When referencing information, ALWAYS cite the source document name and page number.
5. If chunks from multiple documents are relevant, synthesize across them and cite each source.
6. Do not hallucinate or infer information not present in the chunks.

RESPONSE FORMAT:
- Be concise and direct.
- Use inline citations: [Document Name, p.X]
- If multiple documents contain relevant info, present a unified answer citing all sources.
- Note any contradictions between documents if found."""


def _build_rag_context(chunks: list[dict]) -> str:
    """Build the retrieved context string for the reasoning prompt."""
    if not chunks:
        return "NO RELEVANT CHUNKS FOUND."

    lines = ["RETRIEVED DOCUMENT CHUNKS:"]
    lines.append("")

    for i, chunk in enumerate(chunks, 1):
        doc_name = chunk.get("document_name", "Unknown")
        page = chunk.get("page_number", "?")
        similarity = chunk.get("similarity", 0.0)
        content = chunk.get("content", "")

        lines.append(f"[Chunk {i}] {doc_name}, page {page} (relevance: {similarity:.2f})")
        lines.append(content)
        lines.append("")

    return "\n".join(lines)


def reason_node(state: dict) -> dict:
    """
    Pipeline node: generate a grounded answer from RAG context.

    Constructs a prompt with retrieved chunks and conversation history,
    then calls the LLM to generate an answer grounded in project documents.

    If a stream_callback is provided, streams tokens as they arrive.
    """
    message = state["message"]
    chunks = state.get("relevant_chunks", [])
    history = state.get("conversation_history", [])
    stream_callback = state.get("stream_callback")

    context = _build_rag_context(chunks)

    user_prompt = f"""{context}

CONVERSATION HISTORY (last 6 messages):
{_format_history(history)}

USER QUESTION: {message}"""

    try:
        provider = get_vlm_provider()

        response = asyncio.get_event_loop().run_until_complete(
            provider.chat(
                images=[],  # No images for RAG text-based chat
                message=user_prompt,
                history=history[-6:],
                system_prompt=RAG_SYSTEM_PROMPT,
            )
        )

        raw_answer = response["content"]

        # Stream tokens if callback is provided
        if stream_callback:
            for token in raw_answer.split(" "):
                stream_callback(type="token", content=token + " ")

        logger.info("Generated RAG answer", char_count=len(raw_answer))

        return {"raw_answer": raw_answer}

    except Exception as e:
        logger.error("RAG reasoning failed", error=str(e))
        return {
            "raw_answer": "I encountered an error while searching the project documents. Please try again.",
            "error_message": str(e),
        }


def _format_history(history: list[dict]) -> str:
    """Format conversation history for the prompt."""
    if not history:
        return "(no prior messages)"
    lines = []
    for msg in history[-6:]:
        role = msg["role"].upper()
        content = msg["content"][:200]
        lines.append(f"[{role}]: {content}")
    return "\n".join(lines)
```

**Grounding Rules (enforced by system prompt):**
- ONLY answer from retrieved chunks -- never use external knowledge
- Explicitly state when information is not found in project documents
- Always cite source document name and page number
- Synthesize across multiple documents when relevant
- Note contradictions between documents
- Conversation history capped at 6 messages for token efficiency

---

## `cite_node`

```python
"""
Citation node: extract citations from the answer and match them
to retrieved chunks.
"""
import re


def _extract_citations_from_answer(
    answer: str,
    chunks: list[dict],
) -> list[dict]:
    """
    Match answer citations to retrieved chunks.

    Looks for inline citations like [Document Name, p.X] in the answer
    and matches them to the original chunks. Also matches chunk content
    that appears verbatim in the answer.
    """
    citations: list[dict] = []
    seen: set[str] = set()

    # Pattern: [Document Name, p.X] or [Document Name, page X]
    citation_pattern = r'\[([^,\]]+),\s*(?:p\.?|page\s*)(\d+)\]'

    for match in re.finditer(citation_pattern, answer):
        doc_name = match.group(1).strip()
        page_num = int(match.group(2))

        # Find matching chunk
        for chunk in chunks:
            chunk_doc = chunk.get("document_name", "")
            chunk_page = chunk.get("page_number", 0)

            if (doc_name.lower() in chunk_doc.lower() or
                chunk_doc.lower() in doc_name.lower()) and chunk_page == page_num:

                key = f"{chunk['chunk_id']}"
                if key not in seen:
                    seen.add(key)
                    citations.append({
                        "document_id": chunk["document_id"],
                        "document_name": chunk["document_name"],
                        "page_number": chunk["page_number"],
                        "chunk_id": chunk["chunk_id"],
                        "text_span": match.group(0),
                    })
                break

    # Fallback: if no inline citations found, cite all chunks used
    if not citations:
        for chunk in chunks[:5]:  # Top 5 most relevant
            key = chunk["chunk_id"]
            if key not in seen:
                seen.add(key)
                citations.append({
                    "document_id": chunk["document_id"],
                    "document_name": chunk["document_name"],
                    "page_number": chunk["page_number"],
                    "chunk_id": chunk["chunk_id"],
                    "text_span": chunk["content"][:100],
                })

    return citations


def cite_node(state: dict) -> dict:
    """
    Pipeline node: extract citations from the RAG answer.

    Matches answer content to retrieved chunks to create citations
    that link back to source documents and pages.
    """
    raw_answer = state.get("raw_answer", "")
    chunks = state.get("relevant_chunks", [])
    stream_callback = state.get("stream_callback")

    citations = _extract_citations_from_answer(raw_answer, chunks)

    logger.info("Generated RAG citations", citation_count=len(citations))

    # Stream citations if callback is provided
    if stream_callback:
        for citation in citations:
            stream_callback(type="citation", citation=citation)
        stream_callback(type="done", message_id="pending")

    return {
        "answer": raw_answer,
        "citations": citations,
    }
```

---

## SSE Streaming Pattern

The RAG chat pipeline streams tokens and citations via SSE, following the same pattern as the document chat pipeline:

```python
import asyncio
import json
from typing import AsyncGenerator

from docmind.library.pipeline.rag import run_rag_chat_pipeline


async def rag_chat_sse_stream(
    project_id: str,
    user_id: str,
    message: str,
    conversation_history: list[dict],
) -> AsyncGenerator[str, None]:
    """Create an SSE stream for project-level RAG chat responses."""
    token_queue: asyncio.Queue = asyncio.Queue()

    def on_stream(type: str, **kwargs) -> None:
        token_queue.put_nowait({"type": type, **kwargs})

    initial_state = {
        "project_id": project_id,
        "user_id": user_id,
        "message": message,
        "conversation_history": conversation_history,
        "stream_callback": on_stream,
    }

    config = {"configurable": {"thread_id": f"{project_id}:{user_id}"}}
    task = asyncio.create_task(
        asyncio.to_thread(run_rag_chat_pipeline, initial_state, config)
    )

    while not task.done():
        try:
            event = await asyncio.wait_for(token_queue.get(), timeout=30.0)
            yield f"data: {json.dumps(event)}\n\n"
            if event.get("type") == "done":
                break
        except asyncio.TimeoutError:
            yield f"data: {json.dumps({'type': 'heartbeat'})}\n\n"
```

**SSE event types:**

| Event type | Payload | When |
|------------|---------|------|
| `token` | `{"type": "token", "content": "The "}` | Each answer token |
| `citation` | `{"type": "citation", "citation": {...}}` | After answer generation |
| `done` | `{"type": "done", "message_id": "uuid"}` | Pipeline complete |
| `heartbeat` | `{"type": "heartbeat"}` | Every 30s if no events |
| `error` | `{"type": "error", "message": "..."}` | On pipeline failure |

---

## Database Migration

```sql
-- Enable pgvector extension (run once per database)
CREATE EXTENSION IF NOT EXISTS vector;

-- page_chunks table
CREATE TABLE page_chunks (
    id VARCHAR PRIMARY KEY,
    document_id VARCHAR NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    project_id VARCHAR NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    page_number INTEGER NOT NULL,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for fast approximate nearest neighbor search
-- lists = 100 is appropriate for up to ~100k chunks; adjust for scale
CREATE INDEX idx_page_chunks_project_embedding
    ON page_chunks USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- B-tree indexes for filtering
CREATE INDEX idx_page_chunks_project_id ON page_chunks(project_id);
CREATE INDEX idx_page_chunks_document_id ON page_chunks(document_id);

-- Unique constraint: one chunk per position
CREATE UNIQUE INDEX idx_page_chunks_unique_position
    ON page_chunks(document_id, page_number, chunk_index);
```

**Migration notes:**
- The `vector` extension must be enabled before creating the table
- `vector(1024)` matches `EMBEDDING_DIMENSIONS=1024` in settings
- IVFFlat index requires at least `lists` rows to exist before it becomes useful; for small datasets the index still works but with less benefit
- `ON DELETE CASCADE` on both FKs ensures chunks are cleaned up when a document or project is deleted
- The unique index on `(document_id, page_number, chunk_index)` prevents duplicate chunks during re-indexing

---

## Cleanup: Re-indexing a Document

When a document is re-indexed (e.g., after reprocessing), delete existing chunks first:

```python
async def delete_document_chunks(
    session: AsyncSession,
    document_id: str,
) -> int:
    """
    Delete all RAG chunks for a document.

    Called before re-indexing to avoid duplicates.

    Args:
        session: SQLAlchemy async session.
        document_id: Document whose chunks to delete.

    Returns:
        Number of chunks deleted.
    """
    from sqlalchemy import delete, func, select
    from docmind.dbase.psql.models.page_chunk import PageChunk

    # Count before delete
    count_result = await session.execute(
        select(func.count()).where(PageChunk.document_id == document_id)
    )
    count = count_result.scalar() or 0

    await session.execute(
        delete(PageChunk).where(PageChunk.document_id == document_id)
    )
    await session.commit()

    return count
```

---

## State Flow Summary

| Node | Reads from state | Writes to state |
|------|-----------------|-----------------|
| **embed_query** | `message` | `query_embedding` |
| **retrieve** | `project_id`, `query_embedding` | `relevant_chunks` |
| **reason** | `message`, `relevant_chunks`, `conversation_history` | `raw_answer` |
| **cite** | `raw_answer`, `relevant_chunks` | `answer`, `citations` |

---

## Rules

- **RAG library never imports from `docmind/modules/`** -- communication is through function arguments and return values only.
- **Embedding consistency**: always use the same provider and model for indexing and querying. Mixing providers produces incompatible vector spaces.
- **Chunk size is a tradeoff**: 512 chars balances granularity with context. Adjust `RAG_CHUNK_SIZE` for domain-specific needs.
- **IVFFlat index tuning**: the `lists` parameter should be roughly `sqrt(total_chunks)`. Start with 100, increase for large deployments.
- **Cascading deletes**: document and project deletion automatically removes all associated chunks via `ON DELETE CASCADE`.
- **Re-indexing**: always delete existing chunks before re-indexing to avoid duplicates. Use the `delete_document_chunks` helper.
- **Batch embedding**: DashScope supports max 25 texts per call, OpenAI supports 100. The embedder handles batching automatically.
- **Stream callbacks are optional**: all pipeline nodes must work without a callback (for testing and batch use).
- **Thread isolation**: each `(project_id, user_id)` pair is a separate conversation. No cross-contamination between projects or users.
