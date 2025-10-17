#!/usr/bin/env python3
"""Centralized input management for keyboard, hardware buttons, and other input devices."""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union


class InputType(Enum):
    KEYBOARD = "keyboard"
    HARDWARE_BUTTON = "hardware_button"
    GPIO = "gpio"
    SERIAL = "serial"


@dataclass
class InputBinding:
    key: str
    description: str
    category: str
    handler: Optional[Callable[..., Any]] = None
    input_type: InputType = InputType.KEYBOARD
    enabled: bool = True


@dataclass
class InputCategory:
    name: str
    priority: int
    bindings: List[InputBinding]


class InputManager:
    """
    Centralized input management system.

    Handles keyboard input, hardware buttons (PTT, etc.), and future input devices.
    Provides consistent interface for registering, mapping, and dispatching inputs.
    """

    def __init__(self):
        self.bindings: Dict[Union[str, int], InputBinding] = {}
        self.categories: Dict[str, InputCategory] = {}
        self._initialize_categories()

    def _initialize_categories(self):
        category_definitions = [
            ("system", 0),
            ("yolo", 10),
            ("exposure", 20),
            ("display", 30),
            ("movement", 40),
            ("hardware", 50),
        ]

        for name, priority in category_definitions:
            self.categories[name] = InputCategory(name=name, priority=priority, bindings=[])

    def register_keybind(
        self,
        key: str,
        description: str,
        category: str,
        handler: Optional[Callable[..., Any]] = None,
        enabled: bool = True,
    ) -> None:
        """
        Register a keyboard binding.

        Args:
            key: Key identifier (e.g., 'q', 'h', 'esc')
            description: Human-readable description
            category: Category name for grouping
            handler: Optional callback function
            enabled: Whether binding is currently active
        """
        if key in self.bindings:
            old_binding = self.bindings[key]
            old_category = old_binding.category
            if old_category in self.categories:
                try:
                    self.categories[old_category].bindings.remove(old_binding)
                except ValueError:
                    pass

        binding = InputBinding(
            key=key,
            description=description,
            category=category,
            handler=handler,
            input_type=InputType.KEYBOARD,
            enabled=enabled,
        )

        self.bindings[key] = binding

        if category not in self.categories:
            self.categories[category] = InputCategory(name=category, priority=100, bindings=[])

        self.categories[category].bindings.append(binding)

    def register_hardware_input(
        self,
        identifier: str,
        description: str,
        category: str,
        input_type: InputType,
        handler: Optional[Callable] = None,
    ) -> None:
        """
        Register a hardware input (GPIO pin, serial command, etc.).

        Args:
            identifier: Unique identifier for the input
            description: Human-readable description
            category: Category name for grouping
            input_type: Type of hardware input
            handler: Callback function for input events
        """
        if identifier in self.bindings:
            old_binding = self.bindings[identifier]
            old_category = old_binding.category
            if old_category in self.categories:
                try:
                    self.categories[old_category].bindings.remove(old_binding)
                except ValueError:
                    pass

        binding = InputBinding(
            key=identifier,
            description=description,
            category=category,
            handler=handler,
            input_type=input_type,
            enabled=True,
        )

        self.bindings[identifier] = binding

        if category not in self.categories:
            self.categories[category] = InputCategory(name=category, priority=100, bindings=[])

        self.categories[category].bindings.append(binding)

    def handle_key(self, key: int) -> bool:
        """
        Handle keyboard input and dispatch to registered handler.

        Args:
            key: OpenCV key code

        Returns:
            True if key was handled, False otherwise
        """
        if key in self.bindings:
            binding = self.bindings[key]
            if binding.enabled and binding.handler:
                return binding.handler(key)

        key_char = chr(key) if 0 <= key <= 127 else None
        if key_char and key_char in self.bindings:
            binding = self.bindings[key_char]
            if binding.enabled and binding.handler:
                return binding.handler(key)

        return False

    def get_keybinds_by_category(self) -> List[tuple]:
        """
        Get all keyboard bindings organized by category.

        Returns:
            List of (category_name, bindings) tuples sorted by priority
        """
        sorted_categories = sorted(self.categories.values(), key=lambda c: c.priority)

        result = []
        for category in sorted_categories:
            keyboard_bindings = [b for b in category.bindings if b.input_type == InputType.KEYBOARD and b.enabled]
            if keyboard_bindings:
                result.append((category.name, keyboard_bindings))

        return result

    def get_hardware_inputs(self) -> List[InputBinding]:
        """Get all registered hardware input bindings."""
        return [b for b in self.bindings.values() if b.input_type != InputType.KEYBOARD and b.enabled]

    def enable_binding(self, key: str) -> bool:
        """Enable a binding by key."""
        if key in self.bindings:
            self.bindings[key].enabled = True
            return True
        return False

    def disable_binding(self, key: str) -> bool:
        """Disable a binding by key."""
        if key in self.bindings:
            self.bindings[key].enabled = False
            return True
        return False

    def get_binding(self, key: str) -> Optional[InputBinding]:
        """Get binding by key."""
        return self.bindings.get(key)

    def update_handler(self, key: str, handler: Callable[..., Any]) -> bool:
        """Update handler for existing binding."""
        if key in self.bindings:
            self.bindings[key].handler = handler
            return True
        return False

    def load_from_config(self, config: dict) -> None:
        """
        Load keybind configuration from dictionary.

        Expected format:
        {
            'keybinds': {
                'quit': 'q',
                'help': 'h',
                ...
            }
        }
        """
        keybinds_config = config.get("keybinds", {})

        for action, key_value in keybinds_config.items():
            if isinstance(key_value, dict):
                key = key_value.get("key")
                enabled = key_value.get("enabled", True)
                if key and key in self.bindings:
                    self.bindings[key].enabled = enabled
