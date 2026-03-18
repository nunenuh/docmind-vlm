"""
Unit tests for DocumentUseCase.trigger_processing and _processing_stream.

Pipeline, repository, and service are all mocked. Tests verify
SSE event format, error handling, document status updates,
and the async stream mechanics.
"""
import json

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


@pytest.fixture
def mock_repo():
    """Mock DocumentRepository."""
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
def mock_service():
    """Mock DocumentService."""
    service = MagicMock()
    service.load_file_bytes = MagicMock(return_value=b"fake-pdf-bytes")
    return service


class TestTriggerProcessing:
    """Tests for the trigger_processing method."""

    def test_returns_async_generator(self, mock_repo, mock_service):
        from docmind.modules.documents.usecase import DocumentUseCase

        usecase = DocumentUseCase(service=mock_service, repo=mock_repo)
        result = usecase.trigger_processing(document_id="doc-123")
        assert result is not None


class TestProcessingStream:
    """Tests for _processing_stream SSE events."""

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.usecase.run_processing_pipeline")
    async def test_yields_sse_events(self, mock_pipeline, mock_repo, mock_service):
        """SSE events follow the format: data: {JSON}\\n\\n"""
        from docmind.modules.documents.usecase import DocumentUseCase

        def fake_pipeline(state):
            cb = state.get("progress_callback")
            if cb:
                cb("preprocess", 25, "Converting...")
                cb("extract", 50, "Extracting...")
                cb("complete", 100, "Done")
            return {"status": "ready", "extraction_id": "ext-123"}

        mock_pipeline.side_effect = fake_pipeline

        usecase = DocumentUseCase(service=mock_service, repo=mock_repo)

        events = []
        async for event in usecase._processing_stream("doc-123", None):
            events.append(event)

        assert len(events) >= 3
        for event in events:
            assert event.startswith("data: ")
            assert event.endswith("\n\n")
            payload = json.loads(event[len("data: "):-2])
            assert "step" in payload

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.usecase.run_processing_pipeline")
    async def test_yields_error_event_on_pipeline_failure(
        self, mock_pipeline, mock_repo, mock_service
    ):
        """If pipeline returns status='error', yields error SSE event."""
        from docmind.modules.documents.usecase import DocumentUseCase

        mock_pipeline.return_value = {
            "status": "error",
            "error_message": "VLM provider timed out",
        }

        usecase = DocumentUseCase(service=mock_service, repo=mock_repo)

        events = []
        async for event in usecase._processing_stream("doc-123", None):
            events.append(event)

        error_events = [
            e for e in events
            if "error" in json.loads(e[len("data: "):-2]).get("step", "")
        ]
        assert len(error_events) >= 1

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.usecase.run_processing_pipeline")
    async def test_updates_status_to_error_on_failure(
        self, mock_pipeline, mock_repo, mock_service
    ):
        """Document status is updated to 'error' when pipeline fails."""
        from docmind.modules.documents.usecase import DocumentUseCase

        mock_pipeline.return_value = {
            "status": "error",
            "error_message": "Extraction failed",
        }

        usecase = DocumentUseCase(service=mock_service, repo=mock_repo)

        async for _ in usecase._processing_stream("doc-123", None):
            pass

        mock_repo.update_status.assert_any_call("doc-123", "error")

    @pytest.mark.asyncio
    async def test_yields_error_when_document_not_found(self, mock_service):
        """If document is not found, yields error event."""
        from docmind.modules.documents.usecase import DocumentUseCase

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)

        usecase = DocumentUseCase(service=mock_service, repo=repo)

        events = []
        async for event in usecase._processing_stream("nonexistent", None):
            events.append(event)

        assert len(events) >= 1
        payload = json.loads(events[0][len("data: "):-2])
        assert payload["step"] == "error"
        assert "not found" in payload["message"].lower()

    @pytest.mark.asyncio
    async def test_yields_error_when_file_load_fails(self, mock_repo):
        """If file loading fails, yields error event."""
        from docmind.modules.documents.usecase import DocumentUseCase

        service = MagicMock()
        service.load_file_bytes = MagicMock(side_effect=RuntimeError("Storage unavailable"))

        usecase = DocumentUseCase(service=service, repo=mock_repo)

        events = []
        async for event in usecase._processing_stream("doc-123", None):
            events.append(event)

        assert len(events) >= 1
        payload = json.loads(events[0][len("data: "):-2])
        assert payload["step"] == "error"

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.usecase.run_processing_pipeline")
    async def test_updates_status_to_processing_before_pipeline(
        self, mock_pipeline, mock_repo, mock_service
    ):
        """Document status is set to 'processing' before pipeline starts."""
        from docmind.modules.documents.usecase import DocumentUseCase

        mock_pipeline.return_value = {"status": "ready"}

        usecase = DocumentUseCase(service=mock_service, repo=mock_repo)

        async for _ in usecase._processing_stream("doc-123", None):
            pass

        mock_repo.update_status.assert_any_call("doc-123", "processing")

    @pytest.mark.asyncio
    @patch("docmind.modules.documents.usecase.run_processing_pipeline")
    async def test_passes_template_type_in_initial_state(
        self, mock_pipeline, mock_repo, mock_service
    ):
        """template_type from ProcessRequest is passed to pipeline initial state."""
        from docmind.modules.documents.usecase import DocumentUseCase

        def capture_state(state):
            capture_state.captured = state
            return {"status": "ready"}

        mock_pipeline.side_effect = capture_state

        usecase = DocumentUseCase(service=mock_service, repo=mock_repo)

        async for _ in usecase._processing_stream("doc-123", "invoice"):
            pass

        assert capture_state.captured["template_type"] == "invoice"
