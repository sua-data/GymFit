from decimal import Decimal

from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert
from sqlalchemy.orm import Session

from backend.models import Gym


class GymSelection(BaseModel):
    provider: str = Field(max_length=20)
    external_place_id: str = Field(min_length=1, max_length=100)
    gym_name: str = Field(min_length=1, max_length=150)
    road_address: str = Field(min_length=1, max_length=255)
    address: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=50)
    place_url: str | None = Field(default=None, max_length=500)
    category_name: str | None = Field(default=None, max_length=255)
    latitude: Decimal | None = None
    longitude: Decimal | None = None

    @field_validator("provider")
    @classmethod
    def validate_provider(cls, value: str) -> str:
        normalized = value.strip().upper()
        if normalized != "KAKAO":
            raise ValueError("지원하지 않는 장소 제공자입니다.")
        return normalized

    @field_validator("external_place_id", "gym_name", "road_address")
    @classmethod
    def clean_required_text(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("선택한 장소 정보가 올바르지 않습니다.")
        return cleaned

    @field_validator("address", "phone", "place_url", "category_name")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not Decimal("-90") <= value <= Decimal("90"):
            raise ValueError("위도 값이 올바르지 않습니다.")
        return value

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, value: Decimal | None) -> Decimal | None:
        if value is not None and not Decimal("-180") <= value <= Decimal("180"):
            raise ValueError("경도 값이 올바르지 않습니다.")
        return value


def select_or_create_gym(db: Session, selection: GymSelection) -> Gym:
    values = selection.model_dump()
    statement = insert(Gym).values(**values)
    statement = statement.on_duplicate_key_update(
        gym_name=statement.inserted.gym_name,
        road_address=statement.inserted.road_address,
        address=statement.inserted.address,
        phone=statement.inserted.phone,
        place_url=statement.inserted.place_url,
        category_name=statement.inserted.category_name,
        latitude=statement.inserted.latitude,
        longitude=statement.inserted.longitude,
        is_active=True,
    )
    db.execute(statement)
    gym = db.scalar(
        select(Gym).where(
            Gym.provider == selection.provider,
            Gym.external_place_id == selection.external_place_id,
        )
    )
    if gym is None:
        raise RuntimeError("헬스장 정보를 저장하지 못했습니다.")
    return gym
