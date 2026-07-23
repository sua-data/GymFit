import os
from pathlib import Path

import cv2
import numpy as np

from fastapi import (
    FastAPI,
    File,
    HTTPException,
    UploadFile
)

from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from backend.exercise_pose import (
    create_pose_analyzers,
    get_pose_analyzer,
)

from backend.database import (
    Base,
    engine,
    test_database_connection
)
from backend.routers.auth import (
    router as auth_router
)
from backend.routers.dashboard import (
    router as dashboard_router
)

from backend.routers.workout import (
    router as workout_router
)
from backend.routers.user import (
    router as user_router
)
from backend.routers.gym import (
    router as gym_router
)
from backend.routers.gym_machine import router as gym_machine_router
from backend.routers.admin import router as admin_router
from backend.routers.trainer_certification import router as trainer_certification_router
from backend.routers.trainer_employment import router as trainer_employment_router
from backend.routers.pt import router as pt_router
from backend.routers.notification import router as notification_router
from backend.routers.pt_assignment import router as pt_assignment_router
from backend.routers.pt_feedback import router as pt_feedback_router
from backend.routers.pt_schedule import router as pt_schedule_router
from backend.routers.workout_session import router as workout_session_router

# 모든 모델을 SQLAlchemy에 등록
import backend.models


# 프로젝트 최상위 경로
BASE_DIR = Path(__file__).resolve().parent.parent

# frontend 폴더 경로
FRONTEND_DIR = BASE_DIR / "frontend"


app = FastAPI(
    title="GYMFIT API",
    version="1.0.0",
)

exercise_analyzers = create_pose_analyzers()
squat_analyzer = exercise_analyzers["SQUAT"]

COACHING_PATH_TO_CODE = {
    "squat": "SQUAT",
    "pushup": "PUSHUP",
    "push-up": "PUSHUP",
    "shoulder-press": "SHOULDER_PRESS",
    "shoulder_press": "SHOULDER_PRESS",
}

@app.on_event("startup")
def startup_event():
    test_database_connection()

    Base.metadata.create_all(
        bind=engine
    )

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(workout_router)
app.include_router(user_router)
app.include_router(gym_router)
app.include_router(gym_machine_router)
app.include_router(admin_router)
app.include_router(trainer_certification_router)
app.include_router(trainer_employment_router)
app.include_router(pt_router)
app.include_router(notification_router)
app.include_router(pt_assignment_router)
app.include_router(pt_feedback_router)
app.include_router(pt_schedule_router)
app.include_router(workout_session_router)

# frontend 폴더 전체를 /static 경로로 연결
app.mount(
    "/static",
    StaticFiles(directory=str(FRONTEND_DIR)),
    name="static",
)


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(FRONTEND_DIR / "login.html")


@app.get("/login", include_in_schema=False)
def login_page():
    return FileResponse(FRONTEND_DIR / "login.html")

@app.get("/find-password", include_in_schema=False)
def find_password_page():
    return FileResponse(
        FRONTEND_DIR / "find_password.html"
    )

@app.get("/signup/type", include_in_schema=False)
def signup_type_page():
    return FileResponse(
        FRONTEND_DIR / "signup_type.html"
    )

@app.get("/signup", include_in_schema=False)
def signup_page():
    return FileResponse(FRONTEND_DIR / "signup.html")

@app.get("/signup/step2", include_in_schema=False)
def signup_step2_page():
    return FileResponse(FRONTEND_DIR / "signup_step2.html")

@app.get("/signup/trainer", include_in_schema=False)
def signup_trainer_page():
    return FileResponse(
        FRONTEND_DIR / "signup_trainer.html"
    )

@app.get(
    "/signup/trainer/step2",
    include_in_schema=False
)
def signup_trainer_step2_page():
    return FileResponse(
        FRONTEND_DIR / "signup_trainer_step2.html"
    )

@app.get("/dashboard")
def dashboard():
    return FileResponse(
        FRONTEND_DIR / "dashboard.html"
    )

@app.get(
    "/coaching",
    include_in_schema=False,
)
def coaching_page():
    return FileResponse(
        FRONTEND_DIR / "coaching.html"
    )

@app.get(
    "/routine",
    include_in_schema=False,
)
def routine_page():
    return FileResponse(
        FRONTEND_DIR / "routine.html"
    )


@app.get(
    "/records",
    include_in_schema=False,
)
def records_page():
    return FileResponse(
        FRONTEND_DIR / "records.html"
    )


@app.get(
    "/records/{workout_record_id}",
    include_in_schema=False,
)
def record_detail_page(workout_record_id: int):
    return FileResponse(
        FRONTEND_DIR / "records.html"
    )


@app.get(
    "/mypage",
    include_in_schema=False,
)
def mypage_page():
    return FileResponse(
        FRONTEND_DIR / "mypage.html"
    )


@app.get("/my-gym", include_in_schema=False)
def my_gym_page():
    return FileResponse(
        FRONTEND_DIR / "my_gym.html"
    )


@app.get("/machines", include_in_schema=False)
def machines_page():
    return FileResponse(FRONTEND_DIR / "machines.html")


@app.get("/admin/trainers", include_in_schema=False)
def admin_trainers_page():
    return FileResponse(FRONTEND_DIR / "admin_trainers.html")


@app.get("/admin/employments", include_in_schema=False)
def admin_employments_page():
    return FileResponse(FRONTEND_DIR / "admin_employments.html")


@app.get("/admin/dashboard", include_in_schema=False)
def admin_dashboard_page():
    return FileResponse(FRONTEND_DIR / "admin_dashboard.html")


@app.get("/trainer/certifications", include_in_schema=False)
def trainer_certifications_page():
    return FileResponse(FRONTEND_DIR / "trainer_certifications.html")


@app.get("/pt", include_in_schema=False)
@app.get("/pt/requests", include_in_schema=False)
@app.get("/trainer/members", include_in_schema=False)
def pt_page():
    return FileResponse(FRONTEND_DIR / "pt.html")


@app.get("/pt/assignments", include_in_schema=False)
def member_assignments_page():
    return FileResponse(FRONTEND_DIR / "pt_assignments.html")


@app.get("/trainer/assignments", include_in_schema=False)
def trainer_assignments_page():
    return FileResponse(FRONTEND_DIR / "trainer_assignments.html")


@app.get("/pt/feedback", include_in_schema=False)
def pt_feedback_page():
    return FileResponse(FRONTEND_DIR / "pt_feedback.html")


@app.get("/notifications", include_in_schema=False)
def notifications_page():
    return FileResponse(FRONTEND_DIR / "notifications.html")


@app.get("/pt/schedules", include_in_schema=False)
def member_schedules_page():
    return FileResponse(FRONTEND_DIR / "pt_schedules.html")


@app.get("/trainer/schedules", include_in_schema=False)
def trainer_schedules_page():
    return FileResponse(FRONTEND_DIR / "trainer_schedules.html")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "GYMFIT",
    }

@app.get("/api/coaching/squat/status")
def get_squat_status():
    return {
        "count": squat_analyzer.squat_count,
        "stage": squat_analyzer.stage,
        "stage_text": (
            "내려감"
            if squat_analyzer.stage == "DOWN"
            else "일어섬"
        ),
        "last_depth": (
            round(squat_analyzer.last_squat_depth, 1)
            if squat_analyzer.last_squat_depth is not None
            else None
        ),
        "feedback": squat_analyzer.feedback,
    }


@app.post("/api/coaching/squat/reset")
def reset_squat_status():
    squat_analyzer.reset()

    return {
        "success": True,
        "message": "스쿼트 기록이 초기화되었습니다.",
        "count": squat_analyzer.squat_count,
        "stage": squat_analyzer.stage,
        "feedback": squat_analyzer.feedback,
    }

@app.post("/api/coaching/squat/analyze")
async def analyze_squat_frame(
    image: UploadFile = File(...),
):
    frame = await decode_uploaded_image(image)
    _, status = squat_analyzer.process_frame(frame)

    return {
        "success": True,
        **normalize_analysis_status("SQUAT", status),
    }


def get_exercise_analyzer(exercise_path: str):
    exercise_code = COACHING_PATH_TO_CODE.get(
        exercise_path.strip().lower()
    )
    try:
        analyzer = get_pose_analyzer(exercise_analyzers, exercise_code)
    except KeyError:
        raise HTTPException(
            status_code=404,
            detail="지원하지 않는 코칭 운동입니다.",
        ) from None
    return exercise_code, analyzer


def normalize_analysis_status(exercise_code: str, status: dict):
    posture_score = status.get("posture_score")
    if posture_score is None and exercise_code == "SQUAT":
        depth = status.get("last_depth") or status.get("average_angle")
        torso_angle = status.get("last_torso_angle") or status.get("torso_angle")
        posture_score = 70
        if depth is not None:
            if depth < 100:
                posture_score = 95
            elif depth <= 110:
                posture_score = 90
            elif depth <= 125:
                posture_score = 75
            else:
                posture_score = 65
        if torso_angle is not None:
            if torso_angle >= 45:
                posture_score -= 20
            elif torso_angle >= 35:
                posture_score -= 10
        posture_score = max(0, min(100, posture_score))

    normalized = {
        "exercise_code": exercise_code,
        "posture_score": posture_score or 0,
        "landmarks_detected": bool(status.get("pose_valid")),
        "is_visible": bool(status.get("pose_valid")),
        **status,
    }
    if exercise_code == "SQUAT":
        normalized.setdefault(
            "angles",
            {
                "left_knee": status.get("left_angle"),
                "right_knee": status.get("right_angle"),
                "knee": status.get("average_angle"),
                "torso": status.get("torso_angle"),
            },
        )
        if os.getenv("POSE_DEBUG", "").strip().lower() in {
            "1", "true", "yes", "on"
        }:
            selected_side = (
                "BOTH"
                if status.get("left_angle") is not None
                and status.get("right_angle") is not None
                else "LEFT"
                if status.get("left_angle") is not None
                else "RIGHT"
                if status.get("right_angle") is not None
                else None
            )
            normalized.setdefault(
                "debug",
                {
                    "selected_side": selected_side,
                    "stable_frames": max(
                        squat_analyzer.down_frames,
                        squat_analyzer.up_frames,
                    ),
                    "missing_frames": squat_analyzer.missing_frames,
                },
            )
    return normalized


async def decode_uploaded_image(image: UploadFile):
    if not image.content_type:
        raise HTTPException(
            status_code=400,
            detail="이미지 형식을 확인할 수 없습니다.",
        )
    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="이미지 파일만 전송할 수 있습니다.",
        )

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="빈 이미지가 전송되었습니다.",
        )

    frame = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8),
        cv2.IMREAD_COLOR,
    )
    if frame is None:
        raise HTTPException(
            status_code=400,
            detail="이미지를 읽을 수 없습니다.",
        )
    return frame


@app.post("/api/coaching/{exercise_path}/reset")
def reset_exercise_status(exercise_path: str):
    exercise_code, analyzer = get_exercise_analyzer(exercise_path)
    analyzer.reset()
    count = (
        analyzer.squat_count
        if exercise_code == "SQUAT"
        else analyzer.count
    )
    return {
        "success": True,
        "exercise_code": exercise_code,
        "message": "운동 분석 상태가 초기화되었습니다.",
        "count": count,
        "stage": analyzer.stage,
        "feedback": analyzer.feedback,
    }


@app.post("/api/coaching/{exercise_path}/analyze")
async def analyze_exercise_frame(
    exercise_path: str,
    image: UploadFile = File(...),
):
    exercise_code, analyzer = get_exercise_analyzer(exercise_path)
    frame = await decode_uploaded_image(image)
    _, status = analyzer.process_frame(frame)
    return {
        "success": True,
        **normalize_analysis_status(exercise_code, status),
    }
