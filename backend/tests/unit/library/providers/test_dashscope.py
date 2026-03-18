"""
Tests for docmind.library.providers.dashscope module.

All DashScope API calls are mocked — no real API calls.
Tests verify request construction, response parsing, retry logic,
and error handling.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import numpy as np
import pytest

from docmind.library.providers.dashscope import (
    BASE_URL,
    DEFAULT_MODEL,
    MAX_RETRIES,
    RETRY_BASE_DELAY,
    DashScopeProvider,
)
from docmind.library.providers.protocol import VLMResponse


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_settings():
    """Mock settings with valid DashScope config."""
    settings = MagicMock()
    settings.DASHSCOPE_API_KEY = "test-api-key-12345"
    settings.DASHSCOPE_MODEL = "qwen-vl-max"
    return settings


@pytest.fixture
def provider(mock_settings) -> DashScopeProvider:
    """Create a DashScopeProvider with mocked settings."""
    with patch("docmind.library.providers.dashscope.get_settings", return_value=mock_settings):
        return DashScopeProvider()


@pytest.fixture
def sample_image() -> np.ndarray:
    """Small BGR test image."""
    return np.zeros((100, 100, 3), dtype=np.uint8)


@pytest.fixture
def sample_images(sample_image: np.ndarray) -> list[np.ndarray]:
    """List of test images (2 pages)."""
    return [sample_image, sample_image.copy()]


@pytest.fixture
def successful_extract_response() -> dict:
    """Mock DashScope API response for extraction."""
    return {
        "output": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "text": json.dumps({
                                    "invoice_number": "INV-001",
                                    "total": 150.00,
                                    "confidence": 0.95,
                                })
                            }
                        ],
                    }
                }
            ]
        },
        "usage": {
            "input_tokens": 500,
            "output_tokens": 100,
        },
    }


@pytest.fixture
def successful_classify_response() -> dict:
    """Mock DashScope API response for classification."""
    return {
        "output": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "text": json.dumps({
                                    "document_type": "invoice",
                                    "confidence": 0.92,
                                })
                            }
                        ],
                    }
                }
            ]
        },
        "usage": {
            "input_tokens": 300,
            "output_tokens": 50,
        },
    }


@pytest.fixture
def successful_chat_response() -> dict:
    """Mock DashScope API response for chat."""
    return {
        "output": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"text": "The invoice total is $150.00 as shown in the bottom-right section."}
                        ],
                    }
                }
            ]
        },
        "usage": {
            "input_tokens": 800,
            "output_tokens": 50,
        },
    }


@pytest.fixture
def markdown_wrapped_response() -> dict:
    """Mock response with JSON wrapped in markdown code block."""
    return {
        "output": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "text": '```json\n{"document_type": "receipt", "confidence": 0.88}\n```'
                            }
                        ],
                    }
                }
            ]
        },
        "usage": {"input_tokens": 100, "output_tokens": 30},
    }


@pytest.fixture
def non_json_response() -> dict:
    """Mock response with plain text (not JSON)."""
    return {
        "output": {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": [
                            {"text": "I cannot determine the document type from this image."}
                        ],
                    }
                }
            ]
        },
        "usage": {"input_tokens": 100, "output_tokens": 20},
    }


def _mock_httpx_response(status_code: int, json_data: dict) -> httpx.Response:
    """Create a mock httpx.Response."""
    response = httpx.Response(
        status_code=status_code,
        json=json_data,
        request=httpx.Request("POST", BASE_URL),
    )
    return response


# ---------------------------------------------------------------------------
# Constructor
# ---------------------------------------------------------------------------

class TestDashScopeProviderInit:
    """Tests for DashScopeProvider initialization."""

    def test_creates_with_valid_config(self, mock_settings) -> None:
        with patch("docmind.library.providers.dashscope.get_settings", return_value=mock_settings):
            provider = DashScopeProvider()
            assert provider.provider_name == "DashScope"
            assert provider.model_name == "qwen-vl-max"

    def test_raises_on_missing_api_key(self) -> None:
        settings = MagicMock()
        settings.DASHSCOPE_API_KEY = ""
        settings.DASHSCOPE_MODEL = "qwen-vl-max"
        with patch("docmind.library.providers.dashscope.get_settings", return_value=settings):
            with pytest.raises(RuntimeError, match="DASHSCOPE_API_KEY"):
                DashScopeProvider()

    def test_uses_default_model(self) -> None:
        settings = MagicMock()
        settings.DASHSCOPE_API_KEY = "test-key"
        settings.DASHSCOPE_MODEL = ""
        with patch("docmind.library.providers.dashscope.get_settings", return_value=settings):
            provider = DashScopeProvider()
            assert provider.model_name == DEFAULT_MODEL

    def test_provider_name_property(self, provider: DashScopeProvider) -> None:
        assert provider.provider_name == "DashScope"

    def test_model_name_property(self, provider: DashScopeProvider) -> None:
        assert provider.model_name == "qwen-vl-max"


# ---------------------------------------------------------------------------
# extract
# ---------------------------------------------------------------------------

class TestDashScopeExtract:
    """Tests for DashScopeProvider.extract method."""

    @pytest.mark.asyncio
    async def test_returns_vlm_response(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_extract_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_extract_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        result = await provider.extract(sample_images, "Extract invoice fields")

        assert isinstance(result, dict)
        assert "content" in result
        assert "structured_data" in result
        assert "confidence" in result
        assert "model" in result
        assert "usage" in result
        assert "raw_response" in result

    @pytest.mark.asyncio
    async def test_structured_data_parsed(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_extract_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_extract_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        result = await provider.extract(sample_images, "Extract invoice fields")

        assert result["structured_data"]["invoice_number"] == "INV-001"
        assert result["structured_data"]["total"] == 150.00
        assert result["confidence"] == 0.95

    @pytest.mark.asyncio
    async def test_sends_images_as_base64(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_extract_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_extract_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        await provider.extract(sample_images, "Extract")

        # Verify the API was called
        provider._client.post.assert_called_once()
        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]

        # Find user message with image content
        user_msg = [m for m in messages if m["role"] == "user"][0]
        image_items = [c for c in user_msg["content"] if "image" in c]
        assert len(image_items) == 2  # 2 pages
        for item in image_items:
            assert item["image"].startswith("data:image/jpeg;base64,")

    @pytest.mark.asyncio
    async def test_includes_schema_in_prompt(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_extract_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_extract_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        schema = {"type": "object", "properties": {"total": {"type": "number"}}}
        await provider.extract(sample_images, "Extract", schema=schema)

        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        text_items = [c for c in user_msg["content"] if "text" in c]
        prompt_text = text_items[0]["text"]
        assert "Respond with valid JSON matching this schema" in prompt_text

    @pytest.mark.asyncio
    async def test_includes_system_message(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_extract_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_extract_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        await provider.extract(sample_images, "Extract")

        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) == 1

    @pytest.mark.asyncio
    async def test_usage_tokens(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_extract_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_extract_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        result = await provider.extract(sample_images, "Extract")

        assert result["usage"]["input_tokens"] == 500
        assert result["usage"]["output_tokens"] == 100


# ---------------------------------------------------------------------------
# classify
# ---------------------------------------------------------------------------

class TestDashScopeClassify:
    """Tests for DashScopeProvider.classify method."""

    @pytest.mark.asyncio
    async def test_returns_classification(
        self,
        provider: DashScopeProvider,
        sample_image: np.ndarray,
        successful_classify_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_classify_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        result = await provider.classify(sample_image, ["invoice", "receipt", "contract"])

        assert result["structured_data"]["document_type"] == "invoice"
        assert result["confidence"] == 0.92

    @pytest.mark.asyncio
    async def test_sends_single_image(
        self,
        provider: DashScopeProvider,
        sample_image: np.ndarray,
        successful_classify_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_classify_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        await provider.classify(sample_image, ["invoice", "receipt"])

        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        image_items = [c for c in user_msg["content"] if "image" in c]
        assert len(image_items) == 1

    @pytest.mark.asyncio
    async def test_includes_categories_in_prompt(
        self,
        provider: DashScopeProvider,
        sample_image: np.ndarray,
        successful_classify_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_classify_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        await provider.classify(sample_image, ["invoice", "receipt", "contract"])

        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]
        user_msg = [m for m in messages if m["role"] == "user"][0]
        text_items = [c for c in user_msg["content"] if "text" in c]
        prompt_text = text_items[0]["text"]
        assert "invoice" in prompt_text
        assert "receipt" in prompt_text
        assert "contract" in prompt_text


# ---------------------------------------------------------------------------
# chat
# ---------------------------------------------------------------------------

class TestDashScopeChat:
    """Tests for DashScopeProvider.chat method."""

    @pytest.mark.asyncio
    async def test_returns_chat_response(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_chat_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_chat_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        result = await provider.chat(
            sample_images, "What is the total?", [], "You are a document assistant."
        )

        assert "content" in result
        assert "150.00" in result["content"]

    @pytest.mark.asyncio
    async def test_no_history_includes_images_with_message(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_chat_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_chat_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        await provider.chat(sample_images, "What is this?", [], "System prompt")

        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]

        # With no history, images should be in the user message
        user_msgs = [m for m in messages if m["role"] == "user"]
        assert len(user_msgs) == 1
        image_items = [c for c in user_msgs[0]["content"] if "image" in c]
        assert len(image_items) == 2  # 2 page images

    @pytest.mark.asyncio
    async def test_with_history_includes_images_in_first_user_msg(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_chat_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_chat_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        history = [
            {"role": "user", "content": "What document is this?"},
            {"role": "assistant", "content": "This is an invoice."},
        ]

        await provider.chat(sample_images, "What is the total?", history, "System prompt")

        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]

        # First user message should have images
        first_user = [m for m in messages if m["role"] == "user"][0]
        image_items = [c for c in first_user["content"] if "image" in c]
        assert len(image_items) == 2

    @pytest.mark.asyncio
    async def test_includes_system_prompt(
        self,
        provider: DashScopeProvider,
        sample_images: list[np.ndarray],
        successful_chat_response: dict,
    ) -> None:
        mock_response = _mock_httpx_response(200, successful_chat_response)
        provider._client.post = AsyncMock(return_value=mock_response)

        await provider.chat(sample_images, "Hello", [], "Custom system prompt")

        call_kwargs = provider._client.post.call_args
        payload = call_kwargs.kwargs.get("json") or call_kwargs[1].get("json")
        messages = payload["input"]["messages"]
        system_msgs = [m for m in messages if m["role"] == "system"]
        assert len(system_msgs) == 1


# ---------------------------------------------------------------------------
# Response parsing
# ---------------------------------------------------------------------------

class TestResponseParsing:
    """Tests for _parse_response method."""

    def test_parses_json_content(
        self, provider: DashScopeProvider, successful_extract_response: dict
    ) -> None:
        result = provider._parse_response(successful_extract_response)
        assert result["structured_data"]["invoice_number"] == "INV-001"
        assert result["confidence"] == 0.95

    def test_parses_markdown_wrapped_json(
        self, provider: DashScopeProvider, markdown_wrapped_response: dict
    ) -> None:
        result = provider._parse_response(markdown_wrapped_response)
        assert result["structured_data"]["document_type"] == "receipt"
        assert result["confidence"] == 0.88

    def test_fallback_on_non_json(
        self, provider: DashScopeProvider, non_json_response: dict
    ) -> None:
        result = provider._parse_response(non_json_response)
        assert "raw_text" in result["structured_data"]
        assert result["confidence"] == 0.5

    def test_includes_model_name(
        self, provider: DashScopeProvider, successful_extract_response: dict
    ) -> None:
        result = provider._parse_response(successful_extract_response)
        assert result["model"] == "qwen-vl-max"

    def test_includes_usage_tokens(
        self, provider: DashScopeProvider, successful_extract_response: dict
    ) -> None:
        result = provider._parse_response(successful_extract_response)
        assert result["usage"]["input_tokens"] == 500
        assert result["usage"]["output_tokens"] == 100

    def test_includes_raw_response(
        self, provider: DashScopeProvider, successful_extract_response: dict
    ) -> None:
        result = provider._parse_response(successful_extract_response)
        assert result["raw_response"] == successful_extract_response

    def test_handles_empty_choices(self, provider: DashScopeProvider) -> None:
        raw = {"output": {"choices": []}, "usage": {}}
        result = provider._parse_response(raw)
        assert result["content"] == ""

    def test_handles_missing_usage(self, provider: DashScopeProvider) -> None:
        raw = {
            "output": {
                "choices": [{"message": {"content": [{"text": "hello"}]}}]
            },
        }
        result = provider._parse_response(raw)
        assert result["usage"]["input_tokens"] == 0
        assert result["usage"]["output_tokens"] == 0


# ---------------------------------------------------------------------------
# Retry and error handling
# ---------------------------------------------------------------------------

class TestRetryAndErrors:
    """Tests for _call_api retry logic and error handling."""

    @pytest.mark.asyncio
    async def test_retries_on_rate_limit(
        self,
        provider: DashScopeProvider,
        successful_extract_response: dict,
    ) -> None:
        """Should retry on 429 and succeed on subsequent attempt."""
        rate_limit_response = _mock_httpx_response(429, {"error": "rate limited"})
        success_response = _mock_httpx_response(200, successful_extract_response)

        provider._client.post = AsyncMock(
            side_effect=[rate_limit_response, success_response]
        )

        messages = [{"role": "user", "content": [{"text": "test"}]}]
        with patch("docmind.library.providers.dashscope.time.sleep"):
            result = await provider._call_api(messages)

        assert result["structured_data"]["invoice_number"] == "INV-001"
        assert provider._client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_retries_on_network_error(
        self,
        provider: DashScopeProvider,
        successful_extract_response: dict,
    ) -> None:
        """Should retry on transient network errors."""
        success_response = _mock_httpx_response(200, successful_extract_response)

        provider._client.post = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                success_response,
            ]
        )

        messages = [{"role": "user", "content": [{"text": "test"}]}]
        with patch("docmind.library.providers.dashscope.time.sleep"):
            result = await provider._call_api(messages)

        assert provider._client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_raises_after_max_retries(
        self,
        provider: DashScopeProvider,
    ) -> None:
        """Should raise RuntimeError after all retries exhausted."""
        provider._client.post = AsyncMock(
            side_effect=httpx.ConnectError("Connection refused")
        )

        messages = [{"role": "user", "content": [{"text": "test"}]}]
        with patch("docmind.library.providers.dashscope.time.sleep"):
            with pytest.raises(RuntimeError, match=f"failed after {MAX_RETRIES} retries$"):
                await provider._call_api(messages)

        assert provider._client.post.call_count == MAX_RETRIES

    @pytest.mark.asyncio
    async def test_raises_immediately_on_non_retryable_error(
        self,
        provider: DashScopeProvider,
    ) -> None:
        """Non-429 HTTP errors should raise immediately (no retry)."""
        error_response = _mock_httpx_response(401, {"error": "unauthorized"})
        provider._client.post = AsyncMock(return_value=error_response)

        messages = [{"role": "user", "content": [{"text": "test"}]}]
        with pytest.raises(RuntimeError, match="DashScope API error: 401"):
            await provider._call_api(messages)

        assert provider._client.post.call_count == 1

    @pytest.mark.asyncio
    async def test_exponential_backoff_delays(
        self,
        provider: DashScopeProvider,
    ) -> None:
        """Verify exponential backoff timing."""
        provider._client.post = AsyncMock(
            side_effect=httpx.ConnectError("timeout")
        )

        messages = [{"role": "user", "content": [{"text": "test"}]}]
        with patch("docmind.library.providers.dashscope.time.sleep") as mock_sleep:
            with pytest.raises(RuntimeError):
                await provider._call_api(messages)

        sleep_calls = [call.args[0] for call in mock_sleep.call_args_list]
        for i, delay in enumerate(sleep_calls):
            expected = RETRY_BASE_DELAY * (2 ** i)
            assert abs(delay - expected) < 0.01


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------

class TestHealthCheck:
    """Tests for DashScopeProvider.health_check method."""

    @pytest.mark.asyncio
    async def test_returns_true_on_200(self, provider: DashScopeProvider) -> None:
        mock_response = _mock_httpx_response(200, {})
        provider._client.post = AsyncMock(return_value=mock_response)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_returns_true_on_400(self, provider: DashScopeProvider) -> None:
        """400 means valid auth but bad request — still healthy."""
        mock_response = _mock_httpx_response(400, {"error": "bad request"})
        provider._client.post = AsyncMock(return_value=mock_response)
        assert await provider.health_check() is True

    @pytest.mark.asyncio
    async def test_returns_false_on_401(self, provider: DashScopeProvider) -> None:
        mock_response = _mock_httpx_response(401, {"error": "unauthorized"})
        provider._client.post = AsyncMock(return_value=mock_response)
        assert await provider.health_check() is False

    @pytest.mark.asyncio
    async def test_returns_false_on_exception(self, provider: DashScopeProvider) -> None:
        provider._client.post = AsyncMock(side_effect=httpx.ConnectError("timeout"))
        assert await provider.health_check() is False
