#!/usr/bin/env python3
"""
Smart camera detection for WARLOCK.

Automatically detects and initializes:
- USB cameras (via OpenCV VideoCapture)
- Standard Raspberry Pi cameras (v2, v3, HQ)
- Native Arducam cameras (IMX462, IMX290, IMX327)
- Arducam PiVariety cameras

Provides a unified interface regardless of camera type.
"""

import logging
import subprocess
from typing import Optional, Tuple

import cv2

logger = logging.getLogger(__name__)


class CameraInfo:
    """Information about a detected camera"""

    def __init__(self, camera_type: str, sensor_model: str = "Unknown", camera_num: int = 0):
        self.camera_type = camera_type  # "usb", "picamera2"
        self.sensor_model = sensor_model  # "IMX462", "IMX290", "IMX327", "IMX708", etc.
        self.camera_num = camera_num

    def __str__(self):
        return f"{self.camera_type} ({self.sensor_model})"


def detect_picamera2_cameras() -> Optional[list]:
    """
    Detect cameras available via Picamera2/libcamera.

    Returns:
        List of camera info dictionaries, or None if picamera2 not available
    """
    try:
        from picamera2 import Picamera2
    except ImportError:
        logger.debug("Picamera2 not available")
        return None

    try:
        cameras = Picamera2.global_camera_info()
        if cameras:
            logger.info(f"Detected {len(cameras)} camera(s) via libcamera:")
            for idx, cam in enumerate(cameras):
                model = cam.get("Model", "Unknown")
                location = cam.get("Location", "Unknown")
                logger.info(f"  Camera {idx}: {model} (Location: {location})")
            return cameras
        else:
            logger.debug("No cameras detected via libcamera")
            return []
    except Exception as e:
        logger.warning(f"Failed to query picamera2 cameras: {e}")
        return None


def detect_v4l2_cameras() -> list:
    """
    Detect cameras available via V4L2 (USB cameras, etc).

    Returns:
        List of V4L2 device paths (e.g., ['/dev/video0', '/dev/video2'])
    """
    devices = []
    try:
        # List all video devices
        result = subprocess.run(["ls", "-1", "/dev/video*"], capture_output=True, text=True, check=False)
        if result.returncode == 0:
            potential_devices = result.stdout.strip().split("\n")

            # Filter to actual capture devices (not metadata devices)
            for device in potential_devices:
                try:
                    # Try to get device capabilities
                    cap_result = subprocess.run(
                        ["v4l2-ctl", "--device", device, "--all"],
                        capture_output=True,
                        text=True,
                        check=False,
                        timeout=1,
                    )
                    if "Video Capture" in cap_result.stdout:
                        devices.append(device)
                        logger.debug(f"Found V4L2 capture device: {device}")
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    # v4l2-ctl not available or device timeout, try with OpenCV
                    cap = cv2.VideoCapture(device)
                    if cap.isOpened():
                        devices.append(device)
                        cap.release()
                        logger.debug(f"Found OpenCV capture device: {device}")
    except Exception as e:
        logger.debug(f"V4L2 detection failed: {e}")

    return devices


def get_sensor_model_from_camera_info(camera_info: dict) -> str:
    """
    Extract sensor model from Picamera2 camera info.

    Args:
        camera_info: Dictionary from Picamera2.global_camera_info()

    Returns:
        Sensor model string (e.g., "IMX462", "IMX708", "IMX219")
    """
    model = camera_info.get("Model", "Unknown")

    # Extract sensor model - libcamera reports like "imx462" or "/base/axi/pcie.../imx462"
    if "imx462" in model.lower():
        return "IMX462"
    elif "imx290" in model.lower():
        return "IMX290"
    elif "imx327" in model.lower():
        return "IMX327"
    elif "imx708" in model.lower():  # Pi Camera v3
        return "IMX708"
    elif "imx477" in model.lower():  # Pi HQ Camera
        return "IMX477"
    elif "imx219" in model.lower():  # Pi Camera v2
        return "IMX219"
    elif "ov5647" in model.lower():  # Pi Camera v1
        return "OV5647"
    else:
        # Return the model as-is
        return model


def detect_cameras() -> list:
    """
    Detect all available cameras (CSI and USB).

    Returns:
        List of CameraInfo objects describing detected cameras
    """
    detected_cameras = []

    # Try Picamera2 first (CSI cameras on Raspberry Pi)
    picam2_cameras = detect_picamera2_cameras()
    if picam2_cameras:
        for idx, cam_info in enumerate(picam2_cameras):
            sensor = get_sensor_model_from_camera_info(cam_info)
            detected_cameras.append(CameraInfo("picamera2", sensor, idx))

    # Check for V4L2/USB cameras
    v4l2_devices = detect_v4l2_cameras()
    if v4l2_devices:
        logger.info(f"Detected {len(v4l2_devices)} V4L2/USB camera device(s)")
        for idx, device in enumerate(v4l2_devices):
            # If we already detected picamera2 cameras, USB cameras start at higher indices
            camera_num = idx if not detected_cameras else idx + 10
            detected_cameras.append(CameraInfo("usb", f"V4L2 {device}", camera_num))

    return detected_cameras


def initialize_camera(width: int = 1280, height: int = 720, prefer_csi: bool = True):
    """
    Automatically detect and initialize the best available camera.

    Args:
        width: Desired frame width
        height: Desired frame height
        prefer_csi: If True, prefer CSI cameras over USB cameras

    Returns:
        Tuple of (camera_object, CameraInfo) or raises RuntimeError if no camera found

    Raises:
        RuntimeError: If no working camera could be initialized
    """
    cameras = detect_cameras()

    if not cameras:
        raise RuntimeError("No cameras detected")

    logger.info(f"Detected {len(cameras)} camera(s):")
    for cam in cameras:
        logger.info(f"  - {cam}")

    # Sort cameras by preference
    if prefer_csi:
        # CSI cameras (picamera2) first, then USB
        cameras.sort(key=lambda c: (c.camera_type != "picamera2", c.camera_num))
    else:
        # USB cameras first, then CSI
        cameras.sort(key=lambda c: (c.camera_type == "picamera2", c.camera_num))

    # Try to initialize cameras in order of preference
    last_error = None
    for cam_info in cameras:
        try:
            logger.info(f"Attempting to initialize {cam_info}...")

            if cam_info.camera_type == "picamera2":
                cap = _init_picamera2(cam_info.camera_num, width, height)
            else:  # usb
                cap = _init_opencv_camera(cam_info.camera_num, width, height)

            # Verify camera works
            ret, test_frame = cap.read()
            if ret and test_frame is not None:
                logger.info(f"Successfully initialized {cam_info} - Frame shape: {test_frame.shape}")
                return cap, cam_info
            else:
                logger.warning(f"{cam_info} opened but failed to read frames")
                if hasattr(cap, "release"):
                    cap.release()

        except Exception as e:
            logger.warning(f"Failed to initialize {cam_info}: {e}")
            last_error = e
            continue

    # No camera worked
    error_msg = f"Failed to initialize any camera. Last error: {last_error}"
    raise RuntimeError(error_msg)


def _init_picamera2(camera_num: int, width: int, height: int):
    """Initialize a Picamera2 camera"""
    from helmet.core.picamera2_adapter import Picamera2Adapter

    return Picamera2Adapter(camera_num, width, height)


def _init_opencv_camera(camera_num: int, width: int, height: int):
    """Initialize an OpenCV VideoCapture camera"""
    # Try V4L2 backend first
    cap = cv2.VideoCapture(camera_num, cv2.CAP_V4L2)
    if not cap.isOpened():
        logger.debug("V4L2 backend failed, trying default backend...")
        cap = cv2.VideoCapture(camera_num)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera {camera_num}")

    # Configure camera
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"BGR3"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)

    # Test frame capture
    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        # Try YUYV format as fallback
        logger.debug("BGR3 failed, trying YUYV format...")
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            cap.release()
            raise RuntimeError("Camera opened but failed to read frames")

    return cap
