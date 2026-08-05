import base64

import cv2
import numpy as np

from backend.squat_pose import SquatAnalyzer


def analyzer_without_model():
    analyzer = SquatAnalyzer.__new__(SquatAnalyzer)
    analyzer.down_angle = 110
    analyzer.up_angle = 155
    analyzer.deep_angle = 100
    analyzer.good_angle = 110
    analyzer.guide_angle = 135
    analyzer.torso_warning_angle = 45
    analyzer.torso_check_angle = 35
    analyzer.required_frames = 3
    analyzer.max_missing_frames = 15
    analyzer.reset()
    return analyzer


def test_best_valid_score_wins_and_frame_is_copied():
    analyzer = analyzer_without_model()
    analyzer.stage = "DOWN"
    analyzer.down_frames = analyzer.required_frames
    first = np.full((2, 2, 3), 10, dtype=np.uint8)
    best = np.full((2, 2, 3), 20, dtype=np.uint8)

    analyzer.feedback = "first"
    analyzer._update_best_pose(first, 105, 20)
    analyzer.feedback = "best"
    analyzer._update_best_pose(best, 95, 20)
    locked_image = analyzer.best_pose_snapshot["image"]
    best[:] = 99

    assert analyzer.best_pose_score == 95
    assert analyzer.best_pose_angle == 95
    assert analyzer.best_pose_feedback == "best"
    assert locked_image.startswith("data:image/jpeg;base64,")
    assert analyzer.best_pose_snapshot["image"] == locked_image


def test_standing_and_missing_torso_are_not_candidates():
    analyzer = analyzer_without_model()
    frame = np.zeros((2, 2, 3), dtype=np.uint8)

    analyzer._update_best_pose(frame, 156, 10)
    analyzer._update_best_pose(frame, 100, None)

    assert analyzer.best_pose_snapshot is None


def test_high_scoring_standing_frame_is_excluded_by_stage_and_depth():
    analyzer = analyzer_without_model()
    standing = np.full((2, 2, 3), 240, dtype=np.uint8)
    squat = np.full((2, 2, 3), 40, dtype=np.uint8)

    # Even an artificially high-scoring UP frame cannot become a candidate.
    analyzer._calculate_posture_score = lambda angle, torso: (
        100 if angle > analyzer.good_angle else 70
    )
    analyzer.stage = "UP"
    analyzer.down_frames = 0
    analyzer._update_best_pose(standing, 170, 10)

    analyzer.stage = "DOWN"
    analyzer.down_frames = analyzer.required_frames
    analyzer._update_best_pose(squat, 100, 20)

    assert analyzer.best_pose_snapshot["stage"] == "DOWN"
    assert analyzer.best_pose_snapshot["knee_angle"] == 100
    decoded = cv2.imdecode(
        np.frombuffer(
            base64.b64decode(analyzer.best_pose_snapshot["image"].split(",", 1)[1]),
            dtype=np.uint8,
        ),
        cv2.IMREAD_COLOR,
    )
    assert np.mean(decoded) < 60


def test_completed_repetition_exposes_best_once_and_resets_active_state():
    analyzer = analyzer_without_model()
    frame = np.full((2, 2, 3), 7, dtype=np.uint8)
    analyzer.stage = "DOWN"
    analyzer.stage = "DOWN"
    analyzer.down_frames = analyzer.required_frames
    analyzer.feedback = "best frame feedback"
    analyzer._update_best_pose(frame, 105, 20)
    locked_image = analyzer.best_pose_snapshot["image"]
    analyzer.best_pose_snapshot.update({
        "score": 90.0,
        "knee_angle": 105.0,
        "torso_angle": 20.0,
        "feedback": "best frame feedback",
        "stage": "DOWN",
    })
    analyzer.best_pose_score = 90
    analyzer.best_pose_angle = 105
    analyzer.best_pose_torso_angle = 20
    analyzer.best_pose_feedback = "best frame feedback"

    for _ in range(analyzer.required_frames):
        analyzer._update_squat_state(160, 20, frame)

    capture = analyzer.get_completed_pose_capture()
    assert analyzer.squat_count == 1
    assert capture["score"] == 90
    assert capture["knee_angle"] == 105
    assert capture["feedback"] == "best frame feedback"
    assert capture["image"] == locked_image
    # The API must encode first and explicitly clear afterward.
    assert analyzer.best_pose_snapshot is not None
    analyzer.clear_completed_pose_capture()
    assert analyzer.best_pose_frame is None
    assert analyzer.get_completed_pose_capture() is None


def test_up_down_up_encodes_only_down_and_returns_locked_image(monkeypatch):
    analyzer = analyzer_without_model()
    up_a = np.full((8, 8, 3), 220, dtype=np.uint8)
    down_b = np.full((8, 8, 3), 30, dtype=np.uint8)
    up_c = np.full((8, 8, 3), 180, dtype=np.uint8)
    real_imencode = cv2.imencode
    encoded_means = []

    def recording_imencode(extension, image, params):
        encoded_means.append(float(np.mean(image)))
        return real_imencode(extension, image, params)

    monkeypatch.setattr("backend.squat_pose.cv2.imencode", recording_imencode)

    analyzer._update_squat_state(170, 20, up_a)
    for _ in range(analyzer.required_frames):
        analyzer._update_squat_state(100, 20, down_b)
    locked_image = analyzer.best_pose_snapshot["image"]
    locked_hash = analyzer.best_pose_snapshot["image_hash"]

    for _ in range(analyzer.required_frames):
        analyzer._update_squat_state(170, 20, up_c)

    capture = analyzer.get_completed_pose_capture()
    assert encoded_means == [30.0]
    assert capture["image"] == locked_image
    assert capture["image_hash"] == locked_hash


def test_completion_without_candidate_uses_no_capture_for_caller_fallback():
    analyzer = analyzer_without_model()
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    analyzer.stage = "DOWN"

    for _ in range(analyzer.required_frames):
        analyzer._update_squat_state(160, 20, frame)

    assert analyzer.squat_count == 1
    assert analyzer.get_completed_pose_capture() is None
