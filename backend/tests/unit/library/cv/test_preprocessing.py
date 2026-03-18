"""
Tests for docmind.library.cv.preprocessing module.

Tests PDF-to-image conversion, image loading, normalization, and
file-type dispatch. Uses synthetic test data — no external files needed.
"""

from unittest.mock import MagicMock, patch

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
    page1 = doc.new_page(width=612, height=792)
    page1.insert_text((72, 72), "Page 1", fontsize=24)
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
    image = np.zeros((300, 200, 3), dtype=np.uint8)
    image[50:250, 50:150] = (255, 128, 64)
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
            assert img.shape[2] == 3

    def test_page_count_matches_pdf(self, synthetic_pdf_bytes: bytes) -> None:
        images = convert_pdf_to_images(synthetic_pdf_bytes)
        assert len(images) == 2

    def test_single_page_pdf(self, single_page_pdf_bytes: bytes) -> None:
        images = convert_pdf_to_images(single_page_pdf_bytes)
        assert len(images) == 1

    def test_custom_dpi(self, single_page_pdf_bytes: bytes) -> None:
        images_low = convert_pdf_to_images(single_page_pdf_bytes, dpi=72)
        images_high = convert_pdf_to_images(single_page_pdf_bytes, dpi=300)
        assert images_high[0].shape[0] > images_low[0].shape[0]
        assert images_high[0].shape[1] > images_low[0].shape[1]

    def test_raises_on_empty_bytes(self) -> None:
        with pytest.raises(ValueError, match="PDF bytes cannot be empty"):
            convert_pdf_to_images(b"")

    def test_raises_on_invalid_pdf(self) -> None:
        with pytest.raises(Exception):
            convert_pdf_to_images(b"not a pdf file")

    @patch("docmind.library.cv.preprocessing.fitz.open")
    def test_raises_on_zero_page_pdf(self, mock_fitz_open: MagicMock) -> None:
        """A PDF with zero pages should raise ValueError."""
        mock_doc = MagicMock()
        mock_doc.__len__ = MagicMock(return_value=0)
        mock_fitz_open.return_value = mock_doc
        with pytest.raises(ValueError, match="no pages"):
            convert_pdf_to_images(b"%PDF-1.4 empty")

    def test_default_dpi_is_300(self, single_page_pdf_bytes: bytes) -> None:
        """Verify the default DPI produces images at 300 DPI resolution."""
        images = convert_pdf_to_images(single_page_pdf_bytes)
        h, w = images[0].shape[:2]
        expected_w = int(200 * 300 / 72)
        expected_h = int(300 * 300 / 72)
        assert abs(w - expected_w) <= 2
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
        assert image.shape[0] == 300
        assert image.shape[1] == 200

    def test_raises_on_invalid_bytes(self) -> None:
        with pytest.raises(ValueError, match="Failed to decode image"):
            load_image(b"not an image")

    def test_raises_on_empty_bytes(self) -> None:
        with pytest.raises(ValueError, match="Image bytes cannot be empty"):
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
        original_ratio = large_image.shape[1] / large_image.shape[0]
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

    def test_float_in_0_255_range_not_remapped(self) -> None:
        """Float image with values in [0, 255] should not be multiplied by 255."""
        img = np.full((100, 100, 3), 200.0, dtype=np.float32)
        result = normalize_image(img)
        assert result.dtype == np.uint8
        assert result.mean() == pytest.approx(200.0, abs=1.0)

    def test_already_bgr_uint8_returns_copy(self) -> None:
        original = np.zeros((100, 100, 3), dtype=np.uint8)
        result = normalize_image(original)
        assert result is not original
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
