"""Mock plugins for testing the plugin system."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "software"))

from common.plugin_base import HUDContext, HUDPlugin, PluginConfig, PluginMetadata


class ProviderPlugin(HUDPlugin):
    """Simple plugin that provides data."""

    METADATA = PluginMetadata(
        name="Provider", version="1.0.0", author="Test", description="Provides test_data", provides=["test_data"]
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

    def initialize(self) -> bool:
        self.provide_data("test_data", {"value": 42})
        return True

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        return frame


class ConsumerPlugin(HUDPlugin):
    """Plugin with soft dependency on ProviderPlugin."""

    METADATA = PluginMetadata(
        name="Consumer", version="1.0.0", author="Test", description="Consumes test_data", consumes=["test_data"]
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

    def initialize(self) -> bool:
        return True

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        return frame


class HardDependentPlugin(HUDPlugin):
    """Plugin with hard dependency on ProviderPlugin."""

    METADATA = PluginMetadata(
        name="HardDependent",
        version="1.0.0",
        author="Test",
        description="Requires test_data",
        dependencies=["ProviderPlugin"],
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

    def initialize(self) -> bool:
        self.require_data("test_data", "ProviderPlugin must be loaded first")
        return True

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        return frame


class IndependentPlugin(HUDPlugin):
    """Plugin with no dependencies."""

    METADATA = PluginMetadata(name="Independent", version="1.0.0", author="Test", description="No dependencies")

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

    def initialize(self) -> bool:
        return True

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        return frame


class CircularA(HUDPlugin):
    """Plugin A in circular dependency A→B→A."""

    METADATA = PluginMetadata(
        name="CircularA", version="1.0.0", author="Test", description="Depends on CircularB", dependencies=["CircularB"]
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

    def initialize(self) -> bool:
        return True

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        return frame


class CircularB(HUDPlugin):
    """Plugin B in circular dependency A→B→A."""

    METADATA = PluginMetadata(
        name="CircularB", version="1.0.0", author="Test", description="Depends on CircularA", dependencies=["CircularA"]
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

    def initialize(self) -> bool:
        return True

    def update(self, delta_time: float):
        pass

    def render(self, frame: np.ndarray) -> np.ndarray:
        return frame
