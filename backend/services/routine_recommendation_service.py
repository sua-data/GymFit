from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.models.exercise import Exercise
from backend.models.pt_assignment import PtAssignment
from backend.models.routine_recommendation import RoutineRecommendation, RoutineRecommendationItem
from backend.models.user import MemberGoal, MemberProfile, User
from backend.models.workout_plan import WorkoutPlan
from backend.models.workout_record import WorkoutRecord
from backend.models.workout_record_detail import WorkoutRecordDetailItem
from backend.services.exercise_catalog import is_coaching_supported
from backend.services.routine_templates import normalize_goal, normalize_level, select_template

WEEKDAY_CODES = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
WEEKDAY_INDEX = {code: index for index, code in enumerate(WEEKDAY_CODES)}
DEFAULT_TRAINING_DAYS = {
    1: ("WED",),
    2: ("MON", "THU"),
    3: ("MON", "WED", "FRI"),
    4: ("MON", "TUE", "THU", "SAT"),
    5: ("MON", "TUE", "THU", "FRI", "SAT"),
    6: ("MON", "TUE", "WED", "THU", "FRI", "SAT"),
    7: WEEKDAY_CODES,
}
TRAINING_DAY_VARIANTS = {
    2: (
        ("MON", "THU"),
        ("TUE", "FRI"),
        ("WED", "SAT"),
    ),
    3: (
        ("MON", "WED", "FRI"),
        ("TUE", "THU", "SAT"),
        ("WED", "FRI", "SUN"),
    ),
    4: (
        ("MON", "TUE", "THU", "SAT"),
        ("MON", "WED", "FRI", "SAT"),
        ("TUE", "THU", "FRI", "SUN"),
    ),
    5: (
        ("MON", "TUE", "THU", "FRI", "SAT"),
        ("MON", "WED", "THU", "SAT", "SUN"),
        ("TUE", "WED", "FRI", "SAT", "SUN"),
    ),
}
KOREA_TIMEZONE = ZoneInfo("Asia/Seoul")


def korea_today() -> date:
    return datetime.now(KOREA_TIMEZONE).date()


@dataclass(frozen=True)
class ExerciseHistory:
    posture_score: int | None = None
    completion_rate: float | None = None
    consecutive_successes: int = 0
    repeated_feedback: str | None = None


@dataclass(frozen=True)
class Adjustment:
    reps: int
    difficulty: str
    adjustment_type: str
    reason: str


def calculate_completion_rate(actual_reps: int | None, target_reps: int | None) -> float | None:
    if target_reps is None or target_reps <= 0 or actual_reps is None:
        return None
    return max(0.0, actual_reps / target_reps)


def adjust_exercise(base_reps: int, history: ExerciseHistory, exercise_name: str) -> Adjustment:
    score = history.posture_score
    rate = history.completion_rate
    if history.repeated_feedback:
        return Adjustment(
            max(5, base_reps - 2), "EASY", "REPEATED_FEEDBACK",
            f"최근 '{history.repeated_feedback}' 피드백이 반복되어 낮은 강도로 다시 추천합니다.",
        )
    if rate is not None and rate < 0.7:
        return Adjustment(
            max(5, base_reps - 2), "EASY", "PERFORMANCE_DOWN",
            f"최근 {exercise_name} 목표 수행률이 {rate * 100:.0f}%로 확인되어 반복 횟수를 낮춥니다.",
        )
    if score is None:
        return Adjustment(base_reps, "NORMAL", "BASE", "운동 목표와 현재 운동 수준에 맞춘 기본 추천입니다.")
    if score < 70:
        return Adjustment(
            max(5, base_reps - 2), "EASY", "POSTURE_CORRECTION",
            f"최근 {exercise_name} 자세 점수가 {score}점으로 확인되어 반복 횟수를 낮추고 자세 교정을 우선합니다.",
        )
    if score >= 85 and rate is not None and rate >= 1:
        repeated = history.consecutive_successes >= 2
        return Adjustment(
            base_reps + 2,
            "HARD" if repeated else "NORMAL",
            "PROGRESS",
            (
                f"최근 2회 목표를 달성하고 자세 점수도 {score}점으로 안정적이어서 난이도를 높였습니다."
                if repeated
                else f"최근 자세 점수 {score}점, 목표 수행률 {rate * 100:.0f}%로 수행 결과가 좋아 강도를 높였습니다."
            ),
        )
    return Adjustment(
        base_reps, "NORMAL", "MAINTAIN",
        f"최근 자세 점수 {score}점을 반영해 현재 세트와 반복 횟수를 유지합니다.",
    )


def _record_values(db: Session, record: WorkoutRecord, exercise_id: int) -> tuple[int | None, int | None, str | None]:
    detail = db.scalar(
        select(WorkoutRecordDetailItem)
        .where(
            WorkoutRecordDetailItem.record_id == record.workout_record_id,
            WorkoutRecordDetailItem.exercise_id == exercise_id,
        )
        .order_by(WorkoutRecordDetailItem.display_order.asc())
    )
    actual = detail.repetitions if detail and detail.repetitions is not None else record.repetition_count
    score = detail.posture_score if detail and detail.posture_score is not None else record.average_posture_score
    feedback = detail.feedback if detail and detail.feedback else record.feedback
    return actual, score, feedback


def get_recent_history(db: Session, user_id: int, exercise_id: int) -> ExerciseHistory:
    records = list(db.scalars(
        select(WorkoutRecord)
        .where(
            WorkoutRecord.user_id == user_id,
            WorkoutRecord.exercise_id == exercise_id,
            WorkoutRecord.completed_at.is_not(None),
        )
        .order_by(WorkoutRecord.completed_at.desc(), WorkoutRecord.workout_record_id.desc())
        .limit(5)
    ).all())
    # Detail-only multi-exercise records are also supported.
    if not records:
        records = list(db.scalars(
            select(WorkoutRecord)
            .join(WorkoutRecordDetailItem, WorkoutRecordDetailItem.record_id == WorkoutRecord.workout_record_id)
            .where(
                WorkoutRecord.user_id == user_id,
                WorkoutRecordDetailItem.exercise_id == exercise_id,
                WorkoutRecord.completed_at.is_not(None),
            )
            .order_by(WorkoutRecord.completed_at.desc(), WorkoutRecord.workout_record_id.desc())
            .limit(5)
        ).unique().all())
    if not records:
        return ExerciseHistory()

    samples: list[tuple[int | None, float | None, str | None]] = []
    for record in records:
        actual, score, feedback = _record_values(db, record, exercise_id)
        record_date = record.workout_date or record.started_at.date()
        plan = db.scalar(select(WorkoutPlan).where(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.exercise_id == exercise_id,
            WorkoutPlan.plan_date == record_date,
        ))
        target = plan.repetition_count if plan else None
        if target is None:
            assignment = db.scalar(select(PtAssignment).where(
                PtAssignment.member_id == user_id,
                PtAssignment.exercise_id == exercise_id,
                PtAssignment.workout_record_id == record.workout_record_id,
            ))
            target = assignment.target_reps if assignment else None
        samples.append((score, calculate_completion_rate(actual, target), feedback))

    consecutive = 0
    for score, rate, _ in samples:
        if score is not None and score >= 85 and rate is not None and rate >= 1:
            consecutive += 1
        else:
            break
    normalized_feedback = [" ".join(value.split()) for _, _, value in samples if value and value.strip()]
    repeated_feedback = next((value for value, count in Counter(normalized_feedback).items() if count >= 2), None)
    return ExerciseHistory(samples[0][0], samples[0][1], consecutive, repeated_feedback)


def select_training_days(
    days: int,
    preferred_days: list[str] | tuple[str, ...] | None = None,
    variant: int = 0,
) -> tuple[str, ...]:
    if not 1 <= days <= 7:
        raise ValueError("days must be between 1 and 7")
    if preferred_days:
        normalized = tuple(str(day).upper() for day in preferred_days)
        if len(normalized) != days:
            raise ValueError("PREFERRED_DAYS_COUNT_MISMATCH")
        if len(set(normalized)) != len(normalized) or any(
            day not in WEEKDAY_INDEX for day in normalized
        ):
            raise ValueError("INVALID_PREFERRED_DAYS")
        return normalized
    variants = TRAINING_DAY_VARIANTS.get(days)
    if variants:
        return variants[variant % len(variants)]
    base = DEFAULT_TRAINING_DAYS[days]
    if days in {1, 6}:
        shift = variant % 7
        return tuple(
            WEEKDAY_CODES[(WEEKDAY_INDEX[day] + shift) % 7]
            for day in base
        )
    return base


def has_consecutive_run(days: list[str] | tuple[str, ...], run_length: int) -> bool:
    selected = {WEEKDAY_INDEX[day] for day in days}
    return any(
        all((start + offset) % 7 in selected for offset in range(run_length))
        for start in range(7)
    )


def recommendation_dates(
    today: date,
    days: int,
    preferred_days: list[str] | tuple[str, ...] | None = None,
    variant: int = 0,
) -> list[date]:
    selected = select_training_days(days, preferred_days, variant)
    if not preferred_days:
        rotation = (today.toordinal() // 7) % 7
        selected = tuple(
            WEEKDAY_CODES[(WEEKDAY_INDEX[day] + rotation) % 7]
            for day in selected
        )
    offsets = sorted((WEEKDAY_INDEX[day] - today.weekday()) % 7 for day in selected)
    return [today + timedelta(days=offset) for offset in offsets]


def daily_exercise_count(
    level: str,
    workout_minutes: int | None,
    recent_completion_rate: float | None = None,
) -> int:
    normalized_level = str(level or "BEGINNER").upper()
    base = 4 if normalized_level == "BEGINNER" else 5
    if normalized_level == "ADVANCED":
        base = 6
    if workout_minutes is not None:
        if workout_minutes <= 30:
            base = min(base, 4)
        elif workout_minutes > 60:
            base = max(base, 5)
    if recent_completion_rate is not None and recent_completion_rate < 0.7:
        base -= 1
    return max(3, min(6, base))


def _recent_plan_completion_rate(db: Session, user_id: int) -> float | None:
    values = list(db.scalars(
        select(WorkoutPlan.is_completed)
        .where(
            WorkoutPlan.user_id == user_id,
            WorkoutPlan.plan_date <= korea_today(),
        )
        .order_by(WorkoutPlan.plan_date.desc(), WorkoutPlan.workout_plan_id.desc())
        .limit(20)
    ).all())
    if not values:
        return None
    return sum(bool(value) for value in values) / len(values)


def _category_slots(day_index: int, days: int, goal: str) -> tuple[str, ...]:
    if days <= 3:
        extra = "유산소" if goal in {"WEIGHT_LOSS", "ENDURANCE"} else "어깨"
        return ("하체", "가슴", "등", "복근", extra, "팔")
    if day_index % 2 == 0:
        return ("하체", "하체", "하체", "복근", "유산소", "하체")
    return ("가슴", "등", "어깨", "팔", "복근", "유산소")


def build_weekly_exercise_schedule(
    exercises: list[Exercise],
    days: int,
    per_day: int,
    preferred_codes: list[str],
    goal: str,
    variant: int = 0,
) -> list[list[Exercise]]:
    if preferred_codes:
        shift = variant % len(preferred_codes)
        preferred_codes = preferred_codes[shift:] + preferred_codes[:shift]
    rank = {code: index for index, code in enumerate(preferred_codes)}
    ordered = sorted(
        exercises,
        key=lambda exercise: (
            rank.get(exercise.exercise_code, len(rank)),
            exercise.category or "",
            exercise.exercise_id,
        ),
    )
    usage: Counter[int] = Counter()
    schedule: list[list[Exercise]] = []
    previous_categories: Counter[str] = Counter()
    previous_exercise_ids: set[int] = set()
    for day_index in range(days):
        selected: list[Exercise] = []
        slots = _category_slots(day_index + variant, days, goal)
        for slot in slots[:per_day]:
            candidates = [
                exercise for exercise in ordered
                if usage[exercise.exercise_id] < 2
                and exercise not in selected
                and (exercise.category or "") == slot
                and exercise.exercise_id not in previous_exercise_ids
            ]
            if not candidates:
                candidates = [
                    exercise for exercise in ordered
                    if usage[exercise.exercise_id] < 2
                    and exercise not in selected
                    and exercise.exercise_id not in previous_exercise_ids
                ]
            if not candidates:
                candidates = [
                    exercise for exercise in ordered
                    if usage[exercise.exercise_id] < 2
                    and exercise not in selected
                ]
            if not candidates:
                break
            candidates.sort(key=lambda exercise: (
                previous_categories[exercise.category or ""],
                usage[exercise.exercise_id],
                rank.get(exercise.exercise_code, len(rank)),
                exercise.exercise_id,
            ))
            choice = candidates[0]
            selected.append(choice)
            usage[choice.exercise_id] += 1
        schedule.append(selected)
        previous_categories = Counter(
            exercise.category or "" for exercise in selected
        )
        previous_exercise_ids = {
            exercise.exercise_id for exercise in selected
        }
    return schedule


def create_recommendation(db: Session, payload, replace_existing: bool = False) -> RoutineRecommendation:
    user = db.scalar(
        select(User)
        .options(selectinload(User.member_profile), selectinload(User.member_goals))
        .where(User.user_id == payload.user_id, User.is_active.is_(True))
    )
    if not user:
        raise ValueError("USER_NOT_FOUND")
    profile: MemberProfile | None = user.member_profile
    goal_row: MemberGoal | None = user.member_goals[0] if user.member_goals else None
    goal = normalize_goal(goal_row.goal_code if goal_row else None, goal_row.goal_name if goal_row else None)
    raw_level = (profile.exercise_level if profile else None) or "BEGINNER"
    level = raw_level if raw_level in {"BEGINNER", "INTERMEDIATE", "ADVANCED"} else "BEGINNER"
    days = payload.days_per_week or (profile.weekly_workout_days if profile else None) or 3
    preferred_days = payload.preferred_days
    if preferred_days is not None and payload.days_per_week is None:
        days = len(preferred_days)
    select_training_days(days, preferred_days, payload.variant)

    latest = None
    if replace_existing:
        latest = db.scalar(
            select(RoutineRecommendation)
            .options(selectinload(RoutineRecommendation.items))
            .where(
                RoutineRecommendation.user_id == payload.user_id,
                RoutineRecommendation.status == "RECOMMENDED",
            )
            .order_by(RoutineRecommendation.created_at.desc(), RoutineRecommendation.recommendation_id.desc())
            .with_for_update()
        )

    assignments = list(db.scalars(
        select(PtAssignment).where(
            PtAssignment.member_id == payload.user_id,
            PtAssignment.status.in_(("ASSIGNED", "IN_PROGRESS")),
            PtAssignment.exercise_id.is_not(None),
        ).order_by(PtAssignment.due_date.asc(), PtAssignment.assignment_id.asc())
    ).all())
    template = select_template(goal, normalize_level(level))
    assignment_exercises = {
        item.exercise_id: item for item in db.scalars(select(Exercise).where(
            Exercise.exercise_id.in_([assignment.exercise_id for assignment in assignments]),
            Exercise.is_active.is_(True),
        )).all()
    } if assignments else {}
    template_codes = {entry[0] for entry in template}
    for assignment in reversed(assignments):
        exercise = assignment_exercises.get(assignment.exercise_id)
        if exercise and exercise.exercise_code not in template_codes:
            template.insert(0, (
                exercise.exercise_code,
                assignment.target_sets or 3,
                assignment.target_reps or 10,
            ))
            template_codes.add(exercise.exercise_code)

    codes = [code for code, _, _ in template]
    exercises = list(db.scalars(select(Exercise).where(
        Exercise.is_active.is_(True)
    ).order_by(
        Exercise.category.asc(),
        Exercise.exercise_name.asc(),
        Exercise.exercise_id.asc(),
    )).all())
    if not exercises:
        raise ValueError("NO_EXERCISES")
    assignment_by_id = {assignment.exercise_id: assignment for assignment in assignments}
    preferred_codes = [
        exercise.exercise_code
        for assignment in assignments
        if (exercise := assignment_exercises.get(assignment.exercise_id))
    ]
    preferred_codes.extend(code for code in codes if code not in preferred_codes)
    template_settings = {
        code: (sets, reps) for code, sets, reps in template
    }
    completion_rate = _recent_plan_completion_rate(db, payload.user_id)
    per_day = daily_exercise_count(level, payload.workout_minutes, completion_rate)
    schedule = build_weekly_exercise_schedule(
        exercises, days, per_day, preferred_codes, goal, payload.variant
    )

    recommendation = RoutineRecommendation(
        user_id=payload.user_id,
        recommendation_date=korea_today(),
        goal=goal,
        level=level,
        days_per_week=days,
        workout_minutes=payload.workout_minutes,
    )
    db.add(recommendation)
    db.flush()
    dates = recommendation_dates(
        korea_today(), days, preferred_days, payload.variant
    )
    new_signature = tuple(
        (workout_date, exercise.exercise_id)
        for workout_date, daily_exercises in zip(dates, schedule)
        for exercise in daily_exercises
    )
    if latest is not None:
        latest_signature = tuple(
            (item.workout_date, item.exercise_id)
            for item in latest.items
        )
        if latest_signature == new_signature:
            raise ValueError("NO_ALTERNATIVE_RECOMMENDATION")
        latest.status = "REPLACED"
    sequence = 0
    history_cache: dict[int, ExerciseHistory] = {}
    for workout_date, daily_exercises in zip(dates, schedule):
        for exercise in daily_exercises:
            assignment = assignment_by_id.get(exercise.exercise_id)
            default_sets, default_reps = template_settings.get(
                exercise.exercise_code,
                (3 if level == "BEGINNER" else 4, 10),
            )
            sets = assignment.target_sets if assignment and assignment.target_sets else default_sets
            reps = assignment.target_reps if assignment and assignment.target_reps else default_reps
            history = history_cache.get(exercise.exercise_id)
            if history is None:
                history = get_recent_history(
                    db, payload.user_id, exercise.exercise_id
                )
                history_cache[exercise.exercise_id] = history
            adjusted = adjust_exercise(reps, history, exercise.exercise_name)
            sequence += 1
            db.add(RoutineRecommendationItem(
                recommendation_id=recommendation.recommendation_id,
                exercise_id=exercise.exercise_id,
                workout_date=workout_date,
                sequence_no=sequence,
                recommended_sets=sets,
                recommended_reps=adjusted.reps,
                difficulty=adjusted.difficulty,
                coaching_supported=is_coaching_supported(exercise.exercise_code),
                adjustment_type=adjusted.adjustment_type,
                recommendation_reason=adjusted.reason,
                previous_posture_score=history.posture_score,
                previous_completion_rate=history.completion_rate,
            ))
    db.flush()
    return recommendation
