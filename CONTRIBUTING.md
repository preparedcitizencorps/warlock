# Contributing to Project WARLOCK

Thanks for your interest in building the future of tactical AR!

This is an open source project. We're building hardware, software, and documentation together as a community.

## How to Contribute

### Found a Bug?
Open an issue with:
- What you expected to happen
- What actually happened
- Steps to reproduce
- Your hardware/software setup

### Have an Idea?
Open an issue to discuss it first. Let's talk through the approach before you spend time coding.

### Want to Submit Code?
1. Fork the repo
2. Create a feature branch (`git checkout -b feature/cool-thing`)
3. Make your changes
4. Test it works
5. Commit with a clear message
6. Push and open a pull request

### Building Hardware?
Share your build! We want to see:
- Photos of your setup
- Parts you used (if different from BOM)
- What worked and what didn't
- Any modifications you made

### Writing Documentation?
Documentation contributions are gold. Help us:
- Fix typos and unclear instructions
- Add troubleshooting tips
- Create assembly guides with photos
- Write tutorials

## Development Setup

### Install Dependencies

```bash
cd software
pip install -r requirements.txt -r requirements-dev.txt
```

### Install Pre-commit Hooks (Recommended)

Pre-commit hooks automatically format and lint your code before each commit:

```bash
pip install pre-commit
pre-commit install
```

**What gets checked:**
- Python formatting (black, 120 char lines)
- Import sorting (isort)
- Syntax errors (flake8)
- Trailing whitespace
- YAML/JSON validation

**Manual commands:**
```bash
# Run all checks on all files
pre-commit run --all-files

# Skip hooks for a commit (not recommended)
git commit --no-verify

# Switch to pre-push hooks (runs before push instead of commit)
pre-commit uninstall
pre-commit install --hook-type pre-push
```

## Code Style

**Python:**
- Follow PEP 8
- Line length: 120 characters (enforced by black)
- Import sorting: isort with black profile
- Comment your code
- Keep functions small and focused
- Use meaningful variable names

**Hardware:**
- Document part numbers and sources
- Include photos or diagrams
- Note any safety considerations
- Share CAD files if you design mounts/cases

**Documentation:**
- Write clearly and concisely
- Include examples
- Add screenshots/photos where helpful
- Test your instructions by following them

## Testing

Before submitting:
- Run your code and verify it works
- Test on actual hardware when possible
- Check that documentation is accurate
- Make sure you haven't broken existing features

## Communication

- **Discord:** [https://discord.gg/uFMEug4Bb9](https://discord.gg/uFMEug4Bb9) - Daily chat, questions, sharing builds
- **GitHub Issues:** Technical discussions, bug reports, feature requests
- **Pull Requests:** Code reviews and merge discussions

## What We're Looking For

**Right now (Phase 0-1):**
- Testing the basic detection script
- Improving the detection accuracy
- Raspberry Pi 5 setup scripts
- Low-light camera optimization
- Assembly documentation

**Soon:**
- Hardware mount designs
- Power optimization
- HUD rendering code
- Field testing feedback

---

## Plugin Development Guide

WARLOCK uses a modular plugin architecture. Plugins are hot-swappable components that extend functionality without modifying core code.

### Creating a Plugin

#### 1. Create Plugin File

Create a new file in `software/hud/plugins/your_plugin.py`:

```python
#!/usr/bin/env python3
from hud.plugin_base import HUDPlugin, HUDContext, PluginConfig, PluginMetadata
import cv2
import numpy as np

class TargetTrackerPlugin(HUDPlugin):
    METADATA = PluginMetadata(
        name="Target Tracker",
        version="1.0.0",
        author="Your Callsign",
        description="Tracks and displays priority targets",
        provides=['target_list'],
        consumes=['yolo_detections']  # Soft dependency
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

    def initialize(self) -> bool:
        self.targets = []
        return True

    def process_targets(self, detections: list):
        new_targets = []
        for det in detections:
            if det.get('confidence', 0) > 0.5:
                x1, y1, x2, y2 = det['bbox']
                center_x = (x1 + x2) // 2
                center_y = (y1 + y2) // 2
                new_targets.append({
                    'pos': (center_x, center_y),
                    'id': det.get('id', len(new_targets)),
                    'confidence': det['confidence']
                })
        self.targets = new_targets

    def update(self, delta_time: float):
        detections = self.get_data('yolo_detections', [])
        self.process_targets(detections)
        self.provide_data('target_list', self.targets)

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible:
            return frame
        for target in self.targets:
            cv2.circle(frame, target['pos'], 20, (0, 255, 0), 2)
        return frame

    def handle_key(self, key: int) -> bool:
        if key == ord('t'):
            self.toggle_visibility()
            return True
        return False
```

#### 2. Add to Configuration

Add your plugin to `software/hud_config.yaml`:

```yaml
plugins:
  - name: TargetTrackerPlugin
    enabled: true
    visible: true
    z_index: 50
    settings:
      max_targets: 10
      priority_range: 100
```

#### 3. Deploy and Test

```bash
python software/warlock.py
# Press P → select plugin → R to hot-reload
```

### Plugin Dependencies

#### Data Sharing

**Provider Plugin:**
```python
class GPSPlugin(HUDPlugin):
    METADATA = PluginMetadata(
        name="GPS",
        version="1.0.0",
        author="Your Callsign",
        description="GPS position provider",
        provides=['gps_position']
    )

    def update(self, delta_time: float):
        self.provide_data('gps_position', {'lat': lat, 'lon': lon})
```

**Consumer Plugin:**
```python
class NavPlugin(HUDPlugin):
    METADATA = PluginMetadata(
        name="Navigator",
        version="1.0.0",
        author="Your Callsign",
        description="Navigation system",
        consumes=['gps_position']  # Soft dependency
        # OR
        # dependencies=['GPSPlugin']  # Hard dependency
    )

    def update(self, delta_time: float):
        # Soft dependency with fallback
        gps = self.get_data('gps_position', {'lat': 0, 'lon': 0})

        # Hard dependency with error
        gps = self.require_data('gps_position', "GPS required")
```

#### Load Order

The plugin system uses **automatic topological sorting** - just declare dependencies and the system handles load order.

| Type | Declaration | Access | Behavior |
|------|------------|--------|----------|
| **Soft** | `consumes=['key']` | `get_data('key', fallback)` | Adapts if missing |
| **Hard** | `dependencies=['Plugin']` | `require_data('key', msg)` | Fails if missing |

**Note:** Load order ≠ Render order. Use `z_index` in config for rendering layers.

### API Reference

#### Core Classes
- `HUDPlugin` - Base class for all plugins
- `HUDContext` - Shared state + event system
- `PluginConfig` - Configuration container
- `PluginMetadata` - Plugin information

#### Plugin Structure

All plugins must define `METADATA` at class level:

```python
class MyPlugin(HUDPlugin):
    METADATA = PluginMetadata(
        name="My Plugin",
        version="1.0.0",
        author="Your Callsign",
        description="What it does",
        provides=['output_key'],      # Optional: data provided to other plugins
        consumes=['input_key'],        # Optional: soft dependency
        dependencies=['OtherPlugin']   # Optional: hard dependency
    )
```

#### Lifecycle Methods

- `initialize()` → One-time setup, return `True` if successful
- `update(delta_time)` → Per-frame state update (called before render)
- `render(frame)` → Draw to frame, return modified frame
- `handle_key(key)` → Process keyboard input, return `True` if handled
- `handle_event(event)` → Inter-plugin events
- `cleanup()` → Resource cleanup on shutdown

#### Data Access Methods

**Inter-plugin communication via shared data:**

```python
# Publishing data
self.provide_data('key', value)

# Soft dependency with fallback
data = self.get_data('key', default_value)

# Hard dependency with error
data = self.require_data('key', "Error message if missing")
```

#### State Management

```python
# Read/write shared state
player_pos = self.context.state.get('player_position')
self.context.state['my_data'] = value

# Event system
self.context.post_event('target_acquired', {'id': 123})
```

#### Configuration

Access settings from `hud_config.yaml`:

```python
def __init__(self, context: HUDContext, config: PluginConfig):
    super().__init__(context, config)
    self.max_targets = config.settings.get('max_targets', 10)
    self.range = config.settings.get('priority_range', 100)
```

### Hot Reload Workflow

1. Start WARLOCK: `python software/warlock.py`
2. Press `P` → `A` to enable auto-reload
3. Edit your plugin → save
4. Watch it reload automatically
5. No restart needed!

### Troubleshooting

- **Plugin not loading?**
  - Check that class inherits `HUDPlugin`
  - Verify `METADATA` is defined at class level (not in `__init__`)
  - Ensure file is in `software/hud/plugins/`

- **"must define METADATA" error?**
  - Add `METADATA = PluginMetadata(...)` as class attribute

- **Dependency errors?**
  - Check that provider plugins are loaded before consumers
  - Verify `provides` and `consumes` keys match exactly
  - Use `get_data()` with fallback for optional dependencies

### Plugin Examples

Check existing plugins for reference:
- `yolo_detection.py` - Object detection with YOLO
- `auto_exposure.py` - Camera control and hardware access
- `compass.py` - Simple overlay rendering
- `mini_map.py` - Terrain data and GPS integration
- `fps_counter.py` - Minimal plugin example

---

## Core Infrastructure

WARLOCK separates low-level infrastructure (`software/core/`) from HUD implementation (`software/hud/`).

### Design Principles

- **HUD-Independent**: Core components must not import from `hud/`
- **Reusable**: Can be used in CLI tools, tests, non-HUD contexts
- **Thread-Safe**: Designed for concurrent access

### What Goes in Core

**YES**: Input management, camera control, GPS/sensors, serial communication, hardware abstractions

**NO**: Plugin implementations, UI rendering, HUD overlays, plugin management

### Core Components

**InputManager** (`core/input_manager.py`): Centralized keyboard, GPIO, PTT, serial input handling

**CameraController** (`core/camera_controller.py`): Thread-safe OpenCV wrapper with property whitelisting and range validation

---

## Input Management System

WARLOCK uses a centralized input system that handles keyboard, hardware buttons (PTT), GPIO pins, and serial commands.

### Configuration

All keybinds are defined in `software/hud_config.yaml`:

```yaml
keybinds:
  system:
    quit: q
    help: h
    save_frame: s
  yolo:
    toggle: y
    cycle_mode: v
  # ... more categories
```

### Adding Custom Keybinds

**For plugins:**
```python
class MyPlugin(HUDPlugin):
    def initialize(self) -> bool:
        input_manager = self.context.state.get('input_manager')
        if input_manager:
            input_manager.register_keybind(
                't', 'Toggle target tracker', 'display'
            )
        return True
```

**For hardware inputs (PTT, GPIO, etc.):**
```python
from core.input_manager import InputType

input_manager.register_hardware_input(
    identifier='gpio_17',
    description='Push-to-talk (PTT)',
    category='hardware',
    input_type=InputType.GPIO,
    handler=handle_ptt_press
)
```

### Benefits

- **Single source of truth** - All inputs in `hud_config.yaml`
- **Runtime reconfiguration** - Change keybinds without code changes
- **Hardware ready** - GPIO, PTT buttons, serial commands supported
- **Auto-generated UI** - Keybinds overlay (`K` key) reads from registry

### API Reference

Key methods:
- `register_keybind(key, description, category, handler, enabled)` - Register keyboard input
- `register_hardware_input(identifier, description, category, input_type, handler)` - Register hardware input
- `get_keybinds_by_category()` - Get organized keybinds for UI display

See `software/core/input_manager.py` for full API.

---

## License

By contributing, you agree that your contributions will be licensed under the same license as the project:
- Software: MIT License
- Hardware: CERN-OHL-P-2.0
- Documentation: CC BY-SA 4.0

## Questions?

Not sure if something is worth contributing? Just ask in Discord or open an issue. We're friendly, promise.

---

**Let's build something awesome together.** 🎯
