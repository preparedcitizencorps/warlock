#!/usr/bin/env python3
"""
WARLOCK - Wearable Augmented Reality & Linked Operational Combat Kit

Helmet-mounted AR system with:
- Dual low-light cameras + thermal imaging
- AI object detection (YOLO on Hailo)
- TAK integration for waypoint overlay
- HUD rendering and display

Display Modes:
- X11 mode (default): Uses cv2.imshow() - requires desktop or X11 forwarding
- DRM mode: Direct display via DRM/KMS - headless operation without X11
  Enable with: WARLOCK_USE_DRM=1 or --use-drm flag
"""

import logging
import os
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config_loader import create_plugin_config, load_config
from common.input_manager import InputManager
from common.plugin_base import HUDContext
from core.camera_controller import CameraController
from core.tak_client import TAKClient

from hud.plugin_manager import PluginManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class WarlockApplication:
    """WARLOCK application."""

    DEFAULT_FRAME_WIDTH = 1280
    DEFAULT_FRAME_HEIGHT = 720

    def __init__(self, config_path: str = None, use_drm: bool = False):
        """Initialize WARLOCK application.

        Args:
            config_path: Path to config.yaml
            use_drm: Use DRM/KMS display (headless) instead of X11/cv2.imshow
        """
        self.config_path = config_path or str(Path(__file__).parent / "config.yaml")
        self.use_drm = use_drm

        self.context = None
        self.plugin_manager = None
        self.camera = None
        self.input_manager = None

        self.display = None
        self.keyboard = None
        self.tak_client = None

        self.show_help = False
        self.running = False

    def initialize(self):
        """Initialize all WARLOCK components."""
        logger.info("=" * 60)
        logger.info("WARLOCK")
        logger.info("=" * 60)

        logger.info("Loading configuration...")
        config = load_config(self.config_path)

        self.context = HUDContext(self.DEFAULT_FRAME_WIDTH, self.DEFAULT_FRAME_HEIGHT)

        script_dir = Path(__file__).parent
        plugin_dir = str(script_dir / "hud" / "plugins")
        self.plugin_manager = PluginManager(self.context, plugin_dir=plugin_dir)
        self.context.state["plugin_manager"] = self.plugin_manager

        logger.info("Discovering plugins...")
        self.plugin_manager.discover_plugins()

        logger.info("Initializing input system...")
        self.input_manager = self._initialize_input_manager(config)
        self.context.state["input_manager"] = self.input_manager

        logger.info("Loading plugins...")
        plugin_configs, visibility_map = self._prepare_plugin_configs(config)

        try:
            loaded_plugins = self.plugin_manager.load_plugins_with_dependencies(plugin_configs)
            self._apply_visibility_settings(loaded_plugins, visibility_map)
            logger.info(f"Loaded {len(loaded_plugins)} plugins")
        except ValueError as e:
            logger.error(f"Plugin loading failed: {e}")
            raise

        logger.info("Detecting and initializing camera...")
        from core.camera_detection import initialize_camera

        try:
            cap, camera_info = initialize_camera(
                width=self.DEFAULT_FRAME_WIDTH, height=self.DEFAULT_FRAME_HEIGHT, prefer_csi=True
            )
            logger.info(f"Camera initialized: {camera_info}")
        except RuntimeError as e:
            logger.error(f"Camera initialization failed: {e}")
            raise

        self.camera = CameraController(cap)
        self.context.state["camera_handle"] = self.camera

        if self.use_drm:
            logger.info("Initializing DRM/KMS display (headless mode)...")
            try:
                from core.drm_display import DRMDisplay
                from core.evdev_input import EvdevKeyboard

                self.display = DRMDisplay(self.DEFAULT_FRAME_WIDTH, self.DEFAULT_FRAME_HEIGHT)
                self.keyboard = EvdevKeyboard(auto_grab=True)
                logger.info("DRM display mode active")
            except Exception as e:
                logger.error(f"Failed to initialize DRM display: {e}")
                logger.error("Falling back to X11 mode (cv2.imshow)")
                self.use_drm = False
        else:
            logger.info("Using X11 display mode (cv2.imshow)")

        self._initialize_tak_client(config)

        logger.info("=" * 60)
        logger.info("WARLOCK ACTIVE - Press 'H' for help, 'Q' to quit")
        logger.info("=" * 60)

    def _initialize_tak_client(self, config: dict):
        """Initialize TAK server connection for blue-force tracking and POI display."""
        tak_config = config.get("tak", {})

        if not tak_config.get("enabled", False):
            logger.info("TAK integration disabled - running standalone")
            self._setup_simulated_position()
            return

        logger.info("Initializing TAK client...")

        try:
            self.tak_client = TAKClient(
                server_host=tak_config.get("server_host", "192.168.1.100"),
                server_port=tak_config.get("server_port", 8087),
                callsign=tak_config.get("callsign", "WARLOCK-001"),
                team_name=tak_config.get("team_name", "Cyan"),
                team_role=tak_config.get("team_role", "Team Member"),
            )

            if tak_config.get("position_update_interval"):
                self.tak_client.POSITION_UPDATE_INTERVAL = tak_config["position_update_interval"]

            if self.tak_client.connect():
                logger.info(f"Connected to TAK server at {tak_config.get('server_host')}")
                self.context.state["tak_client"] = self.tak_client
                self._setup_simulated_position()
            else:
                logger.warning("Failed to connect to TAK server - running standalone")
                self._setup_simulated_position()

        except Exception as e:
            logger.error(f"TAK client initialization failed: {e}")
            self._setup_simulated_position()

    def _setup_simulated_position(self):
        """Setup simulated GPS position (Schriever Space Force Base area)."""
        self.context.state["player_position"] = {
            "latitude": 38.8339,
            "longitude": -104.8214,
            "altitude": 1839,
            "heading": 0.0,
        }

    def _initialize_input_manager(self, config: dict) -> InputManager:
        """Initialize InputManager with keybinds from config."""
        input_manager = InputManager()

        keybinds_config = config.get("keybinds", {})

        system_binds = keybinds_config.get("system", {})
        if system_binds:
            input_manager.register_keybind(system_binds.get("quit", "q"), "Quit", "system")
            input_manager.register_keybind(system_binds.get("help", "h"), "Toggle help", "system")
            input_manager.register_keybind(system_binds.get("plugin_panel", "p"), "Plugin control panel", "system")

        return input_manager

    def _prepare_plugin_configs(self, config: dict) -> tuple:
        """Prepare plugin configurations from config file."""
        plugin_configs = []
        visibility_map = {}

        for plugin_data in config.get("plugins", []):
            if not plugin_data.get("enabled", True):
                continue

            plugin_name = plugin_data["name"]
            plugin_config = create_plugin_config(plugin_data)
            plugin_configs.append((plugin_name, plugin_config))
            visibility_map[plugin_name] = plugin_data.get("visible", True)

        return plugin_configs, visibility_map

    def _apply_visibility_settings(self, loaded_plugins: list, visibility_map: dict):
        """Apply visibility settings to loaded plugins."""
        for plugin in loaded_plugins:
            plugin_name = plugin.__class__.__name__
            if plugin_name in visibility_map:
                plugin.visible = visibility_map[plugin_name]

    def run(self):
        """Main application loop."""
        self.running = True

        while self.running:
            ret, frame = self.camera.read_frame()
            if not ret:
                logger.error("Failed to grab frame")
                break

            if self.tak_client and self.tak_client.connected:
                pos = self.context.state.get("player_position", {})
                if pos:
                    self.tak_client.update_position(
                        latitude=pos.get("latitude", 0.0),
                        longitude=pos.get("longitude", 0.0),
                        altitude=pos.get("altitude", 0.0),
                        heading=pos.get("heading", 0.0),
                    )

            try:
                self.plugin_manager.update()
            except Exception as e:
                logger.error(f"Plugin update error: {e}", exc_info=True)

            try:
                frame = self.plugin_manager.render(frame)
            except Exception as e:
                logger.error(f"Plugin render error: {e}", exc_info=True)

            if self.use_drm:
                self.display.show(frame)
            else:
                cv2.imshow("WARLOCK", frame)

            if self.use_drm:
                key = self.keyboard.read_key(timeout=0.001)
                if key is None:
                    key = 0xFF
            else:
                key = cv2.waitKey(1) & 0xFF

            key_handled = self.plugin_manager.handle_key(key)

            if not key_handled:
                self._handle_key(key)

        logger.info("Shutting down...")

    def _handle_key(self, key: int):
        """Handle keyboard input."""
        if key == ord("q"):
            self.running = False
        elif key == ord("h"):
            self.show_help = not self.show_help
            logger.info(f"Help overlay: {'ON' if self.show_help else 'OFF'}")

    def cleanup(self):
        """Cleanup resources."""
        logger.info("Cleaning up...")

        if self.tak_client:
            self.tak_client.disconnect()

        if self.plugin_manager:
            self.plugin_manager.cleanup()

        if self.camera:
            self.camera.release()

        if self.use_drm:
            if self.display:
                self.display.cleanup()
            if self.keyboard:
                self.keyboard.cleanup()
        else:
            cv2.destroyAllWindows()

        logger.info("=" * 60)
        logger.info("WARLOCK Shutdown Complete")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="WARLOCK - Wearable Augmented Reality & Linked Operational Combat Kit")
    parser.add_argument("--config", type=str, help="Path to config.yaml")
    parser.add_argument(
        "--use-drm", action="store_true", help="Use DRM/KMS display (headless mode) instead of X11/cv2.imshow"
    )
    args = parser.parse_args()

    use_drm = args.use_drm or os.environ.get("WARLOCK_USE_DRM", "0") == "1"

    if use_drm:
        logger.info("DRM mode requested - will run in headless mode")

    app = WarlockApplication(config_path=args.config, use_drm=use_drm)

    try:
        app.initialize()
        app.run()
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
    finally:
        app.cleanup()


if __name__ == "__main__":
    main()
