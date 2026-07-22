from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
)

from backend.database import Base


class Notification(Base):
    __tablename__ = "notification"

    notification_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="알림 고유 번호",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        index=True,
        comment="회원 번호",
    )

    title: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="알림 제목",
    )

    message: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="알림 내용",
    )

    is_read: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
        comment="읽음 여부",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="알림 생성 일시",
    )

    notification_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    target_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    reference_id: Mapped[int | None] = mapped_column(
        BigInteger,
        nullable=True,
    )
