"""Header-aware contextual text chunking for RAG.

Two-stage chunking strategy (2026 best practice):
1. Split by document structure (Markdown headers) first
2. Then recursive split within sections by sentence boundaries

Each chunk is enriched with its section context (header path)
so it's self-contained for retrieval.
"""

from __future__ import annotations

import re


def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Split text into chunks using sentence boundaries with overlap.

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

    sentences = re.split(r"(?<=[.!?])\s+", text)

    chunks: list[str] = []
    current_chunk = ""

    for sentence in sentences:
        if current_chunk and len(current_chunk) + len(sentence) + 1 > chunk_size:
            chunks.append(current_chunk.strip())
            if overlap > 0 and len(current_chunk) > overlap:
                current_chunk = current_chunk[-overlap:] + " " + sentence
            else:
                current_chunk = sentence
        else:
            current_chunk = (current_chunk + " " + sentence).strip() if current_chunk else sentence

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return chunks


def _split_by_headers(text: str) -> list[dict]:
    """Split Markdown text by headers into sections.

    Args:
        text: Markdown-formatted text.

    Returns:
        List of {"header": str, "level": int, "content": str} dicts.
        Content between headers is grouped under the preceding header.
    """
    lines = text.split("\n")
    sections: list[dict] = []
    current_header = ""
    current_level = 0
    current_lines: list[str] = []

    for line in lines:
        header_match = re.match(r"^(#{1,6})\s+(.+)", line.strip())
        if header_match:
            # Save previous section
            if current_lines:
                content = "\n".join(current_lines).strip()
                if content:
                    sections.append({
                        "header": current_header,
                        "level": current_level,
                        "content": content,
                    })
            current_header = header_match.group(2).strip()
            current_level = len(header_match.group(1))
            current_lines = []
        else:
            current_lines.append(line)

    # Last section
    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({
                "header": current_header,
                "level": current_level,
                "content": content,
            })

    # If no headers found, return entire text as one section
    if not sections and text.strip():
        sections.append({
            "header": "",
            "level": 0,
            "content": text.strip(),
        })

    return sections


def _contextualize_chunk(chunk_text: str, section_header: str, doc_context: str = "") -> str:
    """Prepend section context to a chunk for self-contained retrieval.

    Args:
        chunk_text: The raw chunk text.
        section_header: The header of the section this chunk belongs to.
        doc_context: Optional document-level context (e.g. filename).

    Returns:
        Contextualized chunk string.
    """
    parts: list[str] = []
    if doc_context:
        parts.append(f"[Document: {doc_context}]")
    if section_header:
        parts.append(f"[Section: {section_header}]")
    parts.append(chunk_text)
    return "\n".join(parts)


def chunk_pages(
    pages: list[dict],
    chunk_size: int = 512,
    overlap: int = 64,
    doc_context: str = "",
) -> list[dict]:
    """Chunk all pages with header-aware splitting and contextual enrichment.

    Strategy:
    1. For each page, split by Markdown headers into sections
    2. Within each section, recursive split by sentences
    3. Prepend section header to each chunk for context

    Args:
        pages: List of {"page_number": int, "text": str, "headers": list} dicts.
        chunk_size: Target chunk size in characters.
        overlap: Number of characters to overlap between chunks.
        doc_context: Optional document name for context prefix.

    Returns:
        List of dicts:
        {
            "page_number": int,
            "chunk_index": int,
            "content": str (contextualized),
            "section_header": str,
            "raw_content": str (without context prefix),
        }
    """
    result: list[dict] = []
    global_index = 0

    for page in pages:
        text = page.get("text", "").strip()
        if not text:
            continue

        page_number = page["page_number"]

        # Stage 1: Split by headers
        sections = _split_by_headers(text)

        for section in sections:
            header = section["header"]
            content = section["content"]

            # Stage 2: Recursive split within section
            chunks = chunk_text(content, chunk_size=chunk_size, overlap=overlap)

            for raw_chunk in chunks:
                # Stage 3: Contextualize
                contextualized = _contextualize_chunk(
                    raw_chunk, header, doc_context
                )

                result.append({
                    "page_number": page_number,
                    "chunk_index": global_index,
                    "content": contextualized,
                    "section_header": header,
                    "raw_content": raw_chunk,
                })
                global_index += 1

    return result
