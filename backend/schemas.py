from datetime import date

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
)


# =========================================================
# 공통 약관 동의
# =========================================================

class AgreementSchema(BaseModel):
    terms: bool
    privacy: bool
    marketing: bool = False
    trainer_policy: bool = False


# =========================================================
# 공통 검증 함수
# =========================================================

def normalize_gender_value(
    value: str,
) -> str:
    gender_map = {
        "MALE": "MALE",
        "FEMALE": "FEMALE",
        "NONE": "NONE",
        "남성": "MALE",
        "여성": "FEMALE",
        "선택 안 함": "NONE",
        "선택안함": "NONE",
    }

    cleaned_value = value.strip()

    normalized = gender_map.get(
        cleaned_value.upper(),
        gender_map.get(cleaned_value),
    )

    if normalized is None:
        raise ValueError(
            "올바른 성별 값이 아닙니다."
        )

    return normalized


def normalize_exercise_level_value(
    value: str | None,
) -> str | None:
    if value is None:
        return None

    cleaned_value = value.strip()

    if not cleaned_value:
        return None

    level_map = {
        "BEGINNER": "BEGINNER",
        "INTERMEDIATE": "INTERMEDIATE",
        "ADVANCED": "ADVANCED",
        "초급": "BEGINNER",
        "중급": "INTERMEDIATE",
        "고급": "ADVANCED",
    }

    normalized = level_map.get(
        cleaned_value.upper(),
        level_map.get(cleaned_value),
    )

    if normalized is None:
        raise ValueError(
            "올바른 운동 수준이 아닙니다."
        )

    return normalized


def clean_text_list(
    values: list[str],
) -> list[str]:
    cleaned_values: list[str] = []

    for value in values:
        cleaned_value = value.strip()

        if (
            cleaned_value
            and cleaned_value not in cleaned_values
        ):
            cleaned_values.append(
                cleaned_value
            )

    return cleaned_values


# =========================================================
# 일반 회원 회원가입
# =========================================================

class MemberSignupRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=100,
    )

    gender: str = "NONE"

    birth_date: date | None = None

    height_cm: float | None = Field(
        default=None,
        ge=50,
        le=300,
    )

    weight_kg: float | None = Field(
        default=None,
        ge=20,
        le=500,
    )

    exercise_level: str | None = None

    goals: list[str] = Field(
        default_factory=list,
    )

    agreements: AgreementSchema

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "이름을 입력해 주세요."
            )

        return cleaned_value

    @field_validator("gender")
    @classmethod
    def normalize_gender(
        cls,
        value: str,
    ) -> str:
        return normalize_gender_value(
            value
        )

    @field_validator("exercise_level")
    @classmethod
    def normalize_exercise_level(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_exercise_level_value(
            value
        )

    @field_validator("goals")
    @classmethod
    def normalize_goals(
        cls,
        values: list[str],
    ) -> list[str]:
        return clean_text_list(values)


# =========================================================
# 트레이너 회원가입
# =========================================================

class TrainerSignupRequest(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=100,
    )

    gender: str = "NONE"

    birth_date: date | None = None

    gym_name: str | None = Field(
        default=None,
        max_length=150,
    )

    career_years: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    introduction: str | None = Field(
        default=None,
        max_length=300,
    )

    specialties: list[str] = Field(
        default_factory=list,
    )

    certifications: list[str] = Field(
        default_factory=list,
    )

    agreements: AgreementSchema

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "이름을 입력해 주세요."
            )

        return cleaned_value

    @field_validator("gender")
    @classmethod
    def normalize_gender(
        cls,
        value: str,
    ) -> str:
        return normalize_gender_value(
            value
        )

    @field_validator(
        "gym_name",
        "introduction",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()

        return cleaned_value or None

    @field_validator("specialties")
    @classmethod
    def normalize_specialties(
        cls,
        values: list[str],
    ) -> list[str]:
        return clean_text_list(values)

    @field_validator("certifications")
    @classmethod
    def normalize_certifications(
        cls,
        values: list[str],
    ) -> list[str]:
        return clean_text_list(values)


# =========================================================
# 로그인
# =========================================================

class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=100,
    )


class LoginResponse(BaseModel):
    message: str
    user_id: int
    account_type: str
    name: str
    email: EmailStr
    must_change_password: bool = False


# =========================================================
# 회원가입 응답
# =========================================================

class SignupResponse(BaseModel):
    message: str
    user_id: int
    account_type: str
    email: EmailStr


# =========================================================
# Google Authorization Code 로그인
# =========================================================

class GoogleCodeLoginRequest(BaseModel):
    code: str = Field(
        min_length=1,
    )

    @field_validator("code")
    @classmethod
    def clean_code(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "Google 인증 코드가 없습니다."
            )

        return cleaned_value


class GoogleCodeLoginResponse(BaseModel):
    message: str
    is_new_user: bool

    user_id: int | None = None
    account_type: str | None = None

    name: str
    email: EmailStr

    signup_token: str | None = None


# =========================================================
# Google 일반 회원 최종 가입
# =========================================================

class GoogleMemberSignupRequest(BaseModel):
    signup_token: str = Field(
        min_length=1,
    )

    gender: str = "NONE"

    birth_date: date | None = None

    height_cm: float | None = Field(
        default=None,
        ge=50,
        le=300,
    )

    weight_kg: float | None = Field(
        default=None,
        ge=20,
        le=500,
    )

    exercise_level: str | None = None

    goals: list[str] = Field(
        default_factory=list,
    )

    agreements: AgreementSchema

    @field_validator("signup_token")
    @classmethod
    def clean_signup_token(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "Google 가입 정보가 없습니다."
            )

        return cleaned_value

    @field_validator("gender")
    @classmethod
    def normalize_gender(
        cls,
        value: str,
    ) -> str:
        return normalize_gender_value(
            value
        )

    @field_validator("exercise_level")
    @classmethod
    def normalize_exercise_level(
        cls,
        value: str | None,
    ) -> str | None:
        return normalize_exercise_level_value(
            value
        )

    @field_validator("goals")
    @classmethod
    def normalize_goals(
        cls,
        values: list[str],
    ) -> list[str]:
        return clean_text_list(values)


# =========================================================
# Google 트레이너 최종 가입
# =========================================================

class GoogleTrainerSignupRequest(BaseModel):
    signup_token: str = Field(
        min_length=1,
    )

    gender: str = "NONE"

    birth_date: date | None = None

    gym_name: str | None = Field(
        default=None,
        max_length=150,
    )

    career_years: int | None = Field(
        default=None,
        ge=0,
        le=100,
    )

    introduction: str | None = Field(
        default=None,
        max_length=300,
    )

    specialties: list[str] = Field(
        default_factory=list,
    )

    certifications: list[str] = Field(
        default_factory=list,
    )

    agreements: AgreementSchema

    @field_validator("signup_token")
    @classmethod
    def clean_signup_token(
        cls,
        value: str,
    ) -> str:
        cleaned_value = value.strip()

        if not cleaned_value:
            raise ValueError(
                "Google 가입 정보가 없습니다."
            )

        return cleaned_value

    @field_validator("gender")
    @classmethod
    def normalize_gender(
        cls,
        value: str,
    ) -> str:
        return normalize_gender_value(
            value
        )

    @field_validator(
        "gym_name",
        "introduction",
    )
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        cleaned_value = value.strip()

        return cleaned_value or None

    @field_validator("specialties")
    @classmethod
    def normalize_specialties(
        cls,
        values: list[str],
    ) -> list[str]:
        return clean_text_list(values)

    @field_validator("certifications")
    @classmethod
    def normalize_certifications(
        cls,
        values: list[str],
    ) -> list[str]:
        return clean_text_list(values)