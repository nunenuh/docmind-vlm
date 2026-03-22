"""Embedding provider abstraction.

Supports DashScope text-embedding-v3 and OpenAI text-embedding-3-small.
Provider is selected via EMBEDDING_PROVIDER setting.
"""

from __future__ import annotations

import httpx

from docmind.core.config import get_settings


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured embedding provider.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (one per input text).

    Raises:
        ValueError: If the configured provider is unknown.
        httpx.HTTPStatusError: If the embedding API call fails.
    """
    settings = get_settings()
    if settings.EMBEDDING_PROVIDER == "dashscope":
        return await _embed_dashscope(texts, settings)
    elif settings.EMBEDDING_PROVIDER == "openai":
        return await _embed_openai(texts, settings)
    raise ValueError(f"Unknown embedding provider: {settings.EMBEDDING_PROVIDER}")


async def _embed_dashscope(texts: list[str], settings) -> list[list[float]]:
    """Embed using DashScope text-embedding API.

    Args:
        texts: Texts to embed.
        settings: Application settings with DashScope credentials.

    Returns:
        List of embedding vectors sorted by text_index.
    """
    base_url = settings.DASHSCOPE_BASE_URL.replace(
        "/services/aigc/multimodal-generation/generation",
        "/services/embeddings/text-embedding/text-embedding",
    )
    async with httpx.AsyncClient(timeout=settings.EMBEDDING_TIMEOUT) as client:
        response = await client.post(
            base_url,
            headers={"Authorization": f"Bearer {settings.DASHSCOPE_API_KEY}"},
            json={
                "model": settings.EMBEDDING_MODEL,
                "input": {"texts": texts},
                "parameters": {"dimension": settings.EMBEDDING_DIMENSIONS},
            },
        )
        response.raise_for_status()
        data = response.json()
        embeddings = data["output"]["embeddings"]
        return [
            e["embedding"]
            for e in sorted(embeddings, key=lambda x: x["text_index"])
        ]


async def _embed_openai(texts: list[str], settings) -> list[list[float]]:
    """Embed using OpenAI embeddings API.

    Args:
        texts: Texts to embed.
        settings: Application settings with OpenAI credentials.

    Returns:
        List of embedding vectors.
    """
    async with httpx.AsyncClient(timeout=settings.EMBEDDING_TIMEOUT) as client:
        response = await client.post(
            "https://api.openai.com/v1/embeddings",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={"model": settings.EMBEDDING_MODEL, "input": texts},
        )
        response.raise_for_status()
        data = response.json()
        return [item["embedding"] for item in data["data"]]
