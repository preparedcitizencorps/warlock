#!/usr/bin/env python3
"""Simple FPS counter displayed in top-right corner."""

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.plugin_base import HUDContext, HUDPlugin, PluginConfig, PluginMetadata, PluginPosition


class FPSCounterPlugin(HUDPlugin):
    DEFAULT_UPDATE_INTERVAL_SECONDS = 0.5
    DEFAULT_VISIBILITY = False
    X_OFFSET_FROM_RIGHT = -100
    Y_OFFSET_FROM_TOP = 10
    TEXT_Y_OFFSET = 20
    TEXT_FONT_SCALE = 0.4
    TEXT_THICKNESS = 1

    METADATA = PluginMetadata(
        name="FPS Counter", version="1.0.0", author="Project WARLOCK Team", description="Displays current FPS"
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self.fps = 0.0
        self.frame_count = 0
        # Validate fps_update_interval to prevent division by zero
        configured_interval = self.get_setting("fps_update_interval", self.DEFAULT_UPDATE_INTERVAL_SECONDS)
        if configured_interval <= 0:
            self.fps_update_interval = self.DEFAULT_UPDATE_INTERVAL_SECONDS
        else:
            self.fps_update_interval = configured_interval
        self.time_since_update = 0.0

        self.text_color = (220, 220, 210)

        self.visible = self.get_setting("visible", self.DEFAULT_VISIBILITY)

    def initialize(self) -> bool:
        self.config.position = PluginPosition.TOP_RIGHT
        self.config.x = self.X_OFFSET_FROM_RIGHT
        self.config.y = self.Y_OFFSET_FROM_TOP
        return True

    def _should_update_fps(self) -> bool:
        return self.time_since_update >= self.fps_update_interval

    def _calculate_fps(self):
        if self.time_since_update > 0:
            self.fps = self.frame_count / self.time_since_update
        else:
            self.fps = 0.0
        self.frame_count = 0
        self.time_since_update = 0.0

    def update(self, delta_time: float):
        self.frame_count += 1
        self.time_since_update += delta_time

        if self._should_update_fps():
            self._calculate_fps()

    def _calculate_screen_position(self, x: int) -> int:
        if not hasattr(self.context, "frame_width") or not isinstance(self.context.frame_width, int):
            raise ValueError("HUDContext must have a valid frame_width (int)")

        if x < 0:
            return self.context.frame_width + x
        return x

    def _format_fps_text(self) -> str:
        return f"FPS: {self.fps:.1f}"

    def _draw_fps_text(self, frame: np.ndarray, text: str, x: int, y: int):
        cv2.putText(
            frame,
            text,
            (x, y + self.TEXT_Y_OFFSET),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.TEXT_FONT_SCALE,
            self.text_color,
            self.TEXT_THICKNESS,
            cv2.LINE_AA,
        )

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible:
            return frame

        x, y = self.get_position()
        x = self._calculate_screen_position(x)

        fps_text = self._format_fps_text()
        self._draw_fps_text(frame, fps_text, x, y)

        return frame

    def handle_key(self, key: int) -> bool:
        if key == ord("f"):
            self.toggle_visibility()
            print(f"FPS Counter: {'ON' if self.visible else 'OFF'}")
            return True
        return False
