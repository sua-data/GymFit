from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import TrainerMember, User


JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256").strip()
if JWT_ALGORITHM != "HS256":
    raise RuntimeError("JWT_ALGORITHM은 HS256만 지원합니다.")

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "").strip()
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60")
)
bearer_scheme = HTTPBearer(auto_error=False)


def _secret() -> str:
    if len(JWT_SECRET_KEY) < 32:
        raise RuntimeError("JWT_SECRET_KEY는 32자 이상의 안전한 값이어야 합니다.")
    return JWT_SECRET_KEY


def create_access_token(user: User, *, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires_at = now + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return jwt.encode(
        {
            "sub": str(user.user_id),
            "account_type": user.account_type,
            "iat": now,
            "exp": expires_at,
            "type": "access",
        },
        _secret(),
        algorithm=JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            _secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat", "type"]},
        )
    except ExpiredSignatureError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="인증 토큰이 만료되었습니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except InvalidTokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="유효하지 않은 인증 토큰입니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="로그인이 필요합니다.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(credentials.credentials)
    try:
        user_id = int(payload["sub"])
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=401, detail="유효하지 않은 인증 토큰입니다.") from exc
    user = db.scalar(select(User).where(User.user_id == user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="사용자를 찾을 수 없습니다.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="비활성화된 계정입니다.")
    if payload.get("account_type") != user.account_type:
        raise HTTPException(status_code=401, detail="계정 권한 정보가 변경되었습니다. 다시 로그인해 주세요.")
    return user


get_current_active_user = get_current_user


def require_account_type(*allowed: str):
    normalized = {value.upper() for value in allowed}

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.account_type not in normalized:
            raise HTTPException(status_code=403, detail="접근 권한이 없습니다.")
        return user

    return dependency


def require_trainer(user: User = Depends(get_current_user)) -> User:
    if user.account_type != "TRAINER":
        raise HTTPException(status_code=403, detail="트레이너 계정만 접근할 수 있습니다.")
    return user


def require_approved_trainer(user: User = Depends(get_current_user)) -> User:
    require_trainer(user)
    if (
        user.trainer_profile is None
        or user.trainer_profile.approval_status != "APPROVED"
    ):
        raise HTTPException(
            status_code=403,
            detail="자격 승인이 완료된 트레이너만 접근할 수 있습니다.",
        )
    return user


def require_employed_trainer(user: User = Depends(get_current_user)) -> User:
    require_approved_trainer(user)
    if user.trainer_profile.employment_status != "APPROVED":
        raise HTTPException(
            status_code=403,
            detail="소속 승인이 완료된 트레이너만 접근할 수 있습니다.",
        )
    return user


def require_active_member_relation(
    db: Session,
    *,
    trainer: User,
    member_id: int,
    lock: bool = False,
) -> TrainerMember:
    require_employed_trainer(trainer)
    statement = select(TrainerMember).where(
        TrainerMember.trainer_id == trainer.user_id,
        TrainerMember.member_id == member_id,
        TrainerMember.status == "ACTIVE",
    )
    if lock:
        statement = statement.with_for_update()
    relationship = db.scalar(statement)
    if relationship is None:
        raise HTTPException(status_code=403, detail="활성 담당 회원 관계가 필요합니다.")
    return relationship


def enforce_self(current_user: User, requested_user_id: int) -> None:
    if current_user.user_id != requested_user_id:
        raise HTTPException(status_code=403, detail="다른 사용자의 데이터에는 접근할 수 없습니다.")


def require_active_trainer_member(
    db: Session, *, trainer_id: int, member_id: int
) -> TrainerMember:
    relationship = db.scalar(
        select(TrainerMember).where(
            TrainerMember.trainer_id == trainer_id,
            TrainerMember.member_id == member_id,
            TrainerMember.status == "ACTIVE",
        )
    )
    if relationship is None:
        raise HTTPException(status_code=403, detail="담당 회원 관계가 필요합니다.")
    return relationship
