from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.routers.coaching import router as coaching_router
from backend.routers.routine import router as routine_router
from backend.routers.workout import router as workout_router
from backend.security import get_current_user


def client_for(router, account_type):
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        user_id=10,
        account_type=account_type,
        is_active=True,
    )
    app.dependency_overrides[get_db] = lambda: None
    return TestClient(app)


def test_trainer_cannot_create_coaching_session():
    response = client_for(coaching_router, "TRAINER").post(
        "/api/coaching/sessions",
        json={
            "exercise_code": "SQUAT",
            "target_reps": 10,
            "target_sets": 3,
        },
    )

    assert response.status_code == 403


def test_trainer_cannot_create_personal_routine_recommendation():
    response = client_for(routine_router, "TRAINER").post(
        "/api/routine/recommendations",
        json={
            "user_id": 10,
            "goal": "HEALTH",
            "level": "BEGINNER",
            "days_per_week": 3,
            "workout_minutes": 40,
        },
    )

    assert response.status_code == 403


def test_trainer_cannot_create_personal_workout_plan():
    response = client_for(workout_router, "TRAINER").post(
        "/api/workouts/plans",
        json={
            "user_id": 10,
            "exercise_code": "SQUAT",
            "plan_date": "2026-07-24",
            "set_count": 3,
            "repetition_count": 10,
            "estimated_minutes": 20,
        },
    )

    assert response.status_code == 403


def test_trainer_cannot_create_personal_workout_record():
    response = client_for(workout_router, "TRAINER").post(
        "/api/workouts",
        json={
            "user_id": 10,
            "exercise_code": "SQUAT",
            "completed_sets": 1,
            "repetition_count": 10,
            "workout_minutes": 5,
        },
    )

    assert response.status_code == 403
