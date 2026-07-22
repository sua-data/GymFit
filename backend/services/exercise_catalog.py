AI_COACHING_EXERCISE_CODES = frozenset({"SQUAT"})


def is_coaching_supported(exercise_code: str | None) -> bool:
    return bool(exercise_code and exercise_code.upper() in AI_COACHING_EXERCISE_CODES)
