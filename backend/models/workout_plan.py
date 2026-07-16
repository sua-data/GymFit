from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.database import Base
from backend.models.exercise import Exercise
from backend.models.user_exercise import UserExercise


class WorkoutPlan(Base):
    __tablename__ = "workout_plan"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "exercise_id",
            "plan_date",
            name="uq_workout_plan_user_exercise_date",
        ),
        UniqueConstraint(
            "user_id",
            "user_exercise_id",
            "plan_date",
            name="uq_workout_plan_user_custom_date",
        ),
    )

    workout_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="운동 계획 고유 번호",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="회원 번호",
    )

    exercise_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "exercise.exercise_id",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
        index=True,
        comment="운동 종목 번호",
    )

    user_exercise_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "user_exercise.user_exercise_id",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
        index=True,
    )

    plan_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="운동 예정일",
    )

    set_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
        comment="계획 세트 수",
    )

    repetition_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="세트당 반복 횟수",
    )

    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="예상 운동 시간",
    )

    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="완료 여부",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="등록 일시",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="수정 일시",
    )

    exercise: Mapped[Exercise | None] = relationship()
    user_exercise: Mapped[UserExercise | None] = relationship()
