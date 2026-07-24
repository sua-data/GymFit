from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.routers.coaching import router
from backend.security import get_current_user
from backend.services.coaching_session_service import CoachingSessionStore


class FakeAnalyzer:
    def __init__(self):
        self.count = 0
        self.squat_count = 0
        self.stage = "UNKNOWN"
        self.feedback = "준비"

    def process_frame(self, _frame=None):
        self.count += 1
        self.squat_count += 1
        return None, {"count": self.count, "pose_valid": True}

    def reset(self):
        self.count = 0
        self.squat_count = 0
        self.stage = "UNKNOWN"
        self.feedback = "준비"


@pytest.fixture
def store():
    return CoachingSessionStore(
        ttl=timedelta(minutes=30),
        analyzer_factory=lambda _code: FakeAnalyzer(),
    )


def create(store, user_id, exercise_code="SQUAT"):
    return store.create(
        user_id=user_id,
        exercise_code=exercise_code,
        target_reps=10,
        target_sets=3,
        workout_plan_id=None,
    )


def test_users_receive_independent_analyzers(store):
    session_a = create(store, 1)
    session_b = create(store, 2)

    assert session_a.analyzer is not session_b.analyzer
    with store.locked(session_a.session_id, user_id=1) as item:
        item.analyzer.process_frame()

    assert session_a.analyzer.squat_count == 1
    assert session_b.analyzer.squat_count == 0


def test_reset_only_changes_owned_session(store):
    session_a = create(store, 1)
    session_b = create(store, 2)
    session_a.analyzer.process_frame()
    session_b.analyzer.process_frame()

    store.reset(session_a.session_id, user_id=1)

    assert session_a.analyzer.squat_count == 0
    assert session_b.analyzer.squat_count == 1


@pytest.mark.parametrize("operation", ["analyze", "reset", "delete"])
def test_other_user_cannot_access_session(store, operation):
    session = create(store, 2)

    with pytest.raises(HTTPException) as error:
        if operation == "analyze":
            with store.locked(session.session_id, user_id=1):
                pass
        elif operation == "reset":
            store.reset(session.session_id, user_id=1)
        else:
            store.delete(session.session_id, user_id=1)

    assert error.value.status_code == 403


def test_deleted_session_cannot_be_analyzed(store):
    session = create(store, 1)
    assert store.delete(session.session_id, user_id=1) is True
    assert store.delete(session.session_id, user_id=1) is False

    with pytest.raises(HTTPException) as error:
        with store.locked(session.session_id, user_id=1):
            pass

    assert error.value.status_code == 404


def test_expired_session_is_removed():
    now = [datetime(2026, 7, 24, tzinfo=timezone.utc)]
    store = CoachingSessionStore(
        ttl=timedelta(minutes=30),
        analyzer_factory=lambda _code: FakeAnalyzer(),
        clock=lambda: now[0],
    )
    session = create(store, 1)
    now[0] += timedelta(minutes=31)

    assert store.cleanup_expired() == 1
    with pytest.raises(HTTPException) as error:
        with store.locked(session.session_id, user_id=1):
            pass
    assert error.value.status_code == 404


def test_expired_session_access_returns_410():
    now = [datetime(2026, 7, 24, tzinfo=timezone.utc)]
    store = CoachingSessionStore(
        ttl=timedelta(minutes=30),
        analyzer_factory=lambda _code: FakeAnalyzer(),
        clock=lambda: now[0],
    )
    session = create(store, 1)
    now[0] += timedelta(minutes=31)

    with pytest.raises(HTTPException) as error:
        with store.locked(session.session_id, user_id=1):
            pass

    assert error.value.status_code == 410


def test_same_session_requests_are_serialized(store):
    session = create(store, 1)

    def increment():
        with store.locked(session.session_id, user_id=1) as item:
            current = item.analyzer.count
            item.analyzer.count = current + 1

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _index: increment(), range(100)))

    assert session.analyzer.count == 100


def test_new_same_user_exercise_session_replaces_previous(store):
    old_session = create(store, 1)
    new_session = create(store, 1)

    with pytest.raises(HTTPException) as error:
        with store.locked(old_session.session_id, user_id=1):
            pass

    assert error.value.status_code == 404
    with store.locked(new_session.session_id, user_id=1):
        pass


def test_unsupported_exercise_is_rejected():
    def factory(code):
        raise KeyError(code)

    store = CoachingSessionStore(analyzer_factory=factory)
    with pytest.raises(HTTPException) as error:
        create(store, 1, "NOT_SUPPORTED")

    assert error.value.status_code == 400


def test_coaching_session_creation_requires_token():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post(
        "/api/coaching/sessions",
        json={
            "exercise_code": "SQUAT",
            "target_reps": 10,
            "target_sets": 3,
        },
    )

    assert response.status_code == 401


def test_unsupported_exercise_api_returns_400():
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: type(
        "UserStub", (), {"user_id": 1, "account_type": "MEMBER"}
    )()
    app.dependency_overrides[get_db] = lambda: None

    response = TestClient(app).post(
        "/api/coaching/sessions",
        json={
            "exercise_code": "NOT_SUPPORTED",
            "target_reps": 10,
            "target_sets": 3,
        },
    )

    assert response.status_code == 400
