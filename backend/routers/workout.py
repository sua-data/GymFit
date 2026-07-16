from datetime import (
    datetime,
    timedelta,
    timezone
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from pydantic import (
    BaseModel,
    Field,
    field_validator
)
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Exercise,
    User,
    WorkoutPlan,
    WorkoutRecord
)

router = APIRouter(
    prefix="/api/workouts",
    tags=["운동 기록"],
)

KST = timezone(
    timedelta(hours=9)
)

def korea_now_naive() -> datetime:
    return datetime.now(
        KST
    ).replace(
        tzinfo=None
    )
class WorkoutRecordCreate(BaseModel):
    user_id: int = Field(
        gt=0
    )

    exercise_code: str = Field(
        min_length=1,
        max_length=50,
    )

    completed_sets: int = Field(
        default=0,
        ge=0,
        le=100,
    )

    repetition_count: int = Field(
        default=0,
        ge=0,
        le=10000,
    )

    workout_minutes: int = Field(
        default=0,
        ge=0,
        le=1440,
    )

    calories: int | None = Field(
        default=None,
        ge=0,
    )

    average_posture_score: int = Field(
        default=0,
        ge=0,
        le=100,
    )

    best_posture_score: int = Field(
        default=0,
        ge=0,
        le=100,
    )

    feedback_title: str | None = Field(
        default=None,
        max_length=150,
    )

    feedback: str | None = None

    image_url: str | None = Field(
        default=None,
        max_length=500,
    )

    started_at: datetime | None = None

    @field_validator(
        "exercise_code"
    )
    @classmethod
    def normalize_exercise_code(
        cls,
        value: str,
    ) -> str:
        return (
            value
            .strip()
            .upper()
        )

    @field_validator(
        "feedback_title",
        "feedback",
        "image_url",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned = value.strip()

        return cleaned or None


class WorkoutRecordCreateResponse(BaseModel):
    message: str
    workout_id: int
    exercise_code: str
    exercise_name: str
    calories: int
    workout_minutes: int
    average_posture_score: int
    best_posture_score: int


@router.post(
    "",
    response_model=(
        WorkoutRecordCreateResponse
    ),
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def create_workout_record(
    request: WorkoutRecordCreate,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.user_id
            == request.user_id,
            User.is_active.is_(True),
        )
    )

    if not user:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "사용자를 찾을 수 없습니다."
            ),
        )

    if user.account_type not in {
        "MEMBER",
        "TRAINER",
    }:
        raise HTTPException(
            status_code=403,
            detail="운동 기록을 저장할 권한이 없습니다."
        )

    exercise = db.scalar(
        select(Exercise).where(
            Exercise.exercise_code
            == request.exercise_code,
            Exercise.is_active.is_(True),
        )
    )

    if not exercise:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "지원하지 않는 운동 종목입니다."
            ),
        )

    completed_at = korea_now_naive()

    started_at = request.started_at

    if started_at is not None:
        if started_at.tzinfo is not None:
            started_at = (
                started_at
                .astimezone(KST)
                .replace(tzinfo=None)
            )
    else:
        started_at = (
            completed_at
            - timedelta(
                minutes=request.workout_minutes
            )
        )

    if started_at > completed_at:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "운동 시작 시간은 완료 시간보다 "
                "늦을 수 없습니다."
            ),
        )

    if request.calories is None:
        calculated_calories = round(
            float(
                exercise
                .calories_per_minute
            )
            * request.workout_minutes
        )
    else:
        calculated_calories = (
            request.calories
        )

    try:
        workout_record = WorkoutRecord(
            user_id=request.user_id,
            exercise_id=(
                exercise.exercise_id
            ),
            started_at=started_at,
            completed_at=completed_at,
            completed_sets=(
                request.completed_sets
            ),
            repetition_count=(
                request.repetition_count
            ),
            workout_minutes=(
                request.workout_minutes
            ),
            calories=calculated_calories,
            average_posture_score=(
                request.average_posture_score
            ),
            best_posture_score=(
                request.best_posture_score
            ),
            feedback_title=(
                request.feedback_title
            ),
            feedback=request.feedback,
            image_url=request.image_url,
        )

        db.add(workout_record)
        db.flush()

        today = completed_at.date()

        today_plan = db.scalar(
            select(WorkoutPlan).where(
                WorkoutPlan.user_id
                == request.user_id,
                WorkoutPlan.exercise_id
                == exercise.exercise_id,
                WorkoutPlan.plan_date
                == today,
            )
        )

        if today_plan:
            today_plan.is_completed = True

        db.commit()
        db.refresh(workout_record)

        return WorkoutRecordCreateResponse(
            message="운동 기록이 저장되었습니다.",

            workout_id=(
                workout_record.workout_record_id
            ),

            exercise_code=(
                exercise.exercise_code
            ),

            exercise_name=(
                exercise.exercise_name
            ),

            calories=(
                workout_record.calories
            ),

            workout_minutes=(
                workout_record.workout_minutes
            ),

            average_posture_score=(
                workout_record.average_posture_score
            ),

            best_posture_score=(
                workout_record.best_posture_score
            ),
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        print(
            "운동 기록 저장 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "운동 기록 저장 중 "
                "오류가 발생했습니다."
            ),
        ) from error