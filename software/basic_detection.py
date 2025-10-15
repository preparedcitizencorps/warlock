#!/usr/bin/env python3
"""
Project WARLOCK - Basic Object Detection Test
Phase 0: Foundation

Tests YOLO11 object detection with webcam input.
This script validates the core detection pipeline before moving to embedded hardware.

Usage:
    python software/basic_detection.py

Controls:
    'q' - Quit
    's' - Save current frame with detections
"""

import cv2
from ultralytics import YOLO
import time
from pathlib import Path


def main():
    """Run basic object detection on webcam feed."""

    # Load YOLO11n model (smallest/fastest variant)
    print("Loading YOLO11n model...")
    model = YOLO('yolo11n.pt')
    print("Model loaded successfully!")

    # Open webcam
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Error: Could not open webcam")
        return

    # Set resolution (optional - adjust for your camera)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    print("\nStarting detection...")
    print("Press 'q' to quit, 's' to save current frame")

    # Performance tracking
    fps_time = time.time()
    start_time = time.time()  # Capture start time for final FPS calculation
    frame_count = 0
    fps = 0.0  # Initialize fps to avoid NameError on early frames

    # Create output directory for saved frames
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)

    while True:
        ret, frame = cap.read()
        if not ret:
            print("Error: Failed to grab frame")
            break

        # Run YOLO detection
        results = model(frame, verbose=False)

        # Render detections on frame
        annotated_frame = results[0].plot()

        # Calculate FPS
        frame_count += 1
        if frame_count % 30 == 0:
            current_time = time.time()
            fps = 30 / (current_time - fps_time)
            fps_time = current_time
            print(f"FPS: {fps:.1f}")

        # Add FPS overlay
        cv2.putText(annotated_frame, f"FPS: {fps:.1f}" if frame_count >= 30 else "Calculating...",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)

        # Display frame
        cv2.imshow('WARLOCK - Object Detection Test', annotated_frame)

        # Handle keyboard input
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            break
        elif key == ord('s'):
            # Save current frame
            timestamp = time.strftime("%Y%m%d-%H%M%S")
            filename = output_dir / f"detection_{timestamp}.jpg"
            cv2.imwrite(str(filename), annotated_frame)
            print(f"Saved: {filename}")

    # Cleanup
    end_time = time.time()
    cap.release()
    cv2.destroyAllWindows()
    print("\nDetection test complete!")
    print(f"Final average FPS: {frame_count / (end_time - start_time):.1f}")


if __name__ == "__main__":
    main()
