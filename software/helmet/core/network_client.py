#!/usr/bin/env python3
"""Network client for Helmet-Mounted Unit (HMU) to communicate with BMU."""

import socket
import threading
import logging
import queue
import time
from typing import Optional, Dict, Any
from common.network_base import NetworkConnection
from common.protocol import MessageType, ConnectionStatus
from common.data_models import Position, FriendlyUnit, RFDetection, WiFiDetection

logger = logging.getLogger(__name__)


class HMUNetworkClient(NetworkConnection):
    """Network client for HMU to connect to BMU server."""

    def __init__(self, source_id: str, server_host: str = "192.168.200.2",
                 tcp_port: int = None, udp_port: int = None):
        """Initialize HMU network client.

        Args:
            source_id: Unique identifier (e.g., "WARLOCK-001-HMU")
            server_host: BMU IP address
            tcp_port: TCP port for reliable messages
            udp_port: UDP port for fast messages
        """
        super().__init__(is_server=False, source_id=source_id)

        self.server_host = server_host
        self.tcp_port = tcp_port or self.DEFAULT_PORT_TCP
        self.udp_port = udp_port or self.DEFAULT_PORT_UDP

        self._data_lock = threading.Lock()
        self.latest_data: Dict[str, Any] = {
            'gps_position': None,
            'team_positions': [],
            'rf_alerts': [],
            'wifi_alerts': [],
            'radio_status': None,
            'atak_data': None,
        }

        self.connection_type = "cable"

    def connect(self) -> bool:
        """Connect to BMU server.

        Returns:
            True if connection successful, False otherwise
        """
        logger.info(f"Connecting to BMU at {self.server_host}:{self.tcp_port}")

        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(self.TIMEOUT)
            self.tcp_socket.connect((self.server_host, self.tcp_port))
            logger.info("TCP connection established")

            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(('', 0))
            logger.info(f"UDP socket created on port {self.udp_socket.getsockname()[1]}")

            self.status = ConnectionStatus.CONNECTED
            self.last_heartbeat_received = time.time()

            self.start()

            return True

        except Exception as e:
            logger.error(f"Connection failed: {e}")
            self.status = ConnectionStatus.ERROR
            return False

    def start(self):
        """Start network threads."""
        super().start()

        tcp_send_thread = threading.Thread(target=self._tcp_send_loop, daemon=True)
        tcp_send_thread.start()
        self.threads.append(tcp_send_thread)

        tcp_recv_thread = threading.Thread(target=self._tcp_recv_loop, daemon=True)
        tcp_recv_thread.start()
        self.threads.append(tcp_recv_thread)

        udp_send_thread = threading.Thread(target=self._udp_send_loop, daemon=True)
        udp_send_thread.start()
        self.threads.append(udp_send_thread)

        udp_recv_thread = threading.Thread(target=self._udp_recv_loop, daemon=True)
        udp_recv_thread.start()
        self.threads.append(udp_recv_thread)

        heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        self.threads.append(heartbeat_thread)

        logger.info("Network threads started")

    def _tcp_send_loop(self):
        """TCP send loop."""
        while self.running:
            try:
                message = self.send_queue_tcp.get(timeout=0.1)
                self._send_tcp(message)
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"TCP send error: {e}")

    def _tcp_recv_loop(self):
        """TCP receive loop."""
        while self.running:
            message = self._recv_tcp()
            if message:
                self._dispatch_message(message)
                # Only update heartbeat timestamp for actual heartbeat messages
                if message.get("type") in ["heartbeat_bmu", "heartbeat"]:
                    self.last_heartbeat_received = message.get("timestamp", time.time())

    def _udp_send_loop(self):
        """UDP send loop."""
        while self.running:
            try:
                message = self.send_queue_udp.get(timeout=0.1)
                self._send_udp(message, (self.server_host, self.udp_port))
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"UDP send error: {e}")

    def _udp_recv_loop(self):
        """UDP receive loop."""
        while self.running:
            message, addr = self._recv_udp()
            if message:
                self._dispatch_message(message)
                # Only update heartbeat timestamp for actual heartbeat messages
                if message.get("type") in ["heartbeat_bmu", "heartbeat"]:
                    self.last_heartbeat_received = message.get("timestamp", time.time())

    def _heartbeat_loop(self):
        """Heartbeat send loop."""
        while self.running:
            self.send_heartbeat()

            if not self.monitor_connection() and self.status == ConnectionStatus.CONNECTED:
                logger.warning("Connection lost, attempting WiFi failover")
                self.attempt_wifi_failover()

            threading.Event().wait(self.HEARTBEAT_INTERVAL)

    def attempt_wifi_failover(self):
        """Attempt to failover to WiFi connection."""
        logger.warning("WiFi failover not yet implemented - TODO")
        # TODO: Implement WiFi connection logic
        pass

    def get_latest(self, data_type: str) -> Any:
        """Get latest data of specified type.

        Args:
            data_type: Type of data to retrieve (e.g., 'gps_position', 'team_positions')

        Returns:
            Latest data or None if not available
        """
        with self._data_lock:
            return self.latest_data.get(data_type)

    def register_default_handlers(self):
        """Register default message handlers that update latest_data cache."""

        def handle_gps_update(payload):
            with self._data_lock:
                self.latest_data['gps_position'] = payload

        def handle_team_positions(payload):
            with self._data_lock:
                self.latest_data['team_positions'] = payload.get('units', [])

        def handle_rf_alert(payload):
            with self._data_lock:
                alerts = self.latest_data.get('rf_alerts', [])
                alerts.append(payload)
                self.latest_data['rf_alerts'] = alerts[-10:]  # Keep last 10

        def handle_wifi_alert(payload):
            with self._data_lock:
                alerts = self.latest_data.get('wifi_alerts', [])
                alerts.append(payload)
                self.latest_data['wifi_alerts'] = alerts[-10:]  # Keep last 10

        def handle_radio_status(payload):
            with self._data_lock:
                self.latest_data['radio_status'] = payload

        def handle_atak_data(payload):
            with self._data_lock:
                self.latest_data['atak_data'] = payload

        def handle_heartbeat(payload):
            pass

        self.register_callback(MessageType.GPS_UPDATE, handle_gps_update)
        self.register_callback(MessageType.TEAM_POSITIONS, handle_team_positions)
        self.register_callback(MessageType.RF_ALERT, handle_rf_alert)
        self.register_callback(MessageType.WIFI_ALERT, handle_wifi_alert)
        self.register_callback(MessageType.RADIO_STATUS, handle_radio_status)
        self.register_callback(MessageType.ATAK_DATA, handle_atak_data)
        self.register_callback(MessageType.HEARTBEAT_BMU, handle_heartbeat)

        logger.info("Default message handlers registered")
