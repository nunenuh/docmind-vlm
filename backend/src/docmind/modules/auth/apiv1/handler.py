"""
docmind/modules/auth/apiv1/handler.py

Auth HTTP endpoints — signup, login, logout, session, refresh.
"""

from fastapi import APIRouter, Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from docmind.core.logging import get_logger
from docmind.shared.exceptions import AppException, BaseAppException

from ..dependencies import get_auth_usecase
from ..schemas import (
    AuthSessionResponse,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SessionResponse,
    SignupRequest,
)
from ..usecases import AuthUseCase

logger = get_logger(__name__)
router = APIRouter()
bearer_scheme = HTTPBearer()


@router.post("/signup", response_model=AuthSessionResponse, status_code=201)
async def signup(
    body: SignupRequest,
    usecase: AuthUseCase = Depends(get_auth_usecase),
) -> AuthSessionResponse:
    try:
        return await usecase.signup(email=body.email, password=body.password)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("signup error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.post("/login", response_model=AuthSessionResponse)
async def login(
    body: LoginRequest,
    usecase: AuthUseCase = Depends(get_auth_usecase),
) -> AuthSessionResponse:
    try:
        return await usecase.login(email=body.email, password=body.password)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("login error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.post("/logout", response_model=MessageResponse)
async def logout(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    usecase: AuthUseCase = Depends(get_auth_usecase),
) -> MessageResponse:
    try:
        await usecase.logout(access_token=credentials.credentials)
        return MessageResponse(message="Logged out successfully")
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("logout error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.get("/session", response_model=SessionResponse)
async def get_session(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    usecase: AuthUseCase = Depends(get_auth_usecase),
) -> SessionResponse:
    try:
        return await usecase.get_session(access_token=credentials.credentials)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("get_session error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.post("/refresh", response_model=AuthSessionResponse)
async def refresh(
    body: RefreshRequest,
    usecase: AuthUseCase = Depends(get_auth_usecase),
) -> AuthSessionResponse:
    try:
        return await usecase.refresh(refresh_token=body.refresh_token)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("refresh error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc
