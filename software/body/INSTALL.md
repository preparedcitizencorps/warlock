# Body-Mounted Unit (BMU) Installation

Instructions for deploying the BMU to a Raspberry Pi 5.

## Hardware Requirements

- Raspberry Pi 5 (8GB recommended)
- Intel AX210 WiFi 6E card (M.2 or USB adapter)
- RTL-SDR v4 dongle
- LoRa SX1262 module
- SA818 VHF/UHF radio module
- U-blox ZED-F9P GPS module + active antenna
- BNO085 IMU module
- MicroSD card (64GB+)
- Power supply (12V battery with buck converter to 5V @ 5A)

## Software Installation

### 1. Flash Raspberry Pi OS

```bash
# Use Raspberry Pi Imager
# OS: Raspberry Pi OS (64-bit, Bookworm or later)
# Enable SSH, set hostname to 'warlock-bmu'
```

### 2. Initial Setup

```bash
ssh pi@warlock-bmu.local

# Update system
sudo apt update && sudo apt upgrade -y

# Install system dependencies
sudo apt install -y \
    python3-pip \
    git \
    i2c-tools \
    gpsd \
    gpsd-clients \
    rtl-sdr \
    librtlsdr-dev
```

### 3. Enable Interfaces

```bash
sudo raspi-config
# Interface Options → I2C → Enable
# Interface Options → Serial → Enable (for SA818)
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
pip3 install -r body/requirements.txt
```

### 6. Configure GPS (gpsd)

```bash
# Find GPS device
ls /dev/ttyACM* /dev/ttyUSB*

# Configure gpsd
sudo nano /etc/default/gpsd
# Set: DEVICES="/dev/ttyACM0"  (or your GPS device)
# Set: GPSD_OPTIONS="-n"

# Restart gpsd
sudo systemctl restart gpsd

# Test
cgps
# Should show GPS data
```

### 7. Configure RTL-SDR

```bash
# Test RTL-SDR
rtl_test
# Should detect device

# Blacklist DVB driver (prevents conflicts)
sudo nano /etc/modprobe.d/blacklist-dvb.conf
# Add: blacklist dvb_usb_rtl28xxu
sudo reboot
```

### 8. Configure Intel AX210 WiFi

```bash
# Verify WiFi card detected
lspci | grep -i wireless
# or for USB: lsusb | grep -i wifi

# Install firmware (if needed)
sudo apt install -y firmware-iwlwifi
sudo reboot

# Test WiFi 6E (6 GHz)
iw list | grep -A 10 "6 GHz"
```

### 9. Setup WiFi Mesh (802.11s)

```bash
# Install mesh tools
sudo apt install -y batctl

# Create mesh interface
sudo iw dev wlan0 interface add mesh0 type mp
sudo ip link set mesh0 up
sudo iw dev mesh0 mesh join WARLOCK_MESH freq 5180

# Verify
sudo iw dev mesh0 station dump
```

### 10. Configure Network for HMU Connection

For USB-C Ethernet connection:

```bash
# Set static IP on usb0
sudo nano /etc/dhcpcd.conf
# Add:
# interface usb0
# static ip_address=192.168.200.2/24
```

### 11. Test BMU

```bash
cd ~/warlock/software
python3 body/body_main.py
# Should start and wait for HMU connections
```

## Configure SA818 Radio (Phase 4)

```bash
# Find serial port
ls /dev/ttyUSB* /dev/ttyS*

# Test connection (115200 baud)
screen /dev/ttyUSB0 115200
# Type: AT+DMOCONNECT
# Should respond: +DMOCONNECT:0
# Ctrl-A, K to exit
```

## Configure LoRa Module (Phase 5)

```bash
# LoRa uses SPI, ensure enabled in raspi-config
# GPIO pins:
# - CS: GPIO8 (CE0)
# - RST: GPIO25
# - IRQ: GPIO24

# Test in Python:
python3 -c "import spidev; spi = spidev.SpiDev(); spi.open(0, 0); print('SPI OK')"
```

## Auto-Start on Boot

Create systemd service:

```bash
sudo nano /etc/systemd/system/warlock-bmu.service
```

```ini
[Unit]
Description=WARLOCK Body-Mounted Unit
After=network.target gpsd.service

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/warlock/software
ExecStart=/usr/bin/python3 body/body_main.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

Enable:

```bash
sudo systemctl daemon-reload
sudo systemctl enable warlock-bmu
sudo systemctl start warlock-bmu
```

Check status:

```bash
sudo systemctl status warlock-bmu
sudo journalctl -u warlock-bmu -f  # Follow logs
```

## Troubleshooting

**GPS not working:**

```bash
cgps
# If no data, check:
ls -l /dev/ttyACM*
sudo systemctl status gpsd
```

**RTL-SDR not detected:**

```bash
rtl_test
# If error, check USB connection and blacklist DVB driver
dmesg | grep rtl
```

**WiFi mesh not connecting:**

```bash
sudo iw dev mesh0 station dump
# Should show peer stations
# If empty, check:
# - Mesh ID matches (WARLOCK_MESH)
# - Frequency matches
# - WiFi card supports mesh mode
```

**HMU can't connect:**

```bash
# Check network server is listening
sudo netstat -tulpn | grep 5000
# Should show python listening on 0.0.0.0:5000

# Check firewall (if enabled)
sudo ufw status
sudo ufw allow 5000/tcp
sudo ufw allow 5001/udp
```

**IMU not detected:**

```bash
sudo i2cdetect -y 1
# Should show device at 0x4a or 0x4b
```

## Performance Monitoring

**Check CPU temperature:**

```bash
watch vcgencmd measure_temp
```

**Monitor network traffic:**

```bash
sudo apt install -y iftop
sudo iftop -i usb0  # or wlan0 for WiFi
```

**Check system load:**

```bash
htop
```

## Security Hardening

**Change default password:**

```bash
passwd
```

**Setup SSH keys (disable password auth):**

```bash
ssh-keygen -t ed25519
# Copy public key to authorized_keys
sudo nano /etc/ssh/sshd_config
# Set: PasswordAuthentication no
sudo systemctl restart sshd
```

**Enable firewall:**

```bash
sudo apt install -y ufw
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 5000/tcp  # HMU connection
sudo ufw allow 5001/udp  # HMU connection
sudo ufw enable
```
