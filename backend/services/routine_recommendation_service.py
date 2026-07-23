from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta

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


def _recommendation_dates(today: date, days: int) -> list[date]:
    result = []
    cursor = today
    while len(result) < days:
        if cursor.weekday() < 6:
            result.append(cursor)
        cursor += timedelta(days=1)
    return result


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
    level = normalize_level(profile.exercise_level if profile else None)
    days = payload.days_per_week or (profile.weekly_workout_days if profile else None) or 3

    if replace_existing:
        latest = db.scalar(
            select(RoutineRecommendation)
            .where(
                RoutineRecommendation.user_id == payload.user_id,
                RoutineRecommendation.status == "RECOMMENDED",
            )
            .order_by(RoutineRecommendation.created_at.desc(), RoutineRecommendation.recommendation_id.desc())
            .with_for_update()
        )
        if latest:
            latest.status = "REPLACED"

    assignments = list(db.scalars(
        select(PtAssignment).where(
            PtAssignment.member_id == payload.user_id,
            PtAssignment.status.in_(("ASSIGNED", "IN_PROGRESS")),
            PtAssignment.exercise_id.is_not(None),
        ).order_by(PtAssignment.due_date.asc(), PtAssignment.assignment_id.asc())
    ).all())
    template = select_template(goal, level)
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
        Exercise.exercise_code.in_(codes), Exercise.is_active.is_(True)
    )).all())
    exercise_by_code = {item.exercise_code: item for item in exercises}
    priority_ids = [item.exercise_id for item in assignments]
    available = [entry for entry in template if entry[0] in exercise_by_code]
    history_by_code = {
        entry[0]: get_recent_history(db, payload.user_id, exercise_by_code[entry[0]].exercise_id)
        for entry in available
    }
    ordered = sorted(available, key=lambda entry: (
        exercise_by_code[entry[0]].exercise_id not in priority_ids,
        not (
            history_by_code[entry[0]].posture_score is not None
            and history_by_code[entry[0]].posture_score < 70
            and is_coaching_supported(entry[0])
        ),
        codes.index(entry[0]),
    ))
    if not ordered:
        raise ValueError("NO_EXERCISES")

    recommendation = RoutineRecommendation(
        user_id=payload.user_id,
        recommendation_date=date.today(),
        goal=goal,
        level=level,
        days_per_week=days,
        workout_minutes=payload.workout_minutes,
    )
    db.add(recommendation)
    db.flush()
    dates = _recommendation_dates(date.today(), days)
    per_day = max(1, min(len(ordered), payload.workout_minutes // 10))
    sequence = 0
    for index, (code, sets, reps) in enumerate(ordered[: days * per_day]):
        exercise = exercise_by_code[code]
        history = history_by_code[code]
        adjusted = adjust_exercise(reps, history, exercise.exercise_name)
        sequence += 1
        db.add(RoutineRecommendationItem(
            recommendation_id=recommendation.recommendation_id,
            exercise_id=exercise.exercise_id,
            workout_date=dates[index % len(dates)],
            sequence_no=sequence,
            recommended_sets=sets,
            recommended_reps=adjusted.reps,
            difficulty=adjusted.difficulty,
            coaching_supported=is_coaching_supported(code),
            adjustment_type=adjusted.adjustment_type,
            recommendation_reason=adjusted.reason,
            previous_posture_score=history.posture_score,
            previous_completion_rate=history.completion_rate,
        ))
    db.flush()
    return recommendation
