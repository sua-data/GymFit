from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import PtSchedule, User, WorkoutRecord, WorkoutRecordDetailItem
from backend.pt_schedule_schemas import PtScheduleCompleteRequest, PtScheduleCreate, PtScheduleItem, PtScheduleList, PtScheduleUpdate
from backend.routers.pt import get_current_user, require_role
from backend.security import (
    require_active_member_relation,
    require_employed_trainer,
    require_pt_relation_access,
)
from backend.services.notification_service import create_notification
from backend.routers.workout_session import validate_item_reference


router = APIRouter(prefix="/api/pt/schedules", tags=["pt-schedules"])
KST = ZoneInfo("Asia/Seoul")


def now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


def normalize_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value
    return value.astimezone(KST).replace(tzinfo=None)


def schedule_query():
    return select(PtSchedule).options(joinedload(PtSchedule.trainer), joinedload(PtSchedule.member))


def serialize(item: PtSchedule) -> PtScheduleItem:
    return PtScheduleItem(
        schedule_id=item.schedule_id,
        trainer_member_id=item.trainer_member_id,
        trainer_id=item.trainer_id,
        trainer_name=item.trainer.name,
        member_id=item.member_id,
        member_name=item.member.name,
        start_at=item.start_at,
        end_at=item.end_at,
        location=item.location,
        memo=item.memo,
        status=item.status,
        created_at=item.created_at,
        updated_at=item.updated_at,
    )


def validate_range(start_at: datetime, end_at: datetime) -> None:
    if start_at >= end_at:
        raise HTTPException(status_code=400, detail="종료 시간은 시작 시간보다 늦어야 합니다.")


def validate_overlap(
    db: Session, trainer_id: int, member_id: int, start_at: datetime, end_at: datetime, exclude_id: int | None = None
) -> None:
    filters = [
        PtSchedule.status == "SCHEDULED",
        PtSchedule.start_at < end_at,
        PtSchedule.end_at > start_at,
        or_(PtSchedule.trainer_id == trainer_id, PtSchedule.member_id == member_id),
    ]
    if exclude_id is not None:
        filters.append(PtSchedule.schedule_id != exclude_id)
    conflict = db.scalar(select(PtSchedule.schedule_id).where(*filters).limit(1).with_for_update())
    if conflict is not None:
        raise HTTPException(status_code=409, detail="트레이너 또는 회원의 기존 PT 일정과 시간이 겹칩니다.")


def owned_schedule(db: Session, schedule_id: int, user: User, *, lock: bool = False) -> PtSchedule:
    if user.account_type == "MEMBER":
        owner = PtSchedule.member_id
    else:
        require_employed_trainer(user)
        owner = PtSchedule.trainer_id
    statement = schedule_query().where(PtSchedule.schedule_id == schedule_id, owner == user.user_id)
    if lock:
        statement = statement.with_for_update()
    item = db.scalar(statement)
    if item is None:
        raise HTTPException(status_code=404, detail="PT 일정을 찾을 수 없습니다.")
    require_pt_relation_access(
        db,
        user=user,
        trainer_id=item.trainer_id,
        member_id=item.member_id,
        trainer_member_id=item.trainer_member_id,
        write=False,
    )
    return item


def format_time(value: datetime) -> str:
    return value.strftime("%Y년 %m월 %d일 %H:%M")


@router.post("", response_model=PtScheduleItem, status_code=status.HTTP_201_CREATED)
def create_schedule(payload: PtScheduleCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    try:
        start_at, end_at = normalize_datetime(payload.start_at), normalize_datetime(payload.end_at)
        validate_range(start_at, end_at)
        relationship = require_active_member_relation(
            db, trainer=current_user, member_id=payload.member_id, lock=True
        )
        validate_overlap(db, current_user.user_id, payload.member_id, start_at, end_at)
        item = PtSchedule(
            trainer_member_id=relationship.trainer_member_id,
            trainer_id=current_user.user_id,
            member_id=payload.member_id,
            start_at=start_at,
            end_at=end_at,
            location=payload.location.strip() if payload.location else None,
            memo=payload.memo.strip() if payload.memo else None,
        )
        db.add(item)
        db.flush()
        create_notification(
            db, user_id=item.member_id, title="새 PT 일정이 등록됐어요",
            message=f"{current_user.name} 트레이너님이 {format_time(item.start_at)} PT 일정을 등록했습니다.",
            notification_type="PT_SCHEDULE_CREATED", target_url=f"/pt/schedules#schedule-{item.schedule_id}",
            reference_id=item.schedule_id,
        )
        create_notification(
            db, user_id=item.trainer_id, title="PT 일정 등록 완료",
            message=f"{relationship.member.name} 회원의 {format_time(item.start_at)} PT 일정을 등록했습니다.",
            notification_type="PT_SCHEDULE_CREATED", target_url=f"/trainer/schedules#schedule-{item.schedule_id}",
            reference_id=item.schedule_id,
        )
        db.commit()
        return serialize(db.scalar(schedule_query().where(PtSchedule.schedule_id == item.schedule_id)))
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="PT 일정을 등록하지 못했습니다.") from exc


def list_for_owner(db: Session, owner, owner_id: int, schedule_status: str | None, member_id: int | None, date_from: datetime | None, date_to: datetime | None, limit: int, offset: int, current_user: User) -> PtScheduleList:
    filters = [owner == owner_id]
    if schedule_status:
        filters.append(PtSchedule.status == schedule_status)
    if member_id is not None:
        filters.append(PtSchedule.member_id == member_id)
    if date_from is not None:
        filters.append(PtSchedule.start_at >= normalize_datetime(date_from))
    if date_to is not None:
        filters.append(PtSchedule.start_at < normalize_datetime(date_to))
    total = db.scalar(select(func.count(PtSchedule.schedule_id)).where(*filters)) or 0
    items = db.scalars(schedule_query().where(*filters).order_by(PtSchedule.start_at.asc()).offset(offset).limit(limit)).all()
    for item in items:
        require_pt_relation_access(
            db,
            user=current_user,
            trainer_id=item.trainer_id,
            member_id=item.member_id,
            trainer_member_id=item.trainer_member_id,
            write=False,
        )
    return PtScheduleList(items=[serialize(item) for item in items], total=total)


@router.get("/trainer", response_model=PtScheduleList)
def trainer_schedules(member_id: int | None = Query(None, gt=0), schedule_status: str | None = Query(None, alias="status"), date_from: datetime | None = None, date_to: datetime | None = None, limit: int = Query(200, ge=1, le=200), offset: int = Query(0, ge=0), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    return list_for_owner(db, PtSchedule.trainer_id, current_user.user_id, schedule_status, member_id, date_from, date_to, limit, offset, current_user)


@router.get("/member", response_model=PtScheduleList)
def member_schedules(schedule_status: str | None = Query(None, alias="status"), date_from: datetime | None = None, date_to: datetime | None = None, limit: int = Query(200, ge=1, le=200), offset: int = Query(0, ge=0), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    return list_for_owner(db, PtSchedule.member_id, current_user.user_id, schedule_status, None, date_from, date_to, limit, offset, current_user)


@router.get("/{schedule_id}", response_model=PtScheduleItem)
def schedule_detail(schedule_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return serialize(owned_schedule(db, schedule_id, current_user))


@router.patch("/{schedule_id}", response_model=PtScheduleItem)
def update_schedule(schedule_id: int, payload: PtScheduleUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    try:
        item = owned_schedule(db, schedule_id, current_user, lock=True)
        require_pt_relation_access(
            db,
            user=current_user,
            trainer_id=item.trainer_id,
            member_id=item.member_id,
            trainer_member_id=item.trainer_member_id,
            write=True,
            lock=True,
        )
        if item.status != "SCHEDULED":
            raise HTTPException(status_code=409, detail="예정 상태의 PT 일정만 수정할 수 있습니다.")
        changes = payload.model_dump(exclude_unset=True)
        next_start = normalize_datetime(changes.get("start_at") or item.start_at)
        next_end = normalize_datetime(changes.get("end_at") or item.end_at)
        validate_range(next_start, next_end)
        validate_overlap(db, item.trainer_id, item.member_id, next_start, next_end, item.schedule_id)
        visible_changed = next_start != item.start_at or next_end != item.end_at or any(
            key in changes and changes[key] != getattr(item, key) for key in ("location", "memo")
        )
        item.start_at, item.end_at = next_start, next_end
        for key in ("location", "memo"):
            if key in changes:
                value = changes[key]
                setattr(item, key, value.strip() if value else None)
        if visible_changed:
            create_notification(
                db, user_id=item.member_id, title="PT 일정이 변경됐어요",
                message=f"PT 일정이 {format_time(item.start_at)}로 변경됐습니다.",
                notification_type="PT_SCHEDULE_UPDATED", target_url=f"/pt/schedules#schedule-{item.schedule_id}",
                reference_id=item.schedule_id,
            )
            create_notification(
                db, user_id=item.trainer_id, title="PT 일정 변경 완료",
                message=f"{item.member.name} 회원의 PT 일정을 {format_time(item.start_at)}로 변경했습니다.",
                notification_type="PT_SCHEDULE_UPDATED", target_url=f"/trainer/schedules#schedule-{item.schedule_id}",
                reference_id=item.schedule_id,
            )
        db.commit()
        return serialize(db.scalar(schedule_query().where(PtSchedule.schedule_id == item.schedule_id)))
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="PT 일정을 수정하지 못했습니다.") from exc


@router.patch("/{schedule_id}/cancel", response_model=PtScheduleItem)
def cancel_schedule(schedule_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    try:
        item = owned_schedule(db, schedule_id, current_user, lock=True)
        require_pt_relation_access(
            db,
            user=current_user,
            trainer_id=item.trainer_id,
            member_id=item.member_id,
            trainer_member_id=item.trainer_member_id,
            write=True,
            lock=True,
        )
        if item.status == "CANCELLED":
            raise HTTPException(status_code=409, detail="이미 취소된 PT 일정입니다.")
        if item.status != "SCHEDULED":
            raise HTTPException(status_code=409, detail="예정 상태의 PT 일정만 취소할 수 있습니다.")
        item.status = "CANCELLED"
        create_notification(
            db, user_id=item.member_id, title="PT 일정이 취소됐어요",
            message=f"{format_time(item.start_at)} PT 일정이 취소됐습니다.",
            notification_type="PT_SCHEDULE_CANCELLED", target_url=f"/pt/schedules#schedule-{item.schedule_id}",
            reference_id=item.schedule_id,
        )
        create_notification(
            db, user_id=item.trainer_id, title="PT 일정 취소 완료",
            message=f"{item.member.name} 회원의 {format_time(item.start_at)} PT 일정을 취소했습니다.",
            notification_type="PT_SCHEDULE_CANCELLED", target_url=f"/trainer/schedules#schedule-{item.schedule_id}",
            reference_id=item.schedule_id,
        )
        db.commit()
        return serialize(db.scalar(schedule_query().where(PtSchedule.schedule_id == item.schedule_id)))
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="PT 일정을 취소하지 못했습니다.") from exc


@router.patch("/{schedule_id}/complete", response_model=PtScheduleItem)
def complete_schedule(schedule_id: int, payload: PtScheduleCompleteRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    try:
        item = owned_schedule(db, schedule_id, current_user, lock=True)
        require_pt_relation_access(
            db,
            user=current_user,
            trainer_id=item.trainer_id,
            member_id=item.member_id,
            trainer_member_id=item.trainer_member_id,
            write=True,
            lock=True,
        )
        if item.status == "CANCELLED":
            raise HTTPException(status_code=409, detail="취소된 PT 일정은 완료 처리할 수 없습니다.")
        if item.status == "COMPLETED":
            raise HTTPException(status_code=409, detail="이미 완료된 PT 일정입니다.")
        if item.status != "SCHEDULED":
            raise HTTPException(status_code=409, detail="예정 상태의 PT 일정만 완료 처리할 수 있습니다.")
        if item.start_at > now_kst():
            raise HTTPException(status_code=409, detail="아직 시작하지 않은 PT 일정은 완료 처리할 수 없습니다.")

        existing_record = db.scalar(
            select(WorkoutRecord).where(WorkoutRecord.pt_schedule_id == item.schedule_id).with_for_update()
        )
        if existing_record is not None:
            raise HTTPException(status_code=409, detail="이미 운동 기록이 생성된 PT 일정입니다.")

        item.status = "COMPLETED"
        duration_minutes = max(0, round((item.end_at - item.start_at).total_seconds() / 60))
        record = WorkoutRecord(
            user_id=item.member_id,
            record_type="PT",
            title=(payload.title.strip() if payload.title and payload.title.strip() else "PT 수업"),
            workout_date=item.start_at.date(),
            workout_part=payload.workout_part.strip() if payload.workout_part else None,
            trainer_id=item.trainer_id,
            pt_schedule_id=item.schedule_id,
            location=None,
            memo=(payload.memo.strip() if payload.memo else item.memo),
            record_source="PT_SCHEDULE",
            started_at=item.start_at,
            completed_at=item.end_at,
            completed_sets=sum(detail.completed_sets or 0 for detail in payload.items),
            repetition_count=sum((detail.repetitions or 0) * (detail.completed_sets or 1) for detail in payload.items),
            workout_minutes=duration_minutes,
            calories=0,
            average_posture_score=None,
            best_posture_score=None,
        )
        db.add(record)
        db.flush()
        workout_items = []
        for display_order, detail in enumerate(payload.items, 1):
            validate_item_reference(db, item.member_id, detail)
            workout_item = WorkoutRecordDetailItem(
                record_id=record.workout_record_id,
                exercise_id=detail.exercise_id,
                user_exercise_id=detail.user_exercise_id,
                exercise_name=detail.exercise_name.strip(),
                weight_value=detail.weight_value,
                weight_text=detail.weight_text.strip() if detail.weight_text else None,
                repetitions=detail.repetitions,
                completed_sets=detail.completed_sets,
                rpe=detail.rpe,
                workout_minutes=detail.workout_minutes,
                memo=detail.memo.strip() if detail.memo else None,
                display_order=display_order,
            )
            db.add(workout_item)
            workout_items.append(workout_item)
        db.flush()
        create_notification(
            db,
            user_id=item.member_id,
            title="PT 일정이 완료됐어요",
            message=f"{format_time(item.start_at)} PT 일정이 완료 처리됐습니다.",
            notification_type="PT_SCHEDULE_COMPLETED",
            target_url=f"/pt/schedules#schedule-{item.schedule_id}",
            reference_id=item.schedule_id,
        )
        create_notification(
            db,
            user_id=item.trainer_id,
            title="PT 완료 처리 기록",
            message=f"{item.member.name} 회원의 {format_time(item.start_at)} PT 일정을 완료 처리했습니다.",
            notification_type="PT_SCHEDULE_COMPLETED",
            target_url=f"/trainer/schedules#schedule-{item.schedule_id}",
            reference_id=item.schedule_id,
        )
        db.commit()
        result = serialize(db.scalar(schedule_query().where(PtSchedule.schedule_id == item.schedule_id)))
        result.workout_record_id = record.workout_record_id
        result.workout_item_ids = [workout_item.item_id for workout_item in workout_items]
        return result
    except HTTPException:
        db.rollback(); raise
    except IntegrityError as exc:
        db.rollback(); raise HTTPException(status_code=409, detail="이미 운동 기록이 생성된 PT 일정입니다.") from exc
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="PT 일정을 완료 처리하지 못했습니다.") from exc
