#!/usr/bin/env python3
"""
Project WARLOCK - HUD Plugin System
Phase 0: Modular HUD Architecture

A plugin-based HUD system for tactical AR displays.
All HUD components are plugins that can be easily added, removed, or modified.
"""

from .plugin_base import (
    HUDPlugin,
    HUDContext,
    PluginConfig,
    PluginMetadata,
    PluginPosition
)
from .plugin_manager import PluginManager
from .config_loader import load_config, create_plugin_config

__all__ = [
    'HUDPlugin',
    'HUDContext',
    'PluginConfig',
    'PluginMetadata',
    'PluginPosition',
    'PluginManager',
    'load_config',
    'create_plugin_config'
]

__version__ = '0.1.0'
