# WARLOCK FIELD MANUAL

**OPERATOR'S GUIDE**

---

## PRE-OPERATION

### Daily Inspection

**HMU (Helmet Unit):**

1. Check camera lens - clean if dirty
2. Verify cable connection to BMU - secure bayonet lock
3. Check battery charge - min 80% before mission
4. Test power on - green LED indicates boot
5. Verify display output - no dead pixels

**BMU (Body Unit):**

1. Check GPS antenna mount - must have clear sky view
2. Verify radio antenna connection - hand-tight SMA
3. Check battery charge - min 80% before mission
4. Test power on - listen for radio squelch
5. Verify all cables seated - no loose connections

### Pre-Mission Power-On

**SEQUENCE:**

1. Power BMU first (press power button, hold 2 sec)
2. Wait for GPS lock (LED blinks every 1 sec = locked)
3. Power HMU (press power button, hold 2 sec)
4. HMU connects automatically (connection icon on HUD)
5. Verify map shows your position

**If connection fails:**

- Check cable is plugged into both units
- Verify BMU powered on (LED lit)
- Try HMU reboot (hold power 5 sec, release, power on)

---

## OPERATION

### HUD Elements

```
┌─────────────────────────────────────────┐
│  N                            [RF]  85% │  ← Compass, alerts, battery
│  ↑                                      │
│                                         │
│     [PERSON]                            │  ← YOLO detections
│       87%                               │
│       45° 25m                           │
│                                         │
│                                         │
│                                         │
│  ALPHA-1                                │  ← Team positions
│  315° 200m                              │
│                                         │
│  ┌─────────────┐                       │  ← Mini-map
│  │     •       │                       │
│  │   YOU       │                       │
│  │  •ALPHA-1   │                       │
│  └─────────────┘                       │
│                                         │
│  30 FPS  [===LINK===]                  │  ← Status indicators
└─────────────────────────────────────────┘
```

### Key Controls

| Key | Function | Use When |
|-----|----------|----------|
| `H` | Help overlay | Need reminder of controls |
| `Q` | Quit system | End of mission |
| `P` | Plugin panel | Adjust HUD settings |
| `Y` | YOLO on/off | Conserve power / reduce clutter |
| `M` | Map on/off | Navigate / clear view |
| `F` | FPS counter | Check performance |
| `E` | Auto-exposure | Adjust for lighting |

### Detection Indicators

**YOLO Boxes:**

- **Orange box** = Friendly (IFF match)
- **Red box** = Potential threat
- **Percentage** = Confidence (higher = more certain)
- **Distance** = Estimated range in meters
- **Bearing** = Direction relative to your heading

**RF Alerts:**

- **[RF]** icon = Radio transmission detected
- **Red flash** = Strong signal (close proximity)
- **Direction arrow** = Bearing to emitter (if triangulated)

**WiFi Alerts:**

- **[WiFi]** icon = Motion detected through wall
- **Distance** = Estimated range in meters

### Team Coordination

**On HUD:**

- Team callsigns display with bearing and distance
- Icons show status: Green=active, Yellow=wounded, Red=KIA
- Data updates every 200ms via mesh network

**If team member goes silent:**

- Last known position remains on map for 5 minutes
- Status changes to "STALE" after 30 seconds no update

---

## EMERGENCY PROCEDURES

### BMU Failure

**Symptoms:** "NO LINK" warning on HUD

**Actions:**

1. Check cable connection first
2. If cable OK, HMU switches to backup GPS automatically
3. Continue mission with reduced capability:
   - ✅ Camera and YOLO still work
   - ✅ Local map and compass work
   - ❌ No team positions
   - ❌ No RF/WiFi alerts
   - ❌ No radio comms

**Recovery:** Repair/replace BMU at rally point

### GPS Loss

**Symptoms:** "GPS LOST" warning on HUD

**Actions:**

1. Check GPS antenna (BMU) - ensure clear sky view
2. Move to open area if in building/trees
3. System uses IMU dead reckoning (position drifts)
4. Return to last known position for GPS reacquisition

**Critical:** Do not rely on position after 5 minutes without GPS

### Thermal Warning

**Symptoms:** "THERMAL WARNING" on HUD, performance drop

**Actions:**

1. Reduce YOLO usage (press `Y` to disable temporarily)
2. Remove helmet to allow cooling if safe
3. Check ventilation slots not blocked
4. System auto-throttles to prevent damage

**Note:** Combat mode generates most heat - use patrol mode when possible

### Battery Critical

**Symptoms:** "BATTERY LOW" warning at 20%, "BATTERY CRITICAL" at 10%

**Actions:**

1. Switch to patrol mode (reduces power draw)
2. Disable non-essential HUD elements (map, FPS counter)
3. Plan immediate return to base or swap battery
4. System auto-shutdown at 5% to preserve BMU connection log

---

## POST-OPERATION

### Shutdown Sequence

**SEQUENCE:**

1. Press `Q` on HMU (or hold power button 2 sec)
2. Wait for "Shutdown Complete" message
3. Power off BMU (hold power button 2 sec)
4. Disconnect cable
5. Remove batteries for charging

**DO NOT** force power off (hold button 10 sec) unless system frozen

### Data Retrieval

**HMU Logs:** `/home/pi/warlock/logs/hmu_YYYYMMDD.log`
**BMU Logs:** `/home/pi/warlock/logs/bmu_YYYYMMDD.log`

**To Extract:**

```bash
# Remove microSD card, insert in PC
# Or via SSH:
scp pi@warlock-hmu.local:~/warlock/logs/*.log ./mission_logs/
```

### Maintenance

**After Each Mission:**

- Wipe camera lens with microfiber cloth
- Check cable for damage
- Inspect enclosures for cracks
- Charge batteries overnight

**Weekly:**

- Update software: `git pull && pip install -r requirements.txt`
- Run diagnostics: `pytest tests/ -v`
- Check all sensors: `python3 scripts/sensor_test.py`

**Monthly:**

- Re-calibrate IMU (figure-8 motion, 30 seconds)
- Update YOLO model if new version available
- Test WiFi failover: Disconnect cable during operation

---

## TROUBLESHOOTING

### Camera Black Screen

**Cause:** Camera not detected or failed
**Fix:**

```bash
ls /dev/video*  # Should show video0
# If not found:
sudo reboot
```

### YOLO Not Detecting

**Cause:** Model not loaded or Hailo offline
**Fix:**

```bash
hailo-verify  # Should show device detected
# If not found:
sudo reboot
# If still failing, reinstall Hailo drivers
```

### Radio No RX/TX

**Cause:** SA818 not responding or antenna issue
**Fix:**

1. Check antenna connected (hand-tight, not over-tight)
2. Check frequency programmed correctly
3. Test with: `screen /dev/ttyUSB0 115200` → Type `AT+DMOCONNECT`
4. Should respond `+DMOCONNECT:0`

### Mesh Not Connecting

**Cause:** WiFi mesh not joined or out of range
**Fix:**

```bash
sudo iw dev mesh0 station dump
# If empty, rejoin:
sudo iw dev mesh0 mesh join WARLOCK_MESH freq 5180
```

### Frozen HUD

**Cause:** Software crash or deadlock
**Fix:**

1. Press `Q` to quit gracefully
2. If unresponsive, SSH in: `ssh pi@warlock-hmu.local`
3. Kill process: `pkill -9 python3`
4. Restart: `python3 helmet/helmet_main.py`
5. If still frozen, hard reboot (hold power 10 sec)

---

## SAFETY WARNINGS

⚠️ **DO NOT:**

- Point IR emitters at aircraft
- Transmit on unauthorized frequencies
- Use thermal camera to view sun or lasers
- Rely solely on HUD - maintain visual scan
- Operate with cracked thermal camera window (foggy readings)

⚠️ **BATTERY SAFETY:**

- Do not puncture or short circuit
- Do not expose to fire or extreme heat
- Store at 50% charge for long-term
- Dispose per local regulations (lithium hazard)

⚠️ **RF SAFETY:**

- Keep radio antenna 6" from body during TX
- Do not transmit continuously >5 minutes (overheating)
- Limit radio use near medical implants

---

## QUICK REFERENCE

### Power Modes

```
Combat:  60 FPS YOLO, full RF scan  → 2.5hr runtime
Patrol:  30 FPS YOLO, reduced scan  → 4hr runtime
Standby: 15 FPS YOLO, RF off        → 5hr runtime
```

### Status Icons

```
[===LINK===]  = Cable connected
[~~WIFI~~]    = WiFi failover active
[GPS LOCK]    = GPS acquired
[GPS LOST]    = No GPS signal
[RF]          = RF detection active
[WiFi]        = WiFi CSI active
85%           = Battery percentage
```

### Network Addresses

```
HMU: 192.168.200.1
BMU: 192.168.200.2
Ports: TCP 5000, UDP 5001
```

---

*Document Revision: 2025-10-17*
*For Technical Details See: TECHNICAL-SPECS.md*
