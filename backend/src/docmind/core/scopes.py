"""
docmind/core/scopes.py

Scope enforcement for API token authentication.
JWT users bypass scope checks (scopes=None means unrestricted).
"""

from fastapi import Depends, Request

from docmind.core.auth import get_current_user
from docmind.shared.exceptions import AuthorizationException


def _check_scopes(current_user: dict, required_scopes: list[str]) -> dict:
    """Check if user has all required scopes. Returns user dict if OK."""
    user_scopes = current_user.get("scopes")

    # JWT users — no scope restrictions
    if user_scopes is None:
        return current_user

    # admin:* grants everything
    if "admin:*" in user_scopes:
        return current_user

    # Check each required scope
    for scope in required_scopes:
        if scope not in user_scopes:
            raise AuthorizationException(
                f"Missing required scope: {scope}",
                detail={"missing_scope": scope},
            )

    return current_user


def require_scopes(*scopes: str):
    """
    FastAPI dependency factory that enforces API token scopes.

    Usage:
        current_user: dict = Depends(require_scopes("documents:read"))
    """
    required = list(scopes)

    async def _dependency(
        request: Request,
    ) -> dict:
        current_user = await get_current_user(request)
        return _check_scopes(current_user, required)

    return _dependency
