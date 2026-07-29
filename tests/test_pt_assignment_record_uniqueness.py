import pytest
from fastapi import HTTPException
from sqlalchemy import UniqueConstraint

from backend.models.pt_assignment import PtAssignment
from backend.routers.pt_assignment import (
    WORKOUT_RECORD_ALREADY_LINKED_MESSAGE,
    require_unlinked_workout_record,
)


class ScalarSession:
    def __init__(self, value):
        self.value = value

    def scalar(self, _statement):
        return self.value


def test_workout_record_can_be_linked_when_unused():
    require_unlinked_workout_record(
        ScalarSession(None),
        workout_record_id=10,
        assignment_id=20,
    )


def test_workout_record_linked_to_another_assignment_returns_409():
    with pytest.raises(HTTPException) as exc_info:
        require_unlinked_workout_record(
            ScalarSession(30),
            workout_record_id=10,
            assignment_id=20,
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == WORKOUT_RECORD_ALREADY_LINKED_MESSAGE


def test_pt_assignment_has_unique_workout_record_constraint():
    constraints = {
        constraint.name
        for constraint in PtAssignment.__table__.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert "uq_pt_assignment_workout_record" in constraints
