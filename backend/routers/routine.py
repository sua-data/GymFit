from datetime import datetime
from zoneinfo import ZoneInfo

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
from backend.models.workout_record import WorkoutRecord
from backend.routine_schemas import (
    RecommendationApplyRequest,
    RecommendationApplyResponse,
    RecommendationCreate,
    RecommendationItemResponse,
    RecommendationResponse,
    RecommendationSkipReason,
)
from backend.services.routine_recommendation_service import create_recommendation
from backend.models import User
from backend.security import enforce_self, get_current_user

router = APIRouter(prefix="/api/routine", tags=["맞춤 루틴 추천"])


def require_member(user: User) -> None:
    if user.account_type != "MEMBER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="회원 전용 기능입니다.",
        )


def recommendation_plan_skip_reason(plan: WorkoutPlan) -> str:
    if plan.is_completed:
        return "COMPLETED_PLAN_EXISTS"
    if plan.plan_source == "TRAINER":
        return "TRAINER_PLAN_EXISTS"
    if plan.plan_source == "MANUAL":
        return "MANUAL_PLAN_EXISTS"
    return "RECOMMENDED_PLAN_EXISTS"


def can_replace_recommended_plan(
    plan: WorkoutPlan, has_workout_record: bool
) -> bool:
    return (
        plan.plan_source == "RECOMMENDED"
        and not plan.is_completed
        and not has_workout_record
    )


def _load(db: Session, recommendation_id: int) -> RoutineRecommendation | None:
    return db.scalar(
        select(RoutineRecommendation)
        .options(selectinload(RoutineRecommendation.items))
        .where(RoutineRecommendation.recommendation_id == recommendation_id)
    )


def _serialize(
    db: Session,
    recommendation: RoutineRecommendation,
    variant: int = 0,
) -> RecommendationResponse:
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
    workout_dates = sorted({item.workout_date for item in recommendation.items})
    counts_by_date = {
        workout_date: sum(
            item.workout_date == workout_date for item in recommendation.items
        )
        for workout_date in workout_dates
    }
    weekday_codes = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
    daily_count = max(counts_by_date.values(), default=0)
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
        recommended_days=[
            weekday_codes[workout_date.weekday()]
            for workout_date in workout_dates
        ],
        daily_exercise_count=daily_count,
        recommendation_reason=(
            f"주 {recommendation.days_per_week}회 운동을 "
            "회복일과 운동 부위를 고려해 분산했어요."
        ),
        variant=variant,
        items=response_items,
    )


def _generate(payload: RecommendationCreate, db: Session, replace: bool) -> RecommendationResponse:
    try:
        recommendation = create_recommendation(db, payload, replace_existing=replace)
        db.commit()
        recommendation = _load(db, recommendation.recommendation_id)
        return _serialize(db, recommendation, payload.variant)
    except ValueError as error:
        db.rollback()
        if str(error) == "USER_NOT_FOUND":
            raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.") from error
        if str(error) == "NO_EXERCISES":
            raise HTTPException(status_code=422, detail="추천 가능한 활성 운동이 없습니다.") from error
        if str(error) in {
            "PREFERRED_DAYS_COUNT_MISMATCH",
            "INVALID_PREFERRED_DAYS",
        }:
            raise HTTPException(
                status_code=422,
                detail="선호 운동 요일과 주간 운동 횟수를 확인해 주세요.",
            ) from error
        if str(error) == "NO_ALTERNATIVE_RECOMMENDATION":
            raise HTTPException(
                status_code=409,
                detail=(
                    "현재 조건에서는 다른 추천 구성을 만들기 어렵습니다. "
                    "운동 일수나 운동 시간을 변경해보세요."
                ),
            ) from error
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="추천 생성 중 데이터 충돌이 발생했습니다.") from error


@router.post("/recommendations", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED)
def recommend(
    payload: RecommendationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_member(current_user)
    enforce_self(current_user, payload.user_id)
    return _generate(payload, db, False)


@router.get("/recommendations/latest", response_model=RecommendationResponse)
def latest(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_member(current_user)
    enforce_self(current_user, user_id)
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
def regenerate(
    payload: RecommendationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_member(current_user)
    enforce_self(current_user, payload.user_id)
    return _generate(payload, db, True)


@router.post(
    "/recommendations/{recommendation_id}/apply",
    response_model=RecommendationApplyResponse,
)
def apply_recommendation(
    recommendation_id: int,
    payload: RecommendationApplyRequest = RecommendationApplyRequest(),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_member(current_user)
    recommendation = db.scalar(
        select(RoutineRecommendation)
        .options(
            selectinload(
                RoutineRecommendation.items
            )
        )
        .where(
            RoutineRecommendation.recommendation_id
            == recommendation_id
        )
        .with_for_update()
    )

    if not recommendation:
        raise HTTPException(
            status_code=404,
            detail="추천을 찾을 수 없습니다.",
        )

    enforce_self(
        current_user,
        recommendation.user_id,
    )

    if recommendation.status == "APPLIED":
        raise HTTPException(
            status_code=409,
            detail="이미 적용된 추천입니다.",
        )

    if recommendation.status == "REPLACED":
        raise HTTPException(
            status_code=409,
            detail="교체된 추천은 적용할 수 없습니다.",
        )

    if not recommendation.items:
        raise HTTPException(
            status_code=422,
            detail="적용할 추천 항목이 없습니다.",
        )

    created_ids: list[int] = []
    created_dates: set = set()
    skipped_reasons: list[
        RecommendationSkipReason
    ] = []
    replaced_count = 0

    try:
        kst_today = datetime.now(
            ZoneInfo("Asia/Seoul")
        ).date()

        if payload.replace_existing_recommendations:
            replaceable_plans = db.scalars(
                select(WorkoutPlan)
                .where(
                    WorkoutPlan.user_id
                    == recommendation.user_id,
                    WorkoutPlan.plan_source
                    == "RECOMMENDED",
                    WorkoutPlan.plan_date
                    >= kst_today,
                    WorkoutPlan.is_completed.is_(False),
                )
                .with_for_update()
            ).all()

            for existing_plan in replaceable_plans:
                has_record = db.scalar(
                    select(
                        WorkoutRecord.workout_record_id
                    )
                    .where(
                        WorkoutRecord.workout_plan_id
                        == existing_plan.workout_plan_id
                    )
                    .limit(1)
                )

                if not can_replace_recommended_plan(
                    existing_plan,
                    has_record is not None,
                ):
                    continue

                db.delete(existing_plan)
                replaced_count += 1

            db.flush()

        items_per_date = {
            workout_date: sum(
                candidate.workout_date
                == workout_date
                for candidate
                in recommendation.items
            )
            for workout_date in {
                candidate.workout_date
                for candidate
                in recommendation.items
            }
        }

        for item in recommendation.items:

            if (
                item.exercise_id is None
            ) == (
                item.user_exercise_id is None
            ):
                raise HTTPException(
                    status_code=422,
                    detail=(
                        "추천 항목의 운동 참조가 "
                        "올바르지 않습니다."
                    ),
                )

            if item.exercise_id is not None:
                valid_ref = db.scalar(
                    select(
                        Exercise.exercise_id
                    ).where(
                        Exercise.exercise_id
                        == item.exercise_id,
                        Exercise.is_active.is_(True),
                    )
                )
            else:
                valid_ref = db.scalar(
                    select(
                        UserExercise.user_exercise_id
                    ).where(
                        UserExercise.user_exercise_id
                        == item.user_exercise_id,
                        UserExercise.user_id
                        == recommendation.user_id,
                        UserExercise.is_active.is_(True),
                    )
                )

            if valid_ref is None:
                skipped_reasons.append(
                    RecommendationSkipReason(
                        plan_date=item.workout_date,
                        exercise_id=item.exercise_id,
                        reason="INACTIVE_EXERCISE",
                    )
                )
                continue

            if item.exercise_id is not None:
                reference_filter = (
                    WorkoutPlan.exercise_id
                    == item.exercise_id
                )
            else:
                reference_filter = (
                    WorkoutPlan.user_exercise_id
                    == item.user_exercise_id
                )

            duplicate = db.scalar(
                select(WorkoutPlan).where(
                    WorkoutPlan.user_id
                    == recommendation.user_id,
                    WorkoutPlan.plan_date
                    == item.workout_date,
                    reference_filter,
                )
            )

            if duplicate:
                skipped_reasons.append(
                    RecommendationSkipReason(
                        plan_date=item.workout_date,
                        exercise_id=item.exercise_id,
                        reason=(
                            recommendation_plan_skip_reason(
                                duplicate
                            )
                        ),
                    )
                )
                continue

            estimated_minutes = max(
                1,
                recommendation.workout_minutes
                // max(
                    1,
                    items_per_date.get(
                        item.workout_date,
                        1,
                    ),
                ),
            )

            plan = WorkoutPlan(
                user_id=recommendation.user_id,
                exercise_id=item.exercise_id,
                user_exercise_id=(
                    item.user_exercise_id
                ),
                plan_date=item.workout_date,
                set_count=item.recommended_sets,
                repetition_count=(
                    item.recommended_reps
                ),
                estimated_minutes=(
                    estimated_minutes
                ),
                recommendation_item_id=(
                    item.recommendation_item_id
                ),
                plan_source="RECOMMENDED",
            )

            db.add(plan)
            db.flush()

            created_ids.append(
                plan.workout_plan_id
            )
            created_dates.add(
                item.workout_date
            )

            for order in range(
                1,
                item.recommended_sets + 1,
            ):
                db.add(
                    WorkoutPlanSet(
                        workout_plan_id=(
                            plan.workout_plan_id
                        ),
                        set_order=order,
                        repetition_count=(
                            item.recommended_reps
                        ),
                    )
                )

        if not created_ids:
            raise HTTPException(
                status_code=409,
                detail=(
                    "적용할 수 있는 새 운동이 없습니다. "
                    "기존 루틴과 날짜가 겹치는지 "
                    "확인해주세요."
                ),
            )

        recommendation.status = "APPLIED"

        previous_applied_recommendations = db.scalars(
            select(RoutineRecommendation)
            .where(
                RoutineRecommendation.user_id
                == recommendation.user_id,
                RoutineRecommendation.recommendation_id
                != recommendation.recommendation_id,
                RoutineRecommendation.status
                == "APPLIED",
            )
            .with_for_update()
        ).all()

        for previous_recommendation in (
            previous_applied_recommendations
        ):
            previous_recommendation.status = (
                "REPLACED"
            )

        db.commit()

    except HTTPException:
        db.rollback()
        raise

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=409,
            detail=(
                "운동 계획 적용 중 "
                "중복 데이터가 확인되었습니다."
            ),
        ) from error

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="추천 루틴을 적용하지 못했습니다.",
        ) from error

    return RecommendationApplyResponse(
        message="추천 루틴을 적용했습니다.",
        recommendation_id=recommendation_id,
        created_count=len(created_ids),
        updated_count=replaced_count,
        skipped_count=len(skipped_reasons),
        skipped_reasons=skipped_reasons,
        workout_plan_ids=created_ids,
        affected_dates=sorted(created_dates),
    )
