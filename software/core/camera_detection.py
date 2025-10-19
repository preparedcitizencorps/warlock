#!/usr/bin/env python3
"""Auto-detection for USB, CSI, Arducam Native, and Arducam PiVariety cameras."""

import glob
import logging
import re
import subprocess
from typing import Optional, Tuple

import cv2

logger = logging.getLogger(__name__)


class CameraInfo:
    def __init__(self, camera_type: str, sensor_model: str = "Unknown", camera_num: int = 0):
        self.camera_type = camera_type
        self.sensor_model = sensor_model
        self.camera_num = camera_num

    def __str__(self):
        return f"{self.camera_type} ({self.sensor_model})"


def detect_picamera2_cameras() -> list:
    try:
        from picamera2 import Picamera2
    except ImportError:
        logger.debug("Picamera2 not available")
        return []

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
        return []


def detect_v4l2_cameras() -> list:
    devices = []
    try:
        potential_devices = sorted(glob.glob("/dev/video*"))

        for device in potential_devices:
            try:
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
                cap = cv2.VideoCapture(device)
                if cap.isOpened():
                    devices.append(device)
                    cap.release()
                    logger.debug(f"Found OpenCV capture device: {device}")
    except Exception as e:
        logger.debug(f"V4L2 detection failed: {e}")

    return devices


SENSOR_MAP = {
    "imx462": "IMX462",
    "imx290": "IMX290",
    "imx327": "IMX327",
    "imx708": "IMX708",
    "imx477": "IMX477",
    "imx219": "IMX219",
    "ov5647": "OV5647",
}


def get_sensor_model_from_camera_info(camera_info: dict) -> str:
    model = camera_info.get("Model", "Unknown")

    for pattern, sensor_name in SENSOR_MAP.items():
        if pattern in model.lower():
            return sensor_name

    return model


def detect_cameras() -> list:
    detected_cameras = []

    picam2_cameras = detect_picamera2_cameras()
    if picam2_cameras:
        for idx, cam_info in enumerate(picam2_cameras):
            sensor = get_sensor_model_from_camera_info(cam_info)
            detected_cameras.append(CameraInfo("picamera2", sensor, idx))

    v4l2_devices = detect_v4l2_cameras()
    if v4l2_devices:
        logger.info(f"Detected {len(v4l2_devices)} V4L2/USB camera device(s)")
        for idx, device in enumerate(v4l2_devices):
            match = re.search(r"(\d+)$", device)
            camera_num = int(match.group(1)) if match else idx
            detected_cameras.append(CameraInfo("usb", f"V4L2 {device}", camera_num))

    return detected_cameras


def initialize_camera(width: int = 1280, height: int = 720, prefer_csi: bool = True):
    cameras = detect_cameras()

    if not cameras:
        raise RuntimeError("No cameras detected")

    logger.info(f"Detected {len(cameras)} camera(s):")
    for cam in cameras:
        logger.info(f"  - {cam}")

    if prefer_csi:
        cameras.sort(key=lambda c: (c.camera_type != "picamera2", c.camera_num))
    else:
        cameras.sort(key=lambda c: (c.camera_type == "picamera2", c.camera_num))

    last_error = None
    for cam_info in cameras:
        try:
            logger.info(f"Attempting to initialize {cam_info}...")

            if cam_info.camera_type == "picamera2":
                cap = _init_picamera2(cam_info.camera_num, width, height)
            else:
                cap = _init_opencv_camera(cam_info.camera_num, width, height)

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

    error_msg = f"Failed to initialize any camera. Last error: {last_error}"
    raise RuntimeError(error_msg)


def _init_picamera2(camera_num: int, width: int, height: int):
    from core.picamera2_adapter import Picamera2Adapter

    return Picamera2Adapter(camera_num, width, height)


def _init_opencv_camera(camera_num: int, width: int, height: int):
    cap = cv2.VideoCapture(camera_num, cv2.CAP_V4L2)
    if not cap.isOpened():
        logger.debug("V4L2 backend failed, trying default backend...")
        cap = cv2.VideoCapture(camera_num)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open camera {camera_num}")

    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"BGR3"))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    cap.set(cv2.CAP_PROP_FPS, 30)

    ret, test_frame = cap.read()
    if not ret or test_frame is None:
        logger.debug("BGR3 failed, trying YUYV format...")
        cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"YUYV"))
        ret, test_frame = cap.read()
        if not ret or test_frame is None:
            cap.release()
            raise RuntimeError("Camera opened but failed to read frames")

    return cap
