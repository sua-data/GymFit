import cv2
import numpy as np

from PIL import Image, ImageDraw, ImageFont
from squat_pose import SquatAnalyzer


def put_korean_text(
    frame,
    text,
    position,
    font,
    color=(255, 255, 255),
):
    """OpenCV 화면에 한글을 출력합니다."""
    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    pil_image = Image.fromarray(rgb_image)

    draw = ImageDraw.Draw(pil_image)

    draw.text(
        position,
        text,
        font=font,
        fill=color,
    )

    return cv2.cvtColor(
        np.array(pil_image),
        cv2.COLOR_RGB2BGR,
    )


FONT_PATH = "C:/Windows/Fonts/malgun.ttf"

font_small = ImageFont.truetype(FONT_PATH, 22)
font_medium = ImageFont.truetype(FONT_PATH, 28)
font_large = ImageFont.truetype(FONT_PATH, 38)


analyzer = SquatAnalyzer()

cap = cv2.VideoCapture(0)

if not cap.isOpened():
    raise RuntimeError("웹캠을 열 수 없습니다.")


while True:
    ret, frame = cap.read()

    if not ret:
        break

    frame, status = analyzer.process_frame(frame)

    if status["pose_valid"]:
        status_color = (0, 255, 0)

    elif status["person_valid"]:
        status_color = (255, 220, 0)

    else:
        status_color = (255, 80, 80)

    left_text = (
        f'왼쪽 무릎: {int(status["left_angle"])}도'
        if status["left_angle"] is not None
        else "왼쪽 무릎: -"
    )

    right_text = (
        f'오른쪽 무릎: {int(status["right_angle"])}도'
        if status["right_angle"] is not None
        else "오른쪽 무릎: -"
    )

    average_text = (
        f'평균 각도: {int(status["average_angle"])}도'
        if status["average_angle"] is not None
        else "평균 각도: -"
    )

    depth_text = (
        f'직전 깊이: {int(status["last_depth"])}도'
        if status["last_depth"] is not None
        else "직전 깊이: -"
    )

    frame = put_korean_text(
        frame,
        status["status_text"],
        (20, 20),
        font_medium,
        status_color,
    )

    frame = put_korean_text(
        frame,
        left_text,
        (20, 60),
        font_small,
        (0, 255, 0),
    )

    frame = put_korean_text(
        frame,
        right_text,
        (20, 92),
        font_small,
        (0, 255, 0),
    )

    frame = put_korean_text(
        frame,
        average_text,
        (20, 124),
        font_small,
        (255, 255, 0),
    )

    frame = put_korean_text(
        frame,
        depth_text,
        (20, 156),
        font_small,
        (255, 255, 0),
    )

    frame = put_korean_text(
        frame,
        f'횟수: {status["count"]}회',
        (20, 200),
        font_large,
        (255, 255, 0),
    )

    frame = put_korean_text(
        frame,
        f'현재 상태: {status["stage_text"]}',
        (20, 250),
        font_medium,
        (0, 255, 255),
    )

    frame = put_korean_text(
        frame,
        f'피드백: {status["feedback"]}',
        (20, 292),
        font_medium,
        (255, 180, 0),
    )

    frame = put_korean_text(
        frame,
        "종료하려면 Q 키를 누르세요",
        (20, frame.shape[0] - 40),
        font_small,
        (255, 255, 255),
    )

    cv2.imshow(
        "GYMFIT 스쿼트 자세 코칭",
        frame,
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    # R 키로 횟수와 상태 초기화
    if key == ord("r"):
        analyzer.reset()


cap.release()
cv2.destroyAllWindows()