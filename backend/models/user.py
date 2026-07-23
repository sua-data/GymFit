from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    DECIMAL,
    Enum,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from backend.database import Base


# =========================================================
# 회원 공통 정보
# =========================================================

class User(Base):
    __tablename__ = "users"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="회원 고유 번호",
    )

    account_type: Mapped[str] = mapped_column(
        Enum(
            "MEMBER",
            "TRAINER",
            "ADMIN",
            native_enum=True,
        ),
        nullable=False,
        comment="계정 유형",
    )

    name: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="회원 이름",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
        index=True,
        comment="로그인 이메일",
    )

    login_provider: Mapped[str] = mapped_column(
        Enum(
            "LOCAL",
            "GOOGLE",
            native_enum=True,
        ),
        nullable=False,
        default="LOCAL",
        server_default="LOCAL",
        comment="로그인 제공자",
    )

    google_sub: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
        comment="Google 계정 고유 식별자",
    )

    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="암호화된 비밀번호, 소셜 로그인 계정은 NULL",
    )

    gender: Mapped[str] = mapped_column(
        Enum(
            "MALE",
            "FEMALE",
            "NONE",
            native_enum=True,
        ),
        nullable=False,
        default="NONE",
        server_default="NONE",
        comment="성별",
    )

    birth_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="생년월일",
    )

    is_email_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="이메일 인증 여부",
    )

    must_change_password: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="비밀번호 변경 필요 여부",
    )

    temporary_password_expires_at: Mapped[
        datetime | None
    ] = mapped_column(
        DateTime,
        nullable=True,
        comment="임시 비밀번호 만료 일시",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
        comment="계정 활성화 여부",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="마지막 로그인 일시",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="회원가입 일시",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="회원 정보 수정 일시",
    )

    # 일반 회원 프로필
    member_profile: Mapped[
        MemberProfile | None
    ] = relationship(
        back_populates="user",
        foreign_keys="MemberProfile.user_id",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # 일반 회원 운동 목표
    member_goals: Mapped[list[MemberGoal]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 트레이너 프로필
    trainer_profile: Mapped[
        TrainerProfile | None
    ] = relationship(
        back_populates="user",
        foreign_keys="TrainerProfile.user_id",
        cascade="all, delete-orphan",
        uselist=False,
    )

    # 트레이너 전문 분야
    trainer_specialties: Mapped[
        list[TrainerSpecialty]
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 트레이너 자격증
    trainer_certifications: Mapped[
        list[TrainerCertification]
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # 약관 동의
    agreement: Mapped[
        "UserAgreement | None"
    ] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False,
    )

    trained_member_relationships: Mapped[list["TrainerMember"]] = relationship(
        foreign_keys="TrainerMember.trainer_id",
        back_populates="trainer",
        cascade="all, delete-orphan",
    )

    trainer_relationships: Mapped[list["TrainerMember"]] = relationship(
        foreign_keys="TrainerMember.member_id",
        back_populates="member",
        cascade="all, delete-orphan",
    )


# =========================================================
# 일반 회원 상세 프로필
# =========================================================

class MemberProfile(Base):
    __tablename__ = "member_profile"

    member_profile_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="일반 회원 프로필 고유 번호",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        unique=True,
        comment="회원 번호",
    )

    height_cm: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2),
        nullable=True,
        comment="키(cm)",
    )

    weight_kg: Mapped[Decimal | None] = mapped_column(
        DECIMAL(5, 2),
        nullable=True,
        comment="몸무게(kg)",
    )

    exercise_level: Mapped[str | None] = mapped_column(
        Enum(
            "BEGINNER",
            "INTERMEDIATE",
            "ADVANCED",
            native_enum=True,
        ),
        nullable=True,
        comment="운동 수준",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="프로필 생성 일시",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="프로필 수정 일시",
    )

    user: Mapped[User] = relationship(
        back_populates="member_profile",
        foreign_keys=[user_id],
    )

    weekly_workout_days: Mapped[int | None] = mapped_column(
        SmallInteger,
        nullable=True,
        comment="주간 목표 운동 일수",
    )


# =========================================================
# 일반 회원 운동 목표
# =========================================================

class MemberGoal(Base):
    __tablename__ = "member_goal"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "goal_code",
            name="uq_member_goal",
        ),
    )

    member_goal_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="운동 목표 고유 번호",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        comment="회원 번호",
    )

    goal_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="운동 목표 코드",
    )

    goal_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="운동 목표명",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="운동 목표 등록 일시",
    )

    user: Mapped[User] = relationship(
        back_populates="member_goals"
    )


# =========================================================
# 트레이너 상세 프로필
# =========================================================

class TrainerProfile(Base):
    __tablename__ = "trainer_profile"

    trainer_profile_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="트레이너 프로필 고유 번호",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        unique=True,
        comment="회원 번호",
    )

    gym_name: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="소속 헬스장 이름",
    )

    career_years: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="트레이너 경력 연수",
    )

    introduction: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
        comment="트레이너 자기소개",
    )

    approval_status: Mapped[str] = mapped_column(
        Enum(
            "PENDING",
            "APPROVED",
            "REJECTED",
            native_enum=True,
        ),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        comment="트레이너 승인 상태",
    )

    rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="트레이너 승인 거절 사유",
    )

    reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )

    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    employment_status: Mapped[str] = mapped_column(
        Enum("NONE", "PENDING", "APPROVED", "REJECTED", native_enum=True),
        nullable=False,
        default="NONE",
        server_default="NONE",
        comment="헬스장 소속 승인 상태",
    )

    employment_evidence_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    employment_storage_path: Mapped[str | None] = mapped_column(
        String(1000),
        nullable=True,
    )

    employment_original_name: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    employment_reviewed_by: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("users.user_id", ondelete="SET NULL", onupdate="CASCADE"),
        nullable=True,
    )

    employment_reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
    )

    employment_rejection_reason: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="프로필 생성 일시",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="프로필 수정 일시",
    )

    user: Mapped[User] = relationship(
        back_populates="trainer_profile",
        foreign_keys=[user_id],
    )


# =========================================================
# 트레이너 전문 분야
# =========================================================

class TrainerSpecialty(Base):
    __tablename__ = "trainer_specialty"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "specialty_code",
            name="uq_trainer_specialty",
        ),
    )

    trainer_specialty_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="전문 분야 고유 번호",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        comment="트레이너 회원 번호",
    )

    specialty_code: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="전문 분야 코드",
    )

    specialty_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="전문 분야명",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="전문 분야 등록 일시",
    )

    user: Mapped[User] = relationship(
        back_populates="trainer_specialties"
    )


# =========================================================
# 트레이너 자격증
# =========================================================

class TrainerCertification(Base):
    __tablename__ = "trainer_certification"

    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "certification_name",
            name="uq_trainer_certification",
        ),
    )

    trainer_certification_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="자격증 고유 번호",
    )

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        nullable=False,
        comment="트레이너 회원 번호",
    )

    certification_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
        comment="자격증 이름",
    )

    issuer: Mapped[str | None] = mapped_column(
        String(150),
        nullable=True,
        comment="자격증 발급 기관",
    )

    acquired_date: Mapped[date | None] = mapped_column(
        Date,
        nullable=True,
        comment="자격증 취득일",
    )

    certification_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    evidence_image_url: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="자격증 증빙 이미지 URL",
    )

    evidence_storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    evidence_original_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="자격증 등록 일시",
    )

    user: Mapped[User] = relationship(
        back_populates="trainer_certifications"
    )


# =========================================================
# 회원 약관 동의
# 사용자당 한 행
# =========================================================

class UserAgreement(Base):
    __tablename__ = "user_agreement"

    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey(
            "users.user_id",
            ondelete="CASCADE",
            onupdate="CASCADE",
        ),
        primary_key=True,
        comment="회원 번호",
    )

    terms_agreed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="이용약관 동의 여부",
    )

    privacy_agreed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="개인정보 수집 및 이용 동의 여부",
    )

    marketing_agreed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="마케팅 정보 수신 동의 여부",
    )

    trainer_policy_agreed: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="트레이너 운영정책 동의 여부",
    )

    agreed_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="필수 약관 동의 일시",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="약관 정보 생성 일시",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
        comment="약관 정보 수정 일시",
    )

    user: Mapped["User"] = relationship(
        back_populates="agreement"
    )


# =========================================================
# 이메일 인증번호
# =========================================================

class EmailVerification(Base):
    __tablename__ = "email_verification"

    email_verification_id: Mapped[int] = mapped_column(
        BigInteger,
        primary_key=True,
        autoincrement=True,
        comment="이메일 인증 고유 번호",
    )

    email: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="인증 대상 이메일",
    )

    verification_code_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="암호화된 인증번호",
    )

    purpose: Mapped[str] = mapped_column(
        Enum(
            "SIGNUP",
            "PASSWORD_RESET",
            native_enum=True,
        ),
        nullable=False,
        default="SIGNUP",
        server_default="SIGNUP",
        comment="인증 목적",
    )

    is_verified: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        comment="인증 완료 여부",
    )

    attempt_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
        comment="인증번호 확인 시도 횟수",
    )

    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        comment="인증번호 만료 일시",
    )

    verified_at: Mapped[datetime | None] = mapped_column(
        DateTime,
        nullable=True,
        comment="인증 완료 일시",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        comment="인증번호 생성 일시",
    )
