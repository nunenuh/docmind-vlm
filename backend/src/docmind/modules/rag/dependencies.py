"""DI factory functions for RAG module — used via FastAPI Depends()."""

from .usecase import RAGUseCase


def get_rag_usecase() -> RAGUseCase:
    return RAGUseCase()
