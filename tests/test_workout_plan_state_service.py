from types import SimpleNamespace

from backend.services.workout_plan_state_service import set_workout_plan_completion


def test_set_workout_plan_completion_updates_plan_and_all_sets():
    plan = SimpleNamespace(is_completed=False)
    plan_sets = [
        SimpleNamespace(is_completed=False),
        SimpleNamespace(is_completed=False),
    ]

    set_workout_plan_completion(plan, plan_sets, completed=True)

    assert plan.is_completed is True
    assert all(plan_set.is_completed is True for plan_set in plan_sets)


def test_set_workout_plan_completion_can_reset_plan_without_sets():
    plan = SimpleNamespace(is_completed=True)

    set_workout_plan_completion(plan, [], completed=False)

    assert plan.is_completed is False
