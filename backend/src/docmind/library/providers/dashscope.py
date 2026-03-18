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
from docmind.library.providers.protocol import VLMResponse, encode_image_base64

logger = logging.getLogger(__name__)

BASE_URL = "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation"
DEFAULT_MODEL = "qwen-vl-max"
MAX_RETRIES = 3
RETRY_BASE_DELAY = 2.0  # seconds, doubles each retry
REQUEST_TIMEOUT = 120.0  # seconds


class DashScopeProvider:
    """DashScope VLM provider using Qwen-VL models.

    Requires DASHSCOPE_API_KEY environment variable.
    """

    def __init__(self) -> None:
        """Initialize the DashScope provider.

        Raises:
            RuntimeError: If DASHSCOPE_API_KEY is not set.
        """
        settings = get_settings()
        self._api_key = settings.DASHSCOPE_API_KEY
        if not self._api_key:
            raise RuntimeError(
                "DASHSCOPE_API_KEY is required when VLM_PROVIDER=dashscope"
            )
        self._model = settings.DASHSCOPE_MODEL or DEFAULT_MODEL
        self._client = httpx.AsyncClient(timeout=REQUEST_TIMEOUT)

    @property
    def provider_name(self) -> str:
        """Human-readable provider name."""
        return "DashScope"

    @property
    def model_name(self) -> str:
        """Model identifier string."""
        return self._model

    async def extract(
        self,
        images: list[np.ndarray],
        prompt: str,
        schema: dict | None = None,
    ) -> VLMResponse:
        """Extract structured data from document images.

        Constructs a multimodal payload with all page images and the
        extraction prompt. If a schema is provided, it is included in
        the prompt to guide structured output.

        Args:
            images: List of BGR uint8 page images.
            prompt: Extraction prompt.
            schema: Optional JSON schema for structured output.

        Returns:
            VLMResponse with extracted fields in structured_data.
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

        messages: list[dict[str, Any]] = [
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
        """Classify document type from first page.

        Args:
            image: First page of the document (BGR uint8).
            categories: List of valid document type strings.

        Returns:
            VLMResponse with classification in structured_data.
        """
        categories_str = ", ".join(categories)
        prompt = (
            f"Classify this document into one of these categories: {categories_str}.\n"
            'Respond with JSON: {"document_type": "<category>", "confidence": <0.0-1.0>}'
        )

        messages: list[dict[str, Any]] = [
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
        """Chat about document content with conversation history.

        Images are included in the first user message for visual grounding.
        With no history, images accompany the current message. With history,
        images are attached to the first historical user message.

        Args:
            images: Document page images for visual grounding.
            message: Current user message.
            history: Previous messages as [{"role": str, "content": str}, ...].
            system_prompt: System prompt enforcing grounding rules.

        Returns:
            VLMResponse with answer in content.
        """
        image_contents = [
            {"image": f"data:image/jpeg;base64,{encode_image_base64(img)}"}
            for img in images
        ]

        messages: list[dict[str, Any]] = [
            {"role": "system", "content": [{"text": system_prompt}]},
        ]

        if history:
            # First user message includes images for grounding
            first_user_content = image_contents + [{"text": history[0]["content"]}]
            messages.append({"role": "user", "content": first_user_content})

            for msg in history[1:]:
                messages.append({
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}],
                })

            # Append current message
            messages.append({"role": "user", "content": [{"text": message}]})
        else:
            # No history — include images with current message
            current_content = image_contents + [{"text": message}]
            messages.append({"role": "user", "content": current_content})

        return await self._call_api(messages)

    async def health_check(self) -> bool:
        """Check DashScope API connectivity.

        Returns:
            True if API is reachable (200 or 400), False otherwise.
        """
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
            return response.status_code in (200, 400)
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
        """Build the DashScope multimodal API payload.

        Args:
            messages: List of message dicts in DashScope format.

        Returns:
            Complete API payload dict.
        """
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
        """Call the DashScope API with retry and exponential backoff.

        Retries on 429 rate limit and transient network errors.
        Raises immediately on other HTTP errors (4xx, 5xx).

        Args:
            messages: List of message dicts in DashScope format.

        Returns:
            Parsed VLMResponse.

        Raises:
            RuntimeError: On non-retryable HTTP errors or after all retries exhausted.
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
                logger.error(
                    "DashScope API error: %d", e.response.status_code
                )
                raise RuntimeError(
                    f"DashScope API error: {e.response.status_code}"
                ) from e

            except httpx.RequestError as e:
                last_error = e
                wait = RETRY_BASE_DELAY * (2 ** attempt)
                logger.warning(
                    "DashScope request error: %s. Retrying in %.1fs (attempt %d/%d)",
                    e, wait, attempt + 1, MAX_RETRIES,
                )
                time.sleep(wait)

        raise RuntimeError(
            f"DashScope API failed after {MAX_RETRIES} retries"
        ) from last_error

    def _parse_response(self, raw: dict) -> VLMResponse:
        """Parse DashScope API response into VLMResponse.

        Handles JSON content, markdown-wrapped JSON, and plain text fallback.

        Args:
            raw: Raw API response dict.

        Returns:
            Parsed VLMResponse with structured_data and confidence.
        """
        output = raw.get("output", {})
        choices = output.get("choices", [])
        if not choices:
            logger.warning("DashScope response contained no choices")
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
            text = content.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1] if "\n" in text else text[3:]
                text = text.rsplit("```", 1)[0]
            structured_data = json.loads(text)
            raw_confidence = structured_data.get("confidence", 0.8)
            confidence = max(0.0, min(1.0, float(raw_confidence)))
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
