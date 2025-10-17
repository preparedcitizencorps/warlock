#!/usr/bin/env python3

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.plugin_base import HUDContext
from helmet.hud.plugin_manager import PluginManager


def test_dependency_order():
    context = HUDContext(1280, 720)
    plugin_manager = PluginManager(context, plugin_dir=str(Path(__file__).parent.parent / "helmet" / "hud" / "plugins"))

    plugin_manager.discover_plugins()

    test_plugins = [
        'CompassPlugin',
        'YOLODetectionPlugin',
        'MiniMapPlugin',
        'BorderPaddingPlugin',
        'FPSCounterPlugin',
        'PluginControlPanel',
    ]

    sorted_plugins = plugin_manager.topological_sort_plugins(test_plugins)

    assert sorted_plugins is not None, "topological_sort_plugins should return a list"
    assert len(sorted_plugins) == len(test_plugins), f"Expected {len(test_plugins)} plugins, got {len(sorted_plugins)}"
    assert set(sorted_plugins) == set(test_plugins), "Sorted plugins should contain exactly the same plugins as input"


def test_render_order_by_z_index():
    from common.plugin_base import PluginConfig

    context = HUDContext(1280, 720)
    plugin_manager = PluginManager(context, plugin_dir=str(Path(__file__).parent.parent / "helmet" / "hud" / "plugins"))

    plugin_manager.discover_plugins()

    test_plugins = [
        'BorderPaddingPlugin',
        'MiniMapPlugin',
        'CompassPlugin',
        'YOLODetectionPlugin',
        'FPSCounterPlugin',
        'PluginControlPanel',
    ]

    z_indices = {}
    for plugin_name in test_plugins:
        if plugin_name in plugin_manager.plugin_classes:
            plugin_class = plugin_manager.plugin_classes[plugin_name]
            temp_instance = plugin_class(context, PluginConfig())
            z_indices[plugin_name] = temp_instance.config.z_index

    expected_render_order = sorted(z_indices.keys(), key=lambda p: z_indices[p])

    actual_render_order = sorted(test_plugins, key=lambda p: z_indices.get(p, 0))

    assert actual_render_order == expected_render_order, \
        f"Render order mismatch: {actual_render_order} != {expected_render_order}"


if __name__ == "__main__":
    pytest.main([__file__, '-v'])
