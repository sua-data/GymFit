"""카메라 없이 저장 영상으로 pose 상태 전환을 확인하는 개발 도구.

환경 변수:
    POSE_TEST_VIDEO_PATH=절대 또는 프로젝트 기준 영상 경로
    POSE_TEST_EXERCISE=PUSHUP | SHOULDER_PRESS | SQUAT
    POSE_TEST_LOOP=false  # true일 때만 영상 끝에서 처음으로 이동
    POSE_DEBUG=true       # 상세 디버그 결과 포함

환경 변수가 비어 있으면 웹캠을 대신 열지 않고 명시적으로 종료한다.
운영 웹 화면의 기본 입력은 기존 브라우저 카메라 그대로 유지된다.
"""

import json
import os
from pathlib import Path

import cv2

from backend.pose_factory import create_pose_analyzers, get_pose_analyzer


def _flag(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


def run_video_test() -> int:
    video_value = os.getenv("POSE_TEST_VIDEO_PATH", "").strip()
    if not video_value:
        print("POSE_TEST_VIDEO_PATH가 비어 있어 영상 테스트를 실행하지 않습니다.")
        return 0

    video_path = Path(video_value).expanduser().resolve()
    if not video_path.is_file():
        print(f"테스트 영상을 찾을 수 없습니다: {video_path}")
        return 2

    exercise_code = os.getenv("POSE_TEST_EXERCISE", "PUSHUP").strip().upper()
    analyzers = create_pose_analyzers()
    try:
        analyzer = get_pose_analyzer(analyzers, exercise_code)
    except KeyError:
        print(f"지원하지 않는 운동 코드입니다: {exercise_code}")
        return 2

    capture = cv2.VideoCapture(str(video_path))
    if not capture.isOpened():
        print(f"테스트 영상을 열 수 없습니다: {video_path}")
        return 2

    loop_video = _flag("POSE_TEST_LOOP")
    frame_number = 0
    frames_in_pass = 0
    previous_count = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                if loop_video:
                    if frames_in_pass == 0:
                        print("영상에서 분석 가능한 프레임을 읽지 못해 종료합니다.")
                        break
                    capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    frames_in_pass = 0
                    continue
                print("영상 끝에 도달해 분석을 종료합니다.")
                break

            frame_number += 1
            frames_in_pass += 1
            _, status = analyzer.process_frame(frame)
            count = int(status.get("count", 0))
            if _flag("POSE_DEBUG") or count != previous_count:
                print(
                    json.dumps(
                        {
                            "frame": frame_number,
                            "exercise_code": exercise_code,
                            "count": count,
                            "stage": status.get("stage"),
                            "angles": status.get("angles", {}),
                            "feedback": status.get("feedback"),
                            "debug": status.get("debug", {}),
                        },
                        ensure_ascii=False,
                    )
                )
            previous_count = count
    finally:
        capture.release()
    return 0


if __name__ == "__main__":
    raise SystemExit(run_video_test())
