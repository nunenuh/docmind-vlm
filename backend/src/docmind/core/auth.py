"""
docmind/core/auth.py

Supabase JWT verification dependency using JWKS (ES256).
"""

import threading

import jwt
from jwt import PyJWKClient
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()

# ---------------------------------------------------------------------------
# JWKS client with thread-safe caching
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
    Decode and verify a Supabase JWT token using JWKS (ES256).

    Args:
        token: Raw JWT string from Authorization header.

    Returns:
        Dict with 'id' (from sub claim) and 'email'.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidSignatureError: Signature verification failed.
        jwt.InvalidAudienceError: Audience claim mismatch.
        jwt.DecodeError: Token is malformed.
        jwt.PyJWKClientError: JWKS endpoint unreachable or key not found.
        KeyError: Missing 'sub' claim.
    """
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
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate Supabase JWT token and return user payload.

    Returns:
        dict with at minimum: {"id": str, "email": str | None}

    Raises:
        HTTPException 401 if token is missing, expired, or invalid.
    """
    token = credentials.credentials
    try:
        return decode_jwt(token)
    except jwt.ExpiredSignatureError:
        logger.warning("Expired JWT token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (jwt.InvalidTokenError, jwt.PyJWKClientError, KeyError) as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
