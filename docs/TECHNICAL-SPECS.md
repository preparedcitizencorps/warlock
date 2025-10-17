# WARLOCK TECHNICAL SPECIFICATIONS

---

## NETWORK PROTOCOL

### Physical Layer

- **Primary:** USB-C Ethernet (RNDIS/CDC-ECM)
- **Failover:** WiFi 6E (6 GHz band)
- **Addressing:** Static IP (HMU: 192.168.200.1, BMU: 192.168.200.2)

### Transport Layer

- **TCP Port 5000:** Reliable messages (detections, alerts, commands)
- **UDP Port 5001:** Low-latency data (GPS, telemetry, sensor feeds)

### Message Format

```json
{
  "type": "gps_update",
  "source_id": "WARLOCK-001-BMU",
  "timestamp": 1729166400.123,
  "payload": {
    "latitude": 38.8339,
    "longitude": -104.8214,
    "altitude": 1839.0,
    "heading": 270.5
  }
}
```

### Message Types

**HMU → BMU:**

- `heartbeat_hmu` (UDP, 1 Hz)
- `detection` (TCP, on event)
- `sensor_telemetry` (UDP, 10 Hz)
- `user_input` (TCP, on event)

**BMU → HMU:**

- `heartbeat_bmu` (UDP, 1 Hz)
- `gps_update` (UDP, 10 Hz)
- `team_positions` (UDP, 5 Hz)
- `rf_alert` (TCP, on event)
- `wifi_alert` (TCP, on event)

---

## GPS CONFIGURATION

### Primary GPS (BMU)

- **Module:** U-blox ZED-F9P
- **Antenna:** External active, 3m SMA cable
- **Mount:** Helmet rear (maintains sky view when prone)
- **Accuracy:** RTK cm-level (with base station)
- **Update Rate:** 10 Hz
- **Interface:** UART via gpsd

### Backup GPS (HMU)

- **Module:** U-blox NEO-M9N
- **Antenna:** Integrated patch
- **Accuracy:** Meter-level
- **Update Rate:** 25 Hz (for IMU fusion)
- **Fallback:** Activates if BMU GPS quality < threshold

### Fusion Logic

```python
if primary_gps.hdop < 1.0 and sats > 8:
    use_primary()  # RTK precision
elif backup_gps.hdop < 2.0 and sats > 6:
    use_backup()   # Degraded mode
else:
    use_imu_dead_reckoning()  # Last resort
```

---

## SIGINT SPECIFICATIONS

### RF Detection (RTL-SDR)

- **Frequency Range:** 0.5 MHz - 1.7 GHz
- **Bandwidth:** 3.2 MHz instantaneous
- **Sensitivity:** -148 dBm (LoRa), -120 dBm (FM)
- **Scan Rate:** Full spectrum every 5 seconds
- **Detection Range:** 150-500m (radio emitters)

### WiFi CSI Detection

- **Hardware:** Intel AX210 (WiFi 6E)
- **Method:** Channel State Information analysis
- **Detection:** Motion through walls via multipath changes
- **Range:** 5-15m penetration
- **Update Rate:** Continuous (100 Hz CSI samples)

### Triangulation

- **Method:** Time-difference-of-arrival (TDOA)
- **Requirements:** 3+ units detecting same signal
- **Accuracy:** ±50m (RF), ±2m (WiFi)
- **Latency:** 1-2 seconds for position calculation

---

## MESH NETWORKING

### WiFi Mesh (802.11s)

- **Standard:** IEEE 802.11s (mesh mode)
- **Frequency:** 5 GHz (DFS channels 149-165)
- **Range:** 100-300m line-of-sight
- **Bandwidth:** 1-10 Mbps effective
- **Latency:** 10-50ms
- **Use Case:** Squad-level (4-8 members)

### LoRa Mesh

- **Module:** Semtech SX1262
- **Frequency:** 915 MHz (US ISM band)
- **Power:** 22 dBm (158mW)
- **Range:** 2-10km line-of-sight
- **Bandwidth:** 5-50 kbps
- **Latency:** 100-500ms
- **Use Case:** Inter-squad relay

### Auto-Selection

```python
if distance < 300m and wifi_peer_reachable:
    use_wifi()    # Fast, high-bandwidth
else:
    use_lora()    # Slow, long-range
```

---

## RADIO SPECIFICATIONS

### SA818 Module

- **Type:** VHF/UHF transceiver
- **Frequency:** 134-174 MHz (VHF), 400-480 MHz (UHF)
- **Power:** 1W / 5W selectable
- **Modulation:** FM, 12.5 kHz / 25 kHz
- **Compatibility:** Baofeng (same frequencies)
- **Interface:** UART (115200 baud)

### PTT Interface

- **Input:** Momentary switch (military connector)
- **Detection:** GPIO interrupt
- **Debounce:** 50ms
- **Action:** Trigger SA818 TX, notify HMU (HUD indicator)

---

## POWER SPECIFICATIONS

### HMU Power Budget

| Component | Idle | Load | Notes |
|-----------|------|------|-------|
| Pi 5 | 8W | 12W | Base consumption |
| Hailo-8L | 0W | 5W | Active during inference |
| Camera | 2W | 2W | Constant |
| GPS | 0.5W | 0.5W | Constant |
| IMU | 0.1W | 0.1W | Constant |
| **TOTAL** | **10.6W** | **19.6W** | |

**Battery:** 10Ah @ 5V (50 Wh)
**Runtime:** 2.5-5 hours (load-dependent)

### BMU Power Budget

| Component | Idle | Load | Notes |
|-----------|------|------|-------|
| Pi 5 | 8W | 15W | Base consumption |
| GPS | 1W | 1W | ZED-F9P + antenna |
| WiFi | 1W | 3W | Active scanning |
| RTL-SDR | 2W | 2W | Continuous |
| Radio (RX) | 2W | 2W | Listening |
| Radio (TX) | - | 6W | 5W output, peak |
| LoRa | 0.1W | 0.5W | Intermittent |
| IMU | 0.1W | 0.1W | Constant |
| **TOTAL** | **14.2W** | **29.6W** | |

**Battery:** 20Ah @ 12V (240 Wh) with buck converter
**Runtime:** 8-17 hours (load-dependent)

### Power Modes

| Mode | YOLO FPS | RF Scan | HMU Runtime | BMU Runtime |
|------|----------|---------|-------------|-------------|
| Combat | 60 | Full | 2.5h | 8h |
| Patrol | 30 | Reduced | 4h | 12h |
| Standby | 15 | Off | 5h | 17h |

---

## THERMAL MANAGEMENT

### HMU Cooling

- **Passive:** Aluminum enclosure (thermal pads to Pi/Hailo)
- **Active:** 20mm fan (temp-controlled, activates @ 70°C)
- **Monitoring:** `vcgencmd measure_temp` every 30 sec
- **Throttle:** Reduce YOLO FPS if temp > 75°C
- **Critical:** Shutdown if temp > 85°C

### BMU Cooling

- **Passive:** Aluminum enclosure with ventilation slots
- **Active:** 40mm fan (continuous, low speed)
- **Monitoring:** Same as HMU
- **Note:** Lower thermal load (no AI inference)

---

## SOFTWARE ARCHITECTURE

### HMU Components

```
helmet_main.py
├─ CameraController (OpenCV capture)
├─ NetworkClient (TCP/UDP to BMU)
├─ PluginManager (HUD rendering)
│  ├─ YOLODetectionPlugin (Hailo inference)
│  ├─ CompassPlugin (heading display)
│  ├─ MiniMapPlugin (tactical overlay)
│  ├─ FPSCounterPlugin (performance)
│  └─ AutoExposurePlugin (low-light)
└─ InputManager (keyboard/PTT)
```

### BMU Components

```
body_main.py
├─ NetworkServer (accept HMU connections)
├─ GPSController (ZED-F9P via gpsd)
├─ RFScanner (RTL-SDR) [Phase 3]
├─ WiFiCSI (Intel AX210) [Phase 3]
├─ RadioController (SA818) [Phase 4]
├─ MeshManager (WiFi + LoRa) [Phase 4]
└─ ATAKBridge (CoT messages) [Phase 5]
```

### Plugin System

- **Base Class:** `HUDPlugin` (in `common/plugin_base.py`)
- **Metadata:** Name, version, dependencies
- **Lifecycle:** `initialize()`, `update()`, `render()`, `cleanup()`
- **Hot Reload:** Press `P` in HMU to reload plugins

---

## DATA MODELS

### Position

```python
@dataclass
class Position:
    latitude: float
    longitude: float
    altitude: float
    heading: float
    timestamp: float
    quality: int       # GPS fix (0-9)
    num_satellites: int
```

### Detection

```python
@dataclass
class Detection:
    class_id: int      # YOLO class
    class_name: str    # "person", "vehicle", etc.
    confidence: float  # 0.0-1.0
    bbox: List[int]    # [x, y, width, height]
    bearing: float     # Relative to user heading
    distance: float    # Estimated meters
    timestamp: float
```

### RFDetection

```python
@dataclass
class RFDetection:
    frequency: float       # Hz
    signal_strength: float # dBm
    bearing: float         # Degrees (if triangulated)
    location: Position     # If triangulated
    classification: str    # "radio", "drone", "jammer"
    timestamp: float
```

---

## TESTING

### Unit Tests

```bash
cd software
pytest tests/ -v
```

### Integration Test (Local)

```bash
# Terminal 1
python3 body/body_main.py

# Terminal 2
python3 helmet/helmet_main.py
```

### Field Test Checklist

- [ ] GPS lock within 60 seconds
- [ ] HMU connects to BMU
- [ ] YOLO detection working (30+ FPS)
- [ ] Map displays correct position
- [ ] Compass shows correct heading
- [ ] BMU disconnection → HMU switches to backup GPS
- [ ] Cable disconnect → WiFi failover within 5 seconds
- [ ] System runs for 3+ hours without crash

---

## PERFORMANCE TARGETS

| Metric | Target | Measured |
|--------|--------|----------|
| HMU Boot Time | < 30 sec | TBD |
| BMU Boot Time | < 45 sec | TBD |
| GPS Lock Time | < 60 sec | TBD |
| Connection Latency | < 5 ms | TBD |
| YOLO Inference | 30+ FPS | TBD |
| End-to-End Latency | < 100 ms | TBD |
| System Uptime | > 3 hours | TBD |

---

*Document Revision: 2025-10-17*
*System Version: Phase 1*
