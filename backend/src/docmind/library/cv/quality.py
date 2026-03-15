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
