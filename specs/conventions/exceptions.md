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

## Standard Error Response

All errors return the same JSON shape:

```json
{
    "success": false,
    "error": {
        "code": "NOT_FOUND",
        "message": "Document not found",
        "layer": "usecase"
    }
}
```

Success responses:

```json
{
    "success": true,
    "data": { ... }
}
```

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
        document = await usecase.get_document(
            user_id=current_user["id"],
            document_id=document_id,
        )
        return {"success": True, "data": document}
    except NotFoundException as e:
        raise AppException(status_code=404, message=str(e), code="NOT_FOUND")
    except ValidationException as e:
        raise AppException(status_code=422, message=str(e), code="VALIDATION_ERROR")
    except Exception as e:
        logger.error("Unexpected error: %s", e, exc_info=True)
        raise AppException(status_code=500, message="Internal server error")
```

---

## Global Exception Handler

In `main.py`, register handlers for each exception type:

```python
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
            },
        },
    )

@app.exception_handler(UseCaseException)
async def usecase_exception_handler(request: Request, exc: UseCaseException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "layer": "usecase",
            },
        },
    )

@app.exception_handler(ServiceException)
async def service_exception_handler(request: Request, exc: ServiceException):
    logger.error("Service error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": exc.message,
                "layer": "service",
            },
        },
    )

@app.exception_handler(RepositoryException)
async def repository_exception_handler(request: Request, exc: RepositoryException):
    logger.error("Repository error: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": exc.code,
                "message": "Database error. See server logs.",
                "layer": "repository",
            },
        },
    )

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_ERROR",
                "message": "Internal server error",
            },
        },
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
