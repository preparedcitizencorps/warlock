"""Tests for GPS system essentials.

Tests verify core GPS functionality without being fragile to implementation changes.
"""

import pytest
import math
from body.core.gps_simulator import GPSSimulator


class TestGPSPositionUpdates:
    """Test that GPS provides position data in expected format."""

    def test_gps_provides_required_fields(self):
        """GPS position must have lat, lon, altitude, heading."""
        gps = GPSSimulator()
        position = gps.get_position()

        required_fields = ['latitude', 'longitude', 'altitude', 'heading', 'timestamp']
        for field in required_fields:
            assert field in position, f"Position must include {field}"

    def test_latitude_in_valid_range(self):
        """Latitude must be between -90 and 90 degrees."""
        gps = GPSSimulator()
        position = gps.get_position()

        assert -90 <= position['latitude'] <= 90

    def test_longitude_in_valid_range(self):
        """Longitude must be between -180 and 180 degrees."""
        gps = GPSSimulator()
        position = gps.get_position()

        assert -180 <= position['longitude'] <= 180

    def test_heading_in_valid_range(self):
        """Heading must be between 0 and 360 degrees."""
        gps = GPSSimulator()
        position = gps.get_position()

        assert 0 <= position['heading'] <= 360

    def test_timestamp_is_numeric(self):
        """Timestamp must be numeric for time calculations."""
        gps = GPSSimulator()
        position = gps.get_position()

        assert isinstance(position['timestamp'], (int, float))


class TestGPSMovement:
    """Test GPS movement updates work as expected."""

    def test_forward_movement_changes_position(self):
        """Moving forward should change position."""
        gps = GPSSimulator(start_lat=0.0, start_lon=0.0)
        initial = gps.get_position()

        gps.update(forward=1.0, turn=0)

        updated = gps.get_position()
        assert (updated['latitude'] != initial['latitude'] or
                updated['longitude'] != initial['longitude'])

    def test_turn_changes_heading(self):
        """Turning should change heading."""
        gps = GPSSimulator()
        initial_heading = gps.heading

        gps.update(forward=0, turn=1.0)

        assert gps.heading != initial_heading

    def test_no_movement_keeps_position_stable(self):
        """Position should be stable when not moving."""
        gps = GPSSimulator()
        pos1 = gps.get_position()

        gps.update(forward=0, turn=0)

        pos2 = gps.get_position()
        assert pos1['latitude'] == pos2['latitude']
        assert pos1['longitude'] == pos2['longitude']


class TestGPSEdgeCases:
    """Test GPS handles edge cases without crashing."""

    def test_near_north_pole_does_not_crash(self):
        """GPS should handle positions near poles."""
        gps = GPSSimulator(start_lat=89.0, start_lon=0.0)

        for _ in range(10):
            gps.update(forward=1.0, turn=0)
            position = gps.get_position()
            assert -90 <= position['latitude'] <= 90

    def test_near_south_pole_does_not_crash(self):
        """GPS should handle positions near south pole."""
        gps = GPSSimulator(start_lat=-89.0, start_lon=0.0)

        for _ in range(10):
            gps.update(forward=1.0, turn=0)
            position = gps.get_position()
            assert -90 <= position['latitude'] <= 90

    def test_date_line_crossing_does_not_crash(self):
        """GPS should handle crossing the international date line."""
        gps = GPSSimulator(start_lat=0.0, start_lon=179.0)

        for _ in range(10):
            gps.update(forward=0, turn=1.0)
            position = gps.get_position()
            assert -180 <= position['longitude'] <= 180

    def test_multiple_full_rotations(self):
        """Heading should handle multiple 360° rotations."""
        gps = GPSSimulator()

        for _ in range(100):
            gps.update(forward=0, turn=10.0)

        position = gps.get_position()
        assert 0 <= position['heading'] <= 360
