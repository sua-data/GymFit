from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, Date, DateTime, Enum, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class PtAssignment(Base):
    __tablename__ = "pt_assignment"
    __table_args__ = (
        Index("ix_pt_assignment_trainer_status_assigned", "trainer_id", "status", "assigned_date"),
        Index("ix_pt_assignment_member_status_due", "member_id", "status", "due_date"),
        Index("ix_pt_assignment_trainer_member", "trainer_member_id"),
        UniqueConstraint(
            "workout_record_id",
            name="uq_pt_assignment_workout_record",
        ),
        CheckConstraint(
            "weight_kg IS NULL OR weight_kg > 0",
            name="chk_pt_assignment_weight_kg",
        ),
    )

    assignment_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trainer_member_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("trainer_member.trainer_member_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    trainer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    member_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    exercise_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("exercise.exercise_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=True)
    user_exercise_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("user_exercise.user_exercise_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=True)
    title: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    assigned_date: Mapped[date] = mapped_column(Date, nullable=False)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    target_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    target_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weight_kg: Mapped[Decimal | None] = mapped_column(
        Numeric(6, 2),
        nullable=True,
        comment="PT 숙제에 지정한 사용 중량(kg)",
    )
    status: Mapped[str] = mapped_column(Enum("ASSIGNED", "IN_PROGRESS", "COMPLETED", "CANCELLED", native_enum=True), nullable=False, default="ASSIGNED", server_default="ASSIGNED")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    workout_record_id: Mapped[int | None] = mapped_column(BigInteger, ForeignKey("workout_record.workout_record_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    trainer_member = relationship("TrainerMember")
    trainer = relationship("User", foreign_keys=[trainer_id])
    member = relationship("User", foreign_keys=[member_id])
    exercise = relationship("Exercise")
    user_exercise = relationship("UserExercise")
    workout_record = relationship("WorkoutRecord")

    workout_plan = relationship(
        "WorkoutPlan",
        back_populates="pt_assignment",
        uselist=False,
    )
