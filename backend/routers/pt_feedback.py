from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from backend.database import get_db
from backend.models import PtAssignment, PtFeedback, User, WorkoutRecord
from backend.pt_assignment_schemas import PtAssignmentResult, PtFeedbackItem, PtFeedbackList, PtFeedbackWrite
from backend.routers.pt import get_current_user, require_role
from backend.security import require_employed_trainer
from backend.routers.pt_assignment import assignment_query, serialize_assignment
from backend.services.notification_service import create_notification

router = APIRouter(prefix="/api/pt", tags=["pt-feedback"])


def feedback_query():
    return select(PtFeedback).options(
        joinedload(PtFeedback.assignment).joinedload(PtAssignment.exercise),
        joinedload(PtFeedback.assignment).joinedload(PtAssignment.user_exercise),
        joinedload(PtFeedback.workout_record),
        joinedload(PtFeedback.trainer),
        joinedload(PtFeedback.member),
    )


def serialize_feedback(item: PtFeedback) -> PtFeedbackItem:
    exercise = item.assignment.exercise or item.assignment.user_exercise
    if exercise is None:
        raise HTTPException(status_code=500, detail="피드백의 운동 정보를 찾을 수 없습니다.")
    record = item.workout_record
    return PtFeedbackItem(
        feedback_id=item.feedback_id, assignment_id=item.assignment_id,
        workout_record_id=item.workout_record_id, trainer_id=item.trainer_id,
        trainer_name=item.trainer.name, member_id=item.member_id, member_name=item.member.name,
        assignment_title=item.assignment.title, exercise_name=exercise.exercise_name,
        completed_at=record.completed_at, posture_score=record.average_posture_score,
        image_url=record.image_url, content=item.content,
        created_at=item.created_at, updated_at=item.updated_at,
    )


def result_for_trainer(db: Session, assignment_id: int, trainer_id: int) -> PtAssignmentResult:
    assignment = db.scalar(assignment_query().where(PtAssignment.assignment_id == assignment_id, PtAssignment.trainer_id == trainer_id))
    if assignment is None:
        raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
    if assignment.status != "COMPLETED" or assignment.workout_record_id is None:
        raise HTTPException(status_code=409, detail="운동 기록이 연결된 완료 숙제만 조회할 수 있습니다.")
    record = db.scalar(select(WorkoutRecord).where(WorkoutRecord.workout_record_id == assignment.workout_record_id, WorkoutRecord.user_id == assignment.member_id))
    if record is None or (assignment.exercise_id is not None and record.exercise_id != assignment.exercise_id) or (assignment.user_exercise_id is not None and record.user_exercise_id != assignment.user_exercise_id):
        raise HTTPException(status_code=409, detail="숙제와 운동 기록의 연결이 올바르지 않습니다.")
    feedback = db.scalar(select(PtFeedback).where(PtFeedback.assignment_id == assignment.assignment_id))
    return PtAssignmentResult(
        assignment=serialize_assignment(assignment), completed_sets=record.completed_sets,
        repetition_count=record.repetition_count, workout_minutes=record.workout_minutes,
        calories=record.calories, posture_score=record.average_posture_score,
        feedback_title=record.feedback_title, feedback=record.feedback, image_url=record.image_url,
        trainer_feedback_id=feedback.feedback_id if feedback else None,
        trainer_feedback_content=feedback.content if feedback else None,
        record_source=record.record_source,
        manual_note=record.manual_note,
    )


@router.get("/assignments/{assignment_id}/result", response_model=PtAssignmentResult)
def assignment_result(assignment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    return result_for_trainer(db, assignment_id, current_user.user_id)


@router.post("/assignments/{assignment_id}/feedback", response_model=PtFeedbackItem, status_code=status.HTTP_201_CREATED)
def create_feedback(assignment_id: int, payload: PtFeedbackWrite, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    try:
        assignment = db.scalar(select(PtAssignment).where(PtAssignment.assignment_id == assignment_id, PtAssignment.trainer_id == current_user.user_id).with_for_update())
        if assignment is None:
            raise HTTPException(status_code=404, detail="PT 숙제를 찾을 수 없습니다.")
        if assignment.status != "COMPLETED" or assignment.workout_record_id is None:
            raise HTTPException(status_code=409, detail="완료 기록이 있는 숙제에만 피드백을 작성할 수 있습니다.")
        if db.scalar(select(PtFeedback.feedback_id).where(PtFeedback.assignment_id == assignment_id)) is not None:
            raise HTTPException(status_code=409, detail="이미 작성된 피드백이 있습니다.")
        record = db.scalar(select(WorkoutRecord).where(WorkoutRecord.workout_record_id == assignment.workout_record_id, WorkoutRecord.user_id == assignment.member_id))
        if record is None:
            raise HTTPException(status_code=409, detail="연결된 회원 운동 기록을 찾을 수 없습니다.")
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="피드백 내용을 입력해 주세요.")
        item = PtFeedback(assignment_id=assignment.assignment_id, workout_record_id=record.workout_record_id,
            trainer_id=current_user.user_id, member_id=assignment.member_id, content=content)
        db.add(item); db.flush()
        create_notification(db, user_id=assignment.member_id, title="새로운 운동 피드백이 도착했습니다",
            message=f"{current_user.name} 트레이너님이 {assignment.title}에 피드백을 남겼습니다.",
            notification_type="PT_FEEDBACK_CREATED", target_url="/pt/feedback", reference_id=item.feedback_id)
        db.commit()
        item = db.scalar(feedback_query().where(PtFeedback.feedback_id == item.feedback_id))
        return serialize_feedback(item)
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="피드백 저장에 실패했습니다.") from exc


@router.patch("/feedback/{feedback_id}", response_model=PtFeedbackItem)
def update_feedback(feedback_id: int, payload: PtFeedbackWrite, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_employed_trainer(current_user)
    try:
        item = db.scalar(select(PtFeedback).where(PtFeedback.feedback_id == feedback_id, PtFeedback.trainer_id == current_user.user_id).with_for_update())
        if item is None:
            raise HTTPException(status_code=404, detail="피드백을 찾을 수 없습니다.")
        content = payload.content.strip()
        if not content:
            raise HTTPException(status_code=400, detail="피드백 내용을 입력해 주세요.")
        if item.content != content:
            item.content = content
            create_notification(db, user_id=item.member_id, title="운동 피드백이 수정되었습니다",
                message="트레이너가 PT 숙제 피드백 내용을 수정했습니다.", notification_type="PT_FEEDBACK_UPDATED",
                target_url="/pt/feedback", reference_id=item.feedback_id)
        db.commit(); item = db.scalar(feedback_query().where(PtFeedback.feedback_id == feedback_id)); return serialize_feedback(item)
    except HTTPException:
        db.rollback(); raise
    except Exception as exc:
        db.rollback(); raise HTTPException(status_code=500, detail="피드백 수정에 실패했습니다.") from exc


@router.get("/assignments/{assignment_id}/feedback", response_model=PtFeedbackItem)
def get_assignment_feedback(assignment_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.scalar(feedback_query().where(PtFeedback.assignment_id == assignment_id))
    if item is None or current_user.user_id not in {item.trainer_id, item.member_id}:
        raise HTTPException(status_code=404, detail="피드백을 찾을 수 없습니다.")
    return serialize_feedback(item)


@router.get("/feedback/member", response_model=PtFeedbackList)
def member_feedback(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    require_role(current_user, "MEMBER")
    items = db.scalars(feedback_query().where(PtFeedback.member_id == current_user.user_id).order_by(PtFeedback.updated_at.desc(), PtFeedback.feedback_id.desc())).unique().all()
    return PtFeedbackList(items=[serialize_feedback(item) for item in items], total=len(items))
