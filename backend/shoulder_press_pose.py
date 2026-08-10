"""Shoulder-press pose analysis built on the shared upper-body analyzer."""

import time
import math
from typing import Any

from backend.exercise_pose import UpperBodyExerciseAnalyzer, calculate_angle


SHOULDER_PRESS_CONFIG = {
    "up_elbow_angle": 143.5,
    "down_elbow_angle": 115.0,
    "required_frames": 1,
    "max_missing_frames": 15,
    "min_keypoint_confidence": 0.35,
    "side_switch_margin": 0.20,
    "side_switch_frames": 5,
    "torso_warning_angle": 25.0,

    "arm_angle_difference_limit": 50.0
}

class ShoulderPressPoseAnalyzer(UpperBodyExerciseAnalyzer):
    exercise_code = "SHOULDER_PRESS"
    display_name = "숄더프레스"
    missing_feedback = "어깨와 팔이 카메라에 보이게 해주세요"

    def __init__(self, model_path: str | Any = "yolo11n-pose.pt"):
        super().__init__(model_path, SHOULDER_PRESS_CONFIG)

    def reset(self):
        super().reset()
        self.selected_side = None
        self.side_candidate = None
        self.side_candidate_frames = 0
        self.down_frames = 0
        self.up_frames = 0

        self.last_count_time = 0.0

    @property
    def stage_text(self):
        return {"UP": "팔 위", "DOWN": "팔 아래"}.get(self.stage, "준비")

    def _select_side(self, confidences):
        previous_side = self.selected_side
        scores = {
            "LEFT": min(float(confidences[i]) for i in (5, 7, 9)),
            "RIGHT": min(float(confidences[i]) for i in (6, 8, 10)),
        }
        available = {
            side: score >= self.min_keypoint_conf for side, score in scores.items()
        }
        best = max(scores, key=scores.get)
        if self.selected_side is None or not available[self.selected_side]:
            self.selected_side = best if available[best] else None
            self.side_candidate = None
            self.side_candidate_frames = 0
        elif (
            best != self.selected_side
            and available[best]
            and scores[best]
            >= scores[self.selected_side] + self.config["side_switch_margin"]
        ):
            if self.side_candidate == best:
                self.side_candidate_frames += 1
            else:
                self.side_candidate = best
                self.side_candidate_frames = 1
            if self.side_candidate_frames >= self.config["side_switch_frames"]:
                self.selected_side = best
                self.side_candidate = None
                self.side_candidate_frames = 0
        else:
            self.side_candidate = None
            self.side_candidate_frames = 0
        if previous_side is not None and self.selected_side != previous_side:
            self.down_frames = 0
            self.up_frames = 0
            self.candidate_stage = None
            self.transition_frames = 0
        return self.selected_side, scores

    def _extract_metrics(self, person, person_conf):
        side, scores = self._select_side(person_conf)
        torso_valid, torso_confidence = self._valid(person_conf, 5, 6, 11, 12)
        if side is None or not torso_valid:
            return {
                "pose_valid": False,
                "missing_reason": "ARM_OR_TORSO_LOW_CONFIDENCE",
            }

        indexes = (5, 7, 9) if side == "LEFT" else (6, 8, 10)
        shoulder, elbow, wrist = (self._point(person, i) for i in indexes)
        angles = {}
        for label, arm_indexes in (
            ("LEFT", (5, 7, 9)),
            ("RIGHT", (6, 8, 10)),
        ):
            if min(float(person_conf[i]) for i in arm_indexes) >= self.min_keypoint_conf:
                points = [self._point(person, i) for i in arm_indexes]
                angles[label] = calculate_angle(*points)
        elbow_angle = calculate_angle(shoulder, elbow, wrist)
        left_shoulder, right_shoulder = self._point(person, 5), self._point(person, 6)
        left_hip, right_hip = self._point(person, 11), self._point(person, 12)
        shoulder_mid = (
            (left_shoulder[0] + right_shoulder[0]) / 2,
            (left_shoulder[1] + right_shoulder[1]) / 2,
        )
        hip_mid = (
            (left_hip[0] + right_hip[0]) / 2,
            (left_hip[1] + right_hip[1]) / 2,
        )
        torso_angle = abs(
            math.degrees(
                math.atan2(shoulder_mid[0] - hip_mid[0], hip_mid[1] - shoulder_mid[1])
            )
        )
        return {
            "pose_valid": True,
            "selected_side": side,
            "selected_side_confidence": scores[side],
            "confidence": min(scores[side], torso_confidence),
            "elbow_angle": elbow_angle,
            "average_elbow_angle": sum(angles.values()) / len(angles),
            "left_elbow_angle": angles.get("LEFT"),
            "right_elbow_angle": angles.get("RIGHT"),
            "torso_angle": torso_angle,
        }

    def _evaluate(self, metrics):
        elbow = metrics["elbow_angle"]

        # YOLO가 팔 관절을 순간적으로 잘못 연결한 프레임 제거
        if elbow < 45.0:
            self.down_frames = 0
            self.up_frames = 0
            return None, "팔이 카메라에 잘 보이게 유지해주세요", 75

        target = (
            "UP"
            if elbow >= self.config["up_elbow_angle"]
            else "DOWN"
            if elbow <= self.config["down_elbow_angle"]
            else None
        )

        if target == "DOWN":
            self.down_frames += 1
            self.up_frames = 0
        elif target == "UP":
            self.up_frames += 1
            self.down_frames = 0
        else:
            self.down_frames = 0
            self.up_frames = 0

        if metrics["torso_angle"] > self.config["torso_warning_angle"]:
            return target, "상체를 곧게 유지해주세요", 70

        if target == "DOWN":
            return target, "팔을 머리 위로 끝까지 밀어주세요", 84

        if target is None:
            return target, "팔꿈치를 충분히 펴주세요", 86

        return target, "좋은 자세예요", 92

    def _on_stable_transition(self, previous_stage, target_stage):
        if previous_stage != "DOWN" or target_stage != "UP":
            return

        now = time.monotonic()
        elapsed = now - self.last_count_time

        print(
            "[SHOULDER PRESS TRANSITION]",
            {
                "previous": previous_stage,
                "target": target_stage,
                "elapsed": round(elapsed, 3),
                "count_before": self.count,
            },
        )

        if elapsed < 0.85:
            print("[SHOULDER PRESS] cooldown blocked")
            return

        self.count += 1
        self.last_count_time = now
        self.last_counted = True
        self.feedback = "좋은 숄더프레스입니다"

        print("[SHOULDER PRESS] counted", self.count)

    def process_frame(self, frame):
        annotated_frame, status = super().process_frame(frame)
        detection_reason = (
            "ok"
            if status["pose_valid"]
            else self.last_missing_reason
            or ("PERSON_NOT_FOUND" if not status["person_detected"] else "POSE_INVALID")
        )
        runtime_debug = {
            "left_elbow_angle": status.get("left_elbow_angle"),
            "right_elbow_angle": status.get("right_elbow_angle"),
            "elbow_angle": status.get("elbow_angle"),
            "average_elbow_angle": status.get("average_elbow_angle"),
            "selected_side": status.get("selected_side"),
            "selected_side_confidence": status.get("selected_side_confidence"),
            "down_frames": self.down_frames,
            "up_frames": self.up_frames,
            "required_frames": self.required_frames,
            "stage": self.stage,
            "count": self.count,
            "pose_valid": status["pose_valid"],
            "person_detected": status["person_detected"],
            "detection_reason": detection_reason,
            "analyzer_class": type(self).__name__,
            "analyzer_instance_id": id(self),
            "candidate_stage": self.candidate_stage,
            "side_candidate": self.side_candidate,
            "side_candidate_frames": self.side_candidate_frames,
            "down_threshold": self.config["down_elbow_angle"],
            "up_threshold": self.config["up_elbow_angle"],
            "arm_angle_difference": (
                abs(
                    status["left_elbow_angle"]
                    - status["right_elbow_angle"]
                )
                if status.get("left_elbow_angle") is not None
                and status.get("right_elbow_angle") is not None
                else None
            ),
            "last_count_time": self.last_count_time
        }
        status["detection_reason"] = detection_reason
        status["detection_debug"] = runtime_debug
        status["debug"] = {**status.get("debug", {}), **runtime_debug}
        return annotated_frame, status


ShoulderPressAnalyzer = ShoulderPressPoseAnalyzer
