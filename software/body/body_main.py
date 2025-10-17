#!/usr/bin/env python3
"""
WARLOCK Body-Mounted Unit (BMU) Main Entry Point

This unit handles:
- GPS positioning (primary)
- Radio communications (SA818)
- Mesh networking (WiFi + LoRa)
- SIGINT (RF scanning, WiFi CSI)
- ATAK integration
- Data aggregation and distribution to HMU(s)
"""

import logging
import time
import threading
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from body.core.network_server import BMUNetworkServer
from body.core.gps_simulator import GPSSimulator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class BMUApplication:
    """Body-Mounted Unit application."""

    def __init__(self, source_id: str = "WARLOCK-001-BMU"):
        """Initialize BMU application.

        Args:
            source_id: Unique identifier for this BMU
        """
        self.source_id = source_id
        self.running = False

        self.network_server = None
        self.gps = None

    def initialize(self):
        """Initialize all BMU components."""
        logger.info("=" * 60)
        logger.info("WARLOCK BODY-MOUNTED UNIT")
        logger.info("=" * 60)

        logger.info("Initializing GPS...")
        self.gps = GPSSimulator()

        logger.info("Starting network server...")
        self.network_server = BMUNetworkServer(source_id=self.source_id)
        self.network_server.start()

        logger.info("=" * 60)
        logger.info("BMU ACTIVE - Waiting for HMU connections")
        logger.info("=" * 60)

    def run(self):
        """Main application loop."""
        self.running = True

        gps_thread = threading.Thread(target=self._gps_broadcast_loop, daemon=True)
        gps_thread.start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Interrupted by user")

    def _gps_broadcast_loop(self):
        """Broadcast GPS updates to connected HMUs."""
        while self.running:
            position = self.gps.get_position()

            if self.network_server and self.network_server.has_clients():
                self.network_server.broadcast_gps(position)

            time.sleep(0.1)

    def cleanup(self):
        """Cleanup resources."""
        logger.info("Shutting down...")
        self.running = False

        if self.network_server:
            self.network_server.stop()

        logger.info("=" * 60)
        logger.info("BMU Shutdown Complete")
        logger.info("=" * 60)


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='WARLOCK Body-Mounted Unit')
    parser.add_argument('--id', type=str, default='WARLOCK-001-BMU', help='BMU source ID')
    args = parser.parse_args()

    app = BMUApplication(source_id=args.id)

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
