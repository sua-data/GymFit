from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Enum, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class PtSchedule(Base):
    __tablename__ = "pt_schedule"
    __table_args__ = (
        CheckConstraint("end_at > start_at", name="ck_pt_schedule_time_range"),
        Index("ix_pt_schedule_trainer_status_start", "trainer_id", "status", "start_at"),
        Index("ix_pt_schedule_member_status_start", "member_id", "status", "start_at"),
        Index("ix_pt_schedule_relationship_start", "trainer_member_id", "start_at"),
    )

    schedule_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trainer_member_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("trainer_member.trainer_member_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    trainer_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False
    )
    member_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False
    )
    start_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    end_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        Enum("SCHEDULED", "CANCELLED", "COMPLETED", native_enum=True),
        nullable=False,
        default="SCHEDULED",
        server_default="SCHEDULED",
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    trainer_member = relationship("TrainerMember")
    trainer = relationship("User", foreign_keys=[trainer_id])
    member = relationship("User", foreign_keys=[member_id])
