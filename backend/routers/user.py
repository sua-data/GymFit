from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import Gym, MemberGoal, MemberProfile, User, UserGym
from backend.services.pt_service import (
    get_pending_pt_request_count,
    has_active_trainer,
)


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
    weekly_workout_days: int | None = Field(default=None, ge=1, le=7)

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


def serialize_user(user: User, db: Session) -> dict:
    profile = user.member_profile
    trainer_profile = user.trainer_profile
    gym_row = db.execute(
        select(UserGym, Gym)
        .join(Gym, Gym.gym_id == UserGym.gym_id)
        .where(UserGym.user_id == user.user_id, Gym.is_active.is_(True))
    ).first()
    gym = gym_row[1] if gym_row else None
    return {
        "user_id": user.user_id,
        "account_type": user.account_type,
        "name": user.name,
        "email": user.email,
        "exercise_level": profile.exercise_level if profile else None,
        "weekly_workout_days": profile.weekly_workout_days if profile else None,
        "goals": [
            {
                "goal_code": goal.goal_code,
                "goal_name": GOAL_NAMES.get(goal.goal_code, goal.goal_name),
            }
            for goal in sorted(user.member_goals, key=lambda item: item.member_goal_id)
        ],
        "created_at": user.created_at,
        "last_login_at": user.last_login_at,
        "gym_id": gym.gym_id if gym else None,
        "gym_name": gym.gym_name if gym else (trainer_profile.gym_name if trainer_profile else None),
        "gym_road_address": gym.road_address if gym else None,
        "gym_provider": gym.provider if gym else None,
        "gym_external_place_id": gym.external_place_id if gym else None,
        "trainer_approval_status": (
            trainer_profile.approval_status if trainer_profile else None
        ),
        "trainer_career_years": (
            trainer_profile.career_years if trainer_profile else None
        ),
        "has_active_trainer": has_active_trainer(
            db, user.user_id, user.account_type
        ),
        "pending_pt_request_count": get_pending_pt_request_count(
            db, user.user_id, user.account_type
        ),
    }


@router.get("/{user_id}")
def read_user_profile(user_id: int, db: Session = Depends(get_db)) -> dict:
    return serialize_user(get_active_user(db, user_id), db)


@router.patch("/{user_id}")
def update_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    db: Session = Depends(get_db),
) -> dict:
    user = get_active_user(db, user_id)

    try:
        user.name = payload.name

        if user.member_profile is None and (
            payload.exercise_level is not None
            or payload.weekly_workout_days is not None
        ):
            user.member_profile = MemberProfile(user_id=user.user_id)
        if payload.exercise_level is not None:
            user.member_profile.exercise_level = payload.exercise_level
        if payload.weekly_workout_days is not None:
            user.member_profile.weekly_workout_days = payload.weekly_workout_days
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
        return serialize_user(get_active_user(db, user_id), db)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="프로필을 저장하지 못했습니다.",
        )


class UserGymUpdate(BaseModel):
    gym_id: int | None = Field(default=None, gt=0)


@router.patch("/{user_id}/gym")
def update_user_gym(
    user_id: int,
    payload: UserGymUpdate,
    db: Session = Depends(get_db),
) -> dict:
    user = get_active_user(db, user_id)
    if (
        user.account_type == "TRAINER"
        and user.trainer_profile
        and user.trainer_profile.approval_status == "APPROVED"
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="승인 완료 후에는 소속 헬스장을 직접 변경할 수 없습니다.",
        )

    try:
        link = db.scalar(select(UserGym).where(UserGym.user_id == user.user_id))
        if payload.gym_id is None:
            if link is not None:
                db.delete(link)
            if user.account_type == "TRAINER" and user.trainer_profile:
                user.trainer_profile.gym_name = None
        else:
            gym = db.scalar(
                select(Gym).where(Gym.gym_id == payload.gym_id, Gym.is_active.is_(True))
            )
            if gym is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="선택한 헬스장을 찾을 수 없습니다.",
                )
            if link is None:
                db.add(UserGym(user_id=user.user_id, gym_id=gym.gym_id))
            else:
                link.gym_id = gym.gym_id
            if user.account_type == "TRAINER" and user.trainer_profile:
                user.trainer_profile.gym_name = gym.gym_name
        db.commit()
        return serialize_user(get_active_user(db, user_id), db)
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="헬스장 연결을 변경하지 못했습니다.",
        ) from error
