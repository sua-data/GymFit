from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_coaching_uses_activity_timer_instead_of_wall_clock_duration():
    source = (ROOT / "frontend/js/coaching.js").read_text(encoding="utf-8")

    assert "workoutActivityTimer.update(status" in source
    assert "workoutActivityTimer.getWholeMinutes(totalCompletedReps)" in source
    assert "Math.max(\n    1," not in source
    assert "effectiveEnd.getTime()" not in source


def test_activity_timer_supports_all_coaching_exercise_angle_fields():
    source = (ROOT / "frontend/js/coaching_activity_timer.js").read_text(
        encoding="utf-8"
    )

    assert "status.elbow_angle" in source
    assert "status.average_elbow_angle" in source
    assert "status.average_angle" in source
    assert "stageChanged" in source
    assert "countIncreased" in source


def test_activity_timer_loads_before_main_coaching_script():
    html = (ROOT / "frontend/coaching.html").read_text(encoding="utf-8")

    assert html.index("coaching_activity_timer.js") < html.index("coaching.js?v=")
