"""
docmind/shared/exceptions.py

Exception hierarchy for all layers. Each layer raises its own exception type
so we know exactly where the error originated.

Usage:
    Repository → raises RepositoryException / RecordNotFoundException / DatabaseException
    Service    → raises ServiceException / ProviderException / StorageException / IndexingException
    UseCase    → raises UseCaseException / NotFoundException / ValidationException / AuthorizationException
    Handler    → catches BaseAppException (re-raises); global handler maps to HTTP response
"""


class BaseAppException(Exception):
    """Base for all application exceptions."""

    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class AppException(BaseAppException):
    """Generic application error (fallback for unexpected failures in handlers)."""

    def __init__(self, message: str = "Internal server error", code: str = "INTERNAL_ERROR", status_code: int = 500) -> None:
        super().__init__(message, code, status_code)


# ── UseCase Exceptions ─────────────────────────────────


class UseCaseException(BaseAppException):
    """Base for usecase/business logic errors."""

    def __init__(self, message: str, code: str = "BUSINESS_ERROR", status_code: int = 400) -> None:
        super().__init__(message, code, status_code)


class NotFoundException(UseCaseException):
    """Resource not found."""

    def __init__(self, message: str = "Resource not found") -> None:
        super().__init__(message, code="NOT_FOUND", status_code=404)


class ValidationException(UseCaseException):
    """Business rule validation failed."""

    def __init__(self, message: str = "Validation failed") -> None:
        super().__init__(message, code="VALIDATION_ERROR", status_code=422)


class AuthorizationException(UseCaseException):
    """User not authorized for this action."""

    def __init__(self, message: str = "Not authorized", detail: dict | None = None) -> None:
        super().__init__(message, code="FORBIDDEN", status_code=403)
        self.detail = detail or {}


class AuthenticationException(UseCaseException):
    """Authentication failed (bad credentials, expired token, etc.)."""

    def __init__(self, message: str = "Authentication failed") -> None:
        super().__init__(message, code="AUTHENTICATION_ERROR", status_code=401)


class ConflictException(UseCaseException):
    """Duplicate or conflicting resource."""

    def __init__(self, message: str = "Resource conflict") -> None:
        super().__init__(message, code="CONFLICT", status_code=409)


# ── Service Exceptions ─────────────────────────────────


class ServiceException(BaseAppException):
    """Base for service layer errors."""

    def __init__(self, message: str, code: str = "SERVICE_ERROR", status_code: int = 500) -> None:
        super().__init__(message, code, status_code)


class ProviderException(ServiceException):
    """VLM/embedding provider call failed."""

    def __init__(self, message: str = "Provider call failed") -> None:
        super().__init__(message, code="PROVIDER_ERROR", status_code=502)


class StorageException(ServiceException):
    """File storage operation failed."""

    def __init__(self, message: str = "Storage operation failed") -> None:
        super().__init__(message, code="STORAGE_ERROR", status_code=503)


class IndexingException(ServiceException):
    """RAG indexing failed."""

    def __init__(self, message: str = "Indexing failed") -> None:
        super().__init__(message, code="INDEXING_ERROR", status_code=500)


# ── Repository Exceptions ──────────────────────────────


class RepositoryException(BaseAppException):
    """Base for data access errors."""

    def __init__(self, message: str, code: str = "DATABASE_ERROR", status_code: int = 500) -> None:
        super().__init__(message, code, status_code)


class DatabaseException(RepositoryException):
    """Database query/connection failed."""

    def __init__(self, message: str = "Database error") -> None:
        super().__init__(message, code="DATABASE_ERROR", status_code=500)


class RecordNotFoundException(RepositoryException):
    """Specific record not found in database."""

    def __init__(self, message: str = "Record not found") -> None:
        super().__init__(message, code="RECORD_NOT_FOUND", status_code=404)
