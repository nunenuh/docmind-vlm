# Backend Spec: VLM Providers

Files: `backend/src/docmind/library/providers/protocol.py`, `backend/src/docmind/library/providers/factory.py`, `backend/src/docmind/library/providers/dashscope.py`, `backend/src/docmind/library/providers/openai.py`, `backend/src/docmind/library/providers/google.py`, `backend/src/docmind/library/providers/ollama.py`

See also: [[projects/docmind-vlm/specs/backend/pipeline-processing]] · [[projects/docmind-vlm/specs/backend/pipeline-chat]]

---

## Overview

DocMind-VLM uses a **provider-agnostic VLM architecture** (ADR 8). The application code never imports a specific provider — it works through the `VLMProvider` protocol. Swapping providers requires only changing an environment variable.

```
Application code
    |
    v  library/providers/factory.py
get_vlm_provider() -> VLMProvider
    |
    v  library/providers/protocol.py (Protocol)
VLMProvider.extract() / .classify() / .chat()
    |
    v  library/providers/dashscope.py | openai.py | google.py | ollama.py
Concrete implementation (auth, API format, retry, response parsing)
```

---

## Responsibility

| File | Does |
|------|------|
| `docmind/library/providers/__init__.py` | Re-exports: `get_vlm_provider`, `VLMProvider`, `VLMResponse` |
| `docmind/library/providers/protocol.py` | Protocol definition + shared response types |
| `docmind/library/providers/factory.py` | Factory function — creates provider from env config |
| `docmind/library/providers/dashscope.py` | DashScope/Qwen-VL implementation (primary) |
| `docmind/library/providers/openai.py` | OpenAI GPT-4o Vision implementation |
| `docmind/library/providers/google.py` | Google Gemini Vision implementation |
| `docmind/library/providers/ollama.py` | Ollama local model implementation |

---

## Imports

```python
# From pipeline nodes or other code:
from docmind.library.providers import get_vlm_provider, VLMProvider, VLMResponse

# Or import specific modules:
from docmind.library.providers.protocol import VLMProvider, VLMResponse, encode_image_base64
from docmind.library.providers.factory import get_vlm_provider
```

---

## `library/providers/protocol.py`

```python
"""
docmind/library/providers/protocol.py

VLM provider protocol and shared response types.

All providers must implement this protocol. Application code depends
only on VLMProvider and VLMResponse — never on provider-specific types.
"""
from typing import Protocol, TypedDict
import base64
import numpy as np


class VLMResponse(TypedDict):
    """
    Standard response from any VLM provider.

    Attributes:
        content: Raw text content from the VLM response.
        structured_data: Parsed JSON data (extracted fields, classification, etc.).
        confidence: Model-reported confidence score, 0.0-1.0.
        model: Model identifier string (e.g. "qwen-vl-max", "gpt-4o").
        usage: Token usage dict with "input_tokens" and "output_tokens" keys.
        raw_response: Full provider response for debugging (not exposed to API).
    """
    content: str
    structured_data: dict
    confidence: float
    model: str
    usage: dict
    raw_response: dict


class VLMProvider(Protocol):
    """
    Protocol for Vision Language Model providers.

    All providers must implement these methods. The protocol ensures
    provider-agnostic code throughout the application.
    """

    async def extract(
        self,
        images: list[np.ndarray],
        prompt: str,
        schema: dict | None = None,
    ) -> VLMResponse:
        """
        Extract structured data from document images.

        Args:
            images: List of BGR uint8 page images.
            prompt: Extraction prompt (general or template-specific).
            schema: Optional JSON schema for structured output.

        Returns:
            VLMResponse with extracted fields in structured_data.
        """
        ...

    async def classify(
        self,
        image: np.ndarray,
        categories: list[str],
    ) -> VLMResponse:
        """
        Classify document type from first page image.

        Args:
            image: First page of the document (BGR uint8).
            categories: List of valid document type strings.

        Returns:
            VLMResponse with classification in structured_data:
                {"document_type": str, "confidence": float}
        """
        ...

    async def chat(
        self,
        images: list[np.ndarray],
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> VLMResponse:
        """
        Chat about document content with conversation history.

        Args:
            images: Document page images for visual grounding.
            message: Current user message.
            history: Previous messages as [{"role": str, "content": str}, ...].
            system_prompt: System prompt enforcing grounding rules.

        Returns:
            VLMResponse with answer in content and citations in structured_data.
        """
        ...

    async def health_check(self) -> bool:
        """
        Check if the provider is reachable and authenticated.

        Returns:
            True if healthy, False otherwise.
        """
        ...

    @property
    def provider_name(self) -> str:
        """Human-readable provider name (e.g. 'DashScope', 'OpenAI')."""
        ...

    @property
    def model_name(self) -> str:
        """Model identifier (e.g. 'qwen-vl-max', 'gpt-4o')."""
        ...


def encode_image_base64(image: np.ndarray) -> str:
    """
    Encode a BGR ndarray as base64 JPEG string.

    Used by all providers to prepare images for API submission.

    Args:
        image: BGR uint8 ndarray.

    Returns:
        Base64-encoded JPEG string.
    """
    import cv2
    _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buffer.tobytes()).decode("utf-8")
```

---

## `library/providers/factory.py`

```python
"""
docmind/library/providers/factory.py

Factory function for creating VLM provider instances.

Provider selection is driven by the VLM_PROVIDER environment variable.
Each provider validates its own required env vars on construction.
"""
import logging

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider

logger = logging.getLogger(__name__)

# Provider registry — maps env var values to constructor callables
_PROVIDER_REGISTRY: dict[str, type] = {}


def register_provider(name: str, cls: type) -> None:
    """Register a provider class in the factory registry."""
    _PROVIDER_REGISTRY[name] = cls


def get_vlm_provider() -> VLMProvider:
    """
    Create and return the configured VLM provider.

    Reads VLM_PROVIDER from settings to determine which provider to use.
    Each provider validates its own API key / base URL on construction.

    Returns:
        Configured VLMProvider instance.

    Raises:
        ValueError: If VLM_PROVIDER is not set or not recognized.
        RuntimeError: If the provider's required env vars are missing.
    """
    settings = get_settings()
    provider_name = settings.VLM_PROVIDER

    if not provider_name:
        raise ValueError(
            "VLM_PROVIDER environment variable is not set. "
            "Options: dashscope, openai, google, ollama"
        )

    # Lazy imports to avoid loading unused provider dependencies
    if provider_name == "dashscope" and "dashscope" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.dashscope import DashScopeProvider
        register_provider("dashscope", DashScopeProvider)

    if provider_name == "openai" and "openai" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.openai import OpenAIProvider
        register_provider("openai", OpenAIProvider)

    if provider_name == "google" and "google" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.google import GoogleProvider
        register_provider("google", GoogleProvider)

    if provider_name == "ollama" and "ollama" not in _PROVIDER_REGISTRY:
        from docmind.library.providers.ollama import OllamaProvider
        register_provider("ollama", OllamaProvider)

    provider_cls = _PROVIDER_REGISTRY.get(provider_name)
    if provider_cls is None:
        raise ValueError(
            f"Unknown VLM provider: '{provider_name}'. "
            f"Available: {list(_PROVIDER_REGISTRY.keys())}"
        )

    logger.info("Creating VLM provider: %s", provider_name)
    return provider_cls()
```

---

## `library/providers/dashscope.py`

```python
"""
docmind/library/providers/dashscope.py

DashScope (Alibaba Cloud) VLM provider for Qwen-VL models.

This is the primary provider for DocMind-VLM. Uses the DashScope
multimodal conversation API with base64-encoded images.
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
RETRY_BASE_DELAY = 2.0  # seconds, doubles each retry
REQUEST_TIMEOUT = 120.0  # seconds


class DashScopeProvider:
    """
    DashScope VLM provider using Qwen-VL models.

    Requires DASHSCOPE_API_KEY environment variable.
    """

    def __init__(self) -> None:
        """
        Initialize the DashScope provider.

        Raises:
            RuntimeError: If DASHSCOPE_API_KEY is not set.
        """
        settings = get_settings()
        self._api_key = settings.DASHSCOPE_API_KEY
        if not self._api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY environment variable is required "
                "when VLM_PROVIDER=dashscope"
            )
        self._model = settings.DASHSCOPE_MODEL or DEFAULT_MODEL
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    @property
    def provider_name(self) -> str:
        return "DashScope"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(
        self,
        images: list[np.ndarray],
        prompt: str,
        schema: dict | None = None,
    ) -> VLMResponse:
        """
        Extract structured data from document images.

        Constructs a multimodal payload with all page images and the
        extraction prompt. If a schema is provided, it is included in
        the prompt to guide structured output.
        """
        image_contents = [
            {"image": f"data:image/jpeg;base64,{encode_image_base64(img)}"}
            for img in images
        ]

        extraction_prompt = prompt
        if schema is not None:
            extraction_prompt += (
                "\n\nRespond with valid JSON matching this schema:\n"
                f"```json\n{json.dumps(schema, indent=2)}\n```"
            )

        user_content = image_contents + [{"text": extraction_prompt}]

        messages = [
            {
                "role": "system",
                "content": [{"text": (
                    "You are a document extraction assistant. Extract all requested "
                    "information from the provided document images. Return structured "
                    "JSON. If a field is not visible or legible, set its value to null "
                    "and set confidence to 0.0."
                )}],
            },
            {"role": "user", "content": user_content},
        ]

        return await self._call_api(messages)

    async def classify(
        self,
        image: np.ndarray,
        categories: list[str],
    ) -> VLMResponse:
        """Classify document type from first page."""
        categories_str = ", ".join(categories)
        prompt = (
            f"Classify this document into one of these categories: {categories_str}.\n"
            'Respond with JSON: {"document_type": "<category>", "confidence": <0.0-1.0>}'
        )

        messages = [
            {
                "role": "user",
                "content": [
                    {"image": f"data:image/jpeg;base64,{encode_image_base64(image)}"},
                    {"text": prompt},
                ],
            },
        ]

        return await self._call_api(messages)

    async def chat(
        self,
        images: list[np.ndarray],
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> VLMResponse:
        """Chat about document content with conversation history."""
        image_contents = [
            {"image": f"data:image/jpeg;base64,{encode_image_base64(img)}"}
            for img in images
        ]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": [{"text": system_prompt}]},
        ]

        # First user message includes images for grounding
        if history:
            first_user_content = image_contents + [{"text": history[0]["content"]}]
            messages.append({"role": "user", "content": first_user_content})

            for msg in history[1:]:
                messages.append({
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}],
                })
        else:
            # No history — include images with current message
            current_content = image_contents + [{"text": message}]
            messages.append({"role": "user", "content": current_content})
            return await self._call_api(messages)

        # Append current message
        messages.append({"role": "user", "content": [{"text": message}]})
        return await self._call_api(messages)

    async def health_check(self) -> bool:
        """Check DashScope API connectivity."""
        try:
            response = await self._client.post(
                BASE_URL,
                headers=self._build_headers(),
                json={
                    "model": self._model,
                    "input": {
                        "messages": [
                            {"role": "user", "content": [{"text": "ping"}]},
                        ],
                    },
                    "parameters": {"max_tokens": 1},
                },
            )
            return response.status_code in (200, 400)  # 400 = valid auth, bad request
        except Exception as e:
            logger.warning("DashScope health check failed: %s", e)
            return False

    def _build_headers(self) -> dict[str, str]:
        """Build request headers with auth."""
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _build_payload(self, messages: list[dict]) -> dict:
        """Build the DashScope multimodal API payload."""
        return {
            "model": self._model,
            "input": {"messages": messages},
            "parameters": {
                "max_tokens": 4096,
                "temperature": 0.1,
                "result_format": "message",
            },
        }

    async def _call_api(self, messages: list[dict]) -> VLMResponse:
        """
        Call the DashScope API with retry and exponential backoff.

        Raises:
            RuntimeError: If all retries exhausted.
        """
        payload = self._build_payload(messages)
        headers = self._build_headers()
        last_error: Exception | None = None

        for attempt in range(MAX_RETRIES):
            try:
                response = await self._client.post(
                    BASE_URL,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                return self._parse_response(response.json())

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    wait = RETRY_BASE_DELAY * (2 ** attempt)
                    logger.warning(
                        "DashScope rate limited. Waiting %.1fs (attempt %d/%d)",
                        wait, attempt + 1, MAX_RETRIES,
                    )
                    time.sleep(wait)
                    continue
                logger.error("DashScope API error: %d %s", e.response.status_code, e.response.text)
                raise RuntimeError(f"DashScope API error: {e.response.status_code}") from e

            except httpx.RequestError as e:
                last_error = e
                wait = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "DashScope request error: %s. Retrying in %.1fs (attempt %d/%d)",
                    e, wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"DashScope API failed after {MAX_RETRIES} retries: {last_error}"
        )

    def _parse_response(self, raw: dict) -> VLMResponse:
        """Parse DashScope API response into VLMResponse."""
        output = raw.get("output", {})
        choices = output.get("choices", [{}])
        message = choices[0].get("message", {}) if choices else {}
        content = ""

        # Handle multimodal content format
        raw_content = message.get("content", "")
        if isinstance(raw_content, list):
            content = " ".join(
                item.get("text", "") for item in raw_content if "text" in item
            )
        else:
            content = str(raw_content)

        # Try to parse JSON from content
        structured_data: dict = {}
        confidence = 0.0
        try:
            # Handle markdown code blocks
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            structured_data = json.loads(text)
            confidence = structured_data.get("confidence", 0.8)
        except (json.JSONDecodeError, IndexError):
            structured_data = {"raw_text": content}
            confidence = 0.5

        usage = raw.get("usage", {})

        return VLMResponse(
            content=content,
            structured_data=structured_data,
            confidence=float(confidence),
            model=self._model,
            usage={
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            },
            raw_response=raw,
        )
```

---

## `library/providers/openai.py`

```python
"""
docmind/library/providers/openai.py

OpenAI GPT-4o Vision provider (skeleton).

Uses the OpenAI chat completions API with image_url content type.
"""
import json
import logging

import numpy as np
import openai

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider, VLMResponse, encode_image_base64

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    """
    OpenAI Vision provider using GPT-4o.

    Requires OPENAI_API_KEY environment variable.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required when VLM_PROVIDER=openai")
        self._client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self._model = settings.OPENAI_MODEL or DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(
        self,
        images: list[np.ndarray],
        prompt: str,
        schema: dict | None = None,
    ) -> VLMResponse:
        """Extract structured data using GPT-4o vision."""
        image_messages = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image_base64(img)}",
                    "detail": "high",
                },
            }
            for img in images
        ]

        extraction_prompt = prompt
        if schema is not None:
            extraction_prompt += (
                "\n\nRespond with valid JSON matching this schema:\n"
                f"```json\n{json.dumps(schema, indent=2)}\n```"
            )

        content = image_messages + [{"type": "text", "text": extraction_prompt}]

        response = await self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": (
                    "You are a document extraction assistant. Extract all requested "
                    "information accurately. Return structured JSON."
                )},
                {"role": "user", "content": content},
            ],
            max_tokens=4096,
            temperature=0.1,
        )

        return self._parse_response(response)

    async def classify(self, image: np.ndarray, categories: list[str]) -> VLMResponse:
        raise NotImplementedError("OpenAI classify not yet implemented")

    async def chat(self, images: list[np.ndarray], message: str, history: list[dict], system_prompt: str) -> VLMResponse:
        raise NotImplementedError("OpenAI chat not yet implemented")

    async def health_check(self) -> bool:
        try:
            await self._client.models.retrieve(self._model)
            return True
        except Exception as e:
            logger.warning("OpenAI health check failed: %s", e)
            return False

    def _parse_response(self, response) -> VLMResponse:
        """Parse OpenAI response into VLMResponse."""
        content = response.choices[0].message.content or ""
        structured_data: dict = {}
        confidence = 0.0

        try:
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            structured_data = json.loads(text)
            confidence = structured_data.get("confidence", 0.8)
        except (json.JSONDecodeError, IndexError):
            structured_data = {"raw_text": content}
            confidence = 0.5

        usage = response.usage
        return VLMResponse(
            content=content,
            structured_data=structured_data,
            confidence=float(confidence),
            model=self._model,
            usage={
                "input_tokens": usage.prompt_tokens if usage else 0,
                "output_tokens": usage.completion_tokens if usage else 0,
            },
            raw_response={"choices": [{"message": {"content": content}}]},
        )
```

---

## `library/providers/google.py`

```python
"""
docmind/library/providers/google.py

Google Gemini Vision provider (skeleton).

Uses the Google Generative AI SDK with inline image data.
"""
import logging

import numpy as np

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider, VLMResponse, encode_image_base64

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "gemini-2.0-flash"


class GoogleProvider:
    """
    Google Gemini Vision provider.

    Requires GOOGLE_API_KEY environment variable.
    """

    def __init__(self) -> None:
        settings = get_settings()
        if not settings.GOOGLE_API_KEY:
            raise RuntimeError("GOOGLE_API_KEY is required when VLM_PROVIDER=google")
        self._api_key = settings.GOOGLE_API_KEY
        self._model = settings.GOOGLE_MODEL or DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "Google"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(self, images: list[np.ndarray], prompt: str, schema: dict | None = None) -> VLMResponse:
        raise NotImplementedError("Google extract not yet implemented")

    async def classify(self, image: np.ndarray, categories: list[str]) -> VLMResponse:
        raise NotImplementedError("Google classify not yet implemented")

    async def chat(self, images: list[np.ndarray], message: str, history: list[dict], system_prompt: str) -> VLMResponse:
        raise NotImplementedError("Google chat not yet implemented")

    async def health_check(self) -> bool:
        try:
            import httpx
            response = await httpx.AsyncClient().get(
                f"https://generativelanguage.googleapis.com/v1/models/{self._model}",
                params={"key": self._api_key},
            )
            return response.status_code == 200
        except Exception as e:
            logger.warning("Google health check failed: %s", e)
            return False
```

---

## `library/providers/ollama.py`

```python
"""
docmind/library/providers/ollama.py

Ollama local model provider (skeleton).

Uses the Ollama HTTP API for local VLM inference.
Useful for development, air-gapped environments, and cost control.
"""
import logging

import numpy as np

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider, VLMResponse, encode_image_base64

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "llava:13b"
DEFAULT_BASE_URL = "http://localhost:11434"


class OllamaProvider:
    """
    Ollama local VLM provider.

    Requires OLLAMA_BASE_URL (defaults to localhost:11434).
    No API key needed for local inference.
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.OLLAMA_BASE_URL or DEFAULT_BASE_URL
        self._model = settings.OLLAMA_MODEL or DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "Ollama"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(self, images: list[np.ndarray], prompt: str, schema: dict | None = None) -> VLMResponse:
        raise NotImplementedError("Ollama extract not yet implemented")

    async def classify(self, image: np.ndarray, categories: list[str]) -> VLMResponse:
        raise NotImplementedError("Ollama classify not yet implemented")

    async def chat(self, images: list[np.ndarray], message: str, history: list[dict], system_prompt: str) -> VLMResponse:
        raise NotImplementedError("Ollama chat not yet implemented")

    async def health_check(self) -> bool:
        try:
            import httpx
            response = await httpx.AsyncClient().get(f"{self._base_url}/api/tags")
            return response.status_code == 200
        except Exception as e:
            logger.warning("Ollama health check failed: %s", e)
            return False
```

---

## `library/providers/__init__.py`

```python
"""
docmind/library/providers/__init__.py

Re-exports for convenient access to VLM provider types and factory.
"""
from .protocol import VLMProvider, VLMResponse
from .factory import get_vlm_provider
```

---

## Provider Comparison

| Provider | Model | Strengths | Weaknesses | Cost |
|----------|-------|-----------|------------|------|
| **DashScope** (primary) | Qwen-VL-Max | Best price/performance, CJK support, structured output | Newer API, fewer examples | ~$0.004/image |
| **OpenAI** | GPT-4o | Highest accuracy, best docs, widest adoption | Most expensive, rate limits | ~$0.015/image |
| **Google** | Gemini 2.0 Flash | Fast, good multimodal, generous free tier | Less consistent JSON output | ~$0.002/image |
| **Ollama** | LLaVA 13B | Free, local, air-gapped | Lower accuracy, GPU required | Free (compute cost) |

---

## Environment Variables

```bash
# Required: choose one provider
VLM_PROVIDER=dashscope  # dashscope | openai | google | ollama

# DashScope (when VLM_PROVIDER=dashscope)
DASHSCOPE_API_KEY=sk-...
DASHSCOPE_MODEL=qwen-vl-max  # optional, default: qwen-vl-max

# OpenAI (when VLM_PROVIDER=openai)
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o  # optional, default: gpt-4o

# Google (when VLM_PROVIDER=google)
GOOGLE_API_KEY=AIza...
GOOGLE_MODEL=gemini-2.0-flash  # optional, default: gemini-2.0-flash

# Ollama (when VLM_PROVIDER=ollama)
OLLAMA_BASE_URL=http://localhost:11434  # optional, default: localhost:11434
OLLAMA_MODEL=llava:13b  # optional, default: llava:13b
```

---

## Rules

- **Each provider handles its own auth, rate limiting, retry, and response parsing.** No shared retry logic — providers have different error codes and backoff rules.
- **Never expose provider-specific types outside the provider module.** All application code depends only on `VLMProvider` protocol and `VLMResponse` TypedDict.
- **Factory uses lazy imports** to avoid loading unused provider dependencies (e.g., don't import `openai` when using DashScope).
- **Images are always base64 JPEG** when sent to providers. Use `encode_image_base64()` from `protocol.py`.
- **Confidence scores are normalized to [0.0, 1.0]** by each provider — even if the raw API uses different scales.
- **`raw_response` is for debugging only** — never expose it through the API layer.
