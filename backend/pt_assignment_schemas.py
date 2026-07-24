from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator, model_validator


class PtAssignmentWeightMixin(BaseModel):
    weight_kg: Decimal | None = Field(default=None, gt=0, le=9999.99)

    @field_validator("weight_kg", mode="before")
    @classmethod
    def normalize_zero_weight(cls, value):
        if value is None or value == "":
            return None
        try:
            if Decimal(str(value)) == 0:
                return None
        except (ValueError, ArithmeticError):
            return value
        return value


class PtAssignmentCreate(PtAssignmentWeightMixin):
    member_id: int = Field(gt=0)
    exercise_id: int | None = Field(default=None, gt=0)
    user_exercise_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=5000)
    assigned_date: date
    due_date: date | None = None
    target_sets: int | None = Field(default=None, ge=1, le=100)
    target_reps: int | None = Field(default=None, ge=1, le=10000)
    target_minutes: int | None = Field(default=None, ge=1, le=1440)

    @model_validator(mode="after")
    def validate_assignment(self):
        if (self.exercise_id is None) == (self.user_exercise_id is None):
            raise ValueError("기본 운동과 사용자 운동 중 하나만 선택해 주세요.")
        if not any(value is not None for value in (self.target_sets, self.target_reps, self.target_minutes)):
            raise ValueError("목표 세트, 횟수, 시간 중 하나 이상을 입력해 주세요.")
        if self.due_date is not None and self.due_date < self.assigned_date:
            raise ValueError("마감일은 배정일보다 빠를 수 없습니다.")
        self.description = self.description.strip() if self.description else None
        return self


class PtAssignmentUpdate(PtAssignmentWeightMixin):
    exercise_id: int | None = Field(default=None, gt=0)
    user_exercise_id: int | None = Field(default=None, gt=0)
    description: str | None = Field(default=None, max_length=5000)
    assigned_date: date | None = None
    due_date: date | None = None
    target_sets: int | None = Field(default=None, ge=1, le=100)
    target_reps: int | None = Field(default=None, ge=1, le=10000)
    target_minutes: int | None = Field(default=None, ge=1, le=1440)


class PtAssignmentComplete(BaseModel):
    workout_record_id: int = Field(gt=0)


class PtAssignmentItem(BaseModel):
    assignment_id: int
    trainer_member_id: int
    trainer_id: int
    trainer_name: str
    member_id: int
    member_name: str
    exercise_type: str
    exercise_id: int | None
    user_exercise_id: int | None
    exercise_name: str
    exercise_code: str | None
    title: str
    description: str | None
    assigned_date: date
    due_date: date | None
    target_sets: int | None
    target_reps: int | None
    target_minutes: int | None
    weight_kg: Decimal | None
    status: str
    is_overdue: bool
    completed_at: datetime | None
    workout_record_id: int | None
    created_at: datetime
    updated_at: datetime


class PtAssignmentResult(BaseModel):
    assignment: PtAssignmentItem
    completed_sets: int
    repetition_count: int
    workout_minutes: int
    calories: Decimal | None
    posture_score: int | None
    feedback_title: str | None
    feedback: str | None
    image_url: str | None
    trainer_feedback_id: int | None
    trainer_feedback_content: str | None
    record_source: str
    manual_note: str | None


class PtManualRecordCreate(BaseModel):
    completed_sets: int = Field(default=0, ge=0, le=100)
    repetition_count: int = Field(default=0, ge=0, le=10000)
    workout_minutes: int = Field(default=0, ge=0, le=1440)
    calories: int | None = Field(default=None, ge=0, le=10000)
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_activity(self):
        if self.completed_sets <= 0 and self.repetition_count <= 0 and self.workout_minutes <= 0:
            raise ValueError("완료 세트, 반복 횟수, 운동 시간 중 하나 이상을 입력해 주세요.")
        self.note = self.note.strip() if self.note else None
        return self


class PtCustomExerciseCreate(BaseModel):
    member_id: int = Field(gt=0)
    exercise_name: str = Field(min_length=1, max_length=100)
    category: str | None = Field(default=None, max_length=30)

    @model_validator(mode="after")
    def clean_values(self):
        self.exercise_name = self.exercise_name.strip()
        self.category = self.category.strip() if self.category else None
        if not self.exercise_name:
            raise ValueError("운동명을 입력해 주세요.")
        return self


class PtFeedbackWrite(BaseModel):
    content: str = Field(min_length=1, max_length=5000)


class PtFeedbackItem(BaseModel):
    feedback_id: int
    assignment_id: int
    workout_record_id: int
    trainer_id: int
    trainer_name: str
    member_id: int
    member_name: str
    assignment_title: str
    exercise_name: str
    completed_at: datetime | None
    posture_score: int | None
    image_url: str | None
    content: str
    created_at: datetime
    updated_at: datetime


class PtFeedbackList(BaseModel):
    items: list[PtFeedbackItem]
    total: int


class PtAssignmentList(BaseModel):
    items: list[PtAssignmentItem]
    total: int
