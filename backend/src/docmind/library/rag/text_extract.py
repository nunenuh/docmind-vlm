"""Text extraction from documents.

Extracts raw text from PDF pages using PyMuPDF (fitz).
Images return empty text — VLM handles image understanding.
"""

from __future__ import annotations

import fitz


def extract_text_from_pdf(file_bytes: bytes) -> list[dict]:
    """Extract text from PDF using PyMuPDF (fitz).

    Args:
        file_bytes: Raw PDF bytes.

    Returns:
        List of {"page_number": int, "text": str} dicts, one per page.
    """
    doc = fitz.open(stream=file_bytes, filetype="pdf")
    pages: list[dict] = []
    for i, page in enumerate(doc):
        pages.append({"page_number": i + 1, "text": page.get_text()})
    doc.close()
    return pages


def extract_text_from_image(file_bytes: bytes) -> list[dict]:
    """Fallback for images — returns empty text, VLM will handle.

    Args:
        file_bytes: Raw image bytes (unused).

    Returns:
        Single-page list with empty text.
    """
    return [{"page_number": 1, "text": ""}]


def extract_text(file_bytes: bytes, file_type: str) -> list[dict]:
    """Route to appropriate text extractor based on file type.

    Args:
        file_bytes: Raw file bytes.
        file_type: File extension/type (e.g. "pdf", "png", "jpg").

    Returns:
        List of {"page_number": int, "text": str} dicts.
    """
    if file_type == "pdf":
        return extract_text_from_pdf(file_bytes)
    return extract_text_from_image(file_bytes)
