# Issue #6: CV Preprocessing — PDF to Page Images and Image Normalization

## Summary

Implement the CV preprocessing module that converts PDF files to page images using PyMuPDF (fitz), loads raw image bytes into OpenCV arrays, normalizes images to a consistent BGR uint8 format with bounded dimensions, and dispatches by file type. All functions are pure (no side effects, no I/O beyond decoding bytes in memory). This is the entry point of the CV pipeline — all downstream modules (deskew, quality, VLM providers) depend on its output format.

## Context

- **Phase**: 2 — CV + VLM Providers
- **Priority**: P0
- **Labels**: `phase-2-cv-vlm`, `backend`, `tdd`, `priority-p0`
- **Dependencies**: None
- **Branch**: `feat/6-cv-preprocessing`
- **Estimated scope**: M

## Specs to Read

- `specs/backend/cv.md` — full section on `library/cv/preprocessing.py`, pipeline overview, preprocessing rules
- `specs/system.md` — file layout, Python package root conventions
- `specs/conventions/python-conventions.md` — PEP 8, type hints, naming
- `specs/conventions/python-module-structure.md` — library layer rules
- `specs/conventions/testing.md` — test structure, TDD process

## Current State (Scaffold)

The scaffold is already fully implemented with working logic. The file at `backend/src/docmind/library/cv/preprocessing.py` contains:

```python
"""
docmind/library/cv/preprocessing.py

PDF-to-image conversion and image normalization.
"""
import logging

import cv2
import fitz  # PyMuPDF
import numpy as np

logger = logging.getLogger(__name__)

MAX_DIMENSION = 4096
TARGET_DPI = 300
SUPPORTED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "webp"}


def convert_pdf_to_images(pdf_bytes: bytes, dpi: int = TARGET_DPI) -> list[np.ndarray]:
    if not pdf_bytes:
        raise ValueError("PDF bytes cannot be empty")
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    images: list[np.ndarray] = []
    zoom = dpi / 72.0
    matrix = fitz.Matrix(zoom, zoom)
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        pix = page.get_pixmap(matrix=matrix, alpha=False)
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        bgr_image = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
        images.append(bgr_image)
    doc.close()
    return images


def load_image(image_bytes: bytes) -> np.ndarray:
    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Failed to decode image from bytes")
    return image


def normalize_image(image: np.ndarray, max_dimension: int = MAX_DIMENSION) -> np.ndarray:
    if len(image.shape) == 2:
        result = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        result = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        result = image.copy()
    if result.dtype != np.uint8:
        result = (result * 255).clip(0, 255).astype(np.uint8)
    h, w = result.shape[:2]
    if max(h, w) > max_dimension:
        scale = max_dimension / max(h, w)
        new_w = max(int(w * scale), 100)
        new_h = max(int(h * scale), 100)
        result = cv2.resize(result, (new_w, new_h), interpolation=cv2.INTER_AREA)
    return result


def convert_to_page_images(file_bytes: bytes, file_type: str) -> list[np.ndarray]:
    file_type = file_type.lower().strip(".")
    if file_type not in SUPPORTED_EXTENSIONS:
        raise ValueError(f"Unsupported file type: {file_type}")
    if file_type == "pdf":
        raw_images = convert_pdf_to_images(file_bytes)
    else:
        raw_images = [load_image(file_bytes)]
    normalized = [normalize_image(img) for img in raw_images]
    logger.info("Preprocessed %d page(s), file_type=%s", len(normalized), file_type)
    return normalized
```

The `__init__.py` re-exports:

```python
from .preprocessing import convert_to_page_images
```

The test directory `backend/tests/unit/library/cv/` exists but contains no test files.

## Requirements

### Functional

1. `convert_pdf_to_images(pdf_bytes, dpi=300)` must render each page of a PDF into a BGR uint8 ndarray at the given DPI
2. `convert_pdf_to_images` must raise `ValueError` for empty bytes
3. `convert_pdf_to_images` must return images in page order (index 0 = page 1)
4. `load_image(image_bytes)` must decode PNG, JPG, TIFF, WebP bytes into BGR uint8 ndarray
5. `load_image` must raise `ValueError` for invalid/corrupt image bytes
6. `normalize_image(image, max_dimension=4096)` must convert grayscale to BGR
7. `normalize_image` must convert BGRA (4-channel) to BGR
8. `normalize_image` must convert non-uint8 dtypes to uint8
9. `normalize_image` must scale down images exceeding `max_dimension` while preserving aspect ratio
10. `normalize_image` must never modify the input array (returns new array)
11. `convert_to_page_images(file_bytes, file_type)` must dispatch to PDF or image loading based on `file_type`
12. `convert_to_page_images` must raise `ValueError` for unsupported file types
13. `convert_to_page_images` must normalize all output images
14. `convert_to_page_images` must handle file_type with or without leading dot (e.g., ".pdf" and "pdf")

### Non-Functional

- All functions are pure: no side effects, no filesystem I/O
- Output arrays are always BGR uint8
- Maximum dimension of 4096px prevents OOM on high-DPI scans
- Rendering at 300 DPI is the standard for OCR/VLM quality

## TDD Plan

### Step 1: Write Tests (RED)

**Test file**: `backend/tests/unit/library/cv/test_preprocessing.py`

```python
"""
Tests for docmind.library.cv.preprocessing module.

Tests PDF-to-image conversion, image loading, normalization, and
file-type dispatch. Uses synthetic test data — no external files needed.
"""
import cv2
import fitz  # PyMuPDF
import numpy as np
import pytest

from docmind.library.cv.preprocessing import (
    MAX_DIMENSION,
    SUPPORTED_EXTENSIONS,
    TARGET_DPI,
    convert_pdf_to_images,
    convert_to_page_images,
    load_image,
    normalize_image,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def synthetic_pdf_bytes() -> bytes:
    """Create a minimal 2-page PDF in memory using PyMuPDF."""
    doc = fitz.open()

    # Page 1: white page with "Page 1" text
    page1 = doc.new_page(width=612, height=792)  # US Letter
    page1.insert_text((72, 72), "Page 1", fontsize=24)

    # Page 2: white page with "Page 2" text
    page2 = doc.new_page(width=612, height=792)
    page2.insert_text((72, 72), "Page 2", fontsize=24)

    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def single_page_pdf_bytes() -> bytes:
    """Create a minimal 1-page PDF."""
    doc = fitz.open()
    page = doc.new_page(width=200, height=300)
    page.insert_text((10, 30), "Hello", fontsize=12)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes


@pytest.fixture
def synthetic_png_bytes() -> bytes:
    """Create a minimal PNG image in memory."""
    # Create a 200x300 BGR image with some content
    image = np.zeros((300, 200, 3), dtype=np.uint8)
    image[50:250, 50:150] = (255, 128, 64)  # colored rectangle
    _, buffer = cv2.imencode(".png", image)
    return buffer.tobytes()


@pytest.fixture
def synthetic_jpg_bytes() -> bytes:
    """Create a minimal JPEG image in memory."""
    image = np.ones((100, 150, 3), dtype=np.uint8) * 200
    _, buffer = cv2.imencode(".jpg", image)
    return buffer.tobytes()


@pytest.fixture
def large_image() -> np.ndarray:
    """Create an image exceeding MAX_DIMENSION."""
    return np.zeros((5000, 6000, 3), dtype=np.uint8)


@pytest.fixture
def grayscale_image() -> np.ndarray:
    """Create a 2D grayscale image."""
    return np.ones((200, 300), dtype=np.uint8) * 128


@pytest.fixture
def bgra_image() -> np.ndarray:
    """Create a 4-channel BGRA image."""
    return np.ones((200, 300, 4), dtype=np.uint8) * 100


@pytest.fixture
def float_image() -> np.ndarray:
    """Create a float64 image with values in [0, 1]."""
    return np.random.rand(200, 300, 3).astype(np.float64)


# ---------------------------------------------------------------------------
# convert_pdf_to_images
# ---------------------------------------------------------------------------

class TestConvertPdfToImages:
    """Tests for convert_pdf_to_images function."""

    def test_returns_list_of_ndarrays(self, synthetic_pdf_bytes: bytes) -> None:
        images = convert_pdf_to_images(synthetic_pdf_bytes)
        assert isinstance(images, list)
        assert len(images) == 2
        for img in images:
            assert isinstance(img, np.ndarray)

    def test_images_are_bgr_uint8(self, synthetic_pdf_bytes: bytes) -> None:
        images = convert_pdf_to_images(synthetic_pdf_bytes)
        for img in images:
            assert img.dtype == np.uint8
            assert len(img.shape) == 3
            assert img.shape[2] == 3  # BGR = 3 channels

    def test_page_count_matches_pdf(self, synthetic_pdf_bytes: bytes) -> None:
        images = convert_pdf_to_images(synthetic_pdf_bytes)
        assert len(images) == 2

    def test_single_page_pdf(self, single_page_pdf_bytes: bytes) -> None:
        images = convert_pdf_to_images(single_page_pdf_bytes)
        assert len(images) == 1

    def test_custom_dpi(self, single_page_pdf_bytes: bytes) -> None:
        images_low = convert_pdf_to_images(single_page_pdf_bytes, dpi=72)
        images_high = convert_pdf_to_images(single_page_pdf_bytes, dpi=300)
        # Higher DPI should produce larger images
        assert images_high[0].shape[0] > images_low[0].shape[0]
        assert images_high[0].shape[1] > images_low[0].shape[1]

    def test_raises_on_empty_bytes(self) -> None:
        with pytest.raises(ValueError, match="PDF bytes cannot be empty"):
            convert_pdf_to_images(b"")

    def test_raises_on_invalid_pdf(self) -> None:
        with pytest.raises(Exception):  # fitz raises RuntimeError for invalid PDFs
            convert_pdf_to_images(b"not a pdf file")

    def test_default_dpi_is_300(self, single_page_pdf_bytes: bytes) -> None:
        """Verify the default DPI produces images at 300 DPI resolution."""
        images = convert_pdf_to_images(single_page_pdf_bytes)
        # A 200x300 pt page at 300 DPI should be roughly 833x1250 pixels
        # (200 * 300/72 = 833, 300 * 300/72 = 1250)
        h, w = images[0].shape[:2]
        expected_w = int(200 * 300 / 72)
        expected_h = int(300 * 300 / 72)
        assert abs(w - expected_w) <= 2  # allow small rounding
        assert abs(h - expected_h) <= 2


# ---------------------------------------------------------------------------
# load_image
# ---------------------------------------------------------------------------

class TestLoadImage:
    """Tests for load_image function."""

    def test_loads_png(self, synthetic_png_bytes: bytes) -> None:
        image = load_image(synthetic_png_bytes)
        assert isinstance(image, np.ndarray)
        assert image.dtype == np.uint8
        assert len(image.shape) == 3
        assert image.shape[2] == 3

    def test_loads_jpg(self, synthetic_jpg_bytes: bytes) -> None:
        image = load_image(synthetic_jpg_bytes)
        assert isinstance(image, np.ndarray)
        assert image.dtype == np.uint8

    def test_preserves_dimensions(self, synthetic_png_bytes: bytes) -> None:
        image = load_image(synthetic_png_bytes)
        assert image.shape[0] == 300  # height
        assert image.shape[1] == 200  # width

    def test_raises_on_invalid_bytes(self) -> None:
        with pytest.raises(ValueError, match="Failed to decode image"):
            load_image(b"not an image")

    def test_raises_on_empty_bytes(self) -> None:
        with pytest.raises((ValueError, Exception)):
            load_image(b"")


# ---------------------------------------------------------------------------
# normalize_image
# ---------------------------------------------------------------------------

class TestNormalizeImage:
    """Tests for normalize_image function."""

    def test_grayscale_to_bgr(self, grayscale_image: np.ndarray) -> None:
        result = normalize_image(grayscale_image)
        assert len(result.shape) == 3
        assert result.shape[2] == 3
        assert result.dtype == np.uint8

    def test_bgra_to_bgr(self, bgra_image: np.ndarray) -> None:
        result = normalize_image(bgra_image)
        assert len(result.shape) == 3
        assert result.shape[2] == 3
        assert result.dtype == np.uint8

    def test_float_to_uint8(self, float_image: np.ndarray) -> None:
        result = normalize_image(float_image)
        assert result.dtype == np.uint8
        assert result.max() <= 255
        assert result.min() >= 0

    def test_scales_down_large_image(self, large_image: np.ndarray) -> None:
        result = normalize_image(large_image)
        h, w = result.shape[:2]
        assert max(h, w) <= MAX_DIMENSION

    def test_preserves_aspect_ratio(self, large_image: np.ndarray) -> None:
        original_ratio = large_image.shape[1] / large_image.shape[0]  # w/h
        result = normalize_image(large_image)
        result_ratio = result.shape[1] / result.shape[0]
        assert abs(original_ratio - result_ratio) < 0.05

    def test_does_not_scale_small_image(self) -> None:
        small = np.zeros((100, 100, 3), dtype=np.uint8)
        result = normalize_image(small)
        assert result.shape[:2] == (100, 100)

    def test_does_not_mutate_input(self) -> None:
        original = np.ones((200, 300, 3), dtype=np.uint8) * 50
        original_copy = original.copy()
        _ = normalize_image(original)
        np.testing.assert_array_equal(original, original_copy)

    def test_custom_max_dimension(self) -> None:
        big = np.zeros((2000, 3000, 3), dtype=np.uint8)
        result = normalize_image(big, max_dimension=1000)
        assert max(result.shape[:2]) <= 1000

    def test_already_bgr_uint8_returns_copy(self) -> None:
        original = np.zeros((100, 100, 3), dtype=np.uint8)
        result = normalize_image(original)
        assert result is not original  # must be a copy
        np.testing.assert_array_equal(result, original)


# ---------------------------------------------------------------------------
# convert_to_page_images
# ---------------------------------------------------------------------------

class TestConvertToPageImages:
    """Tests for convert_to_page_images dispatch function."""

    def test_dispatches_pdf(self, synthetic_pdf_bytes: bytes) -> None:
        images = convert_to_page_images(synthetic_pdf_bytes, "pdf")
        assert len(images) == 2
        for img in images:
            assert img.dtype == np.uint8
            assert len(img.shape) == 3

    def test_dispatches_png(self, synthetic_png_bytes: bytes) -> None:
        images = convert_to_page_images(synthetic_png_bytes, "png")
        assert len(images) == 1
        assert images[0].dtype == np.uint8

    def test_dispatches_jpg(self, synthetic_jpg_bytes: bytes) -> None:
        images = convert_to_page_images(synthetic_jpg_bytes, "jpg")
        assert len(images) == 1

    def test_dispatches_jpeg(self, synthetic_jpg_bytes: bytes) -> None:
        images = convert_to_page_images(synthetic_jpg_bytes, "jpeg")
        assert len(images) == 1

    def test_handles_dotted_file_type(self, synthetic_png_bytes: bytes) -> None:
        """File type with leading dot should be stripped."""
        images = convert_to_page_images(synthetic_png_bytes, ".png")
        assert len(images) == 1

    def test_handles_uppercase_file_type(self, synthetic_png_bytes: bytes) -> None:
        images = convert_to_page_images(synthetic_png_bytes, "PNG")
        assert len(images) == 1

    def test_raises_on_unsupported_type(self) -> None:
        with pytest.raises(ValueError, match="Unsupported file type"):
            convert_to_page_images(b"data", "bmp")

    def test_output_is_normalized(self, synthetic_pdf_bytes: bytes) -> None:
        """All output images should be BGR uint8 and within MAX_DIMENSION."""
        images = convert_to_page_images(synthetic_pdf_bytes, "pdf")
        for img in images:
            assert img.dtype == np.uint8
            assert len(img.shape) == 3
            assert img.shape[2] == 3
            assert max(img.shape[:2]) <= MAX_DIMENSION

    @pytest.mark.parametrize("ext", ["pdf", "png", "jpg", "jpeg", "tiff", "webp"])
    def test_supported_extensions_constant(self, ext: str) -> None:
        """All documented extensions should be in SUPPORTED_EXTENSIONS."""
        assert ext in SUPPORTED_EXTENSIONS


# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

class TestConstants:
    """Verify module-level constants match spec."""

    def test_max_dimension(self) -> None:
        assert MAX_DIMENSION == 4096

    def test_target_dpi(self) -> None:
        assert TARGET_DPI == 300

    def test_supported_extensions(self) -> None:
        assert SUPPORTED_EXTENSIONS == {"pdf", "png", "jpg", "jpeg", "tiff", "webp"}
```

### Step 2: Implement (GREEN)

**Files to modify**:
- `backend/src/docmind/library/cv/preprocessing.py` — The scaffold already contains the full implementation matching the spec. Verify it passes all tests.

**Implementation guidance**:

The current scaffold code already implements the spec. The main work for this issue is:

1. **Add docstrings**: The scaffold has minimal docstrings. Add the full docstrings from `specs/backend/cv.md` to each function.
2. **Add logging**: Add `logger.debug()` calls for page rendering as specified in the spec.
3. **Verify edge cases**: Ensure empty bytes, invalid PDFs, and invalid images all raise `ValueError` as specified.
4. **Confirm the `__init__.py` re-export** works: `from docmind.library.cv import convert_to_page_images`.

Key patterns:
- Use `fitz.open(stream=pdf_bytes, filetype="pdf")` for in-memory PDF loading
- Use `cv2.imdecode` for image byte decoding (handles PNG, JPG, TIFF, WebP)
- Use `cv2.cvtColor` for color space conversions
- Use `cv2.resize` with `INTER_AREA` for downscaling (best quality for shrinking)
- Always `doc.close()` after PDF processing

### Step 3: Refactor (IMPROVE)

- Add full docstrings from the spec to all functions
- Ensure debug-level logging for per-page render details
- Ensure info-level logging for summary (page count)
- Verify no type: ignore comments are needed (all types should be clean)
- Consider adding a `try/finally` around `doc.close()` for safety

## Acceptance Criteria

- [ ] `convert_pdf_to_images` renders multi-page PDFs correctly at 300 DPI
- [ ] `convert_pdf_to_images` raises `ValueError` on empty bytes
- [ ] `load_image` decodes PNG and JPG bytes correctly
- [ ] `load_image` raises `ValueError` on invalid bytes
- [ ] `normalize_image` converts grayscale, BGRA, and float images to BGR uint8
- [ ] `normalize_image` scales down images exceeding MAX_DIMENSION
- [ ] `normalize_image` preserves aspect ratio when scaling
- [ ] `normalize_image` never mutates the input array
- [ ] `convert_to_page_images` dispatches PDF vs image correctly
- [ ] `convert_to_page_images` handles file_type with/without dots, upper/lowercase
- [ ] `convert_to_page_images` raises `ValueError` on unsupported types
- [ ] All tests pass with `pytest backend/tests/unit/library/cv/test_preprocessing.py -v`
- [ ] Re-export works: `from docmind.library.cv import convert_to_page_images`

## Files Changed

| File | Action | What |
|------|--------|------|
| `backend/tests/unit/library/cv/__init__.py` | Create | Empty `__init__.py` for test package |
| `backend/tests/unit/library/cv/test_preprocessing.py` | Create | Unit tests for preprocessing module |
| `backend/src/docmind/library/cv/preprocessing.py` | Modify | Add full docstrings and logging from spec |

## Verification

```bash
# Run the tests
cd /workspace/company/nunenuh/docmind-vlm
python -m pytest backend/tests/unit/library/cv/test_preprocessing.py -v

# Run with coverage
python -m pytest backend/tests/unit/library/cv/test_preprocessing.py -v --cov=docmind.library.cv.preprocessing --cov-report=term-missing

# Verify re-export
python -c "from docmind.library.cv import convert_to_page_images; print('OK')"

# Lint
ruff check backend/src/docmind/library/cv/preprocessing.py
```
