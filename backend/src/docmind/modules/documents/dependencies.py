"""DI factory functions for documents module — used via FastAPI Depends()."""

from .usecase import DocumentUseCase


def get_document_usecase() -> DocumentUseCase:
    return DocumentUseCase()
