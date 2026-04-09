"""
docmind/core/middleware.py

Request ID and request logging middleware.
Every request gets a unique ID for tracing across all log lines.
"""

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger(__name__)

# Paths to skip logging (noisy health checks, static assets)
SKIP_PATHS = frozenset({
    "/api/v1/health/ping",
    "/api/v1/health/status",
    "/favicon.ico",
    "/docs",
    "/redoc",
    "/openapi.json",
})


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Assigns a unique request ID to every request.

    If the client sends X-Request-ID, reuse it (distributed tracing).
    Otherwise generate a short UUID. Binds it to structlog context
    so all logs within the request include request_id.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("X-Request-ID")
        if not request_id:
            request_id = str(uuid.uuid4())[:8]

        # Bind to structlog context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        # Store on request state for access in handlers
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs every request with method, path, status, and duration.

    Skips health check and static asset paths.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        path = request.url.path

        # Skip noisy paths
        if path in SKIP_PATHS:
            return await call_next(request)

        start = time.perf_counter()

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.error(
                "request_failed",
                method=request.method,
                path=path,
                duration_ms=duration_ms,
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)

        # Choose log level based on status code
        status = response.status_code
        log_fn = logger.info
        if status >= 500:
            log_fn = logger.error
        elif status >= 400:
            log_fn = logger.warning

        log_fn(
            "request_completed",
            method=request.method,
            path=path,
            status=status,
            duration_ms=duration_ms,
        )

        return response
