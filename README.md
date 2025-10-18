# PROJECT WARLOCK

> **W**earable **A**ugmented **R**eality & **L**inked **O**perational **C**ombat **K**it

**Halo-style tactical HUD for real-world operations. Open source. Built for civilians.**

![WARLOCK HUD with YOLO Detection](docs/images/poc-v1.png)

---

## MISSION

Build a helmet-mounted AR system with:
- Real-time object detection and IFF
- GPS navigation with terrain overlay
- Night vision and thermal imaging
- Team coordination and data sharing
- Field-hardened, modular, extensible

---

## QUICK START

Choose your setup path:

### 💻 Option 1: Test on Your Computer

**Quick test with webcam (5 minutes):**

```bash
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock/software
pip install -r requirements.txt
python3 helmet/helmet_main.py --standalone
```

Press `H` for help, `Q` to quit. YOLO will auto-download on first run (~50MB).

---

### 🎯 Option 2: Raspberry Pi Setup

**Hardware needed:**
- Raspberry Pi 5 (4GB or 8GB)
- Camera (USB webcam or CSI camera)
- MicroSD card (32GB+)
- Optional: Hailo-8L AI accelerator for 60 FPS

**Choose your OS:**

| OS | Use Case | Display Mode |
|----|----------|--------------|
| **Pi OS Desktop** | Development/testing | X11 (easy debugging) |
| **Pi OS Lite** | Field deployment | DRM/KMS (better performance) |

**Installation:**

**Option A: Automated Setup (Recommended)**

```bash
# One-line installer - handles everything automatically
curl -fsSL https://raw.githubusercontent.com/preparedcitizencorps/warlock/master/software/helmet/setup_pi.sh | bash

# OR if you already cloned the repo:
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock/software/helmet
chmod +x setup_pi.sh
./setup_pi.sh
```

The script will:
- Install all dependencies (OpenCV, picamera2, evdev, etc.)
- Configure user groups and permissions
- Set up camera and DRM/KMS support
- Create launcher scripts (`./run_hmu.sh`, `./run_bmu.sh`)
- Optional: Create systemd service for auto-start

**Option B: Manual Setup**

```bash
# 1. Flash Pi OS with Raspberry Pi Imager
# 2. SSH in and update
ssh pi@raspberrypi.local
sudo apt update && sudo apt upgrade -y

# 3. Install dependencies
sudo apt install -y python3-pip python3-opencv python3-picamera2 git libgl1 libglib2.0-0

# 4. For headless mode (DRM/KMS):
sudo apt install -y python3-kms++ python3-evdev
sudo usermod -a -G video,input $USER

# 5. Clone and install
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock/software
pip3 install -r helmet/requirements.txt --break-system-packages

# 6. Run WARLOCK
# On Desktop OS:
python3 helmet/helmet_main.py --standalone

# On Lite OS (headless):
WARLOCK_USE_DRM=1 python3 helmet/helmet_main.py --standalone
```

**Controls:**
- `Q` - Quit | `H` - Help | `P` - Plugin panel
- `Y` - YOLO toggle | `E` - Auto-exposure | `F` - FPS
- `M` - Map | `C` - Screenshot

**Two-Pi System (HMU + BMU):**

Once you have both units configured, run:

```bash
# Terminal 1 - Body Unit:
python3 body/body_main.py

# Terminal 2 - Helmet Unit:
python3 helmet/helmet_main.py
```

---

## CAPABILITIES

- **Two-unit architecture** - Distributed HMU (helmet) + BMU (body) system
- **Modular plugin system** - Hot-swappable components with dependency resolution
- **Real-time AI detection** - YOLO11 with Hailo-8L acceleration (30-60 FPS)
- **GPS navigation** - Compass + terrain overlay with OpenTopoMap
- **Network resilient** - USB-C primary with WiFi failover
- **AR display ready** - Rokid Max glasses with tactical HUD overlay

---

## DEVELOPING PLUGINS

WARLOCK uses a modular plugin architecture. Want to add custom functionality?

**See [CONTRIBUTING.md](CONTRIBUTING.md#plugin-development-guide)** for the complete plugin development guide, including:
- Creating plugins from scratch
- Plugin dependencies and data sharing
- API reference and lifecycle methods
- Hot reload workflow
- Troubleshooting common issues

**Quick example:**
```python
from common.plugin_base import HUDPlugin, PluginMetadata
import numpy as np

class MyPlugin(HUDPlugin):
    METADATA = PluginMetadata(
        name="My Plugin",
        version="1.0.0",
        author="Your Callsign",
        description="Custom functionality"
    )

    def initialize(self) -> bool:
        return True

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        # Draw on frame
        return frame
```

1. Save to `software/helmet/hud/plugins/my_plugin.py`
2. Add to `helmet/helmet_config.yaml`
3. Press `P` for hot-reload!

---

## PERFORMANCE & TESTING

### Laptop/Desktop (Development)
- **20-30 FPS** on CPU (no GPU required)
- **30-50ms** YOLO inference per frame
- **~500MB** memory with YOLO loaded

### Raspberry Pi 5 with Hailo-8L (Production)
- **30-60 FPS** with AI accelerator
- **15-20ms** YOLO inference per frame
- **Real-time** object tracking and HUD overlay

### Display Mode Performance (Pi 5)
| Mode | FPS | Latency | CPU | Best For |
|------|-----|---------|-----|----------|
| **X11** (Desktop) | 45-50 | ~10ms | 15-20% | Development |
| **DRM/KMS** (Headless) | 55-60 | ~2ms | 8-12% | Field deployment |

**Run tests:**
```bash
cd software
pytest -v
# All 30 tests should pass
```

**Troubleshooting:**
- **Camera not found?** Check `ls /dev/video*` or enable CSI in `sudo raspi-config`
- **YOLO error?** Run: `python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"`
- **Import errors?** Make sure you're in `software/` directory: `export PYTHONPATH=$(pwd)`
- **DRM mode fails?** Check you're in `video` and `input` groups, no desktop session active
- **Plugin not loading?** Check class inherits `HUDPlugin`, has class-level `METADATA`

---

## DRM/KMS HEADLESS DISPLAY

For field deployment with Rokid Max AR glasses or headless operation without desktop environment.

### Why DRM Mode?
- ✅ 10-15% better FPS (55-60 vs 45-50 on Pi 5)
- ✅ 5-10ms lower latency (critical for AR)
- ✅ No desktop overhead (lower power consumption)
- ✅ Runs on Raspberry Pi OS Lite

### Quick Setup

**1. Install dependencies:**
```bash
sudo apt install -y python3-kms++
sudo usermod -a -G video,input $USER
# Logout/login for groups to take effect
```

**2. Run in DRM mode:**
```bash
cd ~/warlock/software
WARLOCK_USE_DRM=1 python3 helmet/helmet_main.py --standalone
```

### Auto-Start on Boot (Production)

Create `/etc/systemd/system/warlock-hmu.service`:
```ini
[Unit]
Description=WARLOCK Helmet-Mounted Unit
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/warlock/software
Environment="WARLOCK_USE_DRM=1"
ExecStart=/usr/bin/python3 helmet/helmet_main.py --standalone
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable warlock-hmu
sudo systemctl start warlock-hmu
```

### Troubleshooting DRM Mode

**Permission denied:**
```bash
groups  # Should show: video input
sudo usermod -a -G video,input $USER
sudo reboot
```

**No display found:**
```bash
# Desktop session blocks DRM - boot to console:
sudo systemctl set-default multi-user.target
sudo reboot
```

**No keyboard input:**
```bash
# Setup udev rule for /dev/input access:
echo 'KERNEL=="event*", SUBSYSTEM=="input", MODE="0660", GROUP="input"' | \
  sudo tee /etc/udev/rules.d/99-input.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---

## ROADMAP

**Phase 1: Network Foundation** ✅ COMPLETE
- Two-Pi architecture (HMU + BMU)
- Network protocol and failover
- GPS data flow and plugin system

**Phase 2: Hardware Integration** 🔄 IN PROGRESS
- Real GPS modules (U-blox ZED-F9P for RTK)
- IMU sensors (BNO085)
- Thermal camera (FLIR Lepton 3.5)
- Low-light camera (IMX462)

**Phase 3: SIGINT** 📋 PLANNED
- RTL-SDR RF scanning (150-500m detection)
- WiFi CSI through-wall detection (5-15m)
- Signal triangulation with multi-unit coordination
- Alert display on HUD

**Phase 4: Communications** 📋 PLANNED
- SA818 radio integration (VHF/UHF)
- Hands-free PTT and voice control
- WiFi mesh (0-300m squad coordination)
- LoRa mesh (300m-5km inter-squad relay)

**Phase 5: ATAK Integration** 📋 PLANNED
- CoT message publishing
- Team position sharing
- Waypoint navigation
- TAK server bridge

**Phase 6: Field Hardening** 📋 PLANNED
- Weatherproof enclosures
- Extended battery life (8+ hours)
- 3D-printed helmet mount
- Ruggedized field testing

---

### Detection Capabilities Summary
| Sensor | Range | Best For | Status |
|--------|-------|----------|--------|
| **Low-light Camera** | 50-200m | Visual ID, daylight/night | 🔄 Phase 2 |
| **Thermal Imaging** | 50-300m | Heat signatures, darkness | 🔄 Phase 2 |
| **WiFi CSI** | 5-15m | Through-wall motion | 📋 Phase 3 |
| **RF Triangulation** | 150-500m | Radio emitters, drones | 📋 Phase 3 |

**Combined:** Multi-sensor fusion for comprehensive situational awareness.

---

## DOCUMENTATION

- **[System Overview](docs/SYSTEM-OVERVIEW.md)** - Hardware, capabilities, and deployment
- **[Technical Specs](docs/TECHNICAL-SPECS.md)** - Detailed specifications and protocols
- **[Field Manual](docs/FIELD-MANUAL.md)** - Operational procedures and tactics
- **[Software README](software/README.md)** - Development and testing guide

---

## COMMUNITY

**Discord:** https://discord.gg/uFMEug4Bb9

**YouTube:** https://youtube.com/@preparedcitizencorps

**Email:** contact@preparedcitizencorps.com

**Contributing:** We need help with plugins, Pi optimization, hardware design, ML models, docs, and testing. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## LICENSE

- **Software** → MIT License
- **Hardware** → CERN-OHL-P-2.0
- **Documentation** → CC BY-SA 4.0

Build it. Modify it. Sell it. Just share your improvements.

---

## ACKNOWLEDGMENTS

Built with: [YOLO11](https://github.com/ultralytics/ultralytics) · [OpenCV](https://opencv.org/) · [OpenTopoMap](https://opentopomap.org/) · [Python](https://www.python.org/)

---

⭐ **Star this repo to track development**
