from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def coaching_source():
    return (PROJECT_ROOT / "frontend/js/coaching.js").read_text(encoding="utf-8")


def test_pushup_orientation_requires_mobile_touch_and_portrait():
    source = coaching_source()

    assert 'window.matchMedia?.("(pointer: coarse)")' in source
    assert "navigator.maxTouchPoints" in source
    assert "mobileUserAgent || iPadDesktopMode" in source
    assert "window.innerHeight > window.innerWidth" in source
    assert 'selectedExerciseCode === "PUSHUP"' in source


def test_portrait_pushup_is_advisory_and_never_gates_analysis():
    source = coaching_source()

    assert "shouldShowPushupPortraitAdvisory()" in source
    policy_start = source.index("function updatePushupOrientationAdvisory()")
    policy_end = source.index(
        "function scheduleOrientationAdvisoryUpdate", policy_start
    )
    policy_source = source[policy_start:policy_end]
    assert "stopPoseAnalysis" not in policy_source
    assert "startPoseAnalysis" not in policy_source
    assert "clearPoseOverlay" not in policy_source
    assert "isPushupPortraitBlocked" not in source
    send_start = source.index("async function sendFrameForAnalysis()")
    send_end = source.index("function startPoseAnalysis()", send_start)
    assert "shouldShowPushupPortraitAdvisory" not in source[send_start:send_end]


def test_orientation_listeners_only_update_ui_and_are_cleaned_up():
    source = coaching_source()

    assert 'window.addEventListener("orientationchange"' in source
    assert 'window.addEventListener("resize"' in source
    assert 'window.removeEventListener("orientationchange"' in source
    assert 'window.removeEventListener("resize"' in source
    assert "screen.orientation.lock" not in source
    assert "screen.orientation.unlock" not in source
    assert "detachOrientationListeners();" in source


def test_orientation_guide_and_landscape_layout_exist():
    html = (PROJECT_ROOT / "frontend/coaching.html").read_text(encoding="utf-8")
    css = (PROJECT_ROOT / "frontend/css/coaching.css").read_text(encoding="utf-8")

    assert 'id="pushupOrientationGuide"' in html
    assert "가로 촬영을 권장합니다" in html
    assert "전신이 잘리지 않도록 휴대폰을 멀리 배치하세요" in html
    assert ".pushup-orientation-guide[hidden]" in css
    assert "body.coaching-active.pushup-landscape-mode" in css
    assert "env(safe-area-inset-bottom)" in css
