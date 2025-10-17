# WARLOCK SYSTEM OVERVIEW

**Wearable Augmented Reality & Linked Operational Combat Kit**

---

## MISSION

Tactical HUD system providing real-time situational awareness through AI detection, sensor fusion, and networked coordination.

---

## SYSTEM CONFIGURATION

### Two-Unit Architecture

**HELMET-MOUNTED UNIT (HMU)**

- Visual sensing (low-light + thermal)
- AI object detection (YOLO11)
- HUD rendering and display
- Backup GPS and IMU

**BODY-MOUNTED UNIT (BMU)**

- Primary GPS (RTK-capable)
- Radio communications (VHF/UHF)
- SIGINT (RF + WiFi detection)
- Mesh networking (squad coordination)
- ATAK integration

**CONNECTION:** USB-C cable (1Gbps, <5ms latency) with WiFi 6E failover

---

## CAPABILITIES

### Visual Detection (HMU)

- Low-light camera: 50-200m range
- Thermal imaging: 50-300m range (Phase 3)
- AI classification: humans, weapons, vehicles, drones (YOLO11)
- Friend/foe identification: Planned Phase 4 (requires custom training data, identity database, and IFF transponder integration)

### RF Detection (BMU)

- WiFi CSI: 5-15m through-wall detection
- RTL-SDR scanning: 150-500m radio emitter location
- Triangulation: Multi-unit coordination for precise targeting

### Communications (BMU)

- SA818 radio: VHF/UHF
- WiFi mesh: 0-300m squad coordination
- LoRa mesh: 300m-5km inter-squad relay
- ATAK bridge: Integration with standard TAK servers

---

## HARDWARE BOM

### HMU Components

| Item | Model | Purpose | Cost |
|------|-------|---------|------|
| SBC | Raspberry Pi 5 (8GB) | Processing | $80 |
| AI | Raspberry Pi AI Kit (Hailo-8L) | YOLO inference | $70 |
| Camera | IMX462 sensor | Low-light vision | $60 |
| Thermal | FLIR Lepton 3.5 | Heat signatures | $230 |
| Display | Rokid Max | AR glasses | $440 |
| IMU | BNO085 | Heading/orientation | $20 |
| GPS | U-blox NEO-M9N | Backup positioning | $40 |
| Battery | 10Ah @ 5V | 3hr runtime | $40 |
| **TOTAL** | | | **~$980** |

### BMU Components

| Item | Model | Purpose | Cost |
|------|-------|---------|------|
| SBC | Raspberry Pi 5 (8GB) | Processing | $80 |
| GPS | U-blox ZED-F9P | RTK positioning | $190 |
| Antenna | Active GPS | External mount | $15 |
| WiFi | Intel AX210 | CSI + mesh | $25 |
| SDR | RTL-SDR v4 | RF scanning | $40 |
| Radio | SA818 module | Voice comms | $25 |
| LoRa | SX1262 module | Long-range mesh | $15 |
| IMU | BNO085 | Body orientation | $20 |
| Battery | 20Ah @ 12V | 8hr runtime | $80 |
| **TOTAL** | | | **~$490** |

**SYSTEM TOTAL:** ~$1,470 per unit

---

## DEPLOYMENT

### HMU Setup

1. Flash Raspberry Pi OS to microSD
2. Install dependencies: `pip install -r helmet/requirements.txt`
3. Install Raspberry Pi AI Kit (Hailo-8L) drivers
4. Configure network in `helmet/helmet_config.yaml`
5. Test standalone: `python3 helmet/helmet_main.py --standalone`

**See:** `software/helmet/INSTALL.md`

### BMU Setup

1. Flash Raspberry Pi OS to microSD
2. Install dependencies: `pip install -r body/requirements.txt`
3. Configure GPS (gpsd), RTL-SDR, WiFi mesh
4. Set static IP for HMU connection
5. Test: `python3 body/body_main.py`

**See:** `software/body/INSTALL.md`

---

## OPERATION

### Startup Sequence

1. Power on BMU (wait for GPS lock ~30 sec)
2. Power on HMU
3. HMU connects to BMU automatically
4. Verify connection: Green indicator on HUD

### Controls

- `H` - Help overlay
- `Q` - Quit
- `P` - Plugin panel (hot-reload)
- `Y` - Toggle YOLO detection
- `M` - Toggle map
- `F` - Toggle FPS counter

### Failure Modes

**BMU Disconnected:** HMU continues with backup GPS, no RF/team data
**GPS Lost:** IMU dead reckoning, position drift over time
**Cable Disconnected:** Auto-failover to WiFi within 2 seconds

---

## PERFORMANCE

### HMU

- YOLO inference: 30-60 FPS (Hailo accelerator)
- Camera latency: 16-33ms (30 FPS capture)
- Power draw: 15-20W
- Runtime: 3-5 hours (combat mode)

### BMU

- GPS update: 10 Hz
- RF scan: Full spectrum every 5 seconds
- WiFi CSI: Continuous monitoring
- Power draw: 20-30W
- Runtime: 6-10 hours

### Network

- Cable: 1-5ms latency, 5 Gbps
- WiFi failover: 5-10ms latency, 100 Mbps
- Required bandwidth: 150 Kbps (actual)

---

## DEVELOPMENT PHASES

**Phase 1 - Network Foundation** ✅ COMPLETE

- Two-Pi architecture implemented
- HMU/BMU communication protocol operational
- GPS data flowing

**Phase 2 - Hardware Integration** 📋 CURRENT

- Real GPS modules (replace simulator)
- IMU integration (BNO085)
- Thermal camera (Lepton 3.5)

**Phase 3 - SIGINT** 📋 PLANNED

- RTL-SDR RF scanning
- WiFi CSI detection
- Alert display on HUD

**Phase 4 - Communications** 📋 PLANNED

- SA818 radio controller
- PTT handler
- Mesh networking (WiFi + LoRa)

**Phase 5 - ATAK Integration** 📋 PLANNED

- CoT message publishing
- Team position sharing
- Waypoint navigation

**Phase 6 - Field Hardening** 📋 PLANNED

- Weatherproofing
- Custom enclosures
- 3D-printed helmet mount

---

## TROUBLESHOOTING

### HMU Issues

**Camera not working:** `ls /dev/video*` to verify device
**YOLO slow:** Check Hailo installation with `hailo-verify`
**No BMU connection:** Verify IP in `helmet_config.yaml`, try `--standalone`

### BMU Issues

**No GPS lock:** Check antenna placement, run `cgps` to test
**RF scanner failing:** Blacklist DVB driver, test with `rtl_test`
**WiFi mesh not connecting:** Verify mesh ID matches, check `iw dev mesh0 station dump`

### Network Issues

**High latency:** Check cable connection, monitor with `ping 192.168.200.2`
**Frequent disconnects:** Enable WiFi failover, check cable quality
**No data flow:** Verify firewall allows ports 5000 (TCP) and 5001 (UDP)

---

## SAFETY

- **DO NOT** stare directly at IR emitters with NVG active
- **DO NOT** transmit on radio without proper license
- **DO NOT** use thermal camera to view sun or laser sources
- Maintain situational awareness - HUD is supplemental, not primary
- Test all systems in controlled environment before field use

---

## SUPPORT

**Documentation:** `github.com/preparedcitizencorps/warlock`
**Discord:** `discord.gg/uFMEug4Bb9`
**Email:** `contact@preparedcitizencorps.com`

---

*Document Revision: 2025-10-17*
*System Version: Phase 1*
