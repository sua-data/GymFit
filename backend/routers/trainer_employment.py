from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Gym, TrainerProfile, User, UserGym
from backend.routers.pt import get_current_user
from backend.services.notification_service import create_notification


router = APIRouter(prefix="/api/trainers/me/employment", tags=["trainer-employment"])
BASE_DIR = Path(__file__).resolve().parents[2]
EVIDENCE_DIR = BASE_DIR / "uploads" / "trainer_employment"
MAX_BYTES = int(os.getenv("TRAINER_EMPLOYMENT_IMAGE_MAX_BYTES", str(5 * 1024 * 1024)))
IMAGE_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


def require_trainer(user: User = Depends(get_current_user)) -> User:
    if user.account_type != "TRAINER":
        raise HTTPException(status_code=403, detail="트레이너 계정만 접근할 수 있습니다.")
    return user


def get_profile(db: Session, user_id: int, *, lock: bool = False) -> TrainerProfile:
    statement = select(TrainerProfile).where(TrainerProfile.user_id == user_id)
    if lock:
        statement = statement.with_for_update()
    profile = db.scalar(statement)
    if profile is None:
        raise HTTPException(status_code=404, detail="트레이너 프로필을 찾을 수 없습니다.")
    return profile


def get_gym(db: Session, user_id: int) -> Gym | None:
    return db.scalar(
        select(Gym)
        .join(UserGym, UserGym.gym_id == Gym.gym_id)
        .where(UserGym.user_id == user_id, Gym.is_active.is_(True))
    )


def serialize(db: Session, profile: TrainerProfile) -> dict:
    gym = get_gym(db, profile.user_id)
    return {
        "employment_status": profile.employment_status,
        "employment_rejection_reason": profile.employment_rejection_reason,
        "employment_reviewed_at": profile.employment_reviewed_at,
        "evidence_url": profile.employment_evidence_url,
        "evidence_original_name": profile.employment_original_name,
        "has_evidence": bool(
            profile.employment_storage_path
            and Path(profile.employment_storage_path).is_file()
        ),
        "gym": None if gym is None else {
            "gym_id": gym.gym_id,
            "gym_name": gym.gym_name,
            "road_address": gym.road_address,
        },
    }


def safe_unlink(stored: str | None) -> None:
    if not stored:
        return
    try:
        path = Path(stored).resolve()
        if EVIDENCE_DIR.resolve() in path.parents:
            path.unlink(missing_ok=True)
    except OSError:
        pass


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
    return mime == "image/webp" and len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"


@router.get("")
def read_my_employment(
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    return serialize(db, get_profile(db, trainer.user_id))


@router.post("/evidence")
async def upload_employment_evidence(
    file: UploadFile = File(...),
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> dict:
    profile = get_profile(db, trainer.user_id, lock=True)
    if get_gym(db, trainer.user_id) is None:
        raise HTTPException(status_code=409, detail="소속 헬스장을 먼저 선택해 주세요.")
    mime = (file.content_type or "").lower()
    suffix = Path(file.filename or "").suffix.lower()
    if mime not in IMAGE_TYPES or suffix not in IMAGE_TYPES[mime]:
        raise HTTPException(status_code=400, detail="JPG, PNG, WebP 이미지만 업로드할 수 있습니다.")
    EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)
    destination = EVIDENCE_DIR / f"{uuid4().hex}{suffix}"
    old_path = profile.employment_storage_path
    size = 0
    try:
        with destination.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_BYTES:
                    raise HTTPException(status_code=413, detail="소속 증빙 이미지는 5MB 이하여야 합니다.")
                target.write(chunk)
        if not valid_signature(destination, mime):
            raise HTTPException(status_code=400, detail="파일 내용과 이미지 형식이 일치하지 않습니다.")
        profile.employment_storage_path = str(destination.resolve())
        profile.employment_original_name = Path(file.filename or "employment-evidence").name[:255]
        profile.employment_evidence_url = f"/api/trainers/me/employment/evidence/content?v={uuid4().hex[:8]}"
        profile.employment_status = "PENDING"
        profile.employment_reviewed_by = None
        profile.employment_reviewed_at = None
        profile.employment_rejection_reason = None
        create_notification(
            db,
            user_id=trainer.user_id,
            title="헬스장 소속 승인 검토가 요청되었습니다.",
            message="관리자가 새 헬스장과 소속 증빙을 검토합니다.",
            notification_type="TRAINER_EMPLOYMENT_REVIEW_REQUESTED",
            target_url="/my-gym",
            reference_id=trainer.user_id,
        )
        db.commit()
        safe_unlink(old_path)
        return serialize(db, profile)
    except HTTPException:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    except Exception as error:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="소속 증빙을 저장하지 못했습니다.") from error


@router.get("/evidence/content")
def read_employment_evidence(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    profile = get_profile(db, user.user_id) if user.account_type == "TRAINER" else None
    if user.account_type == "ADMIN":
        raise HTTPException(
            status_code=400,
            detail="관리자 증빙 조회에는 트레이너 ID가 필요합니다.",
        )
    if profile is None or not profile.employment_storage_path:
        raise HTTPException(status_code=404, detail="소속 증빙을 찾을 수 없습니다.")
    path = Path(profile.employment_storage_path).resolve()
    if EVIDENCE_DIR.resolve() not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="소속 증빙을 찾을 수 없습니다.")
    return FileResponse(path)


@router.delete("/evidence", status_code=204, response_class=Response)
def delete_employment_evidence(
    trainer: User = Depends(require_trainer),
    db: Session = Depends(get_db),
) -> Response:
    profile = get_profile(db, trainer.user_id, lock=True)
    old_path = profile.employment_storage_path
    profile.employment_storage_path = None
    profile.employment_original_name = None
    profile.employment_evidence_url = None
    profile.employment_status = "PENDING" if get_gym(db, trainer.user_id) else "NONE"
    profile.employment_reviewed_by = None
    profile.employment_reviewed_at = None
    profile.employment_rejection_reason = None
    db.commit()
    safe_unlink(old_path)
    return Response(status_code=204)
