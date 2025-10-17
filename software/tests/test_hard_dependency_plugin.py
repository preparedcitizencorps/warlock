#!/usr/bin/env python3

import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from common.plugin_base import HUDPlugin, HUDContext, PluginConfig, PluginMetadata


class TestConsumerPlugin(HUDPlugin):
    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self.metadata = PluginMetadata(
            name="Test Consumer",
            version="1.0.0",
            author="Test",
            description="Plugin that requires border padding",
            dependencies=['BorderPaddingPlugin'],
            provides=[]
        )

    def initialize(self) -> bool:
        try:
            border_padding = self.require_data('border_padding',
                "BorderPaddingPlugin must be loaded before TestConsumerPlugin")
            print(f"   ✓ TestConsumerPlugin found border_padding: {border_padding.get('padding_top')}px")
            return True
        except RuntimeError as e:
            print(f"   ✗ TestConsumerPlugin failed: {e}")
            return False

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        return frame

    def handle_key(self, key: int) -> bool:
        return False

    def cleanup(self):
        pass


if __name__ == "__main__":
    from helmet.hud.plugin_manager import PluginManager

    print("=" * 60)
    print("Testing HARD Dependency with Topological Sort")
    print("=" * 60)

    context = HUDContext(1280, 720)
    pm = PluginManager(context, plugin_dir=str(Path(__file__).parent.parent / "helmet" / "hud" / "plugins"))

    pm.discover_plugins()

    pm.plugin_classes['TestConsumerPlugin'] = TestConsumerPlugin

    print("\n1. Config order (wrong): TestConsumerPlugin → BorderPaddingPlugin")
    wrong_order = ['TestConsumerPlugin', 'BorderPaddingPlugin']

    try:
        correct_order = pm.topological_sort_plugins(wrong_order)
        print(f"   Corrected order:         {' → '.join(correct_order)}")

        if correct_order.index('BorderPaddingPlugin') < correct_order.index('TestConsumerPlugin'):
            print("   ✓ Dependencies loaded first!")
        else:
            print("   ✗ ERROR: Dependency order wrong!")

    except ValueError as e:
        print(f"   ✗ Error: {e}")

    print("\n2. Loading plugins in dependency order...")

    configs = [
        ('TestConsumerPlugin', PluginConfig()),
        ('BorderPaddingPlugin', PluginConfig())
    ]

    try:
        loaded = pm.load_plugins_with_dependencies(configs)
        print(f"   ✓ Successfully loaded {len(loaded)} plugins")

    except Exception as e:
        print(f"   ✗ Failed to load: {e}")

    print("\n" + "=" * 60)
    print("Hard Dependency Test Complete!")
    print("=" * 60)
