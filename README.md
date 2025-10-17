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

### Standalone Mode (No Hardware Required)

```bash
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock/software
pip install -r requirements.txt
python3 helmet/helmet_main.py --standalone
```

### Two-Pi System (HMU + BMU)

**Terminal 1 - Body Unit:**
```bash
cd warlock/software
python3 body/body_main.py
```

**Terminal 2 - Helmet Unit:**
```bash
cd warlock/software
python3 helmet/helmet_main.py
```

**Controls:**
- `Q` - Quit | `H` - Help | `P` - Plugin panel
- `Y` - YOLO toggle | `M` - Map | `F` - FPS
- Arrow keys - Simulate movement (standalone mode)

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

**Run tests:**
```bash
cd software
pytest -v
# All 30 tests should pass
```

**Troubleshooting:**
- **Plugin not loading?** Check class inherits `HUDPlugin`, has class-level `METADATA`, file in `software/helmet/hud/plugins/`
- **YOLO error?** Run: `python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"`
- **HMU won't connect?** Check BMU is running first, verify IP in `helmet/helmet_config.yaml`
- **Import errors?** Make sure you're in `software/` directory: `export PYTHONPATH=$(pwd)`

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
