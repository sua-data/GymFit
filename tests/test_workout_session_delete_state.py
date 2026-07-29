from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError

from backend.routers import workout_session


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class DeleteSession:
    def __init__(self, *, scalar_values=None, scalar_lists=None, commit_error=None):
        self.scalar_values = list(scalar_values or [])
        self.scalar_lists = list(scalar_lists or [])
        self.commit_error = commit_error
        self.deleted = []
        self.committed = False
        self.rolled_back = False

    def scalar(self, _statement):
        return self.scalar_values.pop(0)

    def scalars(self, _statement):
        return ScalarResult(self.scalar_lists.pop(0))

    def delete(self, value):
        self.deleted.append(value)

    def commit(self):
        if self.commit_error is not None:
            raise self.commit_error
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def record(*, workout_plan_id=None, record_type="WORKOUT"):
    return SimpleNamespace(
        workout_record_id=10,
        workout_plan_id=workout_plan_id,
        user_id=7,
        record_type=record_type,
        items=[],
    )


def user():
    return SimpleNamespace(user_id=7)


def test_delete_restores_linked_pt_assignment(monkeypatch):
    target = record()
    assignment = SimpleNamespace(
        status="COMPLETED",
        workout_record_id=10,
        completed_at=object(),
    )
    db = DeleteSession(scalar_lists=[[assignment]])
    monkeypatch.setattr(workout_session, "get_owned", lambda *_args, **_kwargs: target)

    workout_session.delete_session(10, user(), db)

    assert assignment.status == "IN_PROGRESS"
    assert assignment.workout_record_id is None
    assert assignment.completed_at is None
    assert db.deleted == [target]
    assert db.committed is True


def test_delete_unlinked_record_does_not_affect_assignment(monkeypatch):
    target = record()
    db = DeleteSession(scalar_lists=[[]])
    monkeypatch.setattr(workout_session, "get_owned", lambda *_args, **_kwargs: target)

    workout_session.delete_session(10, user(), db)

    assert db.deleted == [target]
    assert db.committed is True


def test_delete_restores_routine_and_assignment_together(monkeypatch):
    target = record(workout_plan_id=20)
    assignment = SimpleNamespace(
        status="COMPLETED",
        workout_record_id=10,
        completed_at=object(),
    )
    plan = SimpleNamespace(is_completed=True, workout_plan_id=20)
    plan_sets = [
        SimpleNamespace(is_completed=True),
        SimpleNamespace(is_completed=True),
    ]
    db = DeleteSession(
        scalar_values=[plan],
        scalar_lists=[[assignment], plan_sets],
    )
    monkeypatch.setattr(workout_session, "get_owned", lambda *_args, **_kwargs: target)

    workout_session.delete_session(10, user(), db)

    assert assignment.status == "IN_PROGRESS"
    assert assignment.workout_record_id is None
    assert assignment.completed_at is None
    assert plan.is_completed is False
    assert all(plan_set.is_completed is False for plan_set in plan_sets)
    assert db.deleted == [target]
    assert db.committed is True


def test_feedback_restrict_failure_keeps_409(monkeypatch):
    target = record()
    integrity_error = IntegrityError(
        "DELETE FROM workout_record",
        {},
        Exception("pt_feedback workout_record_id restrict"),
    )
    db = DeleteSession(scalar_lists=[[]], commit_error=integrity_error)
    monkeypatch.setattr(workout_session, "get_owned", lambda *_args, **_kwargs: target)

    with pytest.raises(HTTPException) as exc_info:
        workout_session.delete_session(10, user(), db)

    assert exc_info.value.status_code == 409
    assert db.rolled_back is True


def test_pt_schedule_record_is_rejected_before_assignment_restore(monkeypatch):
    target = record(record_type="PT")
    db = DeleteSession()
    monkeypatch.setattr(workout_session, "get_owned", lambda *_args, **_kwargs: target)

    with pytest.raises(HTTPException) as exc_info:
        workout_session.delete_session(10, user(), db)

    assert exc_info.value.status_code == 403
    assert db.scalar_lists == []
    assert db.deleted == []
    assert db.rolled_back is True
