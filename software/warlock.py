#!/usr/bin/env python3

import cv2
import time
import numpy as np
from pathlib import Path
import math
import platform

from hud import HUDContext, PluginManager
from hud.config_loader import load_config, create_plugin_config
from core import CameraController, InputManager


class ArrowKeys:
    """Platform-independent arrow key detection for OpenCV."""

    def __init__(self):
        self.system = platform.system()

        if self.system == 'Windows':
            self.UP = 2490368
            self.DOWN = 2621440
            self.LEFT = 2424832
            self.RIGHT = 2555904
        else:
            self.UP = 82
            self.DOWN = 84
            self.LEFT = 81
            self.RIGHT = 83

    def is_up(self, key: int) -> bool:
        return key == self.UP or key == ord('w')

    def is_down(self, key: int) -> bool:
        return key == self.DOWN or key == ord('s')

    def is_left(self, key: int) -> bool:
        return key == self.LEFT or key == ord('a')

    def is_right(self, key: int) -> bool:
        return key == self.RIGHT or key == ord('d')


ARROW_KEYS = ArrowKeys()


class GPSSimulator:
    METERS_PER_DEGREE_LATITUDE = 111111
    MINIMUM_SAFE_COS_LAT = 0.01
    SAFE_LATITUDE_RANGE = (-89.9, 89.9)

    def __init__(self, start_lat: float = 38.8339, start_lon: float = -104.8214):
        self.latitude = start_lat
        self.longitude = start_lon
        self.heading = 0.0
        self.altitude = 100.0
        self.speed = 1.0
        self.turn_rate = 2.0

    def update(self, forward: float = 0, turn: float = 0):
        self._update_heading(turn)
        if forward != 0:
            self._update_position(forward)

    def _update_heading(self, turn: float):
        self.heading += turn * self.turn_rate
        self.heading = self.heading % 360

    def _update_position(self, forward: float):
        heading_rad = math.radians(self.heading)
        distance = forward * self.speed

        latitude_delta = self._calculate_latitude_delta(heading_rad, distance)
        longitude_delta = self._calculate_longitude_delta(heading_rad, distance)

        self.latitude += latitude_delta
        self.longitude += longitude_delta
        self._clamp_latitude_to_safe_range()

    def _calculate_latitude_delta(self, heading_rad: float, distance: float) -> float:
        distance_meters_north = distance * math.cos(heading_rad)
        return distance_meters_north / self.METERS_PER_DEGREE_LATITUDE

    def _calculate_longitude_delta(self, heading_rad: float, distance: float) -> float:
        clamped_lat = max(self.SAFE_LATITUDE_RANGE[0], min(self.SAFE_LATITUDE_RANGE[1], self.latitude))
        cos_lat = math.cos(math.radians(clamped_lat))

        if abs(cos_lat) < self.MINIMUM_SAFE_COS_LAT:
            cos_lat = math.copysign(self.MINIMUM_SAFE_COS_LAT, cos_lat)

        distance_meters_east = distance * math.sin(heading_rad)
        return distance_meters_east / (self.METERS_PER_DEGREE_LATITUDE * cos_lat)

    def _clamp_latitude_to_safe_range(self):
        self.latitude = max(self.SAFE_LATITUDE_RANGE[0], min(self.SAFE_LATITUDE_RANGE[1], self.latitude))

    def get_position(self) -> dict:
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'heading': self.heading,
            'altitude': self.altitude
        }


class TeamSimulator:
    METERS_PER_DEGREE_LATITUDE = 111111
    MINIMUM_SAFE_COS_LAT = 0.01

    def __init__(self, player_lat: float, player_lon: float):
        self.units = []
        self._create_test_units(player_lat, player_lon)

    def _offset_position(self, base_lat: float, base_lon: float,
                        bearing: float, distance: float) -> tuple:
        latitude_offset = (distance * math.cos(math.radians(bearing))) / self.METERS_PER_DEGREE_LATITUDE

        cos_lat = math.cos(math.radians(base_lat))
        if abs(cos_lat) < self.MINIMUM_SAFE_COS_LAT:
            cos_lat = math.copysign(self.MINIMUM_SAFE_COS_LAT, cos_lat)

        longitude_offset = (distance * math.sin(math.radians(bearing))) / (self.METERS_PER_DEGREE_LATITUDE * cos_lat)
        return base_lat + latitude_offset, base_lon + longitude_offset

    def _create_test_units(self, player_lat: float, player_lon: float):
        units_data = [
            (45, 200, "ALPHA-1"),
            (315, 350, "BRAVO-1"),
            (90, 150, "CHARLIE-1"),
            (225, 400, "DELTA-1"),
        ]

        for bearing, distance, callsign in units_data:
            lat, lon = self._offset_position(player_lat, player_lon, bearing, distance)
            self.units.append({
                'id': callsign.lower(),
                'bearing': bearing,
                'distance': distance,
                'latitude': lat,
                'longitude': lon,
                'callsign': callsign,
                'status': 'active'
            })

    def update_bearings(self, player_pos: dict):
        for unit in self.units:
            self._recalculate_unit_bearing_and_distance(unit, player_pos)

    def _recalculate_unit_bearing_and_distance(self, unit: dict, player_pos: dict):
        latitude_delta = unit['latitude'] - player_pos['latitude']
        longitude_delta = unit['longitude'] - player_pos['longitude']

        y_meters = latitude_delta * self.METERS_PER_DEGREE_LATITUDE
        x_meters = longitude_delta * self.METERS_PER_DEGREE_LATITUDE * math.cos(math.radians(player_pos['latitude']))

        bearing_radians = math.atan2(x_meters, y_meters)
        bearing_degrees = math.degrees(bearing_radians)
        unit['bearing'] = (bearing_degrees + 360) % 360
        unit['distance'] = math.sqrt(x_meters**2 + y_meters**2)

    def get_units(self) -> list:
        return self.units


def draw_help_overlay(frame: np.ndarray, plugins_info: list) -> np.ndarray:
    OVERLAY_WIDTH = 500
    OVERLAY_HEIGHT = 400
    OVERLAY_ALPHA = 0.7
    LINE_HEIGHT = 22
    VERTICAL_PADDING = 20

    overlay = frame.copy()
    h, w = frame.shape[:2]

    center_x = w // 2
    center_y = h // 2
    overlay_x1 = center_x - OVERLAY_WIDTH // 2
    overlay_y1 = center_y - OVERLAY_HEIGHT // 2
    overlay_x2 = center_x + OVERLAY_WIDTH // 2
    overlay_y2 = center_y + OVERLAY_HEIGHT // 2

    cv2.rectangle(overlay, (overlay_x1, overlay_y1), (overlay_x2, overlay_y2), (0, 0, 0), -1)
    cv2.addWeighted(overlay, OVERLAY_ALPHA, frame, 1 - OVERLAY_ALPHA, 0, frame)

    help_text = _build_help_text(plugins_info)
    _render_help_text(frame, help_text, w // 2, center_y - OVERLAY_HEIGHT // 2 + VERTICAL_PADDING, LINE_HEIGHT)

    return frame


def draw_keybinds_overlay(frame: np.ndarray, input_manager: InputManager) -> np.ndarray:
    OVERLAY_WIDTH = 550
    OVERLAY_HEIGHT = 500
    OVERLAY_ALPHA = 0.7
    LINE_HEIGHT = 20
    VERTICAL_PADDING = 20
    COLUMN_PADDING = 250

    overlay = frame.copy()
    h, w = frame.shape[:2]

    center_x = w // 2
    center_y = h // 2
    overlay_x1 = center_x - OVERLAY_WIDTH // 2
    overlay_y1 = center_y - OVERLAY_HEIGHT // 2
    overlay_x2 = center_x + OVERLAY_WIDTH // 2
    overlay_y2 = center_y + OVERLAY_HEIGHT // 2

    cv2.rectangle(overlay, (overlay_x1, overlay_y1), (overlay_x2, overlay_y2), (0, 0, 0), -1)
    cv2.addWeighted(overlay, OVERLAY_ALPHA, frame, 1 - OVERLAY_ALPHA, 0, frame)

    keybinds = _build_keybinds_from_input_manager(input_manager)
    _render_keybinds_text(frame, keybinds, overlay_x1 + 20,
                         center_y - OVERLAY_HEIGHT // 2 + VERTICAL_PADDING,
                         LINE_HEIGHT, COLUMN_PADDING)

    return frame


def _build_help_text(plugins_info: list) -> list:
    help_text = [
        "WARLOCK TACTICAL HUD",
        "",
        "Q - Quit",
        "S - Save frame",
        "H - Toggle this help",
        "P - Plugin Control Panel",
        "Arrow Keys - Move/Turn",
        "",
        "--- Active Plugins ---",
    ]

    for plugin in plugins_info:
        if plugin['enabled']:
            status = "ON" if plugin['visible'] else "OFF"
            help_text.append(f"{plugin['name']}: {status}")

    help_text.extend([
        "",
        "See hud_config.yaml to modify plugins"
    ])

    return help_text


def _render_help_text(frame: np.ndarray, help_text: list, center_x: int, start_y: int, line_height: int):
    TITLE_FONT_SCALE = 0.6
    BODY_FONT_SCALE = 0.45
    TITLE_THICKNESS = 2
    BODY_THICKNESS = 1
    TITLE_COLOR = (220, 220, 210)
    BODY_COLOR = (180, 180, 170)

    for i, text in enumerate(help_text):
        is_title = (i == 0)
        font_scale = TITLE_FONT_SCALE if is_title else BODY_FONT_SCALE
        thickness = TITLE_THICKNESS if is_title else BODY_THICKNESS
        color = TITLE_COLOR if is_title else BODY_COLOR

        text_size = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)[0]
        text_x = center_x - text_size[0] // 2
        text_y = start_y + i * line_height

        cv2.putText(frame, text, (text_x, text_y),
                   cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, thickness)


def _build_keybinds_from_input_manager(input_manager: InputManager) -> list:
    keybinds = [("KEYBINDS", None), ("", None)]

    categories = input_manager.get_keybinds_by_category()

    for category_name, bindings in categories:
        category_title = category_name.upper()
        keybinds.append((f"--- {category_title} ---", None))

        for binding in bindings:
            keybinds.append((binding.key.upper(), binding.description))

        keybinds.append(("", None))

    return keybinds


def _render_keybinds_text(frame: np.ndarray, keybinds: list, start_x: int,
                         start_y: int, line_height: int, column_padding: int):
    TITLE_FONT_SCALE = 0.6
    KEY_FONT_SCALE = 0.45
    DESC_FONT_SCALE = 0.4
    TITLE_THICKNESS = 2
    KEY_THICKNESS = 2
    DESC_THICKNESS = 1
    TITLE_COLOR = (220, 220, 210)
    KEY_COLOR = (100, 200, 255)
    DESC_COLOR = (180, 180, 170)
    CATEGORY_COLOR = (150, 150, 140)

    for i, (key, desc) in enumerate(keybinds):
        y_pos = start_y + i * line_height

        if desc is None:
            if key:
                if key.startswith("---"):
                    cv2.putText(frame, key, (start_x, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, KEY_FONT_SCALE,
                               CATEGORY_COLOR, KEY_THICKNESS)
                else:
                    text_size = cv2.getTextSize(key, cv2.FONT_HERSHEY_SIMPLEX,
                                               TITLE_FONT_SCALE, TITLE_THICKNESS)[0]
                    text_x = start_x + column_padding - text_size[0] // 2
                    cv2.putText(frame, key, (text_x, y_pos),
                               cv2.FONT_HERSHEY_SIMPLEX, TITLE_FONT_SCALE,
                               TITLE_COLOR, TITLE_THICKNESS)
        else:
            cv2.putText(frame, key, (start_x, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, KEY_FONT_SCALE,
                       KEY_COLOR, KEY_THICKNESS)

            cv2.putText(frame, desc, (start_x + 120, y_pos),
                       cv2.FONT_HERSHEY_SIMPLEX, DESC_FONT_SCALE,
                       DESC_COLOR, DESC_THICKNESS)


def _initialize_input_manager(config: dict) -> InputManager:
    """Initialize InputManager with keybinds from config."""
    input_manager = InputManager()

    keybinds_config = config.get('keybinds', {})

    system_binds = keybinds_config.get('system', {})
    if system_binds:
        input_manager.register_keybind(
            system_binds.get('quit', 'q'), 'Quit', 'system'
        )
        input_manager.register_keybind(
            system_binds.get('help', 'h'), 'Toggle help', 'system'
        )
        input_manager.register_keybind(
            system_binds.get('keybinds_panel', 'k'), 'Toggle keybinds', 'system'
        )
        input_manager.register_keybind(
            system_binds.get('save_frame', 's'), 'Save frame', 'system'
        )
        input_manager.register_keybind(
            system_binds.get('plugin_panel', 'p'), 'Plugin control panel', 'system'
        )

    yolo_binds = keybinds_config.get('yolo', {})
    if yolo_binds:
        input_manager.register_keybind(
            yolo_binds.get('toggle', 'y'), 'Toggle YOLO detection', 'yolo'
        )
        input_manager.register_keybind(
            yolo_binds.get('cycle_mode', 'v'), 'Cycle YOLO mode (seg/box/both)', 'yolo'
        )

    exposure_binds = keybinds_config.get('exposure', {})
    if exposure_binds:
        input_manager.register_keybind(
            exposure_binds.get('toggle', 'e'), 'Toggle auto-exposure', 'exposure'
        )
        input_manager.register_keybind(
            exposure_binds.get('toggle_stats', 'o'), 'Toggle exposure stats', 'exposure'
        )
        input_manager.register_keybind(
            exposure_binds.get('brightness_up', '+'), 'Increase target brightness', 'exposure'
        )
        input_manager.register_keybind(
            exposure_binds.get('brightness_down', '-'), 'Decrease target brightness', 'exposure'
        )

    display_binds = keybinds_config.get('display', {})
    if display_binds:
        input_manager.register_keybind(
            display_binds.get('toggle_fps', 'f'), 'Toggle FPS counter', 'display'
        )
        input_manager.register_keybind(
            display_binds.get('toggle_borders', 'b'), 'Toggle border padding', 'display'
        )
        input_manager.register_keybind(
            display_binds.get('padding_increase', ']'), 'Increase padding', 'display'
        )
        input_manager.register_keybind(
            display_binds.get('padding_decrease', '['), 'Decrease padding', 'display'
        )
        input_manager.register_keybind(
            display_binds.get('toggle_map', 'm'), 'Toggle mini-map', 'display'
        )

    movement_binds = keybinds_config.get('movement', {})
    if movement_binds:
        input_manager.register_keybind(
            movement_binds.get('forward', 'w'), 'Move forward', 'movement'
        )
        input_manager.register_keybind(
            movement_binds.get('backward', 's'), 'Move backward', 'movement'
        )
        input_manager.register_keybind(
            movement_binds.get('left', 'a'), 'Turn left', 'movement'
        )
        input_manager.register_keybind(
            movement_binds.get('right', 'd'), 'Turn right', 'movement'
        )

    return input_manager


def main():
    DEFAULT_FRAME_WIDTH = 1280
    DEFAULT_FRAME_HEIGHT = 720

    print("=" * 60)
    print("PROJECT WARLOCK - Tactical HUD System")
    print("=" * 60)

    context = HUDContext(DEFAULT_FRAME_WIDTH, DEFAULT_FRAME_HEIGHT)

    script_dir = Path(__file__).parent
    plugin_manager = PluginManager(context, plugin_dir=str(script_dir / "hud" / "plugins"))

    context.state['plugin_manager'] = plugin_manager

    print("\nDiscovering plugins...")
    plugin_manager.discover_plugins()

    print("\nLoading configuration...")
    config = load_config(str(script_dir / "hud_config.yaml"))

    print("\nInitializing input system...")
    input_manager = _initialize_input_manager(config)
    context.state['input_manager'] = input_manager

    print("\nLoading plugins...")

    plugin_configs, visibility_map = _prepare_plugin_configs(config)

    try:
        loaded_plugins = plugin_manager.load_plugins_with_dependencies(plugin_configs)
        _apply_visibility_settings(loaded_plugins, visibility_map)
    except ValueError as e:
        _display_circular_dependency_error(e)
        return

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, DEFAULT_FRAME_WIDTH)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, DEFAULT_FRAME_HEIGHT)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)

    print(f"Video resolution: {DEFAULT_FRAME_WIDTH}x{DEFAULT_FRAME_HEIGHT}")

    context.state['camera_handle'] = CameraController(cap)

    gps = GPSSimulator()
    team = TeamSimulator(gps.latitude, gps.longitude)

    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    print("\n" + "=" * 60)
    print("HUD ACTIVE - Press 'H' for help")
    print(f"Loaded {len(plugin_manager.plugins)} plugins")
    print("=" * 60 + "\n")

    show_help = False
    show_keybinds = False
    forward_move = 0
    turn_move = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame")
            break

        gps.update(forward=forward_move, turn=turn_move)
        player_pos = gps.get_position()
        team.update_bearings(player_pos)

        context.state['player_position'] = player_pos
        context.state['friendly_units'] = team.get_units()

        plugin_manager.update()
        frame = plugin_manager.render(frame)

        if show_help:
            frame = draw_help_overlay(frame, plugin_manager.list_plugins())

        if show_keybinds:
            frame = draw_keybinds_overlay(frame, input_manager)

        cv2.imshow('WARLOCK - Tactical HUD', frame)

        key = cv2.waitKey(1) & 0xFF

        forward_move = 0
        turn_move = 0

        key_handled = plugin_manager.handle_key(key)

        if not key_handled:
            show_help, show_keybinds, should_quit = _handle_system_keys(
                key, show_help, show_keybinds, frame, output_dir
            )
            forward_move, turn_move = _handle_movement_keys(key)

            if should_quit:
                break

    plugin_manager.cleanup()
    cap.release()
    cv2.destroyAllWindows()

    print("\n" + "=" * 60)
    print("WARLOCK Shutdown Complete")
    print("=" * 60)


def _prepare_plugin_configs(config: dict) -> tuple:
    plugin_configs = []
    visibility_map = {}

    for plugin_data in config.get('plugins', []):
        if not plugin_data.get('enabled', True):
            continue

        plugin_name = plugin_data['name']
        plugin_config = create_plugin_config(plugin_data)
        plugin_configs.append((plugin_name, plugin_config))
        visibility_map[plugin_name] = plugin_data.get('visible', True)

    return plugin_configs, visibility_map


def _apply_visibility_settings(loaded_plugins: list, visibility_map: dict):
    for plugin in loaded_plugins:
        plugin_name = plugin.__class__.__name__
        if plugin_name in visibility_map:
            plugin.visible = visibility_map[plugin_name]


def _display_circular_dependency_error(error: ValueError):
    print(f"\n{'='*60}")
    print(f"FATAL ERROR: Circular Dependency Detected")
    print(f"{'='*60}")
    print(f"\n{error}")
    print(f"\nHow to fix:")
    print(f"  1. Check your plugin dependencies in metadata")
    print(f"  2. Remove circular references (A depends on B, B depends on A)")
    print(f"  3. Consider using soft dependencies with get_data() instead")
    print(f"\n{'='*60}\n")


def _handle_system_keys(key: int, show_help: bool, show_keybinds: bool,
                       frame: np.ndarray, output_dir: Path) -> tuple:
    should_quit = False

    if key == ord('q'):
        should_quit = True
    elif key == ord('s'):
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = output_dir / f"hud_demo_{timestamp}.jpg"
        cv2.imwrite(str(filename), frame)
        print(f"Saved: {filename}")
    elif key == ord('h'):
        show_help = not show_help
    elif key == ord('k'):
        show_keybinds = not show_keybinds

    return show_help, show_keybinds, should_quit


def _handle_movement_keys(key: int) -> tuple:
    forward_move = 0
    turn_move = 0

    if ARROW_KEYS.is_up(key):
        forward_move = 1
    elif ARROW_KEYS.is_down(key):
        forward_move = -1
    elif ARROW_KEYS.is_left(key):
        turn_move = -1
    elif ARROW_KEYS.is_right(key):
        turn_move = 1

    return forward_move, turn_move


if __name__ == "__main__":
    main()
