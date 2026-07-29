import asyncio
import os
import secrets

from datetime import (
    datetime,
    timedelta,
    timezone
)
from pathlib import Path

import requests

from dotenv import load_dotenv
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status
)
from google.auth.exceptions import GoogleAuthError
from google.auth.transport.requests import (
    Request as GoogleRequest
)
from google.oauth2 import id_token
from pydantic import (
    BaseModel,
    EmailStr
)
from sqlalchemy import (
    or_,
    select
)
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import (
    UserGym,
    MemberGoal,
    MemberProfile,
    TrainerCertification,
    TrainerProfile,
    TrainerSpecialty,
    User,
    UserAgreement
)
from backend.services.gym_service import select_or_create_gym
from backend.services.pt_service import (
    get_pending_pt_request_count,
    has_active_trainer,
)
from backend.services.notification_service import create_welcome_notification
from backend.schemas import (
    GoogleCodeLoginRequest,
    GoogleCodeLoginResponse,
    GoogleMemberSignupRequest,
    GoogleTrainerSignupRequest,
    LoginRequest,
    LoginResponse,
    MemberSignupRequest,
    SignupResponse,
    TrainerSignupRequest
)
from backend.services.email_service import (
    generate_verification_code,
    send_temporary_password_email,
    send_verification_email
)
from backend.services.password_service import (
    hash_password,
    verify_password
)
from backend.security import create_access_token, get_current_user


# =========================================================
# 환경 변수
# =========================================================

BASE_DIR = (
    Path(__file__)
    .resolve()
    .parent
    .parent
    .parent
)

load_dotenv(
    BASE_DIR / ".env"
)

GOOGLE_CLIENT_ID = os.getenv(
    "GOOGLE_CLIENT_ID"
)

GOOGLE_CLIENT_SECRET = os.getenv(
    "GOOGLE_CLIENT_SECRET"
)

GOOGLE_TOKEN_URL = (
    "https://oauth2.googleapis.com/token"
)


# =========================================================
# Router
# =========================================================

router = APIRouter(
    prefix="/api/auth",
    tags=["인증"],
)


# =========================================================
# 개발 단계 임시 저장소
# 서버 재시작 시 초기화됨
# =========================================================

verification_store: dict[
    str,
    dict,
] = {}

google_signup_store: dict[
    str,
    dict,
] = {}


VERIFICATION_EXPIRE_MINUTES = 3

GOOGLE_SIGNUP_EXPIRE_MINUTES = 15


# =========================================================
# 이메일 인증 요청 스키마
# =========================================================

class SendVerificationRequest(BaseModel):
    email: EmailStr

class TemporaryPasswordRequest(BaseModel):
    email: EmailStr

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    code: str


# =========================================================
# 공통 함수
# =========================================================

def normalize_email(
    email: str,
) -> str:
    return email.strip().lower()


def utc_now_naive() -> datetime:
    return datetime.now(
        timezone.utc
    ).replace(
        tzinfo=None
    )


def utc_now_aware() -> datetime:
    return datetime.now(
        timezone.utc
    )


def check_email_verified(
    email: str,
) -> None:
    verification_data = (
        verification_store.get(
            email
        )
    )

    if not verification_data:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "이메일 인증을 먼저 "
                "완료해 주세요."
            ),
        )

    if not verification_data.get(
        "verified"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "이메일 인증을 완료해 주세요."
            ),
        )


def check_required_agreements(
    terms: bool,
    privacy: bool,
    trainer_policy: bool = True,
) -> None:
    if not terms or not privacy:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "필수 약관에 동의해 주세요."
            ),
        )

    if not trainer_policy:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "트레이너 운영정책에 "
                "동의해 주세요."
            ),
        )


MEMBER_GOAL_NAMES = {
    "WEIGHT_LOSS": "체중 감량",
    "MUSCLE_GAIN": "근력 증가",
    "BODY_SHAPE": "체형 관리",
    "HEALTH": "건강 관리",
}


def normalize_member_goal(goal_value: str) -> tuple[str, str]:
    code = goal_value.strip().upper()
    if code not in MEMBER_GOAL_NAMES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="지원하지 않는 운동 목표입니다.",
        )
    return code, MEMBER_GOAL_NAMES[code]


def specialty_code_from_name(
    specialty_name: str,
) -> str:
    specialty_map = {
        "다이어트": "DIET",
        "근력 향상": "MUSCLE_GAIN",
        "재활 운동": "REHABILITATION",
        "체형 교정": "BODY_CORRECTION",
        "기능성 운동": (
            "FUNCTIONAL_TRAINING"
        ),
        "바디프로필": "BODY_PROFILE",
        "컨디셔닝": "CONDITIONING",
    }

    cleaned_name = (
        specialty_name.strip()
    )

    return specialty_map.get(
        cleaned_name,
        cleaned_name
        .upper()
        .replace(
            " ",
            "_",
        ),
    )


def add_user_agreement(
    db: Session,
    user_id: int,
    terms: bool,
    privacy: bool,
    marketing: bool,
    trainer_policy: bool = False,
) -> None:
    agreement = UserAgreement(
        user_id=user_id,
        terms_agreed=terms,
        privacy_agreed=privacy,
        marketing_agreed=marketing,
        trainer_policy_agreed=(
            trainer_policy
        ),
        agreed_at=(
            utc_now_naive()
            if terms and privacy
            else None
        ),
    )

    db.add(agreement)

def generate_temporary_password(
    length: int = 10,
) -> str:
    characters = (
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "abcdefghijkmnopqrstuvwxyz"
        "23456789"
        "!@#$"
    )

    return "".join(
        secrets.choice(characters)
        for _ in range(length)
    )

# =========================================================
# Google 설정 확인
# =========================================================

def check_google_config() -> None:
    if (
        not GOOGLE_CLIENT_ID
        or not GOOGLE_CLIENT_SECRET
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Google 로그인 설정이 없습니다."
            ),
        )


# =========================================================
# Google Authorization Code 교환
# =========================================================

def exchange_google_code(
    code: str,
) -> dict:
    check_google_config()

    try:
        response = requests.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": (
                    GOOGLE_CLIENT_ID
                ),
                "client_secret": (
                    GOOGLE_CLIENT_SECRET
                ),
                "redirect_uri": (
                    "postmessage"
                ),
                "grant_type": (
                    "authorization_code"
                ),
            },
            timeout=10,
        )

    except requests.RequestException as error:
        print(
            "Google 토큰 요청 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Google 인증 서버에 "
                "연결하지 못했습니다."
            ),
        ) from error

    try:
        token_response = (
            response.json()
        )

    except ValueError as error:
        print(
            "Google 토큰 응답 파싱 실패:",
            response.text,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_502_BAD_GATEWAY
            ),
            detail=(
                "Google 인증 응답을 "
                "처리하지 못했습니다."
            ),
        ) from error

    if not response.ok:
        print(
            "Google 토큰 교환 실패:",
            token_response,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Google 인증 코드가 "
                "유효하지 않거나 만료되었습니다."
            ),
        )

    google_id_token = (
        token_response.get(
            "id_token"
        )
    )

    if not google_id_token:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Google 사용자 정보를 "
                "가져오지 못했습니다."
            ),
        )

    return token_response


# =========================================================
# Google ID 토큰 검증
# =========================================================

def verify_google_id_token(
    google_id_token: str,
) -> dict:
    check_google_config()

    try:
        token_data = (
            id_token
            .verify_oauth2_token(
                google_id_token,
                GoogleRequest(),
                GOOGLE_CLIENT_ID,
            )
        )

    except (
        ValueError,
        GoogleAuthError,
    ) as error:
        print(
            "Google ID 토큰 검증 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "유효하지 않은 "
                "Google 로그인 정보입니다."
            ),
        ) from error

    google_sub = token_data.get(
        "sub"
    )

    email = token_data.get(
        "email"
    )

    name = token_data.get(
        "name"
    )

    email_verified = token_data.get(
        "email_verified",
        False,
    )

    if not google_sub or not email:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Google 계정 정보를 "
                "가져올 수 없습니다."
            ),
        )

    if not email_verified:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "인증되지 않은 "
                "Google 이메일입니다."
            ),
        )

    normalized_email = normalize_email(
        str(email)
    )

    display_name = (
        name.strip()
        if (
            isinstance(
                name,
                str,
            )
            and name.strip()
        )
        else normalized_email.split(
            "@"
        )[0]
    )

    return {
        "google_sub": str(
            google_sub
        ),
        "email": normalized_email,
        "name": display_name,
    }


# =========================================================
# Google 신규 가입 토큰 발급
# =========================================================

def create_google_signup_token(
    google_data: dict,
) -> str:
    signup_token = (
        secrets.token_urlsafe(32)
    )

    expires_at = (
        utc_now_aware()
        + timedelta(
            minutes=(
                GOOGLE_SIGNUP_EXPIRE_MINUTES
            )
        )
    )

    google_signup_store[
        signup_token
    ] = {
        "google_sub": (
            google_data["google_sub"]
        ),
        "email": (
            google_data["email"]
        ),
        "name": (
            google_data["name"]
        ),
        "expires_at": expires_at,
    }

    return signup_token


# =========================================================
# Google 신규 가입 토큰 확인
# =========================================================

def get_google_signup_data(
    signup_token: str,
) -> dict:
    signup_data = (
        google_signup_store.get(
            signup_token
        )
    )

    if not signup_data:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Google 가입 정보가 "
                "없거나 만료되었습니다. "
                "다시 로그인해 주세요."
            ),
        )

    expires_at = signup_data.get(
        "expires_at"
    )

    if (
        not expires_at
        or utc_now_aware() > expires_at
    ):
        google_signup_store.pop(
            signup_token,
            None,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "Google 가입 정보가 "
                "만료되었습니다. "
                "다시 로그인해 주세요."
            ),
        )

    return signup_data


# =========================================================
# Google 가입 토큰 삭제
# =========================================================

def remove_google_signup_token(
    signup_token: str,
) -> None:
    google_signup_store.pop(
        signup_token,
        None,
    )


# =========================================================
# 이메일 인증번호 발송
# =========================================================

@router.post(
    "/email/send-code"
)
async def send_email_verification_code(
    request: SendVerificationRequest,
    db: Session = Depends(get_db),
):
    email = normalize_email(
        str(request.email)
    )

    existing_user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "이미 가입된 이메일입니다."
            ),
        )

    verification_code = (
        generate_verification_code()
    )

    expires_at = (
        utc_now_aware()
        + timedelta(
            minutes=(
                VERIFICATION_EXPIRE_MINUTES
            )
        )
    )

    try:
        await asyncio.to_thread(
            send_verification_email,
            email,
            verification_code,
        )

    except Exception as error:
        print(
            "이메일 전송 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "인증메일 전송에 실패했습니다."
            ),
        ) from error

    verification_store[email] = {
        "code": verification_code,
        "expires_at": expires_at,
        "verified": False,
        "attempt_count": 0,
    }

    return {
        "message": (
            "인증번호가 이메일로 "
            "전송되었습니다."
        ),
        "expires_in": (
            VERIFICATION_EXPIRE_MINUTES
            * 60
        ),
    }


# =========================================================
# 이메일 인증번호 확인
# =========================================================

@router.post(
    "/email/verify-code"
)
def verify_email_code(
    request: VerifyEmailRequest,
):
    email = normalize_email(
        str(request.email)
    )

    code = request.code.strip()

    verification_data = (
        verification_store.get(
            email
        )
    )

    if not verification_data:
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "인증번호를 먼저 "
                "발급해 주세요."
            ),
        )

    if (
        utc_now_aware()
        > verification_data[
            "expires_at"
        ]
    ):
        verification_store.pop(
            email,
            None,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "인증번호가 만료되었습니다. "
                "다시 발급해 주세요."
            ),
        )

    verification_data[
        "attempt_count"
    ] += 1

    if (
        verification_data[
            "attempt_count"
        ] > 5
    ):
        verification_store.pop(
            email,
            None,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "인증번호 입력 횟수를 "
                "초과했습니다. "
                "다시 발급해 주세요."
            ),
        )

    if (
        code
        != verification_data["code"]
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "인증번호가 일치하지 않습니다."
            ),
        )

    verification_data[
        "verified"
    ] = True

    return {
        "message": (
            "이메일 인증이 완료되었습니다."
        ),
        "verified": True,
    }


# =========================================================
# 일반 회원가입
# =========================================================

@router.post(
    "/signup/member",
    response_model=SignupResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def signup_member(
    request: MemberSignupRequest,
    db: Session = Depends(get_db),
):
    email = normalize_email(
        str(request.email)
    )

    check_email_verified(
        email
    )

    check_required_agreements(
        terms=(
            request.agreements.terms
        ),
        privacy=(
            request.agreements.privacy
        ),
    )

    existing_user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "이미 가입된 이메일입니다."
            ),
        )

    try:
        user = User(
            account_type="MEMBER",
            name=request.name.strip(),
            email=email,
            login_provider="LOCAL",
            google_sub=None,
            password_hash=(
                hash_password(
                    request.password
                )
            ),
            gender=(
                request.gender
                or "NONE"
            ),
            birth_date=(
                request.birth_date
            ),
            is_email_verified=True,
            is_active=True,
        )

        db.add(user)
        db.flush()

        member_profile = (
            MemberProfile(
                user_id=user.user_id,
                height_cm=(
                    request.height_cm
                ),
                weight_kg=(
                    request.weight_kg
                ),
                exercise_level=(
                    request.exercise_level
                ),
                weekly_workout_days=(
                    request.weekly_workout_days
                ),
            )
        )

        db.add(member_profile)

        for goal_value in request.goals:
            goal_code, goal_name = normalize_member_goal(goal_value)

            db.add(
                MemberGoal(
                    user_id=(
                        user.user_id
                    ),
                    goal_code=goal_code,
                    goal_name=goal_name,
                )
            )

        add_user_agreement(
            db=db,
            user_id=user.user_id,
            terms=(
                request.agreements.terms
            ),
            privacy=(
                request.agreements.privacy
            ),
            marketing=(
                request.agreements.marketing
            ),
            trainer_policy=False,
        )

        create_welcome_notification(db, user.user_id, user.name)
        db.commit()
        db.refresh(user)

        verification_store.pop(
            email,
            None,
        )

        return SignupResponse(
            message=(
                "일반 회원가입이 "
                "완료되었습니다."
            ),
            user_id=user.user_id,
            account_type=(
                user.account_type
            ),
            email=user.email,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        print(
            "일반 회원가입 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "회원가입 처리 중 "
                "오류가 발생했습니다."
            ),
        ) from error


# =========================================================
# 트레이너 회원가입
# =========================================================

@router.post(
    "/signup/trainer",
    response_model=SignupResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def signup_trainer(
    request: TrainerSignupRequest,
    db: Session = Depends(get_db),
):
    email = normalize_email(
        str(request.email)
    )

    check_email_verified(
        email
    )

    check_required_agreements(
        terms=(
            request.agreements.terms
        ),
        privacy=(
            request.agreements.privacy
        ),
        trainer_policy=(
            request
            .agreements
            .trainer_policy
        ),
    )

    existing_user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "이미 가입된 이메일입니다."
            ),
        )

    try:
        user = User(
            account_type="TRAINER",
            name=request.name.strip(),
            email=email,
            login_provider="LOCAL",
            google_sub=None,
            password_hash=(
                hash_password(
                    request.password
                )
            ),
            gender=(
                request.gender
                or "NONE"
            ),
            birth_date=(
                request.birth_date
            ),
            is_email_verified=True,
            is_active=True,
        )

        db.add(user)
        db.flush()

        selected_gym = select_or_create_gym(db, request.selected_gym)
        db.add(UserGym(user_id=user.user_id, gym_id=selected_gym.gym_id))

        db.add(
            TrainerProfile(
                user_id=user.user_id,
                gym_name=selected_gym.gym_name,
                career_years=(
                    request.career_years
                ),
                introduction=(
                    request.introduction
                ),
                approval_status=(
                    "PENDING"
                ),
            )
        )

        for specialty_name in (
            request.specialties
        ):
            cleaned_specialty = (
                specialty_name.strip()
            )

            if not cleaned_specialty:
                continue

            db.add(
                TrainerSpecialty(
                    user_id=(
                        user.user_id
                    ),
                    specialty_code=(
                        specialty_code_from_name(
                            cleaned_specialty
                        )
                    ),
                    specialty_name=(
                        cleaned_specialty
                    ),
                )
            )

        for certification_name in (
            request.certifications
        ):
            cleaned_certification = (
                certification_name.strip()
            )

            if not cleaned_certification:
                continue

            db.add(
                TrainerCertification(
                    user_id=(
                        user.user_id
                    ),
                    certification_name=(
                        cleaned_certification
                    ),
                )
            )

        add_user_agreement(
            db=db,
            user_id=user.user_id,
            terms=(
                request.agreements.terms
            ),
            privacy=(
                request.agreements.privacy
            ),
            marketing=(
                request.agreements.marketing
            ),
            trainer_policy=(
                request
                .agreements
                .trainer_policy
            ),
        )

        create_welcome_notification(db, user.user_id, user.name)
        db.commit()
        db.refresh(user)

        verification_store.pop(
            email,
            None,
        )

        return SignupResponse(
            message=(
                "트레이너 회원가입이 "
                "완료되었습니다."
            ),
            user_id=user.user_id,
            account_type=(
                user.account_type
            ),
            email=user.email,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        print(
            "트레이너 회원가입 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "회원가입 처리 중 "
                "오류가 발생했습니다."
            ),
        ) from error


# =========================================================
# 임시 비밀번호 발급
# =========================================================

@router.post(
    "/password/temporary"
)
async def issue_temporary_password(
    request: TemporaryPasswordRequest,
    db: Session = Depends(get_db),
):
    email = normalize_email(
        str(request.email)
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if not user:
        raise HTTPException(
            status_code=(
                status.HTTP_404_NOT_FOUND
            ),
            detail=(
                "가입되지 않은 이메일입니다."
            ),
        )

    if (
        user.login_provider
        != "LOCAL"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Google로 가입한 계정입니다. "
                "Google 로그인을 이용해 주세요."
            ),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "비활성화된 계정입니다."
            ),
        )

    temporary_password = (
        generate_temporary_password()
    )

    expires_at = (
        utc_now_naive()
        + timedelta(minutes=30)
    )

    previous_password_hash = (
        user.password_hash
    )

    previous_must_change = (
        user.must_change_password
    )

    previous_expires_at = (
        user.temporary_password_expires_at
    )

    try:
        user.password_hash = (
            hash_password(
                temporary_password
            )
        )

        user.must_change_password = True

        user.temporary_password_expires_at = (
            expires_at
        )

        db.flush()

        await asyncio.to_thread(
            send_temporary_password_email,
            email,
            temporary_password,
        )

        db.commit()

    except Exception as error:
        db.rollback()

        user.password_hash = (
            previous_password_hash
        )

        user.must_change_password = (
            previous_must_change
        )

        user.temporary_password_expires_at = (
            previous_expires_at
        )

        print(
            "임시 비밀번호 발급 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "임시 비밀번호 전송에 "
                "실패했습니다."
            ),
        ) from error

    return {
        "message": (
            "임시 비밀번호가 이메일로 "
            "전송되었습니다."
        ),
        "expires_in": 30 * 60,
    }

# =========================================================
# 이메일 로그인
# =========================================================

@router.post(
    "/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
)
def login(
    request: LoginRequest,
    db: Session = Depends(get_db),
):
    email = normalize_email(
        str(request.email)
    )

    user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if not user:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "이메일 또는 비밀번호가 "
                "올바르지 않습니다."
            ),
        )

    if (
        user.login_provider
        != "LOCAL"
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_400_BAD_REQUEST
            ),
            detail=(
                "Google 로그인을 이용해 주세요."
            ),
        )

    if not user.password_hash:
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "이메일 또는 비밀번호가 "
                "올바르지 않습니다."
            ),
        )

    if not verify_password(
        request.password,
        user.password_hash,
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "이메일 또는 비밀번호가 "
                "올바르지 않습니다."
            ),
        )
    
    if (
        user.must_change_password
        and user.temporary_password_expires_at
        and utc_now_naive()
        > user.temporary_password_expires_at
    ):
        raise HTTPException(
            status_code=(
                status.HTTP_401_UNAUTHORIZED
            ),
            detail=(
                "임시 비밀번호가 만료되었습니다. "
                "다시 발급해 주세요."
            ),
        )

    if not user.is_active:
        raise HTTPException(
            status_code=(
                status.HTTP_403_FORBIDDEN
            ),
            detail=(
                "비활성화된 계정입니다."
            ),
        )

    try:
        user.last_login_at = (
            utc_now_naive()
        )

        db.commit()
        db.refresh(user)

        return LoginResponse(
            message="로그인되었습니다.",
            user_id=user.user_id,
            account_type=(
                user.account_type
            ),
            name=user.name,
            email=user.email,
            has_active_trainer=has_active_trainer(
                db, user.user_id, user.account_type
            ),
            pending_pt_request_count=get_pending_pt_request_count(
                db, user.user_id, user.account_type
            ),
            access_token=create_access_token(user),
            token_type="bearer",
        )

    except Exception as error:
        db.rollback()

        print(
            "로그인 처리 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "로그인 처리 중 "
                "오류가 발생했습니다."
            ),
        ) from error


# =========================================================
# Google Authorization Code 로그인
# =========================================================

@router.post(
    "/google/code",
    response_model=(
        GoogleCodeLoginResponse
    ),
    status_code=status.HTTP_200_OK,
)
def google_code_login(
    request: GoogleCodeLoginRequest,
    db: Session = Depends(get_db),
):
    token_response = exchange_google_code(
        request.code
    )

    google_data = (
        verify_google_id_token(
            token_response["id_token"]
        )
    )

    google_sub = (
        google_data["google_sub"]
    )

    email = google_data["email"]

    user = db.scalar(
        select(User).where(
            User.google_sub
            == google_sub
        )
    )

    if user:
        if not user.is_active:
            raise HTTPException(
                status_code=(
                    status.HTTP_403_FORBIDDEN
                ),
                detail=(
                    "비활성화된 계정입니다."
                ),
            )

        try:
            user.last_login_at = (
                utc_now_naive()
            )

            db.commit()
            db.refresh(user)

            return (
                GoogleCodeLoginResponse(
                    message=(
                        "Google 로그인이 "
                        "완료되었습니다."
                    ),
                    is_new_user=False,
                    user_id=user.user_id,
                    account_type=(
                        user.account_type
                    ),
                    name=user.name,
                    email=user.email,
                    signup_token=None,
                    has_active_trainer=has_active_trainer(
                        db, user.user_id, user.account_type
                    ),
                    pending_pt_request_count=get_pending_pt_request_count(
                        db, user.user_id, user.account_type
                    ),
                    access_token=create_access_token(user),
                    token_type="bearer",
                )
            )

        except Exception as error:
            db.rollback()

            print(
                "Google 로그인 처리 실패:",
                error,
            )

            raise HTTPException(
                status_code=(
                    status
                    .HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "Google 로그인 처리 중 "
                    "오류가 발생했습니다."
                ),
            ) from error

    email_user = db.scalar(
        select(User).where(
            User.email == email
        )
    )

    if email_user:
        if (
            email_user.login_provider
            == "LOCAL"
        ):
            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "이미 이메일과 비밀번호로 "
                    "가입된 계정입니다."
                ),
            )

        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "이미 가입된 이메일입니다."
            ),
        )

    signup_token = (
        create_google_signup_token(
            google_data
        )
    )

    return GoogleCodeLoginResponse(
        message=(
            "추가 정보 입력이 필요합니다."
        ),
        is_new_user=True,
        user_id=None,
        account_type=None,
        name=google_data["name"],
        email=email,
        signup_token=signup_token,
    )


@router.get("/me")
def authenticated_user_me(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return {
        "user_id": user.user_id,
        "name": user.name,
        "email": user.email,
        "account_type": user.account_type,
        "is_active": user.is_active,
        "has_active_trainer": has_active_trainer(db, user.user_id, user.account_type),
        "pending_pt_request_count": get_pending_pt_request_count(
            db, user.user_id, user.account_type
        ),
    }


# =========================================================
# Google 일반 회원 최종 가입
# =========================================================

@router.post(
    "/google/signup/member",
    response_model=SignupResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def google_signup_member(
    request: GoogleMemberSignupRequest,
    db: Session = Depends(get_db),
):
    signup_data = (
        get_google_signup_data(
            request.signup_token
        )
    )

    google_sub = (
        signup_data["google_sub"]
    )

    email = signup_data["email"]
    name = signup_data["name"]

    check_required_agreements(
        terms=(
            request.agreements.terms
        ),
        privacy=(
            request.agreements.privacy
        ),
    )

    existing_user = db.scalar(
        select(User).where(
            or_(
                User.email == email,
                User.google_sub
                == google_sub,
            )
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "이미 가입된 Google 계정입니다."
            ),
        )

    try:
        user = User(
            account_type="MEMBER",
            name=name,
            email=email,
            login_provider="GOOGLE",
            google_sub=google_sub,
            password_hash=None,
            gender=(
                request.gender
                or "NONE"
            ),
            birth_date=(
                request.birth_date
            ),
            is_email_verified=True,
            is_active=True,
        )

        db.add(user)
        db.flush()

        db.add(
            MemberProfile(
                user_id=user.user_id,
                height_cm=(
                    request.height_cm
                ),
                weight_kg=(
                    request.weight_kg
                ),
                exercise_level=(
                    request.exercise_level
                ),
                weekly_workout_days=(
                    request.weekly_workout_days
                ),
            )
        )

        for goal_value in request.goals:
            goal_code, goal_name = normalize_member_goal(goal_value)

            db.add(
                MemberGoal(
                    user_id=(
                        user.user_id
                    ),
                    goal_code=goal_code,
                    goal_name=goal_name,
                )
            )

        add_user_agreement(
            db=db,
            user_id=user.user_id,
            terms=(
                request.agreements.terms
            ),
            privacy=(
                request.agreements.privacy
            ),
            marketing=(
                request.agreements.marketing
            ),
            trainer_policy=False,
        )

        create_welcome_notification(db, user.user_id, user.name)
        db.commit()
        db.refresh(user)

        remove_google_signup_token(
            request.signup_token
        )

        return SignupResponse(
            message=(
                "Google 일반 회원가입이 "
                "완료되었습니다."
            ),
            user_id=user.user_id,
            account_type=(
                user.account_type
            ),
            email=user.email,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        print(
            "Google 일반 회원가입 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Google 회원가입 처리 중 "
                "오류가 발생했습니다."
            ),
        ) from error


# =========================================================
# Google 트레이너 최종 가입
# =========================================================

@router.post(
    "/google/signup/trainer",
    response_model=SignupResponse,
    status_code=(
        status.HTTP_201_CREATED
    ),
)
def google_signup_trainer(
    request: GoogleTrainerSignupRequest,
    db: Session = Depends(get_db),
):
    signup_data = (
        get_google_signup_data(
            request.signup_token
        )
    )

    google_sub = (
        signup_data["google_sub"]
    )

    email = signup_data["email"]
    name = signup_data["name"]

    check_required_agreements(
        terms=(
            request.agreements.terms
        ),
        privacy=(
            request.agreements.privacy
        ),
        trainer_policy=(
            request
            .agreements
            .trainer_policy
        ),
    )

    existing_user = db.scalar(
        select(User).where(
            or_(
                User.email == email,
                User.google_sub
                == google_sub,
            )
        )
    )

    if existing_user:
        raise HTTPException(
            status_code=(
                status.HTTP_409_CONFLICT
            ),
            detail=(
                "이미 가입된 Google 계정입니다."
            ),
        )

    try:
        user = User(
            account_type="TRAINER",
            name=name,
            email=email,
            login_provider="GOOGLE",
            google_sub=google_sub,
            password_hash=None,
            gender=(
                request.gender
                or "NONE"
            ),
            birth_date=(
                request.birth_date
            ),
            is_email_verified=True,
            is_active=True,
        )

        db.add(user)
        db.flush()

        selected_gym = select_or_create_gym(db, request.selected_gym)
        db.add(UserGym(user_id=user.user_id, gym_id=selected_gym.gym_id))

        db.add(
            TrainerProfile(
                user_id=user.user_id,
                gym_name=selected_gym.gym_name,
                career_years=(
                    request.career_years
                ),
                introduction=(
                    request.introduction
                ),
                approval_status=(
                    "PENDING"
                ),
            )
        )

        for specialty_name in (
            request.specialties
        ):
            cleaned_specialty = (
                specialty_name.strip()
            )

            if not cleaned_specialty:
                continue

            db.add(
                TrainerSpecialty(
                    user_id=(
                        user.user_id
                    ),
                    specialty_code=(
                        specialty_code_from_name(
                            cleaned_specialty
                        )
                    ),
                    specialty_name=(
                        cleaned_specialty
                    ),
                )
            )

        for certification_name in (
            request.certifications
        ):
            cleaned_certification = (
                certification_name.strip()
            )

            if not cleaned_certification:
                continue

            db.add(
                TrainerCertification(
                    user_id=(
                        user.user_id
                    ),
                    certification_name=(
                        cleaned_certification
                    ),
                )
            )

        add_user_agreement(
            db=db,
            user_id=user.user_id,
            terms=(
                request.agreements.terms
            ),
            privacy=(
                request.agreements.privacy
            ),
            marketing=(
                request.agreements.marketing
            ),
            trainer_policy=(
                request
                .agreements
                .trainer_policy
            ),
        )

        create_welcome_notification(db, user.user_id, user.name)
        db.commit()
        db.refresh(user)

        remove_google_signup_token(
            request.signup_token
        )

        return SignupResponse(
            message=(
                "Google 트레이너 회원가입이 "
                "완료되었습니다."
            ),
            user_id=user.user_id,
            account_type=(
                user.account_type
            ),
            email=user.email,
        )

    except HTTPException:
        db.rollback()
        raise

    except Exception as error:
        db.rollback()

        print(
            "Google 트레이너 회원가입 실패:",
            error,
        )

        raise HTTPException(
            status_code=(
                status.HTTP_500_INTERNAL_SERVER_ERROR
            ),
            detail=(
                "Google 트레이너 회원가입 "
                "처리 중 오류가 발생했습니다."
            ),
        ) from error
