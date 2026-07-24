from __future__ import annotations

import asyncio
import os

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Exercise, User, WorkoutPlan
from backend.security import get_current_user
from backend.services.coaching_session_service import coaching_session_store
from backend.services.exercise_catalog import AI_COACHING_EXERCISE_CODES


router = APIRouter(prefix="/api/coaching/sessions", tags=["coaching-sessions"])


class CoachingSessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    exercise_code: str
    target_reps: int = Field(ge=1, le=1000)
    target_sets: int = Field(ge=1, le=100)
    workout_plan_id: int | None = Field(default=None, gt=0)

    @field_validator("exercise_code")
    @classmethod
    def normalize_exercise_code(cls, value: str) -> str:
        return value.strip().upper()


async def decode_uploaded_image(image: UploadFile):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 전송할 수 있습니다.")
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="빈 이미지가 전송되었습니다.")
    frame = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR
    )
    if frame is None:
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.")
    return frame


def normalize_analysis_status(exercise_code: str, status: dict, analyzer):
    posture_score = status.get("posture_score")
    if posture_score is None and exercise_code == "SQUAT":
        depth = status.get("last_depth") or status.get("average_angle")
        torso_angle = status.get("last_torso_angle") or status.get("torso_angle")
        posture_score = 70
        if depth is not None:
            posture_score = 95 if depth < 100 else 90 if depth <= 110 else 75 if depth <= 125 else 65
        if torso_angle is not None:
            posture_score -= 20 if torso_angle >= 45 else 10 if torso_angle >= 35 else 0
        posture_score = max(0, min(100, posture_score))
    normalized = {
        "exercise_code": exercise_code,
        "posture_score": posture_score or 0,
        "landmarks_detected": bool(status.get("pose_valid")),
        "is_visible": bool(status.get("pose_valid")),
        **status,
    }
    if exercise_code == "SQUAT":
        normalized.setdefault("angles", {
            "left_knee": status.get("left_angle"),
            "right_knee": status.get("right_angle"),
            "knee": status.get("average_angle"),
            "torso": status.get("torso_angle"),
        })
        if os.getenv("POSE_DEBUG", "").strip().lower() in {"1", "true", "yes", "on"}:
            left, right = status.get("left_angle"), status.get("right_angle")
            selected_side = "BOTH" if left is not None and right is not None else "LEFT" if left is not None else "RIGHT" if right is not None else None
            normalized.setdefault("debug", {
                "selected_side": selected_side,
                "stable_frames": max(analyzer.down_frames, analyzer.up_frames),
                "missing_frames": analyzer.missing_frames,
            })
    return normalized


@router.post("")
def create_coaching_session(
    payload: CoachingSessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if payload.exercise_code not in AI_COACHING_EXERCISE_CODES:
        raise HTTPException(
            status_code=400, detail="지원하지 않는 코칭 운동입니다."
        )
    if payload.workout_plan_id is not None:
        owned_plan = db.scalar(
            select(WorkoutPlan.workout_plan_id)
            .join(Exercise, Exercise.exercise_id == WorkoutPlan.exercise_id)
            .where(
                WorkoutPlan.workout_plan_id == payload.workout_plan_id,
                WorkoutPlan.user_id == user.user_id,
                Exercise.exercise_code == payload.exercise_code,
            )
        )
        if owned_plan is None:
            raise HTTPException(
                status_code=404, detail="연결할 운동 계획을 찾을 수 없습니다."
            )
    session = coaching_session_store.create(
        user_id=user.user_id,
        exercise_code=payload.exercise_code,
        target_reps=payload.target_reps,
        target_sets=payload.target_sets,
        workout_plan_id=payload.workout_plan_id,
    )
    return {
        "coaching_session_id": session.session_id,
        "exercise_code": session.exercise_code,
        "target_reps": session.target_reps,
        "target_sets": session.target_sets,
        "workout_plan_id": session.workout_plan_id,
    }


@router.post("/{session_id}/analyze")
async def analyze_coaching_frame(
    session_id: str,
    image: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    frame = await decode_uploaded_image(image)

    def process():
        with coaching_session_store.locked(
            session_id, user_id=user.user_id
        ) as session:
            _, status = session.analyzer.process_frame(frame)
            return {
                "success": True,
                **normalize_analysis_status(
                    session.exercise_code, status, session.analyzer
                ),
            }

    return await asyncio.to_thread(process)


@router.post("/{session_id}/reset")
def reset_coaching_session(
    session_id: str,
    user: User = Depends(get_current_user),
):
    session = coaching_session_store.reset(session_id, user_id=user.user_id)
    count = (
        session.analyzer.squat_count
        if session.exercise_code == "SQUAT"
        else session.analyzer.count
    )
    return {
        "success": True,
        "exercise_code": session.exercise_code,
        "count": count,
        "stage": session.analyzer.stage,
        "feedback": session.analyzer.feedback,
    }


@router.delete("/{session_id}")
def delete_coaching_session(
    session_id: str,
    user: User = Depends(get_current_user),
):
    removed = coaching_session_store.delete(session_id, user_id=user.user_id)
    return {"success": True, "removed": removed}
