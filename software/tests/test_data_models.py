"""Tests for shared data model contracts.

Tests verify data models work as expected without being fragile to field changes.
"""

import pytest
from common.data_models import (
    Detection,
    FriendlyUnit,
    FriendlyUnitStatus,
    Position,
    RFDetection,
    ThermalStatus,
    ThermalStatusLevel,
    WiFiDetection,
)


class TestDataModelCreation:
    """Test that data models can be created with valid data."""

    def test_position_can_be_created(self):
        """Position is the most critical data structure."""
        pos = Position(
            latitude=38.0, longitude=-104.0, altitude=1800.0, heading=270.0, timestamp=0.0, quality=4, num_satellites=12
        )

        assert pos.latitude == 38.0
        assert pos.longitude == -104.0

    def test_detection_can_be_created(self):
        """Detection represents YOLO output."""
        det = Detection(
            class_id=0,
            class_name="person",
            confidence=0.95,
            bbox=[100.0, 200.0, 50.0, 100.0],
            bearing=45.0,
            distance=25.0,
            timestamp=0.0,
        )

        assert det.class_name == "person"
        assert 0.0 <= det.confidence <= 1.0

    def test_friendly_unit_can_be_created(self):
        """FriendlyUnit represents team members."""
        unit = FriendlyUnit(
            id="ALPHA-1",
            callsign="ALPHA-1",
            position=Position(38.0, -104.0, 1800.0, 0.0, 0.0, 4, 12),
            status=FriendlyUnitStatus.ACTIVE,
            bearing=45.0,
            distance=100.0,
        )

        assert unit.callsign == "ALPHA-1"


class TestEnumValidation:
    """Test that enums enforce valid values."""

    def test_friendly_unit_status_has_expected_values(self):
        """FriendlyUnitStatus must support operational states."""
        assert FriendlyUnitStatus.ACTIVE
        assert FriendlyUnitStatus.WOUNDED
        assert FriendlyUnitStatus.KIA

    def test_friendly_unit_status_values_are_strings(self):
        """Enum values should be serializable strings."""
        assert isinstance(FriendlyUnitStatus.ACTIVE.value, str)
        assert isinstance(FriendlyUnitStatus.WOUNDED.value, str)
        assert isinstance(FriendlyUnitStatus.KIA.value, str)

    def test_thermal_status_level_has_expected_values(self):
        """ThermalStatusLevel must support thermal states."""
        assert ThermalStatusLevel.NORMAL
        assert ThermalStatusLevel.WARNING
        assert ThermalStatusLevel.CRITICAL

    def test_thermal_status_level_values_are_strings(self):
        """Enum values should be serializable strings."""
        assert isinstance(ThermalStatusLevel.NORMAL.value, str)
        assert isinstance(ThermalStatusLevel.WARNING.value, str)
        assert isinstance(ThermalStatusLevel.CRITICAL.value, str)

    def test_thermal_status_can_use_enum(self):
        """ThermalStatus should accept enum values."""
        status = ThermalStatus(cpu_temp=65.0, status=ThermalStatusLevel.NORMAL, timestamp=0.0)

        assert status.status == ThermalStatusLevel.NORMAL


class TestBboxFormat:
    """Test that detection bounding boxes use correct format."""

    def test_bbox_is_list_of_numbers(self):
        """Bbox should be [x, y, width, height] as numbers."""
        det = Detection(
            class_id=0,
            class_name="test",
            confidence=0.9,
            bbox=[10.0, 20.0, 30.0, 40.0],
            bearing=0.0,
            distance=0.0,
            timestamp=0.0,
        )

        assert len(det.bbox) == 4
        assert all(isinstance(x, (int, float)) for x in det.bbox)

    def test_bbox_values_are_non_negative(self):
        """Bbox coordinates should be non-negative."""
        det = Detection(
            class_id=0,
            class_name="test",
            confidence=0.9,
            bbox=[10.0, 20.0, 30.0, 40.0],
            bearing=0.0,
            distance=0.0,
            timestamp=0.0,
        )

        assert all(x >= 0 for x in det.bbox)
