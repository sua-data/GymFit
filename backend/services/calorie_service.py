from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP


VALID_INTENSITIES = {"LOW", "MODERATE", "HIGH"}


@dataclass(frozen=True)
class CalorieCalculation:
    calories: Decimal | None
    status: str
    met_used: Decimal
    user_weight_used_kg: Decimal | None


def safe_decimal(value: object) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    return result if result.is_finite() else None


def normalize_intensity(value: str | None) -> tuple[str, bool]:
    if value is None or not value.strip():
        return "MODERATE", True
    normalized = value.strip().upper()
    if normalized not in VALID_INTENSITIES:
        raise ValueError("운동 강도는 LOW, MODERATE, HIGH 중 하나여야 합니다.")
    return normalized, False


def select_met(exercise: object, intensity: str) -> Decimal:
    value = safe_decimal(getattr(exercise, f"met_{intensity.lower()}", None))
    if value is None or value <= 0:
        raise ValueError("운동에 유효한 MET 값이 설정되어 있지 않습니다.")
    return value


def calculate_estimated_calories(
    met_value: object, user_weight_kg: object, workout_minutes: object
) -> Decimal:
    met = safe_decimal(met_value)
    weight = safe_decimal(user_weight_kg)
    minutes = safe_decimal(workout_minutes)
    if met is None or met <= 0:
        raise ValueError("MET 값은 0보다 커야 합니다.")
    if weight is None or weight <= 0:
        raise ValueError("사용자 체중은 0보다 커야 합니다.")
    if minutes is None or minutes <= 0:
        raise ValueError("운동시간은 0보다 커야 합니다.")
    return (met * Decimal("3.5") * weight / Decimal("200") * minutes).quantize(
        Decimal("0.1"), rounding=ROUND_HALF_UP
    )


def calculate_for_record(
    met_value: object, user_weight_kg: object, workout_minutes: object
) -> CalorieCalculation:
    met = safe_decimal(met_value)
    if met is None or met <= 0:
        raise ValueError("MET 값은 0보다 커야 합니다.")
    minutes = safe_decimal(workout_minutes)
    weight = safe_decimal(user_weight_kg)
    if minutes is None or minutes <= 0:
        return CalorieCalculation(None, "INVALID_DURATION", met, weight if weight and weight > 0 else None)
    if weight is None or weight <= 0:
        return CalorieCalculation(None, "WEIGHT_REQUIRED", met, None)
    return CalorieCalculation(
        calculate_estimated_calories(met, weight, minutes), "CALCULATED", met, weight
    )


def calculate_training_volume(
    weight_kg: object, *, total_repetitions: object
) -> Decimal | None:
    """The current record stores total completed reps, so sets must not be multiplied again."""
    weight = safe_decimal(weight_kg)
    repetitions = safe_decimal(total_repetitions)
    if weight is None or weight <= 0 or repetitions is None or repetitions <= 0:
        return None
    return (weight * repetitions).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_set_training_volume(
    sets: object, *, completed_only: bool = True,
) -> Decimal | None:
    """Sum completed set volume without assuming equal weights or repetitions."""
    total = Decimal("0")
    has_volume = False
    for item in sets:
        weight = safe_decimal(getattr(item, "weight_kg", None))
        repetitions = safe_decimal(getattr(item, "repetition_count", None))
        is_completed = getattr(item, "is_completed", True)
        if (
            (is_completed or not completed_only)
            and weight is not None and weight > 0
            and repetitions is not None and repetitions > 0
        ):
            total += weight * repetitions
            has_volume = True
    return (
        total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if has_volume else None
    )
