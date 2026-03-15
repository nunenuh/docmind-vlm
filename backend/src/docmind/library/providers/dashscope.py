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
