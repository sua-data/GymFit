import base64
import copy
import hashlib
import math
import os
from pathlib import Path
from typing import Any

import cv2
from ultralytics import YOLO


class SquatAnalyzer:
    """YOLO Pose 기반 스쿼트 분석기."""

    def __init__(
        self,
        model_path: str = "yolo11n-pose.pt",
    ):
        self.model = YOLO(model_path)

        # 카운트 기준
        self.down_angle = 110
        self.up_angle = 155

        # 자세 깊이 기준
        self.deep_angle = 100
        self.good_angle = 110
        self.guide_angle = 135

        # 상체 기울기 기준
        # 수직선 기준 각도이므로 값이 클수록 상체가 많이 숙여진 상태
        self.torso_warning_angle = 45
        self.torso_check_angle = 35

        # 감지 기준
        self.min_keypoint_conf = 0.35
        self.min_box_width = 70
        self.min_box_height = 150

        # 연속 프레임 기준
        self.required_frames = 3
        self.max_missing_frames = 15

        self.reset()

    def reset(self):
        """운동 상태를 초기화합니다."""
        self.squat_count = 0
        self.stage = "UP"
        self.feedback = "운동을 준비하세요"

        self.current_min_angle = 180
        self.last_squat_depth = None

        self.current_max_torso_angle = 0
        self.last_torso_angle = None

        self.down_frames = 0
        self.up_frames = 0
        self.missing_frames = 0

        self._reset_best_pose()
        self._completed_pose_capture = None

    def _reset_best_pose(self):
        """Clear frame-level state that must never leak into another repetition."""
        self.best_pose_snapshot = None
        self.best_pose_score = -1
        self.best_pose_frame = None
        self.best_pose_angle = None
        self.best_pose_feedback = None
        self.best_pose_torso_angle = None

    def _calculate_posture_score(self, average_angle, torso_angle):
        """Use the squat scoring rules already exposed by the coaching API."""
        score = 70
        if average_angle < self.deep_angle:
            score = 95
        else:
            # Candidates are already limited to good_angle or deeper.
            score = 90

        if torso_angle >= self.torso_warning_angle:
            score -= 20
        elif torso_angle >= self.torso_check_angle:
            score -= 10
        return max(0, min(100, score))

    def _is_capture_candidate(self, average_angle, torso_angle):
        minimum_angle = self.deep_angle - 10
        return (
            self.stage == "DOWN"
            and self.down_frames >= self.required_frames
            and minimum_angle <= average_angle <= self.good_angle
            and torso_angle is not None
        )

    def _debug_best_pose_candidate(self, snapshot):
        if os.getenv("POSE_DEBUG", "").strip().lower() not in {
            "1", "true", "yes", "on"
        }:
            return

        debug_dir = Path(__file__).resolve().parents[1] / "results" / "pose_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        filename = (
            f"squat_{self.squat_count + 1}_df{self.down_frames}_"
            f"angle{snapshot['knee_angle']:.1f}_{snapshot['image_hash']}.jpg"
        )
        jpeg_bytes = base64.b64decode(snapshot["image"].split(",", 1)[1])
        debug_path = debug_dir / filename
        try:
            debug_path.write_bytes(jpeg_bytes)
            saved_path = str(debug_path)
        except OSError:
            saved_path = None
        print({
            "event": "capture locked",
            "stage": snapshot["stage"],
            "down_frames": self.down_frames,
            "up_frames": self.up_frames,
            "angle": snapshot["knee_angle"],
            "score": snapshot["score"],
            "image_hash": snapshot["image_hash"],
            "debug_file": saved_path,
        })

    def _update_best_pose(self, frame, average_angle, torso_angle):
        if not self._is_capture_candidate(average_angle, torso_angle):
            return

        score = self._calculate_posture_score(average_angle, torso_angle)
        if score <= self.best_pose_score:
            return

        locked_frame = frame.copy()
        encoded, jpeg_buffer = cv2.imencode(
            ".jpg", locked_frame, [cv2.IMWRITE_JPEG_QUALITY, 82]
        )
        if not encoded:
            return
        jpeg_bytes = jpeg_buffer.tobytes()
        image = (
            "data:image/jpeg;base64,"
            + base64.b64encode(jpeg_bytes).decode("ascii")
        )
        image_hash = hashlib.sha256(jpeg_bytes).hexdigest()[:16]
        snapshot = {
            "image": image,
            "image_hash": image_hash,
            "score": float(score),
            "knee_angle": float(average_angle),
            "torso_angle": float(torso_angle),
            "feedback": self.feedback,
            "stage": self.stage,
        }
        self.best_pose_snapshot = snapshot
        self.best_pose_score = snapshot["score"]
        self.best_pose_frame = None
        self.best_pose_angle = snapshot["knee_angle"]
        self.best_pose_torso_angle = snapshot["torso_angle"]
        self.best_pose_feedback = snapshot["feedback"]
        self._debug_best_pose_candidate(snapshot)

    def get_completed_pose_capture(self):
        """Expose the already encoded DOWN capture for the API response."""
        return self._completed_pose_capture

    def clear_completed_pose_capture(self):
        """Release completed and active state after response serialization."""
        self._completed_pose_capture = None
        self._reset_best_pose()

    @staticmethod
    def calculate_angle(a, b, c):
        """세 점 a-b-c에서 b를 중심으로 각도를 계산합니다."""
        radians = math.atan2(
            c[1] - b[1],
            c[0] - b[0],
        ) - math.atan2(
            a[1] - b[1],
            a[0] - b[0],
        )

        angle = abs(math.degrees(radians))

        if angle > 180:
            angle = 360 - angle

        return angle

    @staticmethod
    def calculate_torso_angle(
        shoulder,
        hip,
    ):
        """
        어깨-엉덩이 선과 수직선 사이의 각도를 계산합니다.

        0도에 가까울수록 상체가 수직에 가깝고,
        값이 클수록 앞으로 또는 뒤로 많이 기울어진 상태입니다.
        """
        delta_x = shoulder[0] - hip[0]
        delta_y = hip[1] - shoulder[1]

        if delta_y == 0:
            return 90.0

        angle = abs(
            math.degrees(
                math.atan2(
                    delta_x,
                    delta_y,
                )
            )
        )

        return angle

    def _select_largest_person(
        self,
        result,
    ):
        """화면에서 가장 큰 사람의 인덱스를 반환합니다."""
        if (
            result.boxes is None
            or result.keypoints is None
            or result.keypoints.xy is None
            or len(result.boxes) == 0
        ):
            return None

        largest_index = None
        largest_area = 0

        for index, box in enumerate(
            result.boxes.xyxy
        ):
            x1, y1, x2, y2 = box.tolist()

            width = x2 - x1
            height = y2 - y1
            area = width * height

            if (
                width < self.min_box_width
                or height < self.min_box_height
            ):
                continue

            if area > largest_area:
                largest_area = area
                largest_index = index

        return largest_index

    def _extract_pose_data(
        self,
        result,
        person_index,
    ):
        """
        선택한 사람의 무릎 각도와
        상체 기울기를 반환합니다.
        """
        keypoints_xy = result.keypoints.xy
        keypoints_conf = result.keypoints.conf

        if keypoints_conf is None:
            return None, None, None

        person = keypoints_xy[person_index]
        person_conf = keypoints_conf[
            person_index
        ]

        # COCO Pose 관절 번호
        # 왼쪽 어깨 5 / 오른쪽 어깨 6
        # 왼쪽 엉덩이 11 / 오른쪽 엉덩이 12
        # 왼쪽 무릎 13 / 오른쪽 무릎 14
        # 왼쪽 발목 15 / 오른쪽 발목 16

        left_shoulder = person[5].tolist()
        right_shoulder = person[6].tolist()

        left_hip = person[11].tolist()
        right_hip = person[12].tolist()

        left_knee = person[13].tolist()
        right_knee = person[14].tolist()

        left_ankle = person[15].tolist()
        right_ankle = person[16].tolist()

        left_leg_confidence = min(
            float(person_conf[11]),
            float(person_conf[13]),
            float(person_conf[15]),
        )

        right_leg_confidence = min(
            float(person_conf[12]),
            float(person_conf[14]),
            float(person_conf[16]),
        )

        left_torso_confidence = min(
            float(person_conf[5]),
            float(person_conf[11]),
        )

        right_torso_confidence = min(
            float(person_conf[6]),
            float(person_conf[12]),
        )

        left_angle = None
        right_angle = None
        torso_angle = None

        if (
            left_leg_confidence
            >= self.min_keypoint_conf
        ):
            left_angle = self.calculate_angle(
                left_hip,
                left_knee,
                left_ankle,
            )

        if (
            right_leg_confidence
            >= self.min_keypoint_conf
        ):
            right_angle = self.calculate_angle(
                right_hip,
                right_knee,
                right_ankle,
            )

        torso_angles = []

        if (
            left_torso_confidence
            >= self.min_keypoint_conf
        ):
            torso_angles.append(
                self.calculate_torso_angle(
                    left_shoulder,
                    left_hip,
                )
            )

        if (
            right_torso_confidence
            >= self.min_keypoint_conf
        ):
            torso_angles.append(
                self.calculate_torso_angle(
                    right_shoulder,
                    right_hip,
                )
            )

        if torso_angles:
            torso_angle = (
                sum(torso_angles)
                / len(torso_angles)
            )

        return (
            left_angle,
            right_angle,
            torso_angle,
        )

    def _update_feedback(
        self,
        average_angle,
        torso_angle,
    ):
        """현재 깊이와 상체 기울기에 따라 피드백을 갱신합니다."""

        # 상체가 과도하게 숙여진 경우 우선 안내
        if (
            torso_angle is not None
            and torso_angle
            >= self.torso_warning_angle
            and average_angle
            < self.guide_angle
        ):
            self.feedback = (
                "상체가 너무 숙여졌어요. "
                "가슴을 조금 더 들어주세요"
            )
            return

        if (
            torso_angle is not None
            and torso_angle
            >= self.torso_check_angle
            and average_angle
            < self.guide_angle
        ):
            self.feedback = (
                "상체를 조금 더 세워주세요"
            )
            return

        # 깊이 피드백
        if average_angle < self.deep_angle:
            self.feedback = (
                "아주 좋은 깊이입니다"
            )

        elif average_angle < self.good_angle:
            self.feedback = (
                "좋은 자세입니다"
            )

        elif average_angle < self.guide_angle:
            self.feedback = (
                "조금 더 내려가세요"
            )

        elif self.stage == "UP":
            self.feedback = (
                "천천히 내려가세요"
            )

    def _update_squat_state(
        self,
        average_angle,
        torso_angle,
        frame,
    ):
        """스쿼트 상태와 카운트를 갱신합니다."""

        if (
            self.stage == "UP"
            and average_angle < self.down_angle
            and self.down_frames == 0
        ):
            # First confirmed frame of a new descent/attempt.
            self._reset_best_pose()

        if (
            average_angle
            < self.current_min_angle
        ):
            self.current_min_angle = (
                average_angle
            )

        if (
            torso_angle is not None
            and torso_angle
            > self.current_max_torso_angle
        ):
            self.current_max_torso_angle = (
                torso_angle
            )

        self._update_feedback(
            average_angle,
            torso_angle,
        )

        # DOWN 상태 확인
        if average_angle < self.down_angle:
            self.down_frames += 1
            self.up_frames = 0

            if (
                self.down_frames
                >= self.required_frames
            ):
                self.stage = "DOWN"

            if (
                self.stage == "DOWN"
                and self.down_frames >= self.required_frames
            ):
                self._update_best_pose(frame, average_angle, torso_angle)

        # UP 상태 확인
        elif average_angle > self.up_angle:
            self.up_frames += 1
            self.down_frames = 0

            if (
                self.stage == "DOWN"
                and self.up_frames
                >= self.required_frames
            ):
                self.squat_count += 1
                self.stage = "UP"
                self.up_frames = 0

                self.last_squat_depth = (
                    self.current_min_angle
                )

                self.last_torso_angle = (
                    self.current_max_torso_angle
                )

                self._set_completed_feedback()

                snapshot = self.best_pose_snapshot
                minimum_angle = self.deep_angle - 10
                snapshot_valid = (
                    snapshot is not None
                    and snapshot["stage"] == "DOWN"
                    and minimum_angle
                    <= snapshot["knee_angle"]
                    <= self.good_angle
                )
                if snapshot_valid:
                    self._completed_pose_capture = copy.deepcopy(snapshot)
                    if os.getenv("POSE_DEBUG", "").strip().lower() in {
                        "1", "true", "yes", "on"
                    }:
                        print({
                            "event": "repetition completed",
                            "stage": self.stage,
                            "using_locked_capture": True,
                            "locked_angle": snapshot["knee_angle"],
                            "locked_hash": snapshot["image_hash"],
                        })
                else:
                    if os.getenv("POSE_DEBUG", "").strip().lower() in {
                        "1", "true", "yes", "on"
                    }:
                        print({
                            "event": "invalid-best-pose-at-completion",
                            "count": self.squat_count,
                            "stage": snapshot.get("stage") if snapshot else None,
                            "knee_angle": (
                                snapshot.get("knee_angle") if snapshot else None
                            ),
                            "score": snapshot.get("score") if snapshot else None,
                            "fallback_reason": "no-valid-down-pose",
                        })
                    self._reset_best_pose()

                self.current_min_angle = 180
                self.current_max_torso_angle = 0

            elif self.up_frames >= self.required_frames:
                # A descent that never became DOWN is not a repetition.
                self._reset_best_pose()

        else:
            self.down_frames = 0
            self.up_frames = 0

    def _set_completed_feedback(self):
        """완료된 스쿼트 1회의 최종 피드백을 설정합니다."""

        if (
            self.last_torso_angle is not None
            and self.last_torso_angle
            >= self.torso_warning_angle
        ):
            self.feedback = (
                "상체가 많이 숙여졌어요. "
                "다음에는 가슴을 더 들어주세요"
            )
            return

        if (
            self.last_torso_angle is not None
            and self.last_torso_angle
            >= self.torso_check_angle
        ):
            self.feedback = (
                "깊이는 좋았어요. "
                "상체를 조금 더 세워보세요"
            )
            return

        if (
            self.last_squat_depth
            < self.deep_angle
        ):
            self.feedback = (
                "아주 좋은 스쿼트입니다"
            )

        elif (
            self.last_squat_depth
            < self.good_angle
        ):
            self.feedback = (
                "좋은 스쿼트입니다"
            )

        else:
            self.feedback = (
                "다음에는 조금 더 내려가세요"
            )

    def process_frame(
        self,
        frame,
    ) -> tuple[Any, dict]:
        """
        프레임을 분석합니다.

        반환:
            annotated_frame: 관절이 표시된 프레임
            status: 카운트와 피드백 데이터
        """
        left_angle = None
        right_angle = None
        average_angle = None
        torso_angle = None
        count_before_frame = self.squat_count

        valid_person = False
        valid_pose = False

        results = self.model(
            frame,
            conf=0.5,
            classes=[0],
            verbose=False,
        )

        annotated_frame = frame.copy()

        for result in results:
            annotated_frame = result.plot()

            person_index = (
                self._select_largest_person(
                    result
                )
            )

            if person_index is None:
                continue

            valid_person = True

            (
                left_angle,
                right_angle,
                torso_angle,
            ) = self._extract_pose_data(
                result,
                person_index,
            )

            break

        angles = []

        if left_angle is not None:
            angles.append(left_angle)

        if right_angle is not None:
            angles.append(right_angle)

        if angles:
            valid_pose = True
            self.missing_frames = 0

            average_angle = (
                sum(angles)
                / len(angles)
            )

            self._update_squat_state(
                average_angle,
                torso_angle,
                frame,
            )

        else:
            self.missing_frames += 1

            if (
                self.missing_frames
                > self.max_missing_frames
            ):
                self.down_frames = 0
                self.up_frames = 0
                self._reset_best_pose()

                self.feedback = (
                    "전신이 화면에 나오도록 이동하세요"
                )

        if valid_pose:
            status_text = "자세 인식 중"

        elif valid_person:
            status_text = (
                "사람 감지 / 다리 인식 불안정"
            )

        else:
            status_text = (
                "사람을 찾을 수 없습니다"
            )

        torso_status = None

        if torso_angle is not None:
            if (
                torso_angle
                >= self.torso_warning_angle
            ):
                torso_status = "WARNING"

            elif (
                torso_angle
                >= self.torso_check_angle
            ):
                torso_status = "CHECK"

            else:
                torso_status = "GOOD"

        status = {
            "count": self.squat_count,
            "stage": self.stage,
            "stage_text": (
                "내려감"
                if self.stage == "DOWN"
                else "일어섬"
            ),
            "left_angle": (
                round(left_angle, 1)
                if left_angle is not None
                else None
            ),
            "right_angle": (
                round(right_angle, 1)
                if right_angle is not None
                else None
            ),
            "average_angle": (
                round(average_angle, 1)
                if average_angle is not None
                else None
            ),
            "torso_angle": (
                round(torso_angle, 1)
                if torso_angle is not None
                else None
            ),
            "torso_status": torso_status,
            "last_depth": (
                round(
                    self.last_squat_depth,
                    1,
                )
                if self.last_squat_depth
                is not None
                else None
            ),
            "last_torso_angle": (
                round(
                    self.last_torso_angle,
                    1,
                )
                if self.last_torso_angle
                is not None
                else None
            ),
            "feedback": self.feedback,
            "pose_valid": valid_pose,
            "person_valid": valid_person,
            "status_text": status_text,
            "repetition_completed": self.squat_count > count_before_frame,
        }

        return annotated_frame, status
