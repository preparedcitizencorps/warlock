#!/usr/bin/env python3
"""Base networking classes for WARLOCK communication."""

import json
import logging
import socket
import threading
import time
from queue import Empty, Queue
from typing import Any, Callable, Dict, Optional

from common.protocol import ConnectionStatus, MessageType, Transport, validate_message

logger = logging.getLogger(__name__)


class NetworkConnection:
    """Base class for network connection management."""

    DEFAULT_PORT_TCP = 5000
    DEFAULT_PORT_UDP = 5001
    HEARTBEAT_INTERVAL = 1.0  # seconds
    TIMEOUT = 5.0  # seconds
    BUFFER_SIZE = 65536  # 64KB

    def __init__(self, is_server: bool, source_id: str):
        """Initialize network connection.

        Args:
            is_server: True if this is the server, False for client
            source_id: Unique identifier (e.g., "WARLOCK-001")
        """
        self.is_server = is_server
        self.source_id = source_id
        self.status = ConnectionStatus.DISCONNECTED

        # Sockets
        self.tcp_socket: Optional[socket.socket] = None
        self.udp_socket: Optional[socket.socket] = None

        # Queues
        self.send_queue_tcp = Queue()
        self.send_queue_udp = Queue()
        self.recv_callbacks: Dict[str, Callable] = {}

        # Threading
        self.running = False
        self.threads = []

        # Heartbeat tracking
        self.last_heartbeat_sent = 0
        self.last_heartbeat_received = 0

    def register_callback(self, message_type: MessageType, callback: Callable):
        """Register handler for specific message type.

        Args:
            message_type: Message type to handle
            callback: Function to call with message payload
        """
        self.recv_callbacks[message_type.value] = callback

    def send_message(self, msg_type: MessageType, payload: Dict[str, Any], reliable: bool = True):
        """Send message via TCP (reliable) or UDP (fast).

        Args:
            msg_type: Message type
            payload: Message payload dictionary
            reliable: Use TCP if True, UDP if False
        """
        message = {"type": msg_type.value, "source_id": self.source_id, "timestamp": time.time(), "payload": payload}

        if reliable:
            self.send_queue_tcp.put(message)
        else:
            self.send_queue_udp.put(message)

    def _send_tcp(self, message: Dict[str, Any]):
        """Send message via TCP."""
        if not self.tcp_socket:
            logger.warning("TCP socket not connected")
            return

        try:
            data = json.dumps(message).encode("utf-8")
            length = len(data)
            # Send length prefix (4 bytes) + data
            self.tcp_socket.sendall(length.to_bytes(4, "big") + data)
        except Exception as e:
            logger.error(f"TCP send error: {e}")
            self.status = ConnectionStatus.ERROR

    def _send_udp(self, message: Dict[str, Any], addr: tuple):
        """Send message via UDP."""
        if not self.udp_socket:
            logger.warning("UDP socket not created")
            return

        try:
            data = json.dumps(message).encode("utf-8")
            self.udp_socket.sendto(data, addr)
        except Exception as e:
            logger.error(f"UDP send error: {e}")

    def _recv_tcp(self) -> Optional[Dict[str, Any]]:
        """Receive message from TCP socket."""
        if not self.tcp_socket:
            return None

        try:
            # Receive length prefix
            length_bytes = self._recv_exactly(4)
            if not length_bytes:
                return None

            length = int.from_bytes(length_bytes, "big")

            # Receive message data
            data = self._recv_exactly(length)
            if not data:
                return None

            message = json.loads(data.decode("utf-8"))

            if validate_message(message):
                return message
            else:
                logger.warning("Received invalid message format")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logger.error(f"TCP receive error: {e}")
            self.status = ConnectionStatus.ERROR
            return None

    def _recv_exactly(self, n: int) -> Optional[bytes]:
        """Receive exactly n bytes from TCP socket."""
        data = b""
        while len(data) < n:
            try:
                chunk = self.tcp_socket.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except socket.timeout:
                return None
            except Exception as e:
                logger.error(f"Socket receive error: {e}")
                return None
        return data

    def _recv_udp(self) -> tuple[Optional[Dict[str, Any]], Optional[tuple]]:
        """Receive message from UDP socket."""
        if not self.udp_socket:
            return None, None

        try:
            data, addr = self.udp_socket.recvfrom(self.BUFFER_SIZE)
            message = json.loads(data.decode("utf-8"))

            if validate_message(message):
                return message, addr
            else:
                logger.warning("Received invalid UDP message format")
                return None, None

        except socket.timeout:
            return None, None
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return None, None
        except Exception as e:
            logger.error(f"UDP receive error: {e}")
            return None, None

    def _dispatch_message(self, message: Dict[str, Any]):
        """Dispatch received message to registered callback."""
        msg_type = message.get("type")
        if msg_type in self.recv_callbacks:
            try:
                self.recv_callbacks[msg_type](message["payload"])
            except Exception as e:
                logger.error(f"Callback error for {msg_type}: {e}")
        else:
            logger.debug(f"No callback registered for message type: {msg_type}")

    def monitor_connection(self) -> bool:
        """Check if connection is alive based on heartbeat.

        Returns:
            True if connection is alive, False otherwise
        """
        if self.status != ConnectionStatus.CONNECTED:
            return False

        time_since_heartbeat = time.time() - self.last_heartbeat_received
        if time_since_heartbeat > self.TIMEOUT:
            logger.warning(f"Connection timeout ({time_since_heartbeat:.1f}s since last heartbeat)")
            return False

        return True

    def send_heartbeat(self):
        """Send heartbeat message."""
        now = time.time()
        if now - self.last_heartbeat_sent >= self.HEARTBEAT_INTERVAL:
            msg_type = MessageType.HEARTBEAT_HMU if not self.is_server else MessageType.HEARTBEAT_BMU
            self.send_message(msg_type, {"status": self.status.value}, reliable=False)
            self.last_heartbeat_sent = now

    def start(self):
        """Start network threads."""
        self.running = True
        logger.info(f"Network connection starting (source_id={self.source_id})")

    def stop(self):
        """Stop network threads and close sockets."""
        logger.info("Stopping network connection")
        self.running = False

        # Wait for threads to finish
        for thread in self.threads:
            thread.join(timeout=2.0)

        # Close sockets
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except Exception as e:
                logger.debug(f"Error closing TCP socket: {e}")

        if self.udp_socket:
            try:
                self.udp_socket.close()
            except Exception as e:
                logger.debug(f"Error closing UDP socket: {e}")

        self.status = ConnectionStatus.DISCONNECTED
        logger.info("Network connection stopped")
