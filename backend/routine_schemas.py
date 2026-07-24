from datetime import date, datetime

from typing import Literal

from pydantic import BaseModel, Field, field_validator


WeekdayCode = Literal["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"]


class RecommendationCreate(BaseModel):
    user_id: int = Field(gt=0)
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    workout_minutes: int = Field(default=40, ge=10, le=240)
    preferred_days: list[WeekdayCode] | None = Field(
        default=None, min_length=1, max_length=7
    )
    variant: int = Field(default=0, ge=0, le=1000)

    @field_validator("preferred_days")
    @classmethod
    def validate_preferred_days(cls, value):
        if value is not None and len(value) != len(set(value)):
            raise ValueError("선호 운동 요일은 중복될 수 없습니다.")
        return value


class RecommendationItemResponse(BaseModel):
    recommendation_item_id: int
    exercise_id: int | None
    user_exercise_id: int | None
    exercise_code: str | None
    exercise_name: str
    workout_date: date
    sequence_no: int
    recommended_sets: int
    recommended_reps: int
    difficulty: str
    coaching_supported: bool
    adjustment_type: str
    recommendation_reason: str
    previous_posture_score: int | None
    previous_completion_rate: float | None


class RecommendationResponse(BaseModel):
    recommendation_id: int
    user_id: int
    recommendation_date: date
    goal: str
    level: str
    days_per_week: int
    workout_minutes: int
    source_type: str
    status: str
    created_at: datetime
    recommended_days: list[WeekdayCode]
    daily_exercise_count: int
    recommendation_reason: str
    variant: int
    items: list[RecommendationItemResponse]


class RecommendationApplyRequest(BaseModel):
    replace_existing_recommendations: bool = True


class RecommendationSkipReason(BaseModel):
    plan_date: date
    exercise_id: int | None = None
    reason: str


class RecommendationApplyResponse(BaseModel):
    message: str
    recommendation_id: int
    created_count: int
    updated_count: int
    skipped_count: int
    skipped_reasons: list[RecommendationSkipReason]
    workout_plan_ids: list[int]
    affected_dates: list[date]
