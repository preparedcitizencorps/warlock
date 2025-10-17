"""Tests for input manager essentials.

Tests verify core keybind functionality without being fragile to implementation.
"""

import pytest
from common.input_manager import InputManager


class TestKeybindRegistration:
    """Test that keybinds can be registered and managed."""

    def test_can_register_keybind(self):
        """Basic keybind registration must work."""
        manager = InputManager()

        manager.register_keybind('q', 'Quit', 'system')

        binding = manager.get_binding('q')
        assert binding is not None

    def test_can_register_multiple_keybinds(self):
        """Should support multiple keybinds."""
        manager = InputManager()

        manager.register_keybind('q', 'Quit', 'system')
        manager.register_keybind('h', 'Help', 'system')

        assert manager.get_binding('q') is not None
        assert manager.get_binding('h') is not None

    def test_keybind_has_description(self):
        """Keybinds should have human-readable descriptions."""
        manager = InputManager()

        manager.register_keybind('q', 'Quit application', 'system')
        binding = manager.get_binding('q')

        assert binding is not None
        assert binding.description == 'Quit application'

    def test_keybind_has_category(self):
        """Keybinds should be categorized for UI display."""
        manager = InputManager()

        manager.register_keybind('y', 'Toggle YOLO', 'yolo')
        binding = manager.get_binding('y')

        assert binding is not None
        assert binding.category == 'yolo'


class TestKeybindConflicts:
    """Test that keybind conflicts are handled."""

    def test_registering_same_key_twice_updates_binding(self):
        """Re-registering a key should update, not error."""
        manager = InputManager()

        manager.register_keybind('q', 'First action', 'system')
        manager.register_keybind('q', 'Second action', 'system')

        binding = manager.get_binding('q')
        assert binding is not None
        assert binding.description == 'Second action'

    def test_can_enable_and_disable_bindings(self):
        """Should be able to enable/disable bindings."""
        manager = InputManager()

        manager.register_keybind('q', 'Quit', 'system')

        assert manager.disable_binding('q') is True
        assert manager.get_binding('q').enabled is False

        assert manager.enable_binding('q') is True
        assert manager.get_binding('q').enabled is True


class TestKeybindLookup:
    """Test that keybinds can be queried."""

    def test_get_binding_returns_none_for_unregistered(self):
        """Unregistered keys should return None, not error."""
        manager = InputManager()

        binding = manager.get_binding('z')

        assert binding is None

    def test_can_check_if_key_is_registered(self):
        """Should be able to check if a key has a binding."""
        manager = InputManager()

        manager.register_keybind('q', 'Quit', 'system')

        assert manager.get_binding('q') is not None
        assert manager.get_binding('z') is None


class TestCategoryManagement:
    """Test keybind category organization."""

    def test_can_get_keybinds_by_category(self):
        """Should be able to organize keybinds by category."""
        manager = InputManager()

        manager.register_keybind('q', 'Quit', 'system')
        manager.register_keybind('h', 'Help', 'system')
        manager.register_keybind('y', 'YOLO', 'yolo')

        all_categories = manager.get_keybinds_by_category()

        assert len(all_categories) > 0
        assert isinstance(all_categories, list)

    def test_categories_are_initialized(self):
        """Manager should have predefined categories."""
        manager = InputManager()

        assert len(manager.categories) > 0
        assert 'system' in manager.categories
