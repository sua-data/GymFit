from datetime import date

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.routers.workout import create_calendar_days, router
from backend.security import get_current_user


class EmptyResult:
    def all(self):
        return []


class EmptyCalendarSession:
    def execute(self, _statement):
        return EmptyResult()


def calendar_client(user_id=1, db=None):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type(
        "UserStub", (), {"user_id": user_id}
    )()
    app.dependency_overrides[get_db] = lambda: db or EmptyCalendarSession()
    return TestClient(app)


def test_calendar_days_include_dates_without_plans():
    days = create_calendar_days(
        date(2026, 7, 24),
        date(2026, 7, 30),
        {date(2026, 7, 25): (3, 1)},
    )
    assert len(days) == 7
    assert days[0].total_count == 0
    assert days[1].total_count == 3
    assert days[1].completed_count == 1
    assert days[-1].plan_date == date(2026, 7, 30)


def test_calendar_rejects_reversed_range():
    response = calendar_client().get(
        "/api/workouts/plans/calendar/1",
        params={"start_date": "2026-07-30", "end_date": "2026-07-24"},
    )
    assert response.status_code == 422


def test_calendar_rejects_more_than_31_days():
    response = calendar_client().get(
        "/api/workouts/plans/calendar/1",
        params={"start_date": "2026-07-01", "end_date": "2026-08-01"},
    )
    assert response.status_code == 422


def test_calendar_blocks_other_user():
    response = calendar_client(user_id=1).get(
        "/api/workouts/plans/calendar/2",
        params={"start_date": "2026-07-24", "end_date": "2026-07-30"},
    )
    assert response.status_code == 403


def test_calendar_requires_authentication():
    app = FastAPI()
    app.include_router(router)
    response = TestClient(app).get(
        "/api/workouts/plans/calendar/1",
        params={"start_date": "2026-07-24", "end_date": "2026-07-30"},
    )
    assert response.status_code == 401


def test_calendar_response_disables_cache():
    response = calendar_client().get(
        "/api/workouts/plans/calendar/1",
        params={"start_date": "2026-07-24", "end_date": "2026-07-30"},
    )
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store, no-cache, must-revalidate"
    assert len(response.json()["days"]) == 7
