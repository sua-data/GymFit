from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_received_jpeg_is_saved_only_behind_pose_debug():
    source = (PROJECT_ROOT / "backend/routers/coaching.py").read_text(
        encoding="utf-8"
    )

    assert "pose_debug_enabled()" in source
    assert '"debug"\n                        / "pushup_received_frame.jpg"' in source
    assert "write_bytes(uploaded_jpeg)" in source
    assert '"upload_bytes": len(uploaded_jpeg)' in source
    assert '"shape": list(frame.shape)' in source


def test_pushup_raw_yolo_logging_precedes_person_postprocessing():
    source = (PROJECT_ROOT / "backend/pushup_pose.py").read_text(encoding="utf-8")

    model_call = source.index("results = list(self.model(")
    raw_log = source.index("self._debug_raw_yolo_results", model_call)
    selection = source.index("select_reference_person(", raw_log)
    assert model_call < raw_log < selection
    assert '"classes_filter": None' in source
    assert '"raw_box_count": total_boxes' in source
    assert '"raw_box_confidences": raw_box_confidences' in source
    assert "classes=[0]" not in source
    assert '"valid-frame-no-detection"' in source


def test_standalone_confidence_and_filter_ab_comparison_exists():
    source = (PROJECT_ROOT / "backend/pushup_yolo_debug.py").read_text(
        encoding="utf-8"
    )

    assert "for confidence in (0.5, 0.35, 0.25)" in source
    assert "legacy_brightness_contrast_approx" in source
    assert 'source=str(args.input), conf=confidence' in source
    assert 'cv2.imwrite(str(args.output), rendered)' in source
    assert 'pushup_yolo_result.jpg' in source
