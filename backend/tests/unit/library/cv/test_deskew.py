"""
Tests for docmind.library.cv.deskew module.

Tests skew detection via Hough transform, image rotation correction,
and the combined detect_and_correct entry point. Uses synthetic images
with known geometry — no external files needed.
"""

import inspect

import cv2
import numpy as np
import pytest

from docmind.library.cv.deskew import (
    correct_skew,
    detect_and_correct,
    detect_skew,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic images with known geometry
# ---------------------------------------------------------------------------


@pytest.fixture
def blank_image() -> np.ndarray:
    """A blank white image — no edges, no lines to detect."""
    return np.ones((800, 600, 3), dtype=np.uint8) * 255


@pytest.fixture
def straight_line_image() -> np.ndarray:
    """Image with strong horizontal lines — expected skew angle ~0 degrees."""
    image = np.ones((800, 1000, 3), dtype=np.uint8) * 255
    for y in range(100, 700, 50):
        cv2.line(image, (50, y), (950, y), (0, 0, 0), 2)
    return image


@pytest.fixture
def skewed_line_image() -> np.ndarray:
    """Image with lines drawn at a known angle (~5 degrees)."""
    image = np.ones((800, 1000, 3), dtype=np.uint8) * 255
    angle_rad = np.radians(5.0)
    for y_base in range(100, 700, 60):
        x1, y1 = 50, y_base
        x2 = 950
        y2 = y_base + int((x2 - x1) * np.tan(angle_rad))
        cv2.line(image, (x1, y1), (x2, y2), (0, 0, 0), 2)
    return image


@pytest.fixture
def small_skew_line_image() -> np.ndarray:
    """Image with lines at ~1 degree — below the default 2.0 threshold."""
    image = np.ones((800, 1000, 3), dtype=np.uint8) * 255
    angle_rad = np.radians(1.0)
    for y_base in range(100, 700, 60):
        x1, y1 = 50, y_base
        x2 = 950
        y2 = y_base + int((x2 - x1) * np.tan(angle_rad))
        cv2.line(image, (x1, y1), (x2, y2), (0, 0, 0), 2)
    return image


@pytest.fixture
def grayscale_with_lines() -> np.ndarray:
    """Grayscale image (2D) with horizontal lines."""
    image = np.ones((800, 1000), dtype=np.uint8) * 255
    for y in range(100, 700, 50):
        cv2.line(image, (50, y), (950, y), 0, 2)
    return image


# ---------------------------------------------------------------------------
# detect_skew
# ---------------------------------------------------------------------------


class TestDetectSkew:
    """Tests for detect_skew function."""

    def test_returns_float(self, straight_line_image: np.ndarray) -> None:
        angle = detect_skew(straight_line_image)
        assert isinstance(angle, float)

    def test_blank_image_returns_zero(self, blank_image: np.ndarray) -> None:
        """No lines detected should return 0.0."""
        angle = detect_skew(blank_image)
        assert angle == 0.0

    def test_straight_lines_near_zero(self, straight_line_image: np.ndarray) -> None:
        """Horizontal lines should produce angle near 0."""
        angle = detect_skew(straight_line_image)
        assert abs(angle) < 2.0

    def test_skewed_lines_detects_angle(self, skewed_line_image: np.ndarray) -> None:
        """Lines at ~5 degrees should be detected."""
        angle = detect_skew(skewed_line_image)
        assert abs(angle) > 2.0
        assert abs(angle - 5.0) < 3.0

    def test_accepts_grayscale_input(self, grayscale_with_lines: np.ndarray) -> None:
        """Should handle 2D grayscale arrays without error."""
        angle = detect_skew(grayscale_with_lines)
        assert isinstance(angle, float)

    def test_does_not_mutate_input(self, straight_line_image: np.ndarray) -> None:
        original = straight_line_image.copy()
        _ = detect_skew(straight_line_image)
        np.testing.assert_array_equal(straight_line_image, original)


# ---------------------------------------------------------------------------
# correct_skew
# ---------------------------------------------------------------------------


class TestCorrectSkew:
    """Tests for correct_skew function."""

    def test_returns_ndarray(self, straight_line_image: np.ndarray) -> None:
        result = correct_skew(straight_line_image, 5.0)
        assert isinstance(result, np.ndarray)

    def test_preserves_shape(self, straight_line_image: np.ndarray) -> None:
        """Output should have same dimensions as input."""
        result = correct_skew(straight_line_image, 5.0)
        assert result.shape == straight_line_image.shape

    def test_preserves_dtype(self, straight_line_image: np.ndarray) -> None:
        result = correct_skew(straight_line_image, 5.0)
        assert result.dtype == straight_line_image.dtype

    def test_zero_angle_no_change(self, straight_line_image: np.ndarray) -> None:
        """Rotating by 0 degrees should produce identical output."""
        result = correct_skew(straight_line_image, 0.0)
        diff = np.abs(result.astype(float) - straight_line_image.astype(float))
        assert np.mean(diff) < 1.0

    def test_does_not_mutate_input(self, straight_line_image: np.ndarray) -> None:
        original = straight_line_image.copy()
        _ = correct_skew(straight_line_image, 10.0)
        np.testing.assert_array_equal(straight_line_image, original)

    def test_returns_new_array(self, straight_line_image: np.ndarray) -> None:
        result = correct_skew(straight_line_image, 5.0)
        assert result is not straight_line_image

    def test_rotation_changes_pixels(self, straight_line_image: np.ndarray) -> None:
        """A significant rotation should change pixel values."""
        result = correct_skew(straight_line_image, 15.0)
        assert not np.array_equal(result, straight_line_image)

    def test_no_black_edges(self, straight_line_image: np.ndarray) -> None:
        """BORDER_REPLICATE should prevent pure black corners."""
        result = correct_skew(straight_line_image, 10.0)
        corners = [
            result[0, 0],
            result[0, -1],
            result[-1, 0],
            result[-1, -1],
        ]
        for corner in corners:
            assert np.any(corner > 0), (
                "Corner pixel should not be pure black with BORDER_REPLICATE"
            )


# ---------------------------------------------------------------------------
# detect_and_correct
# ---------------------------------------------------------------------------


class TestDetectAndCorrect:
    """Tests for detect_and_correct combined function."""

    def test_returns_tuple(self, straight_line_image: np.ndarray) -> None:
        result = detect_and_correct(straight_line_image)
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], np.ndarray)
        assert isinstance(result[1], float)

    def test_below_threshold_returns_original(
        self, small_skew_line_image: np.ndarray
    ) -> None:
        """When angle < threshold, the SAME array object should be returned."""
        result_image, angle = detect_and_correct(small_skew_line_image, threshold=2.0)
        if abs(angle) < 2.0:
            assert result_image is small_skew_line_image

    def test_above_threshold_returns_corrected(
        self, skewed_line_image: np.ndarray
    ) -> None:
        """When angle > threshold, a new corrected image should be returned."""
        result_image, angle = detect_and_correct(skewed_line_image, threshold=2.0)
        if abs(angle) >= 2.0:
            assert result_image is not skewed_line_image

    def test_blank_image_returns_original(self, blank_image: np.ndarray) -> None:
        """No lines = 0.0 angle = below threshold = return original."""
        result_image, angle = detect_and_correct(blank_image)
        assert angle == 0.0
        assert result_image is blank_image

    def test_custom_threshold(self, skewed_line_image: np.ndarray) -> None:
        """A very high threshold should skip correction even for skewed images."""
        result_image, angle = detect_and_correct(skewed_line_image, threshold=90.0)
        assert result_image is skewed_line_image

    def test_default_threshold_is_two(self) -> None:
        """Verify the default threshold parameter is 2.0."""
        sig = inspect.signature(detect_and_correct)
        assert sig.parameters["threshold"].default == 2.0

    def test_angle_always_returned(self, skewed_line_image: np.ndarray) -> None:
        """The detected angle is always returned, regardless of correction."""
        _, angle_low_threshold = detect_and_correct(skewed_line_image, threshold=0.0)
        _, angle_high_threshold = detect_and_correct(skewed_line_image, threshold=90.0)
        assert abs(angle_low_threshold - angle_high_threshold) < 0.001


# ---------------------------------------------------------------------------
# Re-export via __init__.py
# ---------------------------------------------------------------------------


class TestReExport:
    """Verify the deskew_image re-export works."""

    def test_deskew_image_import(self) -> None:
        from docmind.library.cv import deskew_image

        assert callable(deskew_image)

    def test_deskew_image_is_detect_and_correct(self) -> None:
        from docmind.library.cv import deskew_image

        assert deskew_image is detect_and_correct
