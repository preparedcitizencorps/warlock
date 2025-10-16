#!/usr/bin/env python3
"""YOLO-based object detection with friend/foe classification."""

import cv2
import numpy as np
import sys
import random
from pathlib import Path
from typing import Dict, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from hud.plugin_base import HUDPlugin, HUDContext, PluginConfig, PluginMetadata

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("Warning: ultralytics not available for YOLO detection")


class YOLODetectionPlugin(HUDPlugin):
    DEFAULT_MODEL_PATH = 'yolo11n.pt'
    DEFAULT_CONFIDENCE_THRESHOLD = 0.25
    DEFAULT_FRIEND_COLOR = (255, 200, 100)
    DEFAULT_FOE_COLOR = (0, 100, 255)
    PERSON_CLASS_ID = 0
    BOUNDING_BOX_THICKNESS = 2
    LABEL_FONT_SCALE = 0.4
    LABEL_THICKNESS = 1
    LABEL_X_OFFSET = 4
    LABEL_Y_OFFSET = 14

    METADATA = PluginMetadata(
        name="YOLO Detection",
        version="1.0.0",
        author="Project WARLOCK Team",
        description="YOLO object detection with friend/foe identification and tracking",
        provides=['yolo_detections']
    )

    def __init__(self, context: HUDContext, config: PluginConfig):
        super().__init__(context, config)

        self.model = None
        self.model_loaded = False

        self.model_path = config.settings.get('model_path', self.DEFAULT_MODEL_PATH)
        self.confidence_threshold = config.settings.get('confidence_threshold',
                                                       self.DEFAULT_CONFIDENCE_THRESHOLD)

        self.friend_color = tuple(config.settings.get('friend_color',
                                                      list(self.DEFAULT_FRIEND_COLOR)))
        self.foe_color = tuple(config.settings.get('foe_color',
                                                   list(self.DEFAULT_FOE_COLOR)))

        self.tracked_identities: Dict[int, Tuple[int, int, int]] = {}

    def initialize(self) -> bool:
        if not YOLO_AVAILABLE:
            print("YOLO Detection Plugin: ultralytics not available")
            return False

        try:
            print(f"Loading YOLO model: {self.model_path}")
            self.model = YOLO(self.model_path)
            self.model.to('cpu')
            self.model_loaded = True
            print("YOLO model loaded successfully (CPU mode)")
            return True
        except Exception as e:
            print(f"Failed to load YOLO model: {e}")
            return False

    def update(self, delta_time: float):
        pass

    def _assign_friend_or_foe_color(self, track_id: int) -> Tuple[int, int, int]:
        if track_id not in self.tracked_identities:
            self.tracked_identities[track_id] = random.choice([
                self.friend_color,
                self.foe_color
            ])
        return self.tracked_identities[track_id]

    def _get_status_label(self, color: Tuple[int, int, int]) -> str:
        return "FRIEND" if color == self.friend_color else "FOE"

    def _format_detection_label(self, status: str, track_id: int, confidence: float) -> str:
        return f"{status} #{track_id} {confidence:.2f}"

    def _draw_bounding_box(self, frame: np.ndarray, x1: int, y1: int,
                          x2: int, y2: int, color: Tuple[int, int, int]):
        cv2.rectangle(frame, (x1, y1), (x2, y2), color,
                     self.BOUNDING_BOX_THICKNESS, cv2.LINE_AA)

    def _draw_detection_label(self, frame: np.ndarray, label: str, x1: int, y1: int,
                             color: Tuple[int, int, int]):
        cv2.putText(frame, label, (x1 + self.LABEL_X_OFFSET, y1 + self.LABEL_Y_OFFSET),
                   cv2.FONT_HERSHEY_SIMPLEX, self.LABEL_FONT_SCALE,
                   color, self.LABEL_THICKNESS, cv2.LINE_AA)

    def _process_detection(self, frame: np.ndarray, x1: int, y1: int,
                          x2: int, y2: int, track_id: int, confidence: float):
        box_color = self._assign_friend_or_foe_color(track_id)
        status = self._get_status_label(box_color)
        label = self._format_detection_label(status, track_id, confidence)

        self._draw_bounding_box(frame, x1, y1, x2, y2, box_color)
        self._draw_detection_label(frame, label, x1, y1, box_color)

    def _meets_confidence_threshold(self, confidence: float) -> bool:
        return confidence >= self.confidence_threshold

    def _run_yolo_tracking(self, frame: np.ndarray):
        return self.model.track(frame, persist=True, verbose=False,
                               device='cpu', classes=[self.PERSON_CLASS_ID])

    def _process_all_detections(self, frame: np.ndarray, results):
        detections_list = []

        if results[0].boxes.id is None:
            return

        for box_data in zip(results[0].boxes.xyxy, results[0].boxes.id, results[0].boxes.conf):
            bbox, track_id, confidence = box_data
            x1, y1, x2, y2 = map(int, bbox)
            track_id = int(track_id)
            confidence = float(confidence)

            if not self._meets_confidence_threshold(confidence):
                continue

            self._process_detection(frame, x1, y1, x2, y2, track_id, confidence)

            detections_list.append({
                'bbox': (x1, y1, x2, y2),
                'track_id': track_id,
                'confidence': confidence,
                'identity': self._get_status_label(self._assign_friend_or_foe_color(track_id))
            })

        self.provide_data('yolo_detections', detections_list)

    def render(self, frame: np.ndarray) -> np.ndarray:
        if not self.visible or not self.model_loaded:
            return frame

        try:
            results = self._run_yolo_tracking(frame)
            self._process_all_detections(frame, results)
        except Exception as e:
            print(f"YOLO Detection error: {e}")

        return frame

    def handle_key(self, key: int) -> bool:
        if key == ord('y'):
            self.toggle_visibility()
            print(f"YOLO Detection: {'ENABLED' if self.visible else 'DISABLED'}")
            return True
        return False

    def cleanup(self):
        if self.model is not None:
            del self.model
            self.model = None
        self.tracked_identities.clear()
