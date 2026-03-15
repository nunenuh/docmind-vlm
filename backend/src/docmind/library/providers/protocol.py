"""
docmind/library/providers/protocol.py

VLM provider protocol and shared response types.
"""
from typing import Protocol, TypedDict
import base64
import numpy as np


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


def encode_image_base64(image: np.ndarray) -> str:
    import cv2
    _, buffer = cv2.imencode(".jpg", image, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return base64.b64encode(buffer.tobytes()).decode("utf-8")
