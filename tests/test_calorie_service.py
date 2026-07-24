from decimal import Decimal
from types import SimpleNamespace

import pytest

from backend.services.calorie_service import (
    calculate_estimated_calories,
    calculate_for_record,
    calculate_training_volume,
    normalize_intensity,
    select_met,
)


def test_weight_and_valid_duration_calculates_one_decimal():
    result = calculate_for_record(Decimal("5.0"), Decimal("70"), 30)
    assert result.status == "CALCULATED"
    assert result.calories == Decimal("183.8")
    assert result.user_weight_used_kg == Decimal("70")


def test_missing_weight_keeps_record_calories_null():
    result = calculate_for_record(Decimal("5.0"), None, 30)
    assert result.status == "WEIGHT_REQUIRED"
    assert result.calories is None
    assert result.user_weight_used_kg is None


def test_zero_duration_is_invalid_before_weight_check():
    result = calculate_for_record(Decimal("5.0"), None, 0)
    assert result.status == "INVALID_DURATION"
    assert result.calories is None


def test_missing_intensity_defaults_to_moderate_and_is_recorded():
    assert normalize_intensity(None) == ("MODERATE", True)
    assert normalize_intensity("  ") == ("MODERATE", True)
    assert normalize_intensity("high") == ("HIGH", False)


def test_met_selection_and_invalid_values_are_safe():
    exercise = SimpleNamespace(
        met_low=Decimal("3.5"), met_moderate=Decimal("5.0"), met_high=Decimal("6.0")
    )
    assert select_met(exercise, "MODERATE") == Decimal("5.0")
    with pytest.raises(ValueError):
        calculate_estimated_calories(0, 70, 30)
    with pytest.raises(ValueError):
        calculate_estimated_calories(5, Decimal("NaN"), 30)


def test_bodyweight_volume_is_null():
    assert calculate_training_volume(None, total_repetitions=30) is None


def test_weighted_volume_uses_total_completed_repetitions_once():
    assert calculate_training_volume(Decimal("20"), total_repetitions=30) == Decimal("600.00")


def test_decimal_rounding_is_half_up_to_one_decimal():
    assert calculate_estimated_calories(Decimal("3.5"), Decimal("65"), 17) == Decimal("67.7")
