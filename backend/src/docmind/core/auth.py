"""
docmind/core/auth.py

Unified authentication — supports both:
  - Supabase JWT (HS256 local / ES256 cloud)
  - API tokens (dm_live_xxx / dm_test_xxx prefix)
"""

import threading

import jwt
from fastapi import HTTPException, Request, status
from jwt import PyJWKClient

from docmind.shared.exceptions import AuthenticationException

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)

API_TOKEN_PREFIXES = ("dm_live_", "dm_test_")

# ---------------------------------------------------------------------------
# JWKS client (for cloud Supabase with ES256)
# ---------------------------------------------------------------------------

_jwks_client: PyJWKClient | None = None
_jwks_lock = threading.Lock()


def _get_jwks_client() -> PyJWKClient:
    """Return a cached PyJWKClient for the Supabase JWKS endpoint."""
    global _jwks_client
    if _jwks_client is None:
        with _jwks_lock:
            if _jwks_client is None:
                settings = get_settings()
                jwks_url = (
                    f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
                )
                _jwks_client = PyJWKClient(jwks_url, cache_keys=True)
    return _jwks_client


def reset_jwks_client() -> None:
    """Reset the cached JWKS client (for testing)."""
    global _jwks_client
    with _jwks_lock:
        _jwks_client = None


# ---------------------------------------------------------------------------
# JWT decode
# ---------------------------------------------------------------------------


def decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT token.

    Strategy:
      1. If JWT_SECRET is configured → verify with HS256 (local Supabase)
      2. Otherwise → verify with JWKS/ES256 (cloud Supabase)

    Returns:
        Dict with 'id' (from sub claim) and 'email'.
    """
    settings = get_settings()

    # Strategy 1: HS256 with shared secret (local Supabase)
    if settings.JWT_SECRET:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=["HS256"],
            audience="authenticated",
        )
        return {"id": payload["sub"], "email": payload.get("email")}

    # Strategy 2: ES256 via JWKS (cloud Supabase)
    client = _get_jwks_client()
    signing_key = client.get_signing_key_from_jwt(token)
    payload = jwt.decode(
        token,
        signing_key.key,
        algorithms=["ES256"],
        audience="authenticated",
    )
    return {"id": payload["sub"], "email": payload.get("email")}


# ---------------------------------------------------------------------------
# Token extraction helpers
# ---------------------------------------------------------------------------


def _is_api_token(token: str) -> bool:
    return any(token.startswith(p) for p in API_TOKEN_PREFIXES)


def _extract_token(request: Request) -> str | None:
    """Extract token from X-API-Key or Authorization header."""
    api_key = request.headers.get("x-api-key")
    if api_key and _is_api_token(api_key):
        return api_key

    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        return auth_header[7:]

    return None


# ---------------------------------------------------------------------------
# Lazy import to avoid circular dependency
# ---------------------------------------------------------------------------

from docmind.modules.auth.services.api_token_service import ApiTokenService  # noqa: E402


# ---------------------------------------------------------------------------
# FastAPI dependency — unified JWT + API token
# ---------------------------------------------------------------------------


async def get_current_user(request: Request) -> dict:
    """
    Validate authentication and return user payload.

    Supports:
      - API token: Authorization: Bearer dm_live_xxx or X-API-Key: dm_live_xxx
      - JWT: Authorization: Bearer eyJhbG...

    Returns:
        dict: {"id": str, "email": str, "scopes": list|None,
               "auth_method": "jwt"|"api_token", "token_id": str|None}
    """
    token = _extract_token(request)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # API token path
    if _is_api_token(token):
        from docmind.core.rate_limit import get_token_rate_limiter

        prefix = token[:12]
        limiter = get_token_rate_limiter()
        if limiter.is_blocked(prefix):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many failed attempts. Try again later.",
            )
        try:
            service = ApiTokenService()
            user_data = await service.validate_token(token)
            limiter.reset(prefix)
            return {
                "id": user_data["user_id"],
                "email": "",
                "scopes": user_data["scopes"],
                "auth_method": "api_token",
                "token_id": user_data["token_id"],
            }
        except AuthenticationException:
            limiter.record_failure(prefix)
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired API token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # JWT path
    try:
        payload = decode_jwt(token)
        return {
            **payload,
            "scopes": None,
            "auth_method": "jwt",
            "token_id": None,
        }
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, jwt.PyJWKClientError, jwt.PyJWKSetError, KeyError) as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error("JWT verification error", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
            headers={"WWW-Authenticate": "Bearer"},
        )
