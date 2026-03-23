"""
docmind/router.py

Aggregates all module routers under versioned prefixes.
"""

from fastapi import APIRouter

from .modules.chat.apiv1.handler import router as chat_router
from .modules.documents.apiv1.handler import router as documents_router
from .modules.extractions.apiv1.handler import router as extractions_router
from .modules.health.apiv1.handler import router as health_router
from .modules.personas.apiv1.handler import router as personas_router
from .modules.projects.apiv1.handler import router as projects_router
from .modules.templates.apiv1.handler import router as templates_router
from .modules.analytics.apiv1.handler import router as analytics_router

api_router = APIRouter()

api_router.include_router(health_router, prefix="/v1/health", tags=["Health"])
api_router.include_router(documents_router, prefix="/v1/documents", tags=["Documents"])
api_router.include_router(
    extractions_router, prefix="/v1/extractions", tags=["Extractions"]
)
api_router.include_router(chat_router, prefix="/v1/chat", tags=["Chat"])
api_router.include_router(templates_router, prefix="/v1/templates", tags=["Templates"])
api_router.include_router(projects_router, prefix="/v1/projects", tags=["Projects"])
api_router.include_router(personas_router, prefix="/v1/personas", tags=["Personas"])
api_router.include_router(analytics_router, prefix="/v1/analytics", tags=["Analytics"])
