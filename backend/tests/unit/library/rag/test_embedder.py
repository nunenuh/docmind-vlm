"""Tests for docmind.library.rag.embedder."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from docmind.library.rag.embedder import embed_texts


@pytest.fixture
def mock_settings_dashscope():
    settings = MagicMock()
    settings.EMBEDDING_PROVIDER = "dashscope"
    settings.EMBEDDING_MODEL = "text-embedding-v3"
    settings.EMBEDDING_DIMENSIONS = 1024
    settings.DASHSCOPE_API_KEY = "test-key"
    settings.DASHSCOPE_BASE_URL = (
        "https://dashscope-intl.aliyuncs.com/api/v1"
        "/services/aigc/multimodal-generation/generation"
    )
    return settings


@pytest.fixture
def mock_settings_openai():
    settings = MagicMock()
    settings.EMBEDDING_PROVIDER = "openai"
    settings.EMBEDDING_MODEL = "text-embedding-3-small"
    settings.OPENAI_API_KEY = "test-openai-key"
    return settings


class TestEmbedTexts:
    """Tests for embed_texts."""

    @pytest.mark.asyncio
    @patch("docmind.library.rag.embedder.get_settings")
    @patch("docmind.library.rag.embedder.httpx.AsyncClient")
    async def test_embed_texts_dashscope(
        self, mock_client_cls, mock_get_settings, mock_settings_dashscope
    ):
        mock_get_settings.return_value = mock_settings_dashscope

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "output": {
                "embeddings": [
                    {"text_index": 0, "embedding": [0.1, 0.2, 0.3]},
                    {"text_index": 1, "embedding": [0.4, 0.5, 0.6]},
                ]
            }
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await embed_texts(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.1, 0.2, 0.3]
        assert result[1] == [0.4, 0.5, 0.6]

    @pytest.mark.asyncio
    @patch("docmind.library.rag.embedder.get_settings")
    @patch("docmind.library.rag.embedder.httpx.AsyncClient")
    async def test_embed_texts_openai(
        self, mock_client_cls, mock_get_settings, mock_settings_openai
    ):
        mock_get_settings.return_value = mock_settings_openai

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "data": [
                {"embedding": [0.7, 0.8, 0.9]},
                {"embedding": [1.0, 1.1, 1.2]},
            ]
        }

        mock_client = AsyncMock()
        mock_client.post.return_value = mock_response
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await embed_texts(["hello", "world"])

        assert len(result) == 2
        assert result[0] == [0.7, 0.8, 0.9]
        assert result[1] == [1.0, 1.1, 1.2]

    @pytest.mark.asyncio
    @patch("docmind.library.rag.embedder.get_settings")
    async def test_embed_texts_unknown_provider(self, mock_get_settings):
        settings = MagicMock()
        settings.EMBEDDING_PROVIDER = "unknown"
        mock_get_settings.return_value = settings

        with pytest.raises(ValueError, match="Unknown embedding provider"):
            await embed_texts(["hello"])
