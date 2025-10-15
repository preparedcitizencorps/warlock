# Project WARLOCK

> **W**earable **A**ugmented **R**eality & **L**inked **O**perational **C**ombat **K**it

**Halo-style AR heads-up display for tactical operations. Open source. Built by the community.**

---

## The Vision

Remember playing Halo and having that tactical HUD showing enemies, waypoints, and your shield status? We're building that. For real. For civilians.

**Imagine:**
- Real-time object detection highlighting players through your AR glasses
- Thermal imaging seeing heat signatures in total darkness
- GPS navigation with waypoints overlaid on your actual vision
- Team coordination with shared tactical information
- All running on a helmet-mounted system that survives actual field use

This is **Project WARLOCK**. And we're building it completely open source.

---

## Current Status

**Phase 0:** Basic object detection proof of concept

We have YOLO11 running and detecting people in real-time. That's step one.

Next up: Porting to Raspberry Pi 5 with a low-light camera.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock

# Run the demo (requires Python 3.11+ and pip)
pip install ultralytics opencv-python
python scripts/basic_detection.py
```

You should see real-time object detection on your webcam.

---

## What's Here

This is the beginning. Right now:

- `software/basic_detection.py` - Working YOLO11 detection demo
- `LICENSE` - Multi-license (MIT for software, CERN-OHL-P for hardware, CC BY-SA 4.0 for docs)
- `CONTRIBUTING.md` - How to contribute

Folders for hardware, docs, and build guides will be added as we build the actual system.

---

## Join the Build

**Discord:** [https://discord.gg/uFMEug4Bb9](https://discord.gg/uFMEug4Bb9)

**YouTube:** [https://youtube.com/@preparedcitizencorps](https://youtube.com/@preparedcitizencorps)

**Email:** contact@preparedcitizencorps.com

---

## License

This project uses multiple licenses:
- **Software & firmware** → MIT License
- **Hardware designs** → CERN Open Hardware Licence v2 - Permissive (CERN-OHL-P-2.0)
- **Documentation** → Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)

See the LICENSE file for full terms. Build it, modify it, sell it. Just share your improvements.

---

⭐ **Star this repo to follow development**

*Phase 0 - Proof of Concept - October 2025*
