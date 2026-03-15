"""
docmind/library/cv/deskew.py

Document skew detection and correction using Hough line transform.
All functions are pure: take ndarray, return ndarray. Never mutate the input.
"""
import cv2
import numpy as np


def detect_skew(image: np.ndarray) -> float:
    """Detect document skew angle using Hough line transform."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)
    lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=100, minLineLength=100, maxLineGap=10)
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
    """Correct document skew by rotating the image."""
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
    corrected = cv2.warpAffine(image, matrix, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return corrected


def detect_and_correct(image: np.ndarray, threshold: float = 2.0) -> tuple[np.ndarray, float]:
    """Detect and correct skew if angle exceeds threshold."""
    angle = detect_skew(image)
    if abs(angle) < threshold:
        return image, angle
    corrected = correct_skew(image, angle)
    return corrected, angle
