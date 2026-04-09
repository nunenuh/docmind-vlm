# Issue #1: Supabase JWT Authentication Integration

## Summary

Implement real JWT token verification in `core/auth.py` using PyJWT to replace the current stub `decode_jwt()`. The `get_current_user()` FastAPI dependency must decode Supabase-issued JWTs, validate signature with `SUPABASE_JWT_SECRET`, enforce the `"authenticated"` audience claim, extract `user_id` (from `sub`) and `email`, and raise appropriate HTTP 401 errors for expired, invalid, or missing tokens. This is the foundational security gate for all protected endpoints.

## Context

- **Phase**: 1 — Infrastructure
- **Priority**: P0
- **Labels**: `phase-1-infra`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: None
- **Branch**: `feat/1-auth-jwt`
- **Estimated scope**: S

## Specs to Read

- `specs/conventions/security.md` — Full JWT validation flow, error responses, test fixtures
- `specs/backend/api.md` — Section "Authentication — core/auth.py", error handling rules
- `specs/conventions/python-module-structure.md` — Where auth fits in the architecture

## Current State (Scaffold)

**File: `backend/src/docmind/core/auth.py`**

```python
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
```

**File: `backend/src/docmind/core/config.py`** (relevant excerpt)

```python
class Settings(BaseSettings):
    # ...
    SUPABASE_JWT_SECRET: str = Field(default="")
    # ...
```

**File: `backend/tests/conftest.py`**

```python
"""
Shared test fixtures for DocMind-VLM backend tests.
"""
import pytest


@pytest.fixture
def sample_document_data() -> dict:
    """Sample document creation data."""
    return {
        "filename": "test_invoice.pdf",
        "file_type": "pdf",
        "file_size": 1024,
        "storage_path": "test-user/test-doc/test_invoice.pdf",
    }


@pytest.fixture
def mock_user() -> dict:
    """Mock authenticated user payload."""
    return {
        "id": "test-user-id",
        "email": "test@example.com",
    }
```

## Requirements

### Functional

1. `decode_jwt(token)` must decode the JWT using `PyJWT` with `HS256` algorithm
2. `decode_jwt(token)` must verify the signature against `get_settings().SUPABASE_JWT_SECRET`
3. `decode_jwt(token)` must enforce `audience="authenticated"` (Supabase standard)
4. `decode_jwt(token)` must return `{"id": payload["sub"], "email": payload.get("email")}` on success
5. `get_current_user()` must return the user dict on valid token
6. `get_current_user()` must raise `HTTPException(401)` with `detail="Token expired"` and `WWW-Authenticate: Bearer` header for expired tokens
7. `get_current_user()` must raise `HTTPException(401)` with `detail="Invalid or expired token"` and `WWW-Authenticate: Bearer` header for invalid tokens (bad signature, malformed, wrong audience)
8. Missing `Authorization` header is handled automatically by FastAPI's `HTTPBearer` (returns 403)

### Non-Functional

- No secrets hardcoded — JWT secret comes from `get_settings().SUPABASE_JWT_SECRET`
- Never log the full token — only log warnings with user context
- Token validation must be synchronous (no I/O) since it is CPU-only work
- `decode_jwt` must be a pure function (aside from settings access) for testability

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/core/test_auth.py`

```python
"""
Unit tests for docmind/core/auth.py — JWT validation.

Tests cover:
- Valid token decoding
- Expired token rejection
- Invalid signature rejection
- Malformed token rejection
- Wrong audience rejection
- get_current_user integration with decode_jwt
"""
import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt as pyjwt
import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from docmind.core.auth import decode_jwt, get_current_user

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TEST_JWT_SECRET = "super-secret-test-key-for-jwt-verification"
TEST_USER_ID = "user-abc-123"
TEST_EMAIL = "test@example.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_settings(monkeypatch):
    """Patch SUPABASE_JWT_SECRET for all tests in this module."""
    mock_settings = MagicMock()
    mock_settings.SUPABASE_JWT_SECRET = TEST_JWT_SECRET
    monkeypatch.setattr("docmind.core.auth.get_settings", lambda: mock_settings)


def _make_token(
    user_id: str = TEST_USER_ID,
    email: str = TEST_EMAIL,
    exp: int | None = None,
    aud: str = "authenticated",
    secret: str = TEST_JWT_SECRET,
    algorithm: str = "HS256",
    **extra_claims,
) -> str:
    """Create a JWT token for testing."""
    if exp is None:
        exp = int(time.time()) + 3600  # 1 hour from now
    payload = {
        "sub": user_id,
        "email": email,
        "aud": aud,
        "exp": exp,
        "iat": int(time.time()),
        **extra_claims,
    }
    return pyjwt.encode(payload, secret, algorithm=algorithm)


# ---------------------------------------------------------------------------
# decode_jwt tests
# ---------------------------------------------------------------------------


class TestDecodeJwt:
    """Tests for the decode_jwt function."""

    def test_valid_token_returns_user_dict(self):
        """A valid token should return dict with id and email."""
        token = _make_token()
        result = decode_jwt(token)

        assert result["id"] == TEST_USER_ID
        assert result["email"] == TEST_EMAIL

    def test_valid_token_without_email_returns_none_email(self):
        """A valid token without email claim should return email as None."""
        payload = {
            "sub": TEST_USER_ID,
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        token = pyjwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")
        result = decode_jwt(token)

        assert result["id"] == TEST_USER_ID
        assert result["email"] is None

    def test_expired_token_raises_expired_error(self):
        """An expired token should raise jwt.ExpiredSignatureError."""
        token = _make_token(exp=int(time.time()) - 3600)

        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_jwt(token)

    def test_invalid_signature_raises_error(self):
        """A token signed with the wrong key should raise InvalidSignatureError."""
        token = _make_token(secret="wrong-secret-key")

        with pytest.raises(pyjwt.InvalidSignatureError):
            decode_jwt(token)

    def test_malformed_token_raises_error(self):
        """A malformed (non-JWT) string should raise DecodeError."""
        with pytest.raises(pyjwt.DecodeError):
            decode_jwt("not-a-valid-jwt-token")

    def test_empty_token_raises_error(self):
        """An empty string should raise DecodeError."""
        with pytest.raises(pyjwt.DecodeError):
            decode_jwt("")

    def test_wrong_audience_raises_error(self):
        """A token with wrong audience should raise InvalidAudienceError."""
        token = _make_token(aud="wrong-audience")

        with pytest.raises(pyjwt.InvalidAudienceError):
            decode_jwt(token)

    def test_missing_sub_claim_raises_error(self):
        """A token without 'sub' claim should raise a KeyError or similar."""
        payload = {
            "email": TEST_EMAIL,
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        token = pyjwt.encode(payload, TEST_JWT_SECRET, algorithm="HS256")

        with pytest.raises(KeyError):
            decode_jwt(token)


# ---------------------------------------------------------------------------
# get_current_user tests
# ---------------------------------------------------------------------------


class TestGetCurrentUser:
    """Tests for the get_current_user FastAPI dependency."""

    @pytest.mark.asyncio
    async def test_valid_token_returns_user_payload(self):
        """Valid credentials should return the user dict."""
        token = _make_token()
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token
        )

        result = await get_current_user(credentials)

        assert result["id"] == TEST_USER_ID
        assert result["email"] == TEST_EMAIL

    @pytest.mark.asyncio
    async def test_expired_token_raises_401_with_expired_message(self):
        """Expired token should raise HTTPException 401 with 'Token expired'."""
        token = _make_token(exp=int(time.time()) - 3600)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_401(self):
        """Token with wrong signature should raise HTTPException 401."""
        token = _make_token(secret="wrong-secret")
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_malformed_token_raises_401(self):
        """Malformed token should raise HTTPException 401."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="garbage.token.here"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_401_includes_www_authenticate_header(self):
        """All 401 responses should include WWW-Authenticate: Bearer header."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/core/auth.py` — Replace stub with real implementation

**Implementation guidance**:

1. Import `jwt` (PyJWT) at the top of `auth.py`
2. Import `get_logger` from `docmind.core.logging`
3. Implement `decode_jwt(token: str) -> dict`:
   - Call `get_settings()` to get the JWT secret
   - Use `jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")`
   - Extract `sub` from payload (raise `KeyError` if missing)
   - Return `{"id": payload["sub"], "email": payload.get("email")}`
   - Let PyJWT exceptions (`ExpiredSignatureError`, `InvalidSignatureError`, `DecodeError`, `InvalidAudienceError`) propagate — they are caught by `get_current_user`
4. Update `get_current_user` to differentiate error types:
   - Catch `jwt.ExpiredSignatureError` separately, return detail `"Token expired"`
   - Catch all other `jwt.InvalidTokenError` subclasses, return detail `"Invalid or expired token"`
   - Include `headers={"WWW-Authenticate": "Bearer"}` on all 401 responses
5. Add structured logging: `logger.warning("Expired JWT token")` and `logger.warning("Invalid JWT token", error=str(e))`

**Target implementation** (for reference):

```python
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
```

### Step 3: Refactor (IMPROVE)

- Ensure `decode_jwt` is importable independently for use in tests and other modules
- Verify that no token content is logged (only metadata like "expired", "invalid")
- Confirm that the `conftest.py` `mock_user` fixture returns `{"id": ..., "email": ...}` matching the new format (update if needed)
- Add type hints for return value

## Acceptance Criteria

- [ ] `decode_jwt` decodes valid Supabase JWTs and returns `{"id": ..., "email": ...}`
- [ ] `decode_jwt` raises `jwt.ExpiredSignatureError` for expired tokens
- [ ] `decode_jwt` raises `jwt.InvalidSignatureError` for wrong-secret tokens
- [ ] `decode_jwt` raises `jwt.DecodeError` for malformed tokens
- [ ] `decode_jwt` raises `jwt.InvalidAudienceError` for wrong audience
- [ ] `decode_jwt` raises `KeyError` when `sub` claim is missing
- [ ] `get_current_user` returns user dict for valid tokens
- [ ] `get_current_user` raises HTTP 401 with "Token expired" for expired tokens
- [ ] `get_current_user` raises HTTP 401 with "Invalid or expired token" for all other invalid tokens
- [ ] All 401 responses include `WWW-Authenticate: Bearer` header
- [ ] No secrets or full tokens are logged
- [ ] All 10 unit tests pass

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/core/auth.py` | Modify | Replace stub `decode_jwt` with PyJWT implementation, update `get_current_user` error handling |
| `backend/tests/unit/core/test_auth.py` | Create | 10 unit tests covering valid, expired, invalid, malformed, wrong-audience tokens |

## Verification

```bash
# Run the auth tests
cd backend && python -m pytest tests/unit/core/test_auth.py -v

# Run with coverage
cd backend && python -m pytest tests/unit/core/test_auth.py -v --cov=docmind.core.auth --cov-report=term-missing

# Verify no hardcoded secrets
grep -r "SUPABASE_JWT_SECRET" backend/src/docmind/core/auth.py
# Should only show: settings.SUPABASE_JWT_SECRET (loaded from env)
```
