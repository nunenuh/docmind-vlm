"""RAG pipeline library.

Provides text extraction, chunking, embedding, retrieval, and indexing
for the Knowledge Base / RAG chat feature.
"""

from .chunker import chunk_pages, chunk_text
from .embedder import embed_texts
from .indexer import delete_document_chunks, index_document
from .retriever import retrieve_similar_chunks
from .text_extract import extract_text, extract_text_from_image, extract_text_from_pdf

__all__ = [
    "chunk_pages",
    "chunk_text",
    "delete_document_chunks",
    "embed_texts",
    "extract_text",
    "extract_text_from_image",
    "extract_text_from_pdf",
    "index_document",
    "retrieve_similar_chunks",
]
