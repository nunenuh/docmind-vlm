"""
Unit tests for auth schemas — validation rules and response shapes.
"""

import pytest
from pydantic import ValidationError

from docmind.modules.auth.schemas import (
    AuthSessionResponse,
    AuthUserResponse,
    LoginRequest,
    SignupRequest,
)


# ---------------------------------------------------------------------------
# SignupRequest
# ---------------------------------------------------------------------------


class TestSignupRequest:
    def test_signup_request_valid(self) -> None:
        req = SignupRequest(email="user@example.com", password="secret123")
        assert req.email == "user@example.com"
        assert req.password == "secret123"

    def test_signup_request_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            SignupRequest(email="not-an-email", password="secret123")

    def test_signup_request_short_password(self) -> None:
        with pytest.raises(ValidationError):
            SignupRequest(email="user@example.com", password="abc")


# ---------------------------------------------------------------------------
# LoginRequest
# ---------------------------------------------------------------------------


class TestLoginRequest:
    def test_login_request_valid(self) -> None:
        req = LoginRequest(email="user@example.com", password="p")
        assert req.email == "user@example.com"
        assert req.password == "p"

    def test_login_request_invalid_email(self) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email="bad", password="whatever")


# ---------------------------------------------------------------------------
# AuthSessionResponse
# ---------------------------------------------------------------------------


class TestAuthSessionResponse:
    def test_auth_session_response_shape(self) -> None:
        resp = AuthSessionResponse(
            access_token="at",
            refresh_token="rt",
            expires_in=3600,
            user=AuthUserResponse(id="u1", email="u@x.com", created_at="2026-01-01"),
        )
        assert resp.access_token == "at"
        assert resp.refresh_token == "rt"
        assert resp.expires_in == 3600
        assert resp.token_type == "Bearer"
        assert resp.user.id == "u1"
        assert resp.user.email == "u@x.com"
        assert resp.user.created_at == "2026-01-01"

    def test_auth_session_response_default_token_type(self) -> None:
        resp = AuthSessionResponse(
            access_token="at",
            refresh_token="rt",
            expires_in=3600,
            user=AuthUserResponse(id="u1", email="u@x.com"),
        )
        assert resp.token_type == "Bearer"
        assert resp.user.created_at is None
