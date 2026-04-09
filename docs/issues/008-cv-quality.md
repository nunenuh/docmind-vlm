# Issue #8: CV Quality Assessment — Blur, Noise, and Contrast per Region

## Summary

Implement the CV quality assessment module that measures image quality (blur, noise, contrast) per region of a document image. The module produces a quality map — a dictionary of `RegionQuality` frozen dataclasses keyed by grid position — that the downstream pipeline uses to weight VLM confidence by local image quality. Individual assessment functions (`assess_blur`, `assess_noise`, `assess_contrast`) are composable building blocks, and `assess_regions` divides the image into a configurable grid for per-region analysis.

## Context

- **Phase**: 2 — CV + VLM Providers
- **Priority**: P0
- **Labels**: `phase-2-cv-vlm`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: #6 (cv-preprocessing — provides normalized images)
- **Branch**: `feat/8-cv-quality`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/cv.md` — full section on `library/cv/quality.py`, quality rules, `RegionQuality` dataclass, scoring weights
- `specs/conventions/python-conventions.md` — PEP 8, type hints, naming, frozen dataclasses
- `specs/conventions/testing.md` — test structure, TDD process

## Current State (Scaffold)

The scaffold at `backend/src/docmind/library/cv/quality.py` already contains the full implementation:

```python
"""
docmind/library/cv/quality.py

Image quality assessment per region.
"""
import cv2
import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class RegionQuality:
    blur_score: float
    noise_score: float
    contrast_score: float
    overall_score: float


def assess_blur(region: np.ndarray) -> float:
    laplacian = cv2.Laplacian(region, cv2.CV_64F)
    return float(np.var(laplacian))


def assess_noise(region: np.ndarray) -> float:
    median_filtered = cv2.medianBlur(region, 5)
    diff = np.abs(region.astype(np.float64) - median_filtered.astype(np.float64))
    return float(np.mean(diff))


def assess_contrast(region: np.ndarray) -> float:
    return float(np.std(region.astype(np.float64)))


def _compute_overall_score(blur: float, noise: float, contrast: float) -> float:
    blur_norm = min(blur / 200.0, 1.0)
    noise_norm = max(1.0 - (noise / 30.0), 0.0)
    contrast_norm = min(contrast / 60.0, 1.0)
    overall = (0.4 * blur_norm) + (0.3 * noise_norm) + (0.3 * contrast_norm)
    return round(max(0.0, min(1.0, overall)), 4)


def assess_region(region: np.ndarray) -> RegionQuality:
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region
    blur = assess_blur(gray)
    noise = assess_noise(gray)
    contrast = assess_contrast(gray)
    overall = _compute_overall_score(blur, noise, contrast)
    return RegionQuality(blur_score=round(blur, 2), noise_score=round(noise, 2), contrast_score=round(contrast, 2), overall_score=overall)


def assess_regions(image: np.ndarray, grid_rows: int = 4, grid_cols: int = 4) -> dict[tuple[int, int], RegionQuality]:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    h, w = gray.shape[:2]
    cell_h = h // grid_rows
    cell_w = w // grid_cols
    quality_map: dict[tuple[int, int], RegionQuality] = {}
    for row in range(grid_rows):
        for col in range(grid_cols):
            y_start = row * cell_h
            y_end = (row + 1) * cell_h if row < grid_rows - 1 else h
            x_start = col * cell_w
            x_end = (col + 1) * cell_w if col < grid_cols - 1 else w
            cell = gray[y_start:y_end, x_start:x_end]
            if cell.size == 0:
                continue
            quality_map[(row, col)] = assess_region(cell)
    return quality_map
```

The `__init__.py` re-exports:

```python
from .quality import assess_regions as assess_quality
```

The test directory `backend/tests/unit/library/cv/` exists but contains no test files for quality.

## Requirements

### Functional

1. `RegionQuality` must be a frozen dataclass with fields: `blur_score`, `noise_score`, `contrast_score`, `overall_score`
2. `RegionQuality` must be immutable — attempting to set attributes should raise `FrozenInstanceError`
3. `assess_blur(region)` must return Laplacian variance (higher = sharper)
4. `assess_noise(region)` must return mean absolute deviation from median filter (lower = cleaner)
5. `assess_contrast(region)` must return standard deviation of pixel intensities (higher = better)
6. `_compute_overall_score` must weight: blur 40%, noise 30%, contrast 30%
7. `_compute_overall_score` must return a value in [0.0, 1.0]
8. `assess_region(region)` must accept both BGR and grayscale input
9. `assess_region` must return a `RegionQuality` with all metrics rounded to 2 decimal places (4 for overall)
10. `assess_regions(image, grid_rows=4, grid_cols=4)` must divide the image into a grid and assess each cell
11. `assess_regions` must return a dict keyed by `(row, col)` tuples (0-indexed)
12. `assess_regions` must produce `grid_rows * grid_cols` entries for normal images
13. `assess_regions` must handle non-uniform grid edges (last row/col may be larger)
14. `assess_regions` must skip empty cells (cell.size == 0)

### Non-Functional

- All functions are pure: no side effects, no I/O
- `RegionQuality` is frozen — immutable after creation
- Blur detection uses Laplacian variance — industry standard
- Noise detection uses median filter comparison — robust against structured content
- All individual assessments operate on grayscale input

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/cv/test_quality.py`

```python
"""
Tests for docmind.library.cv.quality module.

Tests blur, noise, and contrast assessment on synthetic images with
known characteristics. Verifies grid-based region quality mapping.
"""
import cv2
import dataclasses
import numpy as np
import pytest

from docmind.library.cv.quality import (
    RegionQuality,
    _compute_overall_score,
    assess_blur,
    assess_contrast,
    assess_noise,
    assess_region,
    assess_regions,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic images with known quality characteristics
# ---------------------------------------------------------------------------

@pytest.fixture
def sharp_image() -> np.ndarray:
    """
    Sharp grayscale image with strong edges.
    High Laplacian variance expected.
    """
    image = np.zeros((200, 200), dtype=np.uint8)
    # Draw a grid of sharp lines
    for i in range(0, 200, 20):
        cv2.line(image, (i, 0), (i, 199), 255, 1)
        cv2.line(image, (0, i), (199, i), 255, 1)
    return image


@pytest.fixture
def blurry_image(sharp_image: np.ndarray) -> np.ndarray:
    """
    Blurred version of sharp_image.
    Low Laplacian variance expected.
    """
    return cv2.GaussianBlur(sharp_image, (31, 31), 10)


@pytest.fixture
def clean_image() -> np.ndarray:
    """
    Clean gradient image — minimal noise.
    Low noise score expected.
    """
    gradient = np.tile(np.arange(200, dtype=np.uint8), (200, 1))
    return gradient


@pytest.fixture
def noisy_image(clean_image: np.ndarray) -> np.ndarray:
    """
    Noisy version of clean_image with added Gaussian noise.
    High noise score expected.
    """
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 30, clean_image.shape).astype(np.float64)
    noisy = np.clip(clean_image.astype(np.float64) + noise, 0, 255).astype(np.uint8)
    return noisy


@pytest.fixture
def high_contrast_image() -> np.ndarray:
    """
    Image with strong contrast (black and white halves).
    High contrast score expected.
    """
    image = np.zeros((200, 200), dtype=np.uint8)
    image[:, 100:] = 255
    return image


@pytest.fixture
def low_contrast_image() -> np.ndarray:
    """
    Uniformly gray image — minimal contrast.
    Low contrast score expected.
    """
    return np.ones((200, 200), dtype=np.uint8) * 128


@pytest.fixture
def bgr_test_image() -> np.ndarray:
    """BGR 3-channel test image for assess_region and assess_regions."""
    image = np.zeros((400, 400, 3), dtype=np.uint8)
    # Add some structure
    cv2.rectangle(image, (50, 50), (350, 350), (255, 255, 255), 2)
    cv2.line(image, (0, 200), (400, 200), (128, 128, 128), 2)
    return image


@pytest.fixture
def large_bgr_image() -> np.ndarray:
    """Larger BGR image for grid division tests."""
    rng = np.random.default_rng(42)
    return rng.integers(0, 255, (800, 1200, 3), dtype=np.uint8)


# ---------------------------------------------------------------------------
# RegionQuality dataclass
# ---------------------------------------------------------------------------

class TestRegionQuality:
    """Tests for RegionQuality frozen dataclass."""

    def test_creation(self) -> None:
        rq = RegionQuality(blur_score=100.0, noise_score=5.0, contrast_score=50.0, overall_score=0.8)
        assert rq.blur_score == 100.0
        assert rq.noise_score == 5.0
        assert rq.contrast_score == 50.0
        assert rq.overall_score == 0.8

    def test_is_frozen(self) -> None:
        rq = RegionQuality(blur_score=100.0, noise_score=5.0, contrast_score=50.0, overall_score=0.8)
        with pytest.raises(dataclasses.FrozenInstanceError):
            rq.blur_score = 200.0  # type: ignore[misc]

    def test_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(RegionQuality)

    def test_equality(self) -> None:
        rq1 = RegionQuality(blur_score=100.0, noise_score=5.0, contrast_score=50.0, overall_score=0.8)
        rq2 = RegionQuality(blur_score=100.0, noise_score=5.0, contrast_score=50.0, overall_score=0.8)
        assert rq1 == rq2

    def test_fields(self) -> None:
        fields = {f.name for f in dataclasses.fields(RegionQuality)}
        assert fields == {"blur_score", "noise_score", "contrast_score", "overall_score"}


# ---------------------------------------------------------------------------
# assess_blur
# ---------------------------------------------------------------------------

class TestAssessBlur:
    """Tests for assess_blur function."""

    def test_returns_float(self, sharp_image: np.ndarray) -> None:
        result = assess_blur(sharp_image)
        assert isinstance(result, float)

    def test_sharp_higher_than_blurry(
        self, sharp_image: np.ndarray, blurry_image: np.ndarray
    ) -> None:
        """Sharp images should have higher Laplacian variance than blurry ones."""
        sharp_score = assess_blur(sharp_image)
        blurry_score = assess_blur(blurry_image)
        assert sharp_score > blurry_score

    def test_non_negative(self, sharp_image: np.ndarray) -> None:
        """Variance is always non-negative."""
        assert assess_blur(sharp_image) >= 0.0

    def test_uniform_image_low_score(self) -> None:
        """A perfectly uniform image should have very low blur score."""
        uniform = np.ones((100, 100), dtype=np.uint8) * 128
        assert assess_blur(uniform) < 1.0


# ---------------------------------------------------------------------------
# assess_noise
# ---------------------------------------------------------------------------

class TestAssessNoise:
    """Tests for assess_noise function."""

    def test_returns_float(self, clean_image: np.ndarray) -> None:
        result = assess_noise(clean_image)
        assert isinstance(result, float)

    def test_noisy_higher_than_clean(
        self, clean_image: np.ndarray, noisy_image: np.ndarray
    ) -> None:
        """Noisy images should have higher median filter deviation."""
        clean_score = assess_noise(clean_image)
        noisy_score = assess_noise(noisy_image)
        assert noisy_score > clean_score

    def test_non_negative(self, clean_image: np.ndarray) -> None:
        assert assess_noise(clean_image) >= 0.0

    def test_uniform_image_zero_noise(self) -> None:
        """A perfectly uniform image should have zero noise."""
        uniform = np.ones((100, 100), dtype=np.uint8) * 128
        assert assess_noise(uniform) == 0.0


# ---------------------------------------------------------------------------
# assess_contrast
# ---------------------------------------------------------------------------

class TestAssessContrast:
    """Tests for assess_contrast function."""

    def test_returns_float(self, high_contrast_image: np.ndarray) -> None:
        result = assess_contrast(high_contrast_image)
        assert isinstance(result, float)

    def test_high_contrast_higher_score(
        self, high_contrast_image: np.ndarray, low_contrast_image: np.ndarray
    ) -> None:
        """High-contrast images should have higher std dev than uniform ones."""
        high_score = assess_contrast(high_contrast_image)
        low_score = assess_contrast(low_contrast_image)
        assert high_score > low_score

    def test_non_negative(self, high_contrast_image: np.ndarray) -> None:
        assert assess_contrast(high_contrast_image) >= 0.0

    def test_uniform_image_zero_contrast(self) -> None:
        """A perfectly uniform image should have zero contrast."""
        uniform = np.ones((100, 100), dtype=np.uint8) * 128
        assert assess_contrast(uniform) == 0.0


# ---------------------------------------------------------------------------
# _compute_overall_score
# ---------------------------------------------------------------------------

class TestComputeOverallScore:
    """Tests for _compute_overall_score internal function."""

    def test_returns_float(self) -> None:
        result = _compute_overall_score(100.0, 5.0, 50.0)
        assert isinstance(result, float)

    def test_result_in_range(self) -> None:
        """Overall score must be in [0.0, 1.0]."""
        result = _compute_overall_score(100.0, 5.0, 50.0)
        assert 0.0 <= result <= 1.0

    def test_perfect_scores(self) -> None:
        """Best-case metrics should produce score near 1.0."""
        # blur >= 200 -> 1.0, noise = 0 -> 1.0, contrast >= 60 -> 1.0
        result = _compute_overall_score(200.0, 0.0, 60.0)
        assert result == 1.0

    def test_worst_scores(self) -> None:
        """Worst-case metrics should produce score near 0.0."""
        # blur = 0 -> 0.0, noise >= 30 -> 0.0, contrast = 0 -> 0.0
        result = _compute_overall_score(0.0, 30.0, 0.0)
        assert result == 0.0

    def test_weights_blur_40_noise_30_contrast_30(self) -> None:
        """Verify the weighting: blur 40%, noise 30%, contrast 30%."""
        # Only blur contributes: blur=200 (norm=1.0), noise=30 (norm=0), contrast=0 (norm=0)
        blur_only = _compute_overall_score(200.0, 30.0, 0.0)
        assert abs(blur_only - 0.4) < 0.001

        # Only noise contributes: blur=0 (norm=0), noise=0 (norm=1.0), contrast=0 (norm=0)
        noise_only = _compute_overall_score(0.0, 0.0, 0.0)
        assert abs(noise_only - 0.3) < 0.001

        # Only contrast contributes: blur=0 (norm=0), noise=30 (norm=0), contrast=60 (norm=1.0)
        contrast_only = _compute_overall_score(0.0, 30.0, 60.0)
        assert abs(contrast_only - 0.3) < 0.001

    def test_clamps_to_range(self) -> None:
        """Even with extreme inputs, result should stay in [0, 1]."""
        result_high = _compute_overall_score(10000.0, 0.0, 10000.0)
        assert result_high <= 1.0

        result_low = _compute_overall_score(0.0, 10000.0, 0.0)
        assert result_low >= 0.0

    def test_rounded_to_four_decimals(self) -> None:
        result = _compute_overall_score(150.0, 10.0, 45.0)
        # Check that the result has at most 4 decimal places
        assert result == round(result, 4)


# ---------------------------------------------------------------------------
# assess_region
# ---------------------------------------------------------------------------

class TestAssessRegion:
    """Tests for assess_region function."""

    def test_returns_region_quality(self, sharp_image: np.ndarray) -> None:
        result = assess_region(sharp_image)
        assert isinstance(result, RegionQuality)

    def test_accepts_bgr_input(self, bgr_test_image: np.ndarray) -> None:
        """Should handle 3-channel BGR input by converting to grayscale."""
        region = bgr_test_image[50:150, 50:150]
        result = assess_region(region)
        assert isinstance(result, RegionQuality)

    def test_accepts_grayscale_input(self, sharp_image: np.ndarray) -> None:
        result = assess_region(sharp_image)
        assert isinstance(result, RegionQuality)

    def test_scores_are_rounded(self, sharp_image: np.ndarray) -> None:
        result = assess_region(sharp_image)
        assert result.blur_score == round(result.blur_score, 2)
        assert result.noise_score == round(result.noise_score, 2)
        assert result.contrast_score == round(result.contrast_score, 2)
        assert result.overall_score == round(result.overall_score, 4)

    def test_overall_in_range(self, sharp_image: np.ndarray) -> None:
        result = assess_region(sharp_image)
        assert 0.0 <= result.overall_score <= 1.0

    def test_sharp_vs_blurry_region(
        self, sharp_image: np.ndarray, blurry_image: np.ndarray
    ) -> None:
        sharp_quality = assess_region(sharp_image)
        blurry_quality = assess_region(blurry_image)
        assert sharp_quality.blur_score > blurry_quality.blur_score


# ---------------------------------------------------------------------------
# assess_regions
# ---------------------------------------------------------------------------

class TestAssessRegions:
    """Tests for assess_regions grid-based quality mapping."""

    def test_returns_dict(self, bgr_test_image: np.ndarray) -> None:
        result = assess_regions(bgr_test_image)
        assert isinstance(result, dict)

    def test_default_grid_4x4(self, bgr_test_image: np.ndarray) -> None:
        """Default grid should produce 16 regions (4x4)."""
        result = assess_regions(bgr_test_image)
        assert len(result) == 16

    def test_keys_are_tuples(self, bgr_test_image: np.ndarray) -> None:
        result = assess_regions(bgr_test_image)
        for key in result:
            assert isinstance(key, tuple)
            assert len(key) == 2
            row, col = key
            assert isinstance(row, int)
            assert isinstance(col, int)

    def test_values_are_region_quality(self, bgr_test_image: np.ndarray) -> None:
        result = assess_regions(bgr_test_image)
        for value in result.values():
            assert isinstance(value, RegionQuality)

    def test_grid_coordinates_zero_indexed(self, bgr_test_image: np.ndarray) -> None:
        result = assess_regions(bgr_test_image, grid_rows=4, grid_cols=4)
        for row, col in result.keys():
            assert 0 <= row < 4
            assert 0 <= col < 4

    @pytest.mark.parametrize(
        "grid_rows,grid_cols,expected_count",
        [
            (1, 1, 1),
            (2, 2, 4),
            (3, 3, 9),
            (4, 4, 16),
            (2, 4, 8),
            (4, 2, 8),
        ],
    )
    def test_custom_grid_sizes(
        self,
        large_bgr_image: np.ndarray,
        grid_rows: int,
        grid_cols: int,
        expected_count: int,
    ) -> None:
        result = assess_regions(large_bgr_image, grid_rows=grid_rows, grid_cols=grid_cols)
        assert len(result) == expected_count

    def test_accepts_grayscale(self) -> None:
        gray = np.ones((400, 400), dtype=np.uint8) * 128
        result = assess_regions(gray, grid_rows=2, grid_cols=2)
        assert len(result) == 4

    def test_all_keys_present(self, bgr_test_image: np.ndarray) -> None:
        """All (row, col) combinations should be present for normal images."""
        result = assess_regions(bgr_test_image, grid_rows=3, grid_cols=3)
        expected_keys = {(r, c) for r in range(3) for c in range(3)}
        assert set(result.keys()) == expected_keys

    def test_last_row_col_handles_remainder(self) -> None:
        """
        For images not evenly divisible by grid size, the last row/col
        should include the remainder pixels.
        """
        # 401x401 with 4x4 grid: cell size = 100, last row/col = 101
        image = np.ones((401, 401, 3), dtype=np.uint8) * 128
        result = assess_regions(image, grid_rows=4, grid_cols=4)
        assert len(result) == 16  # should still have all 16 cells


# ---------------------------------------------------------------------------
# Re-export via __init__.py
# ---------------------------------------------------------------------------

class TestReExport:
    """Verify the assess_quality re-export works."""

    def test_assess_quality_import(self) -> None:
        from docmind.library.cv import assess_quality
        assert callable(assess_quality)

    def test_assess_quality_is_assess_regions(self) -> None:
        from docmind.library.cv import assess_quality
        assert assess_quality is assess_regions
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/cv/quality.py` — The scaffold already contains the full implementation. Add full docstrings from the spec.

**Implementation guidance**:

The current scaffold code matches the spec implementation. The main work is:

1. **Add full docstrings** from `specs/backend/cv.md` to each function and the `RegionQuality` dataclass with attribute descriptions.
2. **Verify all tests pass** — the logic is already implemented correctly.
3. **Confirm the re-export** in `__init__.py` works: `from docmind.library.cv import assess_quality`.

Key algorithm details:
- `assess_blur`: `cv2.Laplacian(region, cv2.CV_64F)` -> `np.var()`. Higher variance = more edges = sharper.
- `assess_noise`: Compare to `cv2.medianBlur(region, 5)` via mean absolute difference. Lower = cleaner.
- `assess_contrast`: `np.std()` of pixel intensities. Higher = more contrast.
- `_compute_overall_score`: Normalize each metric to [0,1], then weighted sum: 0.4*blur + 0.3*noise + 0.3*contrast.
- `assess_regions`: Integer division for cell sizes; last row/col absorbs remainder pixels.

### Step 3: Refactor (IMPROVE)

- Add comprehensive docstrings matching the spec (including threshold guidance in docstrings)
- Ensure all type hints are complete
- Verify `RegionQuality` attribute docstrings explain the metric meaning and typical ranges
- No unnecessary imports

## Acceptance Criteria

- [ ] `RegionQuality` is a frozen dataclass with 4 float fields
- [ ] `RegionQuality` cannot be mutated after creation
- [ ] `assess_blur` returns higher scores for sharp images than blurry ones
- [ ] `assess_noise` returns higher scores for noisy images than clean ones
- [ ] `assess_contrast` returns higher scores for high-contrast images than uniform ones
- [ ] `_compute_overall_score` produces values in [0.0, 1.0] with correct weights (40/30/30)
- [ ] `assess_region` accepts BGR and grayscale input and returns `RegionQuality`
- [ ] `assess_region` rounds scores to 2 decimals (4 for overall)
- [ ] `assess_regions` produces correct number of regions for any grid size
- [ ] `assess_regions` keys are 0-indexed `(row, col)` tuples
- [ ] `assess_regions` handles images not evenly divisible by grid size
- [ ] Re-export `assess_quality` works from `docmind.library.cv`
- [ ] All tests pass with `pytest backend/tests/unit/library/cv/test_quality.py -v`

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/tests/unit/library/cv/__init__.py` | Create | Empty `__init__.py` for test package (if not already created by #6) |
| `backend/tests/unit/library/cv/test_quality.py` | Create | Unit tests for quality assessment module |
| `backend/src/docmind/library/cv/quality.py` | Modify | Add full docstrings from spec |

## Verification

```bash
# Run the tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/cv/test_quality.py -v

# Run with coverage
python -m pytest backend/tests/unit/library/cv/test_quality.py -v --cov=docmind.library.cv.quality --cov-report=term-missing

# Verify re-export
python -c "from docmind.library.cv import assess_quality; print('OK')"

# Lint
ruff check backend/src/docmind/library/cv/quality.py
```
