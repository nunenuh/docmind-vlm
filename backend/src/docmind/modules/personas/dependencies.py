"""DI factory functions for personas module — used via FastAPI Depends()."""

from .usecase import PersonaUseCase


def get_persona_usecase() -> PersonaUseCase:
    return PersonaUseCase()
