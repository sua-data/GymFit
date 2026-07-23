from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models import Gym, TrainerProfile, User, UserGym
from backend.routers.pt import get_current_user
from backend.services.notification_service import create_notification


router = APIRouter(prefix="/api/admin", tags=["admin"])
KST = ZoneInfo("Asia/Seoul")
TRAINER_STATUSES = ("PENDING", "APPROVED", "REJECTED")
EMPLOYMENT_STATUSES = ("NONE", "PENDING", "APPROVED", "REJECTED")


class TrainerReviewReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)

    @field_validator("reason")
    @classmethod
    def clean_reason(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("사유를 입력해 주세요.")
        return cleaned


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.account_type != "ADMIN":
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다.")
    return current_user


def trainer_statement():
    return (
        select(User)
        .options(
            selectinload(User.trainer_profile),
            selectinload(User.trainer_specialties),
            selectinload(User.trainer_certifications),
        )
        .where(User.account_type == "TRAINER", User.is_active.is_(True))
    )


def trainer_gym(db: Session, user_id: int) -> dict | None:
    gym = db.scalar(
        select(Gym)
        .join(UserGym, UserGym.gym_id == Gym.gym_id)
        .where(UserGym.user_id == user_id, Gym.is_active.is_(True))
    )
    if gym is None:
        return None
    return {
        "gym_id": gym.gym_id,
        "gym_name": gym.gym_name,
        "road_address": gym.road_address,
    }


def evidence_exists(item) -> bool:
    storage_path = str(item.evidence_storage_path or "").strip()
    return bool(storage_path and Path(storage_path).is_file())


def serialize_trainer(db: Session, trainer: User) -> dict:
    profile = trainer.trainer_profile
    reviewer = db.get(User, profile.reviewed_by) if profile and profile.reviewed_by else None
    certifications = [
        item for item in trainer.trainer_certifications
        if getattr(item, "is_active", True)
    ]
    return {
        "user_id": trainer.user_id,
        "name": trainer.name,
        "email": trainer.email,
        "login_provider": trainer.login_provider,
        "created_at": trainer.created_at,
        "approval_status": profile.approval_status if profile else None,
        "career_years": profile.career_years if profile else None,
        "introduction": profile.introduction if profile else None,
        "rejection_reason": profile.rejection_reason if profile else None,
        "reviewed_by": profile.reviewed_by if profile else None,
        "reviewer_name": reviewer.name if reviewer else None,
        "reviewed_at": profile.reviewed_at if profile else None,
        "gym": trainer_gym(db, trainer.user_id),
        "specialties": [item.specialty_name for item in trainer.trainer_specialties],
        "certifications": [
            {
                "certification_id": item.trainer_certification_id,
                "certification_name": item.certification_name,
                "issuer": item.issuer,
                "certification_number": item.certification_number,
                "acquired_date": item.acquired_date,
                "evidence_image_url": item.evidence_image_url,
                "has_evidence": evidence_exists(item),
            }
            for item in certifications
        ],
        "has_valid_evidence": any(evidence_exists(item) for item in certifications),
        "employment_status": profile.employment_status if profile else "NONE",
        "employment_evidence_url": (
            f"/api/admin/employments/{trainer.user_id}/evidence"
            if profile and profile.employment_storage_path
            else None
        ),
        "employment_original_name": profile.employment_original_name if profile else None,
        "employment_rejection_reason": profile.employment_rejection_reason if profile else None,
        "employment_reviewed_at": profile.employment_reviewed_at if profile else None,
        "has_employment_evidence": bool(
            profile
            and profile.employment_storage_path
            and Path(profile.employment_storage_path).is_file()
        ),
    }


@router.get("/dashboard")
def read_admin_dashboard(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    counts = {
        value: db.scalar(
            select(func.count(User.user_id))
            .join(TrainerProfile, TrainerProfile.user_id == User.user_id)
            .where(
                User.account_type == "TRAINER",
                User.is_active.is_(True),
                TrainerProfile.approval_status == value,
            )
        ) or 0
        for value in TRAINER_STATUSES
    }
    trainers = db.scalars(
        trainer_statement()
        .join(TrainerProfile, TrainerProfile.user_id == User.user_id)
        .where(TrainerProfile.approval_status == "PENDING")
        .order_by(User.created_at.desc(), User.user_id.desc())
        .limit(5)
    ).unique().all()
    return {
        "pending_count": counts["PENDING"],
        "status_counts": counts,
        "recent_applications": [serialize_trainer(db, trainer) for trainer in trainers],
    }


@router.get("/trainers")
def list_trainers(
    review_status: str = Query("PENDING", alias="status"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    normalized = review_status.upper()
    if normalized not in (*TRAINER_STATUSES, "ALL"):
        raise HTTPException(status_code=422, detail="올바른 승인 상태가 아닙니다.")
    statement = (
        trainer_statement()
        .join(TrainerProfile, TrainerProfile.user_id == User.user_id)
        .order_by(User.created_at.desc(), User.user_id.desc())
    )
    if normalized != "ALL":
        statement = statement.where(TrainerProfile.approval_status == normalized)
    trainers = db.scalars(statement).unique().all()
    return {
        "status": normalized,
        "items": [serialize_trainer(db, trainer) for trainer in trainers],
        "total": len(trainers),
    }


@router.get("/trainers/{user_id}")
def read_trainer(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    trainer = db.scalar(trainer_statement().where(User.user_id == user_id))
    if trainer is None or trainer.trainer_profile is None:
        raise HTTPException(status_code=404, detail="트레이너 신청 정보를 찾을 수 없습니다.")
    return serialize_trainer(db, trainer)


def change_approval_status(
    db: Session,
    trainer_id: int,
    admin_id: int,
    next_status: str,
    rejection_reason: str | None = None,
) -> dict:
    trainer = db.scalar(
        trainer_statement().where(User.user_id == trainer_id).with_for_update()
    )
    if trainer is None or trainer.trainer_profile is None:
        raise HTTPException(status_code=404, detail="트레이너 신청 정보를 찾을 수 없습니다.")
    profile = trainer.trainer_profile
    if profile.approval_status != "PENDING":
        raise HTTPException(status_code=409, detail="승인 대기 상태인 신청만 처리할 수 있습니다.")
    if next_status == "APPROVED":
        active_certifications = [
            item for item in trainer.trainer_certifications
            if getattr(item, "is_active", True)
        ]
        if not any(evidence_exists(item) for item in active_certifications):
            raise HTTPException(
                status_code=409,
                detail="유효한 자격증 증빙 이미지가 1개 이상 필요합니다.",
            )
    try:
        profile.approval_status = next_status
        profile.rejection_reason = None if next_status == "APPROVED" else rejection_reason
        profile.reviewed_by = admin_id
        profile.reviewed_at = datetime.now(KST).replace(tzinfo=None)
        is_approved = next_status == "APPROVED"
        create_notification(
            db,
            user_id=trainer.user_id,
            title="트레이너 승인이 완료되었습니다." if is_approved else "트레이너 승인이 거절되었습니다.",
            message=(
                "이제 GYMFIT 트레이너 기능을 사용할 수 있습니다."
                if is_approved
                else f"거절 사유: {rejection_reason}"
            ),
            notification_type=(
                "TRAINER_APPROVAL_APPROVED" if is_approved else "TRAINER_APPROVAL_REJECTED"
            ),
            target_url="/mypage",
            reference_id=trainer.user_id,
        )
        db.commit()
        return serialize_trainer(db, trainer)
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="트레이너 승인 상태를 변경하지 못했습니다.") from error


@router.post("/trainers/{user_id}/approve")
def approve_trainer(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return change_approval_status(db, user_id, admin.user_id, "APPROVED")


@router.post("/trainers/{user_id}/reject")
def reject_trainer(
    user_id: int,
    payload: TrainerReviewReasonRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return change_approval_status(
        db, user_id, admin.user_id, "REJECTED", payload.reason
    )


@router.post("/trainers/{user_id}/revoke")
def revoke_trainer_approval(
    user_id: int,
    payload: TrainerReviewReasonRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    trainer = db.scalar(
        trainer_statement().where(User.user_id == user_id).with_for_update()
    )
    if trainer is None or trainer.trainer_profile is None:
        raise HTTPException(status_code=404, detail="트레이너 정보를 찾을 수 없습니다.")
    profile = trainer.trainer_profile
    if profile.approval_status != "APPROVED":
        raise HTTPException(status_code=409, detail="승인된 트레이너만 승인을 취소할 수 있습니다.")
    try:
        profile.approval_status = "PENDING"
        profile.reviewed_by = None
        profile.reviewed_at = None
        profile.rejection_reason = None
        create_notification(
            db,
            user_id=trainer.user_id,
            title="트레이너 승인이 재검토 상태로 변경되었습니다.",
            message=f"승인 취소 사유: {payload.reason}",
            notification_type="TRAINER_APPROVAL_REVOKED",
            target_url="/mypage",
            reference_id=trainer.user_id,
        )
        db.commit()
        return serialize_trainer(db, trainer)
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="트레이너 승인을 취소하지 못했습니다.") from error


@router.get("/employments")
def list_employment_reviews(
    review_status: str = Query("PENDING", alias="status"),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    normalized = review_status.upper()
    if normalized not in (*EMPLOYMENT_STATUSES, "ALL"):
        raise HTTPException(status_code=422, detail="올바른 소속 승인 상태가 아닙니다.")
    statement = (
        trainer_statement()
        .join(TrainerProfile, TrainerProfile.user_id == User.user_id)
        .order_by(User.created_at.desc(), User.user_id.desc())
    )
    if normalized != "ALL":
        statement = statement.where(TrainerProfile.employment_status == normalized)
    trainers = db.scalars(statement).unique().all()
    return {
        "status": normalized,
        "items": [serialize_trainer(db, trainer) for trainer in trainers],
        "total": len(trainers),
    }


@router.get("/employments/{user_id}")
def read_employment_review(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    del admin
    trainer = db.scalar(trainer_statement().where(User.user_id == user_id))
    if trainer is None or trainer.trainer_profile is None:
        raise HTTPException(status_code=404, detail="트레이너 소속 정보를 찾을 수 없습니다.")
    return serialize_trainer(db, trainer)


@router.get("/employments/{user_id}/evidence")
def read_employment_evidence(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    del admin
    profile = db.scalar(
        select(TrainerProfile).where(TrainerProfile.user_id == user_id)
    )
    if profile is None or not profile.employment_storage_path:
        raise HTTPException(status_code=404, detail="소속 증빙을 찾을 수 없습니다.")
    path = Path(profile.employment_storage_path).resolve()
    expected = Path(__file__).resolve().parents[2] / "uploads" / "trainer_employment"
    if expected.resolve() not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="소속 증빙을 찾을 수 없습니다.")
    return FileResponse(path)


def change_employment_status(
    db: Session,
    trainer_id: int,
    admin_id: int,
    next_status: str,
    reason: str | None = None,
) -> dict:
    trainer = db.scalar(
        trainer_statement().where(User.user_id == trainer_id).with_for_update()
    )
    if trainer is None or trainer.trainer_profile is None:
        raise HTTPException(status_code=404, detail="트레이너 소속 정보를 찾을 수 없습니다.")
    profile = trainer.trainer_profile
    if profile.employment_status != "PENDING":
        raise HTTPException(status_code=409, detail="소속 승인 대기 상태만 처리할 수 있습니다.")
    if next_status == "APPROVED":
        if trainer_gym(db, trainer.user_id) is None:
            raise HTTPException(status_code=409, detail="선택된 헬스장이 없습니다.")
        if not profile.employment_storage_path or not Path(profile.employment_storage_path).is_file():
            raise HTTPException(status_code=409, detail="유효한 재직 또는 소속 증빙 이미지가 필요합니다.")
    try:
        profile.employment_status = next_status
        profile.employment_reviewed_by = admin_id
        profile.employment_reviewed_at = datetime.now(KST).replace(tzinfo=None)
        profile.employment_rejection_reason = None if next_status == "APPROVED" else reason
        approved = next_status == "APPROVED"
        create_notification(
            db,
            user_id=trainer.user_id,
            title="헬스장 소속 승인이 완료되었습니다." if approved else "헬스장 소속 승인이 거절되었습니다.",
            message=(
                "새 헬스장의 관리 기능을 사용할 수 있습니다."
                if approved else f"거절 사유: {reason}"
            ),
            notification_type=(
                "TRAINER_EMPLOYMENT_APPROVED" if approved else "TRAINER_EMPLOYMENT_REJECTED"
            ),
            target_url="/my-gym",
            reference_id=trainer.user_id,
        )
        db.commit()
        return serialize_trainer(db, trainer)
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="헬스장 소속 승인 상태를 변경하지 못했습니다.") from error


@router.post("/employments/{user_id}/approve")
def approve_employment(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return change_employment_status(db, user_id, admin.user_id, "APPROVED")


@router.post("/employments/{user_id}/reject")
def reject_employment(
    user_id: int,
    payload: TrainerReviewReasonRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    return change_employment_status(
        db, user_id, admin.user_id, "REJECTED", payload.reason
    )
