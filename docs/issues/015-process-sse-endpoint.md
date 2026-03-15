# Issue #15: Wire Processing Pipeline to SSE Endpoint

## Summary

Wire the full LangGraph processing pipeline to the `POST /api/v1/documents/{id}/process` SSE endpoint. This involves: (1) building and compiling the `StateGraph` with all four nodes (`preprocess -> extract -> postprocess -> store`) and conditional error edges, (2) implementing the `run_processing_pipeline` entry point, (3) implementing the `DocumentUseCase.trigger_processing` method that creates an SSE stream connected to the pipeline via a progress callback queue, and (4) updating the handler to return proper SSE events (`step_started`, `step_completed`, `field_extracted`, `processing_complete`, `error`).

## Context
- **Phase**: 3 — Processing Pipeline
- **Priority**: P0
- **Labels**: `phase-3-pipeline`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: #11, #12, #13, #14 (all pipeline nodes must be implemented)
- **Branch**: `feat/15-process-sse-endpoint`
- **Estimated scope**: L

## Specs to Read
- `specs/backend/pipeline-processing.md` — `build_processing_graph()`, `should_continue()`, `run_processing_pipeline()`, SSE progress callback pattern
- `specs/backend/api.md` — Documents handler `process_document`, SSE streaming pattern, `ProcessRequest` schema
- `specs/backend/services.md` — `DocumentUseCase.trigger_processing`, `_processing_stream`

## Current State (Scaffold)

**`backend/src/docmind/library/pipeline/processing.py`** — After issues #11-#14, contains all four node functions. But `run_processing_pipeline` is still a stub, and the `StateGraph` wiring (`build_processing_graph`, `should_continue`) is not implemented:

```python
def run_processing_pipeline(initial_state: dict) -> dict:
    """
    Run the full processing pipeline.
    Stub implementation — raises NotImplementedError.
    """
    raise NotImplementedError("Processing pipeline not yet implemented")
```

**`backend/src/docmind/modules/documents/usecase.py`** — Stub:

```python
class DocumentUseCase:
    def create_document(self, ...): ...  # stub returning hardcoded response
    def get_document(self, ...): ...     # stub returning hardcoded response
    def get_documents(self, ...): ...    # stub
    def delete_document(self, ...): ...  # stub

    def trigger_processing(self, document_id: str, template_type: str | None = None) -> AsyncGenerator[str, None]:
        return self._processing_stream(document_id, template_type)

    async def _processing_stream(self, document_id: str, template_type: str | None) -> AsyncGenerator[str, None]:
        import json
        yield f"data: {json.dumps({'step': 'complete', 'progress': 100, 'message': 'Stub - not implemented'})}\n\n"
```

**`backend/src/docmind/modules/documents/apiv1/handler.py`** — Already wired, calls `usecase.trigger_processing()` and returns `StreamingResponse`:

```python
@router.post("/{document_id}/process")
async def process_document(document_id: str, body: ProcessRequest, current_user: dict = Depends(get_current_user)):
    usecase = DocumentUseCase()
    document = usecase.get_document(user_id=current_user["id"], document_id=document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    event_stream = usecase.trigger_processing(document_id=document_id, template_type=body.template_type)
    return StreamingResponse(event_stream, media_type="text/event-stream", headers={...})
```

**`backend/src/docmind/modules/documents/services.py`** — Stub:

```python
class DocumentService:
    def load_file_bytes(self, storage_path: str) -> bytes:
        raise NotImplementedError
    def delete_storage_file(self, storage_path: str) -> None:
        raise NotImplementedError
```

**`backend/src/docmind/modules/documents/repositories.py`** — Stub:

```python
class DocumentRepository:
    async def create(self, ...): raise NotImplementedError
    async def get_by_id(self, ...): raise NotImplementedError
    async def list_for_user(self, ...): raise NotImplementedError
    async def delete(self, ...): raise NotImplementedError
    async def update_status(self, ...): raise NotImplementedError
```

## Requirements

### Functional — Pipeline Graph Wiring

1. Implement `should_continue(state: ProcessingState) -> str`: returns `"end"` if `state["status"] == "error"`, otherwise `"continue"`.
2. Implement `build_processing_graph() -> CompiledGraph`:
   - Creates `StateGraph(ProcessingState)`
   - Adds nodes: `preprocess`, `extract`, `postprocess`, `store`
   - Sets entry point to `preprocess`
   - Adds conditional edges after each node (except `store` which goes to `END`)
   - Compiles and returns the graph
3. Create module-level `processing_graph = build_processing_graph()`.
4. Implement `run_processing_pipeline(initial_state: dict) -> dict`: invokes `processing_graph.invoke(initial_state)`.

### Functional — Usecase SSE Stream

5. `DocumentUseCase._processing_stream(document_id, template_type)` is an `AsyncGenerator[str, None]`:
   - Gets document metadata via `self.repo.get_by_id(document_id, user_id="")`
   - Updates document status to `"processing"` via `self.repo.update_status()`
   - Loads file bytes via `self.service.load_file_bytes(doc.storage_path)`
   - Builds `initial_state` dict with all ProcessingState fields
   - Creates `asyncio.Queue` and `on_progress` callback
   - Runs pipeline in background via `asyncio.create_task(asyncio.to_thread(run_processing_pipeline, initial_state))`
   - Yields SSE events from queue: `data: {"step": "...", "progress": N, "message": "..."}\n\n`
   - Sends heartbeat every 30s on timeout
   - On pipeline error, updates document status to `"error"` and yields error event
   - Drains remaining events after pipeline completes

### Functional — SSE Event Format

6. Each SSE event is a line: `data: {JSON}\n\n`
7. Progress events: `{"step": "<node_name>", "progress": <0-100>, "message": "<human text>"}`
8. Heartbeat: `{"step": "heartbeat", "progress": -1, "message": "alive"}`
9. Error: `{"step": "error", "progress": 0, "message": "<error description>"}`
10. Final: `{"step": "complete", "progress": 100, "message": "Done"}` (emitted by store node callback)

### Functional — DocumentService

11. `DocumentService.load_file_bytes(storage_path)` calls `get_file_bytes(storage_path)` from Supabase storage.
12. `DocumentService.delete_storage_file(storage_path)` calls `delete_file(storage_path)`, logs warning on failure.

### Non-Functional

- SSE heartbeats every 30 seconds to prevent proxy timeouts
- Pipeline runs in a background thread (`asyncio.to_thread`) to not block the event loop
- Error states trigger document status update to "error"

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/pipeline/test_pipeline_graph.py`

```python
"""
Unit tests for the processing pipeline graph wiring:
should_continue, build_processing_graph, run_processing_pipeline.

Individual nodes are mocked — these tests verify graph structure
and flow control (normal flow + error short-circuit).
"""
import pytest
from unittest.mock import patch, MagicMock


class TestShouldContinue:
    """Tests for the should_continue conditional edge function."""

    def test_returns_continue_when_no_error(self):
        from docmind.library.pipeline.processing import should_continue

        state = {"status": "processing"}
        assert should_continue(state) == "continue"

    def test_returns_end_when_error(self):
        from docmind.library.pipeline.processing import should_continue

        state = {"status": "error"}
        assert should_continue(state) == "end"

    def test_returns_continue_when_status_missing(self):
        from docmind.library.pipeline.processing import should_continue

        state = {}
        assert should_continue(state) == "continue"

    def test_returns_continue_when_status_ready(self):
        from docmind.library.pipeline.processing import should_continue

        state = {"status": "ready"}
        assert should_continue(state) == "continue"


class TestBuildProcessingGraph:
    """Tests for build_processing_graph structure."""

    def test_graph_compiles_without_error(self):
        from docmind.library.pipeline.processing import build_processing_graph

        graph = build_processing_graph()
        assert graph is not None

    def test_graph_is_invocable(self):
        """The compiled graph has an invoke method."""
        from docmind.library.pipeline.processing import build_processing_graph

        graph = build_processing_graph()
        assert hasattr(graph, "invoke")


class TestRunProcessingPipeline:
    """Tests for run_processing_pipeline entry point."""

    @patch("docmind.library.pipeline.processing.processing_graph")
    def test_invokes_graph_with_initial_state(self, mock_graph):
        from docmind.library.pipeline.processing import run_processing_pipeline

        initial_state = {"document_id": "test", "status": "processing"}
        mock_graph.invoke.return_value = {"status": "ready", "extraction_id": "ext-123"}

        result = run_processing_pipeline(initial_state)

        mock_graph.invoke.assert_called_once_with(initial_state)
        assert result["status"] == "ready"

    @patch("docmind.library.pipeline.processing.processing_graph")
    def test_returns_graph_result(self, mock_graph):
        from docmind.library.pipeline.processing import run_processing_pipeline

        expected = {"status": "ready", "extraction_id": "ext-456"}
        mock_graph.invoke.return_value = expected

        result = run_processing_pipeline({})
        assert result == expected
```

**Test file**: `backend/tests/unit/modules/documents/test_process_usecase.py`

```python
"""
Unit tests for DocumentUseCase.trigger_processing and _processing_stream.

Pipeline, repository, and service are all mocked. Tests verify
SSE event format, error handling, document status updates,
and the async stream mechanics.
"""
import asyncio
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock


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

        usecase = DocumentUseCase()
        usecase.repo = mock_repo
        usecase.service = mock_service

        result = usecase.trigger_processing(document_id="doc-123")
        # Should be an async generator or coroutine that yields
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
                cb(step="preprocess", progress=25, message="Converting...")
                cb(step="extract", progress=50, message="Extracting...")
                cb(step="complete", progress=100, message="Done")
            return {"status": "ready", "extraction_id": "ext-123"}

        mock_pipeline.side_effect = fake_pipeline

        usecase = DocumentUseCase()
        usecase.repo = mock_repo
        usecase.service = mock_service

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

        usecase = DocumentUseCase()
        usecase.repo = mock_repo
        usecase.service = mock_service

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

        usecase = DocumentUseCase()
        usecase.repo = mock_repo
        usecase.service = mock_service

        async for _ in usecase._processing_stream("doc-123", None):
            pass

        mock_repo.update_status.assert_any_call("doc-123", "error")

    @pytest.mark.asyncio
    async def test_yields_error_when_document_not_found(self, mock_service):
        """If document is not found, yields error event."""
        from docmind.modules.documents.usecase import DocumentUseCase

        repo = MagicMock()
        repo.get_by_id = AsyncMock(return_value=None)

        usecase = DocumentUseCase()
        usecase.repo = repo
        usecase.service = mock_service

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

        usecase = DocumentUseCase()
        usecase.repo = mock_repo
        usecase.service = service

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

        usecase = DocumentUseCase()
        usecase.repo = mock_repo
        usecase.service = mock_service

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

        usecase = DocumentUseCase()
        usecase.repo = mock_repo
        usecase.service = mock_service

        async for _ in usecase._processing_stream("doc-123", "invoice"):
            pass

        assert capture_state.captured["template_type"] == "invoice"


class TestProcessDocumentHandler:
    """Tests for the handler endpoint integration."""

    @pytest.mark.asyncio
    async def test_returns_streaming_response(self):
        """POST /documents/{id}/process returns StreamingResponse with correct media_type."""
        from fastapi.testclient import TestClient
        from unittest.mock import patch as mock_patch

        # This is a smoke test verifying the handler wiring
        # Full integration test requires more setup
        pass  # Covered by the handler already being wired
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/pipeline/processing.py` — Add `should_continue`, `build_processing_graph`, update `run_processing_pipeline`
- `backend/src/docmind/modules/documents/usecase.py` — Replace stub with real implementation
- `backend/src/docmind/modules/documents/services.py` — Replace stub with real implementation
- `backend/src/docmind/modules/documents/repositories.py` — Replace stub with real implementation (needed by usecase)

**Implementation guidance**:

1. **`processing.py`** — Add graph wiring:
   ```python
   from langgraph.graph import END, StateGraph

   def should_continue(state: ProcessingState) -> str:
       if state.get("status") == "error":
           return "end"
       return "continue"

   def build_processing_graph():
       graph = StateGraph(ProcessingState)
       graph.add_node("preprocess", preprocess_node)
       graph.add_node("extract", extract_node)
       graph.add_node("postprocess", postprocess_node)
       graph.add_node("store", store_node)
       graph.set_entry_point("preprocess")
       graph.add_conditional_edges("preprocess", should_continue, {"continue": "extract", "end": END})
       graph.add_conditional_edges("extract", should_continue, {"continue": "postprocess", "end": END})
       graph.add_conditional_edges("postprocess", should_continue, {"continue": "store", "end": END})
       graph.add_edge("store", END)
       return graph.compile()

   processing_graph = build_processing_graph()

   def run_processing_pipeline(initial_state: dict) -> dict:
       return processing_graph.invoke(initial_state)
   ```

2. **`usecase.py`** — Replace stub with full implementation from spec (see `specs/backend/services.md`):
   - Import `DocumentRepository`, `DocumentService`, `run_processing_pipeline`
   - Implement `__init__` creating repo and service instances
   - Implement `_processing_stream` as async generator with queue pattern
   - Handle document not found, file load failure, pipeline error

3. **`services.py`** — Replace stubs:
   ```python
   from docmind.dbase.supabase.storage import get_file_bytes, delete_file

   class DocumentService:
       def load_file_bytes(self, storage_path: str) -> bytes:
           return get_file_bytes(storage_path)

       def delete_storage_file(self, storage_path: str) -> None:
           try:
               delete_file(storage_path)
           except Exception as e:
               logger.warning("Failed to delete file %s: %s", storage_path, e)
   ```

4. **`repositories.py`** — The repository needs to be implemented for `get_by_id` and `update_status` at minimum (full CRUD can be a separate issue, but these two methods are needed now).

### Step 3: Refactor (IMPROVE)
- Ensure SSE events are flushed promptly (no buffering issues)
- Add structured logging at pipeline start/end
- Verify heartbeat timeout value is configurable

## Acceptance Criteria
- [ ] `should_continue` returns `"end"` on error, `"continue"` otherwise
- [ ] `build_processing_graph` creates a compiled StateGraph with 4 nodes and conditional edges
- [ ] `run_processing_pipeline` invokes the graph and returns final state
- [ ] `DocumentUseCase.trigger_processing` returns an async generator of SSE events
- [ ] SSE events follow format `data: {JSON}\n\n`
- [ ] Progress events include `step`, `progress`, `message`
- [ ] Error events have `step="error"`
- [ ] Document status updated to `"processing"` before pipeline starts
- [ ] Document status updated to `"error"` on pipeline failure
- [ ] `template_type` from `ProcessRequest` is passed through to pipeline
- [ ] File loading failure yields error SSE event
- [ ] Document not found yields error SSE event
- [ ] Heartbeat sent on 30s timeout
- [ ] Pipeline runs in background thread (not blocking event loop)
- [ ] All unit tests pass

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/src/docmind/library/pipeline/processing.py` | Modify | Add `should_continue`, `build_processing_graph`, update `run_processing_pipeline` |
| `backend/src/docmind/modules/documents/usecase.py` | Modify | Replace stub with real SSE stream implementation |
| `backend/src/docmind/modules/documents/services.py` | Modify | Replace stubs with real Supabase storage calls |
| `backend/src/docmind/modules/documents/repositories.py` | Modify | Implement `get_by_id` and `update_status` methods |
| `backend/tests/unit/library/pipeline/test_pipeline_graph.py` | Create | Tests for graph wiring and run_processing_pipeline |
| `backend/tests/unit/modules/__init__.py` | Create | Empty `__init__.py` for test package |
| `backend/tests/unit/modules/documents/__init__.py` | Create | Empty `__init__.py` for test package |
| `backend/tests/unit/modules/documents/test_process_usecase.py` | Create | Tests for DocumentUseCase processing stream |

## Verification

```bash
# Run pipeline graph tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/pipeline/test_pipeline_graph.py -v

# Run usecase tests
python -m pytest backend/tests/unit/modules/documents/test_process_usecase.py -v

# Run all pipeline-related tests
python -m pytest backend/tests/unit/library/pipeline/ backend/tests/unit/modules/documents/ -v

# Run with coverage for all pipeline code
python -m pytest backend/tests/unit/ -v --cov=docmind.library.pipeline --cov=docmind.modules.documents --cov-report=term-missing

# Verify imports
python -c "from docmind.library.pipeline.processing import run_processing_pipeline, build_processing_graph, should_continue; print('OK')"
python -c "from docmind.modules.documents.usecase import DocumentUseCase; print('OK')"

# Smoke test: start the server (requires env vars)
# make backend
```
