from datetime import (
    date,
    datetime,
    time,
    timedelta,
)
from zoneinfo import ZoneInfo

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)
from sqlalchemy import (
    case,
    func,
    select,
)
from sqlalchemy.orm import Session, joinedload, selectinload

from backend.database import get_db
from backend.models import MemberProfile, TrainerMember, User
from backend.models.exercise import Exercise
from backend.models.notification import Notification
from backend.models.workout_plan import WorkoutPlan
from backend.models.workout_record import WorkoutRecord
from backend.models.user_exercise import UserExercise
from backend.models.pt_schedule import PtSchedule
from backend.services.pt_service import has_active_trainer
from backend.services.exercise_catalog import AI_COACHING_EXERCISE_CODES
from backend.security import enforce_self, get_current_user


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
    today: date,
) -> int:
    if not workout_dates:
        return 0

    unique_dates = sorted(
        set(workout_dates),
        reverse=True,
    )

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


def select_best_posture_records(
    records: list[WorkoutRecord],
) -> dict[int, WorkoutRecord]:
    best_record_by_exercise: dict[int, WorkoutRecord] = {}
    for record in records:
        if record.exercise_id not in best_record_by_exercise:
            best_record_by_exercise[record.exercise_id] = record
    return best_record_by_exercise


def best_posture_exercises_statement():
    return (
        select(Exercise)
        .where(
            Exercise.is_active.is_(True),
            Exercise.exercise_code.in_(AI_COACHING_EXERCISE_CODES),
        )
        .order_by(Exercise.exercise_id.asc())
    )


def best_posture_records_statement(
    user_id: int,
    today_start: datetime,
    today_end: datetime,
):
    return (
        select(WorkoutRecord)
        .join(
            Exercise,
            Exercise.exercise_id == WorkoutRecord.exercise_id,
        )
        .where(
            WorkoutRecord.user_id == user_id,
            Exercise.exercise_code.in_(AI_COACHING_EXERCISE_CODES),
            WorkoutRecord.record_source == "COACHING",
            WorkoutRecord.best_posture_score.is_not(None),
            WorkoutRecord.started_at >= today_start,
            WorkoutRecord.started_at < today_end,
        )
        .order_by(
            WorkoutRecord.best_posture_score.desc(),
            WorkoutRecord.started_at.desc(),
            WorkoutRecord.workout_record_id.desc(),
        )
    )


@router.get("/{user_id}")
def get_dashboard(
    user_id: int,
    response: Response,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    enforce_self(current_user, user_id)
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

    kst = ZoneInfo("Asia/Seoul")
    today = datetime.now(kst).date()

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
            func.sum(
                case(
                    (
                        WorkoutRecord.calorie_calculation_status == "CALCULATED",
                        WorkoutRecord.calories,
                    ),
                    else_=None,
                )
            ),
            func.coalesce(
                func.sum(
                    WorkoutRecord.workout_minutes
                ),
                0,
            ),
            func.sum(case((WorkoutRecord.calorie_calculation_status == "CALCULATED", 1), else_=0)),
            func.sum(case((WorkoutRecord.calorie_calculation_status == "WEIGHT_REQUIRED", 1), else_=0)),
            func.sum(case((WorkoutRecord.calorie_calculation_status == "INVALID_DURATION", 1), else_=0)),
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
        normalized_workout_dates,
        today,
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
        best_posture_exercises_statement()
    ).all()

    posture_records = db.scalars(
        best_posture_records_statement(
            user_id,
            today_start,
            today_end,
        )
    ).all()

    best_postures = []

    for exercise in exercises:
        exercise_records = [
            record
            for record in posture_records
            if record.exercise_id == exercise.exercise_id
        ]

        # posture_records는 최고 자세 점수 내림차순이므로 첫 기록이 오늘 최고 자세.
        best_record = (
            exercise_records[0]
            if exercise_records
            else None
        )

        session_count = len(exercise_records)

        total_repetitions = sum(
            int(record.repetition_count or 0)
            for record in exercise_records
        )

        total_completed_sets = sum(
            int(record.completed_sets or 0)
            for record in exercise_records
        )

        average_scores = [
            float(record.average_posture_score)
            for record in exercise_records
            if record.average_posture_score is not None
        ]

        average_posture_score = (
            round(
                sum(average_scores)
                / len(average_scores)
            )
            if average_scores
            else 0
        )

        best_postures.append(
            {
                "exercise_code": (
                    exercise.exercise_code
                ),
                "exercise_name": (
                    exercise.exercise_name
                ),

                # 오늘 최고 자세 기록
                "image_url": (
                    best_record.image_url
                    if best_record
                    else None
                ),
                "posture_score": (
                    best_record.best_posture_score
                    if best_record
                    else None
                ),
                "feedback_title": (
                    best_record.feedback_title
                    if best_record
                    else None
                ),
                "feedback": (
                    best_record.feedback
                    if best_record
                    else None
                ),

                # 오늘 해당 종목 전체 요약
                "session_count": session_count,
                "total_repetitions": total_repetitions,
                "total_completed_sets": total_completed_sets,
                "average_posture_score": average_posture_score,
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
            func.count(WorkoutRecord.workout_record_id).label("session_count"),
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
    weekly_sessions_by_date: dict[date, int] = {}

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
        weekly_sessions_by_date[row_date] = int(row.session_count or 0)

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
                "completed": weekly_sessions_by_date.get(target_date, 0) > 0,
            }
        )

    weekly_total_minutes = sum(
        weekly_minutes_by_date.values()
    )
    weekly_session_count = sum(weekly_sessions_by_date.values())

    # 최근 운동 기록
    recent_rows = db.execute(
        select(
            WorkoutRecord,
            Exercise,
            UserExercise,
        )
        .options(
            joinedload(WorkoutRecord.trainer),
            selectinload(WorkoutRecord.items),
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
                    record.title if record.record_type == "PT"
                    else exercise.exercise_name if exercise else user_exercise.exercise_name if user_exercise else record.title or "운동 기록"
                ),
                "record_type": record.record_type,
                "trainer_name": record.trainer.name if record.trainer else None,
                "exercise_names": [item.exercise_name for item in record.items[:2]],
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

    user_has_active_trainer = has_active_trainer(
        db,
        user.user_id,
        user.account_type,
    )
    should_show_pt_schedule = (
        user.account_type == "TRAINER"
        or user_has_active_trainer
    )
    next_schedule = None
    schedule_owner = (
        PtSchedule.trainer_id
        if user.account_type == "TRAINER"
        else PtSchedule.member_id
    )
    schedule_person_id = (
        PtSchedule.member_id
        if user.account_type == "TRAINER"
        else PtSchedule.trainer_id
    )
    schedule_row = None
    if should_show_pt_schedule:
        schedule_row = db.execute(
            select(PtSchedule, User)
            .join(
                TrainerMember,
                TrainerMember.trainer_member_id
                == PtSchedule.trainer_member_id,
            )
            .join(User, User.user_id == schedule_person_id)
            .where(
                schedule_owner == user_id,
                TrainerMember.status == "ACTIVE",
                PtSchedule.status == "SCHEDULED",
                PtSchedule.start_at >= datetime.now(ZoneInfo("Asia/Seoul")).replace(tzinfo=None),
            )
            .order_by(PtSchedule.start_at.asc())
            .limit(1)
        ).first()
    if schedule_row:
        schedule, person = schedule_row
        next_schedule = {
            "schedule_id": schedule.schedule_id,
            "start_at": schedule.start_at.isoformat(),
            "end_at": schedule.end_at.isoformat(),
            "location": schedule.location,
            "memo": schedule.memo,
            "person_name": person.name,
            "person_label": "회원" if user.account_type == "TRAINER" else "트레이너",
            "target_url": "/trainer/schedules" if user.account_type == "TRAINER" else "/pt/schedules",
        }

    calorie_status = (
        "CALCULATED" if (today_summary[2] or 0) > 0
        else "WEIGHT_REQUIRED" if (today_summary[3] or 0) > 0
        else "INVALID_DURATION" if (today_summary[4] or 0) > 0
        else None
    )

    return {
        "user": {
            "user_id": user.user_id,
            "name": user.name,
        },
        "summary": {
            "calories": (
                round(float(today_summary[0]), 1)
                if calorie_status == "CALCULATED" and today_summary[0] is not None
                else None
            ),
            "calorie_calculation_status": calorie_status,
            "workout_minutes": int(
                today_summary[1] or 0
            ),
            "completed_sets": int(
                today_summary[5] or 0
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
                int(weekly_session_count)
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
        "account_type": user.account_type,
        "has_active_trainer": user_has_active_trainer,
        "next_pt_schedule": next_schedule,
    }