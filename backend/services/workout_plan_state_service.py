from collections.abc import Iterable

from backend.models import WorkoutPlan, WorkoutPlanSet


def set_workout_plan_completion(
    workout_plan: WorkoutPlan,
    plan_sets: Iterable[WorkoutPlanSet],
    *,
    completed: bool,
) -> None:
    """Keep a workout plan and all of its sets in the same completion state."""
    workout_plan.is_completed = completed
    for plan_set in plan_sets:
        plan_set.is_completed = completed
