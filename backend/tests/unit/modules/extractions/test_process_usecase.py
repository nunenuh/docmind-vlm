"""
Unit tests for ExtractionProcessUseCase.trigger_processing and _processing_stream.

Pipeline, repository, and service are all mocked. Tests verify
SSE event format, error handling, document status updates,
and the async stream mechanics.

Moved from documents module — extraction processing now lives in extractions.
"""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_doc_repo():
    """Mock DocumentRepository (read-only cross-module access)."""
    repo = MagicMock()
    repo.get_by_id = AsyncMock(return_value=MagicMock(
        storage_path="test/path/doc.pdf",
        file_type="pdf",
        id="doc-123",
        status="uploaded",
    ))
    repo.update_status = AsyncMock()
    return repo


@pytest.fixture
def mock_storage_service():
    """Mock DocumentStorageService."""
    service = MagicMock()
    service.load_file_bytes = MagicMock(return_value=b"fake-pdf-bytes")
    return service


@pytest.fixture
def mock_pipeline_service():
    """Mock ExtractionPipelineService."""
    service = MagicMock()
    service.run_pipeline = MagicMock(return_value={"status": "ready"})
    return service


@pytest.fixture
def mock_template_repo():
    """Mock TemplateRepository."""
    repo = MagicMock()
    repo.list_all = AsyncMock(return_value=[])
    return repo


def _make_usecase(
    pipeline_service, doc_repo=None, storage_service=None, template_repo=None
):
    """Build ExtractionProcessUseCase with injected mock deps."""
    from docmind.modules.extractions.usecases.process import ExtractionProcessUseCase

    return ExtractionProcessUseCase(
        pipeline_service=pipeline_service,
        doc_repo=doc_repo or MagicMock(),
        storage_service=storage_service or MagicMock(),
        template_repo=template_repo or MagicMock(),
    )


class TestTriggerProcessing:
    """Tests for the trigger_processing method."""

    def test_returns_async_generator(self, mock_pipeline_service):
        usecase = _make_usecase(pipeline_service=mock_pipeline_service)
        result = usecase.trigger_processing(document_id="doc-123", user_id="user-456")
        assert result is not None


class TestProcessingStream:
    """Tests for _processing_stream SSE events."""

    @pytest.mark.asyncio
    @patch("docmind.shared.provider_resolver.resolve_provider_override", new_callable=AsyncMock, return_value=None)
    async def test_yields_sse_events(
        self, _mock_resolve, mock_doc_repo, mock_storage_service, mock_pipeline_service, mock_template_repo
    ):
        """SSE events follow the format: data: {JSON}\\n\\n"""

        def fake_pipeline(state):
            cb = state.get("progress_callback")
            if cb:
                cb("preprocess", 25, "Converting...")
                cb("extract", 50, "Extracting...")
                cb("complete", 100, "Done")
            return {"status": "ready", "extraction_id": "ext-123"}

        mock_pipeline_service.run_pipeline.side_effect = fake_pipeline

        usecase = _make_usecase(
            pipeline_service=mock_pipeline_service,
            doc_repo=mock_doc_repo,
            storage_service=mock_storage_service,
            template_repo=mock_template_repo,
        )

        events = []
        async for event in usecase._processing_stream("doc-123", "user-456", None):
            events.append(event)

        assert len(events) >= 3
        for event in events:
            assert event.startswith("data: ")
            assert event.endswith("\n\n")
            payload = json.loads(event[len("data: "):-2])
            assert "step" in payload

    @pytest.mark.asyncio
    async def test_yields_error_when_document_not_found(
        self, mock_storage_service, mock_pipeline_service, mock_template_repo
    ):
        """If document is not found, yields error event."""
        not_found_repo = MagicMock()
        not_found_repo.get_by_id = AsyncMock(return_value=None)

        usecase = _make_usecase(
            pipeline_service=mock_pipeline_service,
            doc_repo=not_found_repo,
            storage_service=mock_storage_service,
            template_repo=mock_template_repo,
        )

        events = []
        async for event in usecase._processing_stream("nonexistent", "user-456", None):
            events.append(event)

        assert len(events) >= 1
        payload = json.loads(events[0][len("data: "):-2])
        assert payload["step"] == "error"
        assert "not found" in payload["message"].lower()

    @pytest.mark.asyncio
    async def test_yields_error_when_file_load_fails(
        self, mock_doc_repo, mock_pipeline_service, mock_template_repo
    ):
        """If file loading fails, yields error event."""
        bad_storage = MagicMock()
        bad_storage.load_file_bytes = MagicMock(side_effect=RuntimeError("Storage unavailable"))

        usecase = _make_usecase(
            pipeline_service=mock_pipeline_service,
            doc_repo=mock_doc_repo,
            storage_service=bad_storage,
            template_repo=mock_template_repo,
        )

        events = []
        async for event in usecase._processing_stream("doc-123", "user-456", None):
            events.append(event)

        assert len(events) >= 1
        payload = json.loads(events[0][len("data: "):-2])
        assert payload["step"] == "error"
