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
        img_array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
            pix.height, pix.width, 3
        )
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


def normalize_image(
    image: np.ndarray, max_dimension: int = MAX_DIMENSION
) -> np.ndarray:
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
