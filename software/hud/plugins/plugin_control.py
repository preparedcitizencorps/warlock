#!/usr/bin/env python3
"""Interactive overlay for managing plugins at runtime."""

import cv2
import numpy as np
import sys
import logging
import platform
from pathlib import Path
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hud.plugin_base import HUDPlugin, HUDContext, PluginConfig, PluginMetadata, PluginPosition

logger = logging.getLogger(__name__)


class PluginControlPanel(HUDPlugin):
    DEFAULT_AUTO_RELOAD_CHECK_INTERVAL = 1.0
    DEFAULT_VISIBILITY = False
    Z_INDEX_OVERLAY = 1000

    PANEL_MAX_WIDTH = 500
    PANEL_MAX_HEIGHT = 600
    PANEL_MARGIN = 40
    PANEL_BORDER_THICKNESS = 2
    PANEL_BACKGROUND_ALPHA = 0.9

    TITLE_Y_OFFSET = 30
    TITLE_FONT_SCALE = 0.7
    TITLE_THICKNESS = 2

    AUTO_RELOAD_STATUS_X_OFFSET = 150
    AUTO_RELOAD_FONT_SCALE = 0.4
    AUTO_RELOAD_THICKNESS = 1

    PLUGIN_LIST_Y_START = 60
    PLUGIN_LINE_HEIGHT = 40
    PLUGIN_NAME_X_OFFSET = 20
    PLUGIN_NAME_Y_OFFSET = 20
    PLUGIN_NAME_FONT_SCALE = 0.5
    PLUGIN_NAME_THICKNESS = 1

    STATUS_X_OFFSET = 280
    STATUS_FONT_SCALE = 0.4
    STATUS_THICKNESS = 1
    STATUS_ENABLED_X = 280
    STATUS_VISIBLE_X_OFFSET = 100

    SELECTION_BORDER_THICKNESS = 1
    SELECTION_PADDING_X = 10
    SELECTION_PADDING_Y = 5

    HELP_Y_OFFSET_FROM_BOTTOM = 100
    HELP_LINE_SPACING = 18
    HELP_TITLE_FONT_SCALE = 0.5
    HELP_TITLE_THICKNESS = 2
    HELP_TEXT_FONT_SCALE = 0.35
    HELP_TEXT_THICKNESS = 1

    METADATA = PluginMetadata(
        name="Plugin Control Panel",
        version="1.0.0",
        author="Project WARLOCK Team",
        description="Runtime plugin management interface"
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self._setup_arrow_keys()

        self.selected_index = 0
        self.auto_reload = False
        self.auto_reload_check_interval = self.DEFAULT_AUTO_RELOAD_CHECK_INTERVAL
        self.time_since_check = 0.0

        self.visible = self.DEFAULT_VISIBILITY

        self.bg_color = (20, 20, 20)
        self.text_color = (220, 220, 210)
        self.selected_color = (255, 200, 100)
        self.enabled_color = (100, 255, 100)
        self.disabled_color = (100, 100, 100)
        self.border_color = (180, 180, 170)

    def _setup_arrow_keys(self):
        system = platform.system()
        if system == 'Windows':
            self.KEY_UP_ARROW = 2490368
            self.KEY_DOWN_ARROW = 2621440
        else:
            self.KEY_UP_ARROW = 82
            self.KEY_DOWN_ARROW = 84

    def initialize(self) -> bool:
        self.config.position = PluginPosition.CENTER
        self.config.z_index = self.Z_INDEX_OVERLAY
        return True

    def _should_check_auto_reload(self) -> bool:
        return self.time_since_check >= self.auto_reload_check_interval

    def _get_plugin_manager_from_context(self):
        return self.context.state.get('plugin_manager')

    def _trigger_auto_reload(self):
        manager = self._get_plugin_manager_from_context()
        if manager is not None:
            reloaded_count = manager.auto_reload_modified()
            if reloaded_count > 0:
                print(f"Auto-reloaded {reloaded_count} plugin(s)")

    def update(self, delta_time: float):
        if self.auto_reload:
            self.time_since_check += delta_time
            if self._should_check_auto_reload():
                self.time_since_check = 0.0
                self._trigger_auto_reload()

    def _get_plugins_list(self) -> List[Dict]:
        manager = self._get_plugin_manager_from_context()
        if manager is not None:
            return manager.list_plugins()
        return []

    def _calculate_panel_dimensions(self, frame_width: int, frame_height: int) -> tuple:
        panel_width = min(self.PANEL_MAX_WIDTH, frame_width - self.PANEL_MARGIN)
        panel_height = min(self.PANEL_MAX_HEIGHT, frame_height - self.PANEL_MARGIN)
        panel_x = (frame_width - panel_width) // 2
        panel_y = (frame_height - panel_height) // 2
        return panel_width, panel_height, panel_x, panel_y

    def _draw_semi_transparent_background(self, frame: np.ndarray, panel_x: int,
                                         panel_y: int, panel_width: int, panel_height: int):
        overlay = frame.copy()
        cv2.rectangle(overlay, (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     self.bg_color, -1)
        cv2.addWeighted(overlay, self.PANEL_BACKGROUND_ALPHA, frame,
                       1.0 - self.PANEL_BACKGROUND_ALPHA, 0, frame)

    def _draw_panel_border(self, frame: np.ndarray, panel_x: int, panel_y: int,
                          panel_width: int, panel_height: int):
        cv2.rectangle(frame, (panel_x, panel_y),
                     (panel_x + panel_width, panel_y + panel_height),
                     self.border_color, self.PANEL_BORDER_THICKNESS)

    def _draw_title(self, frame: np.ndarray, panel_x: int, panel_y: int):
        title = "PLUGIN CONTROL PANEL"
        cv2.putText(frame, title, (panel_x + self.PLUGIN_NAME_X_OFFSET,
                                  panel_y + self.TITLE_Y_OFFSET),
                   cv2.FONT_HERSHEY_SIMPLEX, self.TITLE_FONT_SCALE,
                   self.text_color, self.TITLE_THICKNESS)

    def _format_auto_reload_status(self) -> str:
        return f"Auto-Reload: {'ON' if self.auto_reload else 'OFF'}"

    def _get_auto_reload_status_color(self) -> tuple:
        return self.selected_color if self.auto_reload else self.text_color

    def _draw_auto_reload_status(self, frame: np.ndarray, panel_x: int,
                                panel_y: int, panel_width: int):
        status_text = self._format_auto_reload_status()
        status_color = self._get_auto_reload_status_color()
        cv2.putText(frame, status_text,
                   (panel_x + panel_width - self.AUTO_RELOAD_STATUS_X_OFFSET,
                    panel_y + self.TITLE_Y_OFFSET),
                   cv2.FONT_HERSHEY_SIMPLEX, self.AUTO_RELOAD_FONT_SCALE,
                   status_color, self.AUTO_RELOAD_THICKNESS)

    def _is_plugin_self(self, plugin: Dict) -> bool:
        return plugin['name'] == self.metadata.name

    def _ensure_valid_selection_index(self, plugin_count: int):
        if plugin_count <= 0:
            self.selected_index = -1
        else:
            self.selected_index = max(0, min(self.selected_index, plugin_count - 1))

    def _is_plugin_selected(self, plugin_index: int) -> bool:
        return plugin_index == self.selected_index

    def _draw_selection_highlight(self, frame: np.ndarray, panel_x: int,
                                  panel_width: int, y_offset: int):
        cv2.rectangle(frame,
                     (panel_x + self.SELECTION_PADDING_X,
                      y_offset - self.SELECTION_PADDING_Y),
                     (panel_x + panel_width - self.SELECTION_PADDING_X,
                      y_offset + self.PLUGIN_LINE_HEIGHT - self.SELECTION_PADDING_Y),
                     self.selected_color, self.SELECTION_BORDER_THICKNESS)

    def _get_plugin_name_color(self, is_selected: bool) -> tuple:
        return self.text_color if is_selected else self.disabled_color

    def _draw_plugin_name(self, frame: np.ndarray, plugin_name: str, panel_x: int,
                         y_offset: int, name_color: tuple):
        cv2.putText(frame, plugin_name,
                   (panel_x + self.PLUGIN_NAME_X_OFFSET,
                    y_offset + self.PLUGIN_NAME_Y_OFFSET),
                   cv2.FONT_HERSHEY_SIMPLEX, self.PLUGIN_NAME_FONT_SCALE,
                   name_color, self.PLUGIN_NAME_THICKNESS)

    def _format_enabled_status(self, is_enabled: bool) -> str:
        return "ENABLED" if is_enabled else "DISABLED"

    def _get_enabled_status_color(self, is_enabled: bool) -> tuple:
        return self.enabled_color if is_enabled else self.disabled_color

    def _draw_enabled_status(self, frame: np.ndarray, plugin: Dict, panel_x: int, y_offset: int):
        status_text = self._format_enabled_status(plugin['enabled'])
        status_color = self._get_enabled_status_color(plugin['enabled'])
        cv2.putText(frame, status_text,
                   (panel_x + self.STATUS_ENABLED_X,
                    y_offset + self.PLUGIN_NAME_Y_OFFSET),
                   cv2.FONT_HERSHEY_SIMPLEX, self.STATUS_FONT_SCALE,
                   status_color, self.STATUS_THICKNESS)

    def _format_visible_status(self, is_visible: bool) -> str:
        return "VISIBLE" if is_visible else "HIDDEN"

    def _get_visible_status_color(self, is_visible: bool) -> tuple:
        return self.enabled_color if is_visible else self.disabled_color

    def _draw_visible_status(self, frame: np.ndarray, plugin: Dict, panel_x: int, y_offset: int):
        status_text = self._format_visible_status(plugin['visible'])
        status_color = self._get_visible_status_color(plugin['visible'])
        cv2.putText(frame, status_text,
                   (panel_x + self.STATUS_ENABLED_X + self.STATUS_VISIBLE_X_OFFSET,
                    y_offset + self.PLUGIN_NAME_Y_OFFSET),
                   cv2.FONT_HERSHEY_SIMPLEX, self.STATUS_FONT_SCALE,
                   status_color, self.STATUS_THICKNESS)

    def _draw_plugin_entry(self, frame: np.ndarray, plugin: Dict, plugin_index: int,
                          panel_x: int, panel_width: int, y_offset: int):
        if self._is_plugin_self(plugin):
            return

        if self._is_plugin_selected(plugin_index):
            self._draw_selection_highlight(frame, panel_x, panel_width, y_offset)

        name_color = self._get_plugin_name_color(self._is_plugin_selected(plugin_index))
        self._draw_plugin_name(frame, plugin['name'], panel_x, y_offset, name_color)
        self._draw_enabled_status(frame, plugin, panel_x, y_offset)
        self._draw_visible_status(frame, plugin, panel_x, y_offset)

    def _draw_plugins_list(self, frame: np.ndarray, plugins: List[Dict],
                          panel_x: int, panel_y: int, panel_width: int):
        if not plugins:
            cv2.putText(frame, "No plugins loaded",
                       (panel_x + self.PLUGIN_NAME_X_OFFSET,
                        panel_y + self.PLUGIN_LIST_Y_START + 10),
                       cv2.FONT_HERSHEY_SIMPLEX, self.PLUGIN_NAME_FONT_SCALE,
                       self.text_color, self.PLUGIN_NAME_THICKNESS)
            return

        self._ensure_valid_selection_index(len(plugins))

        y_offset = panel_y + self.PLUGIN_LIST_Y_START

        for plugin_index, plugin in enumerate(plugins):
            self._draw_plugin_entry(frame, plugin, plugin_index, panel_x,
                                   panel_width, y_offset)
            y_offset += self.PLUGIN_LINE_HEIGHT

    def _get_help_texts(self) -> List[str]:
        return [
            "Controls:",
            "P - Toggle Panel   Up/Down - Select   E - Enable/Disable",
            "V - Show/Hide   R - Reload Plugin   A - Auto-Reload Toggle"
        ]

    def _get_help_text_font_scale(self, text_index: int) -> float:
        return self.HELP_TITLE_FONT_SCALE if text_index == 0 else self.HELP_TEXT_FONT_SCALE

    def _get_help_text_thickness(self, text_index: int) -> int:
        return self.HELP_TITLE_THICKNESS if text_index == 0 else self.HELP_TEXT_THICKNESS

    def _draw_help_section(self, frame: np.ndarray, panel_x: int, panel_y: int, panel_height: int):
        help_y = panel_y + panel_height - self.HELP_Y_OFFSET_FROM_BOTTOM
        help_texts = self._get_help_texts()

        for text_index, text in enumerate(help_texts):
            font_scale = self._get_help_text_font_scale(text_index)
            thickness = self._get_help_text_thickness(text_index)
            cv2.putText(frame, text,
                       (panel_x + self.PLUGIN_NAME_X_OFFSET,
                        help_y + text_index * self.HELP_LINE_SPACING),
                       cv2.FONT_HERSHEY_SIMPLEX, font_scale,
                       self.border_color, thickness)

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible:
            return frame

        frame_height, frame_width = frame.shape[:2]

        panel_width, panel_height, panel_x, panel_y = self._calculate_panel_dimensions(
            frame_width, frame_height)

        self._draw_semi_transparent_background(frame, panel_x, panel_y,
                                               panel_width, panel_height)
        self._draw_panel_border(frame, panel_x, panel_y, panel_width, panel_height)
        self._draw_title(frame, panel_x, panel_y)
        self._draw_auto_reload_status(frame, panel_x, panel_y, panel_width)

        plugins = self._get_plugins_list()
        self._draw_plugins_list(frame, plugins, panel_x, panel_y, panel_width)
        self._draw_help_section(frame, panel_x, panel_y, panel_height)

        return frame

    def _toggle_panel_visibility(self):
        self.toggle_visibility()
        print(f"Plugin Control Panel: {'ON' if self.visible else 'OFF'}")

    def _handle_navigation_up(self, plugin_count: int):
        if plugin_count <= 0:
            return
        self.selected_index = (self.selected_index - 1) % plugin_count

    def _handle_navigation_down(self, plugin_count: int):
        if plugin_count <= 0:
            return
        self.selected_index = (self.selected_index + 1) % plugin_count

    def _is_navigation_key(self, key: int) -> bool:
        return key in [self.KEY_UP_ARROW, self.KEY_DOWN_ARROW, ord('k'), ord('j')]

    def _handle_navigation(self, key: int, plugin_count: int) -> bool:
        if key == self.KEY_UP_ARROW or key == ord('k'):
            self._handle_navigation_up(plugin_count)
            return True
        elif key == self.KEY_DOWN_ARROW or key == ord('j'):
            self._handle_navigation_down(plugin_count)
            return True
        return False

    def _get_selected_plugin(self, plugins: List[Dict]) -> Optional[Dict]:
        if not plugins or self.selected_index >= len(plugins):
            return None

        selected = plugins[self.selected_index]
        if self._is_plugin_self(selected):
            return None

        return selected

    def _toggle_plugin_enabled(self, manager, plugin_name: str):
        try:
            plugin = manager.get_plugin(plugin_name)
            if plugin:
                if plugin.metadata.enabled:
                    manager.disable_plugin(plugin_name)
                else:
                    manager.enable_plugin(plugin_name)
        except Exception as e:
            logger.error(f"Failed to toggle plugin '{plugin_name}': {e}")

    def _toggle_plugin_visibility(self, manager, plugin_name: str):
        try:
            plugin = manager.get_plugin(plugin_name)
            if plugin:
                plugin.toggle_visibility()
                print(f"{plugin_name}: {'VISIBLE' if plugin.visible else 'HIDDEN'}")
        except Exception as e:
            logger.error(f"Failed to toggle visibility for plugin '{plugin_name}': {e}")

    def _reload_plugin(self, manager, plugin_name: str):
        try:
            print(f"Reloading {plugin_name}...")
            manager.reload_plugin(plugin_name)
        except Exception as e:
            logger.error(f"Failed to reload plugin '{plugin_name}': {e}")

    def _toggle_auto_reload(self):
        self.auto_reload = not self.auto_reload
        print(f"Auto-reload: {'ON' if self.auto_reload else 'OFF'}")

    def _handle_plugin_action(self, key: int, manager, plugin_name: str) -> bool:
        if key == ord('e'):
            self._toggle_plugin_enabled(manager, plugin_name)
            return True
        elif key == ord('v'):
            self._toggle_plugin_visibility(manager, plugin_name)
            return True
        elif key == ord('r'):
            self._reload_plugin(manager, plugin_name)
            return True
        elif key == ord('a'):
            self._toggle_auto_reload()
            return True
        return False

    def handle_key(self, key: int) -> bool:
        if key == ord('p'):
            self._toggle_panel_visibility()
            return True

        if not self.visible:
            return False

        plugins = self._get_plugins_list()
        manager = self._get_plugin_manager_from_context()

        if not plugins or not manager:
            return False

        if self._is_navigation_key(key):
            return self._handle_navigation(key, len(plugins))

        selected_plugin = self._get_selected_plugin(plugins)
        if selected_plugin is None:
            return False

        return self._handle_plugin_action(key, manager, selected_plugin['name'])
