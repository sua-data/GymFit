from datetime import date, datetime

from pydantic import BaseModel, Field


class PTRequestCreate(BaseModel):
    member_id: int = Field(gt=0)


class PTUserSummary(BaseModel):
    user_id: int
    name: str
    email: str
    gym_name: str | None = None
    career_years: int | None = None


class PTRelationshipResponse(BaseModel):
    trainer_member_id: int
    trainer_id: int
    member_id: int
    status: str
    started_at: date | None = None
    ended_at: date | None = None
    created_at: datetime
    trainer_name: str
    trainer_email: str
    member_name: str
    member_email: str
    gym_name: str | None = None
    career_years: int | None = None


class PTMemberSearchItem(PTUserSummary):
    relationship_status: str | None = None
    trainer_member_id: int | None = None


class PTListResponse(BaseModel):
    items: list[PTRelationshipResponse]


class PTMemberSearchResponse(BaseModel):
    items: list[PTMemberSearchItem]


class PTMyTrainerResponse(BaseModel):
    item: PTRelationshipResponse | None = None


class SentPtRequestResponse(BaseModel):
    trainer_member_id: int
    member_id: int
    member_name: str
    member_email: str
    member_gym_name: str | None = None
    status: str
    created_at: datetime


class ReceivedPtRequestResponse(BaseModel):
    trainer_member_id: int
    trainer_id: int
    trainer_name: str
    trainer_email: str
    trainer_gym_name: str | None = None
    trainer_career_years: int | None = None
    status: str
    created_at: datetime


class SentPtRequestListResponse(BaseModel):
    items: list[SentPtRequestResponse]


class ReceivedPtRequestListResponse(BaseModel):
    items: list[ReceivedPtRequestResponse]
