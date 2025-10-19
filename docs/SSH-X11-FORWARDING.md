# SSH X11 Forwarding for WARLOCK

This guide explains how to display WARLOCK's output on your local computer when SSH'd into the Raspberry Pi.

---

## Quick Start

From your local computer:

```bash
ssh -X jpb@warlock-hmu.local
cd ~/warlock
./run_warlock.sh
```

The WARLOCK display window will appear on your local computer's monitor.

---

## How It Works

**X11 Forwarding** tunnels graphical output from the Raspberry Pi through SSH to your local machine. This is perfect for:
- Development and testing
- Debugging camera issues
- Viewing HUD output without connecting AR glasses
- Remote demonstrations

---

## Requirements

### On Raspberry Pi (Server)

✅ **Already configured** - The setup script enables X11 forwarding automatically:
- SSH server has `X11Forwarding yes` enabled
- `xauth` package installed

### On Your Local Computer (Client)

**Linux/macOS:**
- X11 server running (usually pre-installed)
- macOS may need XQuartz: `brew install --cask xquartz`

**Windows:**
- Install VcXsrv, Xming, or MobaXterm
- Configure to allow X11 connections

---

## Usage Examples

### Basic X11 Forwarding
```bash
ssh -X jpb@warlock-hmu.local
cd ~/warlock
./run_warlock.sh
```

### Trusted X11 (faster, less secure)
```bash
ssh -Y jpb@warlock-hmu.local
cd ~/warlock
./run_warlock.sh
```

### One-liner Remote Execution
```bash
ssh -X jpb@warlock-hmu.local '~/warlock/run_warlock.sh'
```

---

## Display Modes Comparison

| Mode | Use Case | Pros | Cons |
|------|----------|------|------|
| **X11 (ssh -X)** | Development/testing | Easy remote access | Requires SSH connection |
| **DRM** | Field deployment | Low latency, no X11 | Requires physical display |

---

## Troubleshooting

### "cannot open display" error

**Check DISPLAY variable:**
```bash
echo $DISPLAY
# Should show: localhost:10.0 or similar
```

**If empty, reconnect with `-X` flag:**
```bash
exit
ssh -X jpb@warlock-hmu.local
```

### Slow/laggy display

**Use compression for faster remote display:**
```bash
ssh -XC jpb@warlock-hmu.local
```

**Or use trusted X11 (faster but less secure on untrusted networks):**
```bash
ssh -Y jpb@warlock-hmu.local
```

### "No protocol specified" error

**On Pi, regenerate Xauthority:**
```bash
rm ~/.Xauthority
exit
```

Reconnect with `ssh -X` to regenerate.

### X11 forwarding disabled

**On Pi, check SSH config:**
```bash
grep X11Forwarding /etc/ssh/sshd_config
# Should show: X11Forwarding yes
```

**If not, enable it:**
```bash
sudo sed -i 's/^#*X11Forwarding.*/X11Forwarding yes/' /etc/ssh/sshd_config
sudo systemctl restart ssh
```

---

## SSH Config Shortcut

Add to your local `~/.ssh/config` for easier connection:

```
Host warlock
    HostName warlock-hmu.local
    User jpb
    ForwardX11 yes
    ForwardX11Trusted yes
    Compression yes
```

Then connect with just:
```bash
ssh warlock
```

---

## Performance Notes

- **Local network**: X11 forwarding works great over LAN
- **Remote/WAN**: Use compression (`-C` flag) or consider VNC instead
- **Latency**: Expect 20-50ms additional latency compared to direct display
- **Bandwidth**: ~5-15 Mbps for 1280x720 @ 30 FPS

---

## See Also

- [INSTALL.md](INSTALL.md) - Main installation guide
- [SYSTEM-OVERVIEW.md](SYSTEM-OVERVIEW.md) - System architecture
- [README.md](../README.md) - Project overview
