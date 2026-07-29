from __future__ import annotations

import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Exercise, Gym, GymMachine, User, UserGym
from backend.routers.pt import get_current_user
from backend.security import require_employed_trainer


router = APIRouter(prefix="/api/users/me/gym/machines", tags=["gym-machines"])
BASE_DIR = Path(__file__).resolve().parents[2]
IMAGE_DIR = BASE_DIR / "uploads" / "gym_machines"
MAX_IMAGE_BYTES = int(os.getenv("GYM_MACHINE_IMAGE_MAX_BYTES", str(5 * 1024 * 1024)))
IMAGE_TYPES = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/webp": {".webp"},
}


class GymMachinePayload(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        protected_namespaces=(),
    )

    machine_name: str = Field(min_length=1, max_length=120)
    body_part: str = Field(min_length=1, max_length=30)
    brand: str | None = Field(default=None, max_length=100)
    model_name: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    usage_guide: str | None = Field(default=None, max_length=5000)
    caution: str | None = Field(default=None, max_length=3000)

    @field_validator("machine_name", "body_part")
    @classmethod
    def clean_required(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("필수 정보를 입력해 주세요.")
        return cleaned

    @field_validator("brand", "model_name", "description", "usage_guide", "caution")
    @classmethod
    def clean_optional(cls, value: str | None) -> str | None:
        return value.strip() or None if value else None


class GymMachineUpdate(GymMachinePayload):
    remove_image: bool = False


def current_gym(db: Session, user_id: int) -> Gym:
    gym = db.scalar(
        select(Gym)
        .join(UserGym, UserGym.gym_id == Gym.gym_id)
        .where(UserGym.user_id == user_id, Gym.is_active.is_(True))
    )
    if gym is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="등록된 헬스장이 없습니다. 내 헬스장을 먼저 등록해 주세요.",
        )
    return gym


def can_manage(user: User) -> bool:
    try:
        require_employed_trainer(user)
        return True
    except HTTPException:
        return False


def require_manager(user: User) -> None:
    require_employed_trainer(user)


def categories(db: Session) -> list[str]:
    values = db.scalars(
        select(Exercise.category)
        .where(Exercise.is_active.is_(True), Exercise.category.is_not(None))
        .distinct()
        .order_by(Exercise.category.asc())
    ).all()
    return [value for value in values if value]


def validate_body_part(db: Session, body_part: str) -> None:
    if body_part not in categories(db):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="지원하지 않는 운동 부위입니다.",
        )


def serialize(machine: GymMachine) -> dict:
    return {
        "machine_id": machine.machine_id,
        "machine_name": machine.machine_name,
        "body_part": machine.body_part,
        "brand": machine.brand,
        "model_name": machine.model_name,
        "description": machine.description,
        "usage_guide": machine.usage_guide,
        "caution": machine.caution,
        "image_url": machine.image_url,
        "created_at": machine.created_at,
        "updated_at": machine.updated_at,
    }


def owned_machine(db: Session, gym_id: int, machine_id: int, *, lock: bool = False) -> GymMachine:
    statement = select(GymMachine).where(
        GymMachine.machine_id == machine_id,
        GymMachine.gym_id == gym_id,
        GymMachine.is_active.is_(True),
    )
    if lock:
        statement = statement.with_for_update()
    machine = db.scalar(statement)
    if machine is None:
        raise HTTPException(status_code=404, detail="머신 정보를 찾을 수 없습니다.")
    return machine


def ensure_unique_name(
    db: Session,
    gym_id: int,
    machine_name: str,
    *,
    exclude_id: int | None = None,
) -> None:
    statement = select(GymMachine.machine_id).where(
        GymMachine.gym_id == gym_id,
        GymMachine.is_active.is_(True),
        func.lower(GymMachine.machine_name) == machine_name.lower(),
    )
    if exclude_id is not None:
        statement = statement.where(GymMachine.machine_id != exclude_id)
    if db.scalar(statement) is not None:
        raise HTTPException(status_code=409, detail="같은 이름의 머신이 이미 등록되어 있습니다.")


def lock_gym(db: Session, gym_id: int) -> None:
    db.scalar(select(Gym.gym_id).where(Gym.gym_id == gym_id).with_for_update())


def safe_unlink(stored: str | None) -> None:
    if not stored:
        return
    try:
        path = Path(stored).resolve()
        root = IMAGE_DIR.resolve()
        if root in path.parents:
            path.unlink(missing_ok=True)
    except OSError:
        pass


@router.get("")
def list_machines(
    query: str | None = Query(default=None, max_length=100),
    body_part: str | None = Query(default=None, max_length=30),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    gym = current_gym(db, user.user_id)
    filters = [GymMachine.gym_id == gym.gym_id, GymMachine.is_active.is_(True)]
    if query and query.strip():
        keyword = f"%{query.strip()}%"
        filters.append(or_(
            GymMachine.machine_name.ilike(keyword),
            GymMachine.brand.ilike(keyword),
            GymMachine.model_name.ilike(keyword),
        ))
    if body_part and body_part.strip():
        filters.append(GymMachine.body_part == body_part.strip())
    items = db.scalars(
        select(GymMachine)
        .where(*filters)
        .order_by(GymMachine.machine_name.asc(), GymMachine.machine_id.asc())
    ).all()
    return {
        "gym": {"gym_id": gym.gym_id, "gym_name": gym.gym_name},
        "items": [serialize(item) for item in items],
        "total": len(items),
        "categories": categories(db),
        "can_manage": can_manage(user),
    }


@router.get("/{machine_id}")
def read_machine(
    machine_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    gym = current_gym(db, user.user_id)
    return {"machine": serialize(owned_machine(db, gym.gym_id, machine_id)), "can_manage": can_manage(user)}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_machine(
    payload: GymMachinePayload,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    gym = current_gym(db, user.user_id)
    require_manager(user)
    lock_gym(db, gym.gym_id)
    validate_body_part(db, payload.body_part)
    ensure_unique_name(db, gym.gym_id, payload.machine_name)
    try:
        machine = GymMachine(
            gym_id=gym.gym_id,
            created_by=user.user_id,
            **payload.model_dump(),
        )
        db.add(machine)
        db.commit()
        db.refresh(machine)
        return serialize(machine)
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="머신을 등록하지 못했습니다.") from error


@router.patch("/{machine_id}")
def update_machine(
    machine_id: int,
    payload: GymMachineUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    gym = current_gym(db, user.user_id)
    require_manager(user)
    lock_gym(db, gym.gym_id)
    validate_body_part(db, payload.body_part)
    machine = owned_machine(db, gym.gym_id, machine_id, lock=True)
    ensure_unique_name(db, gym.gym_id, payload.machine_name, exclude_id=machine.machine_id)
    old_path = machine.image_storage_path if payload.remove_image else None
    try:
        for field, value in payload.model_dump(exclude={"remove_image"}).items():
            setattr(machine, field, value)
        if payload.remove_image:
            machine.image_url = None
            machine.image_storage_path = None
        db.commit()
        db.refresh(machine)
        safe_unlink(old_path)
        return serialize(machine)
    except HTTPException:
        db.rollback()
        raise
    except Exception as error:
        db.rollback()
        raise HTTPException(status_code=500, detail="머신 정보를 수정하지 못했습니다.") from error


@router.delete(
    "/{machine_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_machine(
    machine_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    gym = current_gym(db, user.user_id)
    require_manager(user)
    machine = owned_machine(db, gym.gym_id, machine_id, lock=True)
    machine.is_active = False
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


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


@router.post("/{machine_id}/image")
async def upload_machine_image(
    machine_id: int,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    gym = current_gym(db, user.user_id)
    require_manager(user)
    machine = owned_machine(db, gym.gym_id, machine_id, lock=True)
    mime = (file.content_type or "").lower()
    suffix = Path(file.filename or "").suffix.lower()
    if mime not in IMAGE_TYPES or suffix not in IMAGE_TYPES[mime]:
        raise HTTPException(status_code=400, detail="JPG, PNG, WebP 이미지만 업로드할 수 있습니다.")
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    destination = IMAGE_DIR / f"{uuid4().hex}{suffix}"
    size = 0
    old_path = machine.image_storage_path
    try:
        with destination.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_IMAGE_BYTES:
                    raise HTTPException(
                        status_code=413,
                        detail=f"이미지는 {MAX_IMAGE_BYTES // (1024 * 1024)}MB 이하만 업로드할 수 있습니다.",
                    )
                target.write(chunk)
        if not valid_signature(destination, mime):
            raise HTTPException(status_code=400, detail="파일 내용과 이미지 형식이 일치하지 않습니다.")
        machine.image_storage_path = str(destination.resolve())
        machine.image_url = f"/api/users/me/gym/machines/{machine.machine_id}/image/content?v={uuid4().hex[:8]}"
        db.commit()
        db.refresh(machine)
        safe_unlink(old_path)
        return serialize(machine)
    except HTTPException:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise
    except Exception as error:
        db.rollback()
        destination.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="머신 이미지를 저장하지 못했습니다.") from error


@router.get("/{machine_id}/image/content")
def read_machine_image(
    machine_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    gym = current_gym(db, user.user_id)
    machine = owned_machine(db, gym.gym_id, machine_id)
    if not machine.image_storage_path:
        raise HTTPException(status_code=404, detail="머신 이미지가 없습니다.")
    path = Path(machine.image_storage_path).resolve()
    root = IMAGE_DIR.resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="머신 이미지가 없습니다.")
    return FileResponse(path)


@router.delete(
    "/{machine_id}/image",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
)
def delete_machine_image(
    machine_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Response:
    gym = current_gym(db, user.user_id)
    require_manager(user)
    machine = owned_machine(db, gym.gym_id, machine_id, lock=True)
    old_path = machine.image_storage_path
    machine.image_url = None
    machine.image_storage_path = None
    db.commit()
    safe_unlink(old_path)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
