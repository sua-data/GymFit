import math
from typing import Any

from ultralytics import YOLO


class UpperBodyExerciseAnalyzer:
    """YOLO Pose 기반 상체 운동 분석기의 공통 처리."""

    exercise_code = ""
    display_name = ""

    def __init__(self, model_path: str = "yolo11n-pose.pt"):
        self.model = (
            model_path
            if hasattr(model_path, "predict")
            else YOLO(model_path)
        )
        self.min_keypoint_conf = 0.35
        self.min_box_width = 70
        self.min_box_height = 120
        self.required_frames = 3
        self.max_missing_frames = 15
        self.reset()

    def reset(self):
        self.count = 0
        self.stage = None
        self.feedback = "운동을 준비하세요"
        self.transition_frames = 0
        self.missing_frames = 0
        self.last_posture_score = 0

    @staticmethod
    def calculate_angle(a, b, c):
        radians = math.atan2(
            c[1] - b[1],
            c[0] - b[0],
        ) - math.atan2(
            a[1] - b[1],
            a[0] - b[0],
        )
        angle = abs(math.degrees(radians))
        return 360 - angle if angle > 180 else angle

    def _select_largest_person(self, result):
        if (
            result.boxes is None
            or result.keypoints is None
            or result.keypoints.xy is None
            or len(result.boxes) == 0
        ):
            return None

        largest_index = None
        largest_area = 0
        for index, box in enumerate(result.boxes.xyxy):
            x1, y1, x2, y2 = box.tolist()
            width = x2 - x1
            height = y2 - y1
            area = width * height
            if width < self.min_box_width or height < self.min_box_height:
                continue
            if area > largest_area:
                largest_area = area
                largest_index = index
        return largest_index

    @staticmethod
    def _point(person, index):
        return person[index].tolist()

    @staticmethod
    def _confidence(person_conf, *indexes):
        return min(float(person_conf[index]) for index in indexes)

    def _extract_metrics(self, person, person_conf):
        raise NotImplementedError

    def _update_state(self, metrics):
        raise NotImplementedError

    def process_frame(self, frame) -> tuple[Any, dict]:
        valid_person = False
        valid_pose = False
        metrics = {}

        results = self.model(
            frame,
            conf=0.5,
            classes=[0],
            verbose=False,
        )
        annotated_frame = frame.copy()

        for result in results:
            annotated_frame = result.plot()
            person_index = self._select_largest_person(result)
            if person_index is None:
                continue

            valid_person = True
            keypoints_conf = result.keypoints.conf
            if keypoints_conf is None:
                break

            metrics = self._extract_metrics(
                result.keypoints.xy[person_index],
                keypoints_conf[person_index],
            )
            valid_pose = bool(metrics.get("pose_valid"))
            break

        if valid_pose:
            self.missing_frames = 0
            self._update_state(metrics)
        else:
            self.missing_frames += 1
            if self.missing_frames > self.max_missing_frames:
                self.transition_frames = 0
                self.feedback = self.missing_feedback

        if valid_pose:
            status_text = "자세 인식 중"
        elif valid_person:
            status_text = "사람 감지 / 관절 인식 불안정"
        else:
            status_text = "사람을 찾을 수 없습니다"

        return annotated_frame, {
            "exercise_code": self.exercise_code,
            "count": self.count,
            "stage": self.stage,
            "stage_text": self.stage_text,
            "feedback": self.feedback,
            "posture_score": self.last_posture_score,
            "pose_valid": valid_pose,
            "person_valid": valid_person,
            "landmarks_detected": valid_pose,
            "status_text": status_text,
            **{
                key: round(value, 1) if isinstance(value, float) else value
                for key, value in metrics.items()
                if key != "pose_valid"
            },
        }


class PushUpAnalyzer(UpperBodyExerciseAnalyzer):
    exercise_code = "PUSHUP"
    display_name = "푸시업"
    missing_feedback = "전신이 화면에 나오도록 위치를 조정하세요"

    def __init__(self, model_path: str = "yolo11n-pose.pt"):
        self.down_angle = 90
        self.up_angle = 160
        self.body_warning_angle = 25
        super().__init__(model_path)

    @property
    def stage_text(self):
        return "내려감" if self.stage == "DOWN" else "올라옴"

    def _extract_metrics(self, person, person_conf):
        sides = []
        for shoulder_index, elbow_index, wrist_index, hip_index, ankle_index in (
            (5, 7, 9, 11, 15),
            (6, 8, 10, 12, 16),
        ):
            confidence = self._confidence(
                person_conf,
                shoulder_index,
                elbow_index,
                wrist_index,
                hip_index,
                ankle_index,
            )
            if confidence < self.min_keypoint_conf:
                continue

            shoulder = self._point(person, shoulder_index)
            elbow = self._point(person, elbow_index)
            wrist = self._point(person, wrist_index)
            hip = self._point(person, hip_index)
            ankle = self._point(person, ankle_index)
            sides.append({
                "confidence": confidence,
                "elbow_angle": self.calculate_angle(shoulder, elbow, wrist),
                "body_angle": abs(180 - self.calculate_angle(shoulder, hip, ankle)),
            })

        if not sides:
            return {"pose_valid": False}

        best_side = max(sides, key=lambda side: side["confidence"])
        return {
            "pose_valid": True,
            "elbow_angle": best_side["elbow_angle"],
            "body_alignment_error": best_side["body_angle"],
        }

    def _update_state(self, metrics):
        elbow_angle = metrics["elbow_angle"]
        body_error = metrics["body_alignment_error"]

        if body_error >= self.body_warning_angle:
            self.feedback = "허리와 엉덩이를 일직선으로 유지하세요"
            score = 65
        elif elbow_angle > self.down_angle and self.stage != "DOWN":
            self.feedback = "팔을 더 굽혀주세요"
            score = 82
        elif self.stage == "DOWN" and elbow_angle < self.up_angle:
            self.feedback = "팔을 끝까지 펴주세요"
            score = 85
        else:
            self.feedback = "좋은 자세입니다"
            score = 95
        self.last_posture_score = max(0, min(100, score))

        target_stage = None
        if elbow_angle <= self.down_angle:
            target_stage = "DOWN"
        elif elbow_angle >= self.up_angle:
            target_stage = "UP"

        if target_stage is None or target_stage == self.stage:
            self.transition_frames = 0
            return

        self.transition_frames += 1
        if self.transition_frames < self.required_frames:
            return

        if target_stage == "DOWN":
            self.stage = "DOWN"
        elif target_stage == "UP" and self.stage == "DOWN":
            self.stage = "UP"
            self.count += 1
            self.feedback = "좋은 푸시업입니다"
        else:
            self.stage = "UP"
        self.transition_frames = 0


class ShoulderPressAnalyzer(UpperBodyExerciseAnalyzer):
    exercise_code = "SHOULDER_PRESS"
    display_name = "숄더프레스"
    missing_feedback = "상체와 양팔이 화면에 보이도록 위치를 조정하세요"

    def __init__(self, model_path: str = "yolo11n-pose.pt"):
        self.up_elbow_angle = 155
        self.down_elbow_angle = 110
        self.wrist_above_margin = 0.03
        self.wrist_balance_tolerance = 0.09
        self.torso_warning_angle = 25
        super().__init__(model_path)

    @property
    def stage_text(self):
        return "머리 위" if self.stage == "UP" else "어깨 높이"

    def _extract_metrics(self, person, person_conf):
        required_indexes = (5, 6, 7, 8, 9, 10, 11, 12)
        if self._confidence(person_conf, *required_indexes) < self.min_keypoint_conf:
            return {"pose_valid": False}

        left_shoulder = self._point(person, 5)
        right_shoulder = self._point(person, 6)
        left_elbow = self._point(person, 7)
        right_elbow = self._point(person, 8)
        left_wrist = self._point(person, 9)
        right_wrist = self._point(person, 10)
        left_hip = self._point(person, 11)
        right_hip = self._point(person, 12)

        left_angle = self.calculate_angle(left_shoulder, left_elbow, left_wrist)
        right_angle = self.calculate_angle(right_shoulder, right_elbow, right_wrist)
        shoulder_width = max(
            1.0,
            abs(right_shoulder[0] - left_shoulder[0]),
        )
        wrist_balance = abs(left_wrist[1] - right_wrist[1]) / shoulder_width
        shoulder_y = (left_shoulder[1] + right_shoulder[1]) / 2
        wrist_y = (left_wrist[1] + right_wrist[1]) / 2
        torso_angle = (
            abs(90 - math.degrees(math.atan2(
                ((left_hip[1] + right_hip[1]) / 2) - shoulder_y,
                ((left_hip[0] + right_hip[0]) / 2)
                - ((left_shoulder[0] + right_shoulder[0]) / 2),
            )))
        )

        return {
            "pose_valid": True,
            "left_elbow_angle": left_angle,
            "right_elbow_angle": right_angle,
            "average_elbow_angle": (left_angle + right_angle) / 2,
            "wrists_above_shoulders": wrist_y < shoulder_y - (
                shoulder_width * self.wrist_above_margin
            ),
            "wrist_balance_error": wrist_balance,
            "torso_angle": torso_angle,
        }

    def _update_state(self, metrics):
        elbow_angle = metrics["average_elbow_angle"]
        wrists_above = metrics["wrists_above_shoulders"]
        wrist_balance = metrics["wrist_balance_error"]
        torso_angle = metrics["torso_angle"]

        if wrist_balance > self.wrist_balance_tolerance:
            self.feedback = "양팔을 같은 높이로 움직여주세요"
            score = 70
        elif torso_angle > self.torso_warning_angle:
            self.feedback = "허리를 과하게 젖히지 마세요"
            score = 70
        elif self.stage != "UP" and not wrists_above:
            self.feedback = "팔을 머리 위로 더 올려주세요"
            score = 82
        elif self.stage != "UP" and elbow_angle < self.up_elbow_angle:
            self.feedback = "팔을 완전히 펴주세요"
            score = 85
        elif self.stage == "UP" and elbow_angle > self.down_elbow_angle:
            self.feedback = "팔꿈치를 어깨 높이까지 내려주세요"
            score = 84
        else:
            self.feedback = "좋은 자세입니다"
            score = 95
        self.last_posture_score = max(0, min(100, score))

        target_stage = None
        if wrists_above and elbow_angle >= self.up_elbow_angle:
            target_stage = "UP"
        elif elbow_angle <= self.down_elbow_angle:
            target_stage = "DOWN"

        if target_stage is None or target_stage == self.stage:
            self.transition_frames = 0
            return

        self.transition_frames += 1
        if self.transition_frames < self.required_frames:
            return

        if target_stage == "UP" and self.stage == "DOWN":
            self.stage = "UP"
        elif target_stage == "DOWN" and self.stage == "UP":
            self.stage = "DOWN"
            self.count += 1
            self.feedback = "좋은 숄더프레스입니다"
        else:
            self.stage = target_stage
        self.transition_frames = 0
