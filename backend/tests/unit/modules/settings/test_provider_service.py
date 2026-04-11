"""Tests for docmind.modules.settings.services.ProviderTestService."""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

import httpx

from docmind.modules.settings.schemas import ProviderName
from docmind.modules.settings.services import ProviderTestService


@pytest.fixture
def service() -> ProviderTestService:
    return ProviderTestService()


class TestProviderTestServiceOpenAI:
    """Test OpenAI provider connection testing."""

    @pytest.mark.asyncio
    async def test_openai_success(self, service: ProviderTestService) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "data": [
                    {"id": "gpt-4o"},
                    {"id": "gpt-4o-mini"},
                    {"id": "text-embedding-ada-002"},
                    {"id": "dall-e-3"},
                ]
            },
            request=httpx.Request("GET", "https://api.openai.com/v1/models"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await service.test_connection(
                provider_name=ProviderName.OPENAI,
                api_key="sk-test-key",
            )
        assert result.success is True
        assert "gpt-4o" in result.models
        assert "text-embedding-ada-002" in result.models
        # dall-e-3 should be filtered out (not vision or embedding)
        assert "dall-e-3" not in result.models

    @pytest.mark.asyncio
    async def test_openai_auth_failure(self, service: ProviderTestService) -> None:
        mock_response = httpx.Response(
            401,
            json={"error": {"message": "Invalid API key"}},
            request=httpx.Request("GET", "https://api.openai.com/v1/models"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await service.test_connection(
                provider_name=ProviderName.OPENAI,
                api_key="sk-bad-key",
            )
        assert result.success is False
        assert "401" in (result.error or "")


class TestProviderTestServiceGoogle:
    """Test Google Gemini provider connection testing."""

    @pytest.mark.asyncio
    async def test_google_success(self, service: ProviderTestService) -> None:
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {
                        "name": "models/gemini-2.0-flash",
                        "supportedGenerationMethods": ["generateContent"],
                    },
                    {
                        "name": "models/text-embedding-004",
                        "supportedGenerationMethods": ["embedContent"],
                    },
                    {
                        "name": "models/some-other",
                        "supportedGenerationMethods": ["other"],
                    },
                ]
            },
            request=httpx.Request("GET", "https://generativelanguage.googleapis.com/v1/models"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await service.test_connection(
                provider_name=ProviderName.GOOGLE,
                api_key="AIza-test-key",
            )
        assert result.success is True
        assert "gemini-2.0-flash" in result.models
        assert "text-embedding-004" in result.models
        # "some-other" should be filtered out (no generateContent or embedContent)
        assert "some-other" not in result.models

    @pytest.mark.asyncio
    async def test_google_auth_failure(self, service: ProviderTestService) -> None:
        mock_response = httpx.Response(
            400,
            json={"error": {"message": "API key not valid"}},
            request=httpx.Request("GET", "https://generativelanguage.googleapis.com/v1/models"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await service.test_connection(
                provider_name=ProviderName.GOOGLE,
                api_key="bad-key",
            )
        assert result.success is False
        assert "400" in (result.error or "")


class TestProviderTestServiceOllama:
    """Test Ollama provider connection testing."""

    @pytest.mark.asyncio
    @patch("docmind.modules.settings.services.get_settings")
    async def test_ollama_success(
        self, mock_settings: MagicMock, service: ProviderTestService
    ) -> None:
        mock_settings.return_value = MagicMock(OLLAMA_BASE_URL="http://localhost:11434")
        mock_response = httpx.Response(
            200,
            json={
                "models": [
                    {"name": "llava:latest"},
                    {"name": "nomic-embed-text:latest"},
                ]
            },
            request=httpx.Request("GET", "http://localhost:11434/api/tags"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await service.test_connection(
                provider_name=ProviderName.OLLAMA,
                api_key="unused",
                base_url="http://localhost:11434",
            )
        assert result.success is True
        assert "llava:latest" in result.models

    @pytest.mark.asyncio
    @patch("docmind.modules.settings.services.get_settings")
    async def test_ollama_connect_error(
        self, mock_settings: MagicMock, service: ProviderTestService
    ) -> None:
        mock_settings.return_value = MagicMock(OLLAMA_BASE_URL="http://localhost:11434")
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.ConnectError("Connection refused"),
        ):
            result = await service.test_connection(
                provider_name=ProviderName.OLLAMA,
                api_key="unused",
                base_url="http://localhost:11434",
            )
        assert result.success is False
        assert "connect" in (result.error or "").lower()


class TestProviderTestServiceDashScope:
    """Test DashScope provider connection testing."""

    @pytest.mark.asyncio
    @patch("docmind.modules.settings.services.get_settings")
    async def test_dashscope_models_endpoint_success(
        self, mock_settings: MagicMock, service: ProviderTestService
    ) -> None:
        mock_settings.return_value = MagicMock(
            DASHSCOPE_BASE_URL="https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            DASHSCOPE_MODEL="qwen-vl-max",
        )
        mock_response = httpx.Response(
            200,
            json={
                "data": [
                    {"id": "qwen-vl-max"},
                    {"id": "qwen-vl-plus"},
                ]
            },
            request=httpx.Request("GET", "https://dashscope-intl.aliyuncs.com/api/v1/models"),
        )
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, return_value=mock_response):
            result = await service.test_connection(
                provider_name=ProviderName.DASHSCOPE,
                api_key="sk-test-dashscope-key",
            )
        assert result.success is True
        assert "qwen-vl-max" in result.models

    @pytest.mark.asyncio
    @patch("docmind.modules.settings.services.get_settings")
    async def test_dashscope_fallback_generation_success(
        self, mock_settings: MagicMock, service: ProviderTestService
    ) -> None:
        mock_settings.return_value = MagicMock(
            DASHSCOPE_BASE_URL="https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            DASHSCOPE_MODEL="qwen-vl-max",
        )
        # Models endpoint fails, generation endpoint succeeds
        models_fail = httpx.Response(
            404,
            json={},
            request=httpx.Request("GET", "https://dashscope-intl.aliyuncs.com/api/v1/models"),
        )
        gen_success = httpx.Response(
            200,
            json={"output": {"text": "hi"}},
            request=httpx.Request("POST", "https://dashscope-intl.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"),
        )

        async def mock_get(*args, **kwargs):
            return models_fail

        async def mock_post(*args, **kwargs):
            return gen_success

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock, side_effect=mock_get):
            with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=mock_post):
                result = await service.test_connection(
                    provider_name=ProviderName.DASHSCOPE,
                    api_key="sk-test-key",
                )
        assert result.success is True


class TestProviderTestServiceTimeout:
    """Test timeout handling across providers."""

    @pytest.mark.asyncio
    async def test_timeout_returns_error(self, service: ProviderTestService) -> None:
        with patch(
            "httpx.AsyncClient.get",
            new_callable=AsyncMock,
            side_effect=httpx.TimeoutException("Timed out"),
        ):
            result = await service.test_connection(
                provider_name=ProviderName.OPENAI,
                api_key="sk-test-key",
            )
        assert result.success is False
        assert "timed out" in (result.error or "").lower()


class TestMaskApiKey:
    """Test API key masking."""

    def test_long_key(self) -> None:
        assert ProviderTestService.mask_api_key("sk-proj-abcdefgh12345") == "sk-proj-..."

    def test_short_key(self) -> None:
        assert ProviderTestService.mask_api_key("short") == "short..."

    def test_exact_8_chars(self) -> None:
        assert ProviderTestService.mask_api_key("12345678") == "12345678..."

    def test_longer_than_8(self) -> None:
        assert ProviderTestService.mask_api_key("123456789") == "12345678..."
