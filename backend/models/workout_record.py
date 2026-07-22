from datetime import datetime

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
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

    exercise: Mapped[Exercise] = relationship()
    user_exercise = relationship("UserExercise")
