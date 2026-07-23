from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, DateTime, DECIMAL, Enum, ForeignKey, Index, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class WorkoutRecordDetailItem(Base):
    __tablename__ = "workout_record_item"
    __table_args__ = (
        UniqueConstraint("record_id", "display_order", name="uq_workout_record_item_order"),
        Index("ix_workout_record_item_record", "record_id", "display_order"),
    )

    item_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    record_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workout_record.workout_record_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    exercise_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("exercise.exercise_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=True
    )
    user_exercise_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("user_exercise.user_exercise_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=True
    )
    exercise_name: Mapped[str] = mapped_column(String(100), nullable=False)
    weight_value: Mapped[Decimal | None] = mapped_column(DECIMAL(7, 2), nullable=True)
    weight_text: Mapped[str | None] = mapped_column(String(100), nullable=True)
    repetitions: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completed_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    rpe: Mapped[int | None] = mapped_column(Integer, nullable=True)
    workout_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    posture_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    record = relationship("WorkoutRecord", back_populates="items")
    media = relationship("WorkoutRecordMedia", back_populates="item", cascade="all, delete-orphan")


class WorkoutRecordMedia(Base):
    __tablename__ = "workout_record_media"
    __table_args__ = (Index("ix_workout_record_media_item", "item_id", "created_at"),)

    media_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    item_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workout_record_item.item_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False
    )
    media_type: Mapped[str] = mapped_column(Enum("VIDEO", "IMAGE", native_enum=True), nullable=False)
    media_url: Mapped[str] = mapped_column(String(500), nullable=False)
    thumbnail_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_path: Mapped[str] = mapped_column(String(1000), nullable=False)
    thumbnail_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())

    item = relationship("WorkoutRecordDetailItem", back_populates="media")
