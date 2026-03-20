"""Text chunking with sentence-boundary awareness.

Splits text into fixed-size chunks with overlap, respecting sentence boundaries
where possible. Used by the RAG indexing pipeline.
"""

from __future__ import annotations

import re


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into chunks of approximately chunk_size characters.

    Uses sentence boundaries to avoid splitting mid-sentence. Each chunk
    includes `overlap` characters of context from the previous chunk.

    Args:
        text: The input text to chunk.
        chunk_size: Target chunk size in characters.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of chunk strings. Empty list if text is empty/whitespace.
    """
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    # Split into sentences using common delimiters
    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        # If adding this sentence would exceed chunk_size, finalize current chunk
        if current_chunk and len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(current_chunk.strip())

            # Start new chunk with overlap from end of previous chunk
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + " " + sentence
            else:
                current_chunk = sentence
        else:
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence

    # Don't forget the last chunk
    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def chunk_pages(
    pages: list[dict], chunk_size: int = 512, overlap: int = 64
) -> list[dict]:
    """Chunk all pages into indexed chunks.

    Args:
        pages: List of {"page_number": int, "text": str} dicts.
        chunk_size: Target chunk size in characters.
        overlap: Number of characters to overlap between chunks.

    Returns:
        List of {"page_number": int, "chunk_index": int, "content": str} dicts.
    """
    result: list[dict] = []
    global_index = 0

    for page in pages:
        text = page.get("text", "").strip()
        if not text:
            continue

        chunks = chunk_text(text, chunk_size=chunk_size, overlap=overlap)
        for chunk_content in chunks:
            result.append(
                {
                    "page_number": page["page_number"],
                    "chunk_index": global_index,
                    "content": chunk_content,
                }
            )
            global_index += 1

    return result
