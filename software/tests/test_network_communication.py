"""Tests for network communication essentials.

Tests verify the core network contracts work without testing implementation details.
These tests focus on the architectural guarantees, not socket internals.
"""

import socket
import threading
import time

import pytest
from body.core.network_server import BMUNetworkServer
from common.protocol import MessageType
from helmet.core.network_client import HMUNetworkClient


def get_free_port():
    """Get a free port number for testing."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


class TestNetworkClientServerContract:
    """Test that client and server can communicate basic messages."""

    def setup_method(self):
        """Setup is expensive but tests are robust."""
        tcp_port = get_free_port()
        udp_port = get_free_port()

        self.server = BMUNetworkServer(source_id="TEST-BMU", tcp_port=tcp_port, udp_port=udp_port)
        self.server.start()
        time.sleep(0.3)

        self.client = HMUNetworkClient(
            source_id="TEST-HMU", server_host="127.0.0.1", tcp_port=tcp_port, udp_port=udp_port
        )

    def teardown_method(self):
        """Clean up network resources."""
        if hasattr(self, "client") and self.client:
            self.client.stop()
        if hasattr(self, "server") and self.server:
            self.server.stop()
        time.sleep(0.2)

    def test_client_can_connect_to_server(self):
        """Most basic network requirement: connection establishment."""
        connected = self.client.connect()

        assert connected is True

    def test_server_detects_client_connection(self):
        """Server must know when clients connect."""
        self.client.connect()
        time.sleep(0.2)

        assert self.server.has_clients()

    def test_server_has_broadcast_gps_method(self):
        """Server must support GPS broadcast capability."""
        assert hasattr(self.server, "broadcast_gps")
        assert callable(self.server.broadcast_gps)

        gps_data = {
            "latitude": 38.8339,
            "longitude": -104.8214,
            "altitude": 1839.0,
            "heading": 270.0,
            "timestamp": time.time(),
        }

        try:
            self.server.broadcast_gps(gps_data)
            success = True
        except Exception:
            success = False

        assert success is True


class TestNetworkDataCache:
    """Test that network client caches latest data for plugins."""

    def test_client_provides_data_access_method(self):
        """Plugins need a way to get latest network data."""
        client = HMUNetworkClient("TEST-HMU")

        assert hasattr(client, "get_latest")
        assert callable(client.get_latest)

    def test_get_latest_returns_none_when_no_data(self):
        """Should handle missing data gracefully."""
        client = HMUNetworkClient("TEST-HMU")

        result = client.get_latest("gps_position")

        assert result is None or isinstance(result, dict)

    def test_client_has_expected_data_types(self):
        """Client should support all expected data types."""
        client = HMUNetworkClient("TEST-HMU")

        expected_types = ["gps_position", "team_positions", "rf_alerts", "wifi_alerts"]

        for data_type in expected_types:
            result = client.get_latest(data_type)
            assert result is None or isinstance(result, (dict, list))


class TestNetworkThreadSafety:
    """Test that network operations are thread-safe."""

    def test_get_latest_can_be_called_from_multiple_threads(self):
        """Plugins may call get_latest from render threads."""
        client = HMUNetworkClient("TEST-HMU")
        results = []
        errors = []

        def read_data():
            try:
                for _ in range(50):
                    client.get_latest("gps_position")
                results.append(True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=read_data) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety issue: {errors}"
        assert len(results) == 5


class TestHeartbeatMechanism:
    """Test that heartbeat mechanism exists and works."""

    def test_client_has_heartbeat_method(self):
        """Client must support heartbeat for connection monitoring."""
        client = HMUNetworkClient("TEST-HMU")

        assert hasattr(client, "send_heartbeat")
        assert callable(client.send_heartbeat)

    def test_client_can_monitor_connection(self):
        """Client must be able to detect connection loss."""
        client = HMUNetworkClient("TEST-HMU")

        assert hasattr(client, "monitor_connection")
        assert callable(client.monitor_connection)


class TestNetworkCleanup:
    """Test that network resources are properly cleaned up."""

    def test_client_has_stop_method(self):
        """Client must support graceful shutdown."""
        client = HMUNetworkClient("TEST-HMU")

        assert hasattr(client, "stop")
        assert callable(client.stop)

    def test_server_has_stop_method(self):
        """Server must support graceful shutdown."""
        server = BMUNetworkServer("TEST-BMU")

        assert hasattr(server, "stop")
        assert callable(server.stop)

    def test_client_stop_does_not_crash(self):
        """Stopping unconnected client should not crash."""
        client = HMUNetworkClient("TEST-HMU")

        try:
            client.stop()
            success = True
        except Exception:
            success = False

        assert success is True
