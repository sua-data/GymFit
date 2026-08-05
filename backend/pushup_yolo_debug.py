"""Run isolated YOLO Pose diagnostics on the received push-up JPEG."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
from ultralytics import YOLO


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "debug" / "pushup_received_frame.jpg"
DEFAULT_OUTPUT = PROJECT_ROOT / "debug" / "pushup_yolo_result.jpg"


def summarize(results):
    boxes = []
    keypoint_shapes = []
    for result in results:
        if result.boxes is not None:
            confidences = (
                result.boxes.conf.tolist() if result.boxes.conf is not None else []
            )
            coordinates = (
                result.boxes.xyxy.tolist() if result.boxes.xyxy is not None else []
            )
            boxes.extend({
                "confidence": round(float(confidence), 4),
                "xyxy": [round(float(value), 2) for value in coordinate],
            } for confidence, coordinate in zip(confidences, coordinates))
        keypoint_shapes.append(
            list(result.keypoints.xy.shape)
            if result.keypoints is not None and result.keypoints.xy is not None
            else None
        )
    return {
        "person_box_count": len(boxes),
        "boxes": boxes,
        "keypoint_shapes": keypoint_shapes,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--model", default="yolo11n-pose.pt")
    args = parser.parse_args()

    frame = cv2.imread(str(args.input))
    if frame is None:
        raise SystemExit(f"Input JPEG could not be decoded: {args.input}")

    model = YOLO(args.model)
    report = {
        "input": str(args.input),
        "shape": list(frame.shape),
        "mean_brightness": round(float(frame.mean()), 2),
        "min_pixel": int(frame.min()),
        "max_pixel": int(frame.max()),
        "operational_note": "No classes filter; confidence sweep is diagnostic only.",
        "original": {},
        "legacy_brightness_contrast_approx": {},
    }

    # Approximate the recently disabled CSS canvas filter for controlled A/B.
    enhanced = cv2.convertScaleAbs(frame, alpha=1.08, beta=12)
    for confidence in (0.5, 0.35, 0.25):
        original_results = model.predict(
            source=str(args.input), conf=confidence, verbose=False
        )
        enhanced_results = model.predict(
            source=enhanced, conf=confidence, verbose=False
        )
        report["original"][str(confidence)] = summarize(original_results)
        report["legacy_brightness_contrast_approx"][str(confidence)] = summarize(
            enhanced_results
        )
        if confidence == 0.25:
            rendered = (
                original_results[0].plot()
                if original_results
                else frame.copy()
            )
            args.output.parent.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(args.output), rendered)

    report["result_image"] = str(args.output)
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
