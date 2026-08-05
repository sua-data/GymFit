import base64
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np

import backend.exercise_pose as exercise_pose
import backend.pose_factory as pose_factory
import backend.pushup_pose as pushup_pose
from backend.pushup_pose import PUSHUP_CONFIG, PushUpAnalyzer


class FakePoseModel:
    def predict(self, *_args, **_kwargs):
        return []

    def __call__(self, *_args, **_kwargs):
        return []


class FakeBoxes:
    def __init__(self, xyxy, confidence):
        self.xyxy = np.asarray(xyxy, dtype=float)
        self.conf = np.asarray(confidence, dtype=float)

    def __len__(self):
        return len(self.xyxy)


class FakeResult:
    def __init__(self, coordinates, confidences):
        self.keypoints = SimpleNamespace(
            xy=np.asarray([coordinates], dtype=float),
            conf=np.asarray([confidences], dtype=float),
        )
        self.boxes = FakeBoxes([[5, 5, 155, 195]], [0.91])

    def plot(self):
        return np.zeros((200, 160, 3), dtype=np.uint8)


class ResultPoseModel(FakePoseModel):
    def __init__(self, result):
        self.result = result

    def __call__(self, *_args, **_kwargs):
        return [self.result]


def make_pushup_analyzer():
    return PushUpAnalyzer(FakePoseModel())


def accept_frames(analyzer, stage):
    for _ in range(analyzer.required_frames):
        analyzer._accept_stable_stage(stage)


def pushup_metrics(elbow_angle, *, side="LEFT", hip_offset=0.0, body_angle=178.0):
    return {
        "pose_valid": True,
        "selected_side": side,
        "analyzed_side": side,
        "elbow_angle": float(elbow_angle),
        "body_angle": float(body_angle),
        "body_alignment_angle": float(body_angle),
        "body_alignment_error": abs(180.0 - body_angle),
        "hip_line_offset": float(hip_offset),
        "required_joint_confidence": 0.9,
        "arm_available": True,
        "count_available": True,
        "arm_fresh": True,
        "arm_confidence": 0.9,
        "alignment_available": True,
        "alignment_fresh": True,
        "alignment_confidence": 0.9,
        "analysis_quality": "FULL",
    }


def pose_overlay(width=160, height=100):
    return {
        "source_width": width,
        "source_height": height,
        "selected_side": "LEFT",
        "bbox": {
            "x1": 8.0,
            "y1": 12.0,
            "x2": width - 8.0,
            "y2": height - 12.0,
            "confidence": 0.91,
        },
        "keypoints": [
            {
                "id": index,
                "x": float(12 + index * 7),
                "y": float(25 + (index % 4) * 12),
                "confidence": 0.9,
            }
            for index in range(17)
        ],
    }


def update_frames(analyzer, metrics, frame, overlay, count):
    for _ in range(count):
        analyzer._update_state(dict(metrics), frame, overlay)


def test_pushup_module_preserves_configuration_and_reset_state():
    analyzer = make_pushup_analyzer()

    assert analyzer.exercise_code == "PUSHUP"
    assert PUSHUP_CONFIG["down_elbow_angle"] == 90.0
    assert PUSHUP_CONFIG["up_elbow_angle"] == 155.0
    assert analyzer.model_detection_conf == 0.25
    assert analyzer.min_keypoint_conf == 0.35
    assert analyzer.overlay_min_keypoint_conf == 0.30
    assert analyzer.required_frames == 3

    analyzer.count = 4
    analyzer.stage = "DOWN"
    analyzer.completed_down_phase = True
    analyzer.reset()

    assert analyzer.count == 0
    assert analyzer.stage == "UNKNOWN"
    assert analyzer.completed_down_phase is False
    assert analyzer.transition_frames == 0
    assert analyzer.missing_frames == 0


def test_pushup_stable_up_down_up_cycle_counts_once():
    analyzer = make_pushup_analyzer()

    accept_frames(analyzer, "UP")
    assert analyzer.count == 0
    accept_frames(analyzer, "DOWN")
    assert analyzer.completed_down_phase is True
    accept_frames(analyzer, "UP")

    assert analyzer.count == 1
    assert analyzer.stage == "UP"
    assert analyzer.last_counted is True
    assert analyzer.feedback == "좋은 푸시업입니다"


def test_pushup_overlay_contains_bbox_and_coco_keypoints():
    analyzer = make_pushup_analyzer()
    coordinates = np.full((1, 17, 2), 30.0, dtype=float)
    confidences = np.full((1, 17), 0.31, dtype=float)
    result = SimpleNamespace(
        keypoints=SimpleNamespace(xy=coordinates, conf=confidences),
        boxes=SimpleNamespace(
            xyxy=np.array([[5, 5, 155, 95]], dtype=float),
            conf=np.array([0.88], dtype=float),
        ),
    )

    overlay = analyzer._build_pose_overlay(result, 0, 160, 100)

    assert overlay["source_width"] == 160
    assert overlay["source_height"] == 100
    assert overlay["bbox"]["confidence"] == 0.88
    assert len(overlay["keypoints"]) == 17
    assert analyzer.min_keypoint_conf == 0.35
    assert analyzer.overlay_min_keypoint_conf == 0.30


def test_pushup_process_response_exposes_common_overlay_and_pushup_fields():
    coordinates = np.array(
        [(20 + index * 5, 30 + (index % 4) * 20) for index in range(17)],
        dtype=float,
    )
    coordinates[[5, 7, 9]] = [(25, 40), (45, 40), (65, 40)]
    coordinates[[11, 15]] = [(75, 70), (135, 75)]
    coordinates[[6, 8, 10]] = [(25, 100), (45, 100), (65, 100)]
    coordinates[[12, 16]] = [(75, 130), (135, 135)]
    confidences = np.full(17, 0.9, dtype=float)
    analyzer = PushUpAnalyzer(ResultPoseModel(FakeResult(coordinates, confidences)))

    _, status = analyzer.process_frame(np.zeros((200, 160, 3), dtype=np.uint8))

    assert status["person_detected"] is True
    assert status["pose_detected"] is True
    assert status["source_width"] == 160
    assert status["source_height"] == 200
    assert status["bbox"]["confidence"] == 0.91
    assert len(status["keypoints"]) == 17
    assert status["analyzed_side"] in {"LEFT", "RIGHT"}
    assert status["pose_overlay"]["selected_side"] == status["analyzed_side"]
    assert status["elbow_angle"] is not None
    assert status["body_alignment_angle"] is not None
    assert status["depth_status"] in {"UP", "DOWN", "TRANSITION"}


def test_missing_hips_and_ankles_still_leave_arm_count_available():
    coordinates = np.array(
        [(20 + index * 5, 30 + (index % 4) * 20) for index in range(17)],
        dtype=float,
    )
    coordinates[[5, 7, 9]] = [(25, 40), (45, 40), (65, 40)]
    coordinates[[6, 8, 10]] = [(25, 100), (45, 100), (65, 100)]
    confidences = np.full(17, 0.9, dtype=float)
    confidences[[11, 12, 15, 16]] = 0.1
    analyzer = PushUpAnalyzer(ResultPoseModel(FakeResult(coordinates, confidences)))

    _, status = analyzer.process_frame(np.zeros((200, 160, 3), dtype=np.uint8))

    assert status["count_available"] is True
    assert status["alignment_available"] is False
    assert status["analysis_quality"] == "PARTIAL"
    assert status["body_alignment_angle"] is None
    assert "body_alignment" in status["unavailable_metrics"]


def test_pushup_keeps_valid_analyzed_side_until_it_becomes_invalid():
    analyzer = make_pushup_analyzer()
    person = np.zeros((17, 2), dtype=float)
    confidence = np.full(17, 0.9, dtype=float)
    person[5], person[7], person[9] = (10, 10), (20, 10), (30, 10)
    person[11], person[15] = (30, 30), (60, 30)
    person[6], person[8], person[10] = (10, 50), (20, 50), (30, 50)
    person[12], person[16] = (30, 70), (60, 70)

    analyzer.analyzed_side = "LEFT"
    confidence[[6, 8, 10, 12, 16]] = 0.99
    assert analyzer._extract_metrics(person, confidence)["analyzed_side"] == "LEFT"

    confidence[5] = 0.2
    analyzer._frame_sequence += 3
    analyzer._frame_timestamp_ms += 300
    assert analyzer._extract_metrics(person, confidence)["analyzed_side"] == "RIGHT"


def test_pushup_counts_with_arm_when_alignment_joints_are_missing():
    analyzer = make_pushup_analyzer()
    partial_up = pushup_metrics(170)
    partial_up.update({
        "alignment_available": False,
        "alignment_fresh": False,
        "alignment_confidence": None,
        "body_alignment_angle": None,
        "body_alignment_error": None,
        "hip_line_offset": None,
        "analysis_quality": "PARTIAL",
    })
    partial_down = {**partial_up, "elbow_angle": 85.0}

    update_frames(analyzer, partial_up, None, None, 3)
    update_frames(analyzer, partial_down, None, None, 3)
    update_frames(analyzer, partial_up, None, None, 3)

    assert analyzer.count == 1
    assert analyzer.last_posture_score < 92
    assert partial_up["alignment_available"] is False


def test_stale_arm_coordinates_hold_stage_but_cannot_complete_transition():
    analyzer = make_pushup_analyzer()
    update_frames(analyzer, pushup_metrics(170), None, None, 3)
    update_frames(analyzer, pushup_metrics(85), None, None, 3)
    assert analyzer.stage == "DOWN"

    stale_up = pushup_metrics(170)
    stale_up.update({
        "arm_fresh": False,
        "count_available": False,
        "analysis_quality": "LIMITED",
    })
    update_frames(analyzer, stale_up, None, None, 2)

    assert analyzer.stage == "DOWN"
    assert analyzer.count == 0

    update_frames(analyzer, pushup_metrics(170), None, None, 3)
    assert analyzer.stage == "UP"
    assert analyzer.count == 1


def test_joint_cache_expires_after_two_frames_or_250ms():
    analyzer = make_pushup_analyzer()
    analyzer._frame_width = 200
    analyzer._frame_height = 200
    person = np.array(
        [(20 + index * 5, 30 + (index % 4) * 20) for index in range(17)],
        dtype=float,
    )
    confidence = np.full(17, 0.9, dtype=float)
    analyzer._frame_sequence = 1
    analyzer._frame_timestamp_ms = 1000
    assert analyzer._extract_metrics(person, confidence)["count_available"] is True

    occluded = confidence.copy()
    occluded[[5, 6, 7, 8, 9, 10]] = 0.1
    analyzer._frame_sequence = 2
    analyzer._frame_timestamp_ms = 1100
    stale = analyzer._extract_metrics(person, occluded)
    assert stale["arm_available"] is True
    assert stale["count_available"] is False
    assert stale["stale_joints"]

    analyzer._frame_sequence = 4
    analyzer._frame_timestamp_ms = 1300
    expired = analyzer._extract_metrics(person, occluded)
    assert expired["arm_available"] is False


def test_partial_score_reports_evaluated_and_unavailable_metrics():
    analyzer = make_pushup_analyzer()
    metrics = pushup_metrics(85)
    metrics.update({
        "alignment_available": False,
        "alignment_fresh": False,
        "alignment_confidence": None,
        "body_alignment_angle": None,
        "body_alignment_error": None,
        "hip_line_offset": None,
        "analysis_quality": "PARTIAL",
    })

    _, feedback, score = analyzer._evaluate(metrics)

    assert score <= 84
    assert metrics["score_confidence"] < 0.9
    assert metrics["evaluated_metrics"] == ["elbow_depth", "arm_extension"]
    assert metrics["unavailable_metrics"] == ["body_alignment"]
    assert "몸통 정렬은 평가하지 못했어요" in feedback


def test_pushup_locks_and_improves_down_capture_then_reuses_it_on_completion():
    analyzer = make_pushup_analyzer()
    overlay = pose_overlay()
    up_frame = np.full((100, 160, 3), 30, dtype=np.uint8)
    first_down = np.full((100, 160, 3), 90, dtype=np.uint8)
    best_down = np.full((100, 160, 3), 150, dtype=np.uint8)
    completion_up = np.full((100, 160, 3), 240, dtype=np.uint8)

    update_frames(analyzer, pushup_metrics(170), up_frame, overlay, 3)
    update_frames(
        analyzer,
        pushup_metrics(88, hip_offset=0.2),
        first_down,
        overlay,
        3,
    )
    first_hash = analyzer.best_pose_snapshot["image_hash"]
    analyzer._update_state(pushup_metrics(89), best_down, overlay)
    locked = copy_snapshot = dict(analyzer.best_pose_snapshot)

    assert locked["image_hash"] != first_hash
    assert locked["elbow_angle"] == 89.0
    assert locked["body_alignment_angle"] == 178.0
    assert locked["analyzed_side"] == "LEFT"
    decoded = cv2.imdecode(
        np.frombuffer(
            base64.b64decode(locked["image"].split(",", 1)[1]), dtype=np.uint8
        ),
        cv2.IMREAD_COLOR,
    )
    assert decoded.shape[:2] == (400, 640)
    assert decoded.std() > 0

    update_frames(analyzer, pushup_metrics(170), completion_up, overlay, 3)
    completed = analyzer.get_completed_pose_capture()
    assert analyzer.count == 1
    assert completed["image_hash"] == copy_snapshot["image_hash"]
    assert completed["image"] == copy_snapshot["image"]


def test_pushup_completion_without_down_overlay_has_no_current_frame_fallback():
    analyzer = make_pushup_analyzer()
    frame = np.full((100, 160, 3), 220, dtype=np.uint8)
    update_frames(analyzer, pushup_metrics(170), frame, None, 3)
    update_frames(analyzer, pushup_metrics(85), frame, None, 3)
    update_frames(analyzer, pushup_metrics(170), frame, None, 3)

    assert analyzer.count == 1
    assert analyzer.get_completed_pose_capture() is None
    assert analyzer.capture_fallback_reason == "no-valid-down-pose"


def test_pushup_reset_clears_capture_and_repetition_state():
    analyzer = make_pushup_analyzer()
    analyzer.best_pose_snapshot = {"image": "locked"}
    analyzer._completed_pose_capture = {"image": "completed"}
    analyzer.capture_fallback_reason = "no-valid-down-pose"
    analyzer.up_frames = analyzer.down_frames = 3
    analyzer.analyzed_side = "RIGHT"
    analyzer.current_min_elbow_angle = 84
    analyzer.repetition_best_posture_score = 92

    analyzer.reset()

    assert analyzer.best_pose_snapshot is None
    assert analyzer.get_completed_pose_capture() is None
    assert analyzer.capture_fallback_reason is None
    assert analyzer.up_frames == analyzer.down_frames == 0
    assert analyzer.analyzed_side is None
    assert analyzer.current_min_elbow_angle == 180
    assert analyzer.repetition_best_posture_score == -1


def test_factory_selects_dedicated_analyzers_and_shares_one_model(monkeypatch):
    shared_model = FakePoseModel()
    created = []

    class FakeSquatAnalyzer:
        def __init__(self, model_path):
            created.append(model_path)
            self.model = shared_model

    monkeypatch.setattr(pose_factory, "SquatAnalyzer", FakeSquatAnalyzer)

    analyzers = pose_factory.create_pose_analyzers("model.pt")

    assert len(created) == 1
    assert analyzers["SQUAT"].model is shared_model
    assert isinstance(analyzers["PUSHUP"], PushUpAnalyzer)
    assert analyzers["PUSHUP"].model is shared_model
    assert isinstance(analyzers["SHOULDER_PRESS"], exercise_pose.ShoulderPressAnalyzer)
    assert analyzers["SHOULDER_PRESS"].model is shared_model
    assert pose_factory.get_pose_analyzer(analyzers, " pushup ") is analyzers["PUSHUP"]


def test_factory_uses_squat_module_for_squat_and_pushup_module_for_pushup(
    monkeypatch,
):
    shared_model = FakePoseModel()

    class FakeSquatAnalyzer:
        def __init__(self, _model_path):
            self.model = shared_model

    monkeypatch.setattr(pose_factory, "SquatAnalyzer", FakeSquatAnalyzer)

    assert isinstance(
        pose_factory.create_pose_analyzer("SQUAT"), FakeSquatAnalyzer
    )
    pushup = pose_factory.create_pose_analyzer("PUSHUP")
    assert isinstance(pushup, PushUpAnalyzer)
    assert pushup.model is shared_model


def test_import_graph_has_no_reverse_pushup_dependency():
    exercise_source = Path(exercise_pose.__file__).read_text(encoding="utf-8")
    pushup_source = Path(pushup_pose.__file__).read_text(encoding="utf-8")

    assert "backend.pushup_pose" not in exercise_source
    assert "backend.exercise_pose" in pushup_source
    assert not hasattr(exercise_pose, "PushUpAnalyzer")
