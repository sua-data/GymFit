"""Rule-based base templates. Codes are limited to the seeded exercise catalog."""

TEMPLATES = {
    ("WEIGHT_LOSS", "BEGINNER"): [
        ("SQUAT", 3, 10), ("PUSHUP", 3, 8), ("LAT_PULLDOWN", 3, 10),
        ("LUNGE", 3, 8), ("MOUNTAIN_CLIMBER", 3, 12), ("PLANK", 3, 10),
    ],
    ("WEIGHT_LOSS", "INTERMEDIATE"): [
        ("SQUAT", 4, 12), ("PUSHUP", 4, 12), ("SEATED_ROW", 4, 12),
        ("LUNGE", 4, 10), ("MOUNTAIN_CLIMBER", 4, 16), ("PLANK", 4, 12),
    ],
    ("MUSCLE_GAIN", "BEGINNER"): [
        ("SQUAT", 3, 8), ("CHEST_PRESS", 3, 10), ("LAT_PULLDOWN", 3, 10),
        ("SHOULDER_PRESS", 3, 8), ("LEG_PRESS", 3, 10), ("PLANK", 3, 10),
    ],
    ("MUSCLE_GAIN", "INTERMEDIATE"): [
        ("SQUAT", 4, 8), ("BENCH_PRESS", 4, 8), ("BARBELL_ROW", 4, 8),
        ("SHOULDER_PRESS", 4, 10), ("ROMANIAN_DEADLIFT", 4, 8), ("PLANK", 4, 12),
    ],
    ("ENDURANCE", "BEGINNER"): [
        ("SQUAT", 3, 12), ("PUSHUP", 3, 8), ("SEATED_ROW", 3, 12),
        ("MOUNTAIN_CLIMBER", 3, 12), ("CRUNCH", 3, 12), ("PLANK", 3, 10),
    ],
    ("ENDURANCE", "INTERMEDIATE"): [
        ("SQUAT", 4, 15), ("PUSHUP", 4, 12), ("LAT_PULLDOWN", 4, 12),
        ("MOUNTAIN_CLIMBER", 4, 20), ("RUSSIAN_TWIST", 4, 16), ("PLANK", 4, 15),
    ],
}

GOAL_ALIASES = {
    "DIET": "WEIGHT_LOSS", "WEIGHT_LOSS": "WEIGHT_LOSS", "체중 감량": "WEIGHT_LOSS",
    "MUSCLE": "MUSCLE_GAIN", "MUSCLE_GAIN": "MUSCLE_GAIN", "STRENGTH": "MUSCLE_GAIN",
    "근력 향상": "MUSCLE_GAIN", "HEALTH": "ENDURANCE", "ENDURANCE": "ENDURANCE",
    "체력 향상": "ENDURANCE",
}


def normalize_goal(code: str | None, name: str | None = None) -> str:
    return GOAL_ALIASES.get((code or "").upper(), GOAL_ALIASES.get(name or "", "ENDURANCE"))


def normalize_level(level: str | None) -> str:
    return "INTERMEDIATE" if level in {"INTERMEDIATE", "ADVANCED"} else "BEGINNER"


def select_template(goal: str, level: str) -> list[tuple[str, int, int]]:
    return list(TEMPLATES[(normalize_goal(goal), normalize_level(level))])

