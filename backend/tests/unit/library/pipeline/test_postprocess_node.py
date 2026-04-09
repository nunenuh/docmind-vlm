"""
Unit tests for postprocess_node and its helper functions.

Tests verify confidence merging formula, CV quality lookup,
template validation, low-confidence explanations, and audit entries.
No database interaction — all pure functions.
"""
import uuid
from unittest.mock import MagicMock

import pytest


def _make_raw_field(
    field_key: str = "amount",
    confidence: float = 0.9,
    vlm_confidence: float | None = None,
    bounding_box: dict | None = None,
    is_required: bool = False,
    is_missing: bool = False,
    field_id: str | None = None,
) -> dict:
    """Create a raw extracted field dict."""
    return {
        "id": field_id or str(uuid.uuid4()),
        "field_type": "key_value",
        "field_key": field_key,
        "field_value": "100.00",
        "page_number": 1,
        "bounding_box": bounding_box or {"x": 0.5, "y": 0.5, "width": 0.2, "height": 0.05},
        "confidence": confidence,
        "vlm_confidence": vlm_confidence if vlm_confidence is not None else confidence,
        "is_required": is_required,
        "is_missing": is_missing,
    }


def _make_state(
    raw_fields: list[dict] | None = None,
    quality_map: dict | None = None,
    template_type: str | None = None,
    callback: object | None = None,
) -> dict:
    """Build a ProcessingState for postprocess_node."""
    return {
        "document_id": "doc-123",
        "user_id": "user-456",
        "file_bytes": b"",
        "file_type": "pdf",
        "template_type": template_type,
        "page_images": [],
        "page_count": 1,
        "quality_map": quality_map or {},
        "skew_angles": [],
        "raw_fields": raw_fields or [_make_raw_field()],
        "vlm_response": {},
        "document_type": "invoice",
        "enhanced_fields": [],
        "comparison_data": {},
        "extraction_id": "",
        "status": "processing",
        "error_message": None,
        "audit_entries": [],
        "progress_callback": callback,
    }


class TestMergeConfidence:
    """Tests for _merge_confidence helper."""

    def test_standard_merge(self):
        from docmind.library.pipeline.extraction.postprocess import _merge_confidence

        result = _merge_confidence(vlm_confidence=0.9, cv_quality=0.8)
        expected = 0.9 * 0.7 + 0.8 * 0.3  # 0.63 + 0.24 = 0.87
        assert abs(result - expected) < 0.001

    def test_clamped_to_max_1(self):
        from docmind.library.pipeline.extraction.postprocess import _merge_confidence

        result = _merge_confidence(vlm_confidence=1.0, cv_quality=1.0)
        assert result <= 1.0

    def test_clamped_to_min_0(self):
        from docmind.library.pipeline.extraction.postprocess import _merge_confidence

        result = _merge_confidence(vlm_confidence=0.0, cv_quality=0.0)
        assert result >= 0.0

    def test_rounded_to_4_decimals(self):
        from docmind.library.pipeline.extraction.postprocess import _merge_confidence

        result = _merge_confidence(vlm_confidence=0.333, cv_quality=0.777)
        assert len(str(result).split(".")[-1]) <= 4

    def test_vlm_weighted_more_than_cv(self):
        """VLM confidence has 70% weight vs CV 30%."""
        from docmind.library.pipeline.extraction.postprocess import _merge_confidence

        high_vlm = _merge_confidence(vlm_confidence=1.0, cv_quality=0.0)
        high_cv = _merge_confidence(vlm_confidence=0.0, cv_quality=1.0)
        assert high_vlm > high_cv


class TestLookupCvQuality:
    """Tests for _lookup_cv_quality helper."""

    def test_maps_bbox_center_to_grid_cell(self):
        from docmind.library.pipeline.extraction.postprocess import _lookup_cv_quality

        quality_map = {"1,2": {"overall_score": 0.85}}
        bbox = {"x": 0.5, "y": 0.3, "width": 0.1, "height": 0.1}
        # center_x = 0.55, center_y = 0.35
        # grid_col = int(0.55 * 4) = 2, grid_row = int(0.35 * 4) = 1
        result = _lookup_cv_quality(bbox, quality_map)
        assert result == 0.85

    def test_returns_fallback_when_no_quality_map(self):
        from docmind.library.pipeline.extraction.postprocess import _lookup_cv_quality

        result = _lookup_cv_quality({"x": 0.5, "y": 0.5}, {})
        assert result == 0.5

    def test_returns_fallback_when_no_bbox(self):
        from docmind.library.pipeline.extraction.postprocess import _lookup_cv_quality

        result = _lookup_cv_quality({}, {"0,0": {"overall_score": 0.9}})
        assert result == 0.5

    def test_returns_fallback_when_cell_not_found(self):
        from docmind.library.pipeline.extraction.postprocess import _lookup_cv_quality

        quality_map = {"0,0": {"overall_score": 0.9}}
        bbox = {"x": 0.9, "y": 0.9, "width": 0.05, "height": 0.05}
        result = _lookup_cv_quality(bbox, quality_map)
        # Cell (3,3) not in map -> fallback
        assert result == 0.5


class TestGenerateLowConfidenceExplanation:
    """Tests for _generate_low_confidence_explanation."""

    def test_returns_none_for_high_confidence(self):
        from docmind.library.pipeline.extraction.postprocess import _generate_low_confidence_explanation

        field = {"confidence": 0.8, "vlm_confidence": 0.8}
        result = _generate_low_confidence_explanation(field, cv_quality=0.9)
        assert result is None

    def test_returns_explanation_for_low_vlm_confidence(self):
        from docmind.library.pipeline.extraction.postprocess import _generate_low_confidence_explanation

        field = {"confidence": 0.3, "vlm_confidence": 0.3}
        result = _generate_low_confidence_explanation(field, cv_quality=0.8)
        assert result is not None
        assert "VLM" in result

    def test_returns_explanation_for_poor_image_quality(self):
        from docmind.library.pipeline.extraction.postprocess import _generate_low_confidence_explanation

        field = {"confidence": 0.4, "vlm_confidence": 0.6}
        result = _generate_low_confidence_explanation(field, cv_quality=0.2)
        assert result is not None
        assert "quality" in result.lower() or "blur" in result.lower() or "noise" in result.lower()

    def test_returns_explanation_for_missing_field(self):
        from docmind.library.pipeline.extraction.postprocess import _generate_low_confidence_explanation

        field = {"confidence": 0.0, "vlm_confidence": 0.0, "is_missing": True}
        result = _generate_low_confidence_explanation(field, cv_quality=0.5)
        assert result is not None
        assert "not found" in result or "missing" in result

    def test_returns_generic_explanation_when_no_specific_reason(self):
        from docmind.library.pipeline.extraction.postprocess import _generate_low_confidence_explanation

        field = {"confidence": 0.4, "vlm_confidence": 0.6}
        result = _generate_low_confidence_explanation(field, cv_quality=0.8)
        assert result is not None
        assert "threshold" in result or "below" in result


class TestValidateTemplateFields:
    """Tests for _validate_template_fields."""

    def test_adds_missing_required_fields_as_placeholders(self):
        from docmind.library.pipeline.extraction.postprocess import _validate_template_fields

        fields = [_make_raw_field(field_key="invoice_number")]
        result = _validate_template_fields(fields, "invoice")

        keys = [f["field_key"] for f in result]
        assert "date" in keys
        assert "total_amount" in keys
        assert "vendor_name" in keys

    def test_placeholder_fields_have_correct_markers(self):
        from docmind.library.pipeline.extraction.postprocess import _validate_template_fields

        fields = []
        result = _validate_template_fields(fields, "invoice")

        for field in result:
            assert field["is_required"] is True
            assert field["is_missing"] is True
            assert field["confidence"] == 0.0
            assert field["field_value"] == ""

    def test_marks_existing_required_fields(self):
        from docmind.library.pipeline.extraction.postprocess import _validate_template_fields

        fields = [_make_raw_field(field_key="invoice_number", confidence=0.9)]
        result = _validate_template_fields(fields, "invoice")

        inv_field = next(f for f in result if f["field_key"] == "invoice_number")
        assert inv_field["is_required"] is True
        assert inv_field.get("is_missing", False) is False

    def test_returns_fields_unchanged_when_no_template(self):
        from docmind.library.pipeline.extraction.postprocess import _validate_template_fields

        fields = [_make_raw_field(field_key="random_field")]
        result = _validate_template_fields(fields, None)

        assert len(result) == 1
        assert result[0]["field_key"] == "random_field"

    def test_does_not_duplicate_existing_required_fields(self):
        from docmind.library.pipeline.extraction.postprocess import _validate_template_fields

        fields = [
            _make_raw_field(field_key="invoice_number"),
            _make_raw_field(field_key="date"),
            _make_raw_field(field_key="total_amount"),
            _make_raw_field(field_key="vendor_name"),
        ]
        result = _validate_template_fields(fields, "invoice")

        keys = [f["field_key"] for f in result]
        assert keys.count("invoice_number") == 1
        assert keys.count("date") == 1


class TestPostprocessNode:
    """Integration tests for postprocess_node."""

    def test_merges_confidence_on_all_fields(self):
        from docmind.library.pipeline.extraction.postprocess import postprocess_node

        quality_map = {"2,2": {"overall_score": 0.8}}
        fields = [_make_raw_field(
            vlm_confidence=0.9,
            bounding_box={"x": 0.5, "y": 0.5, "width": 0.1, "height": 0.1},
        )]
        state = _make_state(raw_fields=fields, quality_map=quality_map)
        result = postprocess_node(state)

        enhanced = result["enhanced_fields"]
        assert len(enhanced) == 1
        assert "confidence" in enhanced[0]
        assert "vlm_confidence" in enhanced[0]
        assert "cv_quality_score" in enhanced[0]

    def test_creates_comparison_data(self):
        from docmind.library.pipeline.extraction.postprocess import postprocess_node

        state = _make_state()
        result = postprocess_node(state)

        assert "comparison_data" in result
        assert "corrected" in result["comparison_data"]
        assert "added" in result["comparison_data"]

    def test_creates_audit_entry(self):
        from docmind.library.pipeline.extraction.postprocess import postprocess_node

        state = _make_state()
        result = postprocess_node(state)

        assert len(result["audit_entries"]) >= 1
        entry = result["audit_entries"][-1]
        assert entry["step_name"] == "postprocess"
        assert entry["step_order"] == 3

    def test_returns_error_on_exception(self):
        from docmind.library.pipeline.extraction.postprocess import postprocess_node

        state = _make_state()
        state["raw_fields"] = "not-a-list"  # type: ignore
        result = postprocess_node(state)

        assert result["status"] == "error"
        assert "Postprocessing failed" in result["error_message"]

    def test_callback_invoked(self):
        from docmind.library.pipeline.extraction.postprocess import postprocess_node

        callback = MagicMock()
        state = _make_state(callback=callback)
        postprocess_node(state)

        assert callback.call_count >= 2
