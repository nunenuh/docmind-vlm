"""
docmind/library/providers/openrouter.py

OpenRouter VLM provider — OpenAI-compatible API that routes to
Qwen-VL, GPT-4o, Gemini, and other vision models.

Single provider for both VLM (chat/extract/classify) and embeddings.
"""

import json
import logging
import time
from typing import Any

import httpx
import numpy as np

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMResponse, encode_image_base64

logger = logging.getLogger(__name__)


class OpenRouterProvider:
    """OpenRouter VLM provider using OpenAI-compatible API.

    All configuration is read from get_settings().
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._api_key = settings.OPENROUTER_API_KEY
        if not self._api_key:
            raise RuntimeError(
                "OPENROUTER_API_KEY is required when VLM_PROVIDER=openrouter"
            )
        self._model = settings.OPENROUTER_MODEL
        self._base_url = settings.OPENROUTER_BASE_URL.rstrip("/")
        self._max_retries = settings.OPENROUTER_MAX_RETRIES
        self._retry_delay = settings.OPENROUTER_RETRY_DELAY
        self._timeout = settings.OPENROUTER_TIMEOUT
        self._max_tokens = settings.OPENROUTER_MAX_TOKENS
        self._temperature = settings.OPENROUTER_TEMPERATURE
        self._client = httpx.AsyncClient(timeout=self._timeout)

    @property
    def provider_name(self) -> str:
        return "OpenRouter"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(
        self,
        images: list[np.ndarray],
        prompt: str,
        schema: dict | None = None,
    ) -> VLMResponse:
        """Extract structured data from document images."""
        image_contents = [
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image_base64(img)}"
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

        user_content: list[dict[str, Any]] = image_contents + [
            {"type": "text", "text": extraction_prompt}
        ]

        messages: list[dict[str, Any]] = [
            {
                "role": "system",
                "content": (
                    "You are a document extraction assistant. Extract all requested "
                    "information from the provided document images. Return structured "
                    "JSON. If a field is not visible or legible, set its value to null "
                    "and set confidence to 0.0."
                ),
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

        messages: list[dict[str, Any]] = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{encode_image_base64(image)}"
                        },
                    },
                    {"type": "text", "text": prompt},
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
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image_base64(img)}"
                },
            }
            for img in images
        ]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": system_prompt},
        ]

        if history:
            first_user_content: list[dict[str, Any]] = image_contents + [
                {"type": "text", "text": history[0]["content"]}
            ]
            messages.append({"role": "user", "content": first_user_content})

            for msg in history[1:]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                })

            messages.append({"role": "user", "content": message})
        else:
            current_content: list[dict[str, Any]] = image_contents + [
                {"type": "text", "text": message}
            ]
            messages.append({"role": "user", "content": current_content})

        return await self._call_api(messages)

    async def health_check(self) -> bool:
        """Check OpenRouter API connectivity."""
        try:
            response = await self._client.post(
                f"{self._base_url}/chat/completions",
                headers=self._build_headers(),
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "user", "content": "ping"},
                    ],
                    "max_tokens": 1,
                },
            )
            return response.status_code in (200, 400)
        except Exception as e:
            logger.warning("OpenRouter health check failed: %s", e)
            return False

    def _build_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://docmind-vlm.nunenuh.me",
            "X-Title": "DocMind-VLM",
        }

    def _build_payload(self, messages: list[dict]) -> dict:
        return {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }

    async def _call_api(self, messages: list[dict]) -> VLMResponse:
        """Call OpenRouter API with retry and exponential backoff."""
        payload = self._build_payload(messages)
        headers = self._build_headers()
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                response = await self._client.post(
                    f"{self._base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                return self._parse_response(response.json())

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    wait = self._retry_delay * (2 ** attempt)
                    logger.warning(
                        "OpenRouter rate limited. Waiting %.1fs (attempt %d/%d)",
                        wait, attempt + 1, self._max_retries,
                    )
                    time.sleep(wait)
                    continue
                logger.error(
                    "OpenRouter API error: %d", e.response.status_code
                )
                raise RuntimeError(
                    f"OpenRouter API error: {e.response.status_code}"
                ) from e

            except httpx.RequestError as e:
                last_error = e
                wait = self._retry_delay * (2 ** attempt)
                logger.warning(
                    "OpenRouter request error: %s. Retrying in %.1fs (attempt %d/%d)",
                    e, wait, attempt + 1, self._max_retries,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"OpenRouter API failed after {self._max_retries} retries"
        ) from last_error

    def _parse_response(self, raw: dict) -> VLMResponse:
        """Parse OpenAI-compatible response into VLMResponse."""
        choices = raw.get("choices", [])
        if not choices:
            logger.warning("OpenRouter response contained no choices")
        message = choices[0].get("message", {}) if choices else {}
        content = message.get("content", "") or ""

        structured_data: dict = {}
        confidence = 0.0
        try:
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            structured_data = json.loads(text)
            raw_confidence = structured_data.get("confidence", 0.8)
            confidence = max(0.0, min(1.0, float(raw_confidence)))
        except (json.JSONDecodeError, IndexError, ValueError):
            structured_data = {"raw_text": content}
            confidence = 0.5

        usage = raw.get("usage", {})

        return VLMResponse(
            content=content,
            structured_data=structured_data,
            confidence=float(confidence),
            model=raw.get("model", self._model),
            usage={
                "input_tokens": usage.get("prompt_tokens", 0),
                "output_tokens": usage.get("completion_tokens", 0),
            },
            raw_response=raw,
        )
