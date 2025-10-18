#!/usr/bin/env python3
"""Picamera2 adapter with OpenCV-compatible interface."""

import logging

import numpy as np

logger = logging.getLogger(__name__)


class Picamera2Adapter:
    def __init__(self, camera_num=0, width=1280, height=720):
        try:
            from picamera2 import Picamera2
        except ImportError as e:
            raise ImportError("picamera2 not found. Install with: sudo apt install python3-picamera2") from e

        self.camera = Picamera2(camera_num)

        config = self.camera.create_preview_configuration(main={"size": (width, height), "format": "BGR888"})
        self.camera.configure(config)
        self.camera.start()

        logger.info(f"Picamera2 started: {width}x{height}")

    def isOpened(self):
        return self.camera is not None

    def read(self):
        try:
            frame = self.camera.capture_array()
            return True, frame
        except Exception as e:
            logger.error(f"Failed to capture frame: {e}")
            return False, None

    def set(self, prop, value):
        return False

    def get(self, prop):
        return -1

    def release(self):
        if self.camera:
            self.camera.stop()
            self.camera.close()
            logger.info("Picamera2 released")
