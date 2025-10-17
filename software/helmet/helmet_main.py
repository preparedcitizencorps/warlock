#!/usr/bin/env python3
"""
WARLOCK Helmet-Mounted Unit (HMU) Main Entry Point

This unit handles:
- Visual sensing (camera input)
- AI object detection (YOLO on Hailo)
- HUD rendering and display
- Communication with Body-Mounted Unit (BMU) for GPS, team data, alerts
"""

import logging
import sys
import time
from pathlib import Path

import cv2

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.config_loader import create_plugin_config, load_config
from common.input_manager import InputManager
from common.plugin_base import HUDContext
from helmet.core.camera_controller import CameraController
from helmet.core.network_client import HMUNetworkClient
from helmet.hud.plugin_manager import PluginManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class HMUApplication:
    """Helmet-Mounted Unit application."""

    DEFAULT_FRAME_WIDTH = 1280
    DEFAULT_FRAME_HEIGHT = 720

    def __init__(self, config_path: str = None, network_enabled: bool = True):
        """Initialize HMU application.

        Args:
            config_path: Path to helmet_config.yaml
            network_enabled: Connect to BMU if True, standalone mode if False
        """
        self.config_path = config_path or str(Path(__file__).parent / "helmet_config.yaml")
        self.network_enabled = network_enabled

        self.context = None
        self.plugin_manager = None
        self.camera = None
        self.network_client = None
        self.input_manager = None

        self.show_help = False
        self.running = False

    def initialize(self):
        """Initialize all HMU components."""
        logger.info("=" * 60)
        logger.info("WARLOCK HELMET-MOUNTED UNIT")
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

        # Initialize camera
        logger.info("Initializing camera...")
        cap = cv2.VideoCapture(0)
        if not cap.isOpened():
            raise RuntimeError("Could not open camera")

        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.DEFAULT_FRAME_WIDTH)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.DEFAULT_FRAME_HEIGHT)
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        cap.set(cv2.CAP_PROP_FPS, 30)

        self.camera = CameraController(cap)
        self.context.state["camera_handle"] = self.camera

        if self.network_enabled:
            logger.info("Connecting to BMU...")
            bmu_config = config.get("network", {})
            bmu_host = bmu_config.get("bmu_host", "192.168.200.2")
            source_id = bmu_config.get("source_id", "WARLOCK-001-HMU")

            self.network_client = HMUNetworkClient(source_id=source_id, server_host=bmu_host)
            self.network_client.register_default_handlers()

            if self.network_client.connect():
                logger.info("Connected to BMU")
                self.context.state["network_client"] = self.network_client
            else:
                logger.warning("Failed to connect to BMU - running in standalone mode")
                self.network_enabled = False
        else:
            logger.info("Network disabled - running in standalone mode")
            self._setup_simulated_data()

        logger.info("=" * 60)
        logger.info("HMU ACTIVE - Press 'H' for help, 'Q' to quit")
        logger.info("=" * 60)

    def _setup_simulated_data(self):
        """Setup simulated GPS and team data for standalone mode."""
        self.context.state["player_position"] = {
            "latitude": 38.8339,
            "longitude": -104.8214,
            "altitude": 1839,
            "heading": 0.0,
        }

        self.context.state["friendly_units"] = [
            {
                "id": "alpha-1",
                "callsign": "ALPHA-1",
                "latitude": 38.8350,
                "longitude": -104.8200,
                "bearing": 45,
                "distance": 200,
                "status": "active",
            }
        ]

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

            if self.network_enabled and self.network_client:
                gps_pos = self.network_client.get_latest("gps_position")
                if gps_pos:
                    self.context.state["player_position"] = gps_pos

                team_units = self.network_client.get_latest("team_positions")
                if team_units:
                    self.context.state["friendly_units"] = team_units

                rf_alerts = self.network_client.get_latest("rf_alerts")
                wifi_alerts = self.network_client.get_latest("wifi_alerts")
                self.context.state["rf_alerts"] = rf_alerts or []
                self.context.state["wifi_alerts"] = wifi_alerts or []

            self.plugin_manager.update()

            frame = self.plugin_manager.render(frame)

            cv2.imshow("WARLOCK HMU", frame)

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

        if self.plugin_manager:
            self.plugin_manager.cleanup()

        if self.camera:
            self.camera.release()

        if self.network_client:
            self.network_client.stop()

        cv2.destroyAllWindows()

        logger.info("=" * 60)
        logger.info("HMU Shutdown Complete")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="WARLOCK Helmet-Mounted Unit")
    parser.add_argument("--config", type=str, help="Path to helmet_config.yaml")
    parser.add_argument("--standalone", action="store_true", help="Run without BMU connection")
    args = parser.parse_args()

    app = HMUApplication(config_path=args.config, network_enabled=not args.standalone)

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
