#!/usr/bin/env python3
"""Full-width horizontal sliding compass bar showing heading and direction markers."""

import sys
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.plugin_base import HUDContext, HUDPlugin, PluginConfig, PluginMetadata, PluginPosition


class CompassPlugin(HUDPlugin):
    VISIBLE_DEGREES_PER_SIDE = 90
    MAX_VISIBLE_FRIENDLY_UNITS = 2
    COMPASS_BAR_Y_OFFSET = 30
    HEADING_TEXT_Y_OFFSET = 25
    CENTER_INDICATOR_HEIGHT = 8
    CENTER_INDICATOR_TOP_OFFSET = 5
    CENTER_INDICATOR_BOTTOM_OFFSET = 5
    CARDINAL_TICK_HEIGHT = 12
    INTERCARDINAL_TICK_HEIGHT = 8
    CARDINAL_FONT_SCALE = 0.5
    INTERCARDINAL_FONT_SCALE = 0.4
    LABEL_Y_OFFSET = 5
    HEADING_FONT_SCALE = 0.7
    HEADING_GLOW_THICKNESS = 4
    HEADING_TEXT_THICKNESS = 2
    COMPASS_LINE_THICKNESS = 2
    TICK_MARK_THICKNESS = 2
    FRIENDLY_DIAMOND_SIZE = 5
    FRIENDLY_DIAMOND_Y_TOP = 30
    FRIENDLY_DIAMOND_Y_MID = 25
    FRIENDLY_DIAMOND_Y_BOTTOM = 20
    FRIENDLY_OUTLINE_THICKNESS = 1

    METADATA = PluginMetadata(
        name="Compass",
        version="1.0.0",
        author="Project WARLOCK Team",
        description="Full-width horizontal compass bar",
        dependencies=[],
        provides=[],
        consumes=["border_padding"],
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self.heading = 0.0
        self.friendly_units: List[dict] = []

        self.primary_color = (220, 220, 210)
        self.secondary_color = (180, 180, 170)
        self.friendly_color = (255, 200, 100)

    def initialize(self) -> bool:
        self.config.position = PluginPosition.CUSTOM
        self.config.x = 0
        self.config.y = 0
        return True

    def update(self, delta_time: float):
        if "player_position" in self.context.state:
            player_pos = self.context.state["player_position"]
            self.heading = player_pos.get("heading", 0.0) % 360

        if "friendly_units" in self.context.state:
            self.friendly_units = self.context.state["friendly_units"]

    def _get_border_padding_data(self) -> dict:
        return self.get_data(
            "border_padding",
            {
                "padding_top": 0,
                "padding_left": 0,
                "padding_right": 0,
                "bounds": {"width": self.context.frame_width, "x_min": 0, "x_max": self.context.frame_width},
            },
        )

    def _calculate_compass_bar_bounds(self, border_padding: dict) -> tuple:
        bounds = border_padding.get("bounds", {})
        padding_top = border_padding.get("padding_top", 0)

        bar_y = padding_top + self.COMPASS_BAR_Y_OFFSET
        bar_width = bounds.get("width", self.context.frame_width)
        bar_x_start = bounds.get("x_min", 0)
        bar_x_end = bounds.get("x_max", self.context.frame_width)

        return bar_y, bar_width, bar_x_start, bar_x_end

    def _draw_compass_line(self, frame: np.ndarray, bar_x_start: int, bar_x_end: int, bar_y: int):
        cv2.line(
            frame,
            (bar_x_start, bar_y),
            (bar_x_end, bar_y),
            self.secondary_color,
            self.COMPASS_LINE_THICKNESS,
            cv2.LINE_AA,
        )

    def _calculate_relative_angle(self, direction_angle: float) -> float:
        relative_angle = (direction_angle - self.heading + 360) % 360
        if relative_angle > 180:
            relative_angle -= 360
        return relative_angle

    def _is_direction_visible(self, relative_angle: float) -> bool:
        return abs(relative_angle) <= self.VISIBLE_DEGREES_PER_SIDE

    def _calculate_marker_x_position(self, relative_angle: float, center_x: int, pixels_per_degree: float) -> int:
        return int(center_x + relative_angle * pixels_per_degree)

    def _is_cardinal_direction(self, direction: str) -> bool:
        return direction in ["N", "E", "S", "W"]

    def _draw_direction_tick_mark(self, frame: np.ndarray, marker_x: int, bar_y: int, tick_height: int):
        cv2.line(
            frame,
            (marker_x, bar_y - tick_height),
            (marker_x, bar_y),
            self.primary_color,
            self.TICK_MARK_THICKNESS,
            cv2.LINE_AA,
        )

    def _draw_direction_label(
        self, frame: np.ndarray, direction: str, marker_x: int, bar_y: int, tick_height: int, font_scale: float
    ):
        text_size = cv2.getTextSize(direction, cv2.FONT_HERSHEY_SIMPLEX, font_scale, 1)[0]
        text_x = marker_x - text_size[0] // 2
        cv2.putText(
            frame,
            direction,
            (text_x, bar_y - tick_height - self.LABEL_Y_OFFSET),
            cv2.FONT_HERSHEY_SIMPLEX,
            font_scale,
            self.primary_color,
            1,
            cv2.LINE_AA,
        )

    def _draw_direction_marker(
        self,
        frame: np.ndarray,
        direction: str,
        direction_angle: float,
        center_x: int,
        bar_y: int,
        pixels_per_degree: float,
    ):
        relative_angle = self._calculate_relative_angle(direction_angle)

        if not self._is_direction_visible(relative_angle):
            return

        marker_x = self._calculate_marker_x_position(relative_angle, center_x, pixels_per_degree)

        is_cardinal = self._is_cardinal_direction(direction)
        tick_height = self.CARDINAL_TICK_HEIGHT if is_cardinal else self.INTERCARDINAL_TICK_HEIGHT
        font_scale = self.CARDINAL_FONT_SCALE if is_cardinal else self.INTERCARDINAL_FONT_SCALE

        self._draw_direction_tick_mark(frame, marker_x, bar_y, tick_height)
        self._draw_direction_label(frame, direction, marker_x, bar_y, tick_height, font_scale)

    def _get_all_compass_directions(self) -> List[tuple]:
        return [("N", 0), ("NE", 45), ("E", 90), ("SE", 135), ("S", 180), ("SW", 225), ("W", 270), ("NW", 315)]

    def _draw_all_direction_markers(self, frame: np.ndarray, center_x: int, bar_y: int, bar_width: int):
        pixels_per_degree = bar_width / (2 * self.VISIBLE_DEGREES_PER_SIDE)
        directions = self._get_all_compass_directions()

        for direction, angle in directions:
            self._draw_direction_marker(frame, direction, angle, center_x, bar_y, pixels_per_degree)

    def _calculate_friendly_unit_relative_bearing(self, unit: dict) -> Optional[float]:
        bearing = unit.get("bearing", 0)
        relative_bearing = (bearing - self.heading + 360) % 360
        if relative_bearing > 180:
            relative_bearing -= 360

        if abs(relative_bearing) <= self.VISIBLE_DEGREES_PER_SIDE:
            return relative_bearing
        return None

    def _get_visible_friendly_units(self) -> List[tuple]:
        visible_units = []
        for unit in self.friendly_units:
            relative_bearing = self._calculate_friendly_unit_relative_bearing(unit)
            if relative_bearing is not None:
                visible_units.append((unit, relative_bearing))
        return visible_units[: self.MAX_VISIBLE_FRIENDLY_UNITS]

    def _create_friendly_unit_diamond_points(self, marker_x: int, bar_y: int) -> np.ndarray:
        return np.array(
            [
                [marker_x, bar_y - self.FRIENDLY_DIAMOND_Y_TOP],
                [marker_x + self.FRIENDLY_DIAMOND_SIZE, bar_y - self.FRIENDLY_DIAMOND_Y_MID],
                [marker_x, bar_y - self.FRIENDLY_DIAMOND_Y_BOTTOM],
                [marker_x - self.FRIENDLY_DIAMOND_SIZE, bar_y - self.FRIENDLY_DIAMOND_Y_MID],
            ],
            np.int32,
        )

    def _draw_friendly_unit_marker(self, frame: np.ndarray, marker_x: int, bar_y: int):
        diamond_points = self._create_friendly_unit_diamond_points(marker_x, bar_y)
        cv2.fillPoly(frame, [diamond_points], self.friendly_color, cv2.LINE_AA)
        cv2.polylines(frame, [diamond_points], True, (255, 255, 255), self.FRIENDLY_OUTLINE_THICKNESS, cv2.LINE_AA)

    def _draw_all_friendly_unit_markers(self, frame: np.ndarray, center_x: int, bar_y: int, pixels_per_degree: float):
        visible_units = self._get_visible_friendly_units()

        for unit, relative_bearing in visible_units:
            marker_x = self._calculate_marker_x_position(relative_bearing, center_x, pixels_per_degree)
            self._draw_friendly_unit_marker(frame, marker_x, bar_y)

    def _format_heading_text(self) -> str:
        return f"{int(self.heading):03d}"

    def _calculate_heading_text_position(self, center_x: int) -> int:
        heading_text = self._format_heading_text()
        text_size = cv2.getTextSize(
            heading_text, cv2.FONT_HERSHEY_SIMPLEX, self.HEADING_FONT_SCALE, self.HEADING_TEXT_THICKNESS
        )[0]
        return center_x - text_size[0] // 2

    def _draw_heading_with_glow(self, frame: np.ndarray, center_x: int, bar_y: int):
        heading_text = self._format_heading_text()
        text_x = self._calculate_heading_text_position(center_x)
        text_y = bar_y + self.HEADING_TEXT_Y_OFFSET

        cv2.putText(
            frame,
            heading_text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.HEADING_FONT_SCALE,
            self.secondary_color,
            self.HEADING_GLOW_THICKNESS,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            heading_text,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.HEADING_FONT_SCALE,
            self.primary_color,
            self.HEADING_TEXT_THICKNESS,
            cv2.LINE_AA,
        )

    def _create_center_indicator_triangle(self, center_x: int, bar_y: int) -> np.ndarray:
        return np.array(
            [
                [center_x, bar_y + self.CENTER_INDICATOR_TOP_OFFSET],
                [center_x - self.CENTER_INDICATOR_HEIGHT, bar_y - self.CENTER_INDICATOR_BOTTOM_OFFSET],
                [center_x + self.CENTER_INDICATOR_HEIGHT, bar_y - self.CENTER_INDICATOR_BOTTOM_OFFSET],
            ],
            np.int32,
        )

    def _draw_center_indicator(self, frame: np.ndarray, center_x: int, bar_y: int):
        triangle_points = self._create_center_indicator_triangle(center_x, bar_y)
        cv2.fillPoly(frame, [triangle_points], self.primary_color, cv2.LINE_AA)

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible:
            return frame

        border_padding = self._get_border_padding_data()
        bar_y, bar_width, bar_x_start, bar_x_end = self._calculate_compass_bar_bounds(border_padding)
        center_x = (bar_x_start + bar_x_end) // 2
        pixels_per_degree = bar_width / (2 * self.VISIBLE_DEGREES_PER_SIDE)

        self._draw_compass_line(frame, bar_x_start, bar_x_end, bar_y)
        self._draw_all_direction_markers(frame, center_x, bar_y, bar_width)
        self._draw_all_friendly_unit_markers(frame, center_x, bar_y, pixels_per_degree)
        self._draw_heading_with_glow(frame, center_x, bar_y)
        self._draw_center_indicator(frame, center_x, bar_y)

        return frame

    def handle_key(self, key: int) -> bool:
        if key == ord("c"):
            self.toggle_visibility()
            print(f"Compass: {'ON' if self.visible else 'OFF'}")
            return True
        return False
