from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class RoutineRecommendation(Base):
    __tablename__ = "routine_recommendation"

    recommendation_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    recommendation_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    goal: Mapped[str] = mapped_column(String(50), nullable=False)
    level: Mapped[str] = mapped_column(String(30), nullable=False)
    days_per_week: Mapped[int] = mapped_column(Integer, nullable=False)
    workout_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    source_type: Mapped[str] = mapped_column(
        String(30), nullable=False, default="RULE_BASED", server_default="RULE_BASED"
    )
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="RECOMMENDED", server_default="RECOMMENDED"
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    items: Mapped[list["RoutineRecommendationItem"]] = relationship(
        back_populates="recommendation",
        cascade="all, delete-orphan",
        order_by="RoutineRecommendationItem.sequence_no",
    )


class RoutineRecommendationItem(Base):
    __tablename__ = "routine_recommendation_item"
    __table_args__ = (
        UniqueConstraint("recommendation_id", "sequence_no", name="uq_routine_recommendation_item_sequence"),
    )

    recommendation_item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    recommendation_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("routine_recommendation.recommendation_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
        index=True,
    )
    exercise_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("exercise.exercise_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=True
    )
    user_exercise_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user_exercise.user_exercise_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
    )
    workout_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_sets: Mapped[int] = mapped_column(Integer, nullable=False)
    recommended_reps: Mapped[int] = mapped_column(Integer, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(30), nullable=False)
    coaching_supported: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="0")
    adjustment_type: Mapped[str] = mapped_column(String(30), nullable=False)
    recommendation_reason: Mapped[str] = mapped_column(Text, nullable=False)
    previous_posture_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    previous_completion_rate: Mapped[Decimal | None] = mapped_column(Numeric(7, 4), nullable=True)

    recommendation: Mapped[RoutineRecommendation] = relationship(back_populates="items")

