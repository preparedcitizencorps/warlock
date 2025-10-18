# Helmet-Mounted Unit (HMU) Installation

Instructions for deploying the HMU to a Raspberry Pi 5.

## Hardware Requirements

- Raspberry Pi 5 (8GB recommended)
- Raspberry Pi AI Kit (Hailo-8L) or standalone Hailo-8L
- Low-light camera (IMX462 recommended)
- BNO085 IMU module
- U-blox NEO-M9N GPS module (backup)
- MicroSD card (64GB+)
- Power supply (5V @ 4A)

## Software Installation

### 1. Flash Raspberry Pi OS

```bash
# Use Raspberry Pi Imager
# OS: Raspberry Pi OS (64-bit, Bookworm or later)
# Enable SSH, set hostname to 'warlock-hmu'
```

### 2. Initial Setup

```bash
ssh pi@warlock-hmu.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3-pip \
    python3-opencv \
    git \
    i2c-tools
```

### 3. Enable I2C (for IMU)

```bash
sudo raspi-config
# Interface Options → I2C → Enable
sudo reboot
```

### 4. Clone Repository

```bash
cd ~
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock/software
```

### 5. Install Python Dependencies

```bash
pip3 install -r helmet/requirements.txt --break-system-packages

# Install YOLO tracking dependencies (required for object tracking)
pip3 install --break-system-packages "lap>=0.5.12"
```

### 6. Install Hailo AI Kit

Follow official Raspberry Pi AI Kit setup:

```bash
# Install Hailo software
wget https://github.com/hailo-ai/hailo-rpi5-examples/releases/download/v1.0.0/hailo-rpi5-examples-v1.0.0.deb
sudo dpkg -i hailo-rpi5-examples-v1.0.0.deb

# Verify installation
hailo-verify
```

### 7. Configure Network

Edit `helmet/helmet_config.yaml`:

```yaml
network:
  source_id: "WARLOCK-001-HMU"  # Unique ID
  bmu_host: "192.168.200.2"     # BMU IP (cable) or WiFi IP
  tcp_port: 5000
  udp_port: 5001
```

For USB-C Ethernet connection:

```bash
# Set static IP on usb0
sudo nano /etc/dhcpcd.conf
# Add:
# interface usb0
# static ip_address=192.168.200.1/24
```

### 8. Test Camera

For **CSI cameras** (IMX462, etc.):
```bash
# Check if camera is detected
rpicam-hello --list-cameras

# If not detected, check config.txt
sudo nano /boot/firmware/config.txt
# Add: dtoverlay=imx462  (or your camera model)
# Comment out: #camera_auto_detect=1
sudo reboot
```

For **USB cameras**:
```bash
# List video devices
ls /dev/video*

# Check device info
v4l2-ctl --list-devices
```

Test camera capture:
```bash
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAIL')"
```

**Note:** Raspberry Pi 5 uses picamera2 for CSI cameras. USB cameras use OpenCV VideoCapture. WARLOCK automatically detects and uses the appropriate method.

### 9. Copy YOLO Model

```bash
# Copy yolo11n.pt or yolo11n-seg.pt to helmet directory
cp ../yolo11n-seg.pt helmet/
```

### 10. Test Standalone Mode

```bash
cd ~/warlock/software
python3 helmet/helmet_main.py --standalone
# Press 'Q' to quit
```

## Auto-Start on Boot (Optional)

Create systemd service:

```bash
sudo nano /etc/systemd/system/warlock-hmu.service
```

```ini
[Unit]
Description=WARLOCK Helmet-Mounted Unit
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/warlock/software
ExecStart=/usr/bin/python3 helmet/helmet_main.py
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

Check status:

```bash
sudo systemctl status warlock-hmu
```

## Troubleshooting

**CSI Camera not detected:**

```bash
# Check if camera is detected by libcamera
rpicam-hello --list-cameras

# If "No cameras available":
# 1. Check ribbon cable connection (blue tab orientation)
# 2. Check /boot/firmware/config.txt for camera settings
# 3. Try manual overlay:
sudo nano /boot/firmware/config.txt
# Add: dtoverlay=imx462
# Comment: #camera_auto_detect=1
sudo reboot
```

**CSI Camera I2C errors (Error -121):**

```bash
# Check kernel messages
sudo dmesg | grep -i 'imx\|csi\|camera'

# If you see "Error writing reg 0x303a: -121":
# - This indicates faulty camera hardware or loose cable
# - Try reseating the ribbon cable at both ends
# - Test with a different camera
# - Use USB camera as alternative
```

**USB Camera not detected:**

```bash
ls /dev/video*
# Should show /dev/video8 or similar

# Check device info
v4l2-ctl --list-devices
```

**YOLO "No module named 'lap'" error:**

```bash
pip3 install --break-system-packages "lap>=0.5.12"
```

**Hailo not working:**

```bash
hailo-verify
# Should show "Hailo device detected"
```

**IMU not detected:**

```bash
sudo i2cdetect -y 1
# Should show device at 0x4a or 0x4b
```

**Can't connect to BMU:**

```bash
ping 192.168.200.2
# Check cable connection
# Try WiFi fallback if available
```

## Performance Tuning

**Increase GPU memory:**

```bash
sudo nano /boot/config.txt
# Add: gpu_mem=256
sudo reboot
```

**Overclock (if needed):**

```bash
sudo nano /boot/config.txt
# Add: arm_freq=2400
# Add: over_voltage=6
sudo reboot
```

**Monitor temperature:**

```bash
watch vcgencmd measure_temp
# Should stay below 70°C under load
```
