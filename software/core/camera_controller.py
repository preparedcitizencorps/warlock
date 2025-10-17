#!/usr/bin/env python3
"""Thread-safe camera controller wrapper for OpenCV VideoCapture."""

import cv2
import threading
from typing import Optional, Dict, Tuple


class CameraController:
    """
    Thread-safe wrapper around OpenCV VideoCapture that exposes only safe camera operations.
    Prevents plugins from accidentally releasing the camera or calling destructive methods.
    """

    WHITELISTED_PROPERTIES = frozenset({
        cv2.CAP_PROP_EXPOSURE,
        cv2.CAP_PROP_GAIN,
        cv2.CAP_PROP_BRIGHTNESS,
        cv2.CAP_PROP_CONTRAST,
        cv2.CAP_PROP_SATURATION,
        cv2.CAP_PROP_AUTO_EXPOSURE,
        cv2.CAP_PROP_AUTO_WB,
        cv2.CAP_PROP_WB_TEMPERATURE,
        cv2.CAP_PROP_SHARPNESS,
        cv2.CAP_PROP_GAMMA,
        cv2.CAP_PROP_BACKLIGHT,
    })

    EXPOSURE_MIN = -13
    EXPOSURE_MAX = 0
    GAIN_MIN = 0
    GAIN_MAX = 100
    BRIGHTNESS_MIN = 0
    BRIGHTNESS_MAX = 255

    PROPERTY_RANGES: Dict[int, Tuple[float, float]] = {
        cv2.CAP_PROP_EXPOSURE: (EXPOSURE_MIN, EXPOSURE_MAX),
        cv2.CAP_PROP_GAIN: (GAIN_MIN, GAIN_MAX),
        cv2.CAP_PROP_BRIGHTNESS: (BRIGHTNESS_MIN, BRIGHTNESS_MAX),
    }

    def __init__(self, capture: cv2.VideoCapture):
        if capture is None:
            raise ValueError("VideoCapture cannot be None")
        if not hasattr(capture, 'isOpened'):
            raise ValueError("Invalid VideoCapture object: missing isOpened method")
        if not capture.isOpened():
            raise ValueError("VideoCapture is not opened")

        self._capture = capture
        self._lock = threading.Lock()

    def set_exposure(self, value: float) -> bool:
        """Set camera exposure with range validation."""
        if not self.EXPOSURE_MIN <= value <= self.EXPOSURE_MAX:
            return False

        with self._lock:
            return self._capture.set(cv2.CAP_PROP_EXPOSURE, value)

    def get_exposure(self) -> Optional[float]:
        """Get current camera exposure."""
        with self._lock:
            value = self._capture.get(cv2.CAP_PROP_EXPOSURE)
            return value if value != -1 else None

    def set_gain(self, value: float) -> bool:
        """Set camera gain with range validation."""
        if not self.GAIN_MIN <= value <= self.GAIN_MAX:
            return False

        with self._lock:
            return self._capture.set(cv2.CAP_PROP_GAIN, value)

    def get_gain(self) -> Optional[float]:
        """Get current camera gain."""
        with self._lock:
            value = self._capture.get(cv2.CAP_PROP_GAIN)
            return value if value != -1 else None

    def set_brightness(self, value: float) -> bool:
        """Set camera brightness with range validation."""
        if not self.BRIGHTNESS_MIN <= value <= self.BRIGHTNESS_MAX:
            return False

        with self._lock:
            return self._capture.set(cv2.CAP_PROP_BRIGHTNESS, value)

    def get_brightness(self) -> Optional[float]:
        """Get current camera brightness."""
        with self._lock:
            value = self._capture.get(cv2.CAP_PROP_BRIGHTNESS)
            return value if value != -1 else None

    def set_property(self, prop_id: int, value: float) -> bool:
        """
        Set camera property with whitelist and range validation.
        Only allows setting properties that are safe for plugin access.
        """
        if prop_id not in self.WHITELISTED_PROPERTIES:
            return False

        if prop_id in self.PROPERTY_RANGES:
            min_val, max_val = self.PROPERTY_RANGES[prop_id]
            if not min_val <= value <= max_val:
                return False

        with self._lock:
            return self._capture.set(prop_id, value)

    def get_property(self, prop_id: int) -> Optional[float]:
        """Get camera property value."""
        if prop_id not in self.WHITELISTED_PROPERTIES:
            return None

        with self._lock:
            value = self._capture.get(prop_id)
            return value if value != -1 else None
