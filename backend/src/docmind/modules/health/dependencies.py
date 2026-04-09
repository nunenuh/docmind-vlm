"""DI factory functions for health module — used via FastAPI Depends()."""

from .usecase import HealthUseCase


def get_health_usecase() -> HealthUseCase:
    return HealthUseCase()
