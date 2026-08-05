"""GYMFIT 공통 상체 운동 기반 및 숄더프레스 YOLO Pose 분석기."""

import math
import os
from typing import Any

from ultralytics import YOLO


# 아래 모든 값은 실제 카메라 테스트 후 조정 필요
SHOULDER_PRESS_CONFIG = {
    "up_elbow_angle": 155.0,  # 실제 카메라 테스트 후 조정 필요
    "down_elbow_angle": 110.0,  # 실제 카메라 테스트 후 조정 필요
    "wrist_above_head_margin": 0.02,  # 실제 카메라 테스트 후 조정 필요
    "down_wrist_shoulder_tolerance": 0.65,  # 실제 카메라 테스트 후 조정 필요
    "elbow_shoulder_tolerance": 0.55,  # 실제 카메라 테스트 후 조정 필요
    "wrist_balance_tolerance": 0.12,  # 실제 카메라 테스트 후 조정 필요
    "elbow_balance_tolerance": 0.14,  # 실제 카메라 테스트 후 조정 필요
    "minimum_wrist_spacing": 0.35,  # 실제 카메라 테스트 후 조정 필요
    "torso_warning_angle": 25.0,  # 실제 카메라 테스트 후 조정 필요
    "required_frames": 3,  # 실제 카메라 테스트 후 조정 필요
    "max_missing_frames": 15,  # 실제 카메라 테스트 후 조정 필요
    "min_keypoint_confidence": 0.35,  # 실제 카메라 테스트 후 조정 필요
}


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

    def _update_state(self, metrics):
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

    def process_frame(self, frame) -> tuple[Any, dict]:
        valid_person = False
        metrics = {"pose_valid": False, "missing_reason": "PERSON_NOT_FOUND"}
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
            break

        valid_pose = bool(metrics.get("pose_valid"))
        if valid_pose:
            self.missing_frames = 0
            self.last_missing_reason = None
            self._update_state(metrics)
        else:
            self.missing_frames += 1
            self.last_missing_reason = metrics.get("missing_reason")
            if self.missing_frames > self.max_missing_frames:
                self.transition_frames = 0
                self.candidate_stage = None
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
            **{
                key: round(value, 1) if isinstance(value, float) else value
                for key, value in metrics.items()
                if key not in {"pose_valid", "missing_reason"}
            },
        }
        if self.debug_enabled:
            result["debug"] = debug
        return annotated_frame, result


class ShoulderPressAnalyzer(UpperBodyExerciseAnalyzer):
    exercise_code = "SHOULDER_PRESS"
    display_name = "숄더프레스"
    missing_feedback = "양팔이 카메라에 보이게 해주세요"

    def __init__(self, model_path: str | Any = "yolo11n-pose.pt"):
        super().__init__(model_path, SHOULDER_PRESS_CONFIG)
        self.completed_up_phase = False

    def reset(self):
        super().reset()
        self.completed_up_phase = False

    @property
    def stage_text(self):
        return {"UP": "머리 위", "DOWN": "어깨 높이"}.get(self.stage, "준비")

    def _extract_metrics(self, person, person_conf):
        required = (0, 5, 6, 7, 8, 9, 10, 11, 12)
        valid, confidence = self._valid(person_conf, *required)
        if not valid:
            return {
                "pose_valid": False,
                "missing_reason": "BOTH_ARMS_OR_TORSO_LOW_CONFIDENCE",
            }
        nose = self._point(person, 0)
        left_shoulder, right_shoulder = self._point(person, 5), self._point(person, 6)
        left_elbow, right_elbow = self._point(person, 7), self._point(person, 8)
        left_wrist, right_wrist = self._point(person, 9), self._point(person, 10)
        left_hip, right_hip = self._point(person, 11), self._point(person, 12)
        shoulder_width = max(1.0, math.dist(left_shoulder[:2], right_shoulder[:2]))
        shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
        hip_x = (left_hip[0] + right_hip[0]) / 2
        hip_y = (left_hip[1] + right_hip[1]) / 2
        shoulder_x = (left_shoulder[0] + right_shoulder[0]) / 2
        torso_angle = abs(
            math.degrees(math.atan2(shoulder_x - hip_x, hip_y - shoulder_y))
        )
        return {
            "pose_valid": True,
            "confidence": confidence,
            "selected_side": "BOTH",
            "left_elbow_angle": calculate_angle(
                left_shoulder, left_elbow, left_wrist
            ),
            "right_elbow_angle": calculate_angle(
                right_shoulder, right_elbow, right_wrist
            ),
            "average_elbow_angle": (
                calculate_angle(left_shoulder, left_elbow, left_wrist)
                + calculate_angle(right_shoulder, right_elbow, right_wrist)
            ) / 2,
            "wrists_above_head": max(left_wrist[1], right_wrist[1])
            < nose[1] - shoulder_width * self.config["wrist_above_head_margin"],
            "wrist_shoulder_distance": (
                abs(left_wrist[1] - left_shoulder[1])
                + abs(right_wrist[1] - right_shoulder[1])
            ) / (2 * shoulder_width),
            "elbow_shoulder_distance": (
                abs(left_elbow[1] - left_shoulder[1])
                + abs(right_elbow[1] - right_shoulder[1])
            ) / (2 * shoulder_width),
            "wrist_balance_error": abs(left_wrist[1] - right_wrist[1])
            / shoulder_width,
            "elbow_balance_error": abs(left_elbow[1] - right_elbow[1])
            / shoulder_width,
            "wrist_spacing_ratio": abs(left_wrist[0] - right_wrist[0])
            / shoulder_width,
            "torso_angle": torso_angle,
        }

    def _evaluate(self, metrics):
        elbow = metrics["average_elbow_angle"]
        balanced = (
            metrics["wrist_balance_error"]
            <= self.config["wrist_balance_tolerance"]
            and metrics["elbow_balance_error"]
            <= self.config["elbow_balance_tolerance"]
        )
        up = (
            metrics["wrists_above_head"]
            and elbow >= self.config["up_elbow_angle"]
            and balanced
        )
        down = (
            elbow <= self.config["down_elbow_angle"]
            and metrics["wrist_shoulder_distance"]
            <= self.config["down_wrist_shoulder_tolerance"]
            and metrics["elbow_shoulder_distance"]
            <= self.config["elbow_shoulder_tolerance"]
            and balanced
        )
        target = "UP" if up else "DOWN" if down else None
        if not balanced:
            return target, "양팔 높이를 맞춰주세요", 68
        if metrics["wrist_spacing_ratio"] < self.config["minimum_wrist_spacing"]:
            return target, "손목이 너무 안쪽으로 모였어요", 72
        if metrics["torso_angle"] > self.config["torso_warning_angle"]:
            return target, "상체를 곧게 유지하세요", 70
        if self.stage != "UP" and not metrics["wrists_above_head"]:
            return target, "팔을 머리 위로 더 올려주세요", 80
        if self.stage != "UP" and elbow < self.config["up_elbow_angle"]:
            return target, "팔꿈치를 충분히 펴주세요", 84
        if self.stage == "UP" and not down:
            return target, "팔을 천천히 내려주세요", 86
        return target, "좋은 자세예요", 92

    def _on_stable_transition(self, previous_stage, target_stage):
        if target_stage == "UP" and previous_stage == "DOWN":
            self.completed_up_phase = True
        elif (
            target_stage == "DOWN"
            and previous_stage == "UP"
            and self.completed_up_phase
        ):
            self.count += 1
            self.completed_up_phase = False
            self.last_counted = True
            self.feedback = "좋은 숄더프레스입니다"
        elif previous_stage == "UNKNOWN":
            self.completed_up_phase = False
