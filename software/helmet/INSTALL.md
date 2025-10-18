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

### 8. Camera Setup

WARLOCK supports three types of cameras:

#### Option A: USB Cameras (Easiest)
USB cameras work out of the box with OpenCV VideoCapture. Simply plug in and test:

```bash
# List video devices
ls /dev/video*

# Test camera
python3 -c "import cv2; cap = cv2.VideoCapture(0); print('Camera OK' if cap.isOpened() else 'Camera FAIL')"
```

#### Option B: Standard Raspberry Pi Cameras
Standard Pi cameras (v2, v3, HQ) are auto-detected:

```bash
# Check if camera is detected
rpicam-hello --list-cameras

# Test camera
rpicam-still -t 5000 -n -o test.jpg
```

#### Option C: Arducam Low-Light Cameras (IMX462, IMX290, IMX327)

Arducam offers two types of low-light cameras. **Check your product SKU to determine which type you have:**

**C1. Native Low-Light Cameras (Recommended for simplicity)**

These cameras work with standard Raspberry Pi dtoverlays (no special installation needed):

- **IMX462 Native** (SKU: B0423) - 2MP Ultra Low Light
- **IMX290 Native** (SKU: B0424) - 2MP Ultra Low Light
- **IMX327 Native** (SKU: B0425) - 2MP Ultra Low Light (uses imx290 driver)

**Setup for Pi 5 with Bookworm OS:**

```bash
sudo nano /boot/firmware/config.txt
# Find the line: [all], add under it:

# For IMX462:
dtoverlay=imx462

# For IMX290:
dtoverlay=imx290,clock-frequency=37125000

# For IMX327 (uses IMX290 driver):
dtoverlay=imx290,clock-frequency=37125000

# Save and reboot
```

For camera on **cam0 port** (not default), append `,cam0` to the dtoverlay line.

Test camera:
```bash
rpicam-hello --list-cameras
rpicam-still -t 5000 -n -o test.jpg
```

**C2. PiVariety Low-Light Cameras (Requires special installation)**

These cameras require Arducam's custom libcamera packages:

**IMPORTANT:** Connect camera to **Camera Port 1** on Raspberry Pi 5 (between Ethernet and HDMI, silver contacts facing Ethernet port).

1. Download and run Arducam installation script:

```bash
cd ~
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
```

2. Install libcamera:

```bash
./install_pivariety_pkgs.sh -p libcamera_dev
```

3. Install libcamera-apps:

```bash
./install_pivariety_pkgs.sh -p libcamera_apps
```

4. Configure camera overlay:

```bash
sudo nano /boot/firmware/config.txt
# Find the line: [all], add under it:
dtoverlay=arducam-pivariety
# Save and reboot
```

For camera on **cam0 port**, use: `dtoverlay=arducam-pivariety,cam0`

5. Test PiVariety camera:

```bash
rpicam-hello --list-cameras
rpicam-still -t 5000 -n -o test.jpg
```

**Hardware Connection Tips (All Arducam Cameras):**
- Connect camera sensor to adapter board first (if applicable)
- CSI ribbon cable silver contacts face **Ethernet port** on Pi 5
- Ensure ribbon cable is firmly seated at both ends (hear a click)
- Camera modules are ESD sensitive - ground yourself before handling
- Default Camera Port 1 is between Ethernet and HDMI on Pi 5

**Note:** Raspberry Pi 5 uses picamera2/libcamera for CSI cameras. WARLOCK automatically detects and uses the appropriate camera interface.

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
# 1. Check ribbon cable connection (silver contacts face Ethernet on Pi 5)
# 2. Verify camera is connected to correct port (Camera Port 1 is default)
# 3. Check /boot/firmware/config.txt for camera settings

sudo nano /boot/firmware/config.txt
# For Native Arducam cameras, add under [all]:
#   dtoverlay=imx462  (or imx290,clock-frequency=37125000)
# For PiVariety cameras:
#   dtoverlay=arducam-pivariety
# You may also need to comment out: #camera_auto_detect=1

sudo reboot
```

**CSI Camera display issues (Pi 0-3 only):**

```bash
# Enable Glamor acceleration (required for older Pi models)
sudo raspi-config
# Navigate to: Advanced Options → Enable Glamor graphic acceleration
# Reboot

# If still having display issues, try Full KMS:
sudo raspi-config
# Navigate to: Advanced Options → GL Driver → GL (Full KMS)
# Reboot
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
