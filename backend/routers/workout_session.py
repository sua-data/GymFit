from __future__ import annotations

import os
import shutil
import subprocess
from datetime import date, datetime, time, timedelta
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Header, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.database import get_db
from backend.models import (
    Exercise, TrainerMember, User, UserExercise, WorkoutRecord,
    WorkoutRecordDetailItem, WorkoutRecordMedia,
)
from backend.routers.workout import korea_now_naive
from backend.workout_session_schemas import (
    WorkoutMediaItem, WorkoutSessionCreate, WorkoutSessionDetail,
    WorkoutSessionExerciseItem, WorkoutSessionList, WorkoutSessionSummary, WorkoutSessionUpdate,
)


router = APIRouter(prefix="/api/workout-sessions", tags=["운동 세션"])
BASE_DIR = Path(__file__).resolve().parents[2]
MEDIA_DIR = BASE_DIR / "uploads" / "workout_media"
THUMBNAIL_DIR = BASE_DIR / "uploads" / "workout_thumbnails"
MAX_MEDIA_BYTES = int(os.getenv("WORKOUT_MEDIA_MAX_BYTES", str(25 * 1024 * 1024)))
MAX_VIDEO_SECONDS = int(os.getenv("WORKOUT_VIDEO_MAX_SECONDS", "60"))
VIDEO_TYPES = {"video/mp4": ".mp4", "video/webm": ".webm"}
IMAGE_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
TYPE_EXTENSIONS = {
    "video/mp4": {".mp4"}, "video/webm": {".webm"},
    "image/jpeg": {".jpg", ".jpeg"}, "image/png": {".png"}, "image/webp": {".webp"},
}
FFPROBE_PATH = shutil.which("ffprobe")
FFMPEG_PATH = shutil.which("ffmpeg")


def current_user(x_user_id: int = Header(alias="X-User-Id"), db: Session = Depends(get_db)) -> User:
    user = db.scalar(select(User).where(User.user_id == x_user_id, User.is_active.is_(True)))
    if user is None:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")
    return user


def clean(value: str | None) -> str | None:
    return value.strip() or None if value else None


def normalize(value: datetime) -> datetime:
    from backend.routers.workout import KST
    return value.astimezone(KST).replace(tzinfo=None) if value.tzinfo else value


def auto_title(workout_date: date, workout_part: str | None, record_type: str = "WORKOUT") -> str:
    suffix = "PT 수업" if record_type == "PT" else f"{workout_part or '일반'} 운동"
    return f"{workout_date.year}년 {workout_date.month}월 {workout_date.day}일 {suffix}"


def validate_item_reference(db: Session, user_id: int, payload) -> None:
    if payload.exercise_id is not None:
        if db.scalar(select(Exercise.exercise_id).where(Exercise.exercise_id == payload.exercise_id, Exercise.is_active.is_(True))) is None:
            raise HTTPException(status_code=404, detail=f"'{payload.exercise_name}' 운동을 찾을 수 없습니다.")
    if payload.user_exercise_id is not None:
        if db.scalar(select(UserExercise.user_exercise_id).where(UserExercise.user_exercise_id == payload.user_exercise_id, UserExercise.user_id == user_id, UserExercise.is_active.is_(True))) is None:
            raise HTTPException(status_code=404, detail=f"'{payload.exercise_name}' 회원 운동을 찾을 수 없습니다.")


def add_items(db: Session, record: WorkoutRecord, payloads) -> list[WorkoutRecordDetailItem]:
    result = []
    for order, payload in enumerate(payloads, 1):
        validate_item_reference(db, record.user_id, payload)
        item = WorkoutRecordDetailItem(
            record_id=record.workout_record_id, exercise_id=payload.exercise_id,
            user_exercise_id=payload.user_exercise_id, exercise_name=payload.exercise_name.strip(),
            weight_value=payload.weight_value, weight_text=clean(payload.weight_text),
            repetitions=payload.repetitions, completed_sets=payload.completed_sets,
            rpe=payload.rpe, workout_minutes=payload.workout_minutes,
            memo=clean(payload.memo), display_order=order,
        )
        db.add(item); result.append(item)
    return result


def apply_summary(record: WorkoutRecord, payload, record_type: str = "WORKOUT") -> None:
    start, end = normalize(payload.started_at), normalize(payload.completed_at)
    if start >= end:
        raise HTTPException(status_code=400, detail="종료 시간은 시작 시간보다 늦어야 합니다.")
    minutes = max(0, round((end - start).total_seconds() / 60))
    record.record_type = record_type
    record.title = clean(payload.title) or auto_title(payload.workout_date, clean(payload.workout_part), record_type)
    record.workout_date = payload.workout_date
    record.started_at, record.completed_at = start, end
    record.workout_minutes = minutes
    record.workout_part = clean(payload.workout_part)
    record.location, record.memo = clean(payload.location), clean(payload.memo)
    record.completed_sets = sum(item.completed_sets or 0 for item in payload.items)
    record.repetition_count = sum((item.repetitions or 0) * (item.completed_sets or 1) for item in payload.items)


def can_read(db: Session, record: WorkoutRecord, user: User) -> bool:
    if record.user_id == user.user_id:
        return True
    if user.account_type == "TRAINER" and record.record_type == "PT" and record.trainer_id == user.user_id:
        return True
    return False


def get_owned(db: Session, record_id: int, user: User, *, write: bool = False) -> WorkoutRecord:
    statement = select(WorkoutRecord).where(WorkoutRecord.workout_record_id == record_id)
    if write:
        statement = statement.with_for_update()
    record = db.scalar(statement)
    if record is None or not can_read(db, record, user):
        raise HTTPException(status_code=404, detail="운동 기록을 찾을 수 없습니다.")
    return record


def summary(record: WorkoutRecord, items: list[WorkoutRecordDetailItem]) -> WorkoutSessionSummary:
    return WorkoutSessionSummary(
        workout_record_id=record.workout_record_id, record_type=record.record_type,
        title=record.title or "운동 기록", workout_date=record.workout_date or record.started_at.date(),
        started_at=record.started_at, completed_at=record.completed_at,
        workout_minutes=record.workout_minutes, workout_part=record.workout_part,
        trainer_id=record.trainer_id, trainer_name=record.trainer.name if record.trainer else None,
        location=record.location, memo=record.memo,
        posture_score=record.average_posture_score if record.record_type == "WORKOUT" else None,
        item_count=len(items), exercise_names=[item.exercise_name for item in items[:3]],
        has_media=any(bool(item.media) for item in items),
    )


def media_schema(media: WorkoutRecordMedia) -> WorkoutMediaItem:
    return WorkoutMediaItem(media_id=media.media_id, media_type=media.media_type,
        media_url=media.media_url, thumbnail_url=media.thumbnail_url,
        duration_seconds=media.duration_seconds, file_size=media.file_size)


def detail_schema(record: WorkoutRecord) -> WorkoutSessionDetail:
    base = summary(record, list(record.items))
    return WorkoutSessionDetail(**base.model_dump(), calories=record.calories if record.record_type == "WORKOUT" else None,
        best_posture_score=record.best_posture_score if record.record_type == "WORKOUT" else None,
        feedback_title=record.feedback_title if record.record_type == "WORKOUT" else None,
        feedback=record.feedback if record.record_type == "WORKOUT" else None,
        image_url=record.image_url if record.record_type == "WORKOUT" else None,
        items=[WorkoutSessionExerciseItem(
            item_id=item.item_id, exercise_id=item.exercise_id, user_exercise_id=item.user_exercise_id,
            exercise_name=item.exercise_name, weight_value=item.weight_value, weight_text=item.weight_text,
            repetitions=item.repetitions, completed_sets=item.completed_sets, rpe=item.rpe,
            workout_minutes=item.workout_minutes, memo=item.memo, posture_score=item.posture_score,
            feedback=item.feedback, display_order=item.display_order,
            media=[media_schema(media) for media in item.media],
        ) for item in record.items])


@router.post("", response_model=WorkoutSessionDetail, status_code=status.HTTP_201_CREATED)
def create_session(payload: WorkoutSessionCreate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.account_type != "MEMBER":
        raise HTTPException(status_code=403, detail="회원만 일반 운동 기록을 등록할 수 있습니다.")
    try:
        record = WorkoutRecord(user_id=user.user_id, record_source="MANUAL_SESSION", calories=0)
        apply_summary(record, payload)
        db.add(record); db.flush(); add_items(db, record, payload.items)
        db.commit()
        record = db.scalar(select(WorkoutRecord).options(joinedload(WorkoutRecord.trainer), selectinload(WorkoutRecord.items).selectinload(WorkoutRecordDetailItem.media)).where(WorkoutRecord.workout_record_id == record.workout_record_id))
        return detail_schema(record)
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="운동 기록을 저장하지 못했습니다.") from exc


def period_conditions(period: str):
    if period == "all": return []
    today = korea_now_naive().date(); days = {"today": 1, "7d": 7, "30d": 30}[period]
    return [WorkoutRecord.started_at >= datetime.combine(today - timedelta(days=days - 1), time.min), WorkoutRecord.started_at < datetime.combine(today + timedelta(days=1), time.min)]


@router.get("", response_model=WorkoutSessionList)
def list_sessions(period: str = Query("all", pattern="^(all|today|7d|30d)$"), limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    filters = [WorkoutRecord.user_id == user.user_id, *period_conditions(period)]
    total = db.scalar(select(func.count(WorkoutRecord.workout_record_id)).where(*filters)) or 0
    records = db.scalars(select(WorkoutRecord).options(joinedload(WorkoutRecord.trainer), selectinload(WorkoutRecord.items).selectinload(WorkoutRecordDetailItem.media)).where(*filters).order_by(WorkoutRecord.started_at.desc(), WorkoutRecord.workout_record_id.desc()).offset(offset).limit(limit)).unique().all()
    return WorkoutSessionList(items=[summary(record, list(record.items)) for record in records], total=total, limit=limit, offset=offset)


@router.get("/trainer/member/{member_id}", response_model=WorkoutSessionList)
def trainer_member_sessions(member_id: int, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), user: User = Depends(current_user), db: Session = Depends(get_db)):
    if user.account_type != "TRAINER": raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
    relationship = db.scalar(select(TrainerMember.trainer_member_id).where(
        TrainerMember.trainer_id == user.user_id,
        TrainerMember.member_id == member_id,
        TrainerMember.status.in_(("ACTIVE", "ENDED")),
    ))
    if relationship is None: raise HTTPException(status_code=403, detail="PT 연결 기록이 필요합니다.")
    filters = [WorkoutRecord.user_id == member_id, WorkoutRecord.record_type == "PT", WorkoutRecord.trainer_id == user.user_id]
    total = db.scalar(select(func.count(WorkoutRecord.workout_record_id)).where(*filters)) or 0
    records = db.scalars(select(WorkoutRecord).options(joinedload(WorkoutRecord.trainer), selectinload(WorkoutRecord.items).selectinload(WorkoutRecordDetailItem.media)).where(*filters).order_by(WorkoutRecord.started_at.desc()).offset(offset).limit(limit)).unique().all()
    return WorkoutSessionList(items=[summary(record, list(record.items)) for record in records], total=total, limit=limit, offset=offset)


@router.get("/{record_id}", response_model=WorkoutSessionDetail)
def session_detail(record_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    record = db.scalar(select(WorkoutRecord).options(joinedload(WorkoutRecord.trainer), selectinload(WorkoutRecord.items).selectinload(WorkoutRecordDetailItem.media)).where(WorkoutRecord.workout_record_id == record_id))
    if record is None or not can_read(db, record, user): raise HTTPException(status_code=404, detail="운동 기록을 찾을 수 없습니다.")
    return detail_schema(record)


@router.patch("/{record_id}", response_model=WorkoutSessionDetail)
def update_session(record_id: int, payload: WorkoutSessionUpdate, user: User = Depends(current_user), db: Session = Depends(get_db)):
    try:
        record = get_owned(db, record_id, user, write=True)
        if record.user_id != user.user_id or record.record_type != "WORKOUT": raise HTTPException(status_code=403, detail="PT 기록은 회원이 수정할 수 없습니다.")
        old_paths = [Path(path) for item in record.items for media in item.media for path in (media.storage_path, media.thumbnail_storage_path) if path]
        record.items.clear(); db.flush(); apply_summary(record, payload); add_items(db, record, payload.items); db.commit()
        for path in old_paths:
            try: path.unlink(missing_ok=True)
            except OSError: pass
        record = db.scalar(select(WorkoutRecord).options(joinedload(WorkoutRecord.trainer), selectinload(WorkoutRecord.items).selectinload(WorkoutRecordDetailItem.media)).where(WorkoutRecord.workout_record_id == record_id))
        return detail_schema(record)
    except HTTPException: db.rollback(); raise
    except Exception as exc: db.rollback(); raise HTTPException(status_code=500, detail="운동 기록을 수정하지 못했습니다.") from exc


@router.delete("/{record_id}", status_code=204)
def delete_session(record_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    record = get_owned(db, record_id, user, write=True)
    if record.user_id != user.user_id or record.record_type != "WORKOUT": raise HTTPException(status_code=403, detail="PT 기록은 회원이 삭제할 수 없습니다.")
    paths = [Path(path) for item in record.items for media in item.media for path in (media.storage_path, media.thumbnail_storage_path) if path]
    db.delete(record); db.commit()
    for path in paths:
        try: path.unlink(missing_ok=True)
        except OSError: pass


def probe_duration(path: Path) -> int | None:
    if not FFPROBE_PATH: return None
    try:
        result = subprocess.run([FFPROBE_PATH, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(path)], capture_output=True, text=True, timeout=15, check=True)
        return max(0, round(float(result.stdout.strip())))
    except (OSError, ValueError, subprocess.SubprocessError): return None


def make_thumbnail(video_path: Path, name: str) -> Path | None:
    if not FFMPEG_PATH: return None
    THUMBNAIL_DIR.mkdir(parents=True, exist_ok=True); path = THUMBNAIL_DIR / f"{name}.jpg"
    try:
        subprocess.run([FFMPEG_PATH, "-y", "-ss", "0.5", "-i", str(video_path), "-frames:v", "1", "-vf", "scale=640:-2", str(path)], capture_output=True, timeout=30, check=True)
        return path
    except (OSError, subprocess.SubprocessError): path.unlink(missing_ok=True); return None


def valid_signature(path: Path, mime: str) -> bool:
    try:
        with path.open("rb") as source:
            header = source.read(16)
    except OSError:
        return False
    if mime == "video/mp4": return len(header) >= 8 and header[4:8] == b"ftyp"
    if mime == "video/webm": return header.startswith(b"\x1a\x45\xdf\xa3")
    if mime == "image/jpeg": return header.startswith(b"\xff\xd8\xff")
    if mime == "image/png": return header.startswith(b"\x89PNG\r\n\x1a\n")
    if mime == "image/webp": return len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP"
    return False


@router.post("/items/{item_id}/media", response_model=WorkoutMediaItem, status_code=201)
async def upload_media(item_id: int, file: UploadFile = File(...), user: User = Depends(current_user), db: Session = Depends(get_db)):
    item = db.scalar(select(WorkoutRecordDetailItem).options(joinedload(WorkoutRecordDetailItem.record)).where(WorkoutRecordDetailItem.item_id == item_id))
    can_write = item is not None and (
        (item.record.record_type == "WORKOUT" and item.record.user_id == user.user_id)
        or (item.record.record_type == "PT" and item.record.trainer_id == user.user_id)
    )
    if can_write and item.record.record_type == "PT":
        can_write = db.scalar(select(TrainerMember.trainer_member_id).where(
            TrainerMember.trainer_id == user.user_id,
            TrainerMember.member_id == item.record.user_id,
            TrainerMember.status == "ACTIVE",
        )) is not None
    if not can_write: raise HTTPException(status_code=404, detail="운동 항목을 찾을 수 없습니다.")
    mime = (file.content_type or "").lower()
    original_suffix = Path(file.filename or "").suffix.lower()
    if mime not in TYPE_EXTENSIONS or original_suffix not in TYPE_EXTENSIONS[mime]: raise HTTPException(status_code=400, detail="MP4, WebM, JPG, PNG, WebP 파일만 업로드할 수 있습니다.")
    suffix = original_suffix
    MEDIA_DIR.mkdir(parents=True, exist_ok=True); stem = uuid4().hex; path = MEDIA_DIR / f"{stem}{suffix}"; size = 0; thumb = None
    try:
        with path.open("wb") as target:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_MEDIA_BYTES: raise HTTPException(status_code=413, detail=f"미디어는 {MAX_MEDIA_BYTES // (1024*1024)}MB 이하만 업로드할 수 있습니다.")
                target.write(chunk)
        if not valid_signature(path, mime):
            raise HTTPException(status_code=400, detail="파일 내용과 확장자 또는 MIME 형식이 일치하지 않습니다.")
        media_type = "VIDEO" if mime in VIDEO_TYPES else "IMAGE"; duration = probe_duration(path) if media_type == "VIDEO" else None
        if media_type == "VIDEO" and FFPROBE_PATH and duration is None:
            raise HTTPException(status_code=400, detail="영상 길이를 확인할 수 없는 파일입니다.")
        if duration is not None and duration > MAX_VIDEO_SECONDS: raise HTTPException(status_code=400, detail=f"영상은 {MAX_VIDEO_SECONDS}초 이하만 업로드할 수 있습니다.")
        thumb = make_thumbnail(path, stem) if media_type == "VIDEO" else None
        media = WorkoutRecordMedia(item_id=item_id, media_type=media_type, media_url="pending", thumbnail_url=None,
            storage_path=str(path.resolve()), thumbnail_storage_path=str(thumb.resolve()) if thumb else None,
            duration_seconds=duration, file_size=size)
        db.add(media); db.flush(); media.media_url = f"/api/workout-sessions/media/{media.media_id}"; media.thumbnail_url = f"/api/workout-sessions/media/{media.media_id}/thumbnail" if thumb else None
        db.commit(); return media_schema(media)
    except HTTPException:
        db.rollback(); path.unlink(missing_ok=True)
        if thumb: thumb.unlink(missing_ok=True)
        raise
    except Exception as exc:
        db.rollback(); path.unlink(missing_ok=True)
        if thumb: thumb.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail="미디어를 저장하지 못했습니다.") from exc


def media_file(db: Session, media_id: int, user: User, thumbnail: bool = False):
    media = db.scalar(select(WorkoutRecordMedia).options(joinedload(WorkoutRecordMedia.item).joinedload(WorkoutRecordDetailItem.record)).where(WorkoutRecordMedia.media_id == media_id))
    if media is None or not can_read(db, media.item.record, user): raise HTTPException(status_code=404, detail="미디어를 찾을 수 없습니다.")
    stored = media.thumbnail_storage_path if thumbnail else media.storage_path
    if not stored: raise HTTPException(status_code=404, detail="썸네일이 없습니다.")
    path = Path(stored).resolve()
    allowed_root = (THUMBNAIL_DIR if thumbnail else MEDIA_DIR).resolve()
    if allowed_root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="미디어 파일을 찾을 수 없습니다.")
    return FileResponse(path)


@router.get("/media/{media_id}")
def read_media(media_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return media_file(db, media_id, user)


@router.get("/media/{media_id}/thumbnail")
def read_thumbnail(media_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return media_file(db, media_id, user, True)


@router.delete("/media/{media_id}", status_code=204)
def delete_media(media_id: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    media = db.scalar(select(WorkoutRecordMedia).options(joinedload(WorkoutRecordMedia.item).joinedload(WorkoutRecordDetailItem.record)).where(WorkoutRecordMedia.media_id == media_id))
    can_delete = media is not None and (
        (media.item.record.record_type == "WORKOUT" and media.item.record.user_id == user.user_id)
        or (media.item.record.record_type == "PT" and media.item.record.trainer_id == user.user_id)
    )
    if not can_delete: raise HTTPException(status_code=404, detail="미디어를 찾을 수 없습니다.")
    paths = [Path(value) for value in (media.storage_path, media.thumbnail_storage_path) if value]
    db.delete(media); db.commit()
    for path in paths:
        try: path.unlink(missing_ok=True)
        except OSError: pass
