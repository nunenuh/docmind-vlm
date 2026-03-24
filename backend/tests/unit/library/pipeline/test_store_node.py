"""
Unit tests for store_node pipeline function.

Database operations are mocked. Tests verify that store_node
creates the correct ORM objects, calls commit, updates document
status, and handles errors properly.
"""
import uuid
from unittest.mock import AsyncMock, MagicMock, patch


def _make_state(
    enhanced_fields: list[dict] | None = None,
    audit_entries: list[dict] | None = None,
    callback: object | None = None,
) -> dict:
    """Build a ProcessingState for store_node."""
    if enhanced_fields is None:
        enhanced_fields = [
            {
                "id": str(uuid.uuid4()),
                "field_type": "key_value",
                "field_key": "total",
                "field_value": "$500",
                "page_number": 1,
                "bounding_box": {"x": 0.5, "y": 0.8, "width": 0.2, "height": 0.05},
                "confidence": 0.85,
                "vlm_confidence": 0.9,
                "cv_quality_score": 0.7,
                "is_required": False,
                "is_missing": False,
            },
        ]
    if audit_entries is None:
        audit_entries = [
            {
                "step_name": "preprocess",
                "step_order": 1,
                "input_summary": {},
                "output_summary": {},
                "parameters": {},
                "duration_ms": 100,
            },
        ]
    return {
        "document_id": "doc-123",
        "user_id": "user-456",
        "file_bytes": b"",
        "file_type": "pdf",
        "template_type": None,
        "page_images": [],
        "page_count": 2,
        "quality_map": {},
        "skew_angles": [],
        "raw_fields": [],
        "vlm_response": {},
        "document_type": "invoice",
        "enhanced_fields": enhanced_fields,
        "comparison_data": {"corrected": [], "added": []},
        "extraction_id": "",
        "status": "processing",
        "error_message": None,
        "audit_entries": audit_entries,
        "progress_callback": callback,
    }


class TestStoreNode:
    """Tests for store_node database persistence."""

    @patch("docmind.library.pipeline.extraction.store._persist_results", new_callable=AsyncMock)
    def test_returns_extraction_id(self, mock_persist):
        """store_node generates and returns a UUID extraction_id."""
        from docmind.library.pipeline.extraction.store import store_node

        state = _make_state()
        result = store_node(state)

        assert "extraction_id" in result
        uuid.UUID(result["extraction_id"])

    @patch("docmind.library.pipeline.extraction.store._persist_results", new_callable=AsyncMock)
    def test_sets_status_to_ready(self, mock_persist):
        """store_node sets status to 'ready' on success."""
        from docmind.library.pipeline.extraction.store import store_node

        state = _make_state()
        result = store_node(state)

        assert result["status"] == "ready"

    @patch("docmind.library.pipeline.extraction.store._persist_results", new_callable=AsyncMock)
    def test_calls_persist_with_state_and_extraction_id(self, mock_persist):
        """store_node calls _persist_results with the state and extraction_id."""
        from docmind.library.pipeline.extraction.store import store_node

        state = _make_state()
        result = store_node(state)

        mock_persist.assert_called_once()
        call_args = mock_persist.call_args
        assert call_args[0][0] is state or call_args[1].get("state") is state

    @patch("docmind.library.pipeline.extraction.store._persist_results", new_callable=AsyncMock)
    def test_creates_store_audit_entry(self, mock_persist):
        """store_node appends its own audit entry with step_name='store'."""
        from docmind.library.pipeline.extraction.store import store_node

        state = _make_state()
        result = store_node(state)

        store_entry = result["audit_entries"][-1]
        assert store_entry["step_name"] == "store"
        assert store_entry["step_order"] == 4
        assert "extraction_id" in store_entry["output_summary"]

    @patch("docmind.library.pipeline.extraction.store._persist_results", new_callable=AsyncMock)
    def test_preserves_existing_audit_entries(self, mock_persist):
        """Existing audit entries are preserved and store entry appended."""
        from docmind.library.pipeline.extraction.store import store_node

        existing = [{"step_name": "preprocess", "step_order": 1}]
        state = _make_state(audit_entries=existing)
        result = store_node(state)

        assert len(result["audit_entries"]) == 2
        assert result["audit_entries"][0]["step_name"] == "preprocess"
        assert result["audit_entries"][-1]["step_name"] == "store"

    @patch("docmind.library.pipeline.extraction.store._persist_results", new_callable=AsyncMock)
    def test_returns_error_on_db_failure(self, mock_persist):
        """If _persist_results raises, returns status='error'."""
        from docmind.library.pipeline.extraction.store import store_node

        mock_persist.side_effect = RuntimeError("Connection refused")

        state = _make_state()
        result = store_node(state)

        assert result["status"] == "error"
        assert "Storage failed" in result["error_message"]

    @patch("docmind.library.pipeline.extraction.store._persist_results", new_callable=AsyncMock)
    def test_callback_invoked(self, mock_persist):
        """progress_callback is called during store."""
        from docmind.library.pipeline.extraction.store import store_node

        callback = MagicMock()
        state = _make_state(callback=callback)
        store_node(state)

        assert callback.call_count >= 1
