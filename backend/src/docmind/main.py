"""
docmind/main.py

FastAPI app factory. Configures CORS, registers routers, manages lifecycle.
"""

import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .core.config import get_settings
from .core.logging import setup_logging
from .router import api_router

logger = logging.getLogger(__name__)


def get_docs_path():
    """Get docs path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/docs"
    return None


def get_redoc_path():
    """Get redoc path based on environment."""
    settings = get_settings()
    if settings.APP_ENVIRONMENT in ["development", "local", "staging"]:
        return "/redoc"
    return None


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()
    setup_logging()

    application = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        docs_url=get_docs_path(),
        redoc_url=get_redoc_path(),
        debug=settings.APP_DEBUG,
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    application.include_router(api_router, prefix="/api")

    @application.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Catch unhandled exceptions and return proper JSON with CORS headers."""
        logger.error("Unhandled exception: %s", exc, exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"},
        )

    return application


app = create_app()


def main():
    """Entry point for poetry run start."""
    settings = get_settings()
    uvicorn.run(
        "docmind.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
    )


def dev():
    """Entry point for poetry run dev."""
    settings = get_settings()
    uvicorn.run(
        "docmind.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
    )
