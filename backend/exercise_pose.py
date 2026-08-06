"""GYMFIT 공통 상체 운동 기반 및 숄더프레스 YOLO Pose 분석기."""

import math
import os
from typing import Any

from ultralytics import YOLO



def calculate_angle(a, b, c) -> float:
    """세 점 a-b-c에서 b를 중심으로 0~180도 각도를 계산한다."""
    radians = math.atan2(c[1] - b[1], c[0] - b[0]) - math.atan2(
        a[1] - b[1], a[0] - b[0]
    )
    angle = abs(math.degrees(radians))
    return 360.0 - angle if angle > 180.0 else angle


def minimum_confidence(person_conf, *indexes: int) -> float:
    """요청한 키포인트 중 가장 낮은 신뢰도를 반환한다."""
    return min(float(person_conf[index]) for index in indexes)


def select_reference_person(result, min_width: int, min_height: int):
    """한 프레임에서 유효 박스 중 가장 큰 사람 한 명을 선택한다."""
    if (
        result.boxes is None
        or result.keypoints is None
        or result.keypoints.xy is None
        or len(result.boxes) == 0
    ):
        return None

    selected_index = None
    selected_area = 0.0
    for index, box in enumerate(result.boxes.xyxy):
        x1, y1, x2, y2 = box.tolist()
        width, height = x2 - x1, y2 - y1
        if width < min_width or height < min_height:
            continue
        area = width * height
        if area > selected_area:
            selected_index, selected_area = index, area
    return selected_index


def _env_flag(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class UpperBodyExerciseAnalyzer:
    """상체 운동 분석기의 공통 모델 실행·상태 안정화 처리."""

    exercise_code = ""
    display_name = ""
    missing_feedback = "필요한 관절이 화면에 보이게 해주세요"

    def __init__(self, model_path: str | Any = "yolo11n-pose.pt", config=None):
        self.model = model_path if hasattr(model_path, "predict") else YOLO(model_path)
        self.config = dict(config or {})
        self.min_keypoint_conf = float(
            self.config.get("min_keypoint_confidence", 0.35)
        )
        self.overlay_min_keypoint_conf = 0.30
        self.min_box_width = 70
        self.min_box_height = 120
        self.required_frames = int(self.config.get("required_frames", 3))
        self.max_missing_frames = int(self.config.get("max_missing_frames", 15))
        self.debug_enabled = _env_flag("POSE_DEBUG")
        self.reset()

    def reset(self):
        """운동 변경·새 코칭 시작 시 운동별 상태를 독립적으로 초기화한다."""
        self.count = 0
        self.stage = "UNKNOWN"
        self.feedback = "운동을 준비하세요"
        self.transition_frames = 0
        self.candidate_stage = None
        self.missing_frames = 0
        self.last_posture_score = 0
        self.score_total = 0
        self.score_samples = 0
        self.best_posture_score = 0
        self.last_counted = False
        self.last_missing_reason = None

    @staticmethod
    def calculate_angle(a, b, c):
        return calculate_angle(a, b, c)

    @staticmethod
    def _point(person, index):
        return person[index].tolist()

    def _valid(self, person_conf, *indexes):
        confidence = minimum_confidence(person_conf, *indexes)
        return confidence >= self.min_keypoint_conf, confidence

    def _extract_metrics(self, person, person_conf):
        raise NotImplementedError

    def _evaluate(self, metrics) -> tuple[str | None, str, int]:
        raise NotImplementedError

    def _accept_stable_stage(self, target_stage: str | None) -> bool:
        """같은 후보 상태가 연속 프레임 유지된 경우에만 전환한다."""
        if target_stage is None or target_stage == self.stage:
            self.candidate_stage = None
            self.transition_frames = 0
            return False
        if target_stage != self.candidate_stage:
            self.candidate_stage = target_stage
            self.transition_frames = 1
        else:
            self.transition_frames += 1
        if self.transition_frames < self.required_frames:
            return False
        previous_stage = self.stage
        self.stage = target_stage
        self.candidate_stage = None
        self.transition_frames = 0
        self._on_stable_transition(previous_stage, target_stage)
        return True

    def _on_stable_transition(self, previous_stage: str, target_stage: str):
        raise NotImplementedError

    @property
    def stage_text(self):
        return self.stage

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
        self._accept_stable_stage(target_stage)
        self._after_state_update(metrics, target_stage, frame, pose_overlay)

    def _after_state_update(self, metrics, target_stage, frame, pose_overlay):
        """Exercise-specific post-processing hook for the same analyzed frame."""

    def _on_tracking_lost(self):
        """Exercise-specific cleanup after an extended detection gap."""

    def _build_pose_overlay(self, result, person_index, frame_width, frame_height):
        if result.keypoints.conf is None:
            return None
        person = result.keypoints.xy[person_index]
        confidences = result.keypoints.conf[person_index]
        keypoints = []
        for index in range(min(17, len(person))):
            x, y = person[index].tolist()
            confidence = float(confidences[index])
            if (
                confidence < self.overlay_min_keypoint_conf
                or x <= 0
                or y <= 0
                or x >= frame_width
                or y >= frame_height
            ):
                continue
            keypoints.append({
                "id": index,
                "x": round(float(x), 2),
                "y": round(float(y), 2),
                "confidence": round(confidence, 3),
            })
        x1, y1, x2, y2 = result.boxes.xyxy[person_index].tolist()
        person_confidence = (
            float(result.boxes.conf[person_index])
            if result.boxes.conf is not None
            else None
        )
        return {
            "source_width": frame_width,
            "source_height": frame_height,
            "keypoints": keypoints,
            "selected_side": None,
            "bbox": {
                "x1": round(float(x1), 2),
                "y1": round(float(y1), 2),
                "x2": round(float(x2), 2),
                "y2": round(float(y2), 2),
                "confidence": round(person_confidence, 3)
                if person_confidence is not None
                else None,
            },
        }

    def process_frame(self, frame) -> tuple[Any, dict]:
        valid_person = False
        metrics = {"pose_valid": False, "missing_reason": "PERSON_NOT_FOUND"}
        pose_overlay = None
        results = self.model(frame, conf=0.5, classes=[0], verbose=False)
        annotated_frame = frame.copy()

        for result in results:
            annotated_frame = result.plot()
            person_index = select_reference_person(
                result, self.min_box_width, self.min_box_height
            )
            if person_index is None:
                continue
            valid_person = True
            if result.keypoints.conf is None:
                metrics = {
                    "pose_valid": False,
                    "missing_reason": "KEYPOINT_CONFIDENCE_UNAVAILABLE",
                }
                break
            metrics = self._extract_metrics(
                result.keypoints.xy[person_index],
                result.keypoints.conf[person_index],
            )
            pose_overlay = self._build_pose_overlay(
                result, person_index, frame.shape[1], frame.shape[0]
            )
            if pose_overlay is not None:
                pose_overlay["selected_side"] = metrics.get("selected_side")
            break

        valid_pose = bool(metrics.get("pose_valid"))
        if valid_pose:
            self.missing_frames = 0
            self.last_missing_reason = None
            self._update_state(metrics, frame, pose_overlay)
        else:
            self.missing_frames += 1
            self.last_missing_reason = metrics.get("missing_reason")
            if self.missing_frames > self.max_missing_frames:
                self.transition_frames = 0
                self.candidate_stage = None
                self._on_tracking_lost()
                self.feedback = self.missing_feedback

        status_text = (
            "자세 인식 중"
            if valid_pose
            else "사람 감지 / 관절 인식 불안정"
            if valid_person
            else "사람을 찾을 수 없습니다"
        )
        angles = {
            key.removesuffix("_angle"): round(value, 1)
            for key, value in metrics.items()
            if key.endswith("_angle") and isinstance(value, (int, float))
        }
        debug = {
            "selected_side": metrics.get("selected_side"),
            "stable_frames": self.transition_frames,
            "candidate_stage": self.candidate_stage,
            "missing_frames": self.missing_frames,
            "missing_reason": self.last_missing_reason,
            "counted_this_frame": self.last_counted,
            "average_score": round(self.score_total / self.score_samples, 1)
            if self.score_samples
            else 0,
            "best_score": self.best_posture_score,
        }
        result = {
            "exercise_code": self.exercise_code,
            "count": self.count,
            "stage": self.stage,
            "stage_text": self.stage_text,
            "angles": angles,
            "feedback": self.feedback,
            "posture_score": self.last_posture_score,
            "is_visible": valid_pose,
            "pose_valid": valid_pose,
            "person_valid": valid_person,
            "landmarks_detected": valid_pose,
            "status_text": status_text,
            "pose_overlay": pose_overlay if valid_pose else None,
            "source_width": frame.shape[1],
            "source_height": frame.shape[0],
            "bbox": pose_overlay.get("bbox") if pose_overlay else None,
            "person_confidence": (
                pose_overlay.get("bbox", {}).get("confidence")
                if pose_overlay
                else None
            ),
            "keypoints": pose_overlay.get("keypoints", []) if pose_overlay else [],
            "person_detected": valid_person,
            "pose_detected": valid_pose,
            "repetition_completed": self.last_counted,
            **{
                key: round(value, 1) if isinstance(value, float) else value
                for key, value in metrics.items()
                if key not in {"pose_valid", "missing_reason"}
            },
        }
        if self.debug_enabled:
            result["debug"] = debug
        if hasattr(self, "capture_fallback_reason"):
            result["capture_fallback_reason"] = self.capture_fallback_reason
        return annotated_frame, result


def __getattr__(name: str):
    """Keep legacy imports working while implementations stay in dedicated modules."""
    if name in {"ShoulderPressAnalyzer", "SHOULDER_PRESS_CONFIG"}:
        from backend.shoulder_press_pose import (
            SHOULDER_PRESS_CONFIG,
            ShoulderPressPoseAnalyzer,
        )

        return (
            ShoulderPressPoseAnalyzer
            if name == "ShoulderPressAnalyzer"
            else SHOULDER_PRESS_CONFIG
        )
    raise AttributeError(name)
