# Raspberry Pi 5 Quick Start Guide

**Get your WARLOCK HMU running in 15 minutes with just a Pi 5 and camera.**

This guide gets you from unboxing to detecting objects with YOLO in standalone mode (no BMU required).

---

## What You Need

**Hardware:**
- Raspberry Pi 5 (4GB or 8GB)
- Low-light camera (IMX462 or any USB/CSI webcam)
- MicroSD card (32GB+, flashed with Raspberry Pi OS)
- Power supply (official Pi 5 27W USB-C recommended)
- Monitor + keyboard (or SSH access)

**Optional (Phase 2):**
- Raspberry Pi AI Kit (Hailo-8L) for 30-60 FPS YOLO
- Without Hailo: 15-25 FPS on CPU (still usable!)

---

## Installation Steps

### 1. Flash Raspberry Pi OS

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/):

- **OS**: Raspberry Pi OS (64-bit, Bookworm)
- **Hostname**: `warlock-hmu` (optional)
- **Enable SSH**: Set username/password
- **WiFi**: Configure if using wireless

Flash to SD card and boot your Pi 5.

---

### 2. Initial Setup

SSH into your Pi or open terminal:

```bash
ssh pi@warlock-hmu.local
# or use default: ssh pi@raspberrypi.local
```

Update system:

```bash
sudo apt update && sudo apt upgrade -y
```

Install system dependencies:

```bash
sudo apt install -y \
    python3-pip \
    python3-opencv \
    git \
    libgl1 \
    libglib2.0-0
```

---

### 3. Clone WARLOCK Repository

```bash
cd ~
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock/software
```

---

### 4. Install Python Dependencies

```bash
pip3 install -r helmet/requirements.txt --break-system-packages
```

> **Note**: `--break-system-packages` is required on Bookworm. Alternatively, use a virtual environment:
> ```bash
> python3 -m venv ~/.venv/warlock
> source ~/.venv/warlock/bin/activate
> pip install -r helmet/requirements.txt
> ```

This installs:
- OpenCV (camera and image processing)
- YOLO11 via ultralytics (AI object detection)
- NumPy, PyYAML, requests

**Installation takes 5-10 minutes** - YOLO models are ~200MB.

---

### 5. Test Camera

Verify camera is detected:

```bash
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('✓ Camera detected' if cap.isOpened() else '✗ Camera FAILED'); cap.release()"
```

**Troubleshooting:**
- **Camera not found**: Check connection, try `ls /dev/video*`
- **CSI camera**: May need to enable in `sudo raspi-config` → Interface Options → Camera

---

### 6. Run WARLOCK in Standalone Mode

```bash
cd ~/warlock/software
python3 helmet/helmet_main.py --standalone
```

**First run:**
- YOLO will download the model file (~50MB) automatically
- Takes 30-60 seconds to initialize
- Window opens showing camera feed with HUD overlay

**You should see:**
- Live camera feed
- FPS counter (toggle with `F`)
- Auto-exposure adjusting to lighting (toggle with `E`)
- Object detection boxes around people (toggle with `Y`)

---

## Controls

| Key | Action |
|-----|--------|
| `Q` | Quit |
| `H` | Help overlay (shows all keybinds) |
| `Y` | Toggle YOLO detection |
| `E` | Toggle auto-exposure |
| `O` | Show exposure stats |
| `+/-` | Adjust target brightness |
| `F` | Toggle FPS counter |
| `M` | Toggle mini-map (simulated GPS) |
| `P` | Plugin control panel |
| `C` | Capture screenshot |

---

## Low-Light Camera Optimization

The auto-exposure plugin is **enabled by default** for low-light cameras like the IMX462.

**How it works:**
- Automatically adjusts exposure and gain based on scene brightness
- CLAHE (Contrast-Limited Adaptive Histogram Equalization) enhances dark areas
- Center-weighted metering focuses on what's in front of you

**Configuration** (edit `helmet/helmet_config.yaml`):

```yaml
plugins:
  - name: AutoExposurePlugin
    enabled: true
    settings:
      target_brightness: 128      # 0-255, higher = brighter
      adjustment_speed: 0.15      # 0.1-0.5, higher = faster adjustments
      use_clahe: true             # Enhanced contrast for low-light
      enable_auto_exposure: true  # Hardware exposure control
      enable_auto_gain: true      # Hardware gain control
      min_exposure: -13           # Camera-dependent
      max_exposure: 0
      min_gain: 0
      max_gain: 100
```

**Test in different lighting:**
- **Bright daylight**: Auto-exposure lowers exposure/gain
- **Indoor/shade**: Moderate adjustments
- **Night/low-light**: Maxes out gain and exposure, applies CLAHE enhancement

Press `O` to see real-time brightness/exposure/gain stats.

---

## Performance Expectations

### Without Hailo AI Kit (CPU only)
- **15-25 FPS** with YOLO detection
- **Inference**: ~50-70ms per frame
- **Use case**: Proof of concept, development, testing

### With Hailo-8L (Phase 2)
- **30-60 FPS** with YOLO detection
- **Inference**: ~15-20ms per frame
- **Use case**: Production, field deployment

Both modes are fully functional - Hailo just makes it faster and smoother.

---

## Next Steps

### Test the System

**1. Walk around with the camera** - verify YOLO detects people
**2. Test different lighting** - indoor, outdoor, low-light
**3. Adjust auto-exposure** - press `+/-` to change target brightness
**4. Try different YOLO modes** - press `V` to cycle detection/segmentation

### Optional: Auto-Start on Boot

Make WARLOCK start automatically when Pi boots:

```bash
sudo nano /etc/systemd/system/warlock-hmu.service
```

Paste:

```ini
[Unit]
Description=WARLOCK Helmet-Mounted Unit
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/warlock/software
ExecStart=/usr/bin/python3 helmet/helmet_main.py --standalone
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable warlock-hmu
sudo systemctl start warlock-hmu
```

Check status:

```bash
sudo systemctl status warlock-hmu
```

View logs:

```bash
sudo journalctl -u warlock-hmu -f
```

### Phase 2: Add BMU Connection

Once you have a second Pi 5 for the Body-Mounted Unit:

1. Follow [BMU Installation Guide](software/body/INSTALL.md)
2. Connect HMU → BMU via USB-C Ethernet or WiFi
3. Remove `--standalone` flag: `python3 helmet/helmet_main.py`
4. HMU will receive real GPS data from BMU

---

## Troubleshooting

### Camera Issues

**"Could not open camera"**
```bash
# Check camera is detected
ls /dev/video*

# Test with v4l2
v4l2-ctl --list-devices

# For CSI camera, enable in raspi-config
sudo raspi-config
# → Interface Options → Camera → Enable
```

### YOLO Performance Issues

**FPS too low (< 10)**
```bash
# Check CPU temperature (throttling at 80°C)
vcgencmd measure_temp

# Check running processes
htop

# Consider adding heatsink or fan
```

**YOLO model not downloading**
```bash
# Manually download YOLO model
cd ~/warlock/software/helmet
wget https://github.com/ultralytics/assets/releases/download/v8.2.0/yolo11n.pt
```

### Import Errors

**ModuleNotFoundError: No module named 'ultralytics'**
```bash
# Ensure you're in the right directory
cd ~/warlock/software

# Reinstall dependencies
pip3 install -r helmet/requirements.txt --break-system-packages

# Or activate venv if you created one
source ~/.venv/warlock/bin/activate
```

### Display Issues

**No window appears (headless Pi)**

WARLOCK requires a display. For headless operation:
- Use VNC: `sudo raspi-config` → Interface Options → VNC
- Or use X11 forwarding: `ssh -X pi@warlock-hmu.local`
- Or export frames over network (requires custom plugin)

**Window is tiny/huge**

Edit camera resolution in `helmet/helmet_main.py` (lines 35-36):
```python
DEFAULT_FRAME_WIDTH = 1280   # Change to 640 for smaller window
DEFAULT_FRAME_HEIGHT = 720   # Change to 480 for smaller window
```

---

## Need Help?

**Discord**: https://discord.gg/uFMEug4Bb9

**GitHub Issues**: https://github.com/preparedcitizencorps/warlock/issues

**Documentation**: See `docs/` folder for system overview, technical specs, field manual

---

## What's Working Right Now

✅ **Camera capture** (USB and CSI cameras)
✅ **YOLO object detection** (people, vehicles, 80+ classes)
✅ **Auto-exposure** (low-light optimization)
✅ **HUD overlay** (FPS, compass, mini-map)
✅ **Plugin system** (hot-reload, dependencies)
✅ **Standalone mode** (no BMU required)

## What's Coming (Phase 2+)

🔄 **Hailo-8L acceleration** (30-60 FPS YOLO)
🔄 **Real GPS modules** (U-blox ZED-F9P)
🔄 **IMU integration** (BNO085 heading/orientation)
📋 **Thermal camera** (FLIR Lepton 3.5)
📋 **RF scanning** (RTL-SDR detection)
📋 **Mesh networking** (squad coordination)

---

**Ready to test? Run:**

```bash
cd ~/warlock/software
python3 helmet/helmet_main.py --standalone
```

Press `H` for help, `Q` to quit. Have fun! 🎯
