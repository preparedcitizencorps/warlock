"""Tests for plugin dependency resolution and topological sorting."""

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "software"))

from common.plugin_base import HUDContext
from helmet.hud.plugin_manager import PluginManager
from common.plugin_base import PluginConfig
from tests.fixtures.mock_plugins import (
    ProviderPlugin, ConsumerPlugin, HardDependentPlugin,
    IndependentPlugin, CircularA, CircularB
)


class TestTopologicalSort:
    """Test dependency-based plugin load ordering."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)
        self.manager = PluginManager(self.context, plugin_dir="tests/fixtures")

    def test_simple_chain_dependency(self):
        """Provider → Consumer should load as [Provider, Consumer]."""
        self.manager.plugin_classes = {
            'ProviderPlugin': ProviderPlugin,
            'ConsumerPlugin': ConsumerPlugin
        }

        order = self.manager.topological_sort_plugins(['ConsumerPlugin', 'ProviderPlugin'])

        provider_idx = order.index('ProviderPlugin')
        consumer_idx = order.index('ConsumerPlugin')
        assert provider_idx < consumer_idx, "Provider must load before Consumer"

    def test_hard_dependency_ordering(self):
        """Hard dependency should enforce load order."""
        self.manager.plugin_classes = {
            'ProviderPlugin': ProviderPlugin,
            'HardDependentPlugin': HardDependentPlugin
        }

        order = self.manager.topological_sort_plugins(['HardDependentPlugin', 'ProviderPlugin'])

        provider_idx = order.index('ProviderPlugin')
        dependent_idx = order.index('HardDependentPlugin')
        assert provider_idx < dependent_idx

    def test_independent_plugins_any_order(self):
        """Plugins with no dependencies can load in any order."""
        self.manager.plugin_classes = {
            'IndependentPlugin': IndependentPlugin,
            'ProviderPlugin': ProviderPlugin
        }

        order = self.manager.topological_sort_plugins(['IndependentPlugin', 'ProviderPlugin'])

        assert len(order) == 2
        assert 'IndependentPlugin' in order
        assert 'ProviderPlugin' in order

    def test_circular_dependency_detected(self):
        """Circular dependencies should raise ValueError."""
        self.manager.plugin_classes = {
            'CircularA': CircularA,
            'CircularB': CircularB
        }

        with pytest.raises(ValueError, match="Circular dependency"):
            self.manager.topological_sort_plugins(['CircularA', 'CircularB'])

    def test_diamond_dependency(self):
        """Diamond: A→B, A→C, B→D, C→D should resolve correctly."""
        from common.plugin_base import PluginMetadata

        class A(ProviderPlugin):
            METADATA = PluginMetadata(
                name="A",
                version="1.0.0",
                author="Test",
                description="Test plugin A",
                provides=['a_data']
            )

        class B(ConsumerPlugin):
            METADATA = PluginMetadata(
                name="B",
                version="1.0.0",
                author="Test",
                description="Test plugin B",
                consumes=['a_data'],
                provides=['b_data']
            )

        class C(ConsumerPlugin):
            METADATA = PluginMetadata(
                name="C",
                version="1.0.0",
                author="Test",
                description="Test plugin C",
                consumes=['a_data'],
                provides=['c_data']
            )

        class D(ConsumerPlugin):
            METADATA = PluginMetadata(
                name="D",
                version="1.0.0",
                author="Test",
                description="Test plugin D",
                consumes=['b_data', 'c_data']
            )

        self.manager.plugin_classes = {'A': A, 'B': B, 'C': C, 'D': D}

        order = self.manager.topological_sort_plugins(['D', 'C', 'B', 'A'])

        a_idx = order.index('A')
        b_idx = order.index('B')
        c_idx = order.index('C')
        d_idx = order.index('D')

        assert a_idx < b_idx, "A must load before B"
        assert a_idx < c_idx, "A must load before C"
        assert b_idx < d_idx, "B must load before D"
        assert c_idx < d_idx, "C must load before D"


class TestSoftDependencyInference:
    """Test that soft dependencies are inferred from provides/consumes."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)
        self.manager = PluginManager(self.context, plugin_dir="tests/fixtures")

    def test_soft_dependency_inferred_from_consumes(self):
        """Plugin consuming data should load after provider."""
        self.manager.plugin_classes = {
            'ProviderPlugin': ProviderPlugin,
            'ConsumerPlugin': ConsumerPlugin
        }

        deps = self.manager._get_plugin_dependencies('ConsumerPlugin')

        assert 'ProviderPlugin' in deps, "Should infer dependency from consumes field"

    def test_no_dependency_if_no_match(self):
        """Plugin consuming non-existent data has no inferred dependencies."""
        from common.plugin_base import PluginMetadata

        class Orphan(ConsumerPlugin):
            METADATA = PluginMetadata(
                name="Orphan",
                version="1.0.0",
                author="Test",
                description="Orphan plugin",
                consumes=['nonexistent_data']
            )

        self.manager.plugin_classes = {
            'ProviderPlugin': ProviderPlugin,
            'Orphan': Orphan
        }

        deps = self.manager._get_plugin_dependencies('Orphan')

        assert 'ProviderPlugin' not in deps


class TestDependencyValidation:
    """Test dependency checking and warnings."""

    def setup_method(self):
        self.context = HUDContext(1280, 720)
        self.manager = PluginManager(self.context, plugin_dir="tests/fixtures")

    def test_missing_dependency_detected(self):
        """Check dependencies should detect missing plugins."""
        satisfied, missing = self.manager.check_dependencies(HardDependentPlugin)

        assert not satisfied
        assert 'ProviderPlugin' in missing

    def test_satisfied_dependency(self):
        """Check dependencies should pass when dependencies loaded."""
        provider = self.manager.load_plugin(ProviderPlugin, PluginConfig())

        satisfied, missing = self.manager.check_dependencies(HardDependentPlugin)

        assert satisfied
        assert len(missing) == 0
