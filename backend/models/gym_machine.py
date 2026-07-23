from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database import Base


class GymMachine(Base):
    __tablename__ = "gym_machine"
    __table_args__ = (
        Index("ix_gym_machine_gym_active", "gym_id", "is_active"),
        Index("ix_gym_machine_gym_name", "gym_id", "machine_name"),
    )

    machine_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    gym_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("gym.gym_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=False,
    )
    machine_name: Mapped[str] = mapped_column(String(120), nullable=False)
    body_part: Mapped[str] = mapped_column(String(30), nullable=False)
    brand: Mapped[str | None] = mapped_column(String(100), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    usage_guide: Mapped[str | None] = mapped_column(Text, nullable=True)
    caution: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    image_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
