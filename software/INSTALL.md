# HMU DEPLOYMENT MANUAL

**WARLOCK Helmet-Mounted Unit - Field Installation Procedures**

---

## MISSION PARAMETERS

**Platform:** Raspberry Pi 5 (8GB recommended)
**Camera:** Auto-detected (USB/CSI/Arducam)
**Accelerator:** Hailo-8L AI Kit (optional)
**Storage:** 64GB+ MicroSD
**Power:** 5V @ 4A

---

## SECTION 1: SYSTEM PREP

### 1.1 Flash Base OS

```bash
# Raspberry Pi Imager
# OS: Raspberry Pi OS 64-bit (Bookworm or later)
# Configure: SSH enabled, hostname 'warlock-hmu'
```

### 1.2 Initial Access

```bash
ssh pi@warlock-hmu.local
sudo apt update && sudo apt upgrade -y
```

### 1.3 Core Dependencies

```bash
sudo apt install -y python3-pip python3-opencv python3-picamera2 git libgl1 libglib2.0-0 v4l-utils

# Headless mode (DRM/KMS)
sudo apt install -y python3-kms++ python3-evdev
sudo usermod -a -G video,input $USER
```

Logout/login required for group changes.

### 1.4 Input Device Permissions

```bash
echo 'KERNEL=="event*", SUBSYSTEM=="input", MODE="0660", GROUP="input"' | sudo tee /etc/udev/rules.d/99-input.rules
sudo udevadm control --reload-rules && sudo udevadm trigger
```

---

## SECTION 2: WARLOCK INSTALLATION

### 2.1 Clone Repository

```bash
cd ~
git clone https://github.com/preparedcitizencorps/warlock.git
cd warlock/software
```

### 2.2 Python Dependencies

```bash
pip3 install -r helmet/requirements.txt --break-system-packages
pip3 install --break-system-packages "lap>=0.5.12"
```

---

## SECTION 3: CAMERA CONFIGURATION

**WARLOCK AUTO-DETECTS ALL CAMERA TYPES**

System automatically initializes:
- USB cameras
- Standard Pi cameras (v2/v3/HQ)
- Arducam Native sensors (IMX462/IMX290/IMX327)
- Arducam PiVariety modules

### 3.1 USB Cameras

Plug and verify:

```bash
ls /dev/video*
```

### 3.2 Standard Pi Cameras

Test detection:

```bash
rpicam-hello --list-cameras
rpicam-still -t 5000 -n -o test.jpg
```

### 3.3 Arducam Native Sensors

**SKU:** B0423 (IMX462) | B0424 (IMX290) | B0425 (IMX327)

Configure dtoverlay:

```bash
sudo nano /boot/firmware/config.txt
```

Add under `[all]`:

```
# IMX462
dtoverlay=imx462

# IMX290 / IMX327
dtoverlay=imx290,clock-frequency=37125000
```

Reboot and test:

```bash
sudo reboot
rpicam-hello --list-cameras
```

### 3.4 Arducam PiVariety Modules

**Connection:** Camera Port 1 (between Ethernet/HDMI, silver contacts face Ethernet)

Install PiVariety packages:

```bash
cd ~
wget -O install_pivariety_pkgs.sh https://github.com/ArduCAM/Arducam-Pivariety-V4L2-Driver/releases/download/install_script/install_pivariety_pkgs.sh
chmod +x install_pivariety_pkgs.sh
./install_pivariety_pkgs.sh -p libcamera_dev
./install_pivariety_pkgs.sh -p libcamera_apps
```

Configure overlay:

```bash
sudo nano /boot/firmware/config.txt
```

Add under `[all]`:

```
dtoverlay=arducam-pivariety
```

Reboot and verify:

```bash
sudo reboot
rpicam-hello --list-cameras
```

**Hardware checklist:**
- Ribbon cable seated both ends (click sound)
- Silver contacts face Ethernet port
- ESD precautions observed

---

## SECTION 4: NETWORK CONFIG

Edit config:

```bash
nano ~/warlock/software/helmet/helmet_config.yaml
```

Set parameters:

```yaml
network:
  source_id: "WARLOCK-001-HMU"
  bmu_host: "192.168.200.2"
  tcp_port: 5000
  udp_port: 5001
```

USB-C Ethernet static IP (optional):

```bash
sudo nano /etc/dhcpcd.conf
```

Add:

```
interface usb0
static ip_address=192.168.200.1/24
```

---

## SECTION 5: YOLO MODEL

```bash
cd ~/warlock/software
cp /path/to/yolo11n-seg.pt helmet/
```

Model auto-downloads on first run if missing.

---

## SECTION 6: OPERATIONAL TEST

### Desktop Mode (SSH with X forwarding)

```bash
cd ~/warlock/software
python3 helmet/helmet_main.py --standalone
```

### Headless Mode (DRM/KMS)

```bash
cd ~/warlock/software
WARLOCK_USE_DRM=1 python3 helmet/helmet_main.py --standalone
```

**Controls:** `Q` quit | `H` help | `P` plugins | `Y` YOLO | `F` FPS

---

## SECTION 7: AUTO-START SERVICE

Create service file:

```bash
sudo nano /etc/systemd/system/warlock-hmu.service
```

Content:

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

Check status:

```bash
sudo systemctl status warlock-hmu
journalctl -u warlock-hmu -f
```

---

## SECTION 8: HAILO AI KIT (OPTIONAL)

```bash
wget https://github.com/hailo-ai/hailo-rpi5-examples/releases/download/v1.0.0/hailo-rpi5-examples-v1.0.0.deb
sudo dpkg -i hailo-rpi5-examples-v1.0.0.deb
hailo-verify
```

---

## TROUBLESHOOTING

### Camera Not Detected

```bash
rpicam-hello --list-cameras
```

**No cameras:**
1. Check cable orientation (silver contacts face Ethernet)
2. Verify Camera Port 1 connection
3. Check dtoverlay in `/boot/firmware/config.txt`
4. Reboot after config changes

### CSI Display Issues (Pi 0-3)

```bash
sudo raspi-config
# Advanced Options → Glamor acceleration
# Advanced Options → GL Driver → GL (Full KMS)
sudo reboot
```

### I2C Errors (Error -121)

Hardware fault indicated. Actions:
1. Reseat ribbon cable both ends
2. Test different camera module
3. Use USB camera as backup

### Missing Dependencies

```bash
pip3 install --break-system-packages "lap>=0.5.12"
```

### Hailo Not Working

```bash
hailo-verify
```

### IMU Not Detected

```bash
sudo i2cdetect -y 1
```

Should show device at 0x4a or 0x4b.

### BMU Connection Failed

```bash
ping 192.168.200.2
```

Check cable, verify BMU IP in config.

---

## PERFORMANCE OPTIMIZATION

### GPU Memory

```bash
sudo nano /boot/firmware/config.txt
```

Add:

```
gpu_mem=256
```

### Overclock (if needed)

```bash
sudo nano /boot/firmware/config.txt
```

Add:

```
arm_freq=2400
over_voltage=6
```

### Temperature Monitoring

```bash
watch vcgencmd measure_temp
```

Target: Below 70°C under load

---

## PERFORMANCE METRICS

| Mode | FPS | Latency | CPU | Use Case |
|------|-----|---------|-----|----------|
| X11 | 45-50 | ~10ms | 15-20% | Development |
| DRM/KMS | 55-60 | ~2ms | 8-12% | Field ops |

**With Hailo-8L:** 30-60 FPS, 15-20ms inference

---

**END OF MANUAL**
