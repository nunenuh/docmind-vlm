"""Embedding provider abstraction.

Supports DashScope text-embedding-v4 and OpenAI text-embedding-3-small.
Provider is selected via EMBEDDING_PROVIDER setting.
Handles batching to respect API limits.
"""

from __future__ import annotations

import logging

import httpx

from docmind.core.config import get_settings

logger = logging.getLogger(__name__)

# DashScope allows max 25 texts per batch for text-embedding-v4,
# but we use a conservative batch size to avoid 400 errors.
DASHSCOPE_BATCH_SIZE = 10
OPENAI_BATCH_SIZE = 100


async def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts using the configured embedding provider.

    Automatically batches large inputs to respect API limits.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (one per input text).

    Raises:
        ValueError: If the configured provider is unknown.
        httpx.HTTPStatusError: If the embedding API call fails.
    """
    if not texts:
        return []

    settings = get_settings()
    if settings.EMBEDDING_PROVIDER == "dashscope":
        return await _embed_batched(texts, settings, _embed_dashscope_batch, DASHSCOPE_BATCH_SIZE)
    elif settings.EMBEDDING_PROVIDER == "openai":
        return await _embed_batched(texts, settings, _embed_openai_batch, OPENAI_BATCH_SIZE)
    raise ValueError(f"Unknown embedding provider: {settings.EMBEDDING_PROVIDER}")


async def _embed_batched(
    texts: list[str],
    settings,
    embed_fn,
    batch_size: int,
) -> list[list[float]]:
    """Split texts into batches and embed each batch.

    Args:
        texts: All texts to embed.
        settings: Application settings.
        embed_fn: Async function that embeds a single batch.
        batch_size: Max texts per batch.

    Returns:
        Combined list of embedding vectors in original order.
    """
    all_embeddings: list[list[float]] = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        logger.info("Embedding batch %d-%d of %d texts", i, i + len(batch), len(texts))
        batch_embeddings = await embed_fn(batch, settings)
        all_embeddings.extend(batch_embeddings)
    return all_embeddings


async def _embed_dashscope_batch(texts: list[str], settings) -> list[list[float]]:
    """Embed a single batch using DashScope text-embedding API.

    Args:
        texts: Texts to embed (must be <= DASHSCOPE_BATCH_SIZE).
        settings: Application settings with DashScope credentials.

    Returns:
        List of embedding vectors sorted by text_index.
    """
    # Build embedding URL from base URL
    base = settings.DASHSCOPE_BASE_URL
    # Strip the VLM endpoint path and use the embedding endpoint
    if "/services/aigc/" in base:
        base = base.split("/services/aigc/")[0]
    elif "/api/v1" in base:
        base = base.split("/api/v1")[0] + "/api/v1"
    embedding_url = f"{base}/services/embeddings/text-embedding/text-embedding"

    async with httpx.AsyncClient(timeout=settings.EMBEDDING_TIMEOUT) as client:
        response = await client.post(
            embedding_url,
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


async def _embed_openai_batch(texts: list[str], settings) -> list[list[float]]:
    """Embed a single batch using OpenAI embeddings API.

    Args:
        texts: Texts to embed (must be <= OPENAI_BATCH_SIZE).
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
