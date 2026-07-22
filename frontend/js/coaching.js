const exerciseTabs =
  document.querySelectorAll(
    ".exercise-tab"
  );

const cameraVideo =
  document.querySelector(
    "#cameraVideo"
  );

const poseCanvas =
  document.querySelector(
    "#poseCanvas"
  );

const cameraPlaceholder =
  document.querySelector(
    "#cameraPlaceholder"
  );

const movementState =
  document.querySelector(
    "#movementState"
  );

const currentRepCount =
  document.querySelector(
    "#currentRepCount"
  );

const targetRepCount =
  document.querySelector(
    "#targetRepCount"
  );

const currentSetCount =
  document.querySelector(
    "#currentSetCount"
  );

const targetSetCount =
  document.querySelector(
    "#targetSetCount"
  );

const postureScoreValue =
  document.querySelector(
    "#postureScoreValue"
  );

const postureStatus =
  document.querySelector(
    "#postureStatus"
  );

const feedbackTitle =
  document.querySelector(
    "#feedbackTitle"
  );

const feedbackText =
  document.querySelector(
    "#feedbackText"
  );

const startButton =
  document.querySelector(
    "#startButton"
  );

const finishButton =
  document.querySelector(
    "#finishButton"
  );

const coachingSetCurrent =
  document.querySelector("#coachingSetCurrent");
const coachingSetTotal =
  document.querySelector("#coachingSetTotal");
const coachingSetWeight =
  document.querySelector("#coachingSetWeight");
const totalCompletedRepCount =
  document.querySelector("#totalCompletedRepCount");
const totalTargetRepCount =
  document.querySelector("#totalTargetRepCount");
const coachingModeLabel =
  document.querySelector("#coachingModeLabel");
const coachingPlanMeta =
  document.querySelector("#coachingPlanMeta");
const restCard =
  document.querySelector("#restCard");
const restTitle =
  document.querySelector("#restTitle");
const restTime =
  document.querySelector("#restTime");
const nextSetSummary =
  document.querySelector("#nextSetSummary");
const skipRestButton =
  document.querySelector("#skipRestButton");
const coachingSettingsEyebrow =
  document.querySelector("#coachingSettingsEyebrow");
const coachingSettingsTitle =
  document.querySelector("#coachingSettingsTitle");
const coachingSettingsMessage =
  document.querySelector("#coachingSettingsMessage");
const routineCoachingSets =
  document.querySelector("#routineCoachingSets");
const restPresetButtons =
  document.querySelectorAll("[data-rest-seconds]");
const customRestSeconds =
  document.querySelector("#customRestSeconds");
const coachingModeLoading =
  document.querySelector("#coachingModeLoading");
const coachingSettingsCard =
  document.querySelector("#coachingSettingsCard");
const freeCoachingSettings =
  document.querySelector("#freeCoachingSettings");
const freeCoachingSetList =
  document.querySelector("#freeCoachingSetList");
const freeSetAddButton =
  document.querySelector("#freeSetAddButton");
const setProgressCard =
  document.querySelector("#setProgressCard");
const pauseButton =
  document.querySelector("#pauseButton");
const voiceToggleButton =
  document.querySelector("#voiceToggleButton");
const overlayCurrentSet =
  document.querySelector("#overlayCurrentSet");
const overlayTargetSets =
  document.querySelector("#overlayTargetSets");
const overlayCurrentReps =
  document.querySelector("#overlayCurrentReps");
const overlayTargetReps =
  document.querySelector("#overlayTargetReps");
const overlayRepCount =
  document.querySelector("#overlayRepCount");
const overlayMovementState =
  document.querySelector("#overlayMovementState");
const overlayFeedbackText =
  document.querySelector("#overlayFeedbackText");
const coachingResult =
  document.querySelector("#coachingResult");
const resultExerciseName =
  document.querySelector("#resultExerciseName");
const resultRepetitions =
  document.querySelector("#resultRepetitions");
const resultSets =
  document.querySelector("#resultSets");
const resultPostureScore =
  document.querySelector("#resultPostureScore");
const resultWorkoutMinutes =
  document.querySelector("#resultWorkoutMinutes");
const resultCalories =
  document.querySelector("#resultCalories");
const resultFeedbackTitle =
  document.querySelector("#resultFeedbackTitle");
const resultFeedbackText =
  document.querySelector("#resultFeedbackText");
const resultDashboardButton =
  document.querySelector("#resultDashboardButton");


let selectedExerciseCode =
  "SQUAT";

let selectedExerciseName =
  "스쿼트";

let targetReps = 10;
let targetSets = 3;

let currentReps = 0;
let currentSets = 0;
let coachingSets = [];
let currentSetIndex = 0;
let totalTargetReps = 0;
let totalCompletedReps = 0;
let isCurrentSetCompleted = false;
let isResting = false;
let isWorkoutFinished = false;
let isSavingWorkout = false;
let workoutRecordSaved = false;
let savedWorkoutResult = null;
let isResultDisplayed = false;
let restIntervalId = null;
let restSecondsRemaining = 0;
let restDurationSeconds = 60;
let coachingWorkoutPlanId = null;
let isPlanCoaching = false;
let coachingEstimatedMinutes = 0;
let freeCoachingRows = [];
let todayCoachingPlans = [];
let coachingModeRequestId = 0;
let isWorkoutPaused = false;
let isVoiceEnabled = true;
let lastSpokenFeedback = "";
let lastFeedbackSpokenAt = 0;

let postureScores = [];

let workoutStartedAt = null;
let cameraStream = null;

let isWorkoutActive = false;
let isGoalCompleted = false;

let analysisTimer = null;
let analysisInProgress = false;
let lastServerCount = 0;

const captureCanvas =
  document.createElement("canvas");

const captureContext =
  captureCanvas.getContext(
    "2d"
  );

const ANALYSIS_INTERVAL_MS = 350;
const COACHING_REST_STORAGE_KEY =
  "gymfitCoachingRestSeconds";
const FREE_COACHING_SETS_STORAGE_KEY =
  "gymfitFreeCoachingSets";
const COACHING_VOICE_STORAGE_KEY =
  "gymfitCoachingVoiceEnabled";
const FEEDBACK_SPEECH_COOLDOWN_MS = 3000;


/* =========================
   로그인 사용자
========================= */

function getLoginUserId() {
  const savedUser =
    sessionStorage.getItem(
      "gymfitUser"
    );

  if (!savedUser) {
    return null;
  }

  try {
    const user =
      JSON.parse(savedUser);

    return (
      user.user_id
      ?? user.userId
      ?? null
    );

  } catch {
    return null;
  }
}

function getCurrentCoachingSet() {
  return coachingSets[currentSetIndex] || null;
}

function formatSetWeight(weight) {
  const value = Number(weight || 0);
  return value > 0 ? `${value}kg` : "맨몸";
}

function createDefaultFreeCoachingSets() {
  return Array.from({ length: 3 }, (_, index) => ({
    set_order: index + 1,
    repetition_count: 10,
    weight_kg: 0,
  }));
}

function normalizeFreeCoachingSets(value) {
  if (!Array.isArray(value) || value.length < 1 || value.length > 20) {
    return null;
  }

  const normalized = value.map((set, index) => {
    const weight = set.weight_kg === "" ? 0 : Number(set.weight_kg);
    const repetitions = Number(set.repetition_count);

    if (
      !Number.isFinite(weight)
      || weight < 0
      || weight > 500
      || Math.round(weight * 10) !== weight * 10
      || !Number.isInteger(repetitions)
      || repetitions < 1
      || repetitions > 100
    ) {
      return null;
    }

    return {
      set_order: index + 1,
      weight_kg: weight,
      repetition_count: repetitions,
    };
  });

  return normalized.every(Boolean) ? normalized : null;
}

function saveFreeCoachingSets() {
  sessionStorage.setItem(
    FREE_COACHING_SETS_STORAGE_KEY,
    JSON.stringify(freeCoachingRows)
  );
}

function restoreFreeCoachingSets() {
  const savedValue = sessionStorage.getItem(
    FREE_COACHING_SETS_STORAGE_KEY
  );

  if (!savedValue) {
    freeCoachingRows = createDefaultFreeCoachingSets();
    return;
  }

  try {
    const normalized = normalizeFreeCoachingSets(JSON.parse(savedValue));
    if (!normalized) {
      throw new Error("Invalid free coaching sets");
    }
    freeCoachingRows = normalized;
  } catch {
    sessionStorage.removeItem(FREE_COACHING_SETS_STORAGE_KEY);
    freeCoachingRows = createDefaultFreeCoachingSets();
  }
}

function stopSpeech() {
  if ("speechSynthesis" in window) {
    window.speechSynthesis.cancel();
  }
}

function updateVoiceButton() {
  voiceToggleButton.textContent = isVoiceEnabled
    ? "음성 ON"
    : "음성 OFF";
  voiceToggleButton.setAttribute(
    "aria-pressed",
    String(isVoiceEnabled)
  );
}

function restoreVoiceSetting() {
  isVoiceEnabled = sessionStorage.getItem(
    COACHING_VOICE_STORAGE_KEY
  ) !== "false";
  updateVoiceButton();
}

function speakText(text) {
  if (
    !isVoiceEnabled
    || !text
    || !("speechSynthesis" in window)
    || !("SpeechSynthesisUtterance" in window)
  ) {
    return;
  }

  stopSpeech();
  const utterance = new SpeechSynthesisUtterance(String(text));
  utterance.lang = "ko-KR";
  utterance.rate = 1;
  utterance.pitch = 1;
  window.speechSynthesis.speak(utterance);
}

function speakPostureFeedback(text) {
  const normalizedText = String(text || "").trim();
  const now = Date.now();
  if (
    !normalizedText
    || (
      normalizedText === lastSpokenFeedback
      && now - lastFeedbackSpokenAt < FEEDBACK_SPEECH_COOLDOWN_MS
    )
    || now - lastFeedbackSpokenAt < FEEDBACK_SPEECH_COOLDOWN_MS
  ) {
    return;
  }

  lastSpokenFeedback = normalizedText;
  lastFeedbackSpokenAt = now;
  speakText(normalizedText);
}

function updateWorkoutOverlay() {
  const currentSet = getCurrentCoachingSet();
  const currentTarget = Number(currentSet?.repetition_count || targetReps);
  const visibleSetNumber = Math.min(
    currentSetIndex + 1,
    coachingSets.length || 1
  );

  overlayCurrentSet.textContent = String(visibleSetNumber);
  overlayTargetSets.textContent = String(coachingSets.length || targetSets);
  overlayCurrentReps.textContent = String(currentReps);
  overlayTargetReps.textContent = String(currentTarget);
  overlayRepCount.textContent = String(currentReps);
}

function setOverlayMovement(text) {
  overlayMovementState.textContent = text || "준비";
}

function setOverlayFeedback(text) {
  overlayFeedbackText.textContent = text || "자세를 확인하고 있습니다.";
}

function getMovementCue(status) {
  if (!status?.stage) {
    return "준비";
  }

  if (selectedExerciseCode === "SHOULDER_PRESS") {
    return status.stage === "UP"
      ? "내려오세요"
      : "올려주세요";
  }

  return status.stage === "DOWN"
    ? "올라오세요"
    : "내려가세요";
}

function readFreeCoachingRowsFromInputs() {
  return Array.from(
    freeCoachingSetList.querySelectorAll(".free-coaching-set-row")
  ).map((row, index) => ({
    set_order: index + 1,
    weight_kg: row.querySelector("[data-free-weight]").value,
    repetition_count: row.querySelector("[data-free-reps]").value,
  }));
}

function renderFreeCoachingRows() {
  freeCoachingSetList.innerHTML = freeCoachingRows
    .map(
      (set, index) => `
        <div class="free-coaching-set-row" data-free-set-index="${index}">
          <strong class="free-coaching-set-order">${index + 1}세트</strong>
          <div class="free-coaching-set-field">
            <span>중량</span>
            <label>
              <input
                type="number"
                min="0"
                max="500"
                step="0.1"
                inputmode="decimal"
                value="${Number(set.weight_kg || 0)}"
                data-free-weight
                aria-label="${index + 1}세트 중량"
              >
              <b>kg</b>
            </label>
          </div>
          <div class="free-coaching-set-field">
            <span>반복</span>
            <label>
              <input
                type="number"
                min="1"
                max="100"
                step="1"
                inputmode="numeric"
                value="${Number(set.repetition_count)}"
                data-free-reps
                aria-label="${index + 1}세트 반복 횟수"
              >
              <b>회</b>
            </label>
          </div>
          <button
            type="button"
            class="free-set-delete-button"
            data-free-set-delete="${index}"
            aria-label="${index + 1}세트 삭제"
            ${freeCoachingRows.length === 1 ? "disabled" : ""}
          >×</button>
        </div>
      `
    )
    .join("");

  freeSetAddButton.disabled = freeCoachingRows.length >= 20;
}

function setFreeCoachingInputsDisabled(disabled) {
  freeCoachingSetList.querySelectorAll("input, button").forEach((element) => {
    element.disabled = disabled
      || (
        element.matches("[data-free-set-delete]")
        && freeCoachingRows.length === 1
      );
  });
  freeSetAddButton.disabled = disabled || freeCoachingRows.length >= 20;
}

function validateFreeCoachingSets() {
  const rows = readFreeCoachingRowsFromInputs();
  const normalized = normalizeFreeCoachingSets(rows);

  if (!normalized) {
    const invalidIndex = rows.findIndex((set) => {
      const weight = set.weight_kg === "" ? 0 : Number(set.weight_kg);
      const repetitions = Number(set.repetition_count);
      return (
        !Number.isFinite(weight)
        || weight < 0
        || weight > 500
        || Math.round(weight * 10) !== weight * 10
        || !Number.isInteger(repetitions)
        || repetitions < 1
        || repetitions > 100
      );
    });
    setSettingsMessage(
      `${Math.max(0, invalidIndex) + 1}세트의 중량은 0~500kg(소수 첫째 자리), 반복은 1~100회로 입력해 주세요.`
    );
    return null;
  }

  freeCoachingRows = normalized;
  saveFreeCoachingSets();
  return normalized.map((set) => ({
    ...set,
    duration_seconds: null,
  }));
}

function getValidCoachingPlan(plan, expectedExerciseCode = null) {
  const exerciseCode = String(plan?.exercise_code || "").toUpperCase();
  if (
    !plan
    || !isCoachingExerciseCode(exerciseCode)
    || (
      expectedExerciseCode
      && exerciseCode !== expectedExerciseCode
    )
    || !plan.workout_plan_id
    || !Array.isArray(plan.sets)
  ) {
    return null;
  }

  const sets = plan.sets
    .filter((set) => Number(set.repetition_count || 0) > 0)
    .sort(
      (first, second) =>
        Number(first.set_order) - Number(second.set_order)
    );

  return sets.length
    ? {
        ...plan,
        exercise_code: exerciseCode,
        sets,
      }
    : null;
}

function finishModeLoading() {
  coachingModeLoading.hidden = true;
  coachingSettingsCard.hidden = false;
  setProgressCard.hidden = false;
  startButton.disabled = false;
}

function setSettingsMessage(message = "") {
  coachingSettingsMessage.textContent = message;
}

function updateRestSettingUi() {
  restPresetButtons.forEach((button) => {
    button.classList.toggle(
      "active",
      Number(button.dataset.restSeconds) === restDurationSeconds
    );
  });
  customRestSeconds.value = [0, 30, 60, 90].includes(
    restDurationSeconds
  )
    ? ""
    : String(restDurationSeconds);
}

function setRestDuration(value) {
  const seconds = Number(value);
  if (
    !Number.isInteger(seconds)
    || seconds < 0
    || seconds > 300
  ) {
    setSettingsMessage("휴식시간은 0~300초로 입력해 주세요.");
    return false;
  }

  restDurationSeconds = seconds;
  sessionStorage.setItem(
    COACHING_REST_STORAGE_KEY,
    String(restDurationSeconds)
  );
  setSettingsMessage();
  updateRestSettingUi();
  return true;
}

function restoreRestDuration() {
  const savedValue = sessionStorage.getItem(
    COACHING_REST_STORAGE_KEY
  );
  if (savedValue === null || !setRestDuration(savedValue)) {
    restDurationSeconds = 60;
    updateRestSettingUi();
  }
}

function renderRoutineCoachingSets() {
  routineCoachingSets.innerHTML = coachingSets
    .map(
      (set) => `
        <div class="routine-coaching-set">
          <strong>${Number(set.set_order)}세트</strong>
          <span>
            ${formatSetWeight(set.weight_kg)}
            × ${Number(set.repetition_count)}회
          </span>
        </div>
      `
    )
    .join("");
}

function applyDetailedCoachingPlan(plan) {
  const validPlan = getValidCoachingPlan(
    plan,
    selectedExerciseCode
  );

  if (!validPlan) {
    return false;
  }

  coachingSets = validPlan.sets;
  coachingWorkoutPlanId = validPlan.workout_plan_id;
  coachingEstimatedMinutes = Number(validPlan.estimated_minutes || 0);
  isPlanCoaching = coachingWorkoutPlanId !== null;
  selectedExerciseCode = validPlan.exercise_code;
  selectedExerciseName = validPlan.exercise_name
    || getExerciseAnalyzer(selectedExerciseCode)?.displayName
    || selectedExerciseCode;
  targetSets = coachingSets.length;
  targetReps = Number(coachingSets[0].repetition_count);
  totalTargetReps = coachingSets.reduce(
    (sum, set) => sum + Number(set.repetition_count || 0),
    0
  );

  freeCoachingSettings.hidden = true;
  coachingSettingsEyebrow.textContent = "TODAY ROUTINE";
  coachingSettingsTitle.textContent = `오늘의 ${selectedExerciseName}`;
  routineCoachingSets.hidden = false;
  renderRoutineCoachingSets();
  coachingModeLabel.textContent = isPlanCoaching
    ? "루틴 코칭"
    : "자유 코칭";
  coachingPlanMeta.textContent =
    `${selectedExerciseName} · ${
      coachingEstimatedMinutes > 0
        ? `예상 ${coachingEstimatedMinutes}분`
        : "시간 미설정"
    }`;
  return true;
}

function prepareFreeCoaching() {
  coachingSets = freeCoachingRows.map((set) => ({
    ...set,
    duration_seconds: null,
  }));
  coachingWorkoutPlanId = null;
  coachingEstimatedMinutes = 0;
  isPlanCoaching = false;
  freeCoachingSettings.hidden = false;
  renderFreeCoachingRows();
  coachingSettingsEyebrow.textContent = "FREE COACHING";
  coachingSettingsTitle.textContent = `${selectedExerciseName} 자유 코칭 설정`;
  routineCoachingSets.hidden = true;
  routineCoachingSets.innerHTML = "";
  targetSets = coachingSets.length;
  targetReps = Number(coachingSets[0].repetition_count);
  totalTargetReps = coachingSets.reduce(
    (sum, set) => sum + Number(set.repetition_count || 0),
    0
  );
  coachingModeLabel.textContent = "자유 코칭";
  coachingPlanMeta.textContent = `${selectedExerciseName} · 자유 코칭`;
}

function updateDetailedProgressDisplay() {
  const currentSet = getCurrentCoachingSet();
  const currentTarget = Number(currentSet?.repetition_count || targetReps);

  coachingSetCurrent.textContent = String(
    Math.min(currentSetIndex + 1, coachingSets.length || 1)
  );
  coachingSetTotal.textContent = String(coachingSets.length || targetSets);
  coachingSetWeight.textContent = formatSetWeight(currentSet?.weight_kg);
  currentRepCount.textContent = currentReps;
  targetRepCount.textContent = currentTarget;
  currentSetCount.textContent = currentSets;
  targetSetCount.textContent = coachingSets.length || targetSets;
  totalCompletedRepCount.textContent = totalCompletedReps;
  totalTargetRepCount.textContent = totalTargetReps;
  updateWorkoutOverlay();
}

function clearRestTimer() {
  if (restIntervalId !== null) {
    window.clearInterval(restIntervalId);
    restIntervalId = null;
  }
}

function formatRestTime(seconds) {
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${
    String(remainingSeconds).padStart(2, "0")
  }`;
}


/* =========================
   전달받은 운동 및 목표
========================= */

async function fetchTodayCoachingPlans() {
  const userId =
    getLoginUserId();

  if (!userId) {
    todayCoachingPlans = [];
    return "no-user";
  }

  try {
    const response =
      await fetch(
        `/api/workouts/plans/today/${userId}`
      );

    if (!response.ok) {
      todayCoachingPlans = [];
      return "error";
    }

    const data =
      await response.json();

    todayCoachingPlans = (data.items || []).filter(
      (item) =>
        item.ai_coaching_supported
        && getValidCoachingPlan(item)
    );
    return "loaded";

  } catch (error) {
    todayCoachingPlans = [];
    console.error(
      "오늘의 코칭 목표 조회 실패:",
      error
    );

    return "error";
  }
}

function selectExerciseTab(exerciseCode) {
  const targetTab = Array.from(exerciseTabs).find(
    (tab) => tab.dataset.exerciseCode === exerciseCode
  );
  if (!targetTab) {
    return false;
  }

  exerciseTabs.forEach((tab) => {
    tab.classList.toggle("active", tab === targetTab);
  });
  selectedExerciseCode = targetTab.dataset.exerciseCode;
  selectedExerciseName = targetTab.dataset.exerciseName;
  return true;
}

function applySelectedExerciseMode() {
  const selectedPlan = todayCoachingPlans.find(
    (plan) => plan.exercise_code === selectedExerciseCode
  );

  if (selectedPlan && applyDetailedCoachingPlan(selectedPlan)) {
    saveCoachingPlan(selectedPlan);
  } else {
    clearCoachingPlan();
    prepareFreeCoaching();
  }

  currentSetIndex = 0;
  currentReps = 0;
  currentSets = 0;
  totalCompletedReps = 0;
  setSettingsMessage();
  updateTargetDisplay();
  updateCounterDisplay();
}

async function changeSelectedExercise(exerciseCode) {
  if (isWorkoutActive || !selectExerciseTab(exerciseCode)) {
    return;
  }

  const requestId = ++coachingModeRequestId;
  startButton.disabled = true;
  coachingSettingsCard.hidden = true;
  setProgressCard.hidden = true;
  coachingModeLoading.hidden = false;
  coachingModeLoading.textContent =
    `${selectedExerciseName}의 오늘 계획을 확인하고 있습니다.`;

  const result = await fetchTodayCoachingPlans();
  if (requestId !== coachingModeRequestId) {
    return;
  }

  applySelectedExerciseMode();
  if (result === "error") {
    setSettingsMessage(
      "오늘의 운동 계획을 불러오지 못해 자유 코칭으로 시작합니다."
    );
  }
  finishModeLoading();
  movementState.textContent = `${selectedExerciseName} 준비`;
}


/* =========================
   카메라 시작
========================= */

async function startCamera() {
  if (
    !navigator.mediaDevices
    || !navigator.mediaDevices
      .getUserMedia
  ) {
    throw new Error(
      "이 브라우저는 카메라를 지원하지 않습니다."
    );
  }

  cameraStream =
    await navigator.mediaDevices
      .getUserMedia({
        video: {
          facingMode: "user",
          width: {
            ideal: 720
          },
          height: {
            ideal: 960
          }
        },
        audio: false
      });

  cameraVideo.srcObject =
    cameraStream;

  cameraPlaceholder.style.display =
    "none";
}


/* =========================
   카메라 종료
========================= */

function stopCamera() {
  stopPoseAnalysis();
  stopSpeech();

  if (!cameraStream) {
    return;
  }

  cameraStream
    .getTracks()
    .forEach(
      (track) => track.stop()
    );

  cameraStream = null;
  cameraVideo.srcObject = null;
}


/* =========================
   화면 상태 갱신
========================= */

function updateTargetDisplay() {
  updateDetailedProgressDisplay();
}


function updateCounterDisplay() {
  updateDetailedProgressDisplay();
}


function updatePostureFeedback(
  score
) {
  postureScoreValue.textContent =
    score;

  if (score >= 90) {
    postureStatus.textContent =
      "GOOD";

    feedbackTitle.textContent =
      "자세가 안정적이에요.";

    feedbackText.textContent =
      "현재 관절 정렬과 운동 범위가 좋습니다.";

    return;
  }

  if (score >= 70) {
    postureStatus.textContent =
      "CHECK";

    feedbackTitle.textContent =
      "자세를 조금 조정해 주세요.";

    feedbackText.textContent =
      "동작 속도를 줄이고 관절 위치를 확인하세요.";

    return;
  }

  postureStatus.textContent =
    "WARNING";

  feedbackTitle.textContent =
    "잘못된 자세가 감지됐어요.";

  feedbackText.textContent =
    "현재 동작을 멈추고 시작 자세로 돌아가세요.";
}


/* =========================
   반복 횟수 처리
========================= */

function registerRepetition(
  score
) {
  if (
    !isWorkoutActive
    || isGoalCompleted
    || isCurrentSetCompleted
    || isResting
    || isWorkoutPaused
    || isWorkoutFinished
  ) {
    return;
  }

  const currentSet = getCurrentCoachingSet();
  const currentSetTargetReps = Number(
    currentSet?.repetition_count || 0
  );

  if (currentSetTargetReps <= 0) {
    return;
  }

  postureScores.push(score);

  currentReps += 1;
  totalCompletedReps += 1;

  movementState.textContent =
    `${currentSetIndex + 1}세트 ${currentReps}회`;
  setOverlayMovement("좋아요");

  updateCounterDisplay();
  updatePostureFeedback(score);

  if (currentReps >= currentSetTargetReps) {
    if (isCurrentSetCompleted) {
      return;
    }

    isCurrentSetCompleted = true;
    currentSets += 1;

    movementState.textContent =
      `${currentSets}세트 완료`;
    setOverlayMovement(`${currentSets}세트 완료`);
    speakText(`${currentReps}, ${currentSets}세트 완료`);

    if (currentSetIndex >= coachingSets.length - 1) {
      finishWorkoutAutomatically();
      return;
    }

    startRestPeriod();
    return;
  }

  speakText(String(currentReps));
}


function startRestPeriod() {
  clearRestTimer();
  stopPoseAnalysis();
  isResting = true;
  pauseButton.disabled = true;
  restSecondsRemaining = restDurationSeconds;

  if (restDurationSeconds === 0) {
    restCard.hidden = true;
    startNextSet();
    return;
  }

  restCard.hidden = false;
  restTitle.textContent = `${currentSetIndex + 1}세트 완료`;
  setOverlayFeedback(`${currentSetIndex + 1}세트 완료`);

  const nextSet = coachingSets[currentSetIndex + 1];
  nextSetSummary.textContent =
    `다음 세트: ${formatSetWeight(nextSet?.weight_kg)} × ${
      Number(nextSet?.repetition_count || 0)
    }회`;

  const updateRestDisplay = () => {
    restTime.textContent = formatRestTime(restSecondsRemaining);
  };

  updateRestDisplay();
  restIntervalId = window.setInterval(() => {
    restSecondsRemaining -= 1;
    updateRestDisplay();

    if (restSecondsRemaining <= 0) {
      startNextSet();
    }
  }, 1000);
}


async function startNextSet() {
  if (!isResting || isWorkoutFinished) {
    return;
  }

  clearRestTimer();
  currentSetIndex += 1;

  if (currentSetIndex >= coachingSets.length) {
    finishWorkoutAutomatically();
    return;
  }

  currentReps = 0;
  isCurrentSetCompleted = false;
  isResting = false;
  pauseButton.disabled = false;
  restCard.hidden = true;

  try {
    await resetCurrentExerciseAnalyzer();
  } catch (error) {
    console.error("다음 세트 분석 초기화 실패:", error);
  }

  movementState.textContent = `${currentSetIndex + 1}세트 준비`;
  setOverlayMovement("준비");
  feedbackTitle.textContent = "다음 세트를 시작합니다.";
  feedbackText.textContent =
    `${selectedExerciseName} 시작 자세를 준비해 주세요.`;
  setOverlayFeedback(feedbackText.textContent);
  updateCounterDisplay();
  startPoseAnalysis();
}


/* =========================
   스쿼트 분석 API
========================= */

function getPostureScoreFromStatus(
  status
) {
  const commonScore = Number(status.posture_score);
  if (Number.isFinite(commonScore)) {
    return Math.max(0, Math.min(100, Math.round(commonScore)));
  }

  if (!status.pose_valid) {
    return 0;
  }

  const depth =
    status.last_depth
    ?? status.average_angle;

  const torsoAngle =
    status.last_torso_angle
    ?? status.torso_angle;

  let score = 70;

  // 스쿼트 깊이 점수
  if (depth !== null) {
    if (depth < 100) {
      score = 95;

    } else if (depth <= 110) {
      score = 90;

    } else if (depth <= 125) {
      score = 75;

    } else {
      score = 65;
    }
  }

  // 상체 기울기 감점
  if (torsoAngle !== null) {
    if (torsoAngle >= 45) {
      score -= 20;

    } else if (torsoAngle >= 35) {
      score -= 10;
    }
  }

  return Math.max(
    0,
    Math.min(100, score)
  );
}


function applyPoseStatus(
  status
) {
  if (isWorkoutPaused) {
    return;
  }

  const serverCount =
    Number(status.count ?? 0);

  const repetitionDifference =
    Math.max(
      0,
      serverCount - lastServerCount
    );

  const score =
    getPostureScoreFromStatus(
      status
    );

  for (
    let index = 0;
    index < repetitionDifference;
    index += 1
  ) {
    registerRepetition(score);
  }

  lastServerCount =
    serverCount;

  if (
    !isWorkoutActive
    || isGoalCompleted
  ) {
    return;
  }

  if (status.pose_valid) {
    if (repetitionDifference === 0) {
      const movementCue = getMovementCue(status);
      movementState.textContent =
        `${selectedExerciseName} ${movementCue}`;
      setOverlayMovement(movementCue);
    }

    postureScoreValue.textContent =
      score;

    postureStatus.textContent =
      score >= 90
        ? "GOOD"
        : score >= 70
          ? "CHECK"
          : "WARNING";

    feedbackTitle.textContent =
      status.feedback
      || "자세를 분석하고 있습니다.";
    setOverlayFeedback(feedbackTitle.textContent);

    if (repetitionDifference === 0) {
      speakPostureFeedback(feedbackTitle.textContent);
    }

    const angleTexts = [];

    if (status.average_angle != null) {
      angleTexts.push(
        `무릎 ${Math.round(
          status.average_angle
        )}도`
      );
    }

    if (status.torso_angle != null) {
      angleTexts.push(
        `상체 기울기 ${Math.round(
          status.torso_angle
        )}도`
      );
    }

    if (status.elbow_angle != null) {
      angleTexts.push(
        `팔꿈치 ${Math.round(status.elbow_angle)}도`
      );
    }

    if (status.average_elbow_angle != null) {
      angleTexts.push(
        `양팔 평균 ${Math.round(status.average_elbow_angle)}도`
      );
    }

    feedbackText.textContent =
      angleTexts.length > 0
        ? angleTexts.join(" · ")
        : "관절 각도를 확인하고 있습니다.";

    return;
  }

  postureScoreValue.textContent =
    0;

  postureStatus.textContent =
    status.person_valid
      ? "CHECK"
      : "WAIT";

  feedbackTitle.textContent =
    status.status_text
    || "자세를 인식할 수 없습니다.";
  setOverlayMovement("준비");

  feedbackText.textContent =
    status.person_valid
      ? getExerciseAnalyzer(selectedExerciseCode)?.cameraGuide
        || "필요한 관절이 보이도록 위치를 조정하세요."
      : "카메라에 몸이 나오도록 이동하세요.";
  setOverlayFeedback(feedbackText.textContent);

  if (repetitionDifference === 0) {
    speakPostureFeedback(feedbackText.textContent);
  }
}


async function sendFrameForAnalysis() {
  if (
    !isWorkoutActive
    || isWorkoutPaused
    || analysisInProgress
    || !cameraVideo.videoWidth
    || !cameraVideo.videoHeight
  ) {
    return;
  }

  analysisInProgress = true;

  try {
    const sourceWidth =
      cameraVideo.videoWidth;

    const sourceHeight =
      cameraVideo.videoHeight;

    const targetWidth = 480;

    const targetHeight =
      Math.round(
        sourceHeight
        * (
          targetWidth
          / sourceWidth
        )
      );

    captureCanvas.width =
      targetWidth;

    captureCanvas.height =
      targetHeight;

    captureContext.drawImage(
      cameraVideo,
      0,
      0,
      targetWidth,
      targetHeight
    );

    const imageBlob =
      await new Promise(
        (resolve) => {
          captureCanvas.toBlob(
            resolve,
            "image/jpeg",
            0.75
          );
        }
      );

    if (!imageBlob) {
      return;
    }

    const formData =
      new FormData();

    formData.append(
      "image",
      imageBlob,
      `${selectedExerciseCode.toLowerCase()}-frame.jpg`
    );

    const analyzer = getExerciseAnalyzer(selectedExerciseCode);
    if (!analyzer) {
      throw new Error("지원하지 않는 코칭 운동입니다.");
    }

    const response =
      await fetch(
        `/api/coaching/${analyzer.apiPath}/analyze`,
        {
          method: "POST",
          body: formData
        }
      );

    const data =
      await response.json();

    if (!response.ok) {
      throw new Error(
        data.detail
        || "자세 분석에 실패했습니다."
      );
    }

    applyPoseStatus(data);

  } catch (error) {
    console.error(
      `${selectedExerciseName} 자세 분석 실패:`,
      error
    );

  } finally {
    analysisInProgress = false;
  }
}


function startPoseAnalysis() {
  stopPoseAnalysis();

  analysisTimer =
    window.setInterval(
      sendFrameForAnalysis,
      ANALYSIS_INTERVAL_MS
    );
}


function stopPoseAnalysis() {
  if (analysisTimer !== null) {
    window.clearInterval(
      analysisTimer
    );

    analysisTimer = null;
  }

  analysisInProgress = false;
}


async function resetCurrentExerciseAnalyzer() {
  const analyzer = getExerciseAnalyzer(selectedExerciseCode);
  if (!analyzer) {
    throw new Error("지원하지 않는 코칭 운동입니다.");
  }

  const response =
    await fetch(
      `/api/coaching/${analyzer.apiPath}/reset`,
      {
        method: "POST"
      }
    );

  const data =
    await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail
      || `${selectedExerciseName} 분석 상태를 초기화하지 못했습니다.`
    );
  }

  lastServerCount = 0;
}


/* =========================
   운동 시작
========================= */

async function startWorkout() {
  try {
    updateTargetDisplay();

    if (
      !setRestDuration(
        customRestSeconds.value === ""
          ? restDurationSeconds
          : customRestSeconds.value
      )
    ) {
      return;
    }

    if (!isPlanCoaching) {
      const validatedSets = validateFreeCoachingSets();
      if (!validatedSets) {
        return;
      }

      coachingSets = validatedSets;
      targetSets = coachingSets.length;
      targetReps = Number(coachingSets[0].repetition_count);
      totalTargetReps = coachingSets.reduce(
        (sum, set) => sum + Number(set.repetition_count),
        0
      );
      updateCounterDisplay();
    }

    if (!isCoachingExerciseCode(selectedExerciseCode)) {
      throw new Error(
        "지원하지 않는 코칭 운동입니다."
      );
    }

    if (!coachingSets.length) {
      throw new Error(
        "반복 횟수가 설정된 세트가 없습니다."
      );
    }

    clearRestTimer();
    currentSetIndex = 0;
    currentReps = 0;
    currentSets = 0;
    totalCompletedReps = 0;
    isCurrentSetCompleted = false;
    isResting = false;
    isWorkoutFinished = false;
    isSavingWorkout = false;
    workoutRecordSaved = false;
    savedWorkoutResult = null;
    isResultDisplayed = false;
    isWorkoutPaused = false;
    restCard.hidden = true;

    postureScores = [];

    updateCounterDisplay();

    await startCamera();
    await resetCurrentExerciseAnalyzer();

    workoutStartedAt =
      new Date();

    isWorkoutActive = true;
    isGoalCompleted = false;

    document.body.classList.add("coaching-active");
    document.body.classList.remove("coaching-paused");
    pauseButton.hidden = false;
    pauseButton.textContent = "일시정지";

    startPoseAnalysis();

    movementState.textContent =
      "1세트 준비";
    setOverlayMovement("준비");

    postureStatus.textContent =
      "ACTIVE";

    feedbackTitle.textContent =
      "자세 분석을 시작합니다.";

    feedbackText.textContent =
      "카메라에 전신이 보이도록 유지하세요.";
    setOverlayFeedback(feedbackText.textContent);
    updateWorkoutOverlay();
    speakText(`${selectedExerciseName} 코칭을 시작합니다`);

    startButton.disabled = true;
    finishButton.disabled = false;

    setFreeCoachingInputsDisabled(true);
    restPresetButtons.forEach((button) => {
      button.disabled = true;
    });
    customRestSeconds.disabled = true;

    exerciseTabs.forEach(
      (tab) => {
        tab.disabled = true;
      }
    );

  } catch (error) {
    console.error(
      "카메라 시작 실패:",
      error
    );

    stopCamera();

    alert(
      error.message
      || "카메라를 실행하지 못했습니다."
    );
  }
}


/* =========================
   운동 시간 계산
========================= */

function getWorkoutMinutes() {
  if (!workoutStartedAt) {
    return 0;
  }

  const elapsedMilliseconds =
    Date.now()
    - workoutStartedAt.getTime();

  return Math.max(
    1,
    Math.ceil(
      elapsedMilliseconds
      / 60000
    )
  );
}


/* =========================
   평균 점수
========================= */

function getAveragePostureScore() {
  if (
    postureScores.length === 0
  ) {
    return 0;
  }

  const total =
    postureScores.reduce(
      (sum, score) =>
        sum + score,
      0
    );

  return Math.round(
    total
    / postureScores.length
  );
}


function getBestPostureScore() {
  if (postureScores.length === 0) {
    return 0;
  }

  return Math.max(
    ...postureScores
  );
}

function getSavedFeedbackMessage(
  bestScore
) {
  if (bestScore >= 95) {
    return {
      title:
        "오늘 가장 완성도 높은 자세였어요.",
      text:
        "동작 깊이와 무릎 각도가 안정적으로 유지됐습니다."
    };
  }

  if (bestScore >= 90) {
    return {
      title:
        "아주 좋은 자세를 기록했어요.",
      text:
        "오늘 수행한 동작 중 균형과 깊이가 가장 좋았습니다."
    };
  }

  if (bestScore >= 80) {
    return {
      title:
        "안정적인 자세를 보여줬어요.",
      text:
        "무릎 각도와 동작 깊이가 전반적으로 좋았습니다."
    };
  }

  if (bestScore >= 70) {
    return {
      title:
        "전체적인 흐름은 좋았어요.",
      text:
        "다음에는 조금 더 깊게 내려가면 더 좋아집니다."
    };
  }

  return {
    title:
      "다음 동작에서 더 좋아질 수 있어요.",
    text:
      "시작 자세를 안정적으로 잡고 천천히 진행해 보세요."
  };
}

/* =========================
   전체 반복 횟수
========================= */

function getTotalRepetitions() {
  return totalCompletedReps;
}


/* =========================
   운동 기록 저장
========================= */

async function saveWorkoutRecord() {
  const userId =
    getLoginUserId();

  if (!userId) {
    throw new Error(
      "로그인 정보가 없습니다."
    );
  }

  const averageScore =
    getAveragePostureScore();

  const bestScore =
    getBestPostureScore();

  const savedFeedback =
    getSavedFeedbackMessage(
      bestScore
    );

  const response =
    await fetch(
      "/api/workouts",
      {
        method: "POST",

        headers: {
          "Content-Type":
            "application/json"
        },

        body: JSON.stringify({
          user_id: userId,

          exercise_code:
            selectedExerciseCode,

          completed_sets:
            currentSets,

          repetition_count:
            getTotalRepetitions(),

          workout_minutes:
            getWorkoutMinutes(),

          calories: null,

          average_posture_score:
            averageScore,

          best_posture_score:
            bestScore,

          feedback_title:
            savedFeedback.title,

          feedback:
            savedFeedback.text,

          image_url: null,

          started_at:
            workoutStartedAt
              ? workoutStartedAt
                  .toISOString()
              : null
        })
      }
    );

  let data = {};

  try {
    data = await response.json();
  } catch {
    data = {};
  }

  if (!response.ok) {
    throw new Error(
      data.detail
      || "운동 기록을 저장하지 못했습니다."
    );
  }

  return data;
}

async function completeLinkedWorkoutPlan() {
  if (!coachingWorkoutPlanId) {
    return;
  }

  const userId = getLoginUserId();
  if (!userId) {
    throw new Error("로그인 정보가 없어 연결된 루틴을 완료하지 못했습니다.");
  }

  const response = await fetch(
    `/api/workouts/plans/${coachingWorkoutPlanId}/complete`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        user_id: userId
      })
    }
  );

  if (!response.ok) {
    let data = {};
    try {
      data = await response.json();
    } catch {
      data = {};
    }
    throw new Error(
      data.detail || "연결된 루틴을 완료 처리하지 못했습니다."
    );
  }
}


/* =========================
   운동 종료
========================= */

function showWorkoutResult(planCompletionError = null) {
  if (isResultDisplayed) {
    return;
  }
  isResultDisplayed = true;

  const averageScore = getAveragePostureScore();
  const bestScore = getBestPostureScore();
  const savedFeedback = getSavedFeedbackMessage(bestScore);

  resultExerciseName.textContent =
    `${selectedExerciseName} 코칭을 완료했습니다.`;
  resultRepetitions.textContent = String(getTotalRepetitions());
  resultSets.textContent = String(currentSets);
  resultPostureScore.textContent = String(averageScore);
  resultWorkoutMinutes.textContent = String(getWorkoutMinutes());
  resultCalories.textContent = String(savedWorkoutResult?.calories ?? 0);
  resultFeedbackTitle.textContent = planCompletionError
    ? "운동 기록 저장 완료 · 루틴 완료 처리 실패"
    : savedFeedback.title;
  resultFeedbackText.textContent = planCompletionError
    ? `${savedFeedback.text} 운동 기록은 저장되었지만 연결된 루틴 완료 처리는 실패했습니다.`
    : savedFeedback.text;

  document.body.classList.remove("coaching-active", "coaching-paused");
  document.body.classList.add("coaching-result-mode");
  pauseButton.hidden = true;
  coachingResult.hidden = false;
  coachingResult.scrollIntoView({ block: "start" });
}

async function finishWorkout() {
  if (
    !isWorkoutActive
    || !isWorkoutFinished
    || isSavingWorkout
  ) {
    return;
  }

  isSavingWorkout = true;
  finishButton.disabled = true;

  stopPoseAnalysis();

  movementState.textContent =
    "저장 중";

  try {
    if (!workoutRecordSaved) {
      savedWorkoutResult = await saveWorkoutRecord();
      workoutRecordSaved = true;
    }
  } catch (error) {
    console.error(
      "운동 저장 실패:",
      error
    );

    alert(
      error.message
      || "운동 기록을 저장하지 못했습니다."
    );

    isSavingWorkout = false;
    finishButton.disabled = false;
    movementState.textContent = "저장 실패";
    return;
  }

  let planCompletionError = null;
  if (coachingWorkoutPlanId) {
    try {
      await completeLinkedWorkoutPlan();
    } catch (error) {
      planCompletionError = error;
      console.error(
        "운동 기록은 저장되었지만 계획 완료 처리에 실패했습니다:",
        error
      );
    }
  }

  isWorkoutActive = false;
  stopCamera();
  clearRestTimer();
  clearCoachingPlan();
  showWorkoutResult(planCompletionError);
}


/* =========================
   목표 완료
========================= */

async function finishWorkoutAutomatically() {
  if (isWorkoutFinished) {
    return;
  }

  isWorkoutFinished = true;
  isGoalCompleted = true;
  isCurrentSetCompleted = true;
  clearRestTimer();

  stopPoseAnalysis();
  stopCamera();
  speakText("운동 완료");

  movementState.textContent =
    "운동 완료";
  setOverlayMovement("운동 완료");

  postureStatus.textContent =
    "COMPLETE";

  feedbackTitle.textContent =
    "목표 운동을 완료했습니다.";

  feedbackText.textContent =
    "운동 기록과 연결된 루틴을 저장하고 있습니다.";
  setOverlayFeedback(feedbackText.textContent);

  startButton.disabled = true;
  finishButton.disabled = true;
  updateCounterDisplay();

  await finishWorkout();
}


/* =========================
   운동 선택
========================= */

async function toggleWorkoutPause() {
  if (!isWorkoutActive || isResting || isWorkoutFinished) {
    return;
  }

  if (!isWorkoutPaused) {
    isWorkoutPaused = true;
    stopPoseAnalysis();
    document.body.classList.add("coaching-paused");
    pauseButton.textContent = "운동 재개";
    movementState.textContent = "일시정지";
    setOverlayMovement("일시정지");
    setOverlayFeedback("준비되면 운동 재개 버튼을 눌러주세요.");
    speakText("일시정지");
    return;
  }

  pauseButton.disabled = true;
  try {
    await resetCurrentExerciseAnalyzer();
    isWorkoutPaused = false;
    document.body.classList.remove("coaching-paused");
    pauseButton.textContent = "일시정지";
    movementState.textContent = `${currentSetIndex + 1}세트 준비`;
    setOverlayMovement("준비");
    setOverlayFeedback(`${selectedExerciseName} 코칭을 재개합니다.`);
    speakText("운동을 재개합니다");
    startPoseAnalysis();
  } catch (error) {
    console.error("코칭 재개 실패:", error);
    alert(error.message || "코칭을 재개하지 못했습니다.");
  } finally {
    pauseButton.disabled = false;
  }
}

voiceToggleButton.addEventListener("click", () => {
  isVoiceEnabled = !isVoiceEnabled;
  sessionStorage.setItem(
    COACHING_VOICE_STORAGE_KEY,
    String(isVoiceEnabled)
  );
  updateVoiceButton();
  if (isVoiceEnabled) {
    speakText("음성 안내를 시작합니다");
  } else {
    stopSpeech();
  }
});

pauseButton.addEventListener("click", toggleWorkoutPause);

resultDashboardButton.addEventListener("click", () => {
  window.location.href = "/dashboard";
});

exerciseTabs.forEach(
  (tab) => {
    tab.addEventListener(
      "click",
      () => changeSelectedExercise(tab.dataset.exerciseCode)
    );
  }
);


/* =========================
   이벤트
========================= */

freeCoachingSetList.addEventListener("input", () => {
  setSettingsMessage();
  const normalized = normalizeFreeCoachingSets(
    readFreeCoachingRowsFromInputs()
  );
  if (normalized) {
    freeCoachingRows = normalized;
    saveFreeCoachingSets();
  }
});

freeCoachingSetList.addEventListener("click", (event) => {
  const deleteButton = event.target.closest("[data-free-set-delete]");
  if (!deleteButton || isWorkoutActive || freeCoachingRows.length <= 1) {
    return;
  }

  const rows = readFreeCoachingRowsFromInputs();
  rows.splice(Number(deleteButton.dataset.freeSetDelete), 1);
  const normalizedRows = normalizeFreeCoachingSets(rows);
  if (!normalizedRows) {
    setSettingsMessage(
      "남아 있는 세트의 중량과 반복 횟수를 확인해 주세요."
    );
    return;
  }

  freeCoachingRows = normalizedRows;
  saveFreeCoachingSets();
  prepareFreeCoaching();
  updateCounterDisplay();
});

freeSetAddButton.addEventListener("click", () => {
  if (isWorkoutActive || freeCoachingRows.length >= 20) {
    if (freeCoachingRows.length >= 20) {
      setSettingsMessage("자유 코칭은 최대 20세트까지 설정할 수 있습니다.");
    }
    return;
  }

  const currentRows = normalizeFreeCoachingSets(
    readFreeCoachingRowsFromInputs()
  );
  if (!currentRows) {
    setSettingsMessage(
      "현재 세트의 중량과 반복 횟수를 먼저 확인해 주세요."
    );
    return;
  }
  freeCoachingRows = currentRows;

  const previousSet = freeCoachingRows.at(-1) || {
    weight_kg: 0,
    repetition_count: 10,
  };
  freeCoachingRows.push({
    set_order: freeCoachingRows.length + 1,
    weight_kg: previousSet.weight_kg,
    repetition_count: previousSet.repetition_count,
  });
  saveFreeCoachingSets();
  prepareFreeCoaching();
  updateCounterDisplay();
});

restPresetButtons.forEach((button) => {
  button.addEventListener("click", () => {
    setRestDuration(button.dataset.restSeconds);
  });
});

customRestSeconds.addEventListener("change", () => {
  if (customRestSeconds.value === "") {
    return;
  }
  setRestDuration(customRestSeconds.value);
});

skipRestButton.addEventListener(
  "click",
  startNextSet
);


startButton.addEventListener(
  "click",
  startWorkout
);


finishButton.addEventListener("click", async () => {
  if (isWorkoutFinished) {
    await finishWorkout();
    return;
  }

  if (!isWorkoutActive) {
    return;
  }

  const shouldExit = window.confirm(
    "운동을 종료하면 현재 진행 내용은 저장되지 않습니다."
  );

  if (!shouldExit) {
    return;
  }

  isWorkoutActive = false;
  clearRestTimer();
  stopCamera();
  clearCoachingPlan();
  window.location.href = "/routine";
});


window.addEventListener(
  "beforeunload",
  (event) => {
    clearRestTimer();
    stopCamera();

    if (!isWorkoutActive) {
      return;
    }

    event.preventDefault();
    event.returnValue = "";
  }
);


/* =========================
   초기 실행
========================= */

async function initializeCoachingTargets() {
  restoreFreeCoachingSets();
  restoreRestDuration();
  restoreVoiceSetting();
  const savedPlan = loadCoachingPlan();
  const params = new URLSearchParams(window.location.search);
  const requestedExerciseCode = String(
    params.get("exercise_code") || ""
  ).toUpperCase();

  startButton.disabled = true;
  coachingSettingsCard.hidden = true;
  setProgressCard.hidden = true;
  coachingModeLoading.hidden = false;

  const validSavedPlan = getValidCoachingPlan(savedPlan);
  if (savedPlan && !validSavedPlan) {
    clearCoachingPlan();
  }

  const initialExerciseCode = validSavedPlan?.exercise_code
    || (
      isCoachingExerciseCode(requestedExerciseCode)
        ? requestedExerciseCode
        : selectedExerciseCode
    );
  selectExerciseTab(initialExerciseCode);

  const todayPlanResult = await fetchTodayCoachingPlans();
  applySelectedExerciseMode();

  if (todayPlanResult === "error") {
    setSettingsMessage(
      "오늘의 운동 계획을 불러오지 못해 자유 코칭으로 시작합니다."
    );
  }

  finishModeLoading();
  updateTargetDisplay();
  updateCounterDisplay();
}


initializeCoachingTargets();
