from __future__ import annotations

import os
from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import TrainerCertification, TrainerProfile, User
from backend.routers.pt import get_current_user
from backend.security import require_trainer
from backend.services.notification_service import create_notification


router = APIRouter(prefix="/api/trainers/me/certifications", tags=["trainer-certifications"])
BASE_DIR = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = BASE_DIR / "uploads" / "trainer_certifications"
MAX_IMAGE_BYTES = int(os.getenv("TRAINER_CERTIFICATION_IMAGE_MAX_BYTES", str(5 * 1024 * 1024)))
IMAGE_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


class CertificationPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    certification_name: str = Field(min_length=1, max_length=150)
    issuer: str | None = Field(default=None, max_length=150)
    certification_number: str | None = Field(default=None, max_length=100)
    acquired_date: date | None = None

    @field_validator("certification_name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("자격증명을 입력해 주세요.")
        return cleaned

    @field_validator("issuer", "certification_number")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


def profile(db: Session, user_id: int, *, lock: bool = False) -> TrainerProfile:
    statement = select(TrainerProfile).where(TrainerProfile.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    result = db.scalar(statement)
    if result is None:
        raise HTTPException(status_code=404, detail="트레이너 프로필을 찾을 수 없습니다.")
    return result


def owned(db: Session, user_id: int, certification_id: int, *, lock: bool = False) -> TrainerCertification:
    statement = select(TrainerCertification).where(
        TrainerCertification.trainer_certification_id == certification_id,
        TrainerCertification.user_id == user_id,
        TrainerCertification.is_active.is_(True),
    )
    if lock:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if item is None:
        raise HTTPException(status_code=404, detail="자격증 정보를 찾을 수 없습니다.")
    return item


def serialize(item: TrainerCertification) -> dict:
    return {
        "certification_id": item.trainer_certification_id,
        "certification_name": item.certification_name,
        "issuer": item.issuer,
        "certification_number": item.certification_number,
        "acquired_date": item.acquired_date,
        "evidence_image_url": item.evidence_image_url,
        "evidence_original_name": item.evidence_original_name,
    }


def require_re_review(db: Session, trainer: User, trainer_profile: TrainerProfile) -> bool:
    changed = trainer_profile.approval_status in {"APPROVED", "REJECTED"}
    if not changed:
        return False
    trainer_profile.approval_status = "PENDING"
    trainer_profile.reviewed_by = None
    trainer_profile.reviewed_at = None
    trainer_profile.rejection_reason = None
    create_notification(
        db,
        user_id=trainer.user_id,
        title="트레이너 자격 정보가 변경되었습니다.",
        message="증빙자료가 변경되어 다시 심사가 필요해요. 관리자 승인 전까지 트레이너 관리 기능이 제한됩니다.",
        notification_type="TRAINER_CERTIFICATION_REVIEW_REQUIRED",
        target_url="/trainer/certifications",
        reference_id=trainer.user_id,
    )
    return True


def safe_unlink(stored: str | None) -> None:
    if not stored:
        return
    try:
        path = Path(stored).resolve()
        if EVIDENCE_DIR.resolve() in path.parents:
            path.unlink(missing_ok=True)
    except OSError:
        pass


@router.get("")
def list_certifications(
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    trainer_profile = profile(db, trainer.user_id)
    items = db.scalars(
        select(TrainerCertification)
        .where(
            TrainerCertification.user_id == trainer.user_id,
            TrainerCertification.is_active.is_(True),
        )
        .order_by(TrainerCertification.created_at.asc())
    ).all()
    return {
        "items": [serialize(item) for item in items],
        "approval_status": trainer_profile.approval_status,
        "rejection_reason": trainer_profile.rejection_reason,
    }


@router.post("", status_code=201)
def create_certification(
    payload: CertificationPayload,
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    trainer_profile = profile(db, trainer.user_id, lock=True)
    existing = db.scalar(
        select(TrainerCertification).where(
            TrainerCertification.user_id == trainer.user_id,
            TrainerCertification.certification_name == payload.certification_name,
        ).with_for_update()
    )
    try:
        if existing and existing.is_active:
            raise HTTPException(status_code=409, detail="같은 이름의 자격증이 이미 등록되어 있습니다.")
        if existing:
            for key, value in payload.model_dump().items():
                setattr(existing, key, value)
            existing.is_active = True
            item = existing
        else:
            item = TrainerCertification(user_id=trainer.user_id, **payload.model_dump())
            db.add(item)
        require_re_review(db, trainer, trainer_profile)
        db.commit()
        db.refresh(item)
        return serialize(item)
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="자격증을 저장하지 못했습니다.") from error


@router.patch("/{certification_id}")
def update_certification(
    certification_id: int,
    payload: CertificationPayload,
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    trainer_profile = profile(db, trainer.user_id, lock=True)
    item = owned(db, trainer.user_id, certification_id, lock=True)
    duplicate = db.scalar(
        select(TrainerCertification.trainer_certification_id).where(
            TrainerCertification.user_id == trainer.user_id,
            TrainerCertification.certification_name == payload.certification_name,
            TrainerCertification.is_active.is_(True),
            TrainerCertification.trainer_certification_id != certification_id,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="같은 이름의 자격증이 이미 등록되어 있습니다.")
    try:
        for key, value in payload.model_dump().items():
            setattr(item, key, value)
        require_re_review(db, trainer, trainer_profile)
        db.commit()
        db.refresh(item)
        return serialize(item)
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="자격증을 수정하지 못했습니다.") from error


@router.delete("/{certification_id}", status_code=204, response_class=Response)
def delete_certification(
    certification_id: int,
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> Response:
    trainer_profile = profile(db, trainer.user_id, lock=True)
    item = owned(db, trainer.user_id, certification_id, lock=True)
    item.is_active = False
    require_re_review(db, trainer, trainer_profile)
    db.commit()
    return Response(status_code=204)


def valid_signature(path: Path, mime: str) -> bool:
    try:
        with path.open("rb") as source:
            header = source.read(16)
    except OSError:
        return False
    if mime == "image/jpeg":
        return header.startswith(b"\xff\xd8\xff")
    if mime == "image/png":
        return header.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/webp":
        return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    return False


@router.post("/{certification_id}/evidence")
async def upload_evidence(
    certification_id: int,
    file: UploadFile = File(...),
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    trainer_profile = profile(db, trainer.user_id, lock=True)
    item = owned(db, trainer.user_id, certification_id, lock=True)
    mime = (file.content_type or "").lower()
    suffix = Path(file.filename or "").suffix.lower()
    if mime not in IMAGE_TYPES or suffix not in IMAGE_TYPES[mime]:
        raise HTTPException(status_code=400, detail="JPG, PNG, WebP 이미지만 업로드할 수 있습니다.")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    destination = EVIDENCE_DIR / f"{uuid4().hex}{suffix}"
    size = 0
    old_path = item.evidence_storage_path
    try:
        with destination.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_IMAGE_BYTES:
                    raise HTTPException(status_code=413, detail="증빙 이미지는 5MB 이하만 업로드할 수 있습니다.")
                target.write(chunk)
        if not valid_signature(destination, mime):
            raise HTTPException(status_code=400, detail="파일 내용과 이미지 형식이 일치하지 않습니다.")
        item.evidence_storage_path = str(destination.resolve())
        item.evidence_original_name = Path(file.filename or "evidence").name[:255]
        item.evidence_image_url = f"/api/trainers/me/certifications/{item.trainer_certification_id}/evidence/content?v={uuid4().hex[:8]}"
        require_re_review(db, trainer, trainer_profile)
        db.commit()
        db.refresh(item)
        safe_unlink(old_path)
        return serialize(item)
    except HTTPException:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    except Exception as error:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="증빙 이미지를 저장하지 못했습니다.") from error


@router.get("/{certification_id}/evidence/content")
def read_evidence(
    certification_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    item = db.scalar(
        select(TrainerCertification).where(
            TrainerCertification.trainer_certification_id == certification_id,
            TrainerCertification.is_active.is_(True),
        )
    )
    if user.account_type == "ADMIN":
        allowed = item is not None
    else:
        require_trainer(user)
        allowed = item is not None and item.user_id == user.user_id
    if not allowed or not item.evidence_storage_path:
        raise HTTPException(status_code=404, detail="증빙 이미지를 찾을 수 없습니다.")
    path = Path(item.evidence_storage_path).resolve()
    if EVIDENCE_DIR.resolve() not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="증빙 이미지를 찾을 수 없습니다.")
    return FileResponse(path)


@router.delete("/{certification_id}/evidence", status_code=204, response_class=Response)
def delete_evidence(
    certification_id: int,
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> Response:
    trainer_profile = profile(db, trainer.user_id, lock=True)
    item = owned(db, trainer.user_id, certification_id, lock=True)
    old_path = item.evidence_storage_path
    item.evidence_image_url = None
    item.evidence_storage_path = None
    item.evidence_original_name = None
    require_re_review(db, trainer, trainer_profile)
    db.commit()
    safe_unlink(old_path)
    return Response(status_code=204)
