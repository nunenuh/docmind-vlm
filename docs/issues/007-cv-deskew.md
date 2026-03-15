# Issue #7: CV Deskew — Hough Transform Skew Detection and Correction

## Summary

Implement the CV deskew module that detects document skew angle using the Hough line transform and corrects it by rotating the image. The module provides three pure functions: `detect_skew` returns the skew angle in degrees, `correct_skew` rotates an image by a given angle, and `detect_and_correct` combines both with a threshold to skip correction for nearly-straight documents. This module sits between preprocessing and quality assessment in the CV pipeline.

## Context

- **Phase**: 2 — CV + VLM Providers
- **Priority**: P0
- **Labels**: `phase-2-cv-vlm`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: #6 (cv-preprocessing — provides input images)
- **Branch**: `feat/7-cv-deskew`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/cv.md` — full section on `library/cv/deskew.py`, deskew rules, pipeline overview
- `specs/conventions/python-conventions.md` — PEP 8, type hints, naming
- `specs/conventions/testing.md` — test structure, TDD process

## Current State (Scaffold)

The scaffold at `backend/src/docmind/library/cv/deskew.py` already contains the full implementation:

```python
"""
docmind/library/cv/deskew.py

Document skew detection and correction using Hough line transform.
All functions are pure: take ndarray, return ndarray. Never mutate the input.
"""
import cv2
import numpy as np


def detect_skew(image: np.ndarray) -> float:
    """Detect document skew angle using Hough line transform."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
    if lines is None:
        return 0.0
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        angles.append(angle)
    median_angle = np.median(angles)
    return float(median_angle)


def correct_skew(image: np.ndarray, angle: float) -> np.ndarray:
    """Correct document skew by rotating the image."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    corrected = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return corrected


def detect_and_correct(image: np.ndarray, threshold: float = 2.0) -> tuple[np.ndarray, float]:
    """Detect and correct skew if angle exceeds threshold."""
    angle = detect_skew(image)
    if abs(angle) < threshold:
        return image, angle
    corrected = correct_skew(image, angle)
    return corrected, angle
```

The `__init__.py` re-exports:

```python
from .deskew import detect_and_correct as deskew_image
```

The test directory `backend/tests/unit/library/cv/` exists but contains no test files for deskew.

## Requirements

### Functional

1. `detect_skew(image)` must detect the skew angle of a document image in degrees using Hough line transform
2. `detect_skew` must return 0.0 when no lines are detected (e.g., blank image)
3. `detect_skew` must accept both BGR (3-channel) and grayscale (2D) input
4. `detect_skew` must return the median angle from detected lines
5. `correct_skew(image, angle)` must rotate the image by the given angle
6. `correct_skew` must use `BORDER_REPLICATE` to avoid black edges
7. `correct_skew` must use cubic interpolation (`INTER_CUBIC`)
8. `correct_skew` must return a new array (never mutate input)
9. `detect_and_correct(image, threshold=2.0)` must skip correction when `abs(angle) < threshold`
10. `detect_and_correct` must return the original image (same object) when below threshold
11. `detect_and_correct` must return the corrected image and detected angle when above threshold
12. The default threshold is 2.0 degrees

### Non-Functional

- All functions are pure: no side effects, no I/O
- Never mutate input arrays
- Threshold default of 2.0 avoids unnecessary interpolation artifacts on nearly-straight documents

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/cv/test_deskew.py`

```python
"""
Tests for docmind.library.cv.deskew module.

Tests skew detection via Hough transform, image rotation correction,
and the combined detect_and_correct entry point. Uses synthetic images
with known geometry — no external files needed.
"""
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
    """
    Image with strong horizontal lines — expected skew angle ~0 degrees.
    Draws multiple horizontal lines to ensure HoughLinesP detects them.
    """
    image = np.ones((800, 1000, 3), dtype=np.uint8) * 255
    for y in range(100, 700, 50):
        cv2.line(image, (50, y), (950, y), (0, 0, 0), 2)
    return image


@pytest.fixture
def skewed_line_image() -> np.ndarray:
    """
    Image with lines drawn at a known angle (~5 degrees).
    The lines are long enough for HoughLinesP to detect.
    """
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
    """
    Image with lines at ~1 degree — below the default 2.0 threshold.
    """
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
        assert abs(angle) < 2.0  # should be close to zero

    def test_skewed_lines_detects_angle(self, skewed_line_image: np.ndarray) -> None:
        """Lines at ~5 degrees should be detected."""
        angle = detect_skew(skewed_line_image)
        assert abs(angle) > 2.0  # should detect meaningful skew
        # The detected angle should be in the ballpark of 5 degrees
        assert abs(angle - 5.0) < 3.0  # allow tolerance for Hough detection

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
        # Allow tiny floating point differences from interpolation
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
        # Check corners — they should not be pure black (0,0,0)
        corners = [
            result[0, 0],
            result[0, -1],
            result[-1, 0],
            result[-1, -1],
        ]
        for corner in corners:
            # With BORDER_REPLICATE on a white image, corners should not be black
            assert np.any(corner > 0), "Corner pixel should not be pure black with BORDER_REPLICATE"


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

    def test_below_threshold_returns_original(self, small_skew_line_image: np.ndarray) -> None:
        """When angle < threshold, the SAME array object should be returned."""
        result_image, angle = detect_and_correct(small_skew_line_image, threshold=2.0)
        # If angle is below threshold, the original object is returned (identity check)
        if abs(angle) < 2.0:
            assert result_image is small_skew_line_image

    def test_above_threshold_returns_corrected(self, skewed_line_image: np.ndarray) -> None:
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
        # With threshold=90, virtually any detected angle will be below it
        assert result_image is skewed_line_image

    def test_default_threshold_is_two(self) -> None:
        """Verify the default threshold parameter is 2.0."""
        import inspect
        sig = inspect.signature(detect_and_correct)
        assert sig.parameters["threshold"].default == 2.0

    def test_angle_always_returned(self, skewed_line_image: np.ndarray) -> None:
        """The detected angle is always returned, regardless of correction."""
        _, angle_low_threshold = detect_and_correct(skewed_line_image, threshold=0.0)
        _, angle_high_threshold = detect_and_correct(skewed_line_image, threshold=90.0)
        # Same image should detect same angle regardless of threshold
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
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/cv/deskew.py` — The scaffold already contains the full implementation. Add full docstrings from the spec.

**Implementation guidance**:

The current scaffold code matches the spec implementation. The main work is:

1. **Add full docstrings** from `specs/backend/cv.md` to each function (the scaffold has one-liners).
2. **Verify all tests pass** — the logic is already implemented correctly.
3. **Confirm the re-export** in `__init__.py` works: `from docmind.library.cv import deskew_image`.

Key algorithm details:
- `detect_skew`: Converts to grayscale -> Canny edge detection (50, 150) -> HoughLinesP (threshold=100, minLineLength=100, maxLineGap=10) -> median of all detected line angles
- `correct_skew`: `getRotationMatrix2D` around image center -> `warpAffine` with INTER_CUBIC + BORDER_REPLICATE
- `detect_and_correct`: Combines both, skips correction if `abs(angle) < threshold`

### Step 3: Refactor (IMPROVE)

- Add comprehensive docstrings matching the spec
- Verify edge cases: empty images, images with no edges, very small images
- Ensure type hints are complete and correct
- No unnecessary imports

## Acceptance Criteria

- [ ] `detect_skew` returns 0.0 for blank images (no lines)
- [ ] `detect_skew` detects angle near 0 for straight-line images
- [ ] `detect_skew` detects meaningful angle for skewed images
- [ ] `detect_skew` accepts both BGR and grayscale input
- [ ] `correct_skew` rotates image without black edges (BORDER_REPLICATE)
- [ ] `correct_skew` preserves image shape and dtype
- [ ] `correct_skew` never mutates the input array
- [ ] `detect_and_correct` returns original image when below threshold
- [ ] `detect_and_correct` returns corrected image when above threshold
- [ ] `detect_and_correct` always returns the detected angle
- [ ] Default threshold is 2.0 degrees
- [ ] Re-export `deskew_image` works from `docmind.library.cv`
- [ ] All tests pass with `pytest backend/tests/unit/library/cv/test_deskew.py -v`

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/tests/unit/library/cv/__init__.py` | Create | Empty `__init__.py` for test package (if not already created by #6) |
| `backend/tests/unit/library/cv/test_deskew.py` | Create | Unit tests for deskew module |
| `backend/src/docmind/library/cv/deskew.py` | Modify | Add full docstrings from spec |

## Verification

```bash
# Run the tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/cv/test_deskew.py -v

# Run with coverage
python -m pytest backend/tests/unit/library/cv/test_deskew.py -v --cov=docmind.library.cv.deskew --cov-report=term-missing

# Verify re-export
python -c "from docmind.library.cv import deskew_image; print('OK')"

# Lint
ruff check backend/src/docmind/library/cv/deskew.py
```
