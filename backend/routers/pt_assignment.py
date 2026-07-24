from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import Exercise, PtAssignment, TrainerMember, User, UserExercise, WorkoutRecord, WorkoutRecordDetailItem
from backend.pt_assignment_schemas import PtAssignmentComplete, PtAssignmentCreate, PtAssignmentItem, PtAssignmentList, PtAssignmentUpdate, PtManualRecordCreate, PtCustomExerciseCreate
from backend.services.exercise_catalog import is_coaching_supported
from backend.routers.pt import get_current_user, require_role
from backend.services.notification_service import create_notification
from backend.services.calorie_service import calculate_for_record, calculate_training_volume, select_met

router = APIRouter(prefix="/api/pt/assignments", tags=["pt-assignments"])
KST = ZoneInfo("Asia/Seoul")
MUTABLE_STATUSES = ("ASSIGNED", "IN_PROGRESS")


@router.post("/custom-exercises", status_code=status.HTTP_201_CREATED)
def create_member_custom_exercise(payload: PtCustomExerciseCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER")
    try:
        active_relationship(db, current_user.user_id, payload.member_id, lock=True)
        existing = db.scalar(select(UserExercise).where(UserExercise.user_id == payload.member_id, func.lower(UserExercise.exercise_name) == payload.exercise_name.lower()).with_for_update())
        if existing is not None:
            if existing.is_active:
                raise HTTPException(status_code=409, detail="회원에게 이미 등록된 운동명입니다.")
            existing.is_active = True
            existing.category = payload.category
            item = existing
        else:
            item = UserExercise(user_id=payload.member_id, exercise_name=payload.exercise_name, category=payload.category, is_active=True)
            db.add(item)
        db.commit(); db.refresh(item)
        return {"exercise_type": "custom", "exercise_id": None, "user_exercise_id": item.user_exercise_id, "exercise_code": None, "exercise_name": item.exercise_name, "category": item.category or "회원 운동", "coaching_supported": False, "coaching_code": None, "ai_coaching_supported": False}
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="회원 운동 등록에 실패했습니다.") from exc


def now_kst() -> datetime:
    return datetime.now(KST).replace(tzinfo=None)


def assignment_query():
    return select(PtAssignment).options(
        joinedload(PtAssignment.trainer), joinedload(PtAssignment.member),
        joinedload(PtAssignment.exercise), joinedload(PtAssignment.user_exercise),
    )


def serialize_assignment(item: PtAssignment) -> PtAssignmentItem:
    if (item.exercise_id is None) == (item.user_exercise_id is None):
        raise HTTPException(status_code=500, detail="운동 참조가 올바르지 않은 PT 숙제입니다.")
    exercise = item.exercise if item.exercise_id is not None else item.user_exercise
    if exercise is None:
        raise HTTPException(status_code=500, detail="연결된 운동을 찾을 수 없습니다.")
    return PtAssignmentItem(
        assignment_id=item.assignment_id, trainer_member_id=item.trainer_member_id,
        trainer_id=item.trainer_id, trainer_name=item.trainer.name,
        member_id=item.member_id, member_name=item.member.name,
        exercise_type="default" if item.exercise_id is not None else "custom",
        exercise_id=item.exercise_id, user_exercise_id=item.user_exercise_id,
        exercise_name=exercise.exercise_name,
        exercise_code=item.exercise.exercise_code if item.exercise_id is not None else None,
        title=item.title, description=item.description, assigned_date=item.assigned_date,
        due_date=item.due_date, target_sets=item.target_sets, target_reps=item.target_reps,
        target_minutes=item.target_minutes, weight_kg=item.weight_kg, status=item.status,
        is_overdue=item.status in MUTABLE_STATUSES and item.due_date is not None and item.due_date < date.today(),
        completed_at=item.completed_at, workout_record_id=item.workout_record_id,
        created_at=item.created_at, updated_at=item.updated_at,
    )


def active_relationship(db: Session, trainer_id: int, member_id: int, lock: bool = False) -> TrainerMember:
    statement = select(TrainerMember).where(
        TrainerMember.trainer_id == trainer_id,
        TrainerMember.member_id == member_id,
        TrainerMember.status == "ACTIVE",
    )
    if lock:
        statement = statement.with_for_update()
    relationship = db.scalar(statement)
    if relationship is None:
        raise HTTPException(status_code=403, detail="활성 PT 연결 관계가 필요합니다.")
    return relationship


def validate_exercise(db: Session, member_id: int, exercise_id: int | None, user_exercise_id: int | None) -> str:
    if (exercise_id is None) == (user_exercise_id is None):
        raise HTTPException(status_code=400, detail="기본 운동과 사용자 운동 중 하나만 선택해 주세요.")
    if exercise_id is not None:
        exercise = db.scalar(select(Exercise).where(Exercise.exercise_id == exercise_id, Exercise.is_active.is_(True)))
        if exercise is None:
            raise HTTPException(status_code=404, detail="활성 기본 운동을 찾을 수 없습니다.")
        return exercise.exercise_name
    user_exercise = db.scalar(select(UserExercise).where(UserExercise.user_exercise_id == user_exercise_id, UserExercise.user_id == member_id, UserExercise.is_active.is_(True)))
    if user_exercise is None:
        raise HTTPException(status_code=404, detail="회원의 활성 사용자 운동을 찾을 수 없습니다.")
    return user_exercise.exercise_name


def locked_assignment(db: Session, assignment_id: int) -> PtAssignment:
    item = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id).with_for_update())
    if item is None:
        raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
    return item


def require_active_for_change(db: Session, item: PtAssignment) -> None:
    active_relationship(db, item.trainer_id, item.member_id, lock=True)
    if item.status not in MUTABLE_STATUSES:
        raise HTTPException(status_code=409, detail="현재 상태에서는 PT 숙제를 변경할 수 없습니다.")


@router.post("", response_model=PtAssignmentItem, status_code=status.HTTP_201_CREATED)
def create_assignment(payload: PtAssignmentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER")
    try:
        relationship = active_relationship(db, current_user.user_id, payload.member_id, lock=True)
        exercise_name = validate_exercise(db, payload.member_id, payload.exercise_id, payload.user_exercise_id)
        item = PtAssignment(trainer_member_id=relationship.trainer_member_id, trainer_id=current_user.user_id,
            member_id=payload.member_id, exercise_id=payload.exercise_id, user_exercise_id=payload.user_exercise_id,
            title=exercise_name, description=payload.description, assigned_date=payload.assigned_date,
            due_date=payload.due_date, target_sets=payload.target_sets, target_reps=payload.target_reps,
            target_minutes=payload.target_minutes, weight_kg=payload.weight_kg)
        db.add(item); db.flush()
        create_notification(db, user_id=item.member_id, title="새 PT 숙제가 도착했어요",
            message=f"{current_user.name} 트레이너가 '{item.title}' 숙제를 등록했습니다.",
            notification_type="PT_ASSIGNMENT_CREATED", target_url="/pt/assignments", reference_id=item.assignment_id)
        db.commit()
        item = db.scalar(assignment_query().where(PtAssignment.assignment_id == item.assignment_id))
        return serialize_assignment(item)
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="PT 숙제 등록에 실패했습니다.") from exc


def list_assignments(db: Session, owner_field, owner_id: int, assignment_status: str | None, member_id: int | None, date_from: date | None, date_to: date | None, limit: int, offset: int) -> PtAssignmentList:
    filters = [owner_field == owner_id]
    if assignment_status:
        filters.append(PtAssignment.status == assignment_status)
    if member_id is not None:
        filters.append(PtAssignment.member_id == member_id)
    if date_from is not None:
        filters.append(PtAssignment.assigned_date >= date_from)
    if date_to is not None:
        filters.append(PtAssignment.assigned_date <= date_to)
    total = db.scalar(select(func.count(PtAssignment.assignment_id)).where(*filters)) or 0
    items = db.scalars(assignment_query().where(*filters).order_by(PtAssignment.due_date.desc(), PtAssignment.assignment_id.desc()).offset(offset).limit(limit)).all()
    return PtAssignmentList(items=[serialize_assignment(item) for item in items], total=total)


@router.get("/trainer", response_model=PtAssignmentList)
def trainer_assignments(member_id: int | None = Query(default=None, gt=0), assignment_status: str | None = Query(default=None, alias="status"), date_from: date | None = None, date_to: date | None = None, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER")
    return list_assignments(db, PtAssignment.trainer_id, current_user.user_id, assignment_status, member_id, date_from, date_to, limit, offset)


@router.get("/member", response_model=PtAssignmentList)
def member_assignments(assignment_status: str | None = Query(default=None, alias="status"), assigned_date: date | None = None, due_date: date | None = None, limit: int = Query(100, ge=1, le=200), offset: int = Query(0, ge=0), current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    result = list_assignments(db, PtAssignment.member_id, current_user.user_id, assignment_status, None, assigned_date, None, limit, offset)
    if due_date is not None:
        result.items = [item for item in result.items if item.due_date == due_date]
        result.total = len(result.items)
    return result


def get_owned_assignment(db: Session, assignment_id: int, current_user: User, trainer: bool) -> PtAssignmentItem:
    field = PtAssignment.trainer_id if trainer else PtAssignment.member_id
    item = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id, field == current_user.user_id))
    if item is None:
        raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
    return serialize_assignment(item)


@router.get("/trainer/{assignment_id}", response_model=PtAssignmentItem)
def trainer_assignment_detail(assignment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER"); return get_owned_assignment(db, assignment_id, current_user, True)


@router.get("/member/{assignment_id}", response_model=PtAssignmentItem)
def member_assignment_detail(assignment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER"); return get_owned_assignment(db, assignment_id, current_user, False)


@router.patch("/{assignment_id}", response_model=PtAssignmentItem)
def update_assignment(assignment_id: int, payload: PtAssignmentUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER")
    try:
        item = locked_assignment(db, assignment_id)
        if item.trainer_id != current_user.user_id: raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
        require_active_for_change(db, item)
        changes = payload.model_dump(exclude_unset=True)
        exercise_changed = "exercise_id" in changes or "user_exercise_id" in changes
        if exercise_changed:
            next_exercise_id = changes.get("exercise_id", item.exercise_id)
            next_user_exercise_id = changes.get("user_exercise_id", item.user_exercise_id)
            if "exercise_id" in changes and changes["exercise_id"] is not None:
                next_user_exercise_id = None
            if "user_exercise_id" in changes and changes["user_exercise_id"] is not None:
                next_exercise_id = None
            exercise_name = validate_exercise(db, item.member_id, next_exercise_id, next_user_exercise_id)
            source_actually_changed = (
                next_exercise_id != item.exercise_id
                or next_user_exercise_id != item.user_exercise_id
            )
            changes["exercise_id"] = next_exercise_id
            changes["user_exercise_id"] = next_user_exercise_id
            if source_actually_changed:
                changes["title"] = exercise_name
        for key, value in changes.items(): setattr(item, key, value)
        if item.due_date is not None and item.due_date < item.assigned_date: raise HTTPException(status_code=400, detail="마감일은 배정일보다 빠를 수 없습니다.")
        if not any(value is not None for value in (item.target_sets, item.target_reps, item.target_minutes)): raise HTTPException(status_code=400, detail="목표값을 하나 이상 입력해 주세요.")
        create_notification(db, user_id=item.member_id, title="PT 숙제가 수정되었어요", message=f"'{item.title}' 숙제 내용이 변경되었습니다.", notification_type="PT_ASSIGNMENT_UPDATED", target_url="/pt/assignments", reference_id=item.assignment_id)
        db.commit(); item = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id)); return serialize_assignment(item)
    except HTTPException: db.rollback(); raise
    except Exception as exc: db.rollback(); raise HTTPException(status_code=500, detail="PT 숙제 수정에 실패했습니다.") from exc


@router.patch("/{assignment_id}/cancel", response_model=PtAssignmentItem)
def cancel_assignment(assignment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "TRAINER")
    try:
        item = locked_assignment(db, assignment_id)
        if item.trainer_id != current_user.user_id: raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
        require_active_for_change(db, item); item.status = "CANCELLED"
        create_notification(db, user_id=item.member_id, title="PT 숙제가 취소되었어요", message=f"'{item.title}' 숙제가 취소되었습니다.", notification_type="PT_ASSIGNMENT_CANCELLED", target_url="/pt/assignments", reference_id=item.assignment_id)
        db.commit(); item = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id)); return serialize_assignment(item)
    except HTTPException: db.rollback(); raise
    except Exception as exc: db.rollback(); raise HTTPException(status_code=500, detail="PT 숙제 취소에 실패했습니다.") from exc


@router.patch("/{assignment_id}/start", response_model=PtAssignmentItem)
def start_assignment(assignment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    try:
        item = locked_assignment(db, assignment_id)
        if item.member_id != current_user.user_id: raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
        require_active_for_change(db, item)
        if item.status != "ASSIGNED": raise HTTPException(status_code=409, detail="배정 상태의 숙제만 시작할 수 있습니다.")
        item.status = "IN_PROGRESS"; db.commit(); item = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id)); return serialize_assignment(item)
    except HTTPException: db.rollback(); raise
    except Exception as exc: db.rollback(); raise HTTPException(status_code=500, detail="PT 숙제 시작 처리에 실패했습니다.") from exc


@router.patch("/{assignment_id}/complete", response_model=PtAssignmentItem)
def complete_assignment(assignment_id: int, payload: PtAssignmentComplete, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    try:
        item = locked_assignment(db, assignment_id)
        if item.member_id != current_user.user_id: raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
        require_active_for_change(db, item)
        if item.user_exercise_id is not None: raise HTTPException(status_code=400, detail="사용자 운동 숙제에는 기존 운동 기록을 연결할 수 없습니다.")
        record = db.scalar(select(WorkoutRecord).where(WorkoutRecord.workout_record_id == payload.workout_record_id, WorkoutRecord.user_id == current_user.user_id, WorkoutRecord.exercise_id == item.exercise_id))
        if record is None: raise HTTPException(status_code=404, detail="연결할 운동 기록을 찾을 수 없습니다.")
        item.status = "COMPLETED"; item.completed_at = now_kst(); item.workout_record_id = payload.workout_record_id
        create_notification(db, user_id=item.trainer_id, title="PT 숙제를 완료했어요", message=f"{current_user.name} 회원이 '{item.title}' 숙제를 완료했습니다.", notification_type="PT_ASSIGNMENT_COMPLETED", target_url="/trainer/assignments", reference_id=item.assignment_id)
        db.commit(); item = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id)); return serialize_assignment(item)
    except HTTPException: db.rollback(); raise
    except Exception as exc: db.rollback(); raise HTTPException(status_code=500, detail="PT 숙제 완료 처리에 실패했습니다.") from exc


@router.post("/{assignment_id}/manual-record", response_model=PtAssignmentItem, status_code=status.HTTP_201_CREATED)
def create_manual_assignment_record(assignment_id: int, payload: PtManualRecordCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    try:
        item = locked_assignment(db, assignment_id)
        if item.member_id != current_user.user_id:
            raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
        require_active_for_change(db, item)
        if item.workout_record_id is not None:
            raise HTTPException(status_code=409, detail="이미 운동 기록이 연결된 PT 숙제입니다.")
        if item.exercise_id is not None and is_coaching_supported(item.exercise.exercise_code):
            raise HTTPException(status_code=400, detail="실시간 코칭 지원 운동은 코칭 완료 후 저장해 주세요.")
        calorie_result = None
        if item.exercise is not None:
            met_used = select_met(item.exercise, "MODERATE")
            member_weight = current_user.member_profile.weight_kg if current_user.member_profile else None
            calorie_result = calculate_for_record(met_used, member_weight, payload.workout_minutes)
        calories = calorie_result.calories if calorie_result else None
        completed_at = now_kst()
        record = WorkoutRecord(
            user_id=current_user.user_id,
            record_type="WORKOUT",
            title=f"{item.title} 운동",
            workout_date=completed_at.date(),
            exercise_id=item.exercise_id,
            user_exercise_id=item.user_exercise_id,
            started_at=completed_at - timedelta(minutes=payload.workout_minutes),
            completed_at=completed_at,
            completed_sets=payload.completed_sets,
            repetition_count=payload.repetition_count,
            workout_minutes=payload.workout_minutes,
            calories=calories,
            exercise_intensity="MODERATE" if calorie_result else None,
            intensity_is_default=True if calorie_result else None,
            met_used=calorie_result.met_used if calorie_result else None,
            user_weight_used_kg=calorie_result.user_weight_used_kg if calorie_result else None,
            calorie_calculation_status=calorie_result.status if calorie_result else None,
            weight_kg=item.weight_kg,
            training_volume_kg=calculate_training_volume(
                item.weight_kg,
                total_repetitions=payload.repetition_count,
            ),
            average_posture_score=None,
            best_posture_score=None,
            feedback_title=None,
            feedback=None,
            image_url=None,
            record_source="PT_ASSIGNMENT_MANUAL",
            manual_note=payload.note,
        )
        db.add(record); db.flush()
        db.add(WorkoutRecordDetailItem(
            record_id=record.workout_record_id,
            exercise_id=item.exercise_id,
            user_exercise_id=item.user_exercise_id,
            exercise_name=item.title,
            repetitions=payload.repetition_count or None,
            completed_sets=payload.completed_sets or None,
            workout_minutes=payload.workout_minutes or None,
            memo=payload.note,
            display_order=1,
        ))
        item.workout_record_id = record.workout_record_id
        item.status = "COMPLETED"
        item.completed_at = completed_at
        create_notification(db, user_id=item.trainer_id, title="PT 숙제를 완료했습니다",
            message=f"{current_user.name}님이 {item.title} 숙제를 완료했습니다.",
            notification_type="PT_ASSIGNMENT_COMPLETED", target_url="/trainer/assignments", reference_id=item.assignment_id)
        db.commit(); item = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id)); return serialize_assignment(item)
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="수동 운동 기록 저장에 실패했습니다.") from exc
