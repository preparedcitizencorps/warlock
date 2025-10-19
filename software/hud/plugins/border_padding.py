#!/usr/bin/env python3

import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.plugin_base import HUDContext, HUDPlugin, PluginConfig, PluginMetadata


class BorderPaddingPlugin(HUDPlugin):
    DEFAULT_PADDING_PX = 40
    PADDING_ADJUSTMENT_STEP_PX = 5
    CORNER_MARKER_SIZE = 20

    METADATA = PluginMetadata(
        name="Border Padding",
        version="1.0.0",
        author="Project WARLOCK Team",
        description="AR display border padding and margin management",
        dependencies=[],
        provides=["border_padding"],
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self.padding_top = self.get_setting("padding_top", self.DEFAULT_PADDING_PX)
        self.padding_bottom = self.get_setting("padding_bottom", self.DEFAULT_PADDING_PX)
        self.padding_left = self.get_setting("padding_left", self.DEFAULT_PADDING_PX)
        self.padding_right = self.get_setting("padding_right", self.DEFAULT_PADDING_PX)
        self.padding_step = self.get_setting("padding_step", self.PADDING_ADJUSTMENT_STEP_PX)

        self.show_boundaries = self.get_setting("show_boundaries", True)
        self.boundary_color = tuple(self.get_setting("boundary_color", [0, 255, 255]))
        self.boundary_thickness = self.get_setting("boundary_thickness", 2)
        self.show_measurements = self.get_setting("show_measurements", True)

    def initialize(self) -> bool:
        self._publish_padding_bounds_to_context()
        return True

    def _publish_padding_bounds_to_context(self):
        border_padding = {
            "padding_top": self.padding_top,
            "padding_bottom": self.padding_bottom,
            "padding_left": self.padding_left,
            "padding_right": self.padding_right,
            "bounds": {
                "x_min": self.padding_left,
                "x_max": self.context.frame_width - self.padding_right,
                "y_min": self.padding_top,
                "y_max": self.context.frame_height - self.padding_bottom,
                "width": self.context.frame_width - self.padding_left - self.padding_right,
                "height": self.context.frame_height - self.padding_top - self.padding_bottom,
            },
        }
        self.provide_data("border_padding", border_padding)

    def update(self, delta_time: float):
        self._publish_padding_bounds_to_context()

    def _get_safe_area_bounds(self):
        border_padding = self.context.state.get("border_padding", {})
        bounds = border_padding.get("bounds", {})

        x_min = bounds.get("x_min", 0)
        x_max = bounds.get("x_max", self.context.frame_width)
        y_min = bounds.get("y_min", 0)
        y_max = bounds.get("y_max", self.context.frame_height)

        return x_min, x_max, y_min, y_max

    def _draw_boundary_rectangle(self, frame: np.ndarray, x_min: int, x_max: int, y_min: int, y_max: int):
        cv2.rectangle(frame, (x_min, y_min), (x_max, y_max), self.boundary_color, self.boundary_thickness, cv2.LINE_AA)

    def _draw_corner_markers(self, frame: np.ndarray, x_min: int, x_max: int, y_min: int, y_max: int):
        corner_configs = [
            (x_min, y_min, [(1, 0), (0, 1)]),
            (x_max, y_min, [(-1, 0), (0, 1)]),
            (x_min, y_max, [(1, 0), (0, -1)]),
            (x_max, y_max, [(-1, 0), (0, -1)]),
        ]

        for cx, cy, directions in corner_configs:
            for dx, dy in directions:
                end_x = cx + dx * self.CORNER_MARKER_SIZE
                end_y = cy + dy * self.CORNER_MARKER_SIZE
                cv2.line(frame, (cx, cy), (end_x, end_y), self.boundary_color, self.boundary_thickness + 1, cv2.LINE_AA)

    def _draw_padding_measurement_text(self, frame: np.ndarray, text: str, x: int, y: int):
        font_scale = 0.4
        font_thickness = 1
        cv2.putText(
            frame, text, (x, y), cv2.FONT_HERSHEY_SIMPLEX, font_scale, self.boundary_color, font_thickness, cv2.LINE_AA
        )

    def _calculate_centered_text_position(self, text: str, center_x: int, center_y: int) -> tuple:
        font_scale = 0.4
        font_thickness = 1
        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)[0]
        text_x = center_x - text_size[0] // 2
        text_y = center_y + text_size[1] // 2
        return text_x, text_y

    def _draw_all_padding_measurements(self, frame: np.ndarray):
        measurements = [
            (f"{self.padding_top}px", self.context.frame_width // 2, self.padding_top // 2),
            (
                f"{self.padding_bottom}px",
                self.context.frame_width // 2,
                self.context.frame_height - self.padding_bottom // 2,
            ),
            (f"{self.padding_left}px", self.padding_left // 2, self.context.frame_height // 2),
            (
                f"{self.padding_right}px",
                self.context.frame_width - self.padding_right // 2,
                self.context.frame_height // 2,
            ),
        ]

        for text, center_x, center_y in measurements:
            text_x, text_y = self._calculate_centered_text_position(text, center_x, center_y)
            self._draw_padding_measurement_text(frame, text, text_x, text_y)

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible or not self.show_boundaries:
            return frame

        x_min, x_max, y_min, y_max = self._get_safe_area_bounds()

        self._draw_boundary_rectangle(frame, x_min, x_max, y_min, y_max)
        self._draw_corner_markers(frame, x_min, x_max, y_min, y_max)

        if self.show_measurements:
            self._draw_all_padding_measurements(frame)

        return frame

    def _decrease_padding(self):
        self.padding_top = max(0, self.padding_top - self.padding_step)
        self.padding_bottom = max(0, self.padding_bottom - self.padding_step)
        self.padding_left = max(0, self.padding_left - self.padding_step)
        self.padding_right = max(0, self.padding_right - self.padding_step)
        self._publish_padding_bounds_to_context()
        print(f"Border Padding: Decreased to {self.padding_top}px")

    def _increase_padding(self):
        max_padding = min(self.context.frame_width, self.context.frame_height) // 4
        self.padding_top = min(max_padding, self.padding_top + self.padding_step)
        self.padding_bottom = min(max_padding, self.padding_bottom + self.padding_step)
        self.padding_left = min(max_padding, self.padding_left + self.padding_step)
        self.padding_right = min(max_padding, self.padding_right + self.padding_step)
        self._publish_padding_bounds_to_context()
        print(f"Border Padding: Increased to {self.padding_top}px")

    def _toggle_boundary_visibility(self):
        self.show_boundaries = not self.show_boundaries
        print(f"Border Padding Boundaries: {'ON' if self.show_boundaries else 'OFF'}")

    def handle_key(self, key: int) -> bool:
        if key == ord("["):
            self._decrease_padding()
            return True
        elif key == ord("]"):
            self._increase_padding()
            return True
        elif key == ord("b"):
            self._toggle_boundary_visibility()
            return True
        return False

    def cleanup(self):
        pass
