from types import SimpleNamespace

import numpy as np

import backend.exercise_pose as exercise_pose
from backend.shoulder_press_pose import ShoulderPressPoseAnalyzer
from backend.services.coaching_session_service import CoachingSessionStore


class FakePoseModel:
    def __call__(self, *_args, **_kwargs):
        return []


class FakeBoxes:
    def __init__(self):
        self.xyxy = np.asarray([[5, 5, 155, 195]], dtype=float)
        self.conf = np.asarray([0.91])

    def __len__(self):
        return 1


def make_analyzer():
    return ShoulderPressPoseAnalyzer(FakePoseModel())


def metrics(angle):
    return {
        "pose_valid": True,
        "selected_side": "LEFT",
        "elbow_angle": float(angle),
        "average_elbow_angle": float(angle),
        "torso_angle": 0.0,
    }


def update(analyzer, angle, frames=None):
    for _ in range(frames or analyzer.required_frames):
        analyzer._update_state(metrics(angle))


def person_pose():
    person = np.zeros((17, 2), dtype=float)
    person[5], person[7], person[9] = (40, 60), (30, 80), (45, 95)
    person[6], person[8], person[10] = (80, 60), (90, 80), (75, 95)
    person[11], person[12] = (45, 130), (75, 130)
    return person


def test_down_stage_is_accepted_after_required_frames():
    analyzer = make_analyzer()

    update(analyzer, 95)

    assert analyzer.stage == "DOWN"
    assert analyzer.count == 0
    assert analyzer.down_frames == analyzer.required_frames


def test_down_to_up_transition_increments_count():
    analyzer = make_analyzer()
    update(analyzer, 95)
    update(analyzer, 165)

    assert analyzer.stage == "UP"
    assert analyzer.count == 1
    assert analyzer.last_counted is True
    assert analyzer.up_frames == analyzer.required_frames


def test_incomplete_press_does_not_count():
    analyzer = make_analyzer()
    update(analyzer, 95)
    update(analyzer, 135, frames=5)

    assert analyzer.stage == "DOWN"
    assert analyzer.count == 0


def test_missing_arm_joints_makes_pose_invalid():
    analyzer = make_analyzer()
    confidence = np.full(17, 0.9, dtype=float)
    confidence[[5, 6, 7, 8, 9, 10]] = 0.1

    result = analyzer._extract_metrics(person_pose(), confidence)

    assert result["pose_valid"] is False


def test_selected_arm_is_stable_across_short_confidence_fluctuations():
    analyzer = make_analyzer()
    person = person_pose()
    confidence = np.full(17, 0.8, dtype=float)
    confidence[[5, 7, 9]] = 0.95
    confidence[[6, 8, 10]] = 0.75
    assert analyzer._extract_metrics(person, confidence)["selected_side"] == "LEFT"

    confidence[[5, 7, 9]] = 0.72
    confidence[[6, 8, 10]] = 0.96
    for _ in range(2):
        assert analyzer._extract_metrics(person, confidence)["selected_side"] == "LEFT"
    analyzer.down_frames = 2
    analyzer.candidate_stage = "DOWN"
    analyzer.transition_frames = 1
    assert analyzer._extract_metrics(person, confidence)["selected_side"] == "RIGHT"
    assert analyzer.down_frames == analyzer.up_frames == 0
    assert analyzer.candidate_stage is None
    assert analyzer.transition_frames == 0


def test_process_contract_and_legacy_import(monkeypatch):
    analyzer = make_analyzer()
    person = person_pose()
    confidence = np.full(17, 0.9, dtype=float)
    result = SimpleNamespace(
        keypoints=SimpleNamespace(xy=np.asarray([person]), conf=np.asarray([confidence])),
        boxes=FakeBoxes(),
        plot=lambda: np.zeros((200, 160, 3), dtype=np.uint8),
    )
    monkeypatch.setattr(analyzer, "model", lambda *_args, **_kwargs: [result])

    _, status = analyzer.process_frame(np.zeros((200, 160, 3), dtype=np.uint8))

    for field in (
        "count", "stage", "pose_valid", "person_detected", "elbow_angle",
        "average_elbow_angle", "posture_score", "feedback", "pose_overlay",
        "selected_side",
    ):
        assert field in status
    assert status["debug"]["analyzer_class"] == "ShoulderPressPoseAnalyzer"
    assert status["debug"]["analyzer_instance_id"] == id(analyzer)
    assert status["debug"]["required_frames"] == 2
    assert status["detection_reason"] in {"ok", "ARM_OR_TORSO_LOW_CONFIDENCE"}
    assert exercise_pose.ShoulderPressAnalyzer is ShoulderPressPoseAnalyzer


def test_coaching_session_reuses_same_analyzer_between_frames():
    store = CoachingSessionStore(analyzer_factory=lambda _code: make_analyzer())
    session = store.create(
        user_id=1,
        exercise_code="SHOULDER_PRESS",
        target_reps=10,
        target_sets=3,
        workout_plan_id=None,
    )
    analyzer_id = id(session.analyzer)

    with store.locked(session.session_id, user_id=1) as first_frame:
        update(first_frame.analyzer, 95)
    with store.locked(session.session_id, user_id=1) as second_frame:
        update(second_frame.analyzer, 165)

    assert id(second_frame.analyzer) == analyzer_id
    assert second_frame.analyzer.stage == "UP"
    assert second_frame.analyzer.count == 1
