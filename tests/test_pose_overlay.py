from pathlib import Path
from types import SimpleNamespace

import numpy as np

from backend.squat_pose import SquatAnalyzer


def analyzer_without_model():
    analyzer = SquatAnalyzer.__new__(SquatAnalyzer)
    analyzer.min_keypoint_conf = 0.35
    analyzer.overlay_min_keypoint_conf = 0.30
    return analyzer


def test_pose_overlay_filters_confidence_and_out_of_frame_coordinates():
    analyzer = analyzer_without_model()
    coordinates = np.full((1, 17, 2), 20.0, dtype=float)
    confidences = np.full((1, 17), 0.9, dtype=float)
    confidences[0, 7] = 0.2
    coordinates[0, 8] = (-1, 20)
    coordinates[0, 9] = (101, 20)
    result = SimpleNamespace(
        keypoints=SimpleNamespace(xy=coordinates, conf=confidences),
        boxes=SimpleNamespace(
            xyxy=np.array([[5, 5, 95, 195]], dtype=float),
            conf=np.array([0.9], dtype=float),
        ),
    )

    overlay = analyzer._build_pose_overlay(
        result, 0, 100, 200, left_angle=100, right_angle=None
    )

    ids = {point["id"] for point in overlay["keypoints"]}
    assert overlay["source_width"] == 100
    assert overlay["source_height"] == 200
    assert overlay["selected_side"] == "LEFT"
    assert 7 not in ids
    assert 8 not in ids
    assert 9 not in ids
    assert 5 in ids and 11 in ids and 13 in ids and 15 in ids


def test_pose_overlay_reuses_both_analyzed_legs():
    analyzer = analyzer_without_model()
    result = SimpleNamespace(keypoints=SimpleNamespace(
        xy=np.full((1, 17, 2), 30.0, dtype=float),
        conf=np.full((1, 17), 0.8, dtype=float),
    ), boxes=SimpleNamespace(
        xyxy=np.array([[5, 5, 95, 195]], dtype=float),
        conf=np.array([0.8], dtype=float),
    ))

    overlay = analyzer._build_pose_overlay(
        result, 0, 100, 200, left_angle=98, right_angle=102
    )

    assert overlay["selected_side"] == "BOTH"


def test_backend_overlay_includes_selected_person_bbox():
    analyzer = analyzer_without_model()
    frame = np.zeros((200, 100, 3), dtype=np.uint8)
    coordinates = np.full((1, 17, 2), 30.0, dtype=float)
    coordinates[0, :, 1] = np.linspace(20, 180, 17)
    result = SimpleNamespace(
        keypoints=SimpleNamespace(
            xy=coordinates,
            conf=np.full((1, 17), 0.9, dtype=float),
        ),
        boxes=SimpleNamespace(
            xyxy=np.array([[10, 10, 90, 190]], dtype=float),
            conf=np.array([0.87], dtype=float),
        ),
    )

    overlay = analyzer._build_pose_overlay(
        result, 0, 100, 200, left_angle=100, right_angle=102
    )

    assert np.count_nonzero(frame) == 0
    assert overlay["bbox"] == {
        "x1": 10.0,
        "y1": 10.0,
        "x2": 90.0,
        "y2": 190.0,
        "confidence": 0.87,
    }


def test_frontend_uses_cover_crop_mirror_and_rejects_old_frame_ids():
    source = (Path(__file__).resolve().parents[1] / "frontend/js/coaching.js").read_text(
        encoding="utf-8"
    )

    assert 'formData.append("frame_id", String(requestFrameId))' in source
    assert "frameId < latestAnnotatedResponseId" in source
    assert "const coverScale = Math.max(" in source
    assert "const offsetX = (viewWidth - sourceWidth * coverScale) / 2" in source
    assert "const offsetY = (viewHeight - sourceHeight * coverScale) / 2" in source
    assert "x: viewWidth - coveredX" in source
    assert "drawLivePoseOverlay(data);" in source
    assert "drawPoseOverlay(data);" not in source
    assert "}, 700);" in source
    assert (
        "!status.person_detected || !sourceWidth || !sourceHeight"
        in source
    )
    assert "!status.pose_valid || !sourceWidth" not in source

def test_pose_analysis_uses_single_request_continuous_loop():
    source = (Path(__file__).resolve().parents[1] / "frontend/js/coaching.js").read_text(
        encoding="utf-8"
    )

    assert "const ANALYSIS_LOOP_DELAY_MS = 80" in source
    assert "const ANALYSIS_INPUT_WIDTH = 480" in source
    assert "const ANALYSIS_JPEG_QUALITY = 0.75" in source
    assert "analysisInProgress = true" in source
    assert "analysisInProgress = false" in source
    assert "window.setTimeout(\n        sendFrameForAnalysis" in source
    assert "window.setInterval(\n      sendFrameForAnalysis" not in source
    assert 'console.log("[pose performance]"' not in source
    assert "average_inference_ms" not in source
    assert "average_round_trip_ms" not in source
    assert "analyses_per_second" not in source
    assert 'brightnessCanvas.width = 32' in source
    assert 'brightness(1.12) contrast(1.08)' not in source
    assert 'captureContext.filter = "none"' in source
    assert "sourceWidth,\n      sourceHeight,\n      0,\n      0," in source
    assert 'formData.append("frame_mean_brightness"' in source
    assert "brightness_adjusted" in source


def test_overlay_confidence_is_separate_from_analysis_confidence():
    analyzer = analyzer_without_model()

    assert analyzer.min_keypoint_conf == 0.35
    assert analyzer.overlay_min_keypoint_conf == 0.30
