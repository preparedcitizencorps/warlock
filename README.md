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

```bash
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock
pip install -r requirements.txt
python software/warlock.py
```

**Controls:**
- `Q` - Quit | `H` - Help | `P` - Plugin panel
- `Y` - YOLO toggle | `F` - FPS | `B` - Boundaries
- `[`/`]` - Adjust padding | Arrows - Simulate movement

---

## CAPABILITIES

- **Modular plugin architecture** - Hot-swappable components
- **Real-time object detection** - YOLO11n with friend/foe IFF
- **GPS navigation** - Compass + motion tracker with terrain
- **Runtime management** - Live reload, enable/disable plugins
- **AR display ready** - Configurable padding for headset FOV

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
class MyPlugin(HUDPlugin):
    METADATA = PluginMetadata(
        name="My Plugin",
        version="1.0.0",
        author="Your Callsign",
        description="Custom functionality"
    )

    def render(self, frame: np.ndarray) -> np.ndarray:
        # Draw on frame
        return frame
```

Add to `hud_config.yaml`, run, and press `P` for hot-reload!

---

## PERFORMANCE & TESTING

- **20-30 FPS** on laptop CPU (no GPU required)
- **30-50ms** YOLO inference per frame
- **~500MB** memory with YOLO loaded

**Run tests:**
```bash
cd software
pytest -v
```

**Troubleshooting:**
- **Plugin not loading?** Check class inherits `HUDPlugin`, has class-level `METADATA`, file in `software/hud/plugins/`
- **YOLO error?** Run: `python -c "from ultralytics import YOLO; YOLO('yolo11n.pt')"`
- **Hot reload fails?** Check console errors, try manual reload (`P` → select → `R`)

---

## ROADMAP

**Phase 0: HUD & AI** ✅ COMPLETE
- Plugin architecture, YOLO detection, hot-reload

**Phase 1: Night Vision** 🔄 IN PROGRESS
- Raspberry Pi 5 port, low-light camera (IMX462) to validate digital night vision
- Hailo-8L AI accelerator for 60+ FPS object detection

**Phase 2: AR Display** 📋 PLANNED
- AR glasses integration (Rokid Max), heads-up display projection
- Halo-inspired HUD with detection overlays, compass, battery status

**Phase 3: Sensor Fusion** 📋 PLANNED
- Thermal imaging - FLIR Lepton 3.5 for heat signature detection (50m+ range)
- WiFi sensing - Through-wall motion detection using CSI (5-15m range)
- Multi-modal sensor fusion: visual + thermal + RF for complete situational awareness

**Phase 4: Navigation & Comms** 📋 PLANNED
- GPS, compass (BNO085), terrain maps, waypoint navigation
- Radio integration - SA818 VHF/UHF modules for Baofeng compatibility
- Hands-free PTT, voice-activated comms, dual-watch mode

**Phase 5: Electronic Warfare** 📋 PLANNED
- **RF triangulation** - RTL-SDR receiver for distributed SIGINT array
- Squad-level signal detection and localization (150-250m range)
- Detect enemy radios, drones, electronic devices before visual contact
- Frequency scanning, signal fingerprinting, jamming detection

**Phase 6: Mesh Networking** 📋 PLANNED
- LoRa/OpenMANET mesh for beyond-line-of-sight coordination
- Cross-network routing (mesh ↔ traditional radio bridge)
- Team position sharing, encrypted voice/data, ATAK integration
- Relay mode to extend Baofeng range via mesh network

**Phase 7: Field Hardening** 📋 PLANNED
- Complete helmet mounting system, weatherproofing
- 4+ hour battery life, field-tested durability
- Custom 3D-printed enclosures, professional finish

---

### Detection Capabilities Summary
| Sensor | Range | Best For | Status |
|--------|-------|----------|--------|
| **Low-light Camera** | 50-200m | Visual ID, daylight/night | 🔄 Phase 1 |
| **Thermal Imaging** | 50-300m | Heat signatures, darkness | 📋 Phase 3 |
| **WiFi Sensing** | 5-15m | Through-wall motion | 📋 Phase 3 |
| **RF Triangulation** | 150-500m | Radio emitters, drones | 📋 Phase 5 |

**Combined:** Near-omniscient battlefield awareness across all ranges and conditions.

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
