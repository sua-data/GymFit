from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import MemberGoal, MemberProfile, User


router = APIRouter(prefix="/api/users", tags=["users"])

GOAL_NAMES = {
    "WEIGHT_LOSS": "체중 감량",
    "MUSCLE_GAIN": "근력 증가",
    "BODY_SHAPE": "체형 관리",
    "HEALTH": "건강 유지",
}
EXERCISE_LEVELS = {"BEGINNER", "INTERMEDIATE", "ADVANCED"}


class UserProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    exercise_level: str | None = None
    goals: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("이름을 입력해 주세요.")
        return cleaned

    @field_validator("exercise_level")
    @classmethod
    def validate_level(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip().upper()
        if normalized not in EXERCISE_LEVELS:
            raise ValueError("지원하지 않는 운동 수준입니다.")
        return normalized

    @field_validator("goals")
    @classmethod
    def validate_goals(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        normalized = list(dict.fromkeys(item.strip().upper() for item in value))
        if not normalized or any(item not in GOAL_NAMES for item in normalized):
            raise ValueError("지원하지 않는 운동 목표입니다.")
        return normalized


def get_active_user(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User)
        .options(
            selectinload(User.member_profile),
            selectinload(User.member_goals),
            selectinload(User.trainer_profile),
        )
        .where(User.user_id == user_id, User.is_active.is_(True))
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자 정보를 찾을 수 없습니다.",
        )
    return user


def serialize_user(user: User) -> dict:
    profile = user.member_profile
    trainer_profile = user.trainer_profile
    return {
        "user_id": user.user_id,
        "account_type": user.account_type,
        "name": user.name,
        "email": user.email,
        "exercise_level": profile.exercise_level if profile else None,
        "goals": [
            {"goal_code": goal.goal_code, "goal_name": goal.goal_name}
            for goal in sorted(user.member_goals, key=lambda item: item.member_goal_id)
        ],
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "gym_name": trainer_profile.gym_name if trainer_profile else None,
        "trainer_approval_status": (
            trainer_profile.approval_status if trainer_profile else None
        ),
    }


@router.get("/{user_id}")
def read_user_profile(user_id: int, db: Session = Depends(get_db)) -> dict:
    return serialize_user(get_active_user(db, user_id))


@router.patch("/{user_id}")
def update_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
) -> dict:
    user = get_active_user(db, user_id)

    if user.account_type == "TRAINER":
        if payload.exercise_level is not None or payload.goals is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="트레이너 계정은 운동 목표와 수준을 변경할 수 없습니다.",
            )

    try:
        user.name = payload.name

        if user.account_type != "TRAINER":
            if user.member_profile is None:
                user.member_profile = MemberProfile(user_id=user.user_id)
            if payload.exercise_level is not None:
                user.member_profile.exercise_level = payload.exercise_level
            if payload.goals is not None:
                db.execute(
                    delete(MemberGoal).where(MemberGoal.user_id == user.user_id)
                )
                db.add_all([
                    MemberGoal(
                        user_id=user.user_id,
                        goal_code=code,
                        goal_name=GOAL_NAMES[code],
                    )
                    for code in payload.goals
                ])

        db.commit()
        db.expire(user)
        return serialize_user(get_active_user(db, user_id))
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필을 저장하지 못했습니다.",
        )
