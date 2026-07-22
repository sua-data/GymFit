from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class PtFeedback(Base):
    __tablename__ = "pt_feedback"
    __table_args__ = (UniqueConstraint("assignment_id", name="uq_pt_feedback_assignment"),)

    feedback_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    assignment_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("pt_assignment.assignment_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    workout_record_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("workout_record.workout_record_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    trainer_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    member_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    assignment = relationship("PtAssignment")
    workout_record = relationship("WorkoutRecord")
    trainer = relationship("User", foreign_keys=[trainer_id])
    member = relationship("User", foreign_keys=[member_id])
