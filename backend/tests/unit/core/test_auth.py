"""
Unit tests for docmind/core/auth.py — JWKS-based JWT validation (ES256).

Tests cover:
- Valid token decoding
- Expired token rejection
- Invalid signature rejection
- Malformed token rejection
- Wrong audience rejection
- get_current_user integration with decode_jwt
"""
import time
from unittest.mock import MagicMock

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from docmind.core.auth import decode_jwt, get_current_user, reset_jwks_client
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

# ---------------------------------------------------------------------------
# EC key pairs for testing
# ---------------------------------------------------------------------------

_TEST_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())
_TEST_PUBLIC_KEY = _TEST_PRIVATE_KEY.public_key()

_WRONG_PRIVATE_KEY = ec.generate_private_key(ec.SECP256R1())

TEST_USER_ID = "user-abc-123"
TEST_EMAIL = "test@example.com"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _mock_jwks_client(monkeypatch):
    """Mock the JWKS client to return our test public key."""
    reset_jwks_client()

    mock_signing_key = MagicMock()
    mock_signing_key.key = _TEST_PUBLIC_KEY

    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_signing_key

    monkeypatch.setattr(
        "docmind.core.auth._get_jwks_client", lambda: mock_client
    )


def _make_token(
    user_id: str = TEST_USER_ID,
    email: str = TEST_EMAIL,
    exp: int | None = None,
    aud: str = "authenticated",
    private_key=None,
    algorithm: str = "ES256",
    **extra_claims,
) -> str:
    """Create a JWT token signed with ES256 for testing."""
    if private_key is None:
        private_key = _TEST_PRIVATE_KEY
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
    return pyjwt.encode(payload, private_key, algorithm=algorithm)


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
        """A valid token without email claim returns email as None."""
        payload = {
            "sub": TEST_USER_ID,
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        token = pyjwt.encode(
            payload, _TEST_PRIVATE_KEY, algorithm="ES256"
        )
        result = decode_jwt(token)

        assert result["id"] == TEST_USER_ID
        assert result["email"] is None

    def test_expired_token_raises_expired_error(self):
        """An expired token should raise jwt.ExpiredSignatureError."""
        token = _make_token(exp=int(time.time()) - 3600)

        with pytest.raises(pyjwt.ExpiredSignatureError):
            decode_jwt(token)

    def test_invalid_signature_raises_error(self, monkeypatch):
        """A token verified with wrong public key raises error."""
        wrong_public_key = _WRONG_PRIVATE_KEY.public_key()
        mock_signing_key = MagicMock()
        mock_signing_key.key = wrong_public_key

        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )
        monkeypatch.setattr(
            "docmind.core.auth._get_jwks_client", lambda: mock_client
        )

        token = _make_token()

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

    def test_missing_sub_claim_raises_key_error(self):
        """A token without 'sub' claim should raise KeyError."""
        payload = {
            "email": TEST_EMAIL,
            "aud": "authenticated",
            "exp": int(time.time()) + 3600,
        }
        token = pyjwt.encode(
            payload, _TEST_PRIVATE_KEY, algorithm="ES256"
        )

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
        """Expired token should raise 401 with 'Token expired'."""
        token = _make_token(exp=int(time.time()) - 3600)
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials=token
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.status_code == 401
        assert "expired" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_invalid_signature_raises_401(self, monkeypatch):
        """Token with wrong signature should raise HTTPException 401."""
        wrong_public_key = _WRONG_PRIVATE_KEY.public_key()
        mock_signing_key = MagicMock()
        mock_signing_key.key = wrong_public_key

        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = (
            mock_signing_key
        )
        monkeypatch.setattr(
            "docmind.core.auth._get_jwks_client", lambda: mock_client
        )

        token = _make_token()
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
        """All 401 responses should include WWW-Authenticate header."""
        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer", credentials="invalid"
        )

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(credentials)

        assert exc_info.value.headers == {"WWW-Authenticate": "Bearer"}
