import pytest
from pydantic import ValidationError

from backend.routers.workout import WorkoutRecordCreate


def coaching_record_payload(**overrides):
    payload = {
        "user_id": 1,
        "exercise_code": "SQUAT",
        "completed_sets": 0,
        "repetition_count": 1,
        "workout_minutes": 1,
        "average_posture_score": 0,
        "best_posture_score": 0,
    }
    payload.update(overrides)
    return payload


def test_coaching_record_rejects_zero_repetitions():
    with pytest.raises(ValidationError):
        WorkoutRecordCreate(**coaching_record_payload(repetition_count=0))


def test_coaching_record_allows_partial_set_after_valid_repetition():
    record = WorkoutRecordCreate(**coaching_record_payload())

    assert record.completed_sets == 0
    assert record.repetition_count == 1
