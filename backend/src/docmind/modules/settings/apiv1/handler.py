"""
docmind/modules/settings/apiv1/handler.py

Provider settings HTTP endpoints — CRUD + test for user AI providers.
"""

from fastapi import APIRouter, Depends, Request

from docmind.core.auth import get_current_user
from docmind.core.logging import get_logger
from docmind.modules.settings.dependencies import get_provider_settings_usecase
from docmind.modules.settings.schemas import (
    ProviderConfigResponse,
    ProviderType,
    ProvidersResponse,
    SetProviderRequest,
    ValidateProviderRequest,
    ValidateProviderResponse,
)
from docmind.modules.settings.usecase import ProviderSettingsUseCase
from docmind.shared.exceptions import AppException, BaseAppException

logger = get_logger(__name__)
router = APIRouter()


@router.get("/providers", response_model=ProvidersResponse)
async def get_providers(
    request: Request,
    usecase: ProviderSettingsUseCase = Depends(get_provider_settings_usecase),
) -> ProvidersResponse:
    """Get user's current provider configurations (API keys masked)."""
    current_user = await get_current_user(request)
    try:
        return await usecase.get_providers(current_user["id"])
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("get_providers error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.put("/providers/vlm", response_model=ProviderConfigResponse)
async def set_vlm_provider(
    body: SetProviderRequest,
    request: Request,
    usecase: ProviderSettingsUseCase = Depends(get_provider_settings_usecase),
) -> ProviderConfigResponse:
    """Set or update VLM provider configuration."""
    current_user = await get_current_user(request)
    try:
        return await usecase.set_provider(
            current_user["id"], ProviderType.VLM, body
        )
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("set_vlm_provider error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.put("/providers/embedding", response_model=ProviderConfigResponse)
async def set_embedding_provider(
    body: SetProviderRequest,
    request: Request,
    usecase: ProviderSettingsUseCase = Depends(get_provider_settings_usecase),
) -> ProviderConfigResponse:
    """Set or update embedding provider configuration."""
    current_user = await get_current_user(request)
    try:
        return await usecase.set_provider(
            current_user["id"], ProviderType.EMBEDDING, body
        )
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("set_embedding_provider error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.delete("/providers/vlm", status_code=204)
async def delete_vlm_provider(
    request: Request,
    usecase: ProviderSettingsUseCase = Depends(get_provider_settings_usecase),
) -> None:
    """Remove VLM provider config (revert to system default)."""
    current_user = await get_current_user(request)
    try:
        await usecase.delete_provider(current_user["id"], ProviderType.VLM)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("delete_vlm_provider error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.delete("/providers/embedding", status_code=204)
async def delete_embedding_provider(
    request: Request,
    usecase: ProviderSettingsUseCase = Depends(get_provider_settings_usecase),
) -> None:
    """Remove embedding provider config (revert to system default)."""
    current_user = await get_current_user(request)
    try:
        await usecase.delete_provider(current_user["id"], ProviderType.EMBEDDING)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("delete_embedding_provider error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc


@router.post("/providers/test", response_model=ValidateProviderResponse)
async def test_provider(
    body: ValidateProviderRequest,
    request: Request,
    usecase: ProviderSettingsUseCase = Depends(get_provider_settings_usecase),
) -> ValidateProviderResponse:
    """Test a provider connection without saving. Returns available models."""
    await get_current_user(request)  # Ensure authenticated
    try:
        return await usecase.test_provider(body)
    except BaseAppException:
        raise
    except Exception as exc:
        logger.error("test_provider error: %s", exc, exc_info=True)
        raise AppException(message="Internal server error") from exc
