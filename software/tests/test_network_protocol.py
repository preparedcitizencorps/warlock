"""Tests for network protocol message structure and validation.

These tests verify the essential message format contracts, not implementation details.
"""

import time

import pytest
from common.protocol import MessageType, create_message, validate_message


class TestMessageProtocol:
    """Test core message protocol contracts."""

    def test_create_message_has_required_fields(self):
        """Messages must have type, source_id, timestamp, and payload."""
        msg = create_message(MessageType.GPS_UPDATE, "TEST-BMU", {"latitude": 38.0, "longitude": -104.0})

        assert "type" in msg
        assert "source_id" in msg
        assert "timestamp" in msg
        assert "payload" in msg

    def test_message_type_is_string(self):
        """Message type should be serializable as string."""
        msg = create_message(MessageType.GPS_UPDATE, "TEST", {})

        assert isinstance(msg["type"], str)
        assert msg["type"] == "gps_update"

    def test_timestamp_is_numeric(self):
        """Timestamp must be numeric for time calculations."""
        msg = create_message(MessageType.HEARTBEAT_BMU, "TEST", {})

        assert isinstance(msg["timestamp"], (int, float))

    def test_payload_is_dict(self):
        """Payload must be dict for JSON serialization."""
        msg = create_message(MessageType.GPS_UPDATE, "TEST", {"key": "value"})

        assert isinstance(msg["payload"], dict)

    def test_validate_message_accepts_valid_message(self):
        """Well-formed messages should pass validation."""
        msg = create_message(MessageType.GPS_UPDATE, "TEST", {})

        assert validate_message(msg) is True

    def test_validate_message_rejects_missing_fields(self):
        """Messages missing required fields should fail validation."""
        incomplete = {"type": "gps_update", "source_id": "TEST"}

        assert validate_message(incomplete) is False

    def test_validate_message_rejects_invalid_type(self):
        """Messages with invalid type should fail validation."""
        invalid = {"type": "INVALID_TYPE_NOT_IN_ENUM", "source_id": "TEST", "timestamp": time.time(), "payload": {}}

        assert validate_message(invalid) is False

    def test_message_types_are_bidirectional(self):
        """Protocol should support both HMU→BMU and BMU→HMU messages."""
        hmu_to_bmu = create_message(MessageType.DETECTION, "HMU-001", {})
        bmu_to_hmu = create_message(MessageType.GPS_UPDATE, "BMU-001", {})

        assert validate_message(hmu_to_bmu)
        assert validate_message(bmu_to_hmu)


class TestMessageTypeCategories:
    """Test that message types are properly categorized."""

    def test_gps_messages_exist(self):
        """GPS communication is essential to the architecture."""
        assert MessageType.GPS_UPDATE

    def test_heartbeat_messages_exist(self):
        """Both units must support heartbeats."""
        assert MessageType.HEARTBEAT_HMU
        assert MessageType.HEARTBEAT_BMU

    def test_detection_messages_exist(self):
        """HMU must be able to send detection data."""
        assert MessageType.DETECTION

    def test_alert_messages_exist(self):
        """BMU must be able to send alerts."""
        assert MessageType.RF_ALERT
        assert MessageType.WIFI_ALERT
