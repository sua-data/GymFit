from types import SimpleNamespace

from backend.services.pt_assignment_state_service import (
    restore_assignments_for_deleted_workout_record,
)


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class AssignmentSession:
    def __init__(self, assignments):
        self.assignments = assignments
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        return ScalarResult(self.assignments)


def test_completed_assignment_is_restored_when_record_is_deleted():
    assignment = SimpleNamespace(
        status="COMPLETED",
        workout_record_id=10,
        completed_at=object(),
    )
    db = AssignmentSession([assignment])

    restored = restore_assignments_for_deleted_workout_record(
        db,
        workout_record_id=10,
    )

    assert restored == [assignment]
    assert assignment.status == "IN_PROGRESS"
    assert assignment.workout_record_id is None
    assert assignment.completed_at is None
    assert "FOR UPDATE" in str(db.statement.compile()).upper()


def test_unlinked_record_does_not_change_any_assignment():
    db = AssignmentSession([])

    restored = restore_assignments_for_deleted_workout_record(
        db,
        workout_record_id=10,
    )

    assert restored == []


def test_non_completed_assignment_status_is_not_overwritten():
    assignment = SimpleNamespace(
        status="CANCELLED",
        workout_record_id=10,
        completed_at=object(),
    )

    restore_assignments_for_deleted_workout_record(
        AssignmentSession([assignment]),
        workout_record_id=10,
    )

    assert assignment.status == "CANCELLED"
    assert assignment.workout_record_id is None
    assert assignment.completed_at is None
