const GYMFIT_COACHING_PLAN_KEY = "gymfitCoachingPlan";

function saveCoachingPlan(plan) {
  const sets = Array.isArray(plan?.sets)
    ? plan.sets
        .filter((set) => Number(set.repetition_count || 0) > 0)
        .sort(
          (first, second) =>
            Number(first.set_order) - Number(second.set_order)
        )
    : [];

  const coachingPlan = {
    workout_plan_id: plan?.workout_plan_id ?? null,
    exercise_code: plan?.exercise_code ?? "SQUAT",
    exercise_name: plan?.exercise_name ?? "스쿼트",
    estimated_minutes: Number(plan?.estimated_minutes || 0),
    sets,
  };

  sessionStorage.setItem(
    GYMFIT_COACHING_PLAN_KEY,
    JSON.stringify(coachingPlan)
  );
  return coachingPlan;
}

function loadCoachingPlan() {
  const savedPlan = sessionStorage.getItem(GYMFIT_COACHING_PLAN_KEY);
  if (!savedPlan) {
    return null;
  }
  try {
    const plan = JSON.parse(savedPlan);
    return plan && typeof plan === "object" ? plan : null;
  } catch {
    clearCoachingPlan();
    return null;
  }
}

function clearCoachingPlan() {
  sessionStorage.removeItem(GYMFIT_COACHING_PLAN_KEY);
}
