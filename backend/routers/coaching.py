from __future__ import annotations

import asyncio
import os
import time
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Exercise, User, WorkoutPlan
from backend.security import get_current_user, require_account_type
from backend.services.coaching_session_service import coaching_session_store
from backend.services.exercise_catalog import AI_COACHING_EXERCISE_CODES


router = APIRouter(prefix="/api/coaching/sessions", tags=["coaching-sessions"])
require_member = require_account_type("MEMBER")


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


def pose_debug_enabled():
    return os.getenv("POSE_DEBUG", "").strip().lower() in {
        "1", "true", "yes", "on"
    }


async def decode_uploaded_image(image: UploadFile, *, include_bytes=False):
    if not image.content_type or not image.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="이미지 파일만 전송할 수 있습니다.")
    image_bytes = await image.read()
    if not image_bytes:
        if pose_debug_enabled():
            print({"event": "pushup-upload", "reason": "empty-upload"})
        raise HTTPException(status_code=400, detail="빈 이미지가 전송되었습니다.")
    frame = cv2.imdecode(
        np.frombuffer(image_bytes, dtype=np.uint8), cv2.IMREAD_COLOR
    )
    if frame is None:
        if pose_debug_enabled():
            print({
                "event": "pushup-upload",
                "reason": "decode-failed",
                "upload_bytes": len(image_bytes),
            })
        raise HTTPException(status_code=400, detail="이미지를 읽을 수 없습니다.")
    if pose_debug_enabled():
        blank_frame = float(frame.max()) - float(frame.min()) < 3
        print({
            "event": "pushup-upload",
            "reason": "blank-frame" if blank_frame else "decoded-frame",
            "upload_bytes": len(image_bytes),
            "shape": list(frame.shape),
            "mean_brightness": round(float(frame.mean()), 2),
            "min_pixel": int(frame.min()),
            "max_pixel": int(frame.max()),
        })
    return (frame, image_bytes) if include_bytes else frame


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
    user: User = Depends(require_member),
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
    frame_id: int = Form(..., ge=0),
    frame_mean_brightness: float | None = Form(default=None, ge=0, le=255),
    brightness_adjusted: bool = Form(default=False),
    user: User = Depends(require_member),
):
    frame, uploaded_jpeg = await decode_uploaded_image(image, include_bytes=True)

    def process():
        with coaching_session_store.locked(
            session_id, user_id=user.user_id
        ) as session:
            inference_started_at = time.perf_counter()
            if session.exercise_code == "PUSHUP":
                if pose_debug_enabled() and not getattr(
                    session.analyzer, "_debug_received_frame_saved", False
                ):
                    debug_path = (
                        Path(__file__).resolve().parents[2]
                        / "debug"
                        / "pushup_received_frame.jpg"
                    )
                    debug_path.parent.mkdir(parents=True, exist_ok=True)
                    debug_path.write_bytes(uploaded_jpeg)
                    session.analyzer._debug_received_frame_saved = True
                    print({
                        "event": "pushup-received-frame-saved",
                        "path": str(debug_path),
                        "upload_bytes": len(uploaded_jpeg),
                        "shape": list(frame.shape),
                    })
                _, status = session.analyzer.process_frame(
                    frame,
                    frame_mean_brightness=frame_mean_brightness,
                    brightness_adjusted=brightness_adjusted,
                )
            else:
                _, status = session.analyzer.process_frame(frame)
            inference_ms = (time.perf_counter() - inference_started_at) * 1000
            normalized = normalize_analysis_status(
                session.exercise_code, status, session.analyzer
            )
            normalized["frame_id"] = frame_id
            normalized["performance"] = {
                "inference_ms": round(inference_ms, 1),
            }
            if os.getenv("POSE_DEBUG", "").strip().lower() in {
                "1", "true", "yes", "on"
            }:
                print({
                    "event": "pose-detection",
                    "frame_id": frame_id,
                    "reason": status.get("detection_reason"),
                    "debug": status.get("detection_debug"),
                    "failure_counts": status.get("detection_failure_counts"),
                })
            if session.exercise_code in {"SQUAT", "PUSHUP"}:
                capture = session.analyzer.get_completed_pose_capture()
                if capture is not None:
                    try:
                        normalized_capture = dict(capture)
                        for angle_field in (
                            "knee_angle",
                            "torso_angle",
                            "elbow_angle",
                            "body_alignment_angle",
                        ):
                            if normalized_capture.get(angle_field) is not None:
                                normalized_capture[angle_field] = round(
                                    normalized_capture[angle_field], 1
                                )
                        normalized["completed_pose_capture"] = normalized_capture
                        if os.getenv("POSE_DEBUG", "").strip().lower() in {
                            "1", "true", "yes", "on"
                        }:
                            print({
                                "count": status.get("count"),
                                "best_score": capture["score"],
                                "best_angle": capture.get("knee_angle")
                                or capture.get("elbow_angle"),
                                "has_best_frame": True,
                                "has_completed_capture": bool(capture["image"]),
                                "capture_format": (
                                    "data-url"
                                    if capture["image"].startswith("data:image/")
                                    else "empty"
                                ),
                            })
                    finally:
                        # Encoding and response payload construction must happen
                        # before the repetition frame is released.
                        session.analyzer.clear_completed_pose_capture()
                elif status.get("repetition_completed"):
                    normalized["capture_fallback_reason"] = "no-valid-down-pose"
                    if os.getenv("POSE_DEBUG", "").strip().lower() in {
                        "1", "true", "yes", "on"
                    }:
                        print({
                            "count": status.get("count"),
                            "best_score": getattr(
                                session.analyzer,
                                "best_pose_score",
                                getattr(
                                    session.analyzer,
                                    "repetition_best_posture_score",
                                    -1,
                                ),
                            ),
                            "best_angle": getattr(
                                session.analyzer,
                                "best_pose_angle",
                                getattr(
                                    session.analyzer,
                                    "current_min_elbow_angle",
                                    None,
                                ),
                            ),
                            "has_best_frame": False,
                            "has_completed_capture": False,
                            "capture_format": "empty",
                            "fallback_reason": "no-valid-down-pose",
                        })
            return {
                "success": True,
                **normalized,
            }

    return await asyncio.to_thread(process)


@router.post("/{session_id}/reset")
def reset_coaching_session(
    session_id: str,
    user: User = Depends(require_member),
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
    user: User = Depends(require_member),
):
    removed = coaching_session_store.delete(session_id, user_id=user.user_id)
    return {"success": True, "removed": removed}
