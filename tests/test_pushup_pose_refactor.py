from pathlib import Path

import backend.exercise_pose as exercise_pose
import backend.pose_factory as pose_factory
import backend.pushup_pose as pushup_pose
from backend.pushup_pose import PUSHUP_CONFIG, PushUpAnalyzer


class FakePoseModel:
    def predict(self, *_args, **_kwargs):
        return []

    def __call__(self, *_args, **_kwargs):
        return []


def make_pushup_analyzer():
    return PushUpAnalyzer(FakePoseModel())


def accept_frames(analyzer, stage):
    for _ in range(analyzer.required_frames):
        analyzer._accept_stable_stage(stage)


def test_pushup_module_preserves_configuration_and_reset_state():
    analyzer = make_pushup_analyzer()

    assert analyzer.exercise_code == "PUSHUP"
    assert PUSHUP_CONFIG["down_elbow_angle"] == 90.0
    assert PUSHUP_CONFIG["up_elbow_angle"] == 155.0
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
