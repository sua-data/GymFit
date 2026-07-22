from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Index, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base

if TYPE_CHECKING:
    from backend.models.user import User


class TrainerMember(Base):
    __tablename__ = "trainer_member"
    __table_args__ = (
        Index("ix_trainer_member_trainer_status", "trainer_id", "status"),
        Index("ix_trainer_member_member_status", "member_id", "status"),
        Index("ix_trainer_member_pair_status", "trainer_id", "member_id", "status"),
    )

    trainer_member_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    trainer_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    member_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        Enum("PENDING", "ACTIVE", "ENDED", native_enum=True),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
    )
    started_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    ended_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    trainer: Mapped["User"] = relationship(
        foreign_keys=[trainer_id],
        back_populates="trained_member_relationships",
    )
    member: Mapped["User"] = relationship(
        foreign_keys=[member_id],
        back_populates="trainer_relationships",
    )
