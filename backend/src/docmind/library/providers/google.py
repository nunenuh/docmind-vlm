"""
docmind/library/providers/google.py

Google Gemini Vision provider (skeleton).
"""
import logging
import numpy as np

from docmind.core.config import get_settings
from docmind.library.providers.protocol import VLMProvider, VLMResponse, encode_image_base64

logger = logging.getLogger(__name__)
DEFAULT_MODEL = "gemini-2.0-flash"


class GoogleProvider:
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
        return False
