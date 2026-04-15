"""Tests for shared.provider_resolver — resolve user provider config."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestResolveProviderOverride:
    """Tests for resolve_provider_override function."""

    @pytest.mark.asyncio
    @patch("docmind.shared.provider_resolver.UserProviderRepository")
    @patch("docmind.shared.provider_resolver.decrypt")
    async def test_returns_override_when_config_exists(
        self, mock_decrypt, mock_repo_cls
    ):
        from docmind.shared.provider_resolver import resolve_provider_override

        config = MagicMock()
        config.is_validated = True
        config.provider_name = "openai"
        config.encrypted_api_key = "encrypted_key"
        config.model_name = "gpt-4o"
        config.base_url = None

        mock_repo = MagicMock()
        mock_repo.get_by_user_and_type = AsyncMock(return_value=config)
        mock_repo_cls.return_value = mock_repo
        mock_decrypt.return_value = "sk-real-key"

        result = await resolve_provider_override("user-1", "vlm")

        assert result is not None
        assert result.provider_name == "openai"
        assert result.api_key == "sk-real-key"
        assert result.model_name == "gpt-4o"
        assert result.base_url is None
        mock_repo.get_by_user_and_type.assert_awaited_once_with("user-1", "vlm")
        mock_decrypt.assert_called_once_with("encrypted_key")

    @pytest.mark.asyncio
    @patch("docmind.shared.provider_resolver.UserProviderRepository")
    async def test_returns_none_when_no_config(self, mock_repo_cls):
        from docmind.shared.provider_resolver import resolve_provider_override

        mock_repo = MagicMock()
        mock_repo.get_by_user_and_type = AsyncMock(return_value=None)
        mock_repo_cls.return_value = mock_repo

        result = await resolve_provider_override("user-1", "vlm")
        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.shared.provider_resolver.UserProviderRepository")
    async def test_returns_none_when_not_validated(self, mock_repo_cls):
        from docmind.shared.provider_resolver import resolve_provider_override

        config = MagicMock()
        config.is_validated = False

        mock_repo = MagicMock()
        mock_repo.get_by_user_and_type = AsyncMock(return_value=config)
        mock_repo_cls.return_value = mock_repo

        result = await resolve_provider_override("user-1", "vlm")
        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.shared.provider_resolver.UserProviderRepository")
    @patch("docmind.shared.provider_resolver.decrypt")
    async def test_returns_none_on_decrypt_failure(
        self, mock_decrypt, mock_repo_cls
    ):
        from docmind.shared.provider_resolver import resolve_provider_override

        config = MagicMock()
        config.is_validated = True
        config.encrypted_api_key = "bad_encrypted"

        mock_repo = MagicMock()
        mock_repo.get_by_user_and_type = AsyncMock(return_value=config)
        mock_repo_cls.return_value = mock_repo
        mock_decrypt.side_effect = Exception("decrypt failed")

        result = await resolve_provider_override("user-1", "vlm")
        assert result is None

    @pytest.mark.asyncio
    @patch("docmind.shared.provider_resolver.UserProviderRepository")
    @patch("docmind.shared.provider_resolver.decrypt")
    async def test_returns_override_with_base_url(
        self, mock_decrypt, mock_repo_cls
    ):
        from docmind.shared.provider_resolver import resolve_provider_override

        config = MagicMock()
        config.is_validated = True
        config.provider_name = "openai"
        config.encrypted_api_key = "encrypted_key"
        config.model_name = "gpt-4o-mini"
        config.base_url = "https://custom.api.example.com"

        mock_repo = MagicMock()
        mock_repo.get_by_user_and_type = AsyncMock(return_value=config)
        mock_repo_cls.return_value = mock_repo
        mock_decrypt.return_value = "sk-custom-key"

        result = await resolve_provider_override("user-1", "vlm")

        assert result is not None
        assert result.base_url == "https://custom.api.example.com"
        assert result.model_name == "gpt-4o-mini"
