#!/usr/bin/env python3
"""Shared data models for WARLOCK HMU and BMU communication."""

from dataclasses import dataclass, field
from typing import List, Optional
from enum import Enum


@dataclass
class Position:
    """GPS position with heading and altitude."""
    latitude: float
    longitude: float
    altitude: float
    heading: float
    timestamp: float
    quality: Optional[int] = None  # GPS fix quality (0-9)
    num_satellites: Optional[int] = None


@dataclass
class Detection:
    """Object detection from YOLO."""
    class_id: int
    class_name: str
    confidence: float
    bbox: List[float]  # [x, y, width, height] - YOLO returns floats
    bearing: Optional[float] = None  # Relative to user heading (degrees)
    distance: Optional[float] = None  # Estimated distance (meters)
    timestamp: float = 0.0


class FriendlyUnitStatus(Enum):
    """Team member status types."""
    ACTIVE = "active"
    WOUNDED = "wounded"
    KIA = "kia"


@dataclass
class FriendlyUnit:
    """Team member position and status."""
    id: str
    callsign: str
    position: Position
    status: FriendlyUnitStatus
    bearing: float  # Relative to user (degrees)
    distance: float  # Meters


class RFClassification(Enum):
    """RF signal classification types."""
    RADIO = "radio"
    DRONE = "drone"
    JAMMER = "jammer"
    UNKNOWN = "unknown"


@dataclass
class RFDetection:
    """RF signal detection from RTL-SDR."""
    frequency: float  # Hz
    signal_strength: float  # dBm
    bearing: Optional[float] = None  # If triangulated (degrees)
    location: Optional[Position] = None  # If triangulated
    classification: RFClassification = RFClassification.UNKNOWN
    timestamp: float = 0.0


@dataclass
class WiFiDetection:
    """WiFi CSI detection."""
    mac_address: str
    ssid: Optional[str] = None
    signal_strength: float = 0.0  # dBm
    distance: float = 0.0  # From CSI estimate (meters)
    direction: Optional[float] = None  # If directional antenna (degrees)
    motion_detected: bool = False
    timestamp: float = 0.0


@dataclass
class IMUData:
    """Inertial measurement unit data."""
    heading: float  # degrees (0-360, 0=North)
    pitch: float  # degrees (-90 to 90)
    roll: float  # degrees (-180 to 180)
    acceleration_x: float  # m/s²
    acceleration_y: float  # m/s²
    acceleration_z: float  # m/s²
    timestamp: float = 0.0


@dataclass
class BatteryStatus:
    """Battery voltage and percentage."""
    voltage: float  # Volts
    percent: int  # 0-100
    charging: bool = False
    timestamp: float = 0.0


class ThermalStatusLevel(Enum):
    """Thermal status levels."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class ThermalStatus:
    """Thermal monitoring data."""
    cpu_temp: float  # °C
    gpu_temp: Optional[float] = None  # °C
    status: ThermalStatusLevel = ThermalStatusLevel.NORMAL
    fan_active: bool = False
    timestamp: float = 0.0
