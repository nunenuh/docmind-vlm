"""
docmind/library/providers/openai.py

OpenAI GPT-4o Vision provider (skeleton).
"""

import logging

import numpy as np

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMResponse

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "gpt-4o"


class OpenAIProvider:
    def __init__(self) -> None:
        settings = get_settings()
        if not settings.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is required when VLM_PROVIDER=openai")
        self._model = settings.OPENAI_MODEL or DEFAULT_MODEL

    @property
    def provider_name(self) -> str:
        return "OpenAI"

    @property
    def model_name(self) -> str:
        return self._model

    async def extract(
        self, images: list[np.ndarray], prompt: str, schema: dict | None = None
    ) -> VLMResponse:
        raise NotImplementedError("OpenAI extract not yet implemented")

    async def classify(self, image: np.ndarray, categories: list[str]) -> VLMResponse:
        raise NotImplementedError("OpenAI classify not yet implemented")

    async def chat(
        self,
        images: list[np.ndarray],
        message: str,
        history: list[dict],
        system_prompt: str,
    ) -> VLMResponse:
        raise NotImplementedError("OpenAI chat not yet implemented")

    async def health_check(self) -> bool:
        return False
