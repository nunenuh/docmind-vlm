"""
docmind/core/auth.py

Supabase JWT verification dependency.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .config import get_settings

security = HTTPBearer()


def decode_jwt(token: str) -> dict:
    """
    Decode and verify a Supabase JWT token.

    Stub implementation for scaffold — returns a minimal user payload.
    Full implementation will use PyJWT with SUPABASE_JWT_SECRET.
    """
    # TODO: Implement real JWT verification with PyJWT
    # settings = get_settings()
    # payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    raise NotImplementedError("JWT verification not yet implemented")


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate Supabase JWT token and return user payload.

    Returns:
        dict with at minimum: {"id": str, "email": str}

    Raises:
        HTTPException 401 if token is missing or invalid
        HTTPException 403 if token is valid but user lacks access
    """
    token = credentials.credentials
    try:
        payload = decode_jwt(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    return payload
