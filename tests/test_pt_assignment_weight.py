from decimal import Decimal
from pathlib import Path

import pytest
from pydantic import ValidationError

from backend.models.pt_assignment import PtAssignment
from backend.pt_assignment_schemas import PtAssignmentCreate, PtAssignmentUpdate


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def assignment_payload(**overrides):
    payload = {
        "member_id": 2,
        "exercise_id": 1,
        "assigned_date": "2026-07-24",
        "target_sets": 3,
        "target_reps": 10,
    }
    payload.update(overrides)
    return payload


def test_pt_assignment_accepts_optional_positive_weight():
    weighted = PtAssignmentCreate(**assignment_payload(weight_kg="15"))
    bodyweight = PtAssignmentCreate(**assignment_payload(weight_kg=None))

    assert weighted.weight_kg == Decimal("15")
    assert bodyweight.weight_kg is None


def test_pt_assignment_normalizes_zero_weight_to_none():
    created = PtAssignmentCreate(**assignment_payload(weight_kg=0))
    updated = PtAssignmentUpdate(weight_kg="0.00")

    assert created.weight_kg is None
    assert updated.weight_kg is None
    assert updated.model_dump(exclude_unset=True) == {"weight_kg": None}


def test_pt_assignment_rejects_negative_weight():
    with pytest.raises(ValidationError):
        PtAssignmentCreate(**assignment_payload(weight_kg="-0.01"))


def test_pt_assignment_weight_can_be_updated():
    first_update = PtAssignmentUpdate(weight_kg="10")
    second_update = PtAssignmentUpdate(weight_kg="20")

    assert first_update.weight_kg == Decimal("10")
    assert second_update.weight_kg == Decimal("20")


def test_pt_assignment_model_column_is_nullable_decimal_6_2():
    column = PtAssignment.__table__.c.weight_kg

    assert column.nullable is True
    assert column.type.precision == 6
    assert column.type.scale == 2


def test_pt_coaching_uses_verified_assignment_weight_and_wins_over_routine():
    source = (
        PROJECT_ROOT / "frontend" / "js" / "coaching.js"
    ).read_text(encoding="utf-8")

    assert "normalizeRecordWeightKg(coachingAssignment?.weight_kg)" in source
    assert "weight_kg: normalizeRecordWeightKg(assignment.weight_kg)" in source
    assert source.index("if (isPtAssignmentRequest)") < source.index(
        "const validSavedPlan"
    )
    assert source.index("clearCoachingPlan();", source.index(
        "if (isPtAssignmentRequest)"
    )) < source.index("const validSavedPlan")

    workout_router = (
        PROJECT_ROOT / "backend" / "routers" / "workout.py"
    ).read_text(encoding="utf-8")
    assert "record_weight_kg = assignment.weight_kg" in workout_router
    assert "weight_kg=record_weight_kg" in workout_router
    assert "weight_value=record_weight_kg" in workout_router


def test_pt_assignment_weight_ui_and_migrations_are_connected():
    trainer_html = (
        PROJECT_ROOT / "frontend" / "trainer_assignments.html"
    ).read_text(encoding="utf-8")
    trainer_js = (
        PROJECT_ROOT / "frontend" / "js" / "trainer_assignments.js"
    ).read_text(encoding="utf-8")
    member_js = (
        PROJECT_ROOT / "frontend" / "js" / "pt_assignments.js"
    ).read_text(encoding="utf-8")
    migration = (
        PROJECT_ROOT / "migrations" / "20260724_add_pt_assignment_weight.sql"
    ).read_text(encoding="utf-8")
    rollback = (
        PROJECT_ROOT
        / "migrations"
        / "20260724_add_pt_assignment_weight_rollback.sql"
    ).read_text(encoding="utf-8")

    assert 'id="assignmentWeightKg"' in trainer_html
    assert "weight_kg: weightKg" in trainer_js
    assert "item.weight_kg ?? \"\"" in trainer_js
    assert "맨몸 또는 중량 없음" in member_js
    assert "ADD COLUMN weight_kg DECIMAL(6,2) NULL" in migration
    assert "DROP COLUMN weight_kg" in rollback
