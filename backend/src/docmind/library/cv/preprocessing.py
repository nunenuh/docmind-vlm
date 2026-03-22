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

from docmind.core.config import get_settings

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "tiff", "webp"}


def convert_pdf_to_images(
    pdf_bytes: bytes,
    dpi: int | None = None,
) -> list[np.ndarray]:
    """Convert a PDF file to a list of BGR images, one per page.

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

    if dpi is None:
        dpi = get_settings().CV_TARGET_DPI

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        if len(doc) == 0:
            raise ValueError("PDF contains no pages")

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
    finally:
        doc.close()

    return images


def load_image(image_bytes: bytes) -> np.ndarray:
    """Load an image from raw bytes.

    Args:
        image_bytes: Raw image file bytes (PNG, JPG, TIFF, WebP).

    Returns:
        BGR uint8 ndarray.

    Raises:
        ValueError: If the image cannot be decoded.
    """
    if not image_bytes:
        raise ValueError("Image bytes cannot be empty")

    arr = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(arr, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError("Failed to decode image from bytes")

    return image


def normalize_image(
    image: np.ndarray,
    max_dimension: int | None = None,
) -> np.ndarray:
    """Normalize an image for consistent downstream processing.

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
    if max_dimension is None:
        max_dimension = get_settings().CV_MAX_DIMENSION

    # Ensure BGR uint8
    if len(image.shape) == 2:
        result = cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    elif image.shape[2] == 4:
        result = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    else:
        result = image.copy()

    if result.dtype != np.uint8:
        if result.max() > 1.0:
            result = result.clip(0, 255).astype(np.uint8)
        else:
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
    """Convert any supported file to a list of normalized page images.

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
