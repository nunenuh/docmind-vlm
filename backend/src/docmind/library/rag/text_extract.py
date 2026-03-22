"""Text extraction from documents.

Uses pymupdf4llm for high-quality Markdown extraction from PDFs,
preserving headers, tables, lists, and document structure.
Images return empty text — VLM handles image understanding.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def extract_text_from_pdf(file_bytes: bytes) -> list[dict]:
    """Extract structured Markdown text from PDF using pymupdf4llm.

    Preserves document structure: headers, tables, lists, bold/italic.
    Falls back to raw fitz extraction if pymupdf4llm fails.

    Args:
        file_bytes: Raw PDF bytes.

    Returns:
        List of dicts per page:
        {
            "page_number": int,
            "text": str (Markdown-formatted),
            "headers": list[str] (section headers found on this page),
        }
    """
    try:
        import pymupdf4llm

        import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        page_count = len(doc)
        doc.close()

        # Extract per-page using pymupdf4llm page_chunks
        page_chunks = pymupdf4llm.to_markdown(
            file_bytes, page_chunks=True, show_progress=False
        )

        pages: list[dict] = []
        for i, chunk in enumerate(page_chunks):
            text = chunk.get("text", "")

            # Extract headers from markdown
            headers = _extract_headers(text)

            pages.append({
                "page_number": i + 1,
                "text": text,
                "headers": headers,
            })

        # If pymupdf4llm returned fewer pages, pad with empty
        while len(pages) < page_count:
            pages.append({
                "page_number": len(pages) + 1,
                "text": "",
                "headers": [],
            })

        return pages

    except Exception as e:
        logger.warning(
            "pymupdf4llm extraction failed, falling back to raw fitz: %s", e
        )
        return _extract_text_fallback(file_bytes)


def _extract_text_fallback(file_bytes: bytes) -> list[dict]:
    """Fallback raw text extraction using fitz."""
    import fitz

    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[dict] = []
    for i, page in enumerate(doc):
        text = page.get_text()
        pages.append({
            "page_number": i + 1,
            "text": text,
            "headers": _extract_headers(text),
        })
    doc.close()
    return pages


def _extract_headers(text: str) -> list[str]:
    """Extract Markdown headers from text.

    Args:
        text: Markdown-formatted text.

    Returns:
        List of header strings (without # prefix).
    """
    import re

    headers = []
    for line in text.split("\n"):
        match = re.match(r"^(#{1,6})\s+(.+)", line.strip())
        if match:
            headers.append(match.group(2).strip())
    return headers


def extract_text_from_image(file_bytes: bytes) -> list[dict]:
    """Fallback for images — returns empty text, VLM will handle.

    Args:
        file_bytes: Raw image bytes (unused).

    Returns:
        Single-page list with empty text.
    """
    return [{"page_number": 1, "text": "", "headers": []}]


def extract_text(file_bytes: bytes, file_type: str) -> list[dict]:
    """Route to appropriate text extractor based on file type.

    Args:
        file_bytes: Raw file bytes.
        file_type: File extension/type (e.g. "pdf", "png", "jpg").

    Returns:
        List of page dicts with text, page_number, and headers.
    """
    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)
    return extract_text_from_image(file_bytes)
