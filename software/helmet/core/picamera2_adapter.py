#!/usr/bin/env python3
"""
Picamera2 adapter for WARLOCK

Provides OpenCV-compatible interface for Raspberry Pi cameras using picamera2.
"""

import logging

import numpy as np

logger = logging.getLogger(__name__)


class Picamera2Adapter:
    """Adapter to make picamera2 work like cv2.VideoCapture"""

    def __init__(self, camera_num=0, width=1280, height=720):
        """Initialize picamera2 camera.

        Args:
            camera_num: Camera index (usually 0)
            width: Frame width
            height: Frame height
        """
        try:
            from picamera2 import Picamera2
        except ImportError as e:
            raise ImportError("picamera2 not found. Install with: sudo apt install python3-picamera2") from e

        self.camera = Picamera2(camera_num)

        # Configure camera for BGR output (OpenCV format)
        config = self.camera.create_preview_configuration(main={"size": (width, height), "format": "BGR888"})
        self.camera.configure(config)
        self.camera.start()

        logger.info(f"Picamera2 started: {width}x{height}")

    def isOpened(self):
        """Check if camera is open (compatibility with cv2.VideoCapture)"""
        return self.camera is not None

    def read(self):
        """Read a frame from the camera.

        Returns:
            tuple: (success, frame) where frame is a numpy array in BGR format
        """
        try:
            # Capture array returns BGR888 format
            frame = self.camera.capture_array()
            return True, frame
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            return False, None

    def set(self, prop, value):
        """Set camera property (compatibility with cv2.VideoCapture).

        Most properties are ignored since picamera2 handles them differently.
        """
        # Picamera2 doesn't use the same property system as OpenCV
        # Configuration is done at init time
        return True

    def get(self, prop):
        """Get camera property (compatibility with cv2.VideoCapture).

        Returns dummy values for compatibility since picamera2 doesn't expose
        properties the same way as OpenCV.
        """
        # Return -1 (OpenCV convention for unsupported property)
        return -1

    def release(self):
        """Release the camera"""
        if self.camera:
            self.camera.stop()
            self.camera.close()
            logger.info("Picamera2 released")
