"""
docmind/modules/rag/

Independent RAG module — provides indexing, retrieval, and query services
that any module can consume without cross-module dependencies.

This is a service-only module (no HTTP handler/API routes).
Other modules import from here instead of reaching into library/rag directly.
"""
