from datetime import date, datetime

from pydantic import BaseModel, Field


class RecommendationCreate(BaseModel):
    user_id: int = Field(gt=0)
    days_per_week: int | None = Field(default=None, ge=1, le=7)
    workout_minutes: int = Field(default=40, ge=10, le=240)


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
    items: list[RecommendationItemResponse]


class RecommendationApplyResponse(BaseModel):
    message: str
    recommendation_id: int
    created_count: int
    skipped_count: int
    workout_plan_ids: list[int]

