"""Pose analyzer construction and model sharing."""

from backend.exercise_pose import ShoulderPressAnalyzer
from backend.pushup_pose import PushUpAnalyzer
from backend.squat_pose import SquatAnalyzer


def create_pose_analyzers(model_path: str = "yolo11n-pose.pt"):
    squat = SquatAnalyzer(model_path)
    return {
        "SQUAT": squat,
        "PUSHUP": PushUpAnalyzer(squat.model),
        "SHOULDER_PRESS": ShoulderPressAnalyzer(squat.model),
    }


def create_pose_analyzer(exercise_code: str, model_path: str = "yolo11n-pose.pt"):
    normalized = str(exercise_code or "").strip().upper()
    squat = SquatAnalyzer(model_path)
    if normalized == "SQUAT":
        return squat
    if normalized == "PUSHUP":
        return PushUpAnalyzer(squat.model)
    if normalized == "SHOULDER_PRESS":
        return ShoulderPressAnalyzer(squat.model)
    raise KeyError(normalized)


def get_pose_analyzer(analyzers: dict, exercise_code: str):
    normalized = str(exercise_code or "").strip().upper()
    analyzer = analyzers.get(normalized)
    if analyzer is None:
        raise KeyError(normalized)
    return analyzer
