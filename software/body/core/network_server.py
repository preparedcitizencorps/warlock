#!/usr/bin/env python3
"""Network server for Body-Mounted Unit (BMU) to serve HMU clients."""

import json
import logging
import socket
import threading
import time
from typing import Any, Dict, List

from common.network_base import NetworkConnection
from common.protocol import ConnectionStatus, MessageType

logger = logging.getLogger(__name__)


class BMUNetworkServer(NetworkConnection):
    """Network server for BMU to accept HMU connections."""

    SOCKET_TIMEOUT = 1.0  # seconds

    def __init__(self, source_id: str, tcp_port: int = None, udp_port: int = None):
        """Initialize BMU network server.

        Args:
            source_id: Unique identifier (e.g., "WARLOCK-001-BMU")
            tcp_port: TCP port for reliable messages
            udp_port: UDP port for fast messages
        """
        super().__init__(is_server=True, source_id=source_id)

        self.tcp_port = tcp_port or self.DEFAULT_PORT_TCP
        self.udp_port = udp_port or self.DEFAULT_PORT_UDP

        # Connected clients
        self.clients: List[Dict[str, Any]] = []
        self.clients_lock = threading.Lock()

    def start(self):
        """Start network server and listen for connections."""
        super().start()

        try:
            # Create TCP server socket
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tcp_socket.bind(("0.0.0.0", self.tcp_port))
            self.tcp_socket.listen(5)
            logger.info(f"TCP server listening on port {self.tcp_port}")

            # Create UDP socket
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind(("0.0.0.0", self.udp_port))
            self.udp_socket.settimeout(self.SOCKET_TIMEOUT)
            logger.info(f"UDP server listening on port {self.udp_port}")

            self.status = ConnectionStatus.CONNECTED

            # Start accept thread
            accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
            accept_thread.start()
            self.threads.append(accept_thread)

            # Start UDP receive thread
            udp_recv_thread = threading.Thread(target=self._udp_recv_loop, daemon=True)
            udp_recv_thread.start()
            self.threads.append(udp_recv_thread)

            # Heartbeat thread
            heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            heartbeat_thread.start()
            self.threads.append(heartbeat_thread)

            logger.info("Network server started")

        except Exception as e:
            logger.error(f"Failed to start server: {e}")
            self.status = ConnectionStatus.ERROR
            raise

    def _accept_loop(self):
        """Accept incoming TCP connections."""
        while self.running:
            try:
                client_socket, addr = self.tcp_socket.accept()
                client_socket.settimeout(self.SOCKET_TIMEOUT)
                logger.info(f"New connection from {addr}")

                client_info = {"socket": client_socket, "addr": addr, "last_seen": 0}

                with self.clients_lock:
                    self.clients.append(client_info)

                # Start thread to handle this client
                client_thread = threading.Thread(target=self._handle_client, args=(client_info,), daemon=True)
                client_thread.start()

            except Exception as e:
                if self.running:
                    logger.error(f"Accept error: {e}")

    def _handle_client(self, client_info: Dict):
        """Handle messages from a connected client."""
        client_socket = client_info["socket"]

        while self.running:
            try:
                # Receive length prefix
                length_bytes = self._recv_exactly_from(client_socket, 4)
                if not length_bytes:
                    break

                length = int.from_bytes(length_bytes, "big")

                # Receive message
                data = self._recv_exactly_from(client_socket, length)
                if not data:
                    break

                message = json.loads(data.decode("utf-8"))

                # Update last seen
                client_info["last_seen"] = message.get("timestamp", 0)

                # Process message (TODO: implement handlers)
                logger.debug(f"Received from {client_info['addr']}: {message['type']}")

            except Exception as e:
                logger.error(f"Client handler error: {e}")
                break

        # Remove client
        with self.clients_lock:
            if client_info in self.clients:
                self.clients.remove(client_info)
                logger.info(f"Client disconnected: {client_info['addr']}")

        try:
            client_socket.close()
        except Exception as e:
            logger.debug(f"Error closing client socket: {e}")

    def _recv_exactly_from(self, sock: socket.socket, n: int) -> bytes:
        """Receive exactly n bytes from socket."""
        data = b""
        while len(data) < n:
            try:
                chunk = sock.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except (socket.timeout, OSError) as e:
                logger.debug(f"Socket receive error: {e}")
                return None
        return data

    def _udp_recv_loop(self):
        """UDP receive loop."""
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(self.BUFFER_SIZE)
                message = json.loads(data.decode("utf-8"))
                logger.debug(f"Received UDP from {addr}: {message['type']}")
                # TODO: Process UDP messages
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    logger.error(f"UDP receive error: {e}")

    def _heartbeat_loop(self):
        """Send heartbeat to all connected clients."""
        while self.running:
            self.send_heartbeat()
            time.sleep(self.HEARTBEAT_INTERVAL)

    def broadcast_gps(self, position: Dict[str, Any]):
        """Broadcast GPS position to all connected clients.

        Args:
            position: GPS position dictionary
        """
        self.broadcast_message(MessageType.GPS_UPDATE, position, reliable=False)

    def broadcast_message(self, msg_type: MessageType, payload: Dict[str, Any], reliable: bool = True):
        """Broadcast message to all connected clients.

        Args:
            msg_type: Message type
            payload: Message payload
            reliable: Use TCP if True, UDP if False
        """
        message = {"type": msg_type.value, "source_id": self.source_id, "timestamp": time.time(), "payload": payload}

        if reliable:
            # Send via TCP to all clients
            with self.clients_lock:
                for client_info in self.clients:
                    try:
                        self._send_tcp_to(client_info["socket"], message)
                    except Exception as e:
                        logger.error(f"Failed to send to {client_info['addr']}: {e}")
        else:
            # Send via UDP to all clients
            data = json.dumps(message).encode("utf-8")
            with self.clients_lock:
                for client_info in self.clients:
                    try:
                        self.udp_socket.sendto(data, client_info["addr"])
                    except Exception as e:
                        logger.error(f"Failed to send UDP to {client_info['addr']}: {e}")

    def _send_tcp_to(self, sock: socket.socket, message: Dict):
        """Send message via TCP to specific socket."""
        data = json.dumps(message).encode("utf-8")
        length = len(data)
        sock.sendall(length.to_bytes(4, "big") + data)

    def has_clients(self) -> bool:
        """Check if any clients are connected.

        Returns:
            True if clients connected, False otherwise
        """
        with self.clients_lock:
            return len(self.clients) > 0
