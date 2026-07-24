from datetime import datetime
from types import SimpleNamespace

from backend.routers.dashboard import (
    best_posture_exercises_statement,
    best_posture_records_statement,
    select_best_posture_records,
)
from backend.services.exercise_catalog import AI_COACHING_EXERCISE_CODES


def record(record_id, exercise_id, score, started_at):
    return SimpleNamespace(
        workout_record_id=record_id,
        exercise_id=exercise_id,
        best_posture_score=score,
        started_at=started_at,
    )


def test_best_posture_options_are_exactly_supported_exercises():
    assert AI_COACHING_EXERCISE_CODES == {
        "SQUAT",
        "PUSHUP",
        "SHOULDER_PRESS",
    }


def test_best_posture_queries_filter_supported_coaching_records():
    exercise_sql = str(
        best_posture_exercises_statement().compile(
            compile_kwargs={"literal_binds": True}
        )
    )
    record_sql = str(
        best_posture_records_statement(7).compile(
            compile_kwargs={"literal_binds": True}
        )
    )

    for exercise_code in AI_COACHING_EXERCISE_CODES:
        assert exercise_code in exercise_sql
        assert exercise_code in record_sql
    assert "workout_record.user_id = 7" in record_sql
    assert "workout_record.record_source = 'COACHING'" in record_sql
    assert "workout_record.best_posture_score IS NOT NULL" in record_sql


def test_first_sorted_record_is_selected_for_each_exercise():
    high = record(2, 10, 95, datetime(2026, 7, 24, 10))
    low = record(1, 10, 80, datetime(2026, 7, 24, 11))

    selected = select_best_posture_records([high, low])

    assert selected[10] is high


def test_latest_record_wins_when_scores_are_tied():
    recent = record(2, 10, 90, datetime(2026, 7, 24, 11))
    older = record(1, 10, 90, datetime(2026, 7, 24, 10))

    selected = select_best_posture_records([recent, older])

    assert selected[10] is recent
