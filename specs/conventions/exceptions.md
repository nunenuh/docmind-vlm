# Exception Handling Standard

## Principle

Every layer raises its own exception type. The handler catches and maps to HTTP response. No raw `HTTPException` in handlers — use `AppException` or let the global handler catch layer exceptions.

This way, when an error occurs, you immediately know **which layer** caused it.

---

## Exception Hierarchy

```
BaseAppException (base for all custom exceptions)
├── AppException              ← handler/API level (status_code + message)
├── UseCaseException          ← business logic errors
│   ├── NotFoundException     ← resource not found
│   ├── ValidationException   ← business rule violated
│   ├── AuthorizationException← user not allowed
│   └── ConflictException     ← duplicate/conflict
├── ServiceException          ← service layer errors (VLM, RAG, external API)
│   ├── ProviderException     ← VLM/embedding provider failed
│   ├── StorageException      ← file storage failed
│   └── IndexingException     ← RAG indexing failed
└── RepositoryException       ← database errors
    ├── DatabaseException     ← query/connection failed
    └── RecordNotFoundException ← specific record not found in DB
```

---

## Exception Class Design

```python
class BaseAppException(Exception):
    """Base for all application exceptions."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)
```

Every exception carries:
- `message` — human-readable error description
- `code` — machine-readable error code (e.g., `NOT_FOUND`, `VALIDATION_ERROR`)
- `status_code` — HTTP status code for the response

---

## Which Layer Raises What

### Repository Layer
```python
class DocumentRepository:
    async def get_by_id(self, document_id: str, user_id: str) -> Document:
        # Raises RecordNotFoundException if not found
        # Raises DatabaseException if query fails
        # NEVER returns None for required records
```

### Service Layer
```python
class ChatService:
    async def stream_chat(self, ...):
        # Raises ProviderException if VLM call fails
        # Raises ServiceException for other service failures
```

### UseCase Layer
```python
class DocumentUseCase:
    async def get_document(self, user_id: str, document_id: str) -> Document:
        # Raises NotFoundException if doc not found
        # Raises AuthorizationException if user doesn't own doc
        # Raises ValidationException if input is invalid
```

### Handler Layer
```python
@router.get("/{document_id}")
async def get_document(document_id: str, current_user = Depends(get_current_user)):
    try:
        usecase = DocumentUseCase()
        return await usecase.get_document(
            user_id=current_user["id"],
            document_id=document_id,
        )
    except NotFoundException as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValidationException as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
```

---

## Global Exception Handler

In `main.py`, catch any custom exception that leaks past the handler:

```python
@app.exception_handler(BaseAppException)
async def app_exception_handler(request: Request, exc: BaseAppException):
    """Catches any custom exception not handled by the endpoint."""
    logger.error("%s: %s", exc.__class__.__name__, exc.message, exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message},
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Last resort — unhandled exceptions."""
    logger.error("Unhandled: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
```

---

## Exception → HTTP Status Mapping

| Exception | Status | Code |
|-----------|--------|------|
| `NotFoundException` | 404 | `NOT_FOUND` |
| `ValidationException` | 422 | `VALIDATION_ERROR` |
| `AuthorizationException` | 403 | `FORBIDDEN` |
| `ConflictException` | 409 | `CONFLICT` |
| `ProviderException` | 502 | `PROVIDER_ERROR` |
| `StorageException` | 503 | `STORAGE_ERROR` |
| `IndexingException` | 500 | `INDEXING_ERROR` |
| `DatabaseException` | 500 | `DATABASE_ERROR` |
| `AppException` | varies | varies |
| `Exception` (unhandled) | 500 | `INTERNAL_ERROR` |

---

## Rules

- **Handler**: catches usecase exceptions, wraps in `AppException` or lets global handler catch
- **UseCase**: raises `UseCaseException` subtypes (`NotFoundException`, `ValidationException`)
- **Service**: raises `ServiceException` subtypes (`ProviderException`, `StorageException`)
- **Repository**: raises `RepositoryException` subtypes (`DatabaseException`, `RecordNotFoundException`)
- **NEVER** raise raw `HTTPException` — always use custom exceptions
- **NEVER** return `None` for missing records — raise `NotFoundException`
- **NEVER** swallow exceptions silently — always log and re-raise
- Repository exceptions should NOT leak SQL/DB details to the client — generic message in response, details in server logs
