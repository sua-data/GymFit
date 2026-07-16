from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    DECIMAL,
    ForeignKey,
    Integer,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class WorkoutPlanSet(Base):
    __tablename__ = "workout_plan_set"
    __table_args__ = (
        UniqueConstraint(
            "workout_plan_id",
            "set_order",
            name="uq_workout_plan_set_plan_order",
        ),
    )

    workout_plan_set_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
    )
    workout_plan_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "workout_plan.workout_plan_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        index=True,
    )
    set_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    repetition_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    duration_seconds: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )
    weight_kg: Mapped[Decimal | None] = mapped_column(
        DECIMAL(7, 2),
        nullable=True,
    )
    is_completed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    workout_plan = relationship(
        "WorkoutPlan",
        back_populates="sets",
    )
