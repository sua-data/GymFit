from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.routine import (
    can_replace_recommended_plan,
    recommendation_plan_skip_reason,
    router,
)


def plan(*, source="MANUAL", completed=False):
    return SimpleNamespace(
        plan_source=source,
        is_completed=completed,
    )


def test_recommendation_apply_requires_authentication():
    app = FastAPI()
    app.include_router(router)

    response = TestClient(app).post(
        "/api/routine/recommendations/1/apply",
        json={"replace_existing_recommendations": True},
    )

    assert response.status_code == 401


def test_completed_plan_is_preserved():
    item = plan(source="RECOMMENDED", completed=True)
    assert recommendation_plan_skip_reason(item) == "COMPLETED_PLAN_EXISTS"
    assert can_replace_recommended_plan(item, False) is False


def test_trainer_plan_is_preserved():
    item = plan(source="TRAINER")
    assert recommendation_plan_skip_reason(item) == "TRAINER_PLAN_EXISTS"
    assert can_replace_recommended_plan(item, False) is False


def test_manual_plan_is_preserved():
    item = plan(source="MANUAL")
    assert recommendation_plan_skip_reason(item) == "MANUAL_PLAN_EXISTS"
    assert can_replace_recommended_plan(item, False) is False


def test_recommended_plan_with_record_is_preserved():
    item = plan(source="RECOMMENDED")
    assert can_replace_recommended_plan(item, True) is False


def test_only_uncompleted_unlinked_recommendation_is_replaceable():
    item = plan(source="RECOMMENDED")
    assert can_replace_recommended_plan(item, False) is True
