#!/usr/bin/env python3
"""GPS simulator for testing BMU without hardware."""

import math
import time


class GPSSimulator:
    """Simulates GPS position updates."""

    METERS_PER_DEGREE_LATITUDE = 111111
    MINIMUM_SAFE_COS_LAT = 0.01
    SAFE_LATITUDE_RANGE = (-89.9, 89.9)

    def __init__(self, start_lat: float = 38.8339, start_lon: float = -104.8214):
        """Initialize GPS simulator.

        Args:
            start_lat: Starting latitude (default: Colorado Springs)
            start_lon: Starting longitude
        """
        self.latitude = start_lat
        self.longitude = start_lon
        self.altitude = 1839.0  # meters (Colorado Springs elevation)
        self.heading = 0.0
        self.speed = 0.0  # m/s
        self.fix_quality = 4  # RTK fix
        self.num_satellites = 12

    def update(self, forward: float = 0, turn: float = 0):
        """Update position based on movement.

        Args:
            forward: Forward movement (+1 = forward, -1 = backward)
            turn: Turn rate (+1 = right, -1 = left)
        """
        if turn != 0:
            self.heading += turn * 2.0  # degrees per update
            self.heading = self.heading % 360

        if forward != 0:
            distance = forward * 1.0  # meters per update
            heading_rad = math.radians(self.heading)

            lat_delta = (distance * math.cos(heading_rad)) / self.METERS_PER_DEGREE_LATITUDE
            self.latitude += lat_delta

            # Clamp latitude before using it for longitude calculation
            self.latitude = max(self.SAFE_LATITUDE_RANGE[0],
                               min(self.SAFE_LATITUDE_RANGE[1], self.latitude))

            cos_lat = math.cos(math.radians(self.latitude))
            if abs(cos_lat) < self.MINIMUM_SAFE_COS_LAT:
                cos_lat = math.copysign(self.MINIMUM_SAFE_COS_LAT, cos_lat)

            lon_delta = (distance * math.sin(heading_rad)) / (self.METERS_PER_DEGREE_LATITUDE * cos_lat)
            self.longitude += lon_delta

    def get_position(self) -> dict:
        """Get current GPS position.

        Returns:
            Dictionary with latitude, longitude, altitude, heading, timestamp
        """
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'heading': self.heading,
            'timestamp': time.time(),
            'quality': self.fix_quality,
            'num_satellites': self.num_satellites
        }
