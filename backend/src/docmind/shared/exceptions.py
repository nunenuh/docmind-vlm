"""
docmind/shared/exceptions.py

Shared exception types used across modules.
"""


class ServiceException(Exception):
    """Raised by service layer for business logic errors."""

    pass


class RepositoryException(Exception):
    """Raised by repository layer for database errors."""

    pass
