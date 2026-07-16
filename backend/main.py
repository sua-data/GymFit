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

from backend.squat_pose import SquatAnalyzer

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

squat_analyzer = SquatAnalyzer()

@app.on_event("startup")
def startup_event():
    test_database_connection()

    Base.metadata.create_all(
        bind=engine
    )

app.include_router(auth_router)
app.include_router(dashboard_router)
app.include_router(workout_router)

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

    image_array = np.frombuffer(
        image_bytes,
        dtype=np.uint8,
    )

    frame = cv2.imdecode(
        image_array,
        cv2.IMREAD_COLOR,
    )

    if frame is None:
        raise HTTPException(
            status_code=400,
            detail="이미지를 읽을 수 없습니다.",
        )

    _, status = squat_analyzer.process_frame(frame)

    return {
        "success": True,
        **status,
    }
