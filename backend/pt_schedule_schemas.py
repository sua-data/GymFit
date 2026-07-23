from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator
from backend.workout_session_schemas import WorkoutSessionItemInput


class PtScheduleCreate(BaseModel):
    member_id: int = Field(gt=0)
    start_at: datetime
    end_at: datetime
    location: str | None = Field(default=None, max_length=200)
    memo: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_time_range(self):
        if self.start_at >= self.end_at:
            raise ValueError("종료 시간은 시작 시간보다 늦어야 합니다.")
        return self


class PtScheduleUpdate(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    location: str | None = Field(default=None, max_length=200)
    memo: str | None = Field(default=None, max_length=2000)


class PtScheduleItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    schedule_id: int
    trainer_member_id: int
    trainer_id: int
    trainer_name: str
    member_id: int
    member_name: str
    start_at: datetime
    end_at: datetime
    location: str | None
    memo: str | None
    status: str
    created_at: datetime
    updated_at: datetime
    workout_record_id: int | None = None
    workout_item_ids: list[int] = Field(default_factory=list)


class PtScheduleCompleteRequest(BaseModel):
    title: str | None = Field(default=None, max_length=150)
    workout_part: str | None = Field(default=None, max_length=100)
    location: str | None = Field(default=None, max_length=200)
    memo: str | None = Field(default=None, max_length=5000)
    items: list[WorkoutSessionItemInput] = Field(default_factory=list, max_length=50)


class PtScheduleList(BaseModel):
    items: list[PtScheduleItem]
    total: int
