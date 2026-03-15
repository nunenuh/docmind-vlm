"""
docmind/library/cv/__init__.py

Re-exports for convenient access to CV library functions.
"""

from .deskew import detect_and_correct as deskew_image
from .preprocessing import convert_to_page_images
from .quality import assess_regions as assess_quality

__all__ = ["deskew_image", "convert_to_page_images", "assess_quality"]
