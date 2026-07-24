from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_prepare_screen_has_no_intensity_and_completion_step_has_no_default():
    html = (
        PROJECT_ROOT / "frontend" / "coaching.html"
    ).read_text(encoding="utf-8")
    prepare_start = html.index('class="coaching-prepare-controls"')
    prepare_end = html.index("</section>", prepare_start)
    prepare_markup = html[prepare_start:prepare_end]
    intensity_start = html.index('id="workoutIntensityStep"')
    intensity_end = html.index("</section>", intensity_start)
    intensity_markup = html[intensity_start:intensity_end]

    assert 'name="exerciseIntensity"' not in prepare_markup
    assert 'name="completedExerciseIntensity"' in intensity_markup
    assert 'value="LOW"' in intensity_markup
    assert 'value="MODERATE"' in intensity_markup
    assert 'value="HIGH"' in intensity_markup
    assert " checked" not in intensity_markup
    assert 'id="saveWorkoutButton" disabled' in intensity_markup


def test_prepare_screen_has_no_standalone_weight_card():
    html = (
        PROJECT_ROOT / "frontend" / "coaching.html"
    ).read_text(encoding="utf-8")
    css = (
        PROJECT_ROOT / "frontend" / "css" / "coaching.css"
    ).read_text(encoding="utf-8")
    source = (
        PROJECT_ROOT / "frontend" / "js" / "coaching.js"
    ).read_text(encoding="utf-8")

    assert 'id="workoutWeightKg"' not in html
    assert "workout-weight-input" not in html
    assert "calorie-inputs" not in html
    assert ".workout-weight-input" not in css
    assert ".calorie-inputs" not in css
    assert 'document.querySelector("#workoutWeightKg")' not in source
    assert 'document.querySelector(".workout-weight-input")' not in source
    assert "return normalizeRecordWeightKg(coachingSets[0]?.weight_kg);" in source


def test_save_payload_requires_selected_completed_intensity():
    source = (
        PROJECT_ROOT / "frontend" / "js" / "coaching.js"
    ).read_text(encoding="utf-8")

    assert "exercise_intensity:\n            selectedWorkoutIntensity" in source
    assert 'input[name="exerciseIntensity"]' not in source
    assert "체감 운동 강도를 선택해 주세요." in source
    assert "showWorkoutIntensityStep();" in source
    assert source.index("showWorkoutIntensityStep();") < source.index(
        "savedWorkoutResult = await saveWorkoutRecord();"
    )


def test_zero_repetition_branch_skips_intensity_step_and_record_save():
    source = (
        PROJECT_ROOT / "frontend" / "js" / "coaching.js"
    ).read_text(encoding="utf-8")
    finish_start = source.index("async function finishWorkout()")
    zero_branch = source.index(
        "if (getTotalRepetitions() <= 0)",
        finish_start,
    )
    zero_return = source.index("return;", zero_branch)
    zero_source = source[zero_branch:zero_return]

    assert "showWorkoutResult({ noRepetitions: true });" in zero_source
    assert "showWorkoutIntensityStep()" not in zero_source
    assert "saveWorkoutRecord()" not in zero_source


def test_save_click_is_guarded_against_duplicate_requests():
    source = (
        PROJECT_ROOT / "frontend" / "js" / "coaching.js"
    ).read_text(encoding="utf-8")
    listener_start = source.index(
        'saveWorkoutButton.addEventListener("click"'
    )
    listener_end = source.index(
        "resultDashboardButton.addEventListener",
        listener_start,
    )
    listener_source = source[listener_start:listener_end]

    assert "isSavingWorkout" in listener_source
    assert "workoutRecordSaved" in listener_source
    assert "await finishWorkout();" in listener_source
