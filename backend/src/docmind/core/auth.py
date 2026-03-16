"""
docmind/core/auth.py

Supabase JWT verification dependency.
"""

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings
from .logging import get_logger

logger = get_logger(__name__)
security = HTTPBearer()


def decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT token.

    Args:
        token: Raw JWT string from Authorization header.

    Returns:
        Dict with 'id' (from sub claim) and 'email'.

    Raises:
        jwt.ExpiredSignatureError: Token has expired.
        jwt.InvalidSignatureError: Signature verification failed.
        jwt.InvalidAudienceError: Audience claim mismatch.
        jwt.DecodeError: Token is malformed.
        KeyError: Missing 'sub' claim.
    """
    settings = get_settings()
    payload = jwt.decode(
        token,
        settings.SUPABASE_JWT_SECRET,
        algorithms=["HS256"],
        audience="authenticated",
    )
    return {"id": payload["sub"], "email": payload.get("email")}


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
    except (jwt.InvalidTokenError, KeyError) as e:
        logger.warning("Invalid JWT token", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
