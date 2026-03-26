"""DI factory functions for analytics module — used via FastAPI Depends()."""

from .usecase import AnalyticsUseCase


def get_analytics_usecase() -> AnalyticsUseCase:
    return AnalyticsUseCase()
