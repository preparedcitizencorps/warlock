"""Tests for plugin interface contracts and conventions."""

import pytest
import sys
from pathlib import Path
import inspect

sys.path.insert(0, str(Path(__file__).parent.parent / "software"))

from common.plugin_base import HUDContext
from helmet.hud.plugin_manager import PluginManager
from common.plugin_base import HUDPlugin, PluginConfig
from tests.fixtures.mock_plugins import ProviderPlugin


class TestPluginInterface:
    """Test that plugins follow the HUDPlugin interface contract."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)
        self.manager = PluginManager(self.context, plugin_dir="helmet/hud/plugins")

    def test_all_plugins_implement_required_methods(self):
        """Every plugin must implement abstract methods."""
        self.manager.discover_plugins()

        required_methods = ['initialize', 'update', 'render']

        for name, plugin_class in self.manager.plugin_classes.items():
            for method_name in required_methods:
                assert hasattr(plugin_class, method_name), \
                    f"{name} must implement {method_name}()"

                method = getattr(plugin_class, method_name)
                assert callable(method), f"{name}.{method_name} must be callable"

    def test_all_plugins_have_metadata(self):
        """Every plugin must have metadata with required fields."""
        self.manager.discover_plugins()

        required_fields = ['name', 'version', 'author', 'description']

        for name, plugin_class in self.manager.plugin_classes.items():
            plugin = plugin_class(self.context, PluginConfig())

            assert hasattr(plugin, 'metadata'), f"{name} must have metadata"

            for field in required_fields:
                assert hasattr(plugin.metadata, field), \
                    f"{name}.metadata must have {field}"

    def test_plugin_initialize_returns_bool(self):
        """initialize() must return boolean."""
        plugin = ProviderPlugin(self.context, PluginConfig())
        result = plugin.initialize()

        assert isinstance(result, bool), "initialize() must return bool"

    def test_plugin_render_returns_frame(self):
        """render() must return numpy array (frame)."""
        import numpy as np

        plugin = ProviderPlugin(self.context, PluginConfig())
        plugin.initialize()

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = plugin.render(frame)

        assert isinstance(result, np.ndarray), "render() must return numpy array"
        assert result.shape == frame.shape, "render() must preserve frame shape"


class TestPluginDataContract:
    """Test conventions for data sharing between plugins."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)
        self.manager = PluginManager(self.context, plugin_dir="helmet/hud/plugins")

    def test_provides_documented_in_metadata(self):
        """Plugins using provide_data() should declare what they provide."""
        self.context.state.clear()
        plugin = ProviderPlugin(self.context, PluginConfig())
        plugin.initialize()

        provided_keys = set(self.context.state.keys())

        for key in provided_keys:
            assert key in plugin.metadata.provides, \
                f"Plugin provides '{key}' but doesn't declare it in metadata.provides"

    def test_require_data_raises_on_missing(self):
        """require_data() must raise RuntimeError when data missing."""
        plugin = ProviderPlugin(self.context, PluginConfig())

        with pytest.raises(RuntimeError, match="requires"):
            plugin.require_data('nonexistent_key')

    def test_get_data_returns_default_on_missing(self):
        """get_data() must return default when data missing."""
        plugin = ProviderPlugin(self.context, PluginConfig())

        result = plugin.get_data('nonexistent_key', {'default': True})

        assert result == {'default': True}

    def test_provide_data_adds_to_context(self):
        """provide_data() must add data to context.state."""
        plugin = ProviderPlugin(self.context, PluginConfig())

        plugin.provide_data('test_key', 'test_value')

        assert 'test_key' in self.context.state
        assert self.context.state['test_key'] == 'test_value'


class TestPluginLifecycle:
    """Test plugin lifecycle management."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)
        self.manager = PluginManager(self.context, plugin_dir="tests/fixtures")

    def test_plugin_initialized_flag_set_after_load(self):
        """Plugin.initialized should be True after successful load."""
        self.manager.plugin_classes = {'ProviderPlugin': ProviderPlugin}

        plugin = self.manager.load_plugin(ProviderPlugin, PluginConfig())

        assert plugin.initialized is True

    def test_plugin_not_added_if_initialize_fails(self):
        """Plugin should not be added to manager if initialize() returns False."""
        class FailingPlugin(ProviderPlugin):
            def initialize(self):
                return False

        self.manager.plugin_classes = {'FailingPlugin': FailingPlugin}

        result = self.manager.load_plugin(FailingPlugin, PluginConfig())

        assert result is None
        assert len(self.manager.plugins) == 0

    def test_cleanup_called_on_unload(self):
        """cleanup() should be called when plugin is unloaded."""
        class TrackablePlugin(ProviderPlugin):
            def __init__(self, context, config):
                super().__init__(context, config)
                self.cleanup_called = False

            def cleanup(self):
                self.cleanup_called = True

        self.manager.plugin_classes = {'TrackablePlugin': TrackablePlugin}

        plugin = self.manager.load_plugin(TrackablePlugin, PluginConfig())
        self.manager.unload_plugin(plugin)

        assert plugin.cleanup_called is True
