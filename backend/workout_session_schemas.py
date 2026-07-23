from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, model_validator


class WorkoutSessionItemInput(BaseModel):
    exercise_id: int | None = Field(default=None, gt=0)
    user_exercise_id: int | None = Field(default=None, gt=0)
    exercise_name: str = Field(min_length=1, max_length=100)
    weight_value: Decimal | None = Field(default=None, ge=0, le=99999.99)
    weight_text: str | None = Field(default=None, max_length=100)
    repetitions: int | None = Field(default=None, ge=1, le=10000)
    completed_sets: int | None = Field(default=None, ge=1, le=100)
    rpe: int | None = Field(default=None, ge=1, le=10)
    workout_minutes: int | None = Field(default=None, ge=1, le=1440)
    memo: str | None = Field(default=None, max_length=2000)


class WorkoutSessionCreate(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    workout_date: date
    started_at: datetime
    completed_at: datetime
    workout_part: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    memo: str | None = Field(default=None, max_length=5000)
    items: list[WorkoutSessionItemInput] = Field(default_factory=list, max_length=50)

    @model_validator(mode="after")
    def validate_time(self):
        if self.started_at >= self.completed_at:
            raise ValueError("종료 시간은 시작 시간보다 늦어야 합니다.")
        return self


class WorkoutSessionUpdate(WorkoutSessionCreate):
    pass


class WorkoutMediaItem(BaseModel):
    media_id: int
    media_type: str
    media_url: str
    thumbnail_url: str | None
    duration_seconds: int | None
    file_size: int | None


class WorkoutSessionExerciseItem(BaseModel):
    item_id: int
    exercise_id: int | None
    user_exercise_id: int | None
    exercise_name: str
    weight_value: Decimal | None
    weight_text: str | None
    repetitions: int | None
    completed_sets: int | None
    rpe: int | None
    workout_minutes: int | None
    memo: str | None
    posture_score: int | None
    feedback: str | None
    display_order: int
    media: list[WorkoutMediaItem] = Field(default_factory=list)


class WorkoutSessionSummary(BaseModel):
    workout_record_id: int
    record_type: str
    title: str
    workout_date: date
    started_at: datetime
    completed_at: datetime | None
    workout_minutes: int
    workout_part: str | None
    trainer_id: int | None
    trainer_name: str | None
    location: str | None
    memo: str | None
    posture_score: int | None
    item_count: int
    exercise_names: list[str]
    has_media: bool


class WorkoutSessionDetail(WorkoutSessionSummary):
    calories: int | None
    best_posture_score: int | None
    feedback_title: str | None
    feedback: str | None
    image_url: str | None
    items: list[WorkoutSessionExerciseItem]


class WorkoutSessionList(BaseModel):
    items: list[WorkoutSessionSummary]
    total: int
    limit: int
    offset: int
