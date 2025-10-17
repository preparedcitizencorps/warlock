#!/usr/bin/env python3

import yaml
from pathlib import Path
from typing import Dict, List, Any

from .plugin_base import PluginConfig, PluginMetadata


def load_config(config_path: str = "hud_config.yaml") -> Dict[str, Any]:
    config_file = Path(config_path)

    if not config_file.exists():
        print(f"Warning: Config file {config_path} not found, using defaults")
        return {'plugins': []}

    try:
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        return config if config else {'plugins': []}
    except Exception as e:
        print(f"Error loading config file {config_path}: {e}")
        return {'plugins': []}


def create_plugin_config(plugin_data: Dict[str, Any]) -> PluginConfig:
    config = PluginConfig()

    # First merge settings
    if 'settings' in plugin_data and plugin_data['settings'] is not None:
        config.settings.update(plugin_data['settings'])

    # Then apply top-level overrides (these take precedence)
    config.settings['visible'] = plugin_data.get('visible', True)

    if 'z_index' in plugin_data:
        config.z_index = plugin_data['z_index']

    return config
