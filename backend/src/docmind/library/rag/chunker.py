"""Page-level contextual chunking for RAG v2.

Strategy (production-level):
1. Keep full pages together when under threshold (preserves context)
2. Split only pages that exceed threshold by headers then sentences
3. Prepend contextual header: [Document: X] [Page: N/M] [Section: Y]
4. Adaptive chunk size by document type (resume/contract/report)
5. Store both contextualized content (for embedding) and raw content (for BM25)

This solves the "Bima Jaya" problem — full page context prevents
hallucination from isolated fragments.
"""

from __future__ import annotations

import hashlib
import re
from typing import Any

from docmind.core.config import get_settings


# --- Adaptive chunk profiles by document type ---

CHUNK_PROFILES: dict[str, dict[str, int]] = {
    "resume": {"chunk_size": 1500, "threshold": 2000, "overlap": 200},
    "contract": {"chunk_size": 2000, "threshold": 2500, "overlap": 300},
    "report": {"chunk_size": 1200, "threshold": 1500, "overlap": 200},
    "spreadsheet": {"chunk_size": 800, "threshold": 1000, "overlap": 100},
    "default": {"chunk_size": 1200, "threshold": 1500, "overlap": 200},
}


def detect_document_profile(pages: list[dict], filename: str) -> str:
    """Detect document type for adaptive chunk sizing.

    Uses filename heuristics + first-page content analysis.

    Args:
        pages: Extracted page dicts.
        filename: Original filename.

    Returns:
        Profile name: "resume", "contract", "report", "spreadsheet", or "default".
    """
    name_lower = filename.lower()

    if any(kw in name_lower for kw in ["resume", "cv", "curriculum", "vitae"]):
        return "resume"
    if any(kw in name_lower for kw in ["contract", "agreement", "nda", "terms", "lease"]):
        return "contract"
    if any(kw in name_lower for kw in ["report", "analysis", "summary", "review"]):
        return "report"
    if any(kw in name_lower for kw in ["sheet", "spreadsheet", "data", "table"]):
        return "spreadsheet"

    # Content-based detection from first page
    if pages:
        first_page = pages[0].get("text", "").lower()
        if any(kw in first_page for kw in ["experience", "education", "skills", "objective", "employment"]):
            return "resume"
        if any(kw in first_page for kw in ["whereas", "hereby", "parties", "clause", "agreement"]):
            return "contract"

    return "default"


def _content_hash(text: str) -> str:
    """SHA-256 hash of normalized text for duplicate detection.

    Args:
        text: Raw text content.

    Returns:
        64-character hex hash string.
    """
    normalized = " ".join(text.lower().split())
    return hashlib.sha256(normalized.encode()).hexdigest()


def _split_by_sentences(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text by sentence boundaries with overlap.

    Args:
        text: Text to split.
        chunk_size: Target chunk size in characters.
        overlap: Overlap between consecutive chunks.

    Returns:
        List of chunk strings.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    sentences = re.split(r"(?<=[.!?])\s+", text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if current and len(current) + len(sentence) + 1 > chunk_size:
            chunks.append(current.strip())
            if overlap > 0 and len(current) > overlap:
                current = current[-overlap:] + " " + sentence
            else:
                current = sentence
        else:
            current = (current + " " + sentence).strip() if current else sentence

    if current.strip():
        chunks.append(current.strip())

    return chunks


def _split_by_headers(text: str) -> list[dict]:
    """Split Markdown text by headers into sections.

    Args:
        text: Markdown-formatted text.

    Returns:
        List of {"header": str, "level": int, "content": str} dicts.
    """
    lines = text.split("\n")
    sections: list[dict] = []
    current_header = ""
    current_level = 0
    current_lines: list[str] = []

    for line in lines:
        header_match = re.match(r"^(#{1,6})\s+(.+)", line.strip())
        if header_match:
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

    if current_lines:
        content = "\n".join(current_lines).strip()
        if content:
            sections.append({
                "header": current_header,
                "level": current_level,
                "content": content,
            })

    if not sections and text.strip():
        sections.append({"header": "", "level": 0, "content": text.strip()})

    return sections


def _build_contextual_header(
    filename: str,
    page_number: int,
    total_pages: int,
    section_header: str = "",
) -> str:
    """Build contextual header for a chunk.

    Args:
        filename: Document filename.
        page_number: Current page number.
        total_pages: Total pages in document.
        section_header: Section header (if any).

    Returns:
        Contextual header string.
    """
    parts = [f"[Document: {filename}]"]
    parts.append(f"[Page: {page_number}/{total_pages}]")
    if section_header:
        parts.append(f"[Section: {section_header}]")
    return "\n".join(parts)


def chunk_pages(
    pages: list[dict],
    chunk_size: int | None = None,
    overlap: int | None = None,
    doc_context: str = "",
    page_chunk_threshold: int | None = None,
) -> list[dict]:
    """Chunk pages with page-level preservation and contextual headers.

    Strategy:
    1. Detect document type for adaptive chunk sizing
    2. For each page: keep whole if under threshold, split if over
    3. Prepend contextual header with document name, page, section
    4. Generate content hash for duplicate detection

    Args:
        pages: List of {"page_number": int, "text": str, "headers": list} dicts.
        chunk_size: Override chunk size (uses config default if None).
        overlap: Override overlap (uses config default if None).
        doc_context: Document filename for context headers.
        page_chunk_threshold: Override threshold for page-level chunking.

    Returns:
        List of chunk dicts with content, raw_content, page_number,
        chunk_index, section_header, and content_hash.
    """
    settings = get_settings()

    # Adaptive sizing
    profile_name = detect_document_profile(pages, doc_context)
    profile = CHUNK_PROFILES[profile_name]

    effective_chunk_size = chunk_size or profile["chunk_size"]
    effective_overlap = overlap or profile["overlap"]
    effective_threshold = page_chunk_threshold or profile["threshold"]

    total_pages = len(pages)
    result: list[dict] = []
    global_index = 0

    for page in pages:
        text = page.get("text", "").strip()
        if not text:
            continue

        page_number = page["page_number"]

        if len(text) <= effective_threshold:
            # Page-level chunk — keep whole page together
            section_headers = page.get("headers", [])
            primary_header = section_headers[0] if section_headers else ""

            header = _build_contextual_header(
                doc_context, page_number, total_pages, primary_header
            )
            contextualized = f"{header}\n{text}"

            result.append({
                "page_number": page_number,
                "chunk_index": global_index,
                "content": contextualized,
                "raw_content": text,
                "section_header": primary_header,
                "content_hash": _content_hash(text),
            })
            global_index += 1
        else:
            # Page too large — split by headers then sentences
            sections = _split_by_headers(text)

            for section in sections:
                section_header = section["header"]
                section_content = section["content"]

                sub_chunks = _split_by_sentences(
                    section_content, effective_chunk_size, effective_overlap
                )

                for raw_chunk in sub_chunks:
                    header = _build_contextual_header(
                        doc_context, page_number, total_pages, section_header
                    )
                    contextualized = f"{header}\n{raw_chunk}"

                    result.append({
                        "page_number": page_number,
                        "chunk_index": global_index,
                        "content": contextualized,
                        "raw_content": raw_chunk,
                        "section_header": section_header,
                        "content_hash": _content_hash(raw_chunk),
                    })
                    global_index += 1

    return result


# Keep old function for backward compatibility
def chunk_text(text: str, chunk_size: int = 512, overlap: int = 64) -> list[str]:
    """Legacy function — split text by sentences with overlap."""
    return _split_by_sentences(text, chunk_size, overlap)
