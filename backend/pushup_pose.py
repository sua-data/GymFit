"""Push-up-specific pose analysis built on the shared upper-body analyzer."""

import math
from typing import Any

from backend.exercise_pose import UpperBodyExerciseAnalyzer, calculate_angle


PUSHUP_CONFIG = {
    "down_elbow_angle": 90.0,
    "up_elbow_angle": 155.0,
    "body_alignment_warning": 18.0,
    "hip_offset_warning": 0.12,
    "required_frames": 3,
    "max_missing_frames": 15,
    "min_keypoint_confidence": 0.35,
}


class PushUpAnalyzer(UpperBodyExerciseAnalyzer):
    exercise_code = "PUSHUP"
    display_name = "푸시업"
    missing_feedback = "카메라에 몸 전체가 보이게 해주세요"

    def __init__(self, model_path: str | Any = "yolo11n-pose.pt"):
        super().__init__(model_path, PUSHUP_CONFIG)
        self.completed_down_phase = False

    def reset(self):
        super().reset()
        self.completed_down_phase = False

    @property
    def stage_text(self):
        return {"UP": "올라옴", "DOWN": "내려감"}.get(self.stage, "준비")

    def _extract_metrics(self, person, person_conf):
        candidates = []
        for side, indexes in (
            ("LEFT", (5, 7, 9, 11, 13, 15)),
            ("RIGHT", (6, 8, 10, 12, 14, 16)),
        ):
            shoulder_i, elbow_i, wrist_i, hip_i, knee_i, ankle_i = indexes
            arm_valid, arm_conf = self._valid(
                person_conf, shoulder_i, elbow_i, wrist_i
            )
            ankle_valid, ankle_conf = self._valid(
                person_conf, shoulder_i, hip_i, ankle_i
            )
            knee_valid, knee_conf = self._valid(
                person_conf, shoulder_i, hip_i, knee_i
            )
            if not arm_valid or not (ankle_valid or knee_valid):
                continue
            end_i = ankle_i if ankle_conf >= knee_conf else knee_i
            confidence = min(arm_conf, max(ankle_conf, knee_conf))
            shoulder = self._point(person, shoulder_i)
            elbow = self._point(person, elbow_i)
            wrist = self._point(person, wrist_i)
            hip = self._point(person, hip_i)
            body_end = self._point(person, end_i)
            body_angle = calculate_angle(shoulder, hip, body_end)
            line_length = max(1.0, math.dist(shoulder[:2], body_end[:2]))
            vector_x = body_end[0] - shoulder[0]
            vector_y = body_end[1] - shoulder[1]
            projection = max(
                0.0,
                min(
                    1.0,
                    (
                        (hip[0] - shoulder[0]) * vector_x
                        + (hip[1] - shoulder[1]) * vector_y
                    )
                    / (line_length * line_length),
                ),
            )
            expected_hip_y = shoulder[1] + projection * vector_y
            hip_vertical_offset = (hip[1] - expected_hip_y) / line_length
            candidates.append(
                {
                    "confidence": confidence,
                    "selected_side": side,
                    "body_endpoint": "ANKLE" if end_i == ankle_i else "KNEE",
                    "elbow_angle": calculate_angle(shoulder, elbow, wrist),
                    "body_angle": body_angle,
                    "body_alignment_error": abs(180.0 - body_angle),
                    "hip_line_offset": hip_vertical_offset,
                }
            )
        if not candidates:
            return {
                "pose_valid": False,
                "missing_reason": "FULL_BODY_KEYPOINTS_LOW_CONFIDENCE",
            }
        return {"pose_valid": True, **max(candidates, key=lambda x: x["confidence"])}

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
        if abs(hip_offset) >= self.config["hip_offset_warning"]:
            feedback = (
                "엉덩이가 너무 내려갔어요"
                if hip_offset > 0
                else "엉덩이가 너무 올라갔어요"
            )
            return target, feedback, 65
        if body_error >= self.config["body_alignment_warning"]:
            return target, "몸을 일직선으로 유지하세요", 70
        if self.stage in {"UNKNOWN", "UP"} and elbow > self.config["down_elbow_angle"]:
            return target, "팔을 조금 더 굽혀보세요", 82
        if self.stage == "DOWN" and elbow < self.config["up_elbow_angle"]:
            return target, "팔을 끝까지 펴주세요", 85
        return target, "좋은 자세예요", 92

    def _on_stable_transition(self, previous_stage, target_stage):
        if target_stage == "DOWN" and previous_stage == "UP":
            self.completed_down_phase = True
        elif (
            target_stage == "UP"
            and previous_stage == "DOWN"
            and self.completed_down_phase
        ):
            self.count += 1
            self.completed_down_phase = False
            self.last_counted = True
            self.feedback = "좋은 푸시업입니다"
        elif previous_stage == "UNKNOWN":
            self.completed_down_phase = False

