# WARLOCK Software - Two-Pi Architecture

This directory contains the software for the WARLOCK two-Pi distributed system.

## Directory Structure

```
software/
├── helmet/                 # Helmet-Mounted Unit (HMU)
│   ├── core/              # Camera, networking
│   ├── hud/               # HUD plugins and rendering
│   ├── helmet_main.py     # Entry point
│   ├── helmet_config.yaml # Configuration
│   ├── requirements.txt   # HMU dependencies
│   └── INSTALL.md         # Installation guide
│
├── body/                   # Body-Mounted Unit (BMU)
│   ├── core/              # GPS, network server
│   ├── comms/             # Radio, mesh, ATAK (TODO)
│   ├── sigint/            # RF, WiFi CSI (TODO)
│   ├── body_main.py       # Entry point
│   ├── requirements.txt   # BMU dependencies
│   └── INSTALL.md         # Installation guide
│
├── common/                 # Shared code
│   ├── plugin_base.py     # HUD plugin framework
│   ├── data_models.py     # Shared data structures
│   ├── protocol.py        # Network protocol
│   ├── network_base.py    # Network base class
│   └── requirements.txt   # Common dependencies
│
└── tests/                  # Unit tests
```

## Quick Start

### Run Helmet Unit (Standalone)

No BMU required, uses simulated data:

```bash
cd software
python3 helmet/helmet_main.py --standalone
```

### Run Both Units (Local Testing)

**Terminal 1 - Body Unit:**

```bash
python3 body/body_main.py
```

**Terminal 2 - Helmet Unit:**

```bash
python3 helmet/helmet_main.py
```

The HMU will connect to BMU and receive GPS data.

## Configuration

### Helmet Unit

Edit `helmet/helmet_config.yaml`:

- Network settings (BMU IP address)
- Plugin configuration
- Keybinds

### Body Unit

Currently uses defaults. Configuration file coming in Phase 2.

For detailed hardware setup instructions:

- **HMU:** See `helmet/INSTALL.md`
- **BMU:** See `body/INSTALL.md`

## Development

### Adding New Plugins

1. Create plugin in `helmet/hud/plugins/your_plugin.py`
2. Inherit from `common.plugin_base.HUDPlugin`
3. Add to `helmet/helmet_config.yaml` plugins list
4. Hot-reload with `P` key in HMU

### Adding BMU Features

1. Create module in `body/comms/` or `body/sigint/`
2. Register message handlers in `body_main.py`
3. Add message types to `common/protocol.py` if needed

## Testing

```bash
cd /home/jpb/dev/pcc/warlock/software
pytest -v tests/
```

## Documentation

- **Architecture:** `../docs/architecture-two-pi-system.md`
- **Migration Status:** `../docs/MIGRATION-STATUS.md`
- **Hardware Decisions:** `../docs/hardware-decisions.md`

## Dependencies

### Development (Single Machine)

Install dependencies for both units:

```bash
pip install -r requirements.txt
```

For development tools:

```bash
pip install -r requirements-dev.txt
```

### Production (Separate Hardware)

**On Helmet Pi:**

```bash
cd /path/to/warlock/software
pip install -r helmet/requirements.txt
```

**On Body Pi:**

```bash
cd /path/to/warlock/software
pip install -r body/requirements.txt
```

**Note:** Some dependencies (Hailo SDK, CSI tools) require additional setup. See `helmet/requirements.txt` and `body/requirements.txt` for details.

## Troubleshooting

**HMU won't connect to BMU:**

- Check BMU is running first
- Verify IP address in `helmet/helmet_config.yaml`
- Try `--standalone` mode to rule out camera issues

**Camera error:**

- Check webcam is not in use by another app
- Try `ls /dev/video*` to see available cameras
- Update device index in code if needed

**Plugin not loading:**

- Check plugin inherits from `HUDPlugin`
- Verify `METADATA` is defined as class-level attribute
- Check `helmet_config.yaml` syntax

**Import errors:**

- Make sure you're running from `software/` directory
- Python path issues: `export PYTHONPATH=$(pwd)`

## Status

**Phase 1 - Network Foundation:** IN PROGRESS

- ✅ Directory structure
- ✅ Common code extracted
- ✅ HMU functional (standalone + networked)
- ✅ BMU functional (GPS simulator + server)
- 🔄 Testing end-to-end communication

See `../docs/MIGRATION-STATUS.md` for detailed progress.
