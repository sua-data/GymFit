from datetime import (
    date,
    datetime,
    time,
    timedelta,
)

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)
from sqlalchemy import (
    case,
    func,
    select,
)
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import MemberProfile, User
from backend.models.exercise import Exercise
from backend.models.notification import Notification
from backend.models.workout_plan import WorkoutPlan
from backend.models.workout_record import WorkoutRecord
from backend.models.user_exercise import UserExercise


router = APIRouter(
    prefix="/api/dashboard",
    tags=["대시보드"],
)


WEEKDAY_LABELS = [
    "월",
    "화",
    "수",
    "목",
    "금",
    "토",
    "일",
]


def get_day_range(
    target_date: date,
) -> tuple[datetime, datetime]:
    start_at = datetime.combine(
        target_date,
        time.min,
    )

    end_at = start_at + timedelta(days=1)

    return start_at, end_at


def calculate_streak_days(
    workout_dates: list[date],
) -> int:
    if not workout_dates:
        return 0

    unique_dates = sorted(
        set(workout_dates),
        reverse=True,
    )

    today = date.today()
    yesterday = today - timedelta(days=1)

    if unique_dates[0] not in {
        today,
        yesterday,
    }:
        return 0

    streak = 1
    expected_date = (
        unique_dates[0]
        - timedelta(days=1)
    )

    for workout_date in unique_dates[1:]:
        if workout_date == expected_date:
            streak += 1
            expected_date -= timedelta(days=1)

        elif workout_date < expected_date:
            break

    return streak


@router.get("/{user_id}")
def get_dashboard(
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail="사용자를 찾을 수 없습니다.",
        )

    weekly_workout_days = None
    if user.account_type == "MEMBER":
        weekly_workout_days = db.scalar(
            select(MemberProfile.weekly_workout_days).where(
                MemberProfile.user_id == user_id
            )
        )

    today = date.today()

    today_start, today_end = get_day_range(
        today
    )

    week_start = (
        today
        - timedelta(
            days=today.weekday()
        )
    )

    week_end = (
        week_start
        + timedelta(days=7)
    )

    week_start_at = datetime.combine(
        week_start,
        time.min,
    )

    week_end_at = datetime.combine(
        week_end,
        time.min,
    )

    # 오늘 요약
    today_summary = db.execute(
        select(
            func.coalesce(
                func.sum(
                    WorkoutRecord.calories
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    WorkoutRecord.workout_minutes
                ),
                0,
            ),
            func.coalesce(
                func.sum(
                    WorkoutRecord.completed_sets
                ),
                0,
            ),
        ).where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.started_at
            >= today_start,
            WorkoutRecord.started_at
            < today_end,
        )
    ).one()

    # 연속 운동 일수 계산용 날짜
    workout_date_rows = db.scalars(
        select(
            func.date(
                WorkoutRecord.started_at
            )
        )
        .where(
            WorkoutRecord.user_id
            == user_id
        )
        .distinct()
        .order_by(
            func.date(
                WorkoutRecord.started_at
            ).desc()
        )
        .limit(60)
    ).all()

    normalized_workout_dates = []

    for value in workout_date_rows:
        if isinstance(value, datetime):
            normalized_workout_dates.append(
                value.date()
            )
        elif isinstance(value, date):
            normalized_workout_dates.append(
                value
            )
        elif isinstance(value, str):
            normalized_workout_dates.append(
                date.fromisoformat(value)
            )

    streak_days = calculate_streak_days(
        normalized_workout_dates
    )

    # 읽지 않은 알림
    unread_notification_count = db.scalar(
        select(
            func.count(
                Notification.notification_id
            )
        ).where(
            Notification.user_id == user_id,
            Notification.is_read.is_(False),
        )
    ) or 0

    # 분석 가능한 운동 종목
    exercises = db.scalars(
        select(Exercise)
        .where(
            Exercise.is_active.is_(True)
        )
        .order_by(
            Exercise.exercise_id.asc()
        )
    ).all()

    # 오늘 운동 기록
    today_records = db.scalars(
        select(WorkoutRecord)
        .where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.started_at
            >= today_start,
            WorkoutRecord.started_at
            < today_end,
        )
        .order_by(
            WorkoutRecord.best_posture_score.desc(),
            WorkoutRecord.started_at.desc()
        )
    ).all()

    best_record_by_exercise: dict[
        int,
        WorkoutRecord,
    ] = {}

    for record in today_records:
        if (
            record.exercise_id
            not in best_record_by_exercise
        ):
            best_record_by_exercise[
                record.exercise_id
            ] = record

    best_postures = []

    for exercise in exercises:
        record = best_record_by_exercise.get(
            exercise.exercise_id
        )

        best_postures.append(
            {
                "exercise_code": (
                    exercise.exercise_code
                ),
                "exercise_name": (
                    exercise.exercise_name
                ),
                "image_url": (
                    record.image_url
                    if record
                    else None
                ),
                "repetition_count": (
                    record.repetition_count
                    if record
                    else 0
                ),
                "completed_sets": (
                    record.completed_sets
                    if record
                    else 0
                ),
                "posture_score": (
                    record.best_posture_score
                    if record
                    else 0
                ),
                "feedback_title": (
                    record.feedback_title
                    if record
                    else None
                ),
                "feedback": (
                    record.feedback
                    if record
                    else None
                ),
            }
        )

    # 오늘 운동 계획
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
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.plan_date == today,
        )
        .order_by(
            WorkoutPlan.workout_plan_id.asc()
        )
    ).all()

    plan_items = []

    total_plan_minutes = 0

    for plan, exercise, user_exercise in plan_rows:
        if (exercise is None) == (user_exercise is None):
            continue

        exercise_name = (
            exercise.exercise_name
            if exercise is not None
            else user_exercise.exercise_name
        )

        plan_items.append(
            {
                "workout_plan_id": (
                    plan.workout_plan_id
                ),
                "exercise_name": (
                    exercise_name
                ),
                "set_count": plan.set_count,
                "repetition_count": (
                    plan.repetition_count
                ),
                "is_completed": (
                    plan.is_completed
                ),
            }
        )

        total_plan_minutes += (
            plan.estimated_minutes
        )

    # 이번 주 일별 운동 시간
    weekly_rows = db.execute(
        select(
            func.date(
                WorkoutRecord.started_at
            ).label("workout_date"),
            func.coalesce(
                func.sum(
                    WorkoutRecord.workout_minutes
                ),
                0,
            ).label("total_minutes"),
        )
        .where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.started_at
            >= week_start_at,
            WorkoutRecord.started_at
            < week_end_at,
        )
        .group_by(
            func.date(
                WorkoutRecord.started_at
            )
        )
    ).all()

    weekly_minutes_by_date: dict[
        date,
        int,
    ] = {}

    for row in weekly_rows:
        row_date = row.workout_date

        if isinstance(row_date, datetime):
            row_date = row_date.date()

        elif isinstance(row_date, str):
            row_date = date.fromisoformat(
                row_date
            )

        weekly_minutes_by_date[
            row_date
        ] = int(
            row.total_minutes or 0
        )

    max_daily_minutes = max(
        weekly_minutes_by_date.values(),
        default=0,
    )

    weekly_days = []

    for index in range(7):
        target_date = (
            week_start
            + timedelta(days=index)
        )

        minutes = weekly_minutes_by_date.get(
            target_date,
            0,
        )

        percent = (
            round(
                minutes
                / max_daily_minutes
                * 100
            )
            if max_daily_minutes > 0
            else 0
        )

        weekly_days.append(
            {
                "date": target_date.isoformat(),
                "label": WEEKDAY_LABELS[index],
                "minutes": minutes,
                "percent": percent,
                "completed": minutes > 0,
            }
        )

    completed_weekly_workout_days = sum(
        1
        for minutes
        in weekly_minutes_by_date.values()
        if minutes > 0
    )

    weekly_total_minutes = sum(
        weekly_minutes_by_date.values()
    )

    # 최근 운동 기록
    recent_rows = db.execute(
        select(
            WorkoutRecord,
            Exercise,
            UserExercise,
        )
        .outerjoin(
            Exercise,
            WorkoutRecord.exercise_id
            == Exercise.exercise_id,
        )
        .outerjoin(UserExercise, WorkoutRecord.user_exercise_id == UserExercise.user_exercise_id)
        .where(
            WorkoutRecord.user_id == user_id
        )
        .order_by(
            WorkoutRecord.started_at.desc()
        )
        .limit(2)
    ).all()

    recent_workouts = []

    for record, exercise, user_exercise in recent_rows:
        recent_workouts.append(
            {
                "workout_id": (
                    record.workout_record_id
                ),
                "exercise_name": (
                    exercise.exercise_name if exercise else user_exercise.exercise_name if user_exercise else "운동 기록"
                ),
                "image_url": record.image_url,
                "workout_date_text": (
                    record.started_at.strftime(
                        "%Y.%m.%d"
                    )
                ),
                "completed_sets": (
                    record.completed_sets
                ),
                "repetition_count": (
                    record.repetition_count
                ),
                "average_posture_score": (
                    record.average_posture_score
                ),
            }
        )

    return {
        "user": {
            "user_id": user.user_id,
            "name": user.name,
        },
        "summary": {
            "calories": int(
                today_summary[0] or 0
            ),
            "workout_minutes": int(
                today_summary[1] or 0
            ),
            "completed_sets": int(
                today_summary[2] or 0
            ),
            "streak_days": streak_days,
        },
        "has_unread_notification": (
            unread_notification_count > 0
        ),
        "best_postures": best_postures,
        "today_plan": {
            "items": plan_items,
            "total_minutes": (
                total_plan_minutes
            ),
        },
        "weekly_summary": {
            "workout_days": (
                completed_weekly_workout_days
            ),
            "weekly_workout_days": weekly_workout_days,
            "total_minutes": (
                weekly_total_minutes
            ),
            "days": weekly_days,
        },
        "recent_workouts": (
            recent_workouts
        ),
    }
