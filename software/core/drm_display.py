#!/usr/bin/env python3
"""
DRM/KMS Display Backend for WARLOCK HMU

Provides direct display output using Linux DRM/KMS subsystem for headless operation.
This enables true headless deployment without X11 or Wayland compositor overhead.

Usage:
    display = DRMDisplay(width=1280, height=720)
    display.show(frame)  # frame is BGR numpy array from OpenCV
    display.cleanup()

Requirements:
    - python3-kms++ (pykms) - sudo apt install python3-kms++
    - User in 'video' group - sudo usermod -a -G video $USER
    - Console mode (not desktop session) - DRM requires exclusive access
"""

import logging
import sys
from typing import Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger(__name__)


class DRMDisplay:
    """Direct DRM/KMS display output for OpenCV frames.

    This class provides a drop-in replacement for cv2.imshow() that renders
    directly to the display hardware using Linux DRM/KMS, bypassing X11/Wayland.

    Ideal for:
    - Headless AR displays (Rokid Max glasses)
    - Field deployment without desktop environment
    - Low-latency helmet-mounted displays
    """

    def __init__(self, width: int = 1280, height: int = 720, connector_name: Optional[str] = None):
        """Initialize DRM display.

        Args:
            width: Frame width (will resize frames to match)
            height: Frame height (will resize frames to match)
            connector_name: Specific connector (e.g., "HDMI-A-1"), None = auto-detect

        Raises:
            ImportError: If pykms is not installed
            RuntimeError: If DRM initialization fails
        """
        self.width = width
        self.height = height
        self.connector_name = connector_name

        self.card = None
        self.res = None
        self.conn = None
        self.crtc = None
        self.mode = None
        self.fb = None
        self.fb_array = None

        self._initialized = False

        try:
            import pykms

            self.pykms = pykms
        except ImportError as e:
            logger.error("pykms not found. Install with: sudo apt install python3-kms++")
            raise ImportError(
                "pykms (python3-kms++) is required for DRM display. " "Install with: sudo apt install python3-kms++"
            ) from e

        self._initialize()

    def _initialize(self):
        """Initialize DRM resources."""
        try:
            logger.info("Initializing DRM/KMS display...")

            # Open DRM device
            self.card = self.pykms.Card()
            logger.debug(f"Opened DRM card: {self.card}")

            # Reserve resources (connector, CRTC)
            self.res = self.pykms.ResourceManager(self.card)

            if self.connector_name:
                self.conn = self.res.reserve_connector(self.connector_name)
                logger.info(f"Using specified connector: {self.connector_name}")
            else:
                self.conn = self.res.reserve_connector()
                logger.info(f"Auto-detected connector: {self.conn.fullname}")

            if not self.conn:
                raise RuntimeError("No connected display found")

            self.crtc = self.res.reserve_crtc(self.conn)
            if not self.crtc:
                raise RuntimeError("No CRTC available for connector")

            # Get display mode
            self.mode = self.conn.get_default_mode()
            logger.info(f"Display mode: {self.mode.hdisplay}x{self.mode.vdisplay} @ {self.mode.vrefresh}Hz")

            # Create framebuffer
            # Using XRGB8888 (32-bit, no alpha) - compatible with most displays
            self.fb = self.pykms.DumbFramebuffer(self.card, self.width, self.height, "XR24")  # XRGB8888 format
            logger.debug(f"Created framebuffer: {self.width}x{self.height} XRGB8888")

            # Map framebuffer to numpy array for direct memory access
            # Format: (height, width, 4) where 4 = XRGB bytes
            self.fb_array = np.frombuffer(self.fb.map(0), dtype=np.uint8).reshape((self.height, self.width, 4))
            logger.debug(f"Mapped framebuffer to numpy array: {self.fb_array.shape}")

            # Set display mode (activate the display)
            self.crtc.set_mode(self.conn, self.fb, self.mode)
            logger.info("DRM display initialized successfully")

            self._initialized = True

        except Exception as e:
            logger.error(f"DRM initialization failed: {e}")
            logger.error(
                "Common issues:\n"
                "  - Desktop session active (DRM requires console mode)\n"
                "  - User not in 'video' group: sudo usermod -a -G video $USER\n"
                "  - No display connected\n"
                "  - Boot to console: sudo systemctl set-default multi-user.target"
            )
            self._cleanup_resources()
            raise RuntimeError(f"DRM initialization failed: {e}") from e

    def show(self, frame: np.ndarray):
        """Display an OpenCV frame (BGR numpy array).

        Args:
            frame: BGR numpy array from OpenCV (shape: H x W x 3)

        The frame will be automatically:
        1. Resized to match display resolution if needed
        2. Converted from BGR to XRGB8888 format
        3. Copied to framebuffer (displayed immediately)
        """
        if not self._initialized:
            logger.warning("Display not initialized, skipping frame")
            return

        try:
            # Resize frame if dimensions don't match
            if frame.shape[0] != self.height or frame.shape[1] != self.width:
                frame = cv2.resize(frame, (self.width, self.height))

            # Convert BGR (OpenCV) to BGRA, then use as XRGB
            # OpenCV: BGR (3 channels)
            # DRM: XRGB8888 (4 bytes: X=padding, R, G, B)
            # We convert to BGRA which matches the byte order
            frame_bgra = cv2.cvtColor(frame, cv2.COLOR_BGR2BGRA)

            # Copy to framebuffer (this displays it immediately)
            self.fb_array[:] = frame_bgra

        except Exception as e:
            logger.error(f"Failed to display frame: {e}")

    def get_resolution(self) -> Tuple[int, int]:
        """Get current display resolution.

        Returns:
            Tuple of (width, height)
        """
        return (self.width, self.height)

    def get_mode_info(self) -> dict:
        """Get display mode information.

        Returns:
            Dictionary with mode details (resolution, refresh rate, etc.)
        """
        if not self.mode:
            return {}

        return {
            "width": self.mode.hdisplay,
            "height": self.mode.vdisplay,
            "refresh_rate": self.mode.vrefresh,
            "name": self.mode.name,
        }

    def _cleanup_resources(self):
        """Cleanup DRM resources."""
        # pykms handles most cleanup automatically via garbage collection
        # but we can explicitly clear references
        self.fb_array = None
        self.fb = None
        self.mode = None
        self.crtc = None
        self.conn = None
        self.res = None
        self.card = None
        self._initialized = False

    def cleanup(self):
        """Cleanup and release DRM resources.

        Call this before exiting the application.
        """
        if self._initialized:
            logger.info("Cleaning up DRM display...")
            self._cleanup_resources()
            logger.info("DRM display cleanup complete")

    def __del__(self):
        """Destructor - ensure cleanup on object deletion."""
        if self._initialized:
            self._cleanup_resources()


class DRMDisplaySingleton:
    """Singleton wrapper for DRMDisplay to mimic cv2.imshow() API.

    This allows drop-in replacement:
        cv2.imshow("window", frame) -> DRMDisplaySingleton.imshow("window", frame)
        cv2.destroyAllWindows() -> DRMDisplaySingleton.destroyAllWindows()
    """

    _instance: Optional[DRMDisplay] = None

    @classmethod
    def imshow(cls, window_name: str, frame: np.ndarray):
        """Display frame (mimics cv2.imshow).

        Args:
            window_name: Window name (ignored, kept for API compatibility)
            frame: BGR numpy array from OpenCV
        """
        if cls._instance is None:
            # Auto-initialize on first call
            cls._instance = DRMDisplay()

        cls._instance.show(frame)

    @classmethod
    def destroyAllWindows(cls):
        """Cleanup display (mimics cv2.destroyAllWindows)."""
        if cls._instance is not None:
            cls._instance.cleanup()
            cls._instance = None

    @classmethod
    def get_instance(cls) -> Optional[DRMDisplay]:
        """Get the singleton instance (for advanced usage)."""
        return cls._instance


# Convenience aliases
imshow = DRMDisplaySingleton.imshow
destroyAllWindows = DRMDisplaySingleton.destroyAllWindows


if __name__ == "__main__":
    # Test/demo code
    import time

    logging.basicConfig(level=logging.INFO)

    print("DRM Display Test")
    print("=" * 60)
    print("This will display a test pattern on the primary display.")
    print("Make sure you're running from console (not desktop session).")
    print("=" * 60)

    try:
        display = DRMDisplay(1280, 720)

        print(f"Display initialized: {display.get_resolution()}")
        print(f"Mode info: {display.get_mode_info()}")

        # Create test frames
        for i in range(100):
            # Create colored test pattern
            frame = np.zeros((720, 1280, 3), dtype=np.uint8)

            # Animated gradient
            frame[:, :, 0] = (i * 2) % 256  # Blue channel
            frame[:, :, 1] = (i * 3) % 256  # Green channel
            frame[:, :, 2] = (i * 5) % 256  # Red channel

            # Add text
            cv2.putText(
                frame, f"DRM Display Test - Frame {i}", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 255, 255), 3
            )

            display.show(frame)
            time.sleep(0.033)  # ~30 FPS

        print("Test complete!")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if "display" in locals():
            display.cleanup()
