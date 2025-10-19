#!/usr/bin/env python3
"""Circular mini-map with terrain overlay and friendly unit markers."""

import math
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from common.plugin_base import HUDContext, HUDPlugin, PluginConfig, PluginMetadata, PluginPosition


@dataclass
class MapTile:
    """Represents a map tile."""

    zoom: int
    x: int
    y: int
    image: Optional[np.ndarray] = None


class TerrainMapCache:
    """Manages downloading and caching of map tiles."""

    def __init__(self, cache_dir: str = "cache/map_tiles"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.tile_servers = [
            "https://a.tile.opentopomap.org",
            "https://b.tile.opentopomap.org",
            "https://c.tile.opentopomap.org",
        ]
        self.server_index = 0

        self.last_request_time = 0
        self.min_request_interval = 0.1

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "ProjectWARLOCK/0.1 (Tactical HUD System)"})

    def _lat_lon_to_tile(self, lat: float, lon: float, zoom: int) -> Tuple[int, int]:
        latitude_radians = math.radians(lat)
        tiles_per_edge = 2.0**zoom
        tile_x = int((lon + 180.0) / 360.0 * tiles_per_edge)
        tile_y = int((1.0 - math.asinh(math.tan(latitude_radians)) / math.pi) / 2.0 * tiles_per_edge)
        return tile_x, tile_y

    def _tile_to_lat_lon(self, x: int, y: int, zoom: int) -> Tuple[float, float]:
        tiles_per_edge = 2.0**zoom
        longitude = x / tiles_per_edge * 360.0 - 180.0
        latitude_radians = math.atan(math.sinh(math.pi * (1 - 2 * y / tiles_per_edge)))
        latitude = math.degrees(latitude_radians)
        return latitude, longitude

    def _get_cache_path(self, zoom: int, x: int, y: int) -> Path:
        return self.cache_dir / f"z{zoom}_x{x}_y{y}.png"

    def _download_tile(self, zoom: int, x: int, y: int) -> Optional[np.ndarray]:
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        if time_since_last_request < self.min_request_interval:
            time.sleep(self.min_request_interval - time_since_last_request)

        server = self.tile_servers[self.server_index]
        self.server_index = (self.server_index + 1) % len(self.tile_servers)

        url = f"{server}/{zoom}/{x}/{y}.png"

        try:
            response = self.session.get(url, timeout=5)
            self.last_request_time = time.time()

            if response.status_code == 200:
                image_array = np.frombuffer(response.content, dtype=np.uint8)
                image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

                if image is not None:
                    cache_path = self._get_cache_path(zoom, x, y)
                    cv2.imwrite(str(cache_path), image)
                    return image
        except Exception:
            pass

        return None

    def get_tile(self, zoom: int, x: int, y: int) -> Optional[np.ndarray]:
        cache_path = self._get_cache_path(zoom, x, y)
        if cache_path.exists():
            image = cv2.imread(str(cache_path))
            if image is not None:
                return image

        return self._download_tile(zoom, x, y)

    def get_map_region(
        self, lat: float, lon: float, zoom: int, width_pixels: int, height_pixels: int
    ) -> Optional[np.ndarray]:
        """Get a map region centered on lat/lon."""
        center_x, center_y = self._lat_lon_to_tile(lat, lon, zoom)

        tile_size = 256
        tiles_wide = math.ceil(width_pixels / tile_size) + 1
        tiles_high = math.ceil(height_pixels / tile_size) + 1

        start_x = center_x - tiles_wide // 2
        start_y = center_y - tiles_high // 2

        tiles = []
        for ty in range(start_y, start_y + tiles_high):
            row = []
            for tx in range(start_x, start_x + tiles_wide):
                tile = self.get_tile(zoom, tx, ty)
                if tile is None:
                    tile = np.zeros((tile_size, tile_size, 3), dtype=np.uint8)
                row.append(tile)
            if row:
                tiles.append(np.hstack(row))

        if not tiles:
            return None

        composite = np.vstack(tiles)

        n = 2.0**zoom
        pixel_x = ((lon + 180.0) / 360.0 * n - start_x) * tile_size
        pixel_y = ((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n - start_y) * tile_size

        x1 = int(pixel_x - width_pixels // 2)
        y1 = int(pixel_y - height_pixels // 2)
        x2 = x1 + width_pixels
        y2 = y1 + height_pixels

        h, w = composite.shape[:2]
        x1 = max(0, min(x1, w - width_pixels))
        y1 = max(0, min(y1, h - height_pixels))
        x2 = x1 + width_pixels
        y2 = y1 + height_pixels

        if x2 > w or y2 > h:
            padded = np.zeros((height_pixels, width_pixels, 3), dtype=np.uint8)
            valid_h = min(height_pixels, h - y1)
            valid_w = min(width_pixels, w - x1)
            padded[:valid_h, :valid_w] = composite[y1 : y1 + valid_h, x1 : x1 + valid_w]
            return padded

        return composite[y1:y2, x1:x2]

    def close(self):
        """Close the HTTP session."""
        if self.session:
            self.session.close()
            self.session = None


class TerrainOverlay:
    """Provides terrain map overlay for HUD components."""

    def __init__(self, cache_dir: str = "cache/map_tiles"):
        """Initialize terrain overlay system."""
        self.cache = TerrainMapCache(cache_dir)
        self.current_map_unrotated: Optional[np.ndarray] = None
        self.last_update_time = 0
        self.update_interval = 1.0  # Update map every 1 second
        self.last_lat = None
        self.last_lon = None
        self.last_radius_meters = None

    def _calculate_zoom_for_radius(self, radius_meters: float) -> int:
        """Calculate appropriate zoom level for a given radius in meters."""
        if radius_meters <= 150:
            return 18
        elif radius_meters <= 300:
            return 17
        elif radius_meters <= 600:
            return 16
        elif radius_meters <= 1200:
            return 15
        elif radius_meters <= 2400:
            return 14
        elif radius_meters <= 5000:
            return 13
        else:
            return 12

    def get_overlay(
        self, lat: float, lon: float, heading: float, width: int, height: int, radius_meters: float = 300
    ) -> Optional[np.ndarray]:
        """Get rotated terrain overlay for current position."""
        current_time = time.time()

        needs_update = (
            self.current_map_unrotated is None
            or current_time - self.last_update_time > self.update_interval
            or self.last_lat is None
            or self.last_lon is None
            or abs(lat - self.last_lat) > 0.0001
            or abs(lon - self.last_lon) > 0.0001
            or self.last_radius_meters != radius_meters
        )

        if needs_update:
            zoom_level = self._calculate_zoom_for_radius(radius_meters)
            fetch_size = max(width, height) * 3

            self.current_map_unrotated = self.cache.get_map_region(lat, lon, zoom_level, fetch_size, fetch_size)
            self.last_update_time = current_time
            self.last_lat = lat
            self.last_lon = lon
            self.last_radius_meters = radius_meters

        if self.current_map_unrotated is None:
            return None

        h, w = self.current_map_unrotated.shape[:2]
        center = (w // 2, h // 2)

        # Note: heading increases clockwise (0°=N, 90°=E, 180°=S, 270°=W)
        # We want the map to rotate so the player's forward direction points up
        # cv2 rotates positive angles counterclockwise, so we use +heading to rotate clockwise
        rotation_matrix = cv2.getRotationMatrix2D(center, heading, 1.0)
        rotated = cv2.warpAffine(
            self.current_map_unrotated,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=(0, 0, 0),
        )

        x1 = (w - width) // 2
        y1 = (h - height) // 2
        x2 = x1 + width
        y2 = y1 + height

        x1 = max(0, x1)
        y1 = max(0, y1)
        x2 = min(w, x2)
        y2 = min(h, y2)

        cropped = rotated[y1:y2, x1:x2]

        if cropped.shape[:2] != (height, width):
            result = np.zeros((height, width, 3), dtype=np.uint8)
            h_crop, w_crop = cropped.shape[:2]
            h_use = min(h_crop, height)
            w_use = min(w_crop, width)
            result[:h_use, :w_use] = cropped[:h_use, :w_use]
            return result

        return cropped

    def close(self):
        """Close resources."""
        if self.cache:
            self.cache.close()


# ===== MINI-MAP PLUGIN =====


class MiniMapPlugin(HUDPlugin):
    """
    Circular mini-map at bottom left.

    Shows:
    - Topographical terrain map overlay (if enabled)
    - Concentric distance rings
    - Friendly unit markers (rotating with heading)
    - Player marker at center
    - Range indicator
    """

    METADATA = PluginMetadata(
        name="Mini-Map",
        version="1.0.0",
        author="Project WARLOCK Team",
        description="Circular mini-map with terrain overlay and friendly unit positioning",
        dependencies=[],
        provides=[],
        consumes=["border_padding"],
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self.player_pos: Optional[dict] = None
        self.friendly_units: List[dict] = []
        self.zoom_level = self.get_setting("zoom_level", 300)
        self.show_terrain = self.get_setting("show_terrain", True)

        if self.show_terrain:
            self.terrain = TerrainOverlay()
        else:
            self.terrain = None

        self.tracker_size = 0
        self.radius = 0

        self.primary_color = (220, 220, 210)
        self.secondary_color = (180, 180, 170)
        self.bg_color = (40, 30, 20)
        self.ring_color = (140, 140, 130)
        self.friendly_color = (255, 200, 100)

    def initialize(self) -> bool:
        """Initialize mini-map plugin."""
        self.tracker_size = int(self.context.frame_width * 0.15)
        self.radius = self.tracker_size // 2 - 10

        self.config.position = PluginPosition.CUSTOM

        return True

    def update(self, delta_time: float):
        """Update mini-map state from context."""
        if "player_position" in self.context.state:
            self.player_pos = self.context.state["player_position"]

        if "friendly_units" in self.context.state:
            self.friendly_units = self.context.state["friendly_units"]

    def _get_border_padding_data(self) -> dict:
        """Get current border padding values (soft dependency)."""
        return self.get_data("border_padding", {"padding_left": 0, "padding_bottom": 0})

    def _lat_lon_to_meters(self, lat1: float, lon1: float, lat2: float, lon2: float) -> Tuple[float, float]:
        """Convert lat/lon difference to meters."""
        lat_diff = lat2 - lat1
        lon_diff = lon2 - lon1
        y_meters = lat_diff * 111111
        x_meters = lon_diff * 111111 * math.cos(math.radians(lat1))
        return x_meters, y_meters

    def _meters_to_pixels(self, x_meters: float, y_meters: float) -> Tuple[int, int]:
        """Convert meter coordinates to pixel coordinates."""
        scale = self.radius / self.zoom_level
        x_pixels = int(x_meters * scale)
        y_pixels = int(-y_meters * scale)
        return x_pixels, y_pixels

    def render(self, frame: np.ndarray) -> np.ndarray:
        """Render circular mini-map with terrain overlay."""
        if not self.visible or self.player_pos is None:
            return frame

        border_padding = self._get_border_padding_data()
        padding_left = border_padding.get("padding_left", 0)
        padding_bottom = border_padding.get("padding_bottom", 0)

        x = padding_left + 20
        y = self.context.frame_height - padding_bottom - self.tracker_size - 20

        center_x = x + self.tracker_size // 2
        center_y = y + self.tracker_size // 2

        terrain_img = None
        if self.show_terrain and self.terrain is not None:
            try:
                terrain_img = self.terrain.get_overlay(
                    self.player_pos.get("latitude", 0),
                    self.player_pos.get("longitude", 0),
                    self.player_pos.get("heading", 0),
                    self.tracker_size,
                    self.tracker_size,
                    radius_meters=self.zoom_level,
                )
            except Exception as e:
                print(f"Warning: Failed to get terrain overlay: {e}")

        mask = np.zeros((self.tracker_size, self.tracker_size), dtype=np.uint8)
        cv2.circle(mask, (self.tracker_size // 2, self.tracker_size // 2), self.radius, 255, -1)

        if terrain_img is not None and terrain_img.shape[:2] == (self.tracker_size, self.tracker_size):
            terrain_masked = cv2.bitwise_and(terrain_img, terrain_img, mask=mask)

            terrain_masked = cv2.addWeighted(terrain_masked, 0.4, np.zeros_like(terrain_masked), 0, 0)

            roi_y1, roi_y2 = y, y + self.tracker_size
            roi_x1, roi_x2 = x, x + self.tracker_size

            if roi_y2 <= frame.shape[0] and roi_x2 <= frame.shape[1] and roi_y1 >= 0 and roi_x1 >= 0:
                frame_roi = frame[roi_y1:roi_y2, roi_x1:roi_x2].copy()
                frame_roi[mask > 0] = terrain_masked[mask > 0]
                frame[roi_y1:roi_y2, roi_x1:roi_x2] = frame_roi
        else:
            overlay = frame.copy()
            cv2.circle(overlay, (center_x, center_y), self.radius + 5, self.bg_color, -1, cv2.LINE_AA)
            cv2.addWeighted(overlay, 0.5, frame, 0.5, 0, frame)

        cv2.circle(frame, (center_x, center_y), self.radius + 5, self.primary_color, 2, cv2.LINE_AA)

        for i in range(1, 4):
            ring_radius = int((self.radius / 3) * i)
            cv2.circle(frame, (center_x, center_y), ring_radius, self.ring_color, 1, cv2.LINE_AA)

        for unit in self.friendly_units:
            lat = unit.get("latitude")
            lon = unit.get("longitude")
            if lat is None or lon is None:
                continue

            x_meters, y_meters = self._lat_lon_to_meters(
                self.player_pos.get("latitude", 0), self.player_pos.get("longitude", 0), lat, lon
            )

            heading_rad = math.radians(self.player_pos.get("heading", 0))
            cos_h = math.cos(heading_rad)
            sin_h = math.sin(heading_rad)
            rotated_x = x_meters * cos_h - y_meters * sin_h
            rotated_y = x_meters * sin_h + y_meters * cos_h

            px, py = self._meters_to_pixels(rotated_x, rotated_y)
            marker_x = center_x + px
            marker_y = center_y + py

            dist_from_center = math.sqrt(px**2 + py**2)
            if dist_from_center <= self.radius:
                cv2.circle(frame, (marker_x, marker_y), 4, self.friendly_color, -1, cv2.LINE_AA)
                cv2.circle(frame, (marker_x, marker_y), 5, self.friendly_color, 1, cv2.LINE_AA)

        player_size = 6
        pts = np.array(
            [
                [center_x, center_y - player_size],
                [center_x - player_size // 2, center_y + player_size // 2],
                [center_x + player_size // 2, center_y + player_size // 2],
            ],
            np.int32,
        )
        cv2.fillPoly(frame, [pts], self.primary_color, cv2.LINE_AA)

        range_text = f"{int(self.zoom_level)}m"
        cv2.putText(
            frame,
            range_text,
            (x + 5, y + self.tracker_size - 5),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.35,
            self.primary_color,
            1,
            cv2.LINE_AA,
        )

        return frame

    def cleanup(self):
        """Cleanup resources."""
        if self.terrain:
            self.terrain.close()
            self.terrain = None

    def handle_key(self, key: int) -> bool:
        """Handle keyboard input."""
        if key == ord("m"):
            self.toggle_visibility()
            print(f"Mini-Map: {'ON' if self.visible else 'OFF'}")
            return True
        elif key == ord("t"):
            self.show_terrain = not self.show_terrain
            print(f"Terrain overlay: {'ON' if self.show_terrain else 'OFF'}")
            return True
        elif key == ord("+") or key == ord("="):
            self.zoom_level = max(50, self.zoom_level - 50)
            print(f"Map zoom: ±{self.zoom_level}m")
            return True
        elif key == ord("-") or key == ord("_"):
            self.zoom_level = min(2000, self.zoom_level + 50)
            print(f"Map zoom: ±{self.zoom_level}m")
            return True
        return False
