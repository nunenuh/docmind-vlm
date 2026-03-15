# Backend Spec: Classical CV Library

Files: `backend/src/docmind/library/cv/deskew.py`, `backend/src/docmind/library/cv/quality.py`, `backend/src/docmind/library/cv/preprocessing.py`

See also: [[projects/docmind-vlm/specs/backend/pipeline-processing]]

---

## Responsibility

| File | Does |
|------|------|
| `docmind/library/cv/__init__.py` | Re-exports: `deskew_image`, `assess_quality`, `convert_to_page_images` |
| `docmind/library/cv/preprocessing.py` | Convert PDF pages to images, normalize image format/size/color |
| `docmind/library/cv/deskew.py` | Detect document skew angle via Hough transform, correct if above threshold |
| `docmind/library/cv/quality.py` | Assess image quality (blur, noise, contrast) per region, produce quality map |

The CV library is **pure computation**: all functions take `np.ndarray`, return `np.ndarray` or dataclasses. No side effects, no I/O, no mutation of input arrays. Lives under `library/` because it is reusable logic NOT tied to modules or DB.

---

## Imports

```python
# From pipeline nodes or other library code:
from docmind.library.cv import deskew_image, assess_quality, convert_to_page_images

# Or import specific modules:
from docmind.library.cv.deskew import detect_and_correct
from docmind.library.cv.quality import assess_regions, RegionQuality
from docmind.library.cv.preprocessing import convert_to_page_images, normalize_image
```

---

## Pipeline Overview

```
PDF/image input
    |
    v  library/cv/preprocessing.py
convert_to_page_images() -> list[np.ndarray]
normalize_image() -> np.ndarray (BGR, uint8, bounded dimensions)
    |
    v  library/cv/deskew.py
detect_and_correct() -> (corrected_image, skew_angle)
    |
    v  library/cv/quality.py
assess_regions() -> dict[tuple[int,int], RegionQuality]
    |
    v
quality_map + corrected images -> passed to pipeline extract node
```

---

## `library/cv/deskew.py`

```python
"""
docmind/library/cv/deskew.py

Document skew detection and correction using Hough line transform.

All functions are pure: take ndarray, return ndarray. Never mutate the input.
"""
import cv2
import numpy as np


def detect_skew(image: np.ndarray) -> float:
    """
    Detect document skew angle using Hough line transform.

    Converts to grayscale, runs Canny edge detection, then HoughLinesP
    to find dominant line angles. Returns the median angle.

    Args:
        image: Input image as BGR or grayscale ndarray.

    Returns:
        Skew angle in degrees. Positive = clockwise rotation needed.
        Returns 0.0 if no lines detected.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=100,
        minLineLength=100,
        maxLineGap=10,
    )

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
    """
    Correct document skew by rotating the image.

    Uses cubic interpolation and replicates border pixels to avoid
    black edges on the rotated result.

    Args:
        image: Input image (any channel count).
        angle: Rotation angle in degrees (from detect_skew).

    Returns:
        New rotated image. Original is not modified.
    """
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    corrected = cv2.warpAffine(
        image,
        matrix,
        (w, h),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return corrected


def detect_and_correct(
    image: np.ndarray,
    threshold: float = 2.0,
) -> tuple[np.ndarray, float]:
    """
    Detect and correct skew if angle exceeds threshold.

    This is the main entry point for the deskew module. If the detected
    skew angle is below the threshold, the original image is returned
    unchanged (no unnecessary resampling).

    Args:
        image: Input document image.
        threshold: Minimum angle (degrees) to trigger correction. Default 2.0.

    Returns:
        Tuple of (output_image, detected_angle).
        output_image is either the original (if below threshold) or corrected.
    """
    angle = detect_skew(image)

    if abs(angle) < threshold:
        return image, angle

    corrected = correct_skew(image, angle)
    return corrected, angle
```

**Deskew Rules:**
- `detect_skew` returns 0.0 when no lines are found — never raise on empty detection
- `correct_skew` uses `BORDER_REPLICATE` to avoid black edges
- `detect_and_correct` skips correction below threshold to avoid unnecessary interpolation artifacts
- Threshold default is 2.0 degrees — configurable per call

---

## `library/cv/quality.py`

```python
"""
docmind/library/cv/quality.py

Image quality assessment per region.

Measures blur, noise, and contrast at a grid level so the pipeline
can weight VLM confidence by local image quality.
"""
import cv2
import numpy as np
from dataclasses import dataclass


@dataclass(frozen=True)
class RegionQuality:
    """
    Quality metrics for a single image region.

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
    """
    Assess image sharpness using Laplacian variance.

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
    """
    Assess image noise using median filter deviation.

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
    """
    Assess contrast using histogram spread (standard deviation of pixel intensities).

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
    """
    Compute normalized overall quality score from individual metrics.

    Uses sigmoid-like normalization to map each metric to [0, 1],
    then weights them: blur 40%, noise 30%, contrast 30%.

    Args:
        blur: Laplacian variance (higher = better).
        noise: Median filter deviation (lower = better).
        contrast: Histogram std dev (higher = better).

    Returns:
        Overall quality score in [0.0, 1.0].
    """
    # Normalize each metric to [0, 1] using tanh-based scaling
    blur_norm = min(blur / 200.0, 1.0)
    noise_norm = max(1.0 - (noise / 30.0), 0.0)
    contrast_norm = min(contrast / 60.0, 1.0)

    overall = (0.4 * blur_norm) + (0.3 * noise_norm) + (0.3 * contrast_norm)
    return round(max(0.0, min(1.0, overall)), 4)


def assess_region(region: np.ndarray) -> RegionQuality:
    """
    Assess quality of a single image region.

    Args:
        region: Grayscale image region (2D ndarray).

    Returns:
        RegionQuality with all metrics computed.
    """
    gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if len(region.shape) == 3 else region

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
    """
    Assess quality across a grid of image regions.

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

**Quality Rules:**
- `RegionQuality` is frozen (immutable) — never modify after creation
- `assess_blur` uses Laplacian variance — industry standard for blur detection
- `assess_noise` compares to median filter — robust against structured content
- `_compute_overall_score` weights: blur 40%, noise 30%, contrast 30%
- `assess_regions` handles non-uniform grid edges (last row/col may be larger)
- All functions accept both BGR and grayscale input — convert internally

---

## `library/cv/preprocessing.py`

```python
"""
docmind/library/cv/preprocessing.py

PDF-to-image conversion and image normalization.

Uses PyMuPDF (fitz) for PDF rendering. All output images are BGR uint8
with bounded dimensions for consistent downstream processing.
"""
import logging

import cv2
import fitz  # PyMuPDF
import numpy as np

logger = logging.getLogger(__name__)

MAX_DIMENSION = 4096  # Maximum width or height in pixels
TARGET_DPI = 300      # Rendering DPI for PDF pages
SUPPORTED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "webp"}


def convert_pdf_to_images(
    pdf_bytes: bytes,
    dpi: int = TARGET_DPI,
) -> list[np.ndarray]:
    """
    Convert a PDF file to a list of BGR images, one per page.

    Uses PyMuPDF to render each page at the specified DPI.
    Pages are rendered in order; the returned list index matches
    the 0-based page number.

    Args:
        pdf_bytes: Raw PDF file bytes.
        dpi: Rendering resolution. Default 300 DPI.

    Returns:
        List of BGR uint8 ndarrays, one per page.

    Raises:
        ValueError: If pdf_bytes is empty or invalid.
    """
    if not pdf_bytes:
        raise ValueError("PDF bytes cannot be empty")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: list[np.ndarray] = []

    zoom = dpi / 72.0  # fitz default is 72 DPI
    matrix = fitz.Matrix(zoom, zoom)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=matrix, alpha=False)

        # Convert fitz pixmap to numpy array (RGB)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3
        )

        # Convert RGB to BGR for OpenCV compatibility
        bgr_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        images.append(bgr_image)

        logger.debug(
            "Rendered page %d: %dx%d at %d DPI",
            page_num + 1,
            pix.width,
            pix.height,
            dpi,
        )

    doc.close()
    return images


def load_image(image_bytes: bytes) -> np.ndarray:
    """
    Load an image from raw bytes.

    Args:
        image_bytes: Raw image file bytes (PNG, JPG, TIFF, WebP).

    Returns:
        BGR uint8 ndarray.

    Raises:
        ValueError: If the image cannot be decoded.
    """
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Failed to decode image from bytes")

    return image


def normalize_image(
    image: np.ndarray,
    max_dimension: int = MAX_DIMENSION,
) -> np.ndarray:
    """
    Normalize an image for consistent downstream processing.

    Operations performed:
    1. Convert to BGR uint8 if needed
    2. Scale down if either dimension exceeds max_dimension (preserve aspect ratio)
    3. Ensure minimum dimension of 100px

    Args:
        image: Input image (any channel count, any dtype).
        max_dimension: Maximum allowed width or height. Default 4096.

    Returns:
        Normalized BGR uint8 ndarray. Original is not modified.
    """
    # Ensure BGR uint8
    if len(image.shape) == 2:
        result = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        result = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        result = image.copy()

    if result.dtype != np.uint8:
        result = (result * 255).clip(0, 255).astype(np.uint8)

    # Scale down if too large
    h, w = result.shape[:2]
    if max(h, w) > max_dimension:
        scale = max_dimension / max(h, w)
        new_w = max(int(w * scale), 100)
        new_h = max(int(h * scale), 100)
        result = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_AREA)
        logger.debug("Scaled image from %dx%d to %dx%d", w, h, new_w, new_h)

    return result


def convert_to_page_images(
    file_bytes: bytes,
    file_type: str,
) -> list[np.ndarray]:
    """
    Convert any supported file to a list of normalized page images.

    This is the main entry point for the preprocessing module.
    PDFs produce multiple pages; single images produce a one-element list.

    Args:
        file_bytes: Raw file bytes.
        file_type: File extension without dot (e.g. "pdf", "png").

    Returns:
        List of normalized BGR uint8 ndarrays.

    Raises:
        ValueError: If file_type is unsupported or bytes are invalid.
    """
    file_type = file_type.lower().strip(".")

    if file_type not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {file_type}")

    if file_type == "pdf":
        raw_images = convert_pdf_to_images(file_bytes)
    else:
        raw_images = [load_image(file_bytes)]

    normalized = [normalize_image(img) for img in raw_images]
    logger.info(
        "Preprocessed %d page(s), file_type=%s",
        len(normalized),
        file_type,
    )
    return normalized
```

**Preprocessing Rules:**
- `convert_pdf_to_images` renders at 300 DPI — standard for OCR/VLM quality
- All output is BGR uint8 — OpenCV's native format
- `normalize_image` always returns a copy — never modifies the input
- Maximum dimension is 4096px — prevents memory issues with high-DPI scans
- `convert_to_page_images` is the main entry point — callers should not call individual functions directly
- PyMuPDF (`fitz`) is the only PDF dependency — no Poppler, no pdf2image

---

## `library/cv/__init__.py`

```python
"""
docmind/library/cv/__init__.py

Re-exports for convenient access to CV library functions.
"""
from .deskew import detect_and_correct as deskew_image
from .quality import assess_regions as assess_quality
from .preprocessing import convert_to_page_images
```

---

## Rules

- **All CV functions are pure**: take `np.ndarray`, return `np.ndarray` or dataclass. No side effects, no file I/O, no database calls.
- **Never mutate input arrays**: always copy or create new arrays.
- **BGR uint8 is the standard format**: all functions normalize to this internally.
- **Frozen dataclasses only**: `RegionQuality` is `frozen=True` — no mutation after creation.
- **Fail fast on invalid input**: raise `ValueError` with clear messages for empty bytes, unsupported formats, etc.
- **Log at debug level**: preprocessing details are debug, summary counts are info.
