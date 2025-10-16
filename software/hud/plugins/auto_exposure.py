#!/usr/bin/env python3
"""Auto-exposure plugin for automatic camera brightness adjustment in low-light conditions."""

import cv2
import numpy as np
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hud.plugin_base import HUDPlugin, HUDContext, PluginConfig, PluginMetadata
from hud.camera_controller import CameraController


class AutoExposurePlugin(HUDPlugin):
    """
    Automatically adjusts camera exposure settings based on scene brightness.
    Provides enhanced visibility in low-light and high-contrast environments.
    """

    DEFAULT_TARGET_BRIGHTNESS = 128
    DEFAULT_BRIGHTNESS_TOLERANCE = 15
    DEFAULT_ADJUSTMENT_SPEED = 0.15
    DEFAULT_MIN_EXPOSURE = -13
    DEFAULT_MAX_EXPOSURE = 0
    DEFAULT_MIN_GAIN = 0
    DEFAULT_MAX_GAIN = 100
    DEFAULT_USE_HISTOGRAM_EQ = True
    DEFAULT_USE_CLAHE = True
    DEFAULT_ENABLE_AUTO_GAIN = True
    DEFAULT_ENABLE_AUTO_EXPOSURE = True

    CLAHE_CLIP_LIMIT = 2.0
    CLAHE_TILE_GRID_SIZE = (8, 8)

    DISPLAY_FONT = cv2.FONT_HERSHEY_SIMPLEX
    DISPLAY_FONT_SCALE = 0.4
    DISPLAY_FONT_THICKNESS = 1
    DISPLAY_COLOR = (0, 255, 255)
    DISPLAY_POSITION_X = 10
    DISPLAY_POSITION_Y = 20
    DISPLAY_LINE_HEIGHT = 18

    CENTER_WEIGHT = 0.7
    FULL_FRAME_WEIGHT = 0.3
    EXPOSURE_ADJUSTMENT_FACTOR = 0.1
    GAIN_ADJUSTMENT_FACTOR = 0.5
    VERY_DARK_THRESHOLD = 80

    MANUAL_EXPOSURE_MODE = 0.25
    AUTO_EXPOSURE_MODE = 0.75

    TARGET_BRIGHTNESS_STEP = 10

    METADATA = PluginMetadata(
        name="Auto Exposure",
        version="1.0.0",
        author="Project WARLOCK Team",
        description="Automatic camera exposure and brightness adjustment for low-light conditions",
        provides=['camera_brightness', 'auto_exposure_active'],
        consumes=[]
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self.target_brightness = self.get_setting('target_brightness', self.DEFAULT_TARGET_BRIGHTNESS)
        self.brightness_tolerance = self.get_setting('brightness_tolerance', self.DEFAULT_BRIGHTNESS_TOLERANCE)
        self.adjustment_speed = self.get_setting('adjustment_speed', self.DEFAULT_ADJUSTMENT_SPEED)
        self.min_exposure = self.get_setting('min_exposure', self.DEFAULT_MIN_EXPOSURE)
        self.max_exposure = self.get_setting('max_exposure', self.DEFAULT_MAX_EXPOSURE)
        self.min_gain = self.get_setting('min_gain', self.DEFAULT_MIN_GAIN)
        self.max_gain = self.get_setting('max_gain', self.DEFAULT_MAX_GAIN)
        self.use_histogram_eq = self.get_setting('use_histogram_eq', self.DEFAULT_USE_HISTOGRAM_EQ)
        self.use_clahe = self.get_setting('use_clahe', self.DEFAULT_USE_CLAHE)
        self.enable_auto_gain = self.get_setting('enable_auto_gain', self.DEFAULT_ENABLE_AUTO_GAIN)
        self.enable_auto_exposure = self.get_setting('enable_auto_exposure', self.DEFAULT_ENABLE_AUTO_EXPOSURE)

        self.current_exposure: Optional[float] = None
        self.current_gain: Optional[float] = None
        self.current_brightness: float = 0.0
        self.camera_controller: Optional[CameraController] = None
        self.auto_mode_enabled = True
        self.clahe = None
        self.show_stats = True

        if self.use_clahe:
            self.clahe = cv2.createCLAHE(
                clipLimit=self.CLAHE_CLIP_LIMIT,
                tileGridSize=self.CLAHE_TILE_GRID_SIZE
            )

    def initialize(self) -> bool:
        print("Auto Exposure Plugin: Initializing...")

        self.camera_controller = self.get_data('camera_handle', None)

        if self.camera_controller is not None:
            self._initialize_camera_settings()
        else:
            print("Auto Exposure Plugin: Camera controller not available in context")
            print("Auto Exposure Plugin: Software-based adjustments will be used")

        print("Auto Exposure Plugin: Initialized successfully")
        return True

    def _initialize_camera_settings(self):
        try:
            self.camera_controller.set_property(cv2.CAP_PROP_AUTO_EXPOSURE, self.MANUAL_EXPOSURE_MODE)

            if self.enable_auto_exposure:
                initial_exposure = (self.min_exposure + self.max_exposure) / 2
                self.camera_controller.set_exposure(initial_exposure)
                self.current_exposure = self.camera_controller.get_exposure()
                print(f"Auto Exposure Plugin: Initial exposure set to {self.current_exposure}")

            if self.enable_auto_gain:
                initial_gain = (self.min_gain + self.max_gain) / 2
                self.camera_controller.set_gain(initial_gain)
                self.current_gain = self.camera_controller.get_gain()
                print(f"Auto Exposure Plugin: Initial gain set to {self.current_gain}")

        except Exception as e:
            print(f"Auto Exposure Plugin: Error initializing camera settings: {e}")

    def _calculate_scene_brightness(self, frame: np.ndarray) -> float:
        if len(frame.shape) == 3:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        h, w = gray.shape
        center_h, center_w = h // 4, w // 4
        center_region = gray[center_h:3*center_h, center_w:3*center_w]

        full_brightness = np.mean(gray)
        center_brightness = np.mean(center_region)

        weighted_brightness = self.CENTER_WEIGHT * center_brightness + self.FULL_FRAME_WEIGHT * full_brightness

        return weighted_brightness

    def _adjust_exposure(self, current_brightness: float):
        if self.camera_controller is None or not self.enable_auto_exposure:
            return

        brightness_error = self.target_brightness - current_brightness

        if abs(brightness_error) < self.brightness_tolerance:
            return

        try:
            adjustment = brightness_error * self.adjustment_speed * self.EXPOSURE_ADJUSTMENT_FACTOR

            if self.current_exposure is None:
                self.current_exposure = self.camera_controller.get_exposure()

            new_exposure = np.clip(
                self.current_exposure + adjustment,
                self.min_exposure,
                self.max_exposure
            )

            if self.camera_controller.set_exposure(new_exposure):
                self.current_exposure = new_exposure

        except Exception as e:
            print(f"Auto Exposure Plugin: Error adjusting exposure: {e}")

    def _adjust_gain(self, current_brightness: float):
        if self.camera_controller is None or not self.enable_auto_gain:
            return

        brightness_error = self.target_brightness - current_brightness

        if abs(brightness_error) < self.brightness_tolerance:
            return

        if brightness_error > 0 and self.current_exposure is not None:
            if self.current_exposure < self.max_exposure - 1:
                return

        try:
            adjustment = brightness_error * self.adjustment_speed * self.GAIN_ADJUSTMENT_FACTOR

            if self.current_gain is None:
                self.current_gain = self.camera_controller.get_gain()

            new_gain = np.clip(
                self.current_gain + adjustment,
                self.min_gain,
                self.max_gain
            )

            if self.camera_controller.set_gain(new_gain):
                self.current_gain = new_gain

        except Exception as e:
            print(f"Auto Exposure Plugin: Error adjusting gain: {e}")

    def _apply_software_enhancement(self, frame: np.ndarray) -> np.ndarray:
        if not self.auto_mode_enabled:
            return frame

        if self.use_clahe and self.clahe is not None:
            lab = cv2.cvtColor(frame, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)

            l_clahe = self.clahe.apply(l)

            lab_clahe = cv2.merge([l_clahe, a, b])
            frame = cv2.cvtColor(lab_clahe, cv2.COLOR_LAB2BGR)

        elif self.use_histogram_eq and self.current_brightness < self.VERY_DARK_THRESHOLD:
            yuv = cv2.cvtColor(frame, cv2.COLOR_BGR2YUV)
            yuv[:, :, 0] = cv2.equalizeHist(yuv[:, :, 0])
            frame = cv2.cvtColor(yuv, cv2.COLOR_YUV2BGR)

        return frame

    def update(self, delta_time: float):
        raw_frame = self.get_data('raw_frame', None)

        if raw_frame is not None and self.auto_mode_enabled:
            self.current_brightness = self._calculate_scene_brightness(raw_frame)

            self._adjust_exposure(self.current_brightness)
            self._adjust_gain(self.current_brightness)

            self.provide_data('camera_brightness', self.current_brightness)
            self.provide_data('auto_exposure_active', self.auto_mode_enabled)

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible:
            return frame

        self.provide_data('raw_frame', frame.copy())

        self.current_brightness = self._calculate_scene_brightness(frame)

        frame = self._apply_software_enhancement(frame)

        if self.show_stats:
            frame = self._draw_statistics(frame)

        return frame

    def _draw_statistics(self, frame: np.ndarray) -> np.ndarray:
        stats = [
            f"Auto-Exposure: {'ON' if self.auto_mode_enabled else 'OFF'}",
            f"Brightness: {self.current_brightness:.1f} / {self.target_brightness}",
        ]

        if self.current_exposure is not None:
            stats.append(f"Exposure: {self.current_exposure:.1f}")

        if self.current_gain is not None:
            stats.append(f"Gain: {self.current_gain:.1f}")

        y_start = self.DISPLAY_POSITION_Y - 5
        y_end = y_start + len(stats) * self.DISPLAY_LINE_HEIGHT + 10
        cv2.rectangle(
            frame,
            (self.DISPLAY_POSITION_X - 5, y_start),
            (250, y_end),
            (0, 0, 0),
            -1
        )

        for i, stat in enumerate(stats):
            y_pos = self.DISPLAY_POSITION_Y + i * self.DISPLAY_LINE_HEIGHT + 10
            cv2.putText(
                frame,
                stat,
                (self.DISPLAY_POSITION_X, y_pos),
                self.DISPLAY_FONT,
                self.DISPLAY_FONT_SCALE,
                self.DISPLAY_COLOR,
                self.DISPLAY_FONT_THICKNESS,
                cv2.LINE_AA
            )

        return frame

    def handle_key(self, key: int) -> bool:
        if key == ord('e'):
            self.auto_mode_enabled = not self.auto_mode_enabled
            status = "ENABLED" if self.auto_mode_enabled else "DISABLED"
            print(f"Auto Exposure: {status}")
            return True
        elif key == ord('o'):
            self.show_stats = not self.show_stats
            return True
        elif key == ord('+') or key == ord('='):
            self.target_brightness = min(255, self.target_brightness + self.TARGET_BRIGHTNESS_STEP)
            print(f"Auto Exposure: Target brightness = {self.target_brightness}")
            return True
        elif key == ord('-') or key == ord('_'):
            self.target_brightness = max(0, self.target_brightness - self.TARGET_BRIGHTNESS_STEP)
            print(f"Auto Exposure: Target brightness = {self.target_brightness}")
            return True

        return False

    def cleanup(self):
        if self.camera_controller is not None:
            try:
                self.camera_controller.set_property(cv2.CAP_PROP_AUTO_EXPOSURE, self.AUTO_EXPOSURE_MODE)
            except Exception as e:
                print(f"Auto Exposure Plugin: Error during cleanup: {e}")

        self.camera_controller = None
        self.clahe = None
