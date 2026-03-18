"""
Unit tests for the preprocess_node pipeline function.

All CV library functions are mocked — these tests verify
state transitions, audit entry creation, callback invocation,
and error handling.
"""
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import numpy as np
import pytest


@dataclass(frozen=True)
class FakeRegionQuality:
    blur_score: float
    noise_score: float
    contrast_score: float
    overall_score: float


def _make_state(
    file_bytes: bytes = b"fake-pdf-bytes",
    file_type: str = "pdf",
    callback: object | None = None,
) -> dict:
    """Build a minimal ProcessingState dict for preprocess_node."""
    return {
        "document_id": "doc-123",
        "user_id": "user-456",
        "file_bytes": file_bytes,
        "file_type": file_type,
        "template_type": None,
        "page_images": [],
        "page_count": 0,
        "quality_map": {},
        "skew_angles": [],
        "raw_fields": [],
        "vlm_response": {},
        "document_type": None,
        "enhanced_fields": [],
        "comparison_data": {},
        "extraction_id": "",
        "status": "processing",
        "error_message": None,
        "audit_entries": [],
        "progress_callback": callback,
    }


class TestPreprocessNodeHappyPath:
    """Tests for successful preprocessing."""

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_page_images_and_count(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """preprocess_node returns corrected images and page count."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img, fake_img]
        mock_deskew.side_effect = [(fake_img, 0.5), (fake_img, -1.2)]
        mock_quality.return_value = {
            (0, 0): FakeRegionQuality(10.0, 5.0, 40.0, 0.75),
        }

        state = _make_state()
        result = preprocess_node(state)

        assert len(result["page_images"]) == 2
        assert result["page_count"] == 2

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_skew_angles(self, mock_convert, mock_deskew, mock_quality):
        """preprocess_node collects skew angles from each page."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 3.14)
        mock_quality.return_value = {}

        state = _make_state()
        result = preprocess_node(state)

        assert result["skew_angles"] == [3.14]

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_serializes_quality_map(self, mock_convert, mock_deskew, mock_quality):
        """Quality map keys are serialized from tuples to 'row,col' strings."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {
            (0, 0): FakeRegionQuality(10.0, 5.0, 40.0, 0.8),
            (1, 2): FakeRegionQuality(20.0, 8.0, 50.0, 0.6),
        }

        state = _make_state()
        result = preprocess_node(state)

        assert "0,0" in result["quality_map"]
        assert "1,2" in result["quality_map"]
        assert result["quality_map"]["0,0"]["overall_score"] == 0.8
        assert result["quality_map"]["1,2"]["blur_score"] == 20.0

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_creates_audit_entry(self, mock_convert, mock_deskew, mock_quality):
        """preprocess_node appends an audit entry with step_name='preprocess'."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        state = _make_state()
        result = preprocess_node(state)

        assert len(result["audit_entries"]) == 1
        entry = result["audit_entries"][0]
        assert entry["step_name"] == "preprocess"
        assert entry["step_order"] == 1
        assert "file_type" in entry["input_summary"]
        assert "page_count" in entry["output_summary"]
        assert isinstance(entry["duration_ms"], int)
        assert entry["duration_ms"] >= 0

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_appends_to_existing_audit_entries(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """Audit entries accumulate; existing entries are preserved."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        existing_entry = {"step_name": "init", "step_order": 0}
        state = _make_state()
        state["audit_entries"] = [existing_entry]
        result = preprocess_node(state)

        assert len(result["audit_entries"]) == 2
        assert result["audit_entries"][0]["step_name"] == "init"
        assert result["audit_entries"][1]["step_name"] == "preprocess"

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_does_not_set_error_status_on_success(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """On success, result should NOT contain status='error'."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        state = _make_state()
        result = preprocess_node(state)

        assert result.get("status") != "error"


class TestPreprocessNodeCallback:
    """Tests for progress callback invocation."""

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_callback_invoked_at_each_substep(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """progress_callback is called at multiple progress points."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        callback = MagicMock()
        state = _make_state(callback=callback)
        preprocess_node(state)

        assert callback.call_count >= 3

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_works_without_callback(self, mock_convert, mock_deskew, mock_quality):
        """preprocess_node works fine when progress_callback is None."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {}

        state = _make_state(callback=None)
        result = preprocess_node(state)

        assert result["page_count"] == 1


class TestPreprocessNodeErrorHandling:
    """Tests for error cases."""

    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_error_on_conversion_failure(self, mock_convert):
        """If convert_to_page_images raises, returns status='error'."""
        from docmind.library.pipeline.processing import preprocess_node

        mock_convert.side_effect = ValueError("Unsupported file type: xyz")

        state = _make_state(file_type="xyz")
        result = preprocess_node(state)

        assert result["status"] == "error"
        assert "Preprocessing failed" in result["error_message"]

    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_returns_error_on_deskew_failure(self, mock_convert, mock_deskew):
        """If detect_and_correct raises, returns status='error'."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.side_effect = RuntimeError("Deskew failed")

        state = _make_state()
        result = preprocess_node(state)

        assert result["status"] == "error"
        assert "Preprocessing failed" in result["error_message"]

    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_handles_empty_file_bytes(self, mock_convert):
        """Empty file bytes should propagate as an error."""
        from docmind.library.pipeline.processing import preprocess_node

        mock_convert.side_effect = ValueError("PDF bytes cannot be empty")

        state = _make_state(file_bytes=b"")
        result = preprocess_node(state)

        assert result["status"] == "error"


class TestPreprocessNodeQualityMapEdgeCases:
    """Tests for quality map edge cases."""

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_empty_quality_map_when_no_images(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """If no corrected images, quality_map should be empty."""
        from docmind.library.pipeline.processing import preprocess_node

        mock_convert.return_value = []

        state = _make_state()
        result = preprocess_node(state)

        assert result["quality_map"] == {}
        assert result["page_count"] == 0

    @patch("docmind.library.pipeline.processing.assess_regions")
    @patch("docmind.library.pipeline.processing.detect_and_correct")
    @patch("docmind.library.pipeline.processing.convert_to_page_images")
    def test_mean_quality_in_audit_with_regions(
        self, mock_convert, mock_deskew, mock_quality
    ):
        """Audit output_summary includes mean_quality computed from quality_map."""
        from docmind.library.pipeline.processing import preprocess_node

        fake_img = np.zeros((100, 100, 3), dtype=np.uint8)
        mock_convert.return_value = [fake_img]
        mock_deskew.return_value = (fake_img, 0.0)
        mock_quality.return_value = {
            (0, 0): FakeRegionQuality(10.0, 5.0, 40.0, 0.8),
            (0, 1): FakeRegionQuality(10.0, 5.0, 40.0, 0.6),
        }

        state = _make_state()
        result = preprocess_node(state)

        audit = result["audit_entries"][-1]
        expected_mean = (0.8 + 0.6) / 2
        assert abs(audit["output_summary"]["mean_quality"] - expected_mean) < 0.01
