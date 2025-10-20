#!/usr/bin/env python3
"""TAK server client for WARLOCK blue-force tracking and POI display."""

import logging
import socket
import threading
import time
import uuid
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class TAKClient:
    """Client for connecting to TAK servers (ATAK, WinTAK, FreeTAKServer)."""

    DEFAULT_PORT = 8087
    POSITION_UPDATE_INTERVAL = 5.0
    STALE_TIMEOUT = 30.0

    def __init__(
        self,
        server_host: str,
        server_port: int = DEFAULT_PORT,
        callsign: str = "WARLOCK-001",
        team_name: str = "Cyan",
        team_role: str = "Team Member",
    ):
        """Initialize TAK client.

        Args:
            server_host: TAK server IP address (e.g., phone running ATAK)
            server_port: TAK server port (default 8087 for TCP CoT)
            callsign: Your callsign/identifier displayed in TAK
            team_name: Team color (Cyan, Yellow, Magenta, etc.)
            team_role: Your role (Team Member, Team Lead, HQ, etc.)
        """
        self.server_host = server_host
        self.server_port = server_port
        self.callsign = callsign
        self.team_name = team_name
        self.team_role = team_role

        self.uid = str(uuid.uuid4())
        self.socket = None
        self.running = False
        self.connected = False

        self.position_lock = threading.Lock()
        self.current_position: Optional[Dict] = None
        self.current_heading: Optional[float] = None

        self.pois_lock = threading.Lock()
        self.pois: List[Dict] = []

        self.send_thread = None
        self.recv_thread = None

    def connect(self) -> bool:
        """Connect to TAK server.

        Returns:
            True if connection successful
        """
        try:
            logger.info(f"Connecting to TAK server at {self.server_host}:{self.server_port}")
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10.0)
            self.socket.connect((self.server_host, self.server_port))
            self.connected = True
            logger.info(f"Connected to TAK server as {self.callsign}")

            self.running = True
            self.send_thread = threading.Thread(target=self._position_send_loop, daemon=True)
            self.send_thread.start()

            self.recv_thread = threading.Thread(target=self._message_recv_loop, daemon=True)
            self.recv_thread.start()

            return True

        except Exception as e:
            logger.error(f"Failed to connect to TAK server: {e}")
            self.connected = False
            return False

    def disconnect(self):
        """Disconnect from TAK server."""
        self.running = False
        self.connected = False

        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass
            self.socket = None

        if self.send_thread:
            self.send_thread.join(timeout=2.0)
        if self.recv_thread:
            self.recv_thread.join(timeout=2.0)

        logger.info("Disconnected from TAK server")

    def update_position(self, latitude: float, longitude: float, altitude: float = 0.0, heading: float = 0.0):
        """Update current position and heading.

        Args:
            latitude: Latitude in decimal degrees
            longitude: Longitude in decimal degrees
            altitude: Altitude in meters (default 0)
            heading: Heading in degrees (0-360, 0=North)
        """
        with self.position_lock:
            self.current_position = {
                "latitude": latitude,
                "longitude": longitude,
                "altitude": altitude,
            }
            self.current_heading = heading

    def get_pois(self) -> List[Dict]:
        """Get list of points of interest from TAK server.

        Returns:
            List of POI dictionaries with keys: uid, callsign, latitude, longitude, type
        """
        with self.pois_lock:
            return self.pois.copy()

    def _create_position_cot(self) -> Optional[str]:
        """Create CoT XML message for position update.

        Returns:
            CoT XML string or None if no position available
        """
        with self.position_lock:
            if not self.current_position:
                return None

            pos = self.current_position
            heading = self.current_heading or 0.0

        now = datetime.utcnow()
        stale = now + timedelta(seconds=self.STALE_TIMEOUT)

        time_str = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        stale_str = stale.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        event = ET.Element("event")
        event.set("version", "2.0")
        event.set("uid", self.uid)
        event.set("type", "a-f-G-U-C")
        event.set("time", time_str)
        event.set("start", time_str)
        event.set("stale", stale_str)
        event.set("how", "m-g")

        point = ET.SubElement(event, "point")
        point.set("lat", str(pos["latitude"]))
        point.set("lon", str(pos["longitude"]))
        point.set("hae", str(pos["altitude"]))
        point.set("ce", "10.0")
        point.set("le", "10.0")

        detail = ET.SubElement(event, "detail")

        contact = ET.SubElement(detail, "contact")
        contact.set("callsign", self.callsign)

        group = ET.SubElement(detail, "__group")
        group.set("name", self.team_name)
        group.set("role", self.team_role)

        track = ET.SubElement(detail, "track")
        track.set("course", str(heading))
        track.set("speed", "0.0")

        return ET.tostring(event, encoding="unicode")

    def _position_send_loop(self):
        """Background thread that continuously sends position updates."""
        while self.running and self.connected:
            try:
                cot_xml = self._create_position_cot()
                if cot_xml:
                    self._send_cot(cot_xml)
            except Exception as e:
                logger.error(f"Error sending position update: {e}")

            time.sleep(self.POSITION_UPDATE_INTERVAL)

    def _message_recv_loop(self):
        """Background thread that receives CoT messages from TAK server."""
        buffer = ""

        while self.running and self.connected:
            try:
                if not self.socket:
                    break

                data = self.socket.recv(8192)
                if not data:
                    logger.warning("TAK server connection closed")
                    self.connected = False
                    break

                buffer += data.decode("utf-8", errors="ignore")

                while "<event" in buffer and "</event>" in buffer:
                    start = buffer.find("<event")
                    end = buffer.find("</event>") + len("</event>")

                    if start != -1 and end > start:
                        message = buffer[start:end]
                        buffer = buffer[end:]

                        self._process_cot_message(message)

            except socket.timeout:
                continue
            except Exception as e:
                logger.error(f"Error receiving TAK message: {e}")
                self.connected = False
                break

    def _send_cot(self, cot_xml: str):
        """Send CoT XML message to TAK server.

        Args:
            cot_xml: CoT XML string
        """
        if not self.socket or not self.connected:
            return

        try:
            self.socket.sendall(cot_xml.encode("utf-8"))
        except Exception as e:
            logger.error(f"Error sending CoT message: {e}")
            self.connected = False

    def _process_cot_message(self, cot_xml: str):
        """Process received CoT message and extract POIs.

        Args:
            cot_xml: CoT XML string
        """
        try:
            root = ET.fromstring(cot_xml)

            uid = root.get("uid")
            event_type = root.get("type", "")

            if uid == self.uid:
                return

            if not event_type.startswith("a-"):
                return

            point = root.find("point")
            if point is None:
                return

            lat = float(point.get("lat", 0))
            lon = float(point.get("lon", 0))

            detail = root.find("detail")
            callsign = "Unknown"
            if detail is not None:
                contact = detail.find("contact")
                if contact is not None:
                    callsign = contact.get("callsign", "Unknown")

            poi = {
                "uid": uid,
                "callsign": callsign,
                "latitude": lat,
                "longitude": lon,
                "type": event_type,
            }

            with self.pois_lock:
                existing = next((p for p in self.pois if p["uid"] == uid), None)
                if existing:
                    self.pois.remove(existing)
                self.pois.append(poi)

                if len(self.pois) > 100:
                    self.pois = self.pois[-100:]

            logger.debug(f"Received POI: {callsign} at ({lat}, {lon})")

        except Exception as e:
            logger.debug(f"Error parsing CoT message: {e}")
