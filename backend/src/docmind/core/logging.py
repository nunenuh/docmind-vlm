"""
docmind/core/logging.py

Structlog setup — beautiful colored output in dev, JSON in production.
All logs within a request include request_id via contextvars.
"""

import logging
import sys

import structlog

from docmind.core.config import get_settings


def setup_logging() -> None:
    """Configure structlog and standard library logging."""
    settings = get_settings()
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    # Standard library base config
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Silence noisy third-party loggers
    noisy_loggers = [
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "sqlalchemy.engine.Engine",
        "httpx",
        "httpcore",
        "watchfiles",
    ]
    for name in noisy_loggers:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Keep SQLAlchemy SQL at DEBUG only if explicitly requested
    if settings.LOG_LEVEL.upper() == "DEBUG":
        logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.INFO)

    # Shared processors (run in order)
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.APP_ENVIRONMENT in ("development", "local"):
        # Beautiful colored console output with aligned columns
        shared_processors.append(
            structlog.dev.ConsoleRenderer(
                colors=True,
                pad_event=42,
            )
        )
    else:
        # JSON for production log aggregators
        shared_processors.append(
            structlog.processors.JSONRenderer()
        )

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger bound with the module name."""
    return structlog.get_logger(name)
