from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.database import get_db
from backend.models.exercise import Exercise
from backend.models.routine_recommendation import RoutineRecommendation, RoutineRecommendationItem
from backend.models.user_exercise import UserExercise
from backend.models.workout_plan import WorkoutPlan
from backend.models.workout_plan_set import WorkoutPlanSet
from backend.routine_schemas import (
    RecommendationApplyResponse,
    RecommendationCreate,
    RecommendationItemResponse,
    RecommendationResponse,
)
from backend.services.routine_recommendation_service import create_recommendation

router = APIRouter(prefix="/api/routine", tags=["맞춤 루틴 추천"])


def _load(db: Session, recommendation_id: int) -> RoutineRecommendation | None:
    return db.scalar(
        select(RoutineRecommendation)
        .options(selectinload(RoutineRecommendation.items))
        .where(RoutineRecommendation.recommendation_id == recommendation_id)
    )


def _serialize(db: Session, recommendation: RoutineRecommendation) -> RecommendationResponse:
    exercise_ids = [item.exercise_id for item in recommendation.items if item.exercise_id]
    custom_ids = [item.user_exercise_id for item in recommendation.items if item.user_exercise_id]
    exercises = {
        item.exercise_id: item for item in db.scalars(select(Exercise).where(Exercise.exercise_id.in_(exercise_ids))).all()
    } if exercise_ids else {}
    custom = {
        item.user_exercise_id: item
        for item in db.scalars(select(UserExercise).where(UserExercise.user_exercise_id.in_(custom_ids))).all()
    } if custom_ids else {}
    response_items = []
    for item in recommendation.items:
        exercise = exercises.get(item.exercise_id)
        user_exercise = custom.get(item.user_exercise_id)
        if (exercise is None) == (user_exercise is None):
            continue
        response_items.append(RecommendationItemResponse(
            recommendation_item_id=item.recommendation_item_id,
            exercise_id=item.exercise_id,
            user_exercise_id=item.user_exercise_id,
            exercise_code=exercise.exercise_code if exercise else None,
            exercise_name=exercise.exercise_name if exercise else user_exercise.exercise_name,
            workout_date=item.workout_date,
            sequence_no=item.sequence_no,
            recommended_sets=item.recommended_sets,
            recommended_reps=item.recommended_reps,
            difficulty=item.difficulty,
            coaching_supported=item.coaching_supported,
            adjustment_type=item.adjustment_type,
            recommendation_reason=item.recommendation_reason,
            previous_posture_score=item.previous_posture_score,
            previous_completion_rate=(
                float(item.previous_completion_rate) if item.previous_completion_rate is not None else None
            ),
        ))
    return RecommendationResponse(
        recommendation_id=recommendation.recommendation_id,
        user_id=recommendation.user_id,
        recommendation_date=recommendation.recommendation_date,
        goal=recommendation.goal,
        level=recommendation.level,
        days_per_week=recommendation.days_per_week,
        workout_minutes=recommendation.workout_minutes,
        source_type=recommendation.source_type,
        status=recommendation.status,
        created_at=recommendation.created_at,
        items=response_items,
    )


def _generate(payload: RecommendationCreate, db: Session, replace: bool) -> RecommendationResponse:
    try:
        recommendation = create_recommendation(db, payload, replace_existing=replace)
        db.commit()
        recommendation = _load(db, recommendation.recommendation_id)
        return _serialize(db, recommendation)
    except ValueError as error:
        db.rollback()
        if str(error) == "USER_NOT_FOUND":
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.") from error
        if str(error) == "NO_EXERCISES":
            raise HTTPException(status_code=422, detail="추천 가능한 활성 운동이 없습니다.") from error
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="추천 생성 중 데이터 충돌이 발생했습니다.") from error


@router.post("/recommendations", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def recommend(payload: RecommendationCreate, db: Session = Depends(get_db)):
    return _generate(payload, db, False)


@router.get("/recommendations/latest", response_model=RecommendationResponse)
def latest(user_id: int, db: Session = Depends(get_db)):
    recommendation = db.scalar(
        select(RoutineRecommendation)
        .options(selectinload(RoutineRecommendation.items))
        .where(RoutineRecommendation.user_id == user_id)
        .order_by(RoutineRecommendation.created_at.desc(), RoutineRecommendation.recommendation_id.desc())
    )
    if not recommendation:
        raise HTTPException(status_code=404, detail="생성된 추천이 없습니다.")
    return _serialize(db, recommendation)


@router.post("/recommendations/regenerate", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def regenerate(payload: RecommendationCreate, db: Session = Depends(get_db)):
    return _generate(payload, db, True)


@router.post(
    "/recommendations/{recommendation_id}/apply",
    response_model=RecommendationApplyResponse,
)
def apply_recommendation(recommendation_id: int, db: Session = Depends(get_db)):
    recommendation = db.scalar(
        select(RoutineRecommendation)
        .options(selectinload(RoutineRecommendation.items))
        .where(RoutineRecommendation.recommendation_id == recommendation_id)
        .with_for_update()
    )
    if not recommendation:
        raise HTTPException(status_code=404, detail="추천을 찾을 수 없습니다.")
    if recommendation.status == "APPLIED":
        raise HTTPException(status_code=409, detail="이미 적용된 추천입니다.")
    if recommendation.status == "REPLACED":
        raise HTTPException(status_code=409, detail="교체된 추천은 적용할 수 없습니다.")
    if not recommendation.items:
        raise HTTPException(status_code=422, detail="적용할 추천 항목이 없습니다.")

    created_ids: list[int] = []
    skipped = 0
    try:
        for item in recommendation.items:
            if (item.exercise_id is None) == (item.user_exercise_id is None):
                raise HTTPException(status_code=422, detail="추천 항목의 운동 참조가 올바르지 않습니다.")
            valid_ref = db.scalar(
                select(Exercise.exercise_id).where(
                    Exercise.exercise_id == item.exercise_id, Exercise.is_active.is_(True)
                )
            ) if item.exercise_id else db.scalar(
                select(UserExercise.user_exercise_id).where(
                    UserExercise.user_exercise_id == item.user_exercise_id,
                    UserExercise.user_id == recommendation.user_id,
                    UserExercise.is_active.is_(True),
                )
            )
            if valid_ref is None:
                skipped += 1
                continue
            reference_filter = (
                WorkoutPlan.exercise_id == item.exercise_id
                if item.exercise_id is not None
                else WorkoutPlan.user_exercise_id == item.user_exercise_id
            )
            duplicate = db.scalar(select(WorkoutPlan.workout_plan_id).where(
                WorkoutPlan.user_id == recommendation.user_id,
                WorkoutPlan.plan_date == item.workout_date,
                reference_filter,
            ))
            if duplicate:
                skipped += 1
                continue
            plan = WorkoutPlan(
                user_id=recommendation.user_id,
                exercise_id=item.exercise_id,
                user_exercise_id=item.user_exercise_id,
                plan_date=item.workout_date,
                set_count=item.recommended_sets,
                repetition_count=item.recommended_reps,
                estimated_minutes=max(1, recommendation.workout_minutes // max(1, len(recommendation.items))),
                recommendation_item_id=item.recommendation_item_id,
                plan_source="RECOMMENDED",
            )
            db.add(plan)
            db.flush()
            created_ids.append(plan.workout_plan_id)
            for order in range(1, item.recommended_sets + 1):
                db.add(WorkoutPlanSet(
                    workout_plan_id=plan.workout_plan_id,
                    set_order=order,
                    repetition_count=item.recommended_reps,
                ))
        recommendation.status = "APPLIED"
        db.commit()
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="운동 계획 적용 중 중복 데이터가 확인되었습니다.") from error

    return RecommendationApplyResponse(
        message="추천 루틴을 적용했습니다.",
        recommendation_id=recommendation_id,
        created_count=len(created_ids),
        skipped_count=skipped,
        workout_plan_ids=created_ids,
    )
