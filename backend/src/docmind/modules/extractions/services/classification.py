"""Classification service — auto-detect document type using VLM."""

import cv2
import numpy as np

from docmind.core.config import get_settings
from docmind.core.logging import get_logger
from docmind.library.providers.factory import UserProviderOverride, get_vlm_provider

logger = get_logger(__name__)


class ClassificationService:
    """Auto-detect document type using VLM."""

    def __init__(self, settings=None) -> None:
        self._settings = settings or get_settings()

    async def classify(
        self,
        file_bytes: bytes,
        file_type: str,
        template_types: list[str],
        override: UserProviderOverride | None = None,
    ) -> str | None:
        """Classify a document image to detect its type.

        Args:
            file_bytes: Raw file bytes.
            file_type: File extension (pdf, png, etc.).
            template_types: Available template type strings to match against.

        Returns:
            Detected template type string, or None if undetectable.
        """
        image = self._bytes_to_image(file_bytes, file_type)
        if image is None:
            return None

        types_str = ", ".join(template_types)
        provider = get_vlm_provider(override=override)
        prompt = (
            f"What type of document is this? Choose from: {types_str}, or 'unknown' if none match. "
            "Return ONLY the type name, nothing else."
        )

        response = await provider.extract(images=[image], prompt=prompt)
        content = (
            response.get("content", "").strip().lower().replace('"', "").replace("'", "")
        )

        for t_type in template_types:
            if t_type in content:
                return t_type

        return content if content in template_types else None

    def _bytes_to_image(self, file_bytes: bytes, file_type: str) -> np.ndarray | None:
        """Convert file bytes to OpenCV image."""
        if file_type == "pdf":
            try:
                import fitz

                doc = fitz.open(stream=file_bytes, filetype="pdf")
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                arr = np.frombuffer(pix.samples, np.uint8).reshape(pix.h, pix.w, pix.n)
                image = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR) if pix.n == 3 else arr
                doc.close()
                return image
            except Exception as e:
                logger.warning("pdf_to_image_failed: %s", e)
                return None
        else:
            nparr = np.frombuffer(file_bytes, np.uint8)
            return cv2.imdecode(nparr, cv2.IMREAD_COLOR)
