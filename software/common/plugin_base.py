#!/usr/bin/env python3

import cv2
import numpy as np
from typing import Dict, Any, Optional, Tuple, List
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from collections import deque


class PluginPosition(Enum):
    TOP_LEFT = "top_left"
    TOP_CENTER = "top_center"
    TOP_RIGHT = "top_right"
    CENTER_LEFT = "center_left"
    CENTER = "center"
    CENTER_RIGHT = "center_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_CENTER = "bottom_center"
    BOTTOM_RIGHT = "bottom_right"
    CUSTOM = "custom"


@dataclass
class PluginMetadata:
    name: str
    version: str
    author: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    provides: List[str] = field(default_factory=list)
    consumes: List[str] = field(default_factory=list)
    enabled: bool = True


@dataclass
class PluginConfig:
    position: PluginPosition = PluginPosition.CUSTOM
    x: int = 0
    y: int = 0
    width: Optional[int] = None
    height: Optional[int] = None
    z_index: int = 0
    settings: Dict[str, Any] = field(default_factory=dict)


class HUDContext:
    MAX_EVENTS = 1000

    def __init__(self, frame_width: int, frame_height: int):
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.state: Dict[str, Any] = {}
        self.events = deque(maxlen=self.MAX_EVENTS)

    def emit_event(self, event_type: str, data: Any = None):
        self.events.append({
            'type': event_type,
            'data': data
        })

    def get_events(self, event_type: Optional[str] = None) -> List[Dict[str, Any]]:
        if event_type is None:
            return list(self.events)
        return [e for e in self.events if e['type'] == event_type]

    def clear_events(self):
        self.events.clear()


class HUDPlugin(ABC):
    DEFAULT_EDGE_INSET = 10
    METADATA: PluginMetadata

    def __init__(self, context: HUDContext, config: PluginConfig):
        self.context = context
        self.config = config
        self.visible = True
        self.initialized = False

        if not hasattr(self.__class__, 'METADATA') or self.__class__.METADATA is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} must define METADATA as a class-level attribute"
            )

        self.metadata = self.__class__.METADATA

    @abstractmethod
    def initialize(self) -> bool:
        pass

    @abstractmethod
    def update(self, delta_time: float):
        pass

    @abstractmethod
    def render(self, frame: np.ndarray) -> np.ndarray:
        pass

    def cleanup(self):
        pass

    def handle_event(self, event: Dict[str, Any]):
        pass

    def handle_key(self, key: int) -> bool:
        return False

    def get_position(self) -> Tuple[int, int]:
        x, y = self.config.x, self.config.y

        if self.config.position == PluginPosition.TOP_LEFT:
            x += self.DEFAULT_EDGE_INSET
            y += self.DEFAULT_EDGE_INSET
        elif self.config.position == PluginPosition.TOP_CENTER:
            x += self.context.frame_width // 2
            y += self.DEFAULT_EDGE_INSET
        elif self.config.position == PluginPosition.TOP_RIGHT:
            x += self.context.frame_width - self.DEFAULT_EDGE_INSET
            y += self.DEFAULT_EDGE_INSET
        elif self.config.position == PluginPosition.CENTER_LEFT:
            x += self.DEFAULT_EDGE_INSET
            y += self.context.frame_height // 2
        elif self.config.position == PluginPosition.CENTER:
            x += self.context.frame_width // 2
            y += self.context.frame_height // 2
        elif self.config.position == PluginPosition.CENTER_RIGHT:
            x += self.context.frame_width - self.DEFAULT_EDGE_INSET
            y += self.context.frame_height // 2
        elif self.config.position == PluginPosition.BOTTOM_LEFT:
            x += self.DEFAULT_EDGE_INSET
            y += self.context.frame_height - self.DEFAULT_EDGE_INSET
        elif self.config.position == PluginPosition.BOTTOM_CENTER:
            x += self.context.frame_width // 2
            y += self.context.frame_height - self.DEFAULT_EDGE_INSET
        elif self.config.position == PluginPosition.BOTTOM_RIGHT:
            x += self.context.frame_width - self.DEFAULT_EDGE_INSET
            y += self.context.frame_height - self.DEFAULT_EDGE_INSET

        return x, y

    def toggle_visibility(self):
        self.visible = not self.visible

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.config.settings.get(key, default)

    def require_data(self, key: str, error_msg: Optional[str] = None) -> Any:
        if key not in self.context.state:
            if error_msg is None:
                error_msg = (f"Plugin '{self.metadata.name}' requires '{key}' in context. "
                           f"Make sure the providing plugin is loaded first and has lower z_index.")
            raise RuntimeError(error_msg)
        return self.context.state[key]

    def get_data(self, key: str, default: Any = None) -> Any:
        return self.context.state.get(key, default)

    def provide_data(self, key: str, value: Any):
        self.context.state[key] = value
