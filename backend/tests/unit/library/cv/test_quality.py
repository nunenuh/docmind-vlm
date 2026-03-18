"""
Tests for docmind.library.cv.quality module.

Tests blur, noise, and contrast assessment on synthetic images with
known characteristics. Verifies grid-based region quality mapping.
"""

import dataclasses

import cv2
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
    """Sharp grayscale image with strong edges."""
    image = np.zeros((200, 200), dtype=np.uint8)
    for i in range(0, 200, 20):
        cv2.line(image, (i, 0), (i, 199), 255, 1)
        cv2.line(image, (0, i), (199, i), 255, 1)
    return image


@pytest.fixture
def blurry_image(sharp_image: np.ndarray) -> np.ndarray:
    """Blurred version of sharp_image."""
    return cv2.GaussianBlur(sharp_image, (31, 31), 10)


@pytest.fixture
def clean_image() -> np.ndarray:
    """Clean gradient image — minimal noise."""
    return np.tile(np.arange(200, dtype=np.uint8), (200, 1))


@pytest.fixture
def noisy_image(clean_image: np.ndarray) -> np.ndarray:
    """Noisy version of clean_image with added Gaussian noise."""
    rng = np.random.default_rng(42)
    noise = rng.normal(0, 30, clean_image.shape).astype(np.float64)
    return np.clip(clean_image.astype(np.float64) + noise, 0, 255).astype(np.uint8)


@pytest.fixture
def high_contrast_image() -> np.ndarray:
    """Image with strong contrast (black and white halves)."""
    image = np.zeros((200, 200), dtype=np.uint8)
    image[:, 100:] = 255
    return image


@pytest.fixture
def low_contrast_image() -> np.ndarray:
    """Uniformly gray image — minimal contrast."""
    return np.ones((200, 200), dtype=np.uint8) * 128


@pytest.fixture
def bgr_test_image() -> np.ndarray:
    """BGR 3-channel test image for assess_region and assess_regions."""
    image = np.zeros((400, 400, 3), dtype=np.uint8)
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
        rq = RegionQuality(
            blur_score=100.0, noise_score=5.0,
            contrast_score=50.0, overall_score=0.8,
        )
        assert rq.blur_score == 100.0
        assert rq.noise_score == 5.0
        assert rq.contrast_score == 50.0
        assert rq.overall_score == 0.8

    def test_is_frozen(self) -> None:
        rq = RegionQuality(
            blur_score=100.0, noise_score=5.0,
            contrast_score=50.0, overall_score=0.8,
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            rq.blur_score = 200.0  # type: ignore[misc]

    def test_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(RegionQuality)

    def test_equality(self) -> None:
        rq1 = RegionQuality(
            blur_score=100.0, noise_score=5.0,
            contrast_score=50.0, overall_score=0.8,
        )
        rq2 = RegionQuality(
            blur_score=100.0, noise_score=5.0,
            contrast_score=50.0, overall_score=0.8,
        )
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
        assert isinstance(assess_blur(sharp_image), float)

    def test_sharp_higher_than_blurry(
        self, sharp_image: np.ndarray, blurry_image: np.ndarray
    ) -> None:
        """Sharp images should have higher Laplacian variance than blurry ones."""
        assert assess_blur(sharp_image) > assess_blur(blurry_image)

    def test_non_negative(self, sharp_image: np.ndarray) -> None:
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
        assert isinstance(assess_noise(clean_image), float)

    def test_noisy_higher_than_clean(
        self, clean_image: np.ndarray, noisy_image: np.ndarray
    ) -> None:
        """Noisy images should have higher median filter deviation."""
        assert assess_noise(noisy_image) > assess_noise(clean_image)

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
        assert isinstance(assess_contrast(high_contrast_image), float)

    def test_high_contrast_higher_score(
        self, high_contrast_image: np.ndarray, low_contrast_image: np.ndarray
    ) -> None:
        assert assess_contrast(high_contrast_image) > assess_contrast(low_contrast_image)

    def test_non_negative(self, high_contrast_image: np.ndarray) -> None:
        assert assess_contrast(high_contrast_image) >= 0.0

    def test_uniform_image_zero_contrast(self) -> None:
        uniform = np.ones((100, 100), dtype=np.uint8) * 128
        assert assess_contrast(uniform) == 0.0


# ---------------------------------------------------------------------------
# _compute_overall_score
# ---------------------------------------------------------------------------


class TestComputeOverallScore:
    """Tests for _compute_overall_score internal function."""

    def test_returns_float(self) -> None:
        assert isinstance(_compute_overall_score(100.0, 5.0, 50.0), float)

    def test_result_in_range(self) -> None:
        result = _compute_overall_score(100.0, 5.0, 50.0)
        assert 0.0 <= result <= 1.0

    def test_perfect_scores(self) -> None:
        assert _compute_overall_score(200.0, 0.0, 60.0) == 1.0

    def test_worst_scores(self) -> None:
        assert _compute_overall_score(0.0, 30.0, 0.0) == 0.0

    def test_weights_blur_40_noise_30_contrast_30(self) -> None:
        blur_only = _compute_overall_score(200.0, 30.0, 0.0)
        assert abs(blur_only - 0.4) < 0.001

        noise_only = _compute_overall_score(0.0, 0.0, 0.0)
        assert abs(noise_only - 0.3) < 0.001

        contrast_only = _compute_overall_score(0.0, 30.0, 60.0)
        assert abs(contrast_only - 0.3) < 0.001

    def test_clamps_to_range(self) -> None:
        assert _compute_overall_score(10000.0, 0.0, 10000.0) <= 1.0
        assert _compute_overall_score(0.0, 10000.0, 0.0) >= 0.0

    def test_rounded_to_four_decimals(self) -> None:
        result = _compute_overall_score(150.0, 10.0, 45.0)
        assert result == round(result, 4)


# ---------------------------------------------------------------------------
# assess_region
# ---------------------------------------------------------------------------


class TestAssessRegion:
    """Tests for assess_region function."""

    def test_returns_region_quality(self, sharp_image: np.ndarray) -> None:
        assert isinstance(assess_region(sharp_image), RegionQuality)

    def test_accepts_bgr_input(self, bgr_test_image: np.ndarray) -> None:
        region = bgr_test_image[50:150, 50:150]
        assert isinstance(assess_region(region), RegionQuality)

    def test_accepts_grayscale_input(self, sharp_image: np.ndarray) -> None:
        assert isinstance(assess_region(sharp_image), RegionQuality)

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
        assert assess_region(sharp_image).blur_score > assess_region(blurry_image).blur_score


# ---------------------------------------------------------------------------
# assess_regions
# ---------------------------------------------------------------------------


class TestAssessRegions:
    """Tests for assess_regions grid-based quality mapping."""

    def test_returns_dict(self, bgr_test_image: np.ndarray) -> None:
        assert isinstance(assess_regions(bgr_test_image), dict)

    def test_default_grid_4x4(self, bgr_test_image: np.ndarray) -> None:
        assert len(assess_regions(bgr_test_image)) == 16

    def test_keys_are_tuples(self, bgr_test_image: np.ndarray) -> None:
        for key in assess_regions(bgr_test_image):
            assert isinstance(key, tuple)
            assert len(key) == 2
            assert isinstance(key[0], int)
            assert isinstance(key[1], int)

    def test_values_are_region_quality(self, bgr_test_image: np.ndarray) -> None:
        for value in assess_regions(bgr_test_image).values():
            assert isinstance(value, RegionQuality)

    def test_grid_coordinates_zero_indexed(self, bgr_test_image: np.ndarray) -> None:
        for row, col in assess_regions(bgr_test_image, grid_rows=4, grid_cols=4):
            assert 0 <= row < 4
            assert 0 <= col < 4

    @pytest.mark.parametrize(
        "grid_rows,grid_cols,expected_count",
        [(1, 1, 1), (2, 2, 4), (3, 3, 9), (4, 4, 16), (2, 4, 8), (4, 2, 8)],
    )
    def test_custom_grid_sizes(
        self, large_bgr_image: np.ndarray,
        grid_rows: int, grid_cols: int, expected_count: int,
    ) -> None:
        assert len(assess_regions(large_bgr_image, grid_rows=grid_rows, grid_cols=grid_cols)) == expected_count

    def test_accepts_grayscale(self) -> None:
        gray = np.ones((400, 400), dtype=np.uint8) * 128
        assert len(assess_regions(gray, grid_rows=2, grid_cols=2)) == 4

    def test_all_keys_present(self, bgr_test_image: np.ndarray) -> None:
        result = assess_regions(bgr_test_image, grid_rows=3, grid_cols=3)
        expected_keys = {(r, c) for r in range(3) for c in range(3)}
        assert set(result.keys()) == expected_keys

    def test_last_row_col_handles_remainder(self) -> None:
        image = np.ones((401, 401, 3), dtype=np.uint8) * 128
        assert len(assess_regions(image, grid_rows=4, grid_cols=4)) == 16


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
