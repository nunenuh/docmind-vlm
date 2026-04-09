"""DI factory functions for templates module — used via FastAPI Depends()."""

from .usecase import TemplateUseCase


def get_template_usecase() -> TemplateUseCase:
    return TemplateUseCase()
