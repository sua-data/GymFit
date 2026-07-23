from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.database import Base
from backend.models.exercise import Exercise


class WorkoutRecord(Base):
    __tablename__ = "workout_record"

    workout_record_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="운동 기록 고유 번호",
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

    exercise_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey(
            "exercise.exercise_id",
            ondelete="RESTRICT",
            onupdate="CASCADE",
        ),
        nullable=True,
        index=True,
        comment="운동 종목 번호",
    )

    record_type: Mapped[str] = mapped_column(
        Enum("WORKOUT", "PT", native_enum=True), nullable=False, default="WORKOUT", server_default="WORKOUT"
    )
    title: Mapped[str | None] = mapped_column(String(150), nullable=True)
    workout_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    workout_part: Mapped[str | None] = mapped_column(String(100), nullable=True)
    trainer_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.user_id", ondelete="SET NULL", onupdate="CASCADE"), nullable=True, index=True
    )
    pt_schedule_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("pt_schedule.schedule_id", ondelete="RESTRICT", onupdate="CASCADE"), nullable=True, unique=True
    )
    location: Mapped[str | None] = mapped_column(String(200), nullable=True)
    memo: Mapped[str | None] = mapped_column(Text, nullable=True)

    user_exercise_id: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("user_exercise.user_exercise_id", ondelete="RESTRICT", onupdate="CASCADE"),
        nullable=True,
        index=True,
    )

    record_source: Mapped[str] = mapped_column(
        String(50), nullable=False, default="COACHING", server_default="COACHING"
    )

    manual_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        index=True,
        comment="운동 시작 일시",
    )

    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="운동 완료 일시",
    )

    completed_sets: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="완료 세트 수",
    )

    repetition_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="전체 반복 횟수",
    )

    workout_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="운동 시간",
    )

    calories: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="소모 칼로리",
    )

    average_posture_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="운동 세션 평균 자세 점수",
    )

    best_posture_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="운동 세션 최고 자세 점수",
    )

    feedback_title: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="자세 피드백 제목",
    )

    feedback: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="자세 피드백 내용",
    )

    image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="분석 이미지 URL",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="기록 생성 일시",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    exercise: Mapped[Exercise] = relationship()
    user_exercise = relationship("UserExercise")
    trainer = relationship("User", foreign_keys=[trainer_id])
    pt_schedule = relationship("PtSchedule")
    items = relationship(
        "WorkoutRecordDetailItem", back_populates="record", cascade="all, delete-orphan", order_by="WorkoutRecordDetailItem.display_order"
    )
