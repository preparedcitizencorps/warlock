# WARLOCK SYSTEM OVERVIEW

**Wearable Augmented Reality & Linked Operational Combat Kit**

---

## MISSION

Helmet-mounted computer that interfaces with TAK on your phone to overlay waypoints and points of interest on your HUD, combining multi-spectral imaging with AI-powered object detection.

---

## SYSTEM CONFIGURATION

### Single Helmet-Mounted Unit

**PROCESSING**
- Raspberry Pi 5 (8GB)
- Hailo-8L AI accelerator for YOLO inference
- All processing on single unit

**CAMERAS**
- 2x Low-light cameras (IMX462) for stereo/redundancy
- 1x Thermal camera (FLIR Lepton 3.5) for heat signatures
- Mounted under standard NV mount position

**DISPLAY**
- Rokid Max AR glasses (1080p per eye)
- DRM/KMS direct rendering for minimal latency
- Tactical HUD overlay with waypoint markers

**POWER**
- Compact helmet battery: 30 minutes runtime
- Extended battery pack: Connected via cable, worn on body/backpack
- Hot-swap capability for continuous operation

**TAK INTEGRATION**
- Connects to TAK server on your phone
- Displays waypoints and POIs overlayed on HUD
- Real-time position synchronization
- CoT (Cursor on Target) protocol support

---

## CAPABILITIES

### Visual Detection

- **Low-light cameras (2x IMX462)**: 50-200m effective range
  - Starlight sensitivity for night operations
  - Stereo imaging for depth perception
  - Redundancy if one camera fails

- **Thermal imaging (FLIR Lepton 3.5)**: 50-300m range
  - Heat signature detection in total darkness
  - See through smoke, fog, and foliage
  - 160x120 resolution radiometric imaging

- **AI classification (YOLO11)**: Real-time object detection
  - Humans, weapons, vehicles, drones
  - 30-60 FPS with Hailo-8L acceleration
  - Bounding boxes and confidence scores

### TAK Integration

- **Waypoint overlay**: Display TAK waypoints on HUD
- **POI markers**: Show points of interest from TAK server
- **Position sync**: Real-time GPS position sharing with phone
- **CoT protocol**: Standard Cursor on Target messaging
- **Network**: WiFi connection to TAK server on phone

### Navigation

- **GPS module**: U-blox NEO-M9N (planned Phase 3)
- **IMU sensor**: BNO085 for heading and orientation (planned Phase 3)
- **Compass overlay**: Heading indicator on HUD
- **Terrain map**: OpenTopoMap integration with position marker

---

## HARDWARE BOM

### Complete System

| Item | Model | Purpose | Cost |
|------|-------|---------|------|
| **Processing** |
| SBC | Raspberry Pi 5 (8GB) | Main computer | $80 |
| AI Accelerator | Hailo-8L (RPi AI Kit) | YOLO inference | $70 |
| **Cameras** |
| Low-light Camera 1 | IMX462 CSI module | Primary night vision | $60 |
| Low-light Camera 2 | IMX462 CSI module | Stereo/backup | $60 |
| Thermal Camera | FLIR Lepton 3.5 | Heat signatures | $230 |
| **Display** |
| AR Glasses | Rokid Max | HUD display | $440 |
| **Navigation** (Phase 3) |
| GPS Module | U-blox NEO-M9N | Position tracking | $40 |
| IMU Sensor | BNO085 | Heading/orientation | $20 |
| **Power System** (Phase 4) |
| Helmet Battery | 5000mAh Li-ion | 30min runtime | $30 |
| Extended Battery | 20000mAh pack | Extended ops | $60 |
| Power Cable | Custom USB-C 2m | Battery connection | $20 |
| **Mounting** (Phase 5) |
| Helmet Mount | 3D printed | NV mount compatible | $15 |
| Camera Housing | Weatherproof IP65 | Protection | $40 |
| Cable Management | Velcro/clips | Organization | $10 |
| **TOTAL** | | | **~$1,175** |

**Note:** Prices are approximate and may vary by supplier/region

---

## DEPLOYMENT

### Initial Setup

1. **Flash Raspberry Pi OS to microSD**
   - Recommended: Pi OS Lite for headless DRM mode
   - Alternative: Pi OS Desktop for development

2. **Run automated setup script**
   ```bash
   curl -fsSL https://raw.githubusercontent.com/preparedcitizencorps/warlock/master/software/setup_pi.sh | bash
   ```

3. **Install cameras**
   - Connect IMX462 cameras to CSI ports
   - Connect FLIR Lepton via SPI/I2C
   - Verify detection: `ls /dev/video*`

4. **Configure TAK server connection**
   - Edit `software/config.yaml`
   - Set TAK server IP (your phone)
   - Configure WiFi credentials

5. **Test system**
   ```bash
   cd ~/warlock/software
   python3 main.py
   ```

**See:** `software/INSTALL.md` for detailed instructions

---

## OPERATION

### Startup Sequence

1. **Power on helmet unit**
   - Connect helmet battery or extended battery
   - System boots in ~30 seconds

2. **Start TAK server on phone**
   - Launch ATAK/WinTAK/iTAK
   - Enable TAK server mode
   - Note server IP address

3. **Launch WARLOCK**
   - Helmet unit auto-starts if configured
   - Or manually: `python3 main.py`
   - Wait for camera initialization

4. **Verify connections**
   - Cameras detected: Check HUD indicators
   - TAK connected: Waypoints visible on HUD
   - GPS lock: Position marker on map

### Controls

- `H` - Help overlay
- `Q` - Quit
- `P` - Plugin panel (hot-reload)
- `Y` - Toggle YOLO detection
- `M` - Toggle map overlay
- `F` - Toggle FPS counter
- `C` - Capture screenshot

### Battery Management

**Helmet Battery (30min)**
- Use for short missions or when cable is impractical
- Hot-swap with extended battery for continuous operation
- Monitor charge level on HUD

**Extended Battery (4-8hr)**
- Connect via 2m cable
- Worn on body or in backpack
- Primary power for extended operations

---

## PERFORMANCE

### Processing

- **YOLO inference**: 30-60 FPS (with Hailo-8L)
- **Camera capture**: 30 FPS per camera (3x cameras total)
- **Display latency**: 2-5ms (DRM mode), 10-15ms (X11 mode)
- **CPU usage**: 15-25% (with Hailo), 60-80% (CPU-only YOLO)

### Power Consumption

- **Idle**: 8-10W (cameras off, no AI)
- **Active**: 15-20W (cameras + AI + display)
- **Peak**: 25W (all cameras + YOLO + thermal)

### Battery Runtime

**Helmet Battery (5000mAh @ 5V = 25Wh)**
- Active mode (15-20W): 75-100 minutes
- Peak mode (25W): ~60 minutes
- Conservative estimate for field use: **30 minutes** (accounts for battery aging and peaks)

**Extended Battery (20000mAh @ 5V = 100Wh)**
- Active mode (15-20W): 5-6.7 hours
- Peak mode (25W): 4 hours
- Conservative estimate for field use: **4-6 hours** (accounts for battery aging and peaks)

### Network

- **TAK server**: WiFi connection to phone
- **Latency**: 10-50ms (depends on WiFi quality)
- **Bandwidth**: ~100 Kbps (CoT messages + position updates)

---

## DEVELOPMENT PHASES

**Phase 1 - Core System** 🔄 IN PROGRESS

- Single helmet-mounted unit architecture
- Multi-camera support (2x low-light + 1x thermal)
- AI object detection (YOLO11 on Hailo-8L)
- Plugin system and HUD rendering

**Phase 2 - TAK Integration** 📋 PLANNED

- TAK server client (CoT protocol)
- Waypoint overlay on HUD
- POI/marker display
- Real-time position sync with phone

**Phase 3 - GPS & Navigation** 📋 PLANNED

- GPS module integration (U-blox NEO-M9N)
- IMU sensors (BNO085)
- Compass and terrain overlay
- Dead reckoning

**Phase 4 - Power System** 📋 PLANNED

- Compact 30min helmet battery
- Extended battery pack with cable
- Hot-swap capability
- Power management optimization

**Phase 5 - Field Hardening** 📋 PLANNED

- Weatherproof enclosures
- 3D-printed helmet mount (fits standard NV mounts)
- Cable management system
- Ruggedized field testing

---

## TROUBLESHOOTING

### Camera Issues

**No cameras detected**
- Check connections: `ls /dev/video*`
- Enable CSI in `sudo raspi-config`
- Verify camera cable seating

**Thermal camera not working**
- Check SPI/I2C enabled in config
- Test with `i2cdetect -y 1`
- Verify FLIR Lepton power (2.8V)

**Poor image quality**
- Adjust focus (IMX462 has manual focus)
- Check for lens obstruction
- Verify proper exposure settings

### System Issues

**YOLO running slow**
- Check Hailo installation: Run detection test
- Verify Hailo drivers loaded: `lsusb` should show Hailo device
- CPU fallback mode much slower (20-30 FPS vs 60 FPS)

**Display issues**
- DRM mode: Check `video` group membership
- X11 mode: Verify X server running
- Rokid Max: Check HDMI connection and resolution

### TAK Integration

**No waypoints showing**
- Verify TAK server IP in config
- Check WiFi connection to phone
- Confirm TAK server mode enabled
- Test with `ping <TAK_SERVER_IP>`

**Position not syncing**
- Check GPS lock (green indicator on HUD)
- Verify CoT message format
- Check network latency (<100ms)

---

## SAFETY

- **DO NOT** use thermal camera to view sun or laser sources (permanent damage)
- **DO NOT** rely solely on HUD - maintain situational awareness
- **DO NOT** operate while driving or in hazardous environments
- Battery safety: Use only approved Li-ion cells with protection circuits
- Test all systems in controlled environment before field use
- Keep firmware and software updated for security patches

---

## SUPPORT

**Documentation:** `github.com/preparedcitizencorps/warlock`
**Discord:** `discord.gg/uFMEug4Bb9`
**Email:** `contact@preparedcitizencorps.com`

---

*Document Revision: 2025-10-19*
*System Version: Single-Unit Architecture*
