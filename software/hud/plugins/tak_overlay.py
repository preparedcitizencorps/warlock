#!/usr/bin/env python3
"""TAK POI overlay plugin - displays points of interest from TAK server."""

import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.plugin_base import HUDContext, HUDPlugin, PluginConfig, PluginMetadata, PluginPosition


class TAKOverlayPlugin(HUDPlugin):
    MAX_VISIBLE_POIS = 10
    MAX_DISTANCE_METERS = 5000
    POI_MARKER_SIZE = 8
    POI_LINE_THICKNESS = 2
    POI_FONT_SCALE = 0.5
    POI_TEXT_THICKNESS = 1
    LABEL_OFFSET_X = 10
    LABEL_OFFSET_Y = -5

    FRIENDLY_COLOR = (100, 255, 100)
    HOSTILE_COLOR = (0, 100, 255)
    NEUTRAL_COLOR = (200, 200, 200)
    UNKNOWN_COLOR = (150, 150, 150)

    METADATA = PluginMetadata(
        name="TAKOverlay",
        version="1.0.0",
        author="Project WARLOCK Team",
        description="Display TAK points of interest on HUD",
        dependencies=[],
        provides=["tak_overlay"],
        consumes=["border_padding"],
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)
        self.pois: List[Dict] = []
        self.player_position: Optional[Dict] = None
        self.player_heading: float = 0.0

    def initialize(self) -> bool:
        self.config.position = PluginPosition.CUSTOM
        return True

    def update(self, delta_time: float):
        self.player_position = self.context.state.get("player_position")
        if self.player_position:
            self.player_heading = self.player_position.get("heading", 0.0)

        tak_client = self.context.state.get("tak_client")
        if tak_client:
            self.pois = tak_client.get_pois()

    def _calculate_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters using Haversine formula."""
        R = 6371000
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    def _calculate_bearing(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate bearing from point 1 to point 2 in degrees."""
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_lambda = math.radians(lon2 - lon1)

        y = math.sin(delta_lambda) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
        theta = math.atan2(y, x)

        return (math.degrees(theta) + 360) % 360

    def _get_poi_color(self, poi_type: str) -> Tuple[int, int, int]:
        """Determine POI marker color based on CoT type."""
        if poi_type.startswith("a-f"):
            return self.FRIENDLY_COLOR
        elif poi_type.startswith("a-h"):
            return self.HOSTILE_COLOR
        elif poi_type.startswith("a-n"):
            return self.NEUTRAL_COLOR
        else:
            return self.UNKNOWN_COLOR

    def _project_poi_to_screen(
        self, poi: Dict, frame_width: int, frame_height: int, fov: float = 90.0
    ) -> Optional[Tuple[int, int, float, str]]:
        """Project POI to screen coordinates based on bearing and distance."""
        if not self.player_position:
            return None

        player_lat = self.player_position["latitude"]
        player_lon = self.player_position["longitude"]
        poi_lat = poi["latitude"]
        poi_lon = poi["longitude"]

        distance = self._calculate_distance(player_lat, player_lon, poi_lat, poi_lon)

        if distance > self.MAX_DISTANCE_METERS:
            return None

        bearing = self._calculate_bearing(player_lat, player_lon, poi_lat, poi_lon)
        relative_bearing = (bearing - self.player_heading + 360) % 360

        if relative_bearing > 180:
            relative_bearing -= 360

        half_fov = fov / 2
        if abs(relative_bearing) > half_fov:
            return None

        pixels_per_degree = frame_width / fov
        screen_x = int(frame_width / 2 + relative_bearing * pixels_per_degree)

        screen_y = int(frame_height / 2)

        return screen_x, screen_y, distance, poi.get("callsign", "Unknown")

    def _draw_poi_marker(self, frame: np.ndarray, x: int, y: int, color: Tuple[int, int, int]):
        """Draw diamond marker for POI."""
        points = np.array(
            [
                [x, y - self.POI_MARKER_SIZE],
                [x + self.POI_MARKER_SIZE, y],
                [x, y + self.POI_MARKER_SIZE],
                [x - self.POI_MARKER_SIZE, y],
            ],
            np.int32,
        )
        cv2.polylines(frame, [points], True, color, self.POI_LINE_THICKNESS, cv2.LINE_AA)

    def _draw_poi_label(
        self, frame: np.ndarray, x: int, y: int, callsign: str, distance: float, color: Tuple[int, int, int]
    ):
        """Draw POI label with callsign and distance."""
        label = f"{callsign} ({int(distance)}m)"

        text_x = x + self.LABEL_OFFSET_X
        text_y = y + self.LABEL_OFFSET_Y

        cv2.putText(
            frame,
            label,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.POI_FONT_SCALE,
            (0, 0, 0),
            self.POI_TEXT_THICKNESS + 2,
            cv2.LINE_AA,
        )
        cv2.putText(
            frame,
            label,
            (text_x, text_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            self.POI_FONT_SCALE,
            color,
            self.POI_TEXT_THICKNESS,
            cv2.LINE_AA,
        )

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible or not self.player_position:
            return frame

        frame_height, frame_width = frame.shape[:2]

        visible_pois = []
        for poi in self.pois:
            projection = self._project_poi_to_screen(poi, frame_width, frame_height)
            if projection:
                screen_x, screen_y, distance, callsign = projection
                visible_pois.append((distance, screen_x, screen_y, callsign, poi))

        visible_pois.sort(key=lambda x: x[0])
        visible_pois = visible_pois[: self.MAX_VISIBLE_POIS]

        for distance, screen_x, screen_y, callsign, poi in visible_pois:
            color = self._get_poi_color(poi.get("type", ""))
            self._draw_poi_marker(frame, screen_x, screen_y, color)
            self._draw_poi_label(frame, screen_x, screen_y, callsign, distance, color)

        return frame

    def handle_key(self, key: int) -> bool:
        if key == ord("t"):
            self.toggle_visibility()
            print(f"TAK Overlay: {'ON' if self.visible else 'OFF'}")
            return True
        return False
