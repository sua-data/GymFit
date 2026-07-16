const GYMFIT_COACHING_PLAN_KEY = "gymfitCoachingPlan";
const COACHING_EXERCISE_CODES = [
  "SQUAT",
  "PUSHUP",
  "SHOULDER_PRESS",
];

function saveCoachingPlan(plan) {
  const sets = Array.isArray(plan?.sets)
    ? plan.sets
        .filter((set) => Number(set.repetition_count || 0) > 0)
        .sort(
          (first, second) =>
            Number(first.set_order) - Number(second.set_order)
        )
    : [];

  const exerciseCode = String(plan?.exercise_code || "").toUpperCase();
  if (
    !COACHING_EXERCISE_CODES.includes(exerciseCode)
    || !plan?.workout_plan_id
    || sets.length === 0
  ) {
    clearCoachingPlan();
    return null;
  }

  const coachingPlan = {
    workout_plan_id: plan?.workout_plan_id ?? null,
    exercise_code: exerciseCode,
    exercise_name: plan?.exercise_name ?? exerciseCode,
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
    if (
      !plan
      || typeof plan !== "object"
      || !COACHING_EXERCISE_CODES.includes(plan.exercise_code)
    ) {
      clearCoachingPlan();
      return null;
    }
    return plan;
  } catch {
    clearCoachingPlan();
    return null;
  }
}

function clearCoachingPlan() {
  sessionStorage.removeItem(GYMFIT_COACHING_PLAN_KEY);
}
