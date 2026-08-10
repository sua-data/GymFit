"""Push-up-specific pose analysis built on the shared upper-body analyzer."""

import base64
import copy
import hashlib
import math
import os
import time
from typing import Any

import cv2

from backend.exercise_pose import (
    UpperBodyExerciseAnalyzer,
    calculate_angle,
    select_reference_person,
)
from backend.squat_pose import render_pose_capture


PUSHUP_CONFIG = {
    "down_elbow_angle": 105.0,
    "up_elbow_angle": 135.0,
    "body_alignment_warning": 18.0,
    "hip_offset_warning": 0.12,
    "required_frames": 1,
    "max_missing_frames": 15,
    "min_keypoint_confidence": 0.35,
}


class PushUpAnalyzer(UpperBodyExerciseAnalyzer):
    exercise_code = "PUSHUP"
    display_name = "푸시업"
    missing_feedback = "카메라를 몸 옆쪽에 배치해 주세요"
    model_detection_conf = 0.25

    def __init__(self, model_path: str | Any = "yolo11n-pose.pt"):
        super().__init__(model_path, PUSHUP_CONFIG)

        self.min_box_width = 80
        self.min_box_height = 35
        self.completed_down_phase = False

    def reset(self):
        super().reset()
        self.completed_down_phase = False
        self.up_frames = 0
        self.down_frames = 0
        self.analyzed_side = None
        self.best_pose_snapshot = None
        self._completed_pose_capture = None
        self.capture_fallback_reason = None
        self.current_min_elbow_angle = 180.0
        self.repetition_best_posture_score = -1.0
        self._joint_cache = {}
        self._frame_sequence = 0
        self._frame_timestamp_ms = 0.0
        self._frame_width = 0
        self._frame_height = 0
        self._joint_out_of_frame = False
        self.analyzed_alignment_side = None
        self.detection_failure_counts = {
            "no-person": 0,
            "arm-joints-missing": 0,
            "alignment-joints-missing": 0,
            "partial-occlusion": 0,
            "bbox-too-small": 0,
            "frame-too-dark": 0,
            "full-analysis": 0,
            "partial-analysis": 0,
        }

    @property
    def stage_text(self):
        return {"UP": "올라옴", "DOWN": "내려감"}.get(
            self.stage,
            "준비",
        )

    def _resolve_joint(self, person, person_conf, index, max_frames, max_ms):
        confidence = float(person_conf[index])
        point = self._point(person, index)
        coordinates_valid = (
            point[0] > 0
            and point[1] > 0
            and (self._frame_width <= 0 or point[0] < self._frame_width)
            and (self._frame_height <= 0 or point[1] < self._frame_height)
        )
        if confidence >= self.min_keypoint_conf and not coordinates_valid:
            self._joint_out_of_frame = True
        if confidence >= self.min_keypoint_conf and coordinates_valid:
            resolved = {
                "point": point,
                "confidence": confidence,
                "stale": False,
                "frame": self._frame_sequence,
                "timestamp_ms": self._frame_timestamp_ms,
            }
            self._joint_cache[index] = resolved
            return resolved
        cached = self._joint_cache.get(index)
        if cached and (
            self._frame_sequence - cached["frame"] <= max_frames
            and self._frame_timestamp_ms - cached["timestamp_ms"] <= max_ms
        ):
            return {**cached, "stale": True}
        return None

    def _extract_metrics(self, person, person_conf):
        arm_candidates = {}
        alignment_candidates = {}
        missing = []
        stale_joints = []
        side_indexes = {
            "LEFT": (5, 7, 9, 11, 15),
            "RIGHT": (6, 8, 10, 12, 16),
        }
        for side, (shoulder_i, elbow_i, wrist_i, hip_i, ankle_i) in side_indexes.items():
            arm_joints = {
                "shoulder": self._resolve_joint(person, person_conf, shoulder_i, 2, 250),
                "elbow": self._resolve_joint(person, person_conf, elbow_i, 2, 250),
                "wrist": self._resolve_joint(person, person_conf, wrist_i, 2, 250),
            }
            alignment_joints = {
                "shoulder": self._resolve_joint(person, person_conf, shoulder_i, 3, 350),
                "hip": self._resolve_joint(person, person_conf, hip_i, 3, 350),
                "ankle": self._resolve_joint(person, person_conf, ankle_i, 3, 350),
            }
            stale_joints.extend(
                f"{side.lower()}_{name}"
                for name, value in {**arm_joints, **alignment_joints}.items()
                if value is not None and value["stale"]
            )
            if all(arm_joints.values()):
                values = list(arm_joints.values())
                arm_candidates[side] = {
                    "side": side,
                    "elbow_angle": calculate_angle(
                        arm_joints["shoulder"]["point"],
                        arm_joints["elbow"]["point"],
                        arm_joints["wrist"]["point"],
                    ),
                    "confidence": sum(item["confidence"] for item in values) / 3,
                    "fresh": not any(item["stale"] for item in values),
                }
            else:
                missing.extend(
                    f"{side.lower()}_{name}"
                    for name, value in arm_joints.items()
                    if value is None
                )
            if all(alignment_joints.values()):
                values = list(alignment_joints.values())
                shoulder = alignment_joints["shoulder"]["point"]
                hip = alignment_joints["hip"]["point"]
                ankle = alignment_joints["ankle"]["point"]
                body_angle = calculate_angle(shoulder, hip, ankle)
                line_length = max(1.0, math.dist(shoulder[:2], ankle[:2]))
                vector_x, vector_y = ankle[0] - shoulder[0], ankle[1] - shoulder[1]
                projection = max(0.0, min(1.0, (
                    (hip[0] - shoulder[0]) * vector_x
                    + (hip[1] - shoulder[1]) * vector_y
                ) / (line_length * line_length)))
                expected_hip_y = shoulder[1] + projection * vector_y
                alignment_candidates[side] = {
                    "side": side,
                    "body_alignment_angle": body_angle,
                    "body_alignment_error": abs(180.0 - body_angle),
                    "hip_line_offset": (hip[1] - expected_hip_y) / line_length,
                    "confidence": sum(item["confidence"] for item in values) / 3,
                    "fresh": not any(item["stale"] for item in values),
                }
            else:
                missing.extend(
                    f"{side.lower()}_{name}"
                    for name, value in alignment_joints.items()
                    if value is None
                )

        if not arm_candidates:
            return {
                "pose_valid": False,
                "arm_available": False,
                "count_available": False,
                "alignment_available": False,
                "analysis_quality": "LIMITED",
                "missing_required_joints": sorted(set(missing)),
                "stale_joints": sorted(set(stale_joints)),
                "occlusion_reason": "arm-joints-missing",
                "missing_reason": "ARM_JOINTS_MISSING",
            }
        fresh_arm_sides = [
            side for side, candidate in arm_candidates.items()
            if candidate["fresh"]
        ]
        if (
            self.analyzed_side in arm_candidates
            and arm_candidates[self.analyzed_side]["fresh"]
        ):
            arm_side = self.analyzed_side
        elif fresh_arm_sides:
            arm_side = max(
                fresh_arm_sides,
                key=lambda side: arm_candidates[side]["confidence"],
            )
        elif self.analyzed_side in arm_candidates:
            arm_side = self.analyzed_side
        else:
            arm_side = max(
                arm_candidates,
                key=lambda side: arm_candidates[side]["confidence"],
            )
        arm = arm_candidates[arm_side]
        self.analyzed_side = arm_side
        alignment_side = (
            max(alignment_candidates, key=lambda side: alignment_candidates[side]["confidence"])
            if alignment_candidates
            else None
        )
        alignment = alignment_candidates.get(alignment_side)
        self.analyzed_alignment_side = alignment_side
        quality = "FULL" if alignment and arm["fresh"] else "PARTIAL" if arm["fresh"] else "LIMITED"
        reported_missing = [] if quality == "FULL" else sorted(set(missing))
        return {
            "pose_valid": True,
            "selected_side": arm_side,
            "analyzed_side": arm_side,
            "analyzed_arm_side": arm_side,
            "analyzed_alignment_side": alignment_side,
            "arm_available": True,
            "count_available": arm["fresh"],
            "arm_fresh": arm["fresh"],
            "alignment_available": alignment is not None,
            "alignment_fresh": alignment["fresh"] if alignment else False,
            "elbow_angle": arm["elbow_angle"],
            "arm_confidence": arm["confidence"],
            "body_alignment_angle": alignment["body_alignment_angle"] if alignment else None,
            "body_alignment_error": alignment["body_alignment_error"] if alignment else None,
            "hip_line_offset": alignment["hip_line_offset"] if alignment else None,
            "alignment_confidence": alignment["confidence"] if alignment else None,
            "required_joint_confidence": arm["confidence"],
            "analysis_quality": quality,
            "missing_required_joints": reported_missing,
            "stale_joints": sorted(set(stale_joints)),
            "occlusion_reason": None if quality == "FULL" else "alignment-joints-missing" if arm["fresh"] else "partial-occlusion",
        }

    def _evaluate(self, metrics):
        elbow = metrics["elbow_angle"]
        body_error = metrics["body_alignment_error"]
        hip_offset = metrics["hip_line_offset"]
        target = (
            "DOWN"
            if elbow <= self.config["down_elbow_angle"]
            else "UP"
            if elbow >= self.config["up_elbow_angle"]
            else None
        )
        metrics["depth_status"] = target or "TRANSITION"
        metrics["evaluated_metrics"] = ["elbow_depth", "arm_extension"]
        metrics["unavailable_metrics"] = []
        if metrics["alignment_available"]:
            metrics["evaluated_metrics"].append("body_alignment")
        else:
            metrics["unavailable_metrics"].append("body_alignment")
        coverage = 1.0 if metrics["alignment_available"] else 0.8
        freshness = 1.0 if metrics["arm_fresh"] else 0.55
        alignment_freshness = (
            1.0
            if not metrics["alignment_available"] or metrics["alignment_fresh"]
            else 0.85
        )
        confidence_values = [metrics["arm_confidence"]]
        if metrics["alignment_available"]:
            confidence_values.append(metrics["alignment_confidence"])
        metrics["score_confidence"] = max(
            0.0,
            min(
                1.0,
                sum(confidence_values)
                / len(confidence_values)
                * coverage
                * freshness
                * alignment_freshness,
            ),
        )
        if not metrics["alignment_available"]:
            metrics["posture_feedback_override"] = (
                "하체가 가려져 몸통 정렬은 평가하지 못했어요."
            )
        if hip_offset is not None and abs(hip_offset) >= self.config["hip_offset_warning"]:
            feedback = (
                "엉덩이가 너무 내려갔어요"
                if hip_offset > 0
                else "엉덩이가 너무 올라갔어요"
            )
            return target, feedback, 65
        if body_error is not None and body_error >= self.config["body_alignment_warning"]:
            return target, "몸을 일직선으로 유지하세요", 70
        if self.stage in {"UNKNOWN", "UP"} and elbow > self.config["down_elbow_angle"]:
            feedback, score = "팔을 조금 더 굽혀보세요", 82
        elif self.stage == "DOWN" and elbow < self.config["up_elbow_angle"]:
            feedback, score = "팔을 끝까지 펴주세요", 85
        else:
            feedback, score = "좋은 자세예요", 92
        if not metrics["alignment_available"]:
            return target, metrics["posture_feedback_override"], min(score, 84)
        return target, feedback, score

    def _update_state(self, metrics, frame=None, pose_overlay=None):
        self.last_counted = False
        target_stage, feedback, score = self._evaluate(metrics)
        self.feedback = feedback
        self.last_posture_score = max(0, min(100, int(score)))
        self.score_total += self.last_posture_score
        self.score_samples += 1
        self.best_posture_score = max(
            self.best_posture_score, self.last_posture_score
        )
        if metrics.get("arm_fresh"):
            self._accept_stable_stage(target_stage)
        else:
            self.candidate_stage = None
            self.transition_frames = 0
        self._after_state_update(metrics, target_stage, frame, pose_overlay)

    def _reset_repetition_capture(self):
        self.best_pose_snapshot = None
        self.capture_fallback_reason = None
        self.current_min_elbow_angle = 180.0
        self.repetition_best_posture_score = -1.0

    def _candidate_rank(self, score, elbow_angle, body_alignment_angle):
        return (
            -float(elbow_angle),
            float(score),
            -abs(180.0 - float(body_alignment_angle))
            if body_alignment_angle is not None
            else float("-inf"),
        )

    def _update_best_pose(self, frame, metrics, pose_overlay):
        if (
            self.stage != "DOWN"
            or self.down_frames < self.required_frames
            or metrics["elbow_angle"] > self.config["down_elbow_angle"]
            or not metrics.get("arm_fresh")
            or not pose_overlay
            or not pose_overlay.get("keypoints")
            or frame is None
        ):
            return
        score = float(self.last_posture_score)
        rank = self._candidate_rank(
            score,
            metrics["elbow_angle"],
            metrics["body_alignment_angle"],
        )
        current_rank = (
            self.best_pose_snapshot.get("_rank")
            if self.best_pose_snapshot
            else None
        )
        if current_rank is not None and rank <= tuple(current_rank):
            return

        locked_frame = render_pose_capture(frame, pose_overlay)
        encoded, jpeg_buffer = cv2.imencode(
            ".jpg", locked_frame, [cv2.IMWRITE_JPEG_QUALITY, 82]
        )
        if not encoded:
            return
        jpeg_bytes = jpeg_buffer.tobytes()
        self.best_pose_snapshot = {
            "image": "data:image/jpeg;base64,"
            + base64.b64encode(jpeg_bytes).decode("ascii"),
            "image_hash": hashlib.sha256(jpeg_bytes).hexdigest()[:16],
            "score": score,
            "elbow_angle": float(metrics["elbow_angle"]),
            "body_alignment_angle": (
                float(metrics["body_alignment_angle"])
                if metrics["body_alignment_angle"] is not None
                else None
            ),
            "feedback": self.feedback,
            "stage": "DOWN",
            "bbox": copy.deepcopy(pose_overlay["bbox"]),
            "person_confidence": pose_overlay["bbox"].get("confidence"),
            "keypoints": copy.deepcopy(pose_overlay["keypoints"]),
            "analyzed_side": metrics["selected_side"],
            "_rank": rank,
        }
        self.repetition_best_posture_score = score

    def _after_state_update(self, metrics, target_stage, frame, pose_overlay):
        if not metrics.get("arm_fresh"):
            return
        if target_stage == "DOWN":
            if self.stage == "UP" and self.down_frames == 0:
                self._reset_repetition_capture()
            self.down_frames += 1
            self.up_frames = 0
            self.current_min_elbow_angle = min(
                self.current_min_elbow_angle, metrics["elbow_angle"]
            )
        elif target_stage == "UP":
            self.up_frames += 1
            self.down_frames = 0
        else:
            self.up_frames = 0
            self.down_frames = 0
        self._update_best_pose(frame, metrics, pose_overlay)

    def _on_tracking_lost(self):
        self.up_frames = 0
        self.down_frames = 0
        self.analyzed_side = None
        self.completed_down_phase = False
        self._joint_cache = {}
        self._reset_repetition_capture()

    def _on_stable_transition(self, previous_stage, target_stage):
        # DOWN 자세가 확인되면 다음 UP을 카운트할 준비
        if target_stage == "DOWN":
            self.completed_down_phase = True
            return

        # DOWN을 거친 뒤 UP으로 돌아오면 1회 완료
        if (
            target_stage == "UP"
            and self.completed_down_phase
        ):
            self.count += 1
            self.completed_down_phase = False
            self.last_counted = True
            self.feedback = "좋은 푸시업입니다"

            if self.best_pose_snapshot is not None:
                capture = copy.deepcopy(
                    self.best_pose_snapshot
                )
                capture.pop("_rank", None)

                self._completed_pose_capture = capture
                self.capture_fallback_reason = None

            else:
                self._completed_pose_capture = None
                self.capture_fallback_reason = (
                    "no-valid-down-pose"
                )

    def _record_detection(self, reason):
        if reason in self.detection_failure_counts:
            self.detection_failure_counts[reason] += 1

    def _debug_raw_yolo_results(self, results, frame, model_conf):
        if os.getenv("POSE_DEBUG", "").strip().lower() not in {
            "1", "true", "yes", "on"
        }:
            return
        summaries = []
        total_boxes = 0
        raw_box_confidences = []
        for result in results:
            box_count = len(result.boxes) if result.boxes is not None else 0
            total_boxes += box_count
            if result.boxes is not None and result.boxes.conf is not None:
                raw_box_confidences.extend(
                    round(float(value), 4)
                    for value in result.boxes.conf.tolist()
                )
            summaries.append({
                "box_count": box_count,
                "box_confidences": (
                    [round(float(value), 4) for value in result.boxes.conf.tolist()]
                    if result.boxes is not None and result.boxes.conf is not None
                    else []
                ),
                "bbox_xyxy": (
                    [[round(float(value), 2) for value in box]
                     for box in result.boxes.xyxy.tolist()]
                    if result.boxes is not None and result.boxes.xyxy is not None
                    else []
                ),
                "box_classes": (
                    [int(value) for value in result.boxes.cls.tolist()]
                    if result.boxes is not None and result.boxes.cls is not None
                    else []
                ),
                "keypoints_present": result.keypoints is not None,
                "keypoint_shape": (
                    list(result.keypoints.xy.shape)
                    if result.keypoints is not None
                    and result.keypoints.xy is not None
                    else None
                ),
            })
        print({
            "event": "pushup-yolo-raw",
            "reason": "valid-frame-no-detection" if total_boxes == 0 else "raw-detection",
            "model_conf": model_conf,
            "raw_box_count": total_boxes,
            "raw_box_confidences": raw_box_confidences,
            "classes_filter": None,
            "input_shape": list(frame.shape),
            "results": summaries,
        })

    def process_frame(
        self,
        frame,
        frame_mean_brightness=None,
        brightness_adjusted=False,
    ) -> tuple[Any, dict]:
        self._frame_sequence += 1
        self._frame_timestamp_ms = time.monotonic() * 1000
        self._frame_height, self._frame_width = frame.shape[:2]
        self._joint_out_of_frame = False
        frame_brightness = (
            float(frame_mean_brightness)
            if frame_mean_brightness is not None
            else float(frame.mean())
        )
        if frame_brightness < 58:
            self._record_detection("frame-too-dark")

        person_detected = False
        pose_overlay = None
        metrics = {
            "pose_valid": False,
            "arm_available": False,
            "count_available": False,
            "alignment_available": False,
            "analysis_quality": "NONE",
            "missing_required_joints": [],
            "occlusion_reason": "no-person",
        }
        detection_reason = "no-person"
        model_conf = self.model_detection_conf
        results = list(self.model(frame, conf=model_conf, verbose=False))
        self._debug_raw_yolo_results(results, frame, model_conf)
        for result in results:
            box_count = len(result.boxes) if result.boxes is not None else 0
            if box_count:
                person_detected = True
            person_index = select_reference_person(
                result, self.min_box_width, self.min_box_height
            )
            if person_index is None:
                if box_count:
                    detection_reason = "bbox-too-small"
                continue
            if result.keypoints.conf is None:
                detection_reason = "arm-joints-missing"
                break
            pose_overlay = self._build_pose_overlay(
                result, person_index, self._frame_width, self._frame_height
            )
            metrics = self._extract_metrics(
                result.keypoints.xy[person_index],
                result.keypoints.conf[person_index],
            )
            if pose_overlay is not None:
                pose_overlay["selected_side"] = metrics.get("analyzed_arm_side")
            detection_reason = metrics.get("occlusion_reason") or "full-analysis"
            break

        arm_available = bool(metrics.get("arm_available"))
        count_available = bool(metrics.get("count_available"))
        if arm_available:
            self.missing_frames = 0 if count_available else self.missing_frames + 1
            self._update_state(metrics, frame, pose_overlay)
        else:
            self.last_counted = False
            self.missing_frames += 1
            self.last_posture_score = 0
            if detection_reason == "bbox-too-small":
                self.feedback = "카메라를 조금 더 가까이 배치해 주세요."
            elif self._joint_out_of_frame:
                self.feedback = "머리부터 발목까지 화면 안에 들어오게 조정해 주세요."
            elif person_detected:
                self.feedback = (
                    "팔이 가려졌어요. 카메라가 몸의 옆면을 보게 조정해 주세요."
                )
            else:
                self.feedback = "카메라에 몸 전체가 보이게 해주세요"
            if self.missing_frames > self.max_missing_frames:
                self._on_tracking_lost()

        quality = metrics.get("analysis_quality", "NONE")
        if not person_detected:
            quality = "NONE"
            detection_reason = "no-person"
        elif not arm_available:
            quality = "LIMITED"
            detection_reason = (
                "bbox-too-small"
                if detection_reason == "bbox-too-small"
                else "arm-joints-missing"
            )
        elif quality == "FULL":
            detection_reason = "full-analysis"
        elif quality == "PARTIAL":
            detection_reason = "partial-analysis"

        self._record_detection(detection_reason)
        if arm_available and not metrics.get("alignment_available"):
            self._record_detection("alignment-joints-missing")
        if quality in {"PARTIAL", "LIMITED"} and person_detected:
            self._record_detection("partial-occlusion")

        status = {
            "exercise_code": self.exercise_code,
            "count": self.count,
            "stage": self.stage,
            "stage_text": self.stage_text,
            "feedback": self.feedback,
            "posture_score": self.last_posture_score,
            "score_confidence": round(float(metrics.get("score_confidence", 0)), 3),
            "evaluated_metrics": metrics.get("evaluated_metrics", []),
            "unavailable_metrics": metrics.get("unavailable_metrics", []),
            "analysis_quality": quality,
            "count_available": count_available,
            "alignment_available": bool(metrics.get("alignment_available")),
            "arm_available": arm_available,
            "analyzed_side": metrics.get("analyzed_arm_side"),
            "analyzed_arm_side": metrics.get("analyzed_arm_side"),
            "analyzed_alignment_side": metrics.get("analyzed_alignment_side"),
            "elbow_angle": round(metrics["elbow_angle"], 1)
            if metrics.get("elbow_angle") is not None else None,
            "body_alignment_angle": round(metrics["body_alignment_angle"], 1)
            if metrics.get("body_alignment_angle") is not None else None,
            "arm_confidence": round(metrics["arm_confidence"], 3)
            if metrics.get("arm_confidence") is not None else None,
            "alignment_confidence": round(metrics["alignment_confidence"], 3)
            if metrics.get("alignment_confidence") is not None else None,
            "depth_status": metrics.get("depth_status"),
            "missing_required_joints": metrics.get("missing_required_joints", []),
            "stale_joints": metrics.get("stale_joints", []),
            "occlusion_reason": (
                metrics.get("occlusion_reason") or detection_reason
                if arm_available
                else detection_reason
            ),
            "is_visible": arm_available,
            "pose_valid": arm_available,
            "person_valid": person_detected,
            "person_detected": person_detected,
            "pose_detected": bool(pose_overlay and pose_overlay.get("keypoints")),
            "landmarks_detected": bool(pose_overlay and pose_overlay.get("keypoints")),
            "pose_overlay": pose_overlay,
            "source_width": self._frame_width,
            "source_height": self._frame_height,
            "bbox": pose_overlay.get("bbox") if pose_overlay else None,
            "person_confidence": pose_overlay.get("bbox", {}).get("confidence")
            if pose_overlay else None,
            "keypoints": pose_overlay.get("keypoints", []) if pose_overlay else [],
            "status_text": "자세 인식 중" if arm_available else self.feedback,
            "repetition_completed": self.last_counted,
            "capture_fallback_reason": self.capture_fallback_reason,
            "detection_reason": detection_reason,
            "detection_failure_counts": dict(self.detection_failure_counts),
            "frame_brightness": round(frame_brightness, 1),
            "brightness_adjusted": bool(brightness_adjusted),
        }
        return frame.copy(), status

    def get_completed_pose_capture(self):
        return self._completed_pose_capture

    def clear_completed_pose_capture(self):
        self._completed_pose_capture = None
        self._reset_repetition_capture()
