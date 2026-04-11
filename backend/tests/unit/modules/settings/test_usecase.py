"""Tests for docmind.modules.settings.usecase.ProviderSettingsUseCase."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from docmind.modules.settings.schemas import (
    ProviderName,
    ProviderType,
    SetProviderRequest,
    ValidateProviderRequest,
    ValidateProviderResponse,
)
from docmind.modules.settings.usecase import ProviderSettingsUseCase
from docmind.shared.exceptions import ValidationException


def _make_config(
    provider_type: str = "vlm",
    provider_name: str = "openai",
    model_name: str = "gpt-4o",
    encrypted_api_key: str = "encrypted-value",
    is_validated: bool = True,
) -> MagicMock:
    config = MagicMock()
    config.provider_type = provider_type
    config.provider_name = provider_name
    config.model_name = model_name
    config.encrypted_api_key = encrypted_api_key
    config.base_url = None
    config.is_validated = is_validated
    config.created_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    config.updated_at = datetime(2026, 1, 1, tzinfo=timezone.utc)
    return config


@pytest.fixture
def mock_repo() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def mock_service() -> AsyncMock:
    return AsyncMock()


@pytest.fixture
def usecase(mock_repo: AsyncMock, mock_service: AsyncMock) -> ProviderSettingsUseCase:
    return ProviderSettingsUseCase(repository=mock_repo, service=mock_service)


class TestGetProviders:
    @pytest.mark.asyncio
    @patch("docmind.modules.settings.usecase.decrypt", return_value="sk-decrypted-key")
    async def test_returns_providers(
        self, mock_decrypt: MagicMock, usecase: ProviderSettingsUseCase, mock_repo: AsyncMock
    ) -> None:
        mock_repo.get_all_for_user.return_value = [
            _make_config(provider_type="vlm"),
        ]
        result = await usecase.get_providers("user-1")
        assert result.vlm is not None
        assert result.vlm.provider_name == ProviderName.OPENAI
        assert result.vlm.api_key_prefix == "sk-decry..."
        assert result.embedding is None

    @pytest.mark.asyncio
    async def test_empty_configs(
        self, usecase: ProviderSettingsUseCase, mock_repo: AsyncMock
    ) -> None:
        mock_repo.get_all_for_user.return_value = []
        result = await usecase.get_providers("user-1")
        assert result.vlm is None
        assert result.embedding is None

    @pytest.mark.asyncio
    @patch("docmind.modules.settings.usecase.decrypt", side_effect=Exception("bad key"))
    async def test_decrypt_failure_returns_masked_prefix(
        self, mock_decrypt: MagicMock, usecase: ProviderSettingsUseCase, mock_repo: AsyncMock
    ) -> None:
        mock_repo.get_all_for_user.return_value = [
            _make_config(provider_type="vlm"),
        ]
        result = await usecase.get_providers("user-1")
        assert result.vlm is not None
        assert result.vlm.api_key_prefix == "***..."


class TestSetProvider:
    @pytest.mark.asyncio
    @patch("docmind.modules.settings.usecase.encrypt", return_value="encrypted-value")
    async def test_set_provider_success(
        self,
        mock_encrypt: MagicMock,
        usecase: ProviderSettingsUseCase,
        mock_repo: AsyncMock,
        mock_service: AsyncMock,
    ) -> None:
        mock_service.test_connection.return_value = ValidateProviderResponse(
            success=True, models=["gpt-4o"]
        )
        mock_repo.upsert.return_value = _make_config()

        request = SetProviderRequest(
            provider_name=ProviderName.OPENAI,
            api_key="sk-real-key-12345",
            model_name="gpt-4o",
        )
        result = await usecase.set_provider("user-1", ProviderType.VLM, request)
        assert result.provider_name == ProviderName.OPENAI
        assert result.is_validated is True
        mock_encrypt.assert_called_once_with("sk-real-key-12345")

    @pytest.mark.asyncio
    async def test_set_provider_test_fails(
        self,
        usecase: ProviderSettingsUseCase,
        mock_service: AsyncMock,
    ) -> None:
        mock_service.test_connection.return_value = ValidateProviderResponse(
            success=False, error="Invalid API key"
        )
        request = SetProviderRequest(
            provider_name=ProviderName.OPENAI,
            api_key="sk-bad-key",
            model_name="gpt-4o",
        )
        with pytest.raises(ValidationException, match="Provider test failed"):
            await usecase.set_provider("user-1", ProviderType.VLM, request)


class TestDeleteProvider:
    @pytest.mark.asyncio
    async def test_delete_existing(
        self, usecase: ProviderSettingsUseCase, mock_repo: AsyncMock
    ) -> None:
        mock_repo.delete.return_value = True
        result = await usecase.delete_provider("user-1", ProviderType.VLM)
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_nonexistent(
        self, usecase: ProviderSettingsUseCase, mock_repo: AsyncMock
    ) -> None:
        mock_repo.delete.return_value = False
        result = await usecase.delete_provider("user-1", ProviderType.VLM)
        assert result is False


class TestTestProvider:
    @pytest.mark.asyncio
    async def test_delegates_to_service(
        self, usecase: ProviderSettingsUseCase, mock_service: AsyncMock
    ) -> None:
        mock_service.test_connection.return_value = ValidateProviderResponse(
            success=True, models=["gpt-4o"]
        )
        request = ValidateProviderRequest(
            provider_name=ProviderName.OPENAI,
            api_key="sk-test-key",
        )
        result = await usecase.test_provider(request)
        assert result.success is True
        mock_service.test_connection.assert_called_once()
