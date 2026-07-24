from datetime import datetime
from decimal import Decimal
from uuid import uuid4
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator, model_validator
from sqlalchemy import delete, or_, select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import (
    Gym,
    MemberGoal,
    MemberProfile,
    PtSchedule,
    TrainerMember,
    User,
    UserGym,
)
from backend.security import enforce_self, get_current_user
from backend.services.gym_service import GymSelection, select_or_create_gym
from backend.services.password_service import hash_password, verify_password
from backend.routers.trainer_employment import safe_unlink as safe_unlink_employment
from backend.services.pt_service import (
    get_pending_pt_request_count,
    has_active_trainer,
)


router = APIRouter(prefix="/api/users", tags=["users"])
KST = ZoneInfo("Asia/Seoul")

GOAL_NAMES = {
    "WEIGHT_LOSS": "체중 감량",
    "MUSCLE_GAIN": "근력 증가",
    "BODY_SHAPE": "체형 관리",
    "HEALTH": "건강 유지",
}
EXERCISE_LEVELS = {"BEGINNER", "INTERMEDIATE", "ADVANCED"}


class UserProfileUpdate(BaseModel):
    name: str | None = None
    goal: str | None = None
    level: str | None = None
    weekly_workout_days: int | None = Field(
        default=None,
        ge=1,
        le=7,
    )

    height_cm: Decimal | None = Field(
        default=None,
        ge=Decimal("100"),
        le=Decimal("250"),
    )

    weight_kg: Decimal | None = Field(
        default=None,
        ge=Decimal("30"),
        le=Decimal("300"),
    )

    @field_validator(
        "height_cm",
        "weight_kg",
        mode="before",
    )
    @classmethod
    def normalize_optional_decimal(
        cls,
        value,
    ):
        if value in ("", None):
            return None

        return value

    @field_validator(
        "height_cm",
        "weight_kg",
    )
    @classmethod
    def limit_decimal_places(
        cls,
        value: Decimal | None,
    ) -> Decimal | None:
        if value is None:
            return None

        if value.as_tuple().exponent < -2:
            raise ValueError(
                "소수점은 둘째 자리까지만 입력할 수 있습니다."
            )

        return value


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
        "gender": user.gender,
        "birth_date": user.birth_date,
        "login_provider": user.login_provider,
        "height_cm": float(profile.height_cm) if profile and profile.height_cm is not None else None,
        "weight_kg": float(profile.weight_kg) if profile and profile.weight_kg is not None else None,
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
        "trainer_employment_status": (
            trainer_profile.employment_status if trainer_profile else None
        ),
        "trainer_employment_rejection_reason": (
            trainer_profile.employment_rejection_reason if trainer_profile else None
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


def serialize_my_gym(gym: Gym | None) -> dict | None:
    if gym is None:
        return None
    return {
        "gym_id": gym.gym_id,
        "provider": gym.provider,
        "external_place_id": gym.external_place_id,
        "gym_name": gym.gym_name,
        "road_address": gym.road_address,
        "address": gym.address,
        "phone": gym.phone,
        "place_url": gym.place_url,
        "category_name": gym.category_name,
        "latitude": float(gym.latitude) if gym.latitude is not None else None,
        "longitude": float(gym.longitude) if gym.longitude is not None else None,
    }


def get_linked_gym(db: Session, user_id: int) -> Gym | None:
    return db.scalar(
        select(Gym)
        .join(UserGym, UserGym.gym_id == Gym.gym_id)
        .where(UserGym.user_id == user_id, Gym.is_active.is_(True))
    )


def ensure_gym_is_editable(user: User) -> None:
    # 트레이너 자격 승인과 헬스장 소속 승인은 독립적이다.
    # 승인된 트레이너도 헬스장을 변경할 수 있다.
    del user


@router.get("/me/gym")
def read_my_gym(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = get_active_user(db, current_user.user_id)
    return {
        "gym": serialize_my_gym(get_linked_gym(db, user.user_id)),
        "can_edit": True,
        "employment_status": (
            user.trainer_profile.employment_status
            if user.account_type == "TRAINER" and user.trainer_profile
            else None
        ),
        "employment_rejection_reason": (
            user.trainer_profile.employment_rejection_reason
            if user.account_type == "TRAINER" and user.trainer_profile
            else None
        ),
    }


@router.patch("/me/gym")
def replace_my_gym(
    payload: GymSelection,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = get_active_user(db, current_user.user_id)
    ensure_gym_is_editable(user)
    old_evidence_path = None
    try:
        gym = select_or_create_gym(db, payload)
        link = db.scalar(
            select(UserGym)
            .where(UserGym.user_id == user.user_id)
            .with_for_update()
        )
        gym_changed = link is None or link.gym_id != gym.gym_id
        if link is None:
            db.add(UserGym(user_id=user.user_id, gym_id=gym.gym_id))
        else:
            link.gym_id = gym.gym_id
        if user.account_type == "TRAINER" and user.trainer_profile:
            profile = user.trainer_profile
            profile.gym_name = gym.gym_name
            if gym_changed:
                old_evidence_path = profile.employment_storage_path
                profile.employment_status = "PENDING"
                profile.employment_evidence_url = None
                profile.employment_storage_path = None
                profile.employment_original_name = None
                profile.employment_reviewed_by = None
                profile.employment_reviewed_at = None
                profile.employment_rejection_reason = None
        db.commit()
        safe_unlink_employment(old_evidence_path)
        return {
            "gym": serialize_my_gym(get_linked_gym(db, user.user_id)),
            "can_edit": True,
            "employment_status": (
                user.trainer_profile.employment_status
                if user.account_type == "TRAINER" and user.trainer_profile
                else None
            ),
        }
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="헬스장 정보를 변경하지 못했습니다.",
        ) from error


@router.delete("/me/gym")
def disconnect_my_gym(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = get_active_user(db, current_user.user_id)
    ensure_gym_is_editable(user)
    old_evidence_path = None
    try:
        link = db.scalar(
            select(UserGym)
            .where(UserGym.user_id == user.user_id)
            .with_for_update()
        )
        if link is not None:
            db.delete(link)
        if user.account_type == "TRAINER" and user.trainer_profile:
            profile = user.trainer_profile
            old_evidence_path = profile.employment_storage_path
            profile.gym_name = None
            profile.employment_status = "NONE"
            profile.employment_evidence_url = None
            profile.employment_storage_path = None
            profile.employment_original_name = None
            profile.employment_reviewed_by = None
            profile.employment_reviewed_at = None
            profile.employment_rejection_reason = None
        db.commit()
        safe_unlink_employment(old_evidence_path)
        return {"gym": None, "can_edit": True, "employment_status": "NONE"}
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="헬스장 연결을 해제하지 못했습니다.",
        ) from error


@router.get("/{user_id}")
def read_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    enforce_self(current_user, user_id)
    return serialize_user(get_active_user(db, user_id), db)


@router.patch("/{user_id}")
def update_user_profile(
    user_id: int,
    payload: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    enforce_self(current_user, user_id)
    user = get_active_user(db, user_id)

    try:
        user.name = payload.name
        member_fields = {
            "exercise_level",
            "weekly_workout_days",
            "goals",
            "height_cm",
            "weight_kg",
        }
        if (
            user.account_type != "MEMBER"
            and member_fields.intersection(payload.model_fields_set)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="회원 운동 프로필은 일반 회원만 수정할 수 있습니다.",
            )

        if user.member_profile is None and (
            payload.exercise_level is not None
            or payload.weekly_workout_days is not None
            or payload.height_cm is not None
            or payload.weight_kg is not None
        ):
            user.member_profile = MemberProfile(user_id=user.user_id)
        if payload.exercise_level is not None:
            user.member_profile.exercise_level = payload.exercise_level
        if payload.weekly_workout_days is not None:
            user.member_profile.weekly_workout_days = payload.weekly_workout_days
        if "height_cm" in payload.model_fields_set:
            if user.member_profile is None:
                user.member_profile = MemberProfile(user_id=user.user_id)
            user.member_profile.height_cm = payload.height_cm
        if "weight_kg" in payload.model_fields_set:
            if user.member_profile is None:
                user.member_profile = MemberProfile(user_id=user.user_id)
            user.member_profile.weight_kg = payload.weight_kg
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
    except HTTPException:
        db.rollback()
        raise
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    enforce_self(current_user, user_id)
    user = get_active_user(db, user_id)
    old_evidence_path = None

    try:
        link = db.scalar(select(UserGym).where(UserGym.user_id == user.user_id))
        if payload.gym_id is None:
            if link is not None:
                db.delete(link)
            if user.account_type == "TRAINER" and user.trainer_profile:
                profile = user.trainer_profile
                old_evidence_path = profile.employment_storage_path
                profile.gym_name = None
                profile.employment_status = "NONE"
                profile.employment_evidence_url = None
                profile.employment_storage_path = None
                profile.employment_original_name = None
                profile.employment_reviewed_by = None
                profile.employment_reviewed_at = None
                profile.employment_rejection_reason = None
        else:
            gym = db.scalar(
                select(Gym).where(Gym.gym_id == payload.gym_id, Gym.is_active.is_(True))
            )
            if gym is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="선택한 헬스장을 찾을 수 없습니다.",
                )
            gym_changed = link is None or link.gym_id != gym.gym_id
            if link is None:
                db.add(UserGym(user_id=user.user_id, gym_id=gym.gym_id))
            else:
                link.gym_id = gym.gym_id
            if user.account_type == "TRAINER" and user.trainer_profile:
                profile = user.trainer_profile
                profile.gym_name = gym.gym_name
                if gym_changed:
                    old_evidence_path = profile.employment_storage_path
                    profile.employment_status = "PENDING"
                    profile.employment_evidence_url = None
                    profile.employment_storage_path = None
                    profile.employment_original_name = None
                    profile.employment_reviewed_by = None
                    profile.employment_reviewed_at = None
                    profile.employment_rejection_reason = None
        db.commit()
        safe_unlink_employment(old_evidence_path)
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


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=8, max_length=100)
    new_password: str = Field(min_length=8, max_length=100)
    new_password_confirm: str = Field(min_length=8, max_length=100)

    @model_validator(mode="after")
    def validate_new_password_confirmation(self):
        if self.new_password != self.new_password_confirm:
            raise ValueError("새 비밀번호가 일치하지 않습니다.")
        return self


class WithdrawalRequest(BaseModel):
    confirmation_phrase: str = Field(min_length=1, max_length=20)
    current_password: str | None = Field(default=None, max_length=100)

    @field_validator("confirmation_phrase")
    @classmethod
    def validate_confirmation_phrase(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned != "회원 탈퇴":
            raise ValueError("확인 문구에 '회원 탈퇴'를 정확히 입력해 주세요.")
        return cleaned


@router.patch("/me/password")
def change_my_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = db.scalar(
        select(User)
        .where(
            User.user_id == current_user.user_id,
            User.is_active.is_(True),
        )
        .with_for_update()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자 정보를 찾을 수 없습니다.",
        )
    if user.login_provider != "LOCAL" or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Google 로그인 계정은 비밀번호를 변경할 수 없습니다.",
        )
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="현재 비밀번호가 올바르지 않습니다.",
        )
    if verify_password(payload.new_password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="새 비밀번호는 현재 비밀번호와 달라야 합니다.",
        )

    try:
        user.password_hash = hash_password(payload.new_password)
        user.must_change_password = False
        user.temporary_password_expires_at = None
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호를 변경하지 못했습니다.",
        ) from error

    return {"message": "비밀번호가 변경되었습니다."}


@router.post("/me/withdraw")
def withdraw_my_account(
    payload: WithdrawalRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    user = db.scalar(
        select(User)
        .where(
            User.user_id == current_user.user_id,
            User.is_active.is_(True),
        )
        .with_for_update()
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자 정보를 찾을 수 없습니다.",
        )

    if user.login_provider == "LOCAL":
        if not payload.current_password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호를 입력해 주세요.",
            )
        if not user.password_hash or not verify_password(
            payload.current_password,
            user.password_hash,
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="현재 비밀번호가 올바르지 않습니다.",
            )

    now = datetime.now(KST).replace(tzinfo=None)
    relationships = db.scalars(
        select(TrainerMember)
        .where(
            or_(
                TrainerMember.trainer_id == user.user_id,
                TrainerMember.member_id == user.user_id,
            ),
            TrainerMember.status.in_(("PENDING", "ACTIVE")),
        )
        .with_for_update()
    ).all()
    schedules = db.scalars(
        select(PtSchedule)
        .where(
            or_(
                PtSchedule.trainer_id == user.user_id,
                PtSchedule.member_id == user.user_id,
            ),
            PtSchedule.status == "SCHEDULED",
        )
        .with_for_update()
    ).all()

    try:
        for relationship in relationships:
            relationship.status = "ENDED"
            relationship.ended_at = now.date()
        for schedule in schedules:
            schedule.status = "CANCELLED"

        anonymized_key = f"{user.user_id}-{uuid4().hex}"
        user.email = f"deleted+{anonymized_key}@deleted.gymfit.local"
        user.name = "탈퇴 회원"
        user.google_sub = None
        user.password_hash = None
        user.must_change_password = False
        user.temporary_password_expires_at = None
        user.last_login_at = None
        user.is_active = False
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원 탈퇴를 처리하지 못했습니다.",
        ) from error

    return {
        "message": "회원 탈퇴가 완료되었습니다.",
        "cancelled_schedule_count": len(schedules),
        "ended_relationship_count": len(relationships),
    }
