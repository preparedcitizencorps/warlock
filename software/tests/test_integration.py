import pytest
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from hud import HUDContext, PluginManager
from hud.config_loader import load_config, create_plugin_config


class TestPluginSystemIntegration:
    """Test the full plugin system works end-to-end."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)
        self.manager = PluginManager(self.context, plugin_dir="hud/plugins")

    def test_can_discover_all_plugins(self):
        """Plugin discovery should find all plugin files."""
        discovered = self.manager.discover_plugins()

        assert len(discovered) > 0, "Should discover at least one plugin"
        for name, plugin_class in discovered.items():
            from hud.plugin_base import HUDPlugin
            assert issubclass(plugin_class, HUDPlugin), \
                f"{name} must be a subclass of HUDPlugin"

    def test_can_load_all_configured_plugins(self):
        """All enabled plugins in config should load successfully."""
        self.manager.discover_plugins()

        config_path = Path("hud_config.yaml")
        if not config_path.exists():
            pytest.skip("hud_config.yaml not found")

        config = load_config(str(config_path))

        plugin_configs = []
        for plugin_data in config.get('plugins', []):
            if not plugin_data.get('enabled', True):
                continue
            plugin_name = plugin_data['name']
            plugin_config = create_plugin_config(plugin_data)
            plugin_configs.append((plugin_name, plugin_config))

        try:
            loaded = self.manager.load_plugins_with_dependencies(plugin_configs)
            assert len(loaded) > 0, "Should load at least one plugin"
        except ValueError as e:
            pytest.fail(f"Failed to load plugins due to circular dependency: {e}")

    def test_render_pipeline_completes(self):
        """Basic render pipeline should complete without crashing."""
        self.manager.discover_plugins()

        from tests.fixtures.mock_plugins import ProviderPlugin, IndependentPlugin

        self.manager.plugin_classes['ProviderPlugin'] = ProviderPlugin
        self.manager.plugin_classes['IndependentPlugin'] = IndependentPlugin

        configs = [
            ('ProviderPlugin', create_plugin_config({'z_index': 1})),
            ('IndependentPlugin', create_plugin_config({'z_index': 2}))
        ]

        loaded = self.manager.load_plugins_with_dependencies(configs)

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        self.manager.update()

        result = self.manager.render(frame)

        assert isinstance(result, np.ndarray)
        assert result.shape == frame.shape

    def test_plugins_render_in_z_index_order(self):
        """Plugins should render in z-index order, not load order."""
        from tests.fixtures.mock_plugins import IndependentPlugin

        class LowZPlugin(IndependentPlugin):
            def __init__(self, context, config):
                super().__init__(context, config)
                self.metadata.name = "LowZ"

            def render(self, frame):
                frame[0, 0] = [1, 0, 0]
                return frame

        class HighZPlugin(IndependentPlugin):
            def __init__(self, context, config):
                super().__init__(context, config)
                self.metadata.name = "HighZ"

            def render(self, frame):
                frame[0, 0] = [2, 0, 0]
                return frame

        self.manager.plugin_classes = {
            'LowZPlugin': LowZPlugin,
            'HighZPlugin': HighZPlugin
        }

        low_config = create_plugin_config({'z_index': 1})
        high_config = create_plugin_config({'z_index': 10})

        self.manager.load_plugin(HighZPlugin, high_config)
        self.manager.load_plugin(LowZPlugin, low_config)

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = self.manager.render(frame)

        assert result[0, 0, 0] == 2, "HighZ plugin should render last (overwriting LowZ)"


class TestEventSystem:
    """Test inter-plugin event communication."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)

    def test_events_can_be_emitted(self):
        """Plugins should be able to emit events."""
        self.context.emit_event('test_event', {'key': 'value'})

        events = self.context.get_events('test_event')

        assert len(events) == 1
        assert events[0]['type'] == 'test_event'
        assert events[0]['data']['key'] == 'value'

    def test_events_cleared_each_frame(self):
        """Events should be cleared after each frame."""
        self.context.emit_event('test_event', {})

        assert len(self.context.events) == 1

        self.context.clear_events()

        assert len(self.context.events) == 0


class TestConfigLoading:
    """Test configuration loading and validation."""

    def test_can_load_valid_config(self):
        """Should load valid YAML config without errors."""
        config_path = Path("hud_config.yaml")
        if not config_path.exists():
            pytest.skip("hud_config.yaml not found")

        config = load_config(str(config_path))

        assert 'plugins' in config
        assert isinstance(config['plugins'], list)

    def test_handles_missing_config_gracefully(self):
        """Should return default config when file missing."""
        config = load_config("nonexistent.yaml")

        assert 'plugins' in config
        assert config['plugins'] == []
