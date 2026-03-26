"""DI factory functions for projects module — used via FastAPI Depends()."""

from .usecases import (
    ProjectChatUseCase,
    ProjectConversationUseCase,
    ProjectCRUDUseCase,
    ProjectDocumentUseCase,
)


def get_project_crud_usecase() -> ProjectCRUDUseCase:
    return ProjectCRUDUseCase()


def get_project_document_usecase() -> ProjectDocumentUseCase:
    return ProjectDocumentUseCase()


def get_project_conversation_usecase() -> ProjectConversationUseCase:
    return ProjectConversationUseCase()


def get_project_chat_usecase() -> ProjectChatUseCase:
    return ProjectChatUseCase()
