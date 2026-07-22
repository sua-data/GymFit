from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, DateTime, DECIMAL, ForeignKey, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database import Base


class Gym(Base):
    __tablename__ = "gym"
    __table_args__ = (
        UniqueConstraint("provider", "external_place_id", name="uq_gym_provider_external_place"),
    )

    gym_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(20), nullable=False)
    external_place_id: Mapped[str] = mapped_column(String(100), nullable=False)
    gym_name: Mapped[str] = mapped_column(String(150), nullable=False)
    road_address: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255), nullable=True)
    latitude: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 7), nullable=True)
    longitude: Mapped[Decimal | None] = mapped_column(DECIMAL(10, 7), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="1")
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())


class UserGym(Base):
    __tablename__ = "user_gym"
    __table_args__ = (UniqueConstraint("user_id", name="uq_user_gym_user"),)

    user_gym_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.user_id", ondelete="CASCADE", onupdate="CASCADE"), nullable=False)
    gym_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("gym.gym_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    gym: Mapped[Gym] = relationship()
