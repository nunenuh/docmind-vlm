"""
docmind/library/cv/quality.py

Image quality assessment per region.

Measures blur, noise, and contrast at a grid level so the pipeline
can weight VLM confidence by local image quality.
"""

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass(frozen=True)
class RegionQuality:
    """Quality metrics for a single image region.

    Attributes:
        blur_score: Laplacian variance. Higher = sharper. Threshold ~100.
        noise_score: Deviation from median filter. Lower = cleaner. Threshold ~10.
        contrast_score: Histogram spread (std dev of intensities). Higher = better. Threshold ~40.
        overall_score: Weighted combination normalized to [0.0, 1.0].
    """

    blur_score: float
    noise_score: float
    contrast_score: float
    overall_score: float


def assess_blur(region: np.ndarray) -> float:
    """Assess image sharpness using Laplacian variance.

    The Laplacian highlights edges; its variance measures how much
    edge content exists. Low variance = blurry.

    Args:
        region: Grayscale image region.

    Returns:
        Laplacian variance (higher = sharper). Typical range: 0-500+.
    """
    laplacian = cv2.Laplacian(region, cv2.CV_64F)
    return float(np.var(laplacian))


def assess_noise(region: np.ndarray) -> float:
    """Assess image noise using median filter deviation.

    Compares the original region to a median-filtered version.
    The mean absolute difference indicates noise level.

    Args:
        region: Grayscale image region.

    Returns:
        Mean absolute deviation from median filter. Lower = cleaner.
        Typical range: 0-30+.
    """
    median_filtered = cv2.medianBlur(region, 5)
    diff = np.abs(region.astype(np.float64) - median_filtered.astype(np.float64))
    return float(np.mean(diff))


def assess_contrast(region: np.ndarray) -> float:
    """Assess contrast using histogram spread (standard deviation of pixel intensities).

    Low std dev means the image is washed out or uniformly colored.

    Args:
        region: Grayscale image region.

    Returns:
        Standard deviation of pixel intensities. Higher = better contrast.
        Typical range: 0-80+.
    """
    return float(np.std(region.astype(np.float64)))


def _compute_overall_score(
    blur: float,
    noise: float,
    contrast: float,
) -> float:
    """Compute normalized overall quality score from individual metrics.

    Uses linear normalization to map each metric to [0, 1],
    then weights them: blur 40%, noise 30%, contrast 30%.

    Args:
        blur: Laplacian variance (higher = better).
        noise: Median filter deviation (lower = better).
        contrast: Histogram std dev (higher = better).

    Returns:
        Overall quality score in [0.0, 1.0].
    """
    blur_norm = min(blur / 200.0, 1.0)
    noise_norm = max(1.0 - (noise / 30.0), 0.0)
    contrast_norm = min(contrast / 60.0, 1.0)

    overall = (0.4 * blur_norm) + (0.3 * noise_norm) + (0.3 * contrast_norm)
    return round(max(0.0, min(1.0, overall)), 4)


def assess_region(region: np.ndarray) -> RegionQuality:
    """Assess quality of a single image region.

    Args:
        region: Image region (BGR or grayscale ndarray).

    Returns:
        RegionQuality with all metrics computed.
    """
    gray = (
        cv2.cvtColor(region, cv2.COLOR_BGR2GRAY)
        if len(region.shape) == 3
        else region
    )

    blur = assess_blur(gray)
    noise = assess_noise(gray)
    contrast = assess_contrast(gray)
    overall = _compute_overall_score(blur, noise, contrast)

    return RegionQuality(
        blur_score=round(blur, 2),
        noise_score=round(noise, 2),
        contrast_score=round(contrast, 2),
        overall_score=overall,
    )


def assess_regions(
    image: np.ndarray,
    grid_rows: int = 4,
    grid_cols: int = 4,
) -> dict[tuple[int, int], RegionQuality]:
    """Assess quality across a grid of image regions.

    Divides the image into a grid and computes quality metrics per cell.
    The pipeline uses this to weight VLM confidence by local image quality.

    Args:
        image: Full document image (BGR or grayscale).
        grid_rows: Number of rows in the grid. Default 4.
        grid_cols: Number of columns in the grid. Default 4.

    Returns:
        Dict mapping (row, col) grid coordinates to RegionQuality.
        Grid coordinates are 0-indexed.
    """
    gray = (
        cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        if len(image.shape) == 3
        else image
    )
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
