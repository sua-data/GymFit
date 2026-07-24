from types import SimpleNamespace
from decimal import Decimal

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from backend.routers.routine import require_member
from backend.routers.user import UserProfileUpdate


def test_routine_recommendation_allows_member():
    require_member(SimpleNamespace(account_type="MEMBER"))


def test_routine_recommendation_rejects_trainer():
    with pytest.raises(HTTPException) as error:
        require_member(SimpleNamespace(account_type="TRAINER"))

    assert error.value.status_code == 403


def test_member_body_profile_accepts_nullable_decimal_values():
    payload = UserProfileUpdate(
        name="회원",
        height_cm=165.5,
        weight_kg=55.25,
    )

    assert payload.height_cm == Decimal("165.5")
    assert payload.weight_kg == Decimal("55.25")

    cleared = UserProfileUpdate(name="회원", height_cm=None, weight_kg=None)
    assert cleared.height_cm is None
    assert cleared.weight_kg is None


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("height_cm", 99),
        ("height_cm", 251),
        ("weight_kg", 29),
        ("weight_kg", 301),
    ],
)
def test_member_body_profile_rejects_out_of_range_values(field, value):
    with pytest.raises(ValidationError):
        UserProfileUpdate(name="회원", **{field: value})
