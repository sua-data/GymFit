# 푸시업과 숄더프레스는 실제 카메라 임계값 튜닝 전의 초기 테스트 지원이다.
AI_COACHING_EXERCISE_CODES = frozenset(
    {"SQUAT", "PUSHUP", "SHOULDER_PRESS"}
)


def is_coaching_supported(exercise_code: str | None) -> bool:
    return bool(exercise_code and exercise_code.upper() in AI_COACHING_EXERCISE_CODES)
