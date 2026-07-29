from datetime import datetime

import pytest
from fastapi import HTTPException

from backend.routers.pt_schedule import (
    SCHEDULE_OVERLAP_MESSAGE,
    lock_schedule_participants,
    validate_overlap,
)


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class ScheduleSession:
    def __init__(self, *, participant_ids=None, conflict_id=None):
        self.participant_ids = participant_ids or []
        self.conflict_id = conflict_id
        self.statements = []

    def scalars(self, statement):
        self.statements.append(statement)
        return ScalarResult(self.participant_ids)

    def scalar(self, statement):
        self.statements.append(statement)
        return self.conflict_id


def test_participants_are_locked_in_stable_id_order():
    db = ScheduleSession(participant_ids=[3, 9])

    lock_schedule_participants(db, trainer_id=9, member_id=3)

    sql = str(db.statements[0])
    assert "ORDER BY users.user_id ASC" in sql
    assert db.statements[0]._for_update_arg is not None


def test_overlap_returns_unified_409_message():
    db = ScheduleSession(conflict_id=77)

    with pytest.raises(HTTPException) as error:
        validate_overlap(
            db,
            trainer_id=9,
            member_id=3,
            start_at=datetime(2026, 8, 1, 10, 0),
            end_at=datetime(2026, 8, 1, 11, 0),
        )

    assert error.value.status_code == 409
    assert error.value.detail == SCHEDULE_OVERLAP_MESSAGE


def test_update_overlap_query_excludes_current_schedule():
    db = ScheduleSession(conflict_id=None)

    validate_overlap(
        db,
        trainer_id=9,
        member_id=3,
        start_at=datetime(2026, 8, 1, 10, 0),
        end_at=datetime(2026, 8, 1, 11, 0),
        exclude_id=55,
    )

    sql = str(db.statements[0])
    assert "pt_schedule.schedule_id !=" in sql
    assert db.statements[0]._for_update_arg is not None
