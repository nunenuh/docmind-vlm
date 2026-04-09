# Logging Standard

## Principle

Logs should be **beautiful in development** (colored, readable, aligned) and **structured in production** (JSON, parseable, queryable). Every request gets a unique ID for tracing.

---

## Development Output (what you see in terminal)

```
2026-03-24T12:00:01 [info     ] Server started                  port=8009
2026-03-24T12:00:05 [info     ] ← POST /api/v1/documents 201   request_id=a1b2c3 duration=245ms user_id=51091692
2026-03-24T12:00:05 [info     ] Document uploaded                request_id=a1b2c3 filename=ktp.jpg file_size=423696
2026-03-24T12:00:06 [warning  ] Auto-classify failed             request_id=a1b2c3 error="timeout"
2026-03-24T12:00:10 [info     ] ← GET /api/v1/documents 200     request_id=d4e5f6 duration=12ms user_id=51091692
2026-03-24T12:00:15 [error    ] Storage upload failed            request_id=g7h8i9 error="Bucket not found"
```

Key properties:
- **Colored** — info=green, warning=yellow, error=red
- **Aligned** — log level padded to same width
- **Timestamp** — ISO format, no date in dev (just time)
- **Request ID** — short 8-char UUID prefix on every log within a request
- **Duration** — on request/response logs
- **No SQL noise** — SQLAlchemy at WARNING level unless DEBUG mode

---

## Production Output (JSON)

```json
{"timestamp":"2026-03-24T12:00:05Z","level":"info","event":"request_completed","request_id":"a1b2c3d4","method":"POST","path":"/api/v1/documents","status":201,"duration_ms":245,"user_id":"51091692"}
```

---

## Components

### 1. Request ID Middleware

Every incoming request gets a unique ID. If the client sends `X-Request-ID` header, use that (for distributed tracing). Otherwise generate a UUID.

```python
# core/middleware.py

import uuid
import structlog
from starlette.middleware.base import BaseHTTPMiddleware

class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:8])

        # Bind to structlog context — all logs within this request get the ID
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
```

### 2. Request Logging Middleware

Log every request with method, path, status code, and duration.

```python
# core/middleware.py

import time

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = int((time.perf_counter() - start) * 1000)

        logger.info(
            "request_completed",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms,
        )
        return response
```

### 3. Structlog Configuration

```python
# core/logging.py

def setup_logging():
    settings = get_settings()

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.APP_ENVIRONMENT == "development":
        # Beautiful colored console output
        renderer = structlog.dev.ConsoleRenderer(
            colors=True,
            pad_event=40,  # align key=value pairs
        )
    else:
        # JSON for production log aggregators
        renderer = structlog.processors.JSONRenderer()

    shared_processors.append(renderer)

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Silence noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
```

### 4. Middleware Registration in main.py

```python
def create_app():
    app = FastAPI(...)

    # Order matters — RequestID first, then logging
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestIDMiddleware)

    return app
```

---

## Logging Rules

### What to log

| Level | When |
|-------|------|
| **DEBUG** | Detailed internal state (SQL queries, embeddings, chunk details) |
| **INFO** | Normal operations (request completed, document uploaded, indexing done) |
| **WARNING** | Recoverable issues (auto-classify failed, retry succeeded, fallback used) |
| **ERROR** | Failed operations (VLM call failed, DB connection lost, storage error) |

### How to log

```python
# GOOD — structured key=value
logger.info("document_uploaded", filename="ktp.jpg", file_size=423696, user_id="abc")

# BAD — unstructured string formatting
logger.info(f"Document {filename} uploaded by user {user_id}, size: {file_size}")
```

### What NOT to log

- Secrets (API keys, passwords, tokens)
- Full file contents or embeddings
- PII in production (redact user data)
- Every SQL query (use DEBUG level only)

---

## Log Levels per Layer

| Layer | Typical logs |
|-------|-------------|
| **Handler** | request_completed (auto via middleware) |
| **UseCase** | Business events: document_uploaded, extraction_started, chat_completed |
| **Service** | External calls: vlm_call_started, embedding_completed, storage_uploaded |
| **Repository** | Only errors: db_query_failed, record_not_found |
| **Library** | Processing details at DEBUG: chunk_created, confidence_merged |

---

## Files to create/modify

| File | Change |
|------|--------|
| `core/middleware.py` | NEW — RequestIDMiddleware + RequestLoggingMiddleware |
| `core/logging.py` | Update — silence noisy loggers, pad console output |
| `main.py` | Add middleware registration |

---

## Skip paths (don't log)

Health check endpoints generate noise. Skip logging for:
- `GET /api/v1/health/ping`
- `GET /api/v1/health/status`
- `GET /favicon.ico`
