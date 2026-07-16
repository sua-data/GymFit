from backend.models.user import (
    EmailVerification,
    MemberGoal,
    MemberProfile,
    TrainerCertification,
    TrainerProfile,
    TrainerSpecialty,
    User,
    UserAgreement,
)

from backend.models.exercise import Exercise
from backend.models.user_exercise import UserExercise
from backend.models.notification import Notification
from backend.models.workout_plan import WorkoutPlan
from backend.models.workout_plan_set import WorkoutPlanSet
from backend.models.workout_record import WorkoutRecord


__all__ = [
    "User",
    "MemberProfile",
    "MemberGoal",
    "TrainerProfile",
    "TrainerSpecialty",
    "TrainerCertification",
    "UserAgreement",
    "EmailVerification",
    "Exercise",
    "UserExercise",
    "Notification",
    "WorkoutPlan",
    "WorkoutPlanSet",
    "WorkoutRecord",
]
