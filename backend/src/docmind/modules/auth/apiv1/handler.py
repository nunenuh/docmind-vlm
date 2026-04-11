"""
docmind/modules/auth/apiv1/handler.py

Auth HTTP endpoints — signup, login, logout, session, refresh.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.shared.exceptions import AppException, BaseAppException

from ..dependencies import get_api_token_usecase, get_auth_usecase
from ..schemas import (
    AuthSessionResponse,
    CreateTokenRequest,
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    SessionResponse,
    SignupRequest,
    TokenCreatedResponse,
    TokenListResponse,
    TokenResponse,
    UpdateTokenRequest,
)
from ..usecases import ApiTokenUseCase, AuthUseCase

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


# ── API Token CRUD ────────────────────────────────────


@router.post("/tokens", response_model=TokenCreatedResponse, status_code=201)
async def create_token(
    body: CreateTokenRequest,
    request: Request,
    usecase: ApiTokenUseCase = Depends(get_api_token_usecase),
) -> TokenCreatedResponse:
    current_user = await get_current_user(request)
    try:
        return await usecase.create_token(current_user["id"], body)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("create_token error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.get("/tokens", response_model=TokenListResponse)
async def list_tokens(
    request: Request,
    usecase: ApiTokenUseCase = Depends(get_api_token_usecase),
) -> TokenListResponse:
    current_user = await get_current_user(request)
    try:
        return await usecase.list_tokens(current_user["id"])
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("list_tokens error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.delete("/tokens/{token_id}", status_code=204)
async def revoke_token(
    token_id: str,
    request: Request,
    usecase: ApiTokenUseCase = Depends(get_api_token_usecase),
) -> None:
    current_user = await get_current_user(request)
    try:
        await usecase.revoke_token(token_id, current_user["id"])
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("revoke_token error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.post("/tokens/{token_id}/regenerate", response_model=TokenCreatedResponse)
async def regenerate_token(
    token_id: str,
    request: Request,
    usecase: ApiTokenUseCase = Depends(get_api_token_usecase),
) -> TokenCreatedResponse:
    current_user = await get_current_user(request)
    try:
        return await usecase.regenerate_token(token_id, current_user["id"])
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("regenerate_token error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.patch("/tokens/{token_id}", response_model=TokenResponse)
async def update_token(
    token_id: str,
    body: UpdateTokenRequest,
    request: Request,
    usecase: ApiTokenUseCase = Depends(get_api_token_usecase),
) -> TokenResponse:
    current_user = await get_current_user(request)
    try:
        return await usecase.update_token(token_id, current_user["id"], body)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("update_token error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc
