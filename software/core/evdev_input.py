#!/usr/bin/env python3
"""
Evdev Keyboard Input Handler for WARLOCK HMU

Provides keyboard input handling using evdev for headless operation (without X11).
This replaces cv2.waitKey() when running in DRM/KMS mode.

Usage:
    keyboard = EvdevKeyboard()
    while True:
        key = keyboard.read_key()  # Returns key code or None
        if key == ord('q'):
            break
    keyboard.cleanup()

Requirements:
    - python3-evdev - sudo apt install python3-evdev OR pip install evdev
    - User in 'input' group - sudo usermod -a -G input $USER
    - udev rule for /dev/input/event* access (see setup_udev_rule())
"""

import logging
import select
import sys
from typing import Optional

logger = logging.getLogger(__name__)


class EvdevKeyboard:
    """Keyboard input handler using evdev (Linux event devices).

    This class provides keyboard input without requiring X11/Wayland,
    suitable for headless console applications using DRM display.
    """

    def __init__(self, device_path: Optional[str] = None, auto_grab: bool = True):
        """Initialize evdev keyboard handler.

        Args:
            device_path: Path to event device (e.g., "/dev/input/event0"), None = auto-detect
            auto_grab: Grab device for exclusive access (prevents input to other apps)

        Raises:
            ImportError: If evdev is not installed
            RuntimeError: If no keyboard found or permission denied
        """
        self.device_path = device_path
        self.auto_grab = auto_grab
        self.device = None
        self._grabbed = False

        try:
            import evdev
            from evdev import ecodes

            self.evdev = evdev
            self.ecodes = ecodes
        except ImportError as e:
            logger.error("evdev not found. Install with: sudo apt install python3-evdev")
            raise ImportError(
                "evdev is required for keyboard input in DRM mode. "
                "Install with: sudo apt install python3-evdev OR pip install evdev"
            ) from e

        self._initialize()

    def _initialize(self):
        """Initialize evdev device."""
        try:
            logger.info("Initializing evdev keyboard input...")

            if self.device_path:
                self.device = self.evdev.InputDevice(self.device_path)
                logger.info(f"Using specified keyboard: {self.device.name} at {self.device_path}")
            else:
                self.device = self._find_keyboard()
                if not self.device:
                    raise RuntimeError("No keyboard device found")
                logger.info(f"Auto-detected keyboard: {self.device.name} at {self.device.path}")

            if self.auto_grab:
                self.device.grab()
                self._grabbed = True
                logger.debug("Grabbed keyboard for exclusive access")

            logger.info("Evdev keyboard initialized successfully")

        except PermissionError as e:
            logger.error(f"Permission denied accessing input device: {e}")
            logger.error(
                "Common fixes:\n"
                "  1. Add user to 'input' group: sudo usermod -a -G input $USER\n"
                "  2. Setup udev rule (see evdev_input.setup_udev_rule())\n"
                "  3. Or run with sudo (not recommended)\n"
                "  4. Logout and login after adding to group"
            )
            raise RuntimeError(f"Permission denied: {e}") from e

        except Exception as e:
            logger.error(f"Keyboard initialization failed: {e}")
            raise RuntimeError(f"Keyboard initialization failed: {e}") from e

    def _find_keyboard(self) -> Optional[object]:
        """Auto-detect keyboard device.

        Returns:
            evdev.InputDevice or None if not found
        """
        devices = [self.evdev.InputDevice(path) for path in self.evdev.list_devices()]

        # Try to find device with "keyboard" in name
        for device in devices:
            name_lower = device.name.lower()
            if "keyboard" in name_lower or "kbd" in name_lower:
                logger.debug(f"Found keyboard candidate: {device.name}")
                return device

        # Fallback: find device that supports key events
        for device in devices:
            capabilities = device.capabilities()
            # Check if device has EV_KEY capability with keyboard keys
            if self.ecodes.EV_KEY in capabilities:
                keys = capabilities[self.ecodes.EV_KEY]
                # Check for common keyboard keys (not just mouse buttons)
                if self.ecodes.KEY_A in keys or self.ecodes.KEY_ENTER in keys:
                    logger.debug(f"Found keyboard-like device: {device.name}")
                    return device

        logger.warning("No keyboard device found")
        return None

    def read_key(self, timeout: float = 0.0) -> Optional[int]:
        """Read a key press (non-blocking by default).

        Args:
            timeout: Timeout in seconds (0 = non-blocking, None = blocking)

        Returns:
            ASCII key code (compatible with cv2.waitKey), or None if no key pressed
        """
        if not self.device:
            return None

        try:
            # Use select for non-blocking or timeout read
            r, w, x = select.select([self.device.fd], [], [], timeout)

            if not r:
                return None  # No input available

            # Read all pending events
            for event in self.device.read():
                # We only care about key press events (not release)
                if event.type == self.ecodes.EV_KEY and event.value == 1:  # 1 = key down
                    return self._evdev_to_ascii(event.code)

        except Exception as e:
            logger.error(f"Error reading keyboard: {e}")

        return None

    def read_key_blocking(self) -> int:
        """Read a key press (blocking until key is pressed).

        Returns:
            ASCII key code (compatible with cv2.waitKey)
        """
        while True:
            key = self.read_key(timeout=None)  # Block forever
            if key is not None:
                return key

    def _evdev_to_ascii(self, keycode: int) -> int:
        """Convert evdev keycode to ASCII (compatible with cv2.waitKey).

        Args:
            keycode: evdev keycode (e.g., ecodes.KEY_A)

        Returns:
            ASCII character code (e.g., ord('a') = 97)
        """
        # Map evdev keycodes to ASCII
        # This covers common keys used in WARLOCK

        # Letters (KEY_A to KEY_Z -> lowercase a-z)
        if self.ecodes.KEY_A <= keycode <= self.ecodes.KEY_Z:
            return ord("a") + (keycode - self.ecodes.KEY_A)

        # Numbers (KEY_1 to KEY_0)
        if self.ecodes.KEY_1 <= keycode <= self.ecodes.KEY_9:
            return ord("1") + (keycode - self.ecodes.KEY_1)
        if keycode == self.ecodes.KEY_0:
            return ord("0")

        # Special keys
        special_keys = {
            self.ecodes.KEY_SPACE: ord(" "),
            self.ecodes.KEY_ENTER: ord("\n"),
            self.ecodes.KEY_ESC: 27,  # ESC
            self.ecodes.KEY_TAB: ord("\t"),
            self.ecodes.KEY_MINUS: ord("-"),
            self.ecodes.KEY_EQUAL: ord("="),
            self.ecodes.KEY_LEFTBRACE: ord("["),
            self.ecodes.KEY_RIGHTBRACE: ord("]"),
            self.ecodes.KEY_SEMICOLON: ord(";"),
            self.ecodes.KEY_APOSTROPHE: ord("'"),
            self.ecodes.KEY_GRAVE: ord("`"),
            self.ecodes.KEY_BACKSLASH: ord("\\"),
            self.ecodes.KEY_COMMA: ord(","),
            self.ecodes.KEY_DOT: ord("."),
            self.ecodes.KEY_SLASH: ord("/"),
            self.ecodes.KEY_KPPLUS: ord("+"),
            self.ecodes.KEY_KPMINUS: ord("-"),
        }

        if keycode in special_keys:
            return special_keys[keycode]

        # Arrow keys (use extended ASCII codes for compatibility)
        arrow_keys = {
            self.ecodes.KEY_UP: 82,  # Up arrow
            self.ecodes.KEY_DOWN: 84,  # Down arrow
            self.ecodes.KEY_LEFT: 81,  # Left arrow
            self.ecodes.KEY_RIGHT: 83,  # Right arrow
        }

        if keycode in arrow_keys:
            return arrow_keys[keycode]

        # Function keys (F1-F12)
        if self.ecodes.KEY_F1 <= keycode <= self.ecodes.KEY_F12:
            # Return values compatible with OpenCV
            return 0x70 + (keycode - self.ecodes.KEY_F1)  # F1=0x70, F2=0x71, etc.

        # Unmapped key - return raw keycode
        logger.debug(f"Unmapped keycode: {keycode}")
        return keycode

    def cleanup(self):
        """Release keyboard device."""
        if self.device:
            logger.info("Cleaning up evdev keyboard...")
            if self._grabbed:
                try:
                    self.device.ungrab()
                    self._grabbed = False
                except Exception as e:
                    logger.warning(f"Error ungrabbing device: {e}")

            self.device.close()
            self.device = None
            logger.info("Evdev keyboard cleanup complete")

    def __del__(self):
        """Destructor - ensure cleanup."""
        self.cleanup()


def setup_udev_rule():
    """Helper function to setup udev rule for input device access.

    This allows non-root users to access /dev/input/event* devices.

    Run this function and follow the instructions.
    """
    rule_content = """# Allow users in 'input' group to access input devices
KERNEL=="event*", SUBSYSTEM=="input", MODE="0660", GROUP="input"
"""

    rule_path = "/etc/udev/rules.d/99-input.rules"

    print("=" * 60)
    print("UDEV RULE SETUP FOR EVDEV INPUT")
    print("=" * 60)
    print("\n1. Create udev rule (requires sudo):")
    print(f"\n   echo '{rule_content.strip()}' | sudo tee {rule_path}")
    print("\n2. Reload udev rules:")
    print("\n   sudo udevadm control --reload-rules")
    print("   sudo udevadm trigger")
    print("\n3. Add your user to 'input' group:")
    print(f"\n   sudo usermod -a -G input $USER")
    print("\n4. Logout and login (or reboot)")
    print("\n5. Verify:")
    print("\n   groups  # Should show 'input'")
    print("   ls -l /dev/input/event*  # Should show group 'input'")
    print("=" * 60)


if __name__ == "__main__":
    # Test/demo code
    logging.basicConfig(level=logging.INFO)

    print("Evdev Keyboard Test")
    print("=" * 60)
    print("This will read keyboard input using evdev.")
    print("Make sure you're in 'input' group or running as root.")
    print("Press 'q' to quit, 'h' for help")
    print("=" * 60)

    # Check if setup is needed
    import os

    if not os.path.exists("/etc/udev/rules.d/99-input.rules"):
        print("\nUdev rule not found. Run setup:")
        setup_udev_rule()
        print("\nContinuing with test (may require sudo)...\n")

    try:
        keyboard = EvdevKeyboard()

        print(f"Keyboard ready: {keyboard.device.name}")
        print("Press keys...\n")

        while True:
            key = keyboard.read_key(timeout=0.1)  # 100ms timeout

            if key is not None:
                # Convert to character if printable
                if 32 <= key <= 126:  # Printable ASCII
                    print(f"Key pressed: '{chr(key)}' (code: {key})")
                else:
                    print(f"Key pressed: code {key}")

                if key == ord("q"):
                    print("\nQuitting...")
                    break
                elif key == ord("h"):
                    print("Help: Press any key to see its code, 'q' to quit")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        print("\nTry running setup:")
        setup_udev_rule()
        sys.exit(1)
    finally:
        if "keyboard" in locals():
            keyboard.cleanup()
