from datetime import datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    DECIMAL,
    String,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.database import Base


class Exercise(Base):
    __tablename__ = "exercise"

    exercise_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="운동 종목 고유 번호",
    )

    exercise_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        unique=True,
        index=True,
        comment="운동 종목 코드",
    )

    exercise_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="운동 종목명",
    )

    calories_per_minute: Mapped[Decimal] = mapped_column(
        DECIMAL(5, 2),
        nullable=False,
        default=0,
        server_default="0",
        comment="분당 예상 소모 칼로리",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="사용 여부",
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