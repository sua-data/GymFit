from datetime import (
    date,
    datetime,
    timedelta,
    timezone
)
from decimal import Decimal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status
)
from pydantic import (
    BaseModel,
    Field,
    field_validator,
    model_validator
)
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    Exercise,
    User,
    UserExercise,
    WorkoutPlan,
    WorkoutPlanSet,
    WorkoutRecord
)

router = APIRouter(
    prefix="/api/workouts",
    tags=["운동 기록"],
)

KST = timezone(
    timedelta(hours=9)
)

AI_COACHING_EXERCISE_CODES = {
    "SQUAT",
    "PUSHUP",
    "SHOULDER_PRESS",
}

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


class WorkoutRecordItem(BaseModel):
    workout_record_id: int
    exercise_name: str
    exercise_code: str | None
    started_at: datetime
    completed_at: datetime | None
    completed_sets: int
    repetition_count: int
    workout_minutes: int
    calories: int
    posture_score: float | None
    best_posture_score: float | None
    feedback_title: str | None
    feedback: str | None
    image_url: str | None


class WorkoutRecordListResponse(BaseModel):
    items: list[WorkoutRecordItem]
    total: int
    limit: int
    offset: int


class WorkoutPlanSetItem(BaseModel):
    workout_plan_set_id: int | None
    set_order: int
    repetition_count: int | None
    duration_seconds: int | None
    weight_kg: Decimal | None
    is_completed: bool


class WorkoutPlanSetInput(BaseModel):
    repetition_count: int | None = Field(
        default=None,
        ge=1,
        le=10000
    )
    duration_seconds: int | None = Field(
        default=None,
        ge=1,
        le=86400
    )
    weight_kg: Decimal | None = Field(
        default=None,
        ge=0,
        le=99999.99
    )

    @model_validator(mode="after")
    def require_repetition_or_duration(self):
        if (
            self.repetition_count is None
            and self.duration_seconds is None
        ):
            raise ValueError(
                "각 세트에는 반복 횟수 또는 유지 시간이 필요합니다."
            )
        return self


class TodayWorkoutPlanItem(BaseModel):
    workout_plan_id: int
    exercise_type: str
    exercise_id: int | None
    user_exercise_id: int | None
    exercise_code: str | None
    exercise_name: str
    set_count: int
    repetition_count: int
    estimated_minutes: int
    is_completed: bool
    ai_coaching_supported: bool
    sets: list[WorkoutPlanSetItem]


class TodayWorkoutPlanResponse(BaseModel):
    plan_date: date
    total_count: int
    completed_count: int
    total_minutes: int
    items: list[TodayWorkoutPlanItem]


class ExerciseListItem(BaseModel):
    exercise_type: str
    exercise_id: int | None
    user_exercise_id: int | None
    exercise_code: str | None
    exercise_name: str
    ai_coaching_supported: bool


class ExerciseListResponse(BaseModel):
    items: list[ExerciseListItem]


class WorkoutPlanCreate(BaseModel):
    user_id: int = Field(
        gt=0
    )

    exercise_type: str | None = None
    exercise_id: int | None = Field(default=None, gt=0)
    user_exercise_id: int | None = Field(default=None, gt=0)
    exercise_code: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    plan_date: date

    set_count: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    repetition_count: int | None = Field(
        default=None,
        ge=1,
        le=10000,
    )

    estimated_minutes: int = Field(
        ge=1,
        le=1440,
    )
    sets: list[WorkoutPlanSetInput] | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def require_sets_or_legacy_summary(self):
        if self.sets:
            return self
        if self.set_count and self.repetition_count:
            return self
        raise ValueError(
            "세트 상세 또는 기존 세트 수와 반복 횟수가 필요합니다."
        )

    @field_validator(
        "exercise_code"
    )
    @classmethod
    def normalize_plan_exercise_code(
        cls,
        value: str | None,
    ) -> str | None:
        return value.strip().upper() if value else None


class UserExerciseCreate(BaseModel):
    user_id: int = Field(gt=0)
    exercise_name: str = Field(min_length=1, max_length=100)

    @field_validator("exercise_name")
    @classmethod
    def clean_exercise_name(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("운동명을 입력해 주세요.")
        return cleaned


class UserExerciseUpdate(UserExerciseCreate):
    pass


class UserExerciseResponse(BaseModel):
    message: str
    item: ExerciseListItem


class UserExerciseDeleteResponse(BaseModel):
    message: str
    user_exercise_id: int


class WorkoutPlanCreateResponse(BaseModel):
    message: str
    created: bool
    item: TodayWorkoutPlanItem


class WorkoutPlanUpdate(BaseModel):
    user_id: int = Field(
        gt=0
    )

    set_count: int | None = Field(
        default=None,
        ge=1,
        le=100,
    )

    repetition_count: int | None = Field(
        default=None,
        ge=1,
        le=10000,
    )

    estimated_minutes: int = Field(
        ge=1,
        le=1440,
    )
    sets: list[WorkoutPlanSetInput] | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    @model_validator(mode="after")
    def require_sets_or_legacy_summary(self):
        if self.sets:
            return self
        if self.set_count and self.repetition_count:
            return self
        raise ValueError(
            "세트 상세 또는 기존 세트 수와 반복 횟수가 필요합니다."
        )


class WorkoutPlanUpdateResponse(BaseModel):
    message: str
    item: TodayWorkoutPlanItem


class WorkoutPlanCompleteRequest(BaseModel):
    user_id: int = Field(
        gt=0
    )


class WorkoutPlanCompleteResponse(BaseModel):
    message: str
    item: TodayWorkoutPlanItem


class WorkoutPlanDeleteResponse(BaseModel):
    message: str
    workout_plan_id: int


def require_active_user(db: Session, user_id: int) -> User:
    user = db.scalar(
        select(User).where(
            User.user_id == user_id,
            User.is_active.is_(True),
        )
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )
    return user


def create_exercise_item(
    user_exercise: UserExercise,
) -> ExerciseListItem:
    return ExerciseListItem(
        exercise_type="custom",
        exercise_id=None,
        user_exercise_id=user_exercise.user_exercise_id,
        exercise_code=None,
        exercise_name=user_exercise.exercise_name,
        ai_coaching_supported=False,
    )


def get_owned_user_exercise(
    db: Session,
    user_id: int,
    user_exercise_id: int,
    active_only: bool = False,
) -> UserExercise:
    conditions = [
        UserExercise.user_exercise_id == user_exercise_id,
        UserExercise.user_id == user_id,
    ]
    if active_only:
        conditions.append(UserExercise.is_active.is_(True))
    user_exercise = db.scalar(select(UserExercise).where(*conditions))
    if not user_exercise:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자 운동을 찾을 수 없습니다.",
        )
    return user_exercise


def build_plan_set_inputs(
    sets: list[WorkoutPlanSetInput] | None,
    set_count: int | None,
    repetition_count: int | None,
) -> list[WorkoutPlanSetInput]:
    if sets:
        return sets

    if set_count is None or repetition_count is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="세트 상세 정보가 필요합니다.",
        )

    return [
        WorkoutPlanSetInput(
            repetition_count=repetition_count,
        )
        for _ in range(set_count)
    ]


def sync_plan_sets(
    db: Session,
    workout_plan: WorkoutPlan,
    set_inputs: list[WorkoutPlanSetInput],
) -> list[WorkoutPlanSet]:
    existing_sets = db.scalars(
        select(WorkoutPlanSet).where(
            WorkoutPlanSet.workout_plan_id
            == workout_plan.workout_plan_id
        )
    ).all()

    for existing_set in existing_sets:
        db.delete(existing_set)

    db.flush()

    plan_sets = []

    for index, set_input in enumerate(set_inputs, start=1):
        plan_set = WorkoutPlanSet(
            workout_plan_id=workout_plan.workout_plan_id,
            set_order=index,
            repetition_count=set_input.repetition_count,
            duration_seconds=set_input.duration_seconds,
            weight_kg=set_input.weight_kg,
            is_completed=workout_plan.is_completed,
        )
        db.add(plan_set)
        plan_sets.append(plan_set)

    workout_plan.set_count = len(set_inputs)
    workout_plan.repetition_count = (
        set_inputs[0].repetition_count or 0
    )

    return plan_sets


def get_plan_sets(
    db: Session,
    workout_plan: WorkoutPlan,
) -> list[WorkoutPlanSet]:
    plan_sets = db.scalars(
        select(WorkoutPlanSet)
        .where(
            WorkoutPlanSet.workout_plan_id
            == workout_plan.workout_plan_id
        )
        .order_by(WorkoutPlanSet.set_order.asc())
    ).all()

    return list(plan_sets)


def create_plan_item(
    workout_plan: WorkoutPlan,
    exercise: Exercise | None,
    user_exercise: UserExercise | None,
    plan_sets: list[WorkoutPlanSet],
) -> TodayWorkoutPlanItem:
    if (exercise is None) == (user_exercise is None):
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="운동 참조가 올바르지 않은 계획입니다.",
        )

    if exercise is not None:
        exercise_type = "default"
        exercise_id = exercise.exercise_id
        user_exercise_id = None
        exercise_code = exercise.exercise_code
        exercise_name = exercise.exercise_name
    elif user_exercise is not None:
        exercise_type = "custom"
        exercise_id = None
        user_exercise_id = user_exercise.user_exercise_id
        exercise_code = None
        exercise_name = user_exercise.exercise_name
    return TodayWorkoutPlanItem(
        workout_plan_id=(
            workout_plan.workout_plan_id
        ),
        exercise_type=exercise_type,
        exercise_id=exercise_id,
        user_exercise_id=user_exercise_id,
        exercise_code=exercise_code,
        exercise_name=exercise_name,
        set_count=(
            workout_plan.set_count
        ),
        repetition_count=(
            workout_plan.repetition_count
        ),
        estimated_minutes=(
            workout_plan.estimated_minutes
        ),
        is_completed=(
            workout_plan.is_completed
        ),
        ai_coaching_supported=(
            exercise_code
            in AI_COACHING_EXERCISE_CODES
        ),
        sets=[
            WorkoutPlanSetItem(
                workout_plan_set_id=plan_set.workout_plan_set_id,
                set_order=plan_set.set_order,
                repetition_count=plan_set.repetition_count,
                duration_seconds=plan_set.duration_seconds,
                weight_kg=plan_set.weight_kg,
                is_completed=plan_set.is_completed,
            )
            for plan_set in plan_sets
        ],
    )


@router.get(
    "/exercises",
    response_model=ExerciseListResponse,
)
def get_active_exercises(
    user_id: int,
    db: Session = Depends(get_db),
):
    require_active_user(db, user_id)
    exercises = db.scalars(
        select(Exercise)
        .where(
            Exercise.is_active.is_(True)
        )
        .order_by(
            Exercise.exercise_name.asc(),
            Exercise.exercise_id.asc(),
        )
    ).all()

    user_exercises = db.scalars(
        select(UserExercise)
        .where(
            UserExercise.user_id == user_id,
            UserExercise.is_active.is_(True),
        )
        .order_by(
            UserExercise.exercise_name.asc(),
            UserExercise.user_exercise_id.asc(),
        )
    ).all()

    items = [
            ExerciseListItem(
                exercise_type="default",
                exercise_id=(
                    exercise.exercise_id
                ),
                user_exercise_id=None,
                exercise_code=(
                    exercise.exercise_code
                ),
                exercise_name=(
                    exercise.exercise_name
                ),
                ai_coaching_supported=(
                    exercise.exercise_code
                    in AI_COACHING_EXERCISE_CODES
                ),
            )
            for exercise in exercises
        ]
    items.extend(
        ExerciseListItem(
            exercise_type="custom",
            exercise_id=None,
            user_exercise_id=user_exercise.user_exercise_id,
            exercise_code=None,
            exercise_name=user_exercise.exercise_name,
            ai_coaching_supported=False,
        )
        for user_exercise in user_exercises
    )
    return ExerciseListResponse(items=items)


@router.post(
    "/exercises/custom",
    response_model=UserExerciseResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_user_exercise(
    request: UserExerciseCreate,
    db: Session = Depends(get_db),
):
    require_active_user(db, request.user_id)
    existing = db.scalar(
        select(UserExercise).where(
            UserExercise.user_id == request.user_id,
            UserExercise.exercise_name == request.exercise_name,
        )
    )
    if existing:
        if not existing.is_active:
            existing.is_active = True
            try:
                db.commit()
                db.refresh(existing)
            except Exception as error:
                db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="사용자 운동 복구 중 오류가 발생했습니다.",
                ) from error
            return UserExerciseResponse(
                message="사용자 운동이 다시 활성화되었습니다.",
                item=create_exercise_item(existing),
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 사용자 운동이 이미 있습니다.",
        )

    user_exercise = UserExercise(
        user_id=request.user_id,
        exercise_name=request.exercise_name,
    )
    db.add(user_exercise)
    try:
        db.commit()
        db.refresh(user_exercise)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 사용자 운동이 이미 있습니다.",
        ) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 운동 등록 중 오류가 발생했습니다.",
        ) from error
    return UserExerciseResponse(
        message="사용자 운동이 등록되었습니다.",
        item=create_exercise_item(user_exercise),
    )


@router.patch(
    "/exercises/custom/{user_exercise_id}",
    response_model=UserExerciseResponse,
)
def update_user_exercise(
    user_exercise_id: int,
    request: UserExerciseUpdate,
    db: Session = Depends(get_db),
):
    require_active_user(db, request.user_id)
    user_exercise = get_owned_user_exercise(
        db, request.user_id, user_exercise_id, active_only=True
    )
    duplicate = db.scalar(
        select(UserExercise).where(
            UserExercise.user_id == request.user_id,
            UserExercise.exercise_name == request.exercise_name,
            UserExercise.user_exercise_id != user_exercise_id,
        )
    )
    if duplicate:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 사용자 운동이 이미 있습니다.",
        )
    user_exercise.exercise_name = request.exercise_name
    try:
        db.commit()
        db.refresh(user_exercise)
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 사용자 운동이 이미 있습니다.",
        ) from error
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 운동 수정 중 오류가 발생했습니다.",
        ) from error
    return UserExerciseResponse(
        message="사용자 운동명이 수정되었습니다.",
        item=create_exercise_item(user_exercise),
    )


@router.delete(
    "/exercises/custom/{user_exercise_id}",
    response_model=UserExerciseDeleteResponse,
)
def deactivate_user_exercise(
    user_exercise_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    require_active_user(db, user_id)
    user_exercise = get_owned_user_exercise(
        db, user_id, user_exercise_id, active_only=True
    )
    user_exercise.is_active = False
    try:
        db.commit()
    except Exception as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="사용자 운동 비활성화 중 오류가 발생했습니다.",
        ) from error
    return UserExerciseDeleteResponse(
        message="사용자 운동이 비활성화되었습니다.",
        user_exercise_id=user_exercise_id,
    )


@router.get(
    "/plans/today/{user_id}",
    response_model=(
        TodayWorkoutPlanResponse
    ),
)
def get_today_workout_plan(
    user_id: int,
    plan_date: date | None = None,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.user_id == user_id,
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

    target_date = (
        plan_date
        or korea_now_naive().date()
    )

    plan_rows = db.execute(
        select(
            WorkoutPlan,
            Exercise,
            UserExercise,
        )
        .outerjoin(
            Exercise,
            WorkoutPlan.exercise_id
            == Exercise.exercise_id,
        )
        .outerjoin(
            UserExercise,
            (WorkoutPlan.user_exercise_id == UserExercise.user_exercise_id)
            & (WorkoutPlan.user_id == UserExercise.user_id),
        )
        .where(
            WorkoutPlan.user_id
            == user_id,
            WorkoutPlan.plan_date
            == target_date,
        )
        .order_by(
            WorkoutPlan
            .workout_plan_id
            .asc()
        )
    ).all()

    items = []

    for plan, exercise, user_exercise in plan_rows:
        if (exercise is None) == (user_exercise is None):
            continue

        items.append(
            create_plan_item(
                plan,
                exercise,
                user_exercise,
                get_plan_sets(db, plan),
            )
        )

    return TodayWorkoutPlanResponse(
        plan_date=target_date,
        total_count=len(items),
        completed_count=sum(
            item.is_completed
            for item in items
        ),
        total_minutes=sum(
            item.estimated_minutes
            for item in items
        ),
        items=items,
    )


@router.post(
    "/plans",
    response_model=(
        WorkoutPlanCreateResponse
    ),
    status_code=status.HTTP_200_OK,
)
def create_or_update_workout_plan(
    request: WorkoutPlanCreate,
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
            detail="사용자를 찾을 수 없습니다.",
        )

    if user.account_type not in {
        "MEMBER",
        "TRAINER",
    }:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "운동 계획을 등록할 권한이 없습니다."
            ),
        )

    exercise = None
    user_exercise = None
    if request.exercise_type not in {None, "default", "custom"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="exercise_type은 default 또는 custom이어야 합니다.",
        )
    if request.user_exercise_id and (
        request.exercise_id or request.exercise_code
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="기본 운동과 사용자 운동을 동시에 지정할 수 없습니다.",
        )
    if request.exercise_type == "default" and request.user_exercise_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="default 계획에는 사용자 운동 ID를 사용할 수 없습니다.",
        )
    if request.exercise_type == "custom" and (
        request.exercise_id or request.exercise_code
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="custom 계획에는 기본 운동 정보를 사용할 수 없습니다.",
        )
    if request.exercise_type == "custom" or request.user_exercise_id:
        if not request.user_exercise_id:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="사용자 운동 ID가 필요합니다.",
            )
        user_exercise = get_owned_user_exercise(
            db,
            request.user_id,
            request.user_exercise_id,
            active_only=True,
        )
    else:
        conditions = [Exercise.is_active.is_(True)]
        if request.exercise_id:
            conditions.append(Exercise.exercise_id == request.exercise_id)
        elif request.exercise_code:
            conditions.append(Exercise.exercise_code == request.exercise_code)
        else:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="기본 운동 ID 또는 운동 코드가 필요합니다.",
            )
        exercise = db.scalar(select(Exercise).where(*conditions))
        if not exercise:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="등록할 수 없는 운동 종목입니다.",
            )

    existing_plan = db.scalar(
        select(WorkoutPlan).where(
            WorkoutPlan.user_id
            == request.user_id,
            WorkoutPlan.plan_date
            == request.plan_date,
            (
                WorkoutPlan.user_exercise_id == user_exercise.user_exercise_id
                if user_exercise is not None
                else WorkoutPlan.exercise_id == exercise.exercise_id
            ),
        )
    )

    set_inputs = build_plan_set_inputs(
        request.sets,
        request.set_count,
        request.repetition_count,
    )
    created = existing_plan is None

    if existing_plan:
        workout_plan = existing_plan
        workout_plan.estimated_minutes = (
            request.estimated_minutes
        )
    else:
        workout_plan = WorkoutPlan(
            user_id=request.user_id,
            exercise_id=(exercise.exercise_id if exercise else None),
            user_exercise_id=(
                user_exercise.user_exercise_id if user_exercise else None
            ),
            plan_date=request.plan_date,
            set_count=len(set_inputs),
            repetition_count=set_inputs[0].repetition_count or 0,
            estimated_minutes=(
                request.estimated_minutes
            ),
        )

        db.add(workout_plan)

    try:
        db.flush()
        plan_sets = sync_plan_sets(
            db,
            workout_plan,
            set_inputs,
        )
        db.commit()
        db.refresh(workout_plan)
        for plan_set in plan_sets:
            db.refresh(plan_set)

    except IntegrityError as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "동일한 날짜에 같은 운동 계획이 "
                "이미 등록되어 있습니다. 다시 시도해 주세요."
            ),
        ) from error

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "운동 계획 저장 중 "
                "오류가 발생했습니다."
            ),
        ) from error

    return WorkoutPlanCreateResponse(
        message=(
            "운동 계획이 등록되었습니다."
            if created
            else "기존 운동 계획이 수정되었습니다."
        ),
        created=created,
        item=create_plan_item(
            workout_plan,
            exercise,
            user_exercise,
            plan_sets,
        ),
    )


@router.patch(
    "/plans/{workout_plan_id}",
    response_model=(
        WorkoutPlanUpdateResponse
    ),
)
def update_workout_plan(
    workout_plan_id: int,
    request: WorkoutPlanUpdate,
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

    plan_row = db.execute(
        select(
            WorkoutPlan,
            Exercise,
            UserExercise,
        )
        .outerjoin(
            Exercise,
            WorkoutPlan.exercise_id
            == Exercise.exercise_id,
        )
        .outerjoin(
            UserExercise,
            (WorkoutPlan.user_exercise_id == UserExercise.user_exercise_id)
            & (WorkoutPlan.user_id == UserExercise.user_id),
        )
        .where(
            WorkoutPlan.workout_plan_id
            == workout_plan_id,
            WorkoutPlan.user_id
            == request.user_id,
        )
    ).first()

    if not plan_row:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "수정할 운동 계획을 찾을 수 없습니다."
            ),
        )

    workout_plan, exercise, user_exercise = plan_row

    if (exercise is None) == (user_exercise is None):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="운동 참조가 올바르지 않은 비정상 계획입니다.",
        )

    set_inputs = build_plan_set_inputs(
        request.sets,
        request.set_count,
        request.repetition_count,
    )
    workout_plan.estimated_minutes = (
        request.estimated_minutes
    )

    try:
        plan_sets = sync_plan_sets(
            db,
            workout_plan,
            set_inputs,
        )
        db.commit()
        db.refresh(workout_plan)
        for plan_set in plan_sets:
            db.refresh(plan_set)

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "운동 계획 수정 중 "
                "오류가 발생했습니다."
            ),
        ) from error

    return WorkoutPlanUpdateResponse(
        message=(
            "운동 계획이 수정되었습니다."
        ),
        item=create_plan_item(
            workout_plan,
            exercise,
            user_exercise,
            plan_sets,
        ),
    )


@router.patch(
    "/plans/{workout_plan_id}/complete",
    response_model=(
        WorkoutPlanCompleteResponse
    ),
)
def complete_workout_plan(
    workout_plan_id: int,
    request: WorkoutPlanCompleteRequest,
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
            detail="사용자를 찾을 수 없습니다.",
        )

    plan_row = db.execute(
        select(
            WorkoutPlan,
            Exercise,
            UserExercise,
        )
        .outerjoin(
            Exercise,
            WorkoutPlan.exercise_id
            == Exercise.exercise_id,
        )
        .outerjoin(
            UserExercise,
            (WorkoutPlan.user_exercise_id == UserExercise.user_exercise_id)
            & (WorkoutPlan.user_id == UserExercise.user_id),
        )
        .where(
            WorkoutPlan.workout_plan_id
            == workout_plan_id,
            WorkoutPlan.user_id
            == request.user_id,
        )
    ).first()

    if not plan_row:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "완료 처리할 운동 계획을 찾을 수 없습니다."
            ),
        )

    workout_plan, exercise, user_exercise = plan_row

    if (exercise is None) == (user_exercise is None):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="운동 참조가 올바르지 않은 비정상 계획입니다.",
        )
    workout_plan.is_completed = True

    try:
        plan_sets = get_plan_sets(db, workout_plan)
        for plan_set in plan_sets:
            plan_set.is_completed = True
        db.commit()
        db.refresh(workout_plan)

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "운동 계획 완료 처리 중 "
                "오류가 발생했습니다."
            ),
        ) from error

    return WorkoutPlanCompleteResponse(
        message=(
            "운동 계획이 완료 처리되었습니다."
        ),
        item=create_plan_item(
            workout_plan,
            exercise,
            user_exercise,
            plan_sets,
        ),
    )


@router.delete(
    "/plans/{workout_plan_id}",
    response_model=(
        WorkoutPlanDeleteResponse
    ),
)
def delete_workout_plan(
    workout_plan_id: int,
    user_id: int,
    db: Session = Depends(get_db),
):
    user = db.scalar(
        select(User).where(
            User.user_id == user_id,
            User.is_active.is_(True),
        )
    )

    if not user:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail="사용자를 찾을 수 없습니다.",
        )

    workout_plan = db.scalar(
        select(WorkoutPlan).where(
            WorkoutPlan.workout_plan_id
            == workout_plan_id,
            WorkoutPlan.user_id
            == user_id,
        )
    )

    if not workout_plan:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "삭제할 운동 계획을 찾을 수 없습니다."
            ),
        )

    try:
        db.delete(workout_plan)
        db.commit()

    except Exception as error:
        db.rollback()

        raise HTTPException(
            status_code=(
                status
                .HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "운동 계획 삭제 중 "
                "오류가 발생했습니다."
            ),
        ) from error

    return WorkoutPlanDeleteResponse(
        message=(
            "운동 계획이 삭제되었습니다."
        ),
        workout_plan_id=workout_plan_id,
    )


def create_workout_record_item(
    record: WorkoutRecord,
    exercise: Exercise | None,
) -> WorkoutRecordItem:
    return WorkoutRecordItem(
        workout_record_id=record.workout_record_id,
        exercise_name=(
            exercise.exercise_name
            if exercise
            else "운동 기록"
        ),
        exercise_code=(
            exercise.exercise_code
            if exercise
            else None
        ),
        started_at=record.started_at,
        completed_at=record.completed_at,
        completed_sets=record.completed_sets,
        repetition_count=record.repetition_count,
        workout_minutes=record.workout_minutes,
        calories=record.calories,
        posture_score=(
            float(record.average_posture_score)
            if record.average_posture_score is not None
            else None
        ),
        best_posture_score=(
            float(record.best_posture_score)
            if record.best_posture_score is not None
            else None
        ),
        feedback_title=record.feedback_title,
        feedback=record.feedback,
        image_url=record.image_url,
    )


@router.get(
    "/records",
    response_model=WorkoutRecordListResponse,
)
def get_workout_records(
    user_id: int = Query(gt=0),
    period: str = Query(
        default="all",
        pattern="^(all|today|7d|30d)$",
    ),
    limit: int = Query(default=30, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
):
    require_active_user(db, user_id)

    conditions = [WorkoutRecord.user_id == user_id]
    today = korea_now_naive().date()

    if period != "all":
        days = {
            "today": 1,
            "7d": 7,
            "30d": 30,
        }[period]
        start_date = today - timedelta(days=days - 1)
        start_at = datetime.combine(start_date, datetime.min.time())
        end_at = datetime.combine(
            today + timedelta(days=1),
            datetime.min.time(),
        )
        conditions.extend([
            WorkoutRecord.started_at >= start_at,
            WorkoutRecord.started_at < end_at,
        ])

    total = db.scalar(
        select(func.count())
        .select_from(WorkoutRecord)
        .where(*conditions)
    ) or 0

    rows = db.execute(
        select(WorkoutRecord, Exercise)
        .outerjoin(
            Exercise,
            WorkoutRecord.exercise_id == Exercise.exercise_id,
        )
        .where(*conditions)
        .order_by(
            WorkoutRecord.started_at.desc(),
            WorkoutRecord.workout_record_id.desc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()

    return WorkoutRecordListResponse(
        items=[
            create_workout_record_item(record, exercise)
            for record, exercise in rows
        ],
        total=int(total),
        limit=limit,
        offset=offset,
    )


@router.get(
    "/records/{workout_record_id}",
    response_model=WorkoutRecordItem,
)
def get_workout_record_detail(
    workout_record_id: int,
    user_id: int = Query(gt=0),
    db: Session = Depends(get_db),
):
    require_active_user(db, user_id)

    row = db.execute(
        select(WorkoutRecord, Exercise)
        .outerjoin(
            Exercise,
            WorkoutRecord.exercise_id == Exercise.exercise_id,
        )
        .where(
            WorkoutRecord.workout_record_id == workout_record_id,
            WorkoutRecord.user_id == user_id,
        )
    ).first()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="운동 기록을 찾을 수 없습니다.",
        )

    record, exercise = row
    return create_workout_record_item(record, exercise)


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
