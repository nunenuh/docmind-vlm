# Issue #9: DashScope VLM Provider — Extract, Classify, Chat Implementation

## Summary

Implement the `extract()`, `classify()`, and `chat()` methods on the `DashScopeProvider` class, the primary VLM provider for DocMind-VLM. The scaffold has these methods raising `NotImplementedError`. This issue replaces them with working implementations that call the DashScope multimodal generation API using `httpx`, handle retry with exponential backoff on rate limits and transient errors, and parse responses into the standard `VLMResponse` TypedDict. All API interactions are tested via mocked `httpx` responses — no real API calls in tests.

## Context

- **Phase**: 2 — CV + VLM Providers
- **Priority**: P0
- **Labels**: `phase-2-cv-vlm`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: None (protocol.py and config.py are already scaffolded)
- **Branch**: `feat/9-dashscope-provider`
- **Estimated scope**: L

## Specs to Read

- `specs/backend/providers.md` — full DashScope provider section, VLMProvider protocol, VLMResponse TypedDict, provider rules
- `specs/backend/cv.md` — `encode_image_base64` usage
- `specs/system.md` — env vars (`DASHSCOPE_API_KEY`, `DASHSCOPE_MODEL`)
- `specs/conventions/python-conventions.md` — PEP 8, type hints, error handling

## Current State (Scaffold)

The scaffold at `backend/src/docmind/library/providers/dashscope.py`:

```python
"""
docmind/library/providers/dashscope.py

DashScope (Alibaba Cloud) VLM provider for Qwen-VL models.
"""
import json
import logging
import time
from typing import Any

import httpx
import numpy as np

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider, VLMResponse, encode_image_base64

logger = logging.getLogger(__name__)
BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
DEFAULT_MODEL = "qwen-vl-max"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0
REQUEST_TIMEOUT = 120.0


class DashScopeProvider:
    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.DASHSCOPE_API_KEY
        if not self._api_key:
            raise RuntimeError("DASHSCOPE_API_KEY environment variable is required when VLM_PROVIDER=dashscope")
        self._model = settings.DASHSCOPE_MODEL or DEFAULT_MODEL
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    @property
    def provider_name(self) -> str:
        return "DashScope"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(self, images: list[np.ndarray], prompt: str, schema: dict | None = None) -> VLMResponse:
        raise NotImplementedError("DashScope extract not yet implemented in scaffold")

    async def classify(self, image: np.ndarray, categories: list[str]) -> VLMResponse:
        raise NotImplementedError("DashScope classify not yet implemented in scaffold")

    async def chat(self, images: list[np.ndarray], message: str, history: list[dict], system_prompt: str) -> VLMResponse:
        raise NotImplementedError("DashScope chat not yet implemented in scaffold")

    async def health_check(self) -> bool:
        try:
            response = await self._client.post(
                BASE_URL,
                headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
                json={"model": self._model, "input": {"messages": [{"role": "user", "content": [{"text": "ping"}]}]}, "parameters": {"max_tokens": 1}},
            )
            return response.status_code in (200, 400)
        except Exception as e:
            logger.warning("DashScope health check failed: %s", e)
            return False
```

The protocol at `backend/src/docmind/library/providers/protocol.py`:

```python
class VLMResponse(TypedDict):
    content: str
    structured_data: dict
    confidence: float
    model: str
    usage: dict
    raw_response: dict


class VLMProvider(Protocol):
    async def extract(self, images: list[np.ndarray], prompt: str, schema: dict | None = None) -> VLMResponse: ...
    async def classify(self, image: np.ndarray, categories: list[str]) -> VLMResponse: ...
    async def chat(self, images: list[np.ndarray], message: str, history: list[dict], system_prompt: str) -> VLMResponse: ...
    async def health_check(self) -> bool: ...

    @property
    def provider_name(self) -> str: ...
    @property
    def model_name(self) -> str: ...
```

The config at `backend/src/docmind/core/config.py` includes:

```python
VLM_PROVIDER: str = Field(default="dashscope")
DASHSCOPE_API_KEY: str = Field(default="")
DASHSCOPE_MODEL: str = Field(default="qwen-vl-max")
```

The test directory `backend/tests/unit/library/providers/` exists but contains no test files.

## Requirements

### Functional

1. `extract(images, prompt, schema=None)` must construct a multimodal payload with base64-encoded page images and the extraction prompt
2. `extract` must append JSON schema to prompt when `schema` is provided
3. `extract` must include a system prompt instructing structured JSON extraction
4. `classify(image, categories)` must construct a prompt asking for classification into the given categories
5. `classify` must request JSON response with `document_type` and `confidence` fields
6. `chat(images, message, history, system_prompt)` must include images in the first user message for visual grounding
7. `chat` must correctly interleave conversation history
8. `chat` with no history must include images alongside the current message
9. All methods must call `_call_api` which handles retry with exponential backoff
10. `_call_api` must retry up to `MAX_RETRIES` (3) times on rate limit (429) and transient network errors
11. `_call_api` must raise `RuntimeError` on non-retryable HTTP errors (4xx other than 429, 5xx)
12. `_call_api` must raise `RuntimeError` after all retries exhausted
13. `_parse_response` must extract content text from DashScope multimodal response format
14. `_parse_response` must attempt JSON parsing of content (handling markdown code blocks)
15. `_parse_response` must fall back to `{"raw_text": content}` with confidence 0.5 on parse failure
16. `_parse_response` must extract usage tokens from response
17. `health_check` must return True for 200 or 400 status (valid auth), False on errors

### Non-Functional

- API key is never logged or exposed in error messages
- Rate limit retries use exponential backoff: `RETRY_BASE_DELAY * 2^attempt`
- Request timeout is 120 seconds
- Images are sent as base64 JPEG via `encode_image_base64`
- Confidence scores normalized to [0.0, 1.0]
- `raw_response` is included for debugging but never exposed through the API layer

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/providers/test_dashscope.py`

```python
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
            with pytest.raises(RuntimeError, match=f"failed after {MAX_RETRIES} retries"):
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

        # Verify backoff delays: 2.0, 4.0, 8.0 (but only MAX_RETRIES-1 sleeps
        # since the last attempt raises without sleeping after)
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
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/providers/dashscope.py` — Replace `NotImplementedError` stubs with full implementation

**Implementation guidance**:

Replace the three `NotImplementedError` methods with the implementations from `specs/backend/providers.md`. The key additions:

1. **`extract` method**: Build multimodal messages with base64 images + extraction prompt. If schema provided, append to prompt. Include system message. Call `_call_api`.

2. **`classify` method**: Build prompt with categories list. Send single image + classification prompt. Call `_call_api`.

3. **`chat` method**: Handle two cases:
   - No history: images + current message in one user message
   - With history: images in first user message, then interleave history, then current message

4. **`_build_headers` helper**: Return auth and content-type headers.

5. **`_build_payload` helper**: Build the DashScope payload structure with model, messages, and parameters.

6. **`_call_api` method**: POST to BASE_URL with retry. On 429: sleep and retry. On other HTTP errors: raise immediately. On network errors: sleep and retry. After MAX_RETRIES: raise RuntimeError.

7. **`_parse_response` method**: Extract content from DashScope format (may be list of content items). Try JSON parsing (handle markdown code blocks). Fall back to raw_text with confidence 0.5.

Gotchas:
- DashScope content format is `[{"text": "..."}, {"image": "..."}]` — different from OpenAI
- `time.sleep` is used for retry (not `asyncio.sleep`) — this is intentional in the spec to keep it simple, but could be improved later
- Must handle both list and string content formats in response parsing

### Step 3: Refactor (IMPROVE)

- Add full docstrings to all methods
- Consider extracting message construction into helper methods
- Ensure no API key leakage in logs or error messages
- Add type annotations to all private methods

## Acceptance Criteria

- [ ] `extract()` sends multimodal payload with base64 images and returns parsed VLMResponse
- [ ] `extract()` includes JSON schema in prompt when provided
- [ ] `classify()` sends single image with categories prompt and returns classification
- [ ] `chat()` correctly handles no-history and with-history cases
- [ ] `chat()` includes images in first user message for visual grounding
- [ ] `_call_api` retries on 429 rate limit with exponential backoff
- [ ] `_call_api` retries on network errors with exponential backoff
- [ ] `_call_api` raises RuntimeError on non-retryable HTTP errors
- [ ] `_call_api` raises RuntimeError after MAX_RETRIES exhausted
- [ ] `_parse_response` handles JSON, markdown-wrapped JSON, and non-JSON content
- [ ] `health_check` returns True for 200/400, False for errors
- [ ] No API key is logged or exposed in error messages
- [ ] All tests pass with `pytest backend/tests/unit/library/providers/test_dashscope.py -v`

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/tests/unit/library/providers/__init__.py` | Create | Empty `__init__.py` for test package |
| `backend/tests/unit/library/providers/test_dashscope.py` | Create | Unit tests for DashScope provider |
| `backend/src/docmind/library/providers/dashscope.py` | Modify | Implement extract, classify, chat, _call_api, _parse_response, _build_headers, _build_payload |

## Verification

```bash
# Run the tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/providers/test_dashscope.py -v

# Run with coverage
python -m pytest backend/tests/unit/library/providers/test_dashscope.py -v --cov=docmind.library.providers.dashscope --cov-report=term-missing

# Lint
ruff check backend/src/docmind/library/providers/dashscope.py
```
