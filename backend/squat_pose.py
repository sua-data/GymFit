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
        self.overlay_min_keypoint_conf = 0.30
        self.min_box_width = 70
        self.min_box_height = 150

        # 연속 프레임 기준
        self.required_frames = 2
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
        self.last_detection_reason = "no-person"
        self.detection_failure_counts = {
            "no-person": 0,
            "bbox-too-small": 0,
            "insufficient-keypoints": 0,
            "required-joints-missing": 0,
        }

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

    def _draw_best_pose_capture(
        self,
        frame,
        pose_overlay,
        knee_angle,
        posture_score,
    ):
        """Annotate a copy of the locked DOWN frame only."""
        capture_frame = frame.copy()
        frame_height, frame_width = capture_frame.shape[:2]
        bbox = pose_overlay["bbox"]
        all_x = [bbox["x1"], bbox["x2"]] + [
            point["x"] for point in pose_overlay["keypoints"]
        ]
        all_y = [bbox["y1"], bbox["y2"]] + [
            point["y"] for point in pose_overlay["keypoints"]
        ]
        content_x1, content_x2 = min(all_x), max(all_x)
        content_y1, content_y2 = min(all_y), max(all_y)
        content_width = max(1.0, content_x2 - content_x1)
        content_height = max(1.0, content_y2 - content_y1)
        margin_x = content_width * 0.12
        margin_y = content_height * 0.12
        crop_x1 = content_x1 - margin_x
        crop_x2 = content_x2 + margin_x
        crop_y1 = content_y1 - margin_y
        crop_y2 = content_y2 + margin_y

        target_aspect_ratio = 16 / 10
        crop_width = crop_x2 - crop_x1
        crop_height = crop_y2 - crop_y1
        if crop_width / crop_height < target_aspect_ratio:
            required_width = crop_height * target_aspect_ratio
            extra = required_width - crop_width
            crop_x1 -= extra / 2
            crop_x2 += extra / 2
        else:
            required_height = crop_width / target_aspect_ratio
            extra = required_height - crop_height
            crop_y1 -= extra / 2
            crop_y2 += extra / 2

        def fit_axis(start, end, limit):
            desired = min(float(limit), end - start)
            if start < 0:
                end -= start
                start = 0
            if end > limit:
                start -= end - limit
                end = float(limit)
            start = max(0.0, start)
            end = min(float(limit), end)
            if end - start < desired:
                if start <= 0:
                    end = min(float(limit), desired)
                else:
                    start = max(0.0, float(limit) - desired)
            return start, end

        crop_x1, crop_x2 = fit_axis(crop_x1, crop_x2, frame_width)
        crop_y1, crop_y2 = fit_axis(crop_y1, crop_y2, frame_height)
        ix1 = max(0, int(math.floor(crop_x1)))
        iy1 = max(0, int(math.floor(crop_y1)))
        ix2 = min(frame_width, int(math.ceil(crop_x2)))
        iy2 = min(frame_height, int(math.ceil(crop_y2)))
        cropped = capture_frame[iy1:iy2, ix1:ix2]
        output_width, output_height = 640, 400
        cropped_width = max(1, ix2 - ix1)
        cropped_height = max(1, iy2 - iy1)
        cropped_ratio = cropped_width / cropped_height
        if abs(cropped_ratio - target_aspect_ratio) <= 0.02:
            capture_frame = cv2.resize(
                cropped,
                (output_width, output_height),
                interpolation=cv2.INTER_AREA,
            )
            scale_x = output_width / cropped_width
            scale_y = output_height / cropped_height
            content_offset_x = 0
            content_offset_y = 0
        else:
            # A portrait source cannot contain a full body in a 16:10 crop
            # without cutting joints. Fill the sides with the same blurred
            # frame while keeping the person layer undistorted.
            background = cv2.resize(
                cropped,
                (output_width, output_height),
                interpolation=cv2.INTER_AREA,
            )
            capture_frame = cv2.GaussianBlur(background, (31, 31), 0)
            uniform_scale = min(
                output_width / cropped_width,
                output_height / cropped_height,
            )
            foreground_width = max(1, int(round(cropped_width * uniform_scale)))
            foreground_height = max(1, int(round(cropped_height * uniform_scale)))
            foreground = cv2.resize(
                cropped,
                (foreground_width, foreground_height),
                interpolation=cv2.INTER_AREA,
            )
            content_offset_x = (output_width - foreground_width) // 2
            content_offset_y = (output_height - foreground_height) // 2
            capture_frame[
                content_offset_y:content_offset_y + foreground_height,
                content_offset_x:content_offset_x + foreground_width,
            ] = foreground
            scale_x = uniform_scale
            scale_y = uniform_scale

        def transform_point(x, y):
            return (
                int(round((x - ix1) * scale_x + content_offset_x)),
                int(round((y - iy1) * scale_y + content_offset_y)),
            )

        points = {
            point["id"]: transform_point(point["x"], point["y"])
            for point in pose_overlay["keypoints"]
        }
        connections = (
            (0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 6),
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
            (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16),
        )
        left_ids = {1, 3, 5, 7, 9, 11, 13, 15}
        right_ids = {2, 4, 6, 8, 10, 12, 14, 16}

        def color_for(start, end=None):
            end = start if end is None else end
            if start in left_ids and end in left_ids:
                return (80, 220, 255)
            if start in right_ids and end in right_ids:
                return (255, 150, 70)
            return (80, 255, 120)

        for start, end in connections:
            if start not in points or end not in points:
                continue
            cv2.line(
                capture_frame,
                points[start],
                points[end],
                color_for(start, end),
                2,
                cv2.LINE_AA,
            )
        for index, point in points.items():
            cv2.circle(
                capture_frame, point, 3, color_for(index), -1, cv2.LINE_AA
            )

        height, width = capture_frame.shape[:2]
        x1, y1 = transform_point(bbox["x1"], bbox["y1"])
        x2, y2 = transform_point(bbox["x2"], bbox["y2"])
        x1 = max(0, min(width - 1, x1))
        y1 = max(0, min(height - 1, y1))
        x2 = max(0, min(width - 1, x2))
        y2 = max(0, min(height - 1, y2))
        cv2.rectangle(capture_frame, (x1, y1), (x2, y2), (168, 255, 53), 1)
        return capture_frame

    def _update_best_pose(
        self,
        frame,
        average_angle,
        torso_angle,
        pose_overlay=None,
    ):
        if not self._is_capture_candidate(average_angle, torso_angle):
            return

        score = self._calculate_posture_score(average_angle, torso_angle)
        if score <= self.best_pose_score:
            return

        if pose_overlay is None or not pose_overlay.get("keypoints"):
            return

        locked_frame = self._draw_best_pose_capture(
            frame,
            pose_overlay,
            average_angle,
            score,
        )
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
            "bbox": copy.deepcopy(pose_overlay["bbox"]),
            "person_confidence": pose_overlay["bbox"].get("confidence"),
            "keypoints": copy.deepcopy(pose_overlay["keypoints"]),
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
        self.last_detection_reason = "no-person"
        if (
            result.boxes is None
            or result.keypoints is None
            or result.keypoints.xy is None
            or len(result.boxes) == 0
        ):
            return None

        largest_index = None
        largest_area = 0
        rejected_small_box = False

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
                rejected_small_box = True
                continue

            if area > largest_area:
                largest_area = area
                largest_index = index

        if largest_index is not None:
            self.last_detection_reason = "selected"
        elif rejected_small_box:
            self.last_detection_reason = "bbox-too-small"
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

    def _build_pose_overlay(
        self,
        result,
        person_index,
        frame_width,
        frame_height,
        left_angle,
        right_angle,
    ):
        """Return validated source-frame coordinates for browser drawing."""
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

        selected_side = (
            "BOTH"
            if left_angle is not None and right_angle is not None
            else "LEFT"
            if left_angle is not None
            else "RIGHT"
            if right_angle is not None
            else None
        )
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
            "selected_side": selected_side,
            "bbox": {
                "x1": round(float(x1), 2),
                "y1": round(float(y1), 2),
                "x2": round(float(x2), 2),
                "y2": round(float(y2), 2),
                "confidence": (
                    round(person_confidence, 3)
                    if person_confidence is not None
                    else None
                ),
            },
        }

    def _build_detection_debug(self, result, person_index, pose_overlay):
        confidences = [
            round(float(value), 3)
            for value in result.keypoints.conf[person_index].tolist()[:17]
        ]
        required = {
            "left_shoulder": confidences[5],
            "right_shoulder": confidences[6],
            "left_hip": confidences[11],
            "right_hip": confidences[12],
            "left_knee": confidences[13],
            "right_knee": confidences[14],
            "left_ankle": confidences[15],
            "right_ankle": confidences[16],
        }
        return {
            "person_confidence": (
                round(float(result.boxes.conf[person_index]), 3)
                if result.boxes.conf is not None
                else None
            ),
            "keypoint_confidences": confidences,
            "analysis_valid_keypoints": sum(
                confidence >= self.min_keypoint_conf
                for confidence in confidences
            ),
            "overlay_valid_keypoints": len(pose_overlay["keypoints"]),
            "required_joint_confidences": required,
            "selected_bbox": pose_overlay["bbox"],
        }

    def _draw_annotated_pose(self, frame, result, person_index):
        """Draw only the selected person's bbox and validated COCO pose."""
        annotated = frame.copy()
        height, width = annotated.shape[:2]
        person = result.keypoints.xy[person_index]
        confidences = result.keypoints.conf[person_index]
        points = {}
        for index in range(min(17, len(person))):
            x, y = person[index].tolist()
            confidence = float(confidences[index])
            if (
                confidence < self.min_keypoint_conf
                or x <= 0
                or y <= 0
                or x >= width
                or y >= height
            ):
                continue
            points[index] = (int(round(x)), int(round(y)))

        connections = (
            (0, 1), (0, 2), (1, 3), (2, 4), (3, 5), (4, 6),
            (5, 6), (5, 7), (7, 9), (6, 8), (8, 10),
            (5, 11), (6, 12), (11, 12),
            (11, 13), (13, 15), (12, 14), (14, 16),
        )
        left_ids = {1, 3, 5, 7, 9, 11, 13, 15}
        right_ids = {2, 4, 6, 8, 10, 12, 14, 16}
        for start, end in connections:
            if start not in points or end not in points:
                continue
            if start in left_ids and end in left_ids:
                color = (80, 220, 255)
            elif start in right_ids and end in right_ids:
                color = (255, 150, 70)
            else:
                color = (80, 255, 120)
            cv2.line(annotated, points[start], points[end], color, 2, cv2.LINE_AA)

        for index, point in points.items():
            color = (
                (80, 220, 255) if index in left_ids
                else (255, 150, 70) if index in right_ids
                else (80, 255, 120)
            )
            cv2.circle(annotated, point, 3, color, -1, cv2.LINE_AA)

        x1, y1, x2, y2 = result.boxes.xyxy[person_index].tolist()
        box_start = (max(0, int(x1)), max(0, int(y1)))
        box_end = (min(width - 1, int(x2)), min(height - 1, int(y2)))
        cv2.rectangle(annotated, box_start, box_end, (168, 255, 53), 1, cv2.LINE_AA)
        box_confidence = (
            float(result.boxes.conf[person_index])
            if result.boxes.conf is not None
            else 0.0
        )
        label_y = max(16, box_start[1] - 6)
        cv2.putText(
            annotated,
            f"person {box_confidence:.2f}",
            (box_start[0], label_y),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (168, 255, 53),
            1,
            cv2.LINE_AA,
        )
        return annotated

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
        pose_overlay=None,
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
                self._update_best_pose(
                    frame,
                    average_angle,
                    torso_angle,
                    pose_overlay,
                )

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
        pose_overlay = None
        detection_debug = None
        detection_reason = "no-person"

        results = self.model(
            frame,
            conf=0.5,
            classes=[0],
            verbose=False,
        )

        annotated_frame = frame.copy()

        for result in results:
            person_index = (
                self._select_largest_person(
                    result
                )
            )

            if person_index is None:
                detection_reason = self.last_detection_reason
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

            pose_overlay = self._build_pose_overlay(
                result,
                person_index,
                frame.shape[1],
                frame.shape[0],
                left_angle,
                right_angle,
            )
            detection_debug = self._build_detection_debug(
                result, person_index, pose_overlay
            )

            break

        angles = []

        if left_angle is not None:
            angles.append(left_angle)

        if right_angle is not None:
            angles.append(right_angle)

        if angles:
            valid_pose = True
            detection_reason = "ok"
            self.missing_frames = 0

            average_angle = (
                sum(angles)
                / len(angles)
            )

            self._update_squat_state(
                average_angle,
                torso_angle,
                frame,
                pose_overlay,
            )

        else:
            if valid_person and detection_debug is not None:
                detection_reason = (
                    "insufficient-keypoints"
                    if detection_debug["analysis_valid_keypoints"] < 6
                    else "required-joints-missing"
                )
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

        if detection_reason in self.detection_failure_counts:
            self.detection_failure_counts[detection_reason] += 1

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
            "pose_overlay": pose_overlay if valid_pose else None,
            "detection_reason": detection_reason,
            "detection_debug": detection_debug,
            "detection_failure_counts": dict(self.detection_failure_counts),
        }

        return annotated_frame, status


def render_pose_capture(frame, pose_overlay):
    """Render the shared 640x400 bbox/skeleton capture without mutating input."""
    return SquatAnalyzer._draw_best_pose_capture(
        None, frame, pose_overlay, None, None
    )
