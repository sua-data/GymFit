import base64
from pathlib import Path

import cv2
import numpy as np

from backend.routers import workout


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def encode_capture_frame(frame):
    encoded, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 82])
    assert encoded
    return "data:image/jpeg;base64," + base64.b64encode(buffer).decode("ascii")


def test_backend_capture_is_a_nonempty_jpeg_data_url():
    best_frame = np.full((12, 12, 3), (10, 40, 220), dtype=np.uint8)

    image = encode_capture_frame(best_frame)

    assert image.startswith("data:image/jpeg;base64,")
    assert len(image) > len("data:image/jpeg;base64,")


def test_frontend_backend_capture_branch_never_reads_canvas():
    source = (PROJECT_ROOT / "frontend/js/coaching.js").read_text(encoding="utf-8")
    register_start = source.index("function registerRepetition(")
    register_end = source.index("function getPostureScoreFromStatus", register_start)
    register_source = source[register_start:register_end]

    assert "captureCanvas" not in register_source
    assert "captureImage || fallbackImage" in register_source
    assert '"backend-best-pose"' in source
    assert '"frontend-current-frame-fallback"' in source
    assert '["SQUAT", "PUSHUP"].includes(selectedExerciseCode)' in source
    assert "? null\n      : submittedFrameDataUrl" in source
    assert "completedCapture?.image" in source


def test_final_save_payload_uses_selected_repetition_capture():
    source = (PROJECT_ROOT / "frontend/js/coaching.js").read_text(encoding="utf-8")

    assert "bestPostureImageDataUrl = selectedImage" in source
    assert "best_image_data_url:\n            bestPostureImageDataUrl" in source


def test_final_file_bytes_come_from_backend_best_frame(monkeypatch, tmp_path):
    best_frame = np.full((12, 12, 3), (10, 40, 220), dtype=np.uint8)
    completion_frame = np.full((12, 12, 3), (220, 40, 10), dtype=np.uint8)
    best_image = encode_capture_frame(best_frame)
    completion_image = encode_capture_frame(completion_frame)
    monkeypatch.setattr(workout, "CAPTURE_DIR", tmp_path)

    _, saved_path = workout.save_representative_capture(best_image, user_id=7)

    expected = base64.b64decode(best_image.split(",", 1)[1])
    wrong = base64.b64decode(completion_image.split(",", 1)[1])
    assert saved_path.read_bytes() == expected
    assert saved_path.read_bytes() != wrong
