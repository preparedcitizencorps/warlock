#!/usr/bin/env python3
"""Network protocol definitions for HMU-BMU communication."""

import time
from enum import Enum
from typing import Any, Dict


class MessageType(Enum):
    """Message types for HMU-BMU protocol."""

    # HMU → BMU (Upstream)
    HEARTBEAT_HMU = "heartbeat_hmu"
    DETECTION = "detection"
    SENSOR_TELEMETRY = "sensor_telemetry"
    USER_INPUT = "user_input"
    FRAME_METADATA = "frame_metadata"

    # BMU → HMU (Downstream)
    HEARTBEAT_BMU = "heartbeat_bmu"
    GPS_UPDATE = "gps_update"
    TEAM_POSITIONS = "team_positions"
    RF_ALERT = "rf_alert"
    WIFI_ALERT = "wifi_alert"
    RADIO_STATUS = "radio_status"
    ATAK_DATA = "atak_data"

    # Bidirectional
    CAPABILITY_EXCHANGE = "capability_exchange"
    TIME_SYNC = "time_sync"
    MODE_CHANGE = "mode_change"
    ERROR = "error"


class Transport(Enum):
    """Transport layer types."""

    TCP = "tcp"
    UDP = "udp"


class ConnectionStatus(Enum):
    """Connection status."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    CABLE = "cable"
    WIFI = "wifi"
    ERROR = "error"


def create_message(msg_type: MessageType, source_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a standardized protocol message.

    Args:
        msg_type: Message type from MessageType enum
        source_id: Source identifier (e.g., "WARLOCK-001-HMU")
        payload: Message payload data

    Returns:
        Formatted message dictionary
    """
    return {"type": msg_type.value, "source_id": source_id, "timestamp": time.time(), "payload": payload}


def validate_message(message: Dict[str, Any]) -> bool:
    """Validate message format.

    Args:
        message: Message dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["type", "source_id", "timestamp", "payload"]

    if not all(field in message for field in required_fields):
        return False

    # Validate message type
    try:
        MessageType(message["type"])
    except ValueError:
        return False

    # Validate timestamp
    if not isinstance(message["timestamp"], (int, float)):
        return False

    # Validate payload is dict
    if not isinstance(message["payload"], dict):
        return False

    return True


# Message transport requirements
MESSAGE_TRANSPORT = {
    # HMU → BMU
    MessageType.HEARTBEAT_HMU: (Transport.UDP, 1),  # (transport, frequency_hz)
    MessageType.DETECTION: (Transport.TCP, None),  # event-driven
    MessageType.SENSOR_TELEMETRY: (Transport.UDP, 10),
    MessageType.USER_INPUT: (Transport.TCP, None),
    MessageType.FRAME_METADATA: (Transport.UDP, 30),
    # BMU → HMU
    MessageType.HEARTBEAT_BMU: (Transport.UDP, 1),
    MessageType.GPS_UPDATE: (Transport.UDP, 10),
    MessageType.TEAM_POSITIONS: (Transport.UDP, 5),
    MessageType.RF_ALERT: (Transport.TCP, None),
    MessageType.WIFI_ALERT: (Transport.TCP, None),
    MessageType.RADIO_STATUS: (Transport.UDP, 1),
    MessageType.ATAK_DATA: (Transport.TCP, None),
    # Bidirectional
    MessageType.CAPABILITY_EXCHANGE: (Transport.TCP, None),
    MessageType.TIME_SYNC: (Transport.UDP, 1),
    MessageType.MODE_CHANGE: (Transport.TCP, None),
    MessageType.ERROR: (Transport.TCP, None),
}
