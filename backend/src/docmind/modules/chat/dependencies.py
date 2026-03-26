"""DI factory functions for chat module — used via FastAPI Depends()."""

from .usecase import ChatUseCase


def get_chat_usecase() -> ChatUseCase:
    return ChatUseCase()
