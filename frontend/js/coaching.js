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

const pushupOrientationGuide =
  document.querySelector("#pushupOrientationGuide");

const poseContext = poseCanvas.getContext("2d");

const POSE_SKELETON_CONNECTIONS = [
  [5, 6], [5, 11], [6, 12], [11, 12],
  [11, 13], [13, 15], [12, 14], [14, 16],
  [5, 7], [7, 9], [6, 8], [8, 10]
];

const LEFT_ANALYSIS_KEYPOINTS = new Set([5, 11, 13, 15]);
const RIGHT_ANALYSIS_KEYPOINTS = new Set([6, 12, 14, 16]);

function clearPoseOverlay() {
  poseContext.setTransform(1, 0, 0, 1, 0, 0);
  poseContext.clearRect(0, 0, poseCanvas.width, poseCanvas.height);
}

function drawPoseOverlay(status) {
  const overlay = status.pose_overlay;
  const width = Number(overlay?.source_width);
  const height = Number(overlay?.source_height);
  const keypoints = Array.isArray(overlay?.keypoints)
    ? overlay.keypoints
    : [];

  if (!status.pose_valid || !width || !height || keypoints.length === 0) {
    clearPoseOverlay();
    return;
  }

  if (poseCanvas.width !== width || poseCanvas.height !== height) {
    poseCanvas.width = width;
    poseCanvas.height = height;
  } else {
    clearPoseOverlay();
  }

  // The video is mirrored with CSS. Mirror only x coordinates here so text
  // remains readable while joints stay aligned with the front-camera image.
  const points = new Map(
    keypoints.map((point) => [point.id, {
      ...point,
      drawX: width - point.x,
      drawY: point.y,
    }])
  );
  const selectedSide = overlay.selected_side;
  const emphasized = new Set();
  if (selectedSide === "LEFT" || selectedSide === "BOTH") {
    LEFT_ANALYSIS_KEYPOINTS.forEach((id) => emphasized.add(id));
  }
  if (selectedSide === "RIGHT" || selectedSide === "BOTH") {
    RIGHT_ANALYSIS_KEYPOINTS.forEach((id) => emphasized.add(id));
  }

  poseContext.lineCap = "round";
  poseContext.lineJoin = "round";
  POSE_SKELETON_CONNECTIONS.forEach(([fromId, toId]) => {
    const from = points.get(fromId);
    const to = points.get(toId);
    if (!from || !to) return;
    const highlighted = emphasized.has(fromId) && emphasized.has(toId);
    poseContext.beginPath();
    poseContext.moveTo(from.drawX, from.drawY);
    poseContext.lineTo(to.drawX, to.drawY);
    poseContext.strokeStyle = highlighted
      ? "rgba(255, 224, 88, 0.96)"
      : "rgba(168, 255, 53, 0.82)";
    poseContext.lineWidth = highlighted ? 4 : 2.5;
    poseContext.stroke();
  });

  points.forEach((point, id) => {
    const highlighted = emphasized.has(id);
    poseContext.beginPath();
    poseContext.arc(point.drawX, point.drawY, highlighted ? 5 : 3.5, 0, Math.PI * 2);
    poseContext.fillStyle = highlighted ? "#ffe058" : "#a8ff35";
    poseContext.fill();
    poseContext.lineWidth = 1.5;
    poseContext.strokeStyle = "rgba(0, 0, 0, 0.78)";
    poseContext.stroke();
  });

  const kneeIds = selectedSide === "LEFT"
    ? [13]
    : selectedSide === "RIGHT"
      ? [14]
      : [13, 14];
  const kneeAngle = Number(status.average_angle);
  if (Number.isFinite(kneeAngle)) {
    kneeIds.forEach((id) => {
      const knee = points.get(id);
      if (!knee) return;
      const labelX = Math.max(8, Math.min(width - 66, knee.drawX + 10));
      const labelY = Math.max(22, Math.min(height - 8, knee.drawY - 10));
      poseContext.font = "700 15px system-ui, sans-serif";
      poseContext.lineWidth = 4;
      poseContext.strokeStyle = "rgba(0, 0, 0, 0.82)";
      poseContext.strokeText(`${Math.round(kneeAngle)}°`, labelX, labelY);
      poseContext.fillStyle = "#ffffff";
      poseContext.fillText(`${Math.round(kneeAngle)}°`, labelX, labelY);
    });
  }

  const score = Number(status.posture_score);
  const summary = Number.isFinite(score)
    ? `${status.stage || "UP"} · ${Math.round(score)}`
    : String(status.stage || "UP");
  poseContext.font = "800 14px system-ui, sans-serif";
  poseContext.textBaseline = "bottom";
  poseContext.lineWidth = 4;
  poseContext.strokeStyle = "rgba(0, 0, 0, 0.82)";
  poseContext.strokeText(summary, 12, height - 12);
  poseContext.fillStyle = "#ffffff";
  poseContext.fillText(summary, 12, height - 12);
  poseContext.textBaseline = "alphabetic";
}

function drawLivePoseOverlay(status) {
  const frameId = Number(status.frame_id);
  if (!Number.isInteger(frameId) || frameId < latestAnnotatedResponseId) {
    return;
  }
  latestAnnotatedResponseId = frameId;

  const overlay = status.pose_overlay;
  const sourceWidth = Number(overlay?.source_width);
  const sourceHeight = Number(overlay?.source_height);
  const keypoints = Array.isArray(overlay?.keypoints) ? overlay.keypoints : [];
  if (!status.person_detected || !sourceWidth || !sourceHeight || keypoints.length === 0) {
    clearPoseOverlay();
    return;
  }

  const rect = poseCanvas.getBoundingClientRect();
  const viewWidth = rect.width;
  const viewHeight = rect.height;
  if (viewWidth <= 0 || viewHeight <= 0) {
    clearPoseOverlay();
    return;
  }
  const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
  const backingWidth = Math.round(viewWidth * pixelRatio);
  const backingHeight = Math.round(viewHeight * pixelRatio);
  if (poseCanvas.width !== backingWidth || poseCanvas.height !== backingHeight) {
    poseCanvas.width = backingWidth;
    poseCanvas.height = backingHeight;
  }
  poseContext.setTransform(pixelRatio, 0, 0, pixelRatio, 0, 0);
  poseContext.clearRect(0, 0, viewWidth, viewHeight);

  const coverScale = Math.max(
    viewWidth / sourceWidth,
    viewHeight / sourceHeight
  );
  const offsetX = (viewWidth - sourceWidth * coverScale) / 2;
  const offsetY = (viewHeight - sourceHeight * coverScale) / 2;
  const project = (x, y) => {
    const coveredX = x * coverScale + offsetX;
    return {
      x: viewWidth - coveredX,
      y: y * coverScale + offsetY,
    };
  };

  const points = new Map(
    keypoints.map((point) => [point.id, project(point.x, point.y)])
  );
  const connections = [
    [0, 1], [0, 2], [1, 3], [2, 4], [3, 5], [4, 6],
    [5, 6], [5, 7], [7, 9], [6, 8], [8, 10],
    [5, 11], [6, 12], [11, 12],
    [11, 13], [13, 15], [12, 14], [14, 16]
  ];
  const leftIds = new Set([1, 3, 5, 7, 9, 11, 13, 15]);
  const rightIds = new Set([2, 4, 6, 8, 10, 12, 14, 16]);
  const colorFor = (start, end = start) => {
    if (leftIds.has(start) && leftIds.has(end)) return "#ffdc50";
    if (rightIds.has(start) && rightIds.has(end)) return "#4696ff";
    return "#50ff78";
  };

  poseContext.lineCap = "round";
  connections.forEach(([start, end]) => {
    const from = points.get(start);
    const to = points.get(end);
    if (!from || !to) return;
    poseContext.beginPath();
    poseContext.moveTo(from.x, from.y);
    poseContext.lineTo(to.x, to.y);
    poseContext.strokeStyle = colorFor(start, end);
    poseContext.lineWidth = 1.5;
    poseContext.stroke();
  });
  points.forEach((point, id) => {
    poseContext.beginPath();
    poseContext.arc(point.x, point.y, 2.5, 0, Math.PI * 2);
    poseContext.fillStyle = colorFor(id);
    poseContext.fill();
  });

  const bbox = overlay.bbox;
  if (bbox) {
    const topRight = project(bbox.x1, bbox.y1);
    const bottomLeft = project(bbox.x2, bbox.y2);
    const boxX = bottomLeft.x;
    const boxY = topRight.y;
    const boxWidth = topRight.x - bottomLeft.x;
    const boxHeight = bottomLeft.y - topRight.y;
    poseContext.strokeStyle = "rgba(168, 255, 53, 0.9)";
    poseContext.lineWidth = 1;
    poseContext.strokeRect(boxX, boxY, boxWidth, boxHeight);
    if (Number.isFinite(Number(bbox.confidence))) {
      poseContext.font = "600 11px system-ui, sans-serif";
      poseContext.fillStyle = "#a8ff35";
      poseContext.fillText(
        `person ${Number(bbox.confidence).toFixed(2)}`,
        Math.max(3, boxX),
        Math.max(12, boxY - 4)
      );
    }
  }

  window.clearTimeout(poseStaleTimer);
  poseStaleTimer = window.setTimeout(() => {
    if (frameId === latestAnnotatedResponseId) clearPoseOverlay();
  }, 700);
}

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
const overlayExerciseName =
  document.querySelector("#overlayExerciseName");
const coachingResult =
  document.querySelector("#coachingResult");
const coachingResultTitle =
  document.querySelector("#coachingResultTitle");
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
const resultCaloriesLine =
  document.querySelector("#resultCaloriesLine");
const resultCaloriesHelp =
  document.querySelector("#resultCaloriesHelp");
const workoutIntensityStep =
  document.querySelector("#workoutIntensityStep");
const workoutIntensityTitle =
  document.querySelector("#workoutIntensityTitle");
const workoutIntensitySummary =
  document.querySelector("#workoutIntensitySummary");
const workoutIntensityMessage =
  document.querySelector("#workoutIntensityMessage");
const workoutIntensityChoices =
  document.querySelector("#workoutIntensityChoices");
const saveWorkoutButton =
  document.querySelector("#saveWorkoutButton");
const resultFeedbackTitle =
  document.querySelector("#resultFeedbackTitle");
const resultFeedbackText =
  document.querySelector("#resultFeedbackText");
const resultDashboardButton =
  document.querySelector("#resultDashboardButton");
const resultPrimaryButton =
  document.querySelector("#resultPrimaryButton");
const resultRetryButton =
  document.querySelector("#resultRetryButton");
const resultRecordStatus =
  document.querySelector("#resultRecordStatus");
const resultPlanStatus =
  document.querySelector("#resultPlanStatus");
const cameraRetryButton =
  document.querySelector("#cameraRetryButton");
const ptAssignmentContext = document.querySelector("#ptAssignmentContext");
const ptAssignmentSummary = document.querySelector("#ptAssignmentSummary");
const poseInitialNotice = document.querySelector("#poseInitialNotice");


let selectedExerciseCode =
  "SQUAT";

let selectedExerciseName =
  "스쿼트";

const COACHING_SESSION_STORAGE_KEY = "gymfitCoachingSessionId";
let coachingSessionId = null;

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
let selectedWorkoutIntensity = null;
let isAwaitingIntensity = false;
let isWorkoutMeasurementFinalized = false;
let workoutMeasurementFinalizationPromise = null;
let savedWorkoutResult = null;
let isResultDisplayed = false;
let lastWorkoutSaveError = null;
let lastPlanCompletionError = null;
let planCompletionSucceeded = null;
let restIntervalId = null;
let restSecondsRemaining = 0;
let restDurationSeconds = 60;
let coachingWorkoutPlanId = null;
let coachingAssignmentId = null;
let coachingAssignment = null;
let isPlanCoaching = false;
const COACHING_CONTEXT = Object.freeze({
  FREE: "FREE",
  ROUTINE: "ROUTINE",
  PT_ASSIGNMENT: "PT_ASSIGNMENT",
});
let coachingContext = COACHING_CONTEXT.FREE;
let coachingEstimatedMinutes = 0;
let freeCoachingRows = [];
let todayCoachingPlans = [];
let coachingModeRequestId = 0;
let isWorkoutPaused = false;
let isVoiceEnabled = true;
let lastSpokenFeedback = "";
let lastFeedbackSpokenAt = 0;

let postureScores = [];
let bestCapturedPostureScore = -1;
let bestPostureImageDataUrl = null;

let workoutStartedAt = null;
let effectiveWorkoutStartedAt = null;
let workoutFinishedAt = null;
let pauseStartedAt = null;
let accumulatedPausedMilliseconds = 0;
const workoutActivityTimer = new CoachingActivityTimer({
  idleTimeoutMs: 7000,
  angleChangeDegrees: 4.5,
});
let cameraStream = null;
let currentFacingMode = "user";
let orientationListenersAttached = false;
let orientationUpdateFrame = null;

let isWorkoutActive = false;
let isGoalCompleted = false;

let analysisTimer = null;
let analysisInProgress = false;
let lastServerCount = 0;
let nextAnalysisFrameId = 0;
let latestAnnotatedResponseId = -1;
let poseStaleTimer = null;

const captureCanvas =
  document.createElement("canvas");

const captureContext =
  captureCanvas.getContext(
    "2d"
  );

const brightnessCanvas = document.createElement("canvas");
brightnessCanvas.width = 32;
brightnessCanvas.height = 32;
const brightnessContext = brightnessCanvas.getContext("2d", {
  willReadFrequently: true
});

const LEGACY_ANALYSIS_INTERVAL_MS = 350;
const ANALYSIS_LOOP_DELAY_MS = 80;
const ANALYSIS_INPUT_WIDTH = 480;
const ANALYSIS_JPEG_QUALITY = 0.75;
const POSE_PERFORMANCE_SAMPLE_SIZE = 30;
const posePerformanceSamples = [];
let lastPoseResponseAt = null;
let posePerformanceResponseCount = 0;

function isMobileTouchDevice() {
  const coarsePointer = window.matchMedia?.("(pointer: coarse)")?.matches === true;
  const touchPoints = Number(navigator.maxTouchPoints || 0);
  const userAgent = String(navigator.userAgent || "");
  const mobileUserAgent = /Android|iPhone|iPad|iPod|Mobile/i.test(userAgent);
  const iPadDesktopMode = /Macintosh/i.test(userAgent) && touchPoints > 1;
  return (coarsePointer || touchPoints > 0) && (mobileUserAgent || iPadDesktopMode);
}

function shouldShowPushupPortraitAdvisory() {
  const isPortrait = window.innerHeight > window.innerWidth;
  return selectedExerciseCode === "PUSHUP"
    && isMobileTouchDevice()
    && isPortrait;
}

function resizePoseCanvasToCamera() {
  const rect = poseCanvas.getBoundingClientRect();
  const pixelRatio = Math.max(1, window.devicePixelRatio || 1);
  const width = Math.max(1, Math.round(rect.width * pixelRatio));
  const height = Math.max(1, Math.round(rect.height * pixelRatio));
  if (poseCanvas.width !== width || poseCanvas.height !== height) {
    poseCanvas.width = width;
    poseCanvas.height = height;
  }
}

function updatePushupOrientationAdvisory() {
  const showAdvisory = shouldShowPushupPortraitAdvisory();
  pushupOrientationGuide.hidden = !showAdvisory;
  document.body.classList.toggle(
    "pushup-landscape-mode",
    selectedExerciseCode === "PUSHUP"
      && isMobileTouchDevice()
      && !showAdvisory
  );

  resizePoseCanvasToCamera();
}

function scheduleOrientationAdvisoryUpdate() {
  if (orientationUpdateFrame !== null) {
    window.cancelAnimationFrame(orientationUpdateFrame);
  }
  orientationUpdateFrame = window.requestAnimationFrame(() => {
    orientationUpdateFrame = null;
    updatePushupOrientationAdvisory();
  });
}

function attachOrientationListeners() {
  if (orientationListenersAttached) return;
  window.addEventListener("orientationchange", scheduleOrientationAdvisoryUpdate);
  window.addEventListener("resize", scheduleOrientationAdvisoryUpdate);
  orientationListenersAttached = true;
}

function detachOrientationListeners() {
  if (!orientationListenersAttached) return;
  window.removeEventListener("orientationchange", scheduleOrientationAdvisoryUpdate);
  window.removeEventListener("resize", scheduleOrientationAdvisoryUpdate);
  orientationListenersAttached = false;
  if (orientationUpdateFrame !== null) {
    window.cancelAnimationFrame(orientationUpdateFrame);
    orientationUpdateFrame = null;
  }
}

function recordPosePerformance({
  roundTripMs,
  inferenceMs,
  prepareMs,
  detectionReason,
  detectionDebug,
  detectionFailureCounts,
  frameBrightness,
  brightnessAdjusted,
}) {
  const now = performance.now();
  const responseIntervalMs = lastPoseResponseAt === null
    ? null
    : now - lastPoseResponseAt;
  lastPoseResponseAt = now;
  posePerformanceResponseCount += 1;
  posePerformanceSamples.push({
    roundTripMs,
    inferenceMs,
    prepareMs,
    responseIntervalMs,
  });
  if (posePerformanceSamples.length > POSE_PERFORMANCE_SAMPLE_SIZE) {
    posePerformanceSamples.shift();
  }
  if (posePerformanceResponseCount % 10 !== 0) return;

  const average = (key) => {
    const values = posePerformanceSamples
      .map((sample) => sample[key])
      .filter(Number.isFinite);
    return values.length
      ? values.reduce((sum, value) => sum + value, 0) / values.length
      : 0;
  };
  const averageInterval = average("responseIntervalMs");
  console.log("[pose performance]", {
    strategy: "continuous-after-response",
    legacy_interval_ms: LEGACY_ANALYSIS_INTERVAL_MS,
    loop_delay_ms: ANALYSIS_LOOP_DELAY_MS,
    input_width: ANALYSIS_INPUT_WIDTH,
    jpeg_quality: ANALYSIS_JPEG_QUALITY,
    samples: posePerformanceSamples.length,
    average_prepare_ms: Number(average("prepareMs").toFixed(1)),
    average_inference_ms: Number(average("inferenceMs").toFixed(1)),
    average_round_trip_ms: Number(average("roundTripMs").toFixed(1)),
    analyses_per_second: averageInterval > 0
      ? Number((1000 / averageInterval).toFixed(2))
      : 0,
  });
  console.log("[pose detection summary]", {
    latest_reason: detectionReason,
    failure_counts: detectionFailureCounts,
    person_confidence: detectionDebug?.person_confidence ?? null,
    analysis_valid_keypoints: detectionDebug?.analysis_valid_keypoints ?? 0,
    overlay_valid_keypoints: detectionDebug?.overlay_valid_keypoints ?? 0,
    required_joint_confidences:
      detectionDebug?.required_joint_confidences ?? null,
    keypoint_confidences: detectionDebug?.keypoint_confidences ?? null,
    selected_bbox: detectionDebug?.selected_bbox ?? null,
    frame_brightness: Number.isFinite(frameBrightness)
      ? Number(frameBrightness.toFixed(1))
      : null,
    brightness_adjusted: Boolean(brightnessAdjusted),
  });
}
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
  overlayExerciseName.textContent = selectedExerciseName;
}

function setOverlayMovement(text) {
  overlayMovementState.textContent = text || "준비";
}

function setOverlayFeedback(text) {
  overlayFeedbackText.textContent = text || "자세를 확인하고 있습니다.";
}

function getMovementCue(status) {
  if (!status?.stage || status.stage === "UNKNOWN") {
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

function normalizeRecordWeightKg(value) {
  if (value === null || value === undefined || value === "") {
    return null;
  }

  const weight = Number(value);
  return Number.isFinite(weight) && weight > 0 ? weight : null;
}

function getWorkoutRecordWeightKg() {
  if (coachingContext === COACHING_CONTEXT.ROUTINE) {
    return normalizeRecordWeightKg(coachingSets[0]?.weight_kg);
  }

  if (coachingContext === COACHING_CONTEXT.PT_ASSIGNMENT) {
    return normalizeRecordWeightKg(coachingAssignment?.weight_kg);
  }

  return normalizeRecordWeightKg(coachingSets[0]?.weight_kg);
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
  coachingContext = COACHING_CONTEXT.ROUTINE;
  coachingAssignmentId = null;
  coachingAssignment = null;
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
  coachingAssignmentId = null;
  coachingAssignment = null;
  coachingEstimatedMinutes = 0;
  isPlanCoaching = false;
  coachingContext = COACHING_CONTEXT.FREE;
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
  const analyzer = getExerciseAnalyzer(selectedExerciseCode);
  if (poseInitialNotice) {
    poseInitialNotice.hidden = !analyzer?.initialTest;
  }
  if (selectedExerciseCode === "PUSHUP") {
    attachOrientationListeners();
  } else if (!isWorkoutActive) {
    detachOrientationListeners();
  }
  updatePushupOrientationAdvisory();
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

  try {
    await closeCoachingSession();
  } catch (error) {
    console.error("기존 코칭 세션 종료 실패:", error);
  }

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
    || !navigator.mediaDevices.getUserMedia
  ) {
    throw new Error(
      "이 브라우저는 카메라를 지원하지 않습니다."
    );
  }

  setCameraPlaceholderState(
    "permission",
    "카메라 권한 요청 중",
    "브라우저의 카메라 권한을 확인하고 있어요."
  );

  const isLandscape =
    window.innerWidth > window.innerHeight;

  cameraStream =
    await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: currentFacingMode,

        width: {
          ideal: isLandscape
            ? 1280
            : 720
        },

        height: {
          ideal: isLandscape
            ? 720
            : 960
        }
      },

      audio: false
    });

  setCameraPlaceholderState(
    "connecting",
    "카메라 연결 중",
    "영상 장치를 준비하고 있어요."
  );

  cameraVideo.srcObject = cameraStream;

  await cameraVideo.play();

  setCameraPlaceholderState(
    "ready",
    "분석 준비 완료",
    "운동을 시작합니다."
  );

  cameraPlaceholder.hidden = true;
}

function setCameraPlaceholderState(state, title, message, { error = false } = {}) {
  document.body.dataset.coachingState = state;
  cameraPlaceholder.dataset.cameraState = state;
  cameraPlaceholder.hidden = false;
  cameraPlaceholder.style.display = "";
  cameraPlaceholder.setAttribute("role", error ? "alert" : "status");
  cameraPlaceholder.querySelector("strong").textContent = title;
  cameraPlaceholder.querySelector("span").textContent = message;
  cameraRetryButton.hidden = !error;
}


/* =========================
   카메라 종료
========================= */

function stopCamera() {
  stopPoseAnalysis();
  stopSpeech();
  clearPoseOverlay();
  window.clearTimeout(poseStaleTimer);
  detachOrientationListeners();
  pushupOrientationGuide.hidden = true;
  document.body.classList.remove("pushup-landscape-mode");

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
  score,
  captureImage = null,
  fallbackImage = null
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

  if (totalCompletedReps === 0) {
    effectiveWorkoutStartedAt = new Date();
  }

  postureScores.push(score);

  if (score > bestCapturedPostureScore) {
    const selectedImage = captureImage || fallbackImage;
    if (selectedImage) {
      bestPostureImageDataUrl = selectedImage;
      bestCapturedPostureScore = score;
    }
  }

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
  workoutActivityTimer.suspend();
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
  workoutActivityTimer.resume();
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
  status,
  submittedFrameDataUrl = null
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

  workoutActivityTimer.update(status, Date.now(), (
    isWorkoutActive
    && !isWorkoutPaused
    && !isResting
    && !isWorkoutFinished
  ));

  const completedCapture = status.completed_pose_capture;
  const backendImageValue = String(completedCapture?.image || "").trim();
  const backendImage = backendImageValue
    ? (backendImageValue.startsWith("data:")
      ? backendImageValue
      : `data:image/jpeg;base64,${backendImageValue}`)
    : null;
  const captureSource = backendImage
    ? "backend-best-pose"
    : (["SQUAT", "PUSHUP"].includes(selectedExerciseCode)
      ? "no-valid-down-pose-capture"
      : "frontend-current-frame-fallback");
  const repetitionCaptureImage = backendImage
    || (["SQUAT", "PUSHUP"].includes(selectedExerciseCode)
      ? null
      : submittedFrameDataUrl);

  if (repetitionDifference > 0) {
    console.log("[capture source]", captureSource, {
      count: serverCount,
      score: completedCapture?.score ?? null,
      knee_angle: completedCapture?.knee_angle ?? null,
      elbow_angle: completedCapture?.elbow_angle ?? null,
      has_image: Boolean(backendImage),
      fallback_reason: status.capture_fallback_reason ?? null,
    });
  }

  const score = completedCapture?.score
    ?? getPostureScoreFromStatus(status);

  for (
    let index = 0;
    index < repetitionDifference;
    index += 1
  ) {
    registerRepetition(
      score,
      backendImage,
      backendImage ? null : repetitionCaptureImage
    );
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
    document.body.dataset.coachingState = "active";
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

    if (selectedExerciseCode === "SQUAT" && status.average_angle != null) {
      angleTexts.push(
        `무릎 ${Math.round(
          status.average_angle
        )}도`
      );
    }

    if (selectedExerciseCode === "SQUAT" && status.torso_angle != null) {
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

    if (status.body_alignment_angle != null) {
      angleTexts.push(
        `몸 정렬 ${Math.round(status.body_alignment_angle)}도`
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
  document.body.dataset.coachingState = status.person_valid
    ? "analysis-waiting"
    : "person-missing";

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
    || isResting
    || analysisInProgress
    || !coachingSessionId
    || !cameraVideo.videoWidth
    || !cameraVideo.videoHeight
  ) {
    return;
  }

  analysisInProgress = true;
  const framePreparationStartedAt = performance.now();
  let frameBrightness = null;
  let brightnessAdjusted = false;

  try {
    const sourceWidth = cameraVideo.videoWidth;
    const sourceHeight = cameraVideo.videoHeight;

    const targetWidth = ANALYSIS_INPUT_WIDTH;

    const targetHeight = Math.round(
      sourceHeight * (
        targetWidth / sourceWidth
      )
    );

    captureCanvas.width = targetWidth;
    captureCanvas.height = targetHeight;

    captureContext.setTransform(
      1,
      0,
      0,
      1,
      0,
      0
    );

    captureContext.clearRect(
      0,
      0,
      targetWidth,
      targetHeight
    );

    captureContext.filter = "none";

    captureContext.drawImage(
      cameraVideo,
      0,
      0,
      sourceWidth,
      sourceHeight,
      0,
      0,
      targetWidth,
      targetHeight
    );

    if (
      selectedExerciseCode === "PUSHUP"
      && brightnessCanvas
      && brightnessContext
    ) {
      brightnessContext.clearRect(
        0,
        0,
        brightnessCanvas.width,
        brightnessCanvas.height
      );

      brightnessContext.drawImage(
        cameraVideo,
        0,
        0,
        brightnessCanvas.width,
        brightnessCanvas.height
      );

      const pixels = brightnessContext.getImageData(
        0,
        0,
        brightnessCanvas.width,
        brightnessCanvas.height
      ).data;

      let brightnessTotal = 0;
      let samples = 0;

      for (
        let index = 0;
        index < pixels.length;
        index += 4
      ) {
        brightnessTotal += (
          pixels[index]
          + pixels[index + 1]
          + pixels[index + 2]
        ) / 3;

        samples += 1;
      }

      frameBrightness = samples > 0
        ? brightnessTotal / samples
        : null;
    }

    const imageBlob =
      await new Promise(
        (resolve) => {
          captureCanvas.toBlob(
            resolve,
            "image/jpeg",
            ANALYSIS_JPEG_QUALITY
          );
        }
      );

    if (!imageBlob) {
      return;
    }

    // Freeze this request's frame before awaiting the backend. It is used only
    // when the backend explicitly has no completed best-pose image.
    const submittedFrameDataUrl = ["SQUAT", "PUSHUP"].includes(selectedExerciseCode)
      ? null
      : captureCanvas.toDataURL("image/jpeg", 0.82);

    const formData =
      new FormData();

    const requestFrameId = ++nextAnalysisFrameId;

    formData.append(
      "image",
      imageBlob,
      `${selectedExerciseCode.toLowerCase()}-frame.jpg`
    );
    formData.append("frame_id", String(requestFrameId));
    if (selectedExerciseCode === "PUSHUP" && Number.isFinite(frameBrightness)) {
      formData.append("frame_mean_brightness", frameBrightness.toFixed(2));
      formData.append("brightness_adjusted", String(brightnessAdjusted));
    }

    const framePrepareMs =
      performance.now() - framePreparationStartedAt;

    const requestSessionId = coachingSessionId;
    const requestStartedAt = performance.now();

    const response =
      await fetch(
        `/api/coaching/sessions/${encodeURIComponent(requestSessionId)}/analyze`,
        {
          method: "POST",
          body: formData
        }
      );

    const data =
      await response.json();

    const roundTripMs =
      performance.now() - requestStartedAt;

    if (
      response.status === 404
      || response.status === 410
    ) {
      if (coachingSessionId === requestSessionId) {
        coachingSessionId = null;

        sessionStorage.removeItem(
          COACHING_SESSION_STORAGE_KEY
        );

        stopPoseAnalysis();

        movementState.textContent =
          "세션 만료";

        feedbackText.textContent =
          "코칭 세션이 만료되었습니다. 운동 재개 시 자동으로 다시 연결합니다.";

        setOverlayFeedback(
          feedbackText.textContent
        );
      }

      throw new Error(
        "코칭 분석 세션이 만료되었습니다."
      );
    }

    if (!response.ok) {
      throw new Error(
        data.detail
        || "자세 분석에 실패했습니다."
      );
    }

    drawLivePoseOverlay(data);
    applyPoseStatus(
      data,
      submittedFrameDataUrl
    );
    recordPosePerformance({
      roundTripMs,
      inferenceMs: Number(data.performance?.inference_ms),
      prepareMs: framePrepareMs,
      detectionReason: data.detection_reason,
      detectionDebug: data.detection_debug,
      detectionFailureCounts: data.detection_failure_counts,
      frameBrightness,
      brightnessAdjusted,
    });

  } catch (error) {
    console.error(
      `${selectedExerciseName} 자세 분석 실패:`,
      error
    );

  } finally {
    analysisInProgress = false;
    if (
      isWorkoutActive
      && !isWorkoutPaused
      && !isResting
      && !isWorkoutFinished
      && coachingSessionId
    ) {
      analysisTimer = window.setTimeout(
        sendFrameForAnalysis,
        ANALYSIS_LOOP_DELAY_MS
      );
    }
  }
}


function startPoseAnalysis() {
  stopPoseAnalysis();
  if (
    analysisInProgress
    || isResting
    || isWorkoutPaused
    || isWorkoutFinished
  ) {
    return;
  }
  analysisTimer = window.setTimeout(sendFrameForAnalysis, 0);
}


function stopPoseAnalysis() {
  if (analysisTimer !== null) {
    window.clearTimeout(
      analysisTimer
    );

    analysisTimer = null;
  }

}


async function resetCurrentExerciseAnalyzer() {
  if (!coachingSessionId) {
    await createCoachingSession();
    lastServerCount = 0;
    return;
  }

  const sessionId = coachingSessionId;

  const response = await fetch(
    `/api/coaching/sessions/${encodeURIComponent(sessionId)}/reset`,
    {
      method: "POST",
    }
  );

  if (
    response.status === 404
    || response.status === 410
  ) {
    console.warn(
      "[coaching] 분석 세션 만료/유실 → 새 세션 생성"
    );

    // 현재 요청한 세션이 아직 활성 세션일 때만 제거
    if (coachingSessionId === sessionId) {
      coachingSessionId = null;
      sessionStorage.removeItem(
        COACHING_SESSION_STORAGE_KEY
      );
    }

    await createCoachingSession();

    // 새 Analyzer는 count 0부터 시작
    lastServerCount = 0;

    return;
  }

  if (!response.ok) {
    const errorData = await response
      .json()
      .catch(() => ({}));

    throw new Error(
      errorData.detail
      || "분석 세션 초기화에 실패했습니다."
    );
  }

  // 정상 reset도 Analyzer count가 0부터 다시 시작함
  lastServerCount = 0;
}


async function createCoachingSession() {
  await closeCoachingSession();
  const response = await fetch("/api/coaching/sessions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      exercise_code: selectedExerciseCode,
      target_reps: targetReps,
      target_sets: targetSets,
      workout_plan_id: coachingWorkoutPlanId || null,
    }),
  });
  const data = await response.json().catch(() => null);
  if (!response.ok || !data?.coaching_session_id) {
    throw new Error(data?.detail || "코칭을 시작하지 못했습니다.");
  }
  coachingSessionId = data.coaching_session_id;
  sessionStorage.setItem(COACHING_SESSION_STORAGE_KEY, coachingSessionId);
}


async function closeCoachingSession({ keepalive = false } = {}) {
  const sessionId = coachingSessionId
    || sessionStorage.getItem(COACHING_SESSION_STORAGE_KEY);
  coachingSessionId = null;
  sessionStorage.removeItem(COACHING_SESSION_STORAGE_KEY);
  if (!sessionId) {
    return;
  }
  const response = await fetch(
    `/api/coaching/sessions/${encodeURIComponent(sessionId)}`,
    { method: "DELETE", keepalive }
  );
  if (!response.ok && response.status !== 404) {
    const data = await response.json().catch(() => null);
    throw new Error(data?.detail || "코칭 세션을 종료하지 못했습니다.");
  }
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
    selectedWorkoutIntensity = null;
    isAwaitingIntensity = false;
    isWorkoutMeasurementFinalized = false;
    workoutMeasurementFinalizationPromise = null;
    savedWorkoutResult = null;
    isResultDisplayed = false;
    lastWorkoutSaveError = null;
    lastPlanCompletionError = null;
    planCompletionSucceeded = null;
    isWorkoutPaused = false;
    effectiveWorkoutStartedAt = null;
    workoutFinishedAt = null;
    pauseStartedAt = null;
    accumulatedPausedMilliseconds = 0;
    workoutActivityTimer.reset();
    restCard.hidden = true;
    workoutIntensityStep.hidden = true;
    workoutIntensityMessage.textContent = "";
    saveWorkoutButton.disabled = true;
    saveWorkoutButton.removeAttribute("aria-busy");
    workoutIntensityChoices.querySelectorAll("input").forEach((input) => {
      input.checked = false;
    });
    document.body.classList.remove(
      "coaching-intensity-mode",
      "coaching-result-mode"
    );

    postureScores = [];
    bestCapturedPostureScore = -1;
    bestPostureImageDataUrl = null;

    updateCounterDisplay();

    startButton.disabled = true;
    startButton.setAttribute("aria-busy", "true");
    await createCoachingSession();
    await startCamera();
    await resetCurrentExerciseAnalyzer();

    workoutStartedAt =
      new Date();

    isWorkoutActive = true;
    isGoalCompleted = false;

    document.body.classList.add("coaching-active");
    document.body.dataset.coachingState = "active";
    document.body.classList.remove("coaching-paused");
    pauseButton.hidden = false;
    pauseButton.textContent = "일시정지";
    cameraPlaceholder.hidden = true;
    attachOrientationListeners();
    updatePushupOrientationAdvisory();
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
    startButton.removeAttribute("aria-busy");
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
    await closeCoachingSession().catch(() => {});

    const permissionMessage = error?.name === "NotAllowedError"
      ? "브라우저 설정에서 카메라 권한을 허용한 뒤 다시 시도해 주세요."
      : error.message || "카메라 연결을 확인한 뒤 다시 시도해 주세요.";
    setCameraPlaceholderState(
      "error",
      "카메라를 시작하지 못했어요.",
      permissionMessage,
      { error: true }
    );
    feedbackTitle.textContent = "카메라 설정을 확인해 주세요.";
    feedbackText.textContent = permissionMessage;
    movementState.textContent = "카메라 확인 필요";
    postureStatus.textContent = "READY";
    startButton.disabled = false;
    startButton.removeAttribute("aria-busy");
    startButton.textContent = "카메라 다시 시도";
  }
}


/* =========================
   운동 시간 계산
========================= */

function getWorkoutMinutes() {
  return workoutActivityTimer.getWholeMinutes(totalCompletedReps);
}

function freezeEffectiveWorkoutTime() {
  if (workoutFinishedAt) {
    return;
  }

  const finishedAt = new Date();
  if (pauseStartedAt) {
    accumulatedPausedMilliseconds += Math.max(
      0,
      finishedAt.getTime() - pauseStartedAt.getTime()
    );
    pauseStartedAt = null;
  }
  workoutFinishedAt = finishedAt;
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

  if (!["LOW", "MODERATE", "HIGH"].includes(selectedWorkoutIntensity)) {
    throw new Error("체감 운동 강도를 선택해 주세요.");
  }

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
          exercise_intensity:
            selectedWorkoutIntensity,
          weight_kg:
            getWorkoutRecordWeightKg(),

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
            totalCompletedReps > 0
              ? new Date(
                  (workoutFinishedAt || new Date()).getTime()
                  - workoutActivityTimer.getMilliseconds()
                ).toISOString()
              : null,

          assignment_id:
            coachingAssignmentId,

          workout_plan_id:
            coachingWorkoutPlanId,

          best_image_data_url:
            bestPostureImageDataUrl
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

function setResultStatus(element, message, type = "") {
  element.textContent = message;
  element.className = type ? `result-status-${type}` : "";
  element.setAttribute("role", type === "error" ? "alert" : "status");
}

function showWorkoutResult({
  saveError = null,
  planCompletionError = null,
  noRepetitions = false,
} = {}) {
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
  if (noRepetitions) {
    resultCaloriesLine.textContent = "예상 소모 칼로리 0 kcal";
    resultCaloriesHelp.textContent =
      "완료된 반복이 없어 소모 칼로리를 계산하지 않았어요.";
  } else if (saveError) {
    resultCaloriesLine.textContent = "예상 소모 칼로리 계산되지 않음";
    resultCaloriesHelp.textContent =
      "운동 기록 저장에 성공하면 계산 결과를 확인할 수 있어요.";
  } else if (savedWorkoutResult?.calorie_calculation_status === "WEIGHT_REQUIRED") {
    resultCaloriesLine.textContent =
      "체중을 등록하면 예상 소모 칼로리를 확인할 수 있어요.";
    resultCaloriesHelp.textContent =
      "MET 기준과 체중, 운동시간을 바탕으로 계산한 예상값입니다.";
  } else if (savedWorkoutResult?.calorie_calculation_status === "INVALID_DURATION") {
    resultCaloriesLine.textContent = "운동시간을 확인해 주세요.";
    resultCaloriesHelp.textContent =
      "예상 소모 칼로리를 계산하려면 0분보다 긴 운동시간이 필요합니다.";
  } else {
    resultCaloriesLine.innerHTML =
      `<b>${Number(savedWorkoutResult?.calories ?? 0).toFixed(1)}</b> kcal`;
    resultCaloriesHelp.textContent =
      "MET 기준과 체중, 운동시간을 바탕으로 계산한 예상값입니다.";
  }
  resultFeedbackTitle.textContent = noRepetitions
    ? "완료된 운동이 없어요."
    : savedFeedback.title;
  resultFeedbackText.textContent = noRepetitions
    ? "첫 번째 유효 반복부터 운동시간과 예상 소모 칼로리를 계산해요."
    : savedFeedback.text;

  if (noRepetitions) {
    setResultStatus(
      resultRecordStatus,
      "완료된 반복이 없어 운동 기록을 저장하지 않았어요."
    );
  } else if (saveError) {
    setResultStatus(
      resultRecordStatus,
      `운동 기록을 저장하지 못했어요. ${saveError.message || "다시 시도해 주세요."}`,
      "error"
    );
  } else {
    setResultStatus(resultRecordStatus, "운동 기록을 저장했어요.", "success");
  }

  if (noRepetitions) {
    setResultStatus(
      resultPlanStatus,
      coachingAssignmentId
        ? "PT 숙제를 완료 처리하지 않았어요."
        : coachingWorkoutPlanId
          ? "루틴을 완료 처리하지 않았어요."
          : "자유 코칭 결과를 저장하지 않았어요."
    );
  } else if (coachingAssignmentId) {
    setResultStatus(
      resultPlanStatus,
      saveError
        ? "PT 숙제 반영 여부를 확인하지 못했어요."
        : "PT 숙제 수행 기록으로 반영했어요.",
      saveError ? "error" : "success"
    );
  } else if (!coachingWorkoutPlanId) {
    setResultStatus(resultPlanStatus, "자유 코칭으로 진행한 운동이에요.");
  } else if (planCompletionError) {
    setResultStatus(
      resultPlanStatus,
      "루틴 완료 상태는 반영하지 못했어요. 루틴에서 직접 완료할 수 있어요.",
      "error"
    );
  } else if (planCompletionSucceeded) {
    setResultStatus(resultPlanStatus, "오늘 루틴에 완료로 반영했어요.", "success");
  } else {
    setResultStatus(resultPlanStatus, "루틴 완료 상태를 확인하지 못했어요.");
  }

  document.body.classList.remove(
    "coaching-active",
    "coaching-paused",
    "coaching-intensity-mode"
  );
  document.body.classList.add("coaching-result-mode");
  document.body.dataset.coachingState = saveError
    ? "save-failed"
    : "save-complete";
  pauseButton.hidden = true;
  workoutIntensityStep.hidden = true;
  coachingResult.hidden = false;
  resultRetryButton.hidden = !saveError;
  resultRetryButton.disabled = false;
  resultDashboardButton.hidden = Boolean(saveError);
  resultPrimaryButton.textContent = coachingAssignmentId
    ? "PT 숙제로 돌아가기"
    : coachingWorkoutPlanId
      ? "루틴으로 돌아가기"
      : "대시보드로 이동";
  resultDashboardButton.textContent = coachingWorkoutPlanId
    ? "대시보드로 이동"
    : "기록 보기";
  coachingResult.scrollIntoView({ block: "start" });
  coachingResultTitle.focus({ preventScroll: true });
}

async function finalizeWorkoutMeasurement() {
  if (isWorkoutMeasurementFinalized) {
    return;
  }

  if (workoutMeasurementFinalizationPromise) {
    await workoutMeasurementFinalizationPromise;
    return;
  }

  workoutMeasurementFinalizationPromise = (async () => {
    freezeEffectiveWorkoutTime();
    stopPoseAnalysis();
    isWorkoutActive = false;
    stopCamera();
    await closeCoachingSession().catch((error) => {
      console.error("코칭 세션 종료 실패:", error);
    });
    clearRestTimer();
    isWorkoutMeasurementFinalized = true;
  })();

  try {
    await workoutMeasurementFinalizationPromise;
  } finally {
    workoutMeasurementFinalizationPromise = null;
  }
}

function showWorkoutIntensityStep() {
  isAwaitingIntensity = true;
  workoutIntensityMessage.textContent = "";
  workoutIntensitySummary.textContent =
    `${getTotalRepetitions()}회 · ${currentSets}세트 · ${getWorkoutMinutes()}분 운동을 완료했어요.`;
  document.body.classList.remove(
    "coaching-active",
    "coaching-paused",
    "coaching-result-mode"
  );
  document.body.classList.add("coaching-intensity-mode");
  document.body.dataset.coachingState = "awaiting-intensity";
  pauseButton.hidden = true;
  coachingResult.hidden = true;
  workoutIntensityStep.hidden = false;
  saveWorkoutButton.disabled = selectedWorkoutIntensity === null;
  workoutIntensityStep.scrollIntoView({ block: "start" });
  workoutIntensityTitle.focus({ preventScroll: true });
}

async function finishWorkout() {
  if (
    !isWorkoutFinished
    || isSavingWorkout
    || (isResultDisplayed && !lastWorkoutSaveError)
  ) {
    return;
  }

  finishButton.disabled = true;
  lastWorkoutSaveError = null;
  lastPlanCompletionError = null;

  if (getTotalRepetitions() <= 0) {
    isSavingWorkout = true;
    movementState.textContent = "종료 처리 중";
    document.body.dataset.coachingState = "finishing";
    await finalizeWorkoutMeasurement();
    isSavingWorkout = false;
    showWorkoutResult({ noRepetitions: true });
    return;
  }

  if (!selectedWorkoutIntensity) {
    if (isAwaitingIntensity) {
      return;
    }
    isSavingWorkout = true;
    movementState.textContent = "운동 결과 확정 중";
    document.body.dataset.coachingState = "finishing";
    setOverlayMovement("종료 처리 중");
    setOverlayFeedback("운동 결과를 확정하고 있어요.");
    await finalizeWorkoutMeasurement();
    isSavingWorkout = false;
    showWorkoutIntensityStep();
    return;
  }

  isSavingWorkout = true;
  isAwaitingIntensity = false;
  saveWorkoutButton.disabled = true;
  saveWorkoutButton.setAttribute("aria-busy", "true");
  movementState.textContent = "결과 저장 중";
  document.body.dataset.coachingState = "saving";

  await finalizeWorkoutMeasurement();

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

    lastWorkoutSaveError = error;
  }

  if (!lastWorkoutSaveError && coachingWorkoutPlanId) {
    try {
      await completeLinkedWorkoutPlan();
      planCompletionSucceeded = true;
    } catch (error) {
      lastPlanCompletionError = error;
      planCompletionSucceeded = false;
      console.error(
        "운동 기록은 저장되었지만 계획 완료 처리에 실패했습니다:",
        error
      );
    }
  }

  if (workoutRecordSaved) {
    clearCoachingPlan();
  }
  isSavingWorkout = false;
  saveWorkoutButton.removeAttribute("aria-busy");
  showWorkoutResult({
    saveError: lastWorkoutSaveError,
    planCompletionError: lastPlanCompletionError,
  });
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
    workoutActivityTimer.suspend();
    pauseStartedAt = new Date();
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
    if (pauseStartedAt) {
      accumulatedPausedMilliseconds += Math.max(
        0,
        Date.now() - pauseStartedAt.getTime()
      );
      pauseStartedAt = null;
    }
    isWorkoutPaused = false;
    workoutActivityTimer.resume();
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

workoutIntensityChoices.addEventListener("change", (event) => {
  const input = event.target.closest(
    'input[name="completedExerciseIntensity"]'
  );
  if (!input || !["LOW", "MODERATE", "HIGH"].includes(input.value)) {
    return;
  }
  selectedWorkoutIntensity = input.value;
  workoutIntensityMessage.textContent = "";
  saveWorkoutButton.disabled = false;
});

saveWorkoutButton.addEventListener("click", async () => {
  if (
    isSavingWorkout
    || workoutRecordSaved
  ) {
    return;
  }
  if (!selectedWorkoutIntensity) {
    workoutIntensityMessage.textContent =
      "체감 운동 강도를 선택해 주세요.";
    saveWorkoutButton.disabled = true;
    return;
  }
  await finishWorkout();
});

resultDashboardButton.addEventListener("click", () => {
  window.location.href = coachingWorkoutPlanId ? "/dashboard" : "/records";
});

resultPrimaryButton.addEventListener("click", () => {
  window.location.href = coachingAssignmentId
    ? "/pt/assignments"
    : coachingWorkoutPlanId
      ? "/routine"
      : "/dashboard";
});

resultRetryButton.addEventListener("click", async () => {
  if (isSavingWorkout || workoutRecordSaved) {
    return;
  }
  resultRetryButton.disabled = true;
  setResultStatus(resultRecordStatus, "운동 기록을 다시 저장하고 있어요.");
  await finishWorkout();
});

cameraRetryButton.addEventListener("click", async () => {
  cameraRetryButton.disabled = true;
  try {
    await startWorkout();
  } finally {
    cameraRetryButton.disabled = false;
  }
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
    "운동을 종료하고 현재까지의 결과를 저장할까요?"
  );

  if (!shouldExit) {
    return;
  }

  isWorkoutFinished = true;
  isGoalCompleted = true;
  isCurrentSetCompleted = true;
  clearRestTimer();
  stopPoseAnalysis();
  stopCamera();
  finishButton.disabled = true;
  await finishWorkout();
});


window.addEventListener(
  "beforeunload",
  (event) => {
    clearRestTimer();
    stopCamera();
    closeCoachingSession({ keepalive: true }).catch(() => {});

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
  const requestedReps = Number(params.get("reps"));
  const requestedSets = Number(params.get("sets"));
  const hasRequestedFreeTarget = (
    Number.isInteger(requestedReps)
    && requestedReps >= 1
    && requestedReps <= 100
    && Number.isInteger(requestedSets)
    && requestedSets >= 1
    && requestedSets <= 20
  );
  const requestedAssignmentId = Number(params.get("assignment_id"));
  const isPtAssignmentRequest = params.get("source") === "PT_ASSIGNMENT"
    && Number.isInteger(requestedAssignmentId)
    && requestedAssignmentId > 0;

  startButton.disabled = true;
  coachingSettingsCard.hidden = true;
  setProgressCard.hidden = true;
  coachingModeLoading.hidden = false;

  if (isPtAssignmentRequest) {
    try {
      const userId = getLoginUserId();
      if (!userId) {
        throw new Error("로그인 정보가 없습니다.");
      }
      const response = await fetch(
        `/api/pt/assignments/member/${requestedAssignmentId}`,
        { headers: { "X-User-Id": String(userId) } }
      );
      const assignment = await response.json().catch(() => null);
      if (!response.ok) {
        throw new Error(assignment?.detail || "PT 숙제를 확인하지 못했습니다.");
      }
      const code = String(assignment.exercise_code || "").toUpperCase();
      const setCount = Number(assignment.target_sets);
      const repetitions = Number(assignment.target_reps);
      if (!isCoachingExerciseCode(code) || setCount < 1 || repetitions < 1
          || !["ASSIGNED", "IN_PROGRESS"].includes(assignment.status)) {
        throw new Error("실시간 코칭으로 수행할 수 없는 PT 숙제입니다.");
      }
      selectExerciseTab(code);
      coachingAssignmentId = assignment.assignment_id;
      coachingAssignment = assignment;
      coachingWorkoutPlanId = null;
      coachingContext = COACHING_CONTEXT.PT_ASSIGNMENT;
      clearCoachingPlan();
      coachingSets = Array.from({ length: setCount }, (_, index) => ({
        set_order: index + 1,
        repetition_count: repetitions,
        duration_seconds: null,
        weight_kg: normalizeRecordWeightKg(assignment.weight_kg),
      }));
      targetSets = setCount;
      targetReps = repetitions;
      totalTargetReps = setCount * repetitions;
      isPlanCoaching = true;
      freeCoachingSettings.hidden = true;
      routineCoachingSets.hidden = false;
      renderRoutineCoachingSets();
      coachingSettingsEyebrow.textContent = "PT ASSIGNMENT";
      coachingSettingsTitle.textContent = assignment.title;
      coachingModeLabel.textContent = "PT 숙제";
      coachingPlanMeta.textContent = `${assignment.trainer_name} 트레이너 · ${setCount}세트 × ${repetitions}회`;
      ptAssignmentContext.hidden = false;
      ptAssignmentSummary.textContent = `${assignment.title} · ${assignment.trainer_name} 트레이너`;
      finishModeLoading();
      updateTargetDisplay();
      updateCounterDisplay();
      return;
    } catch (error) {
      console.error("PT 숙제 코칭 초기화 실패:", error);
      alert(error.message);
      window.location.replace("/pt/assignments");
      return;
    }
  }

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
  if (hasRequestedFreeTarget && !validSavedPlan) {
    freeCoachingRows = Array.from(
      { length: requestedSets },
      (_, index) => ({
        set_order: index + 1,
        repetition_count: requestedReps,
        weight_kg: 0,
      })
    );
    saveFreeCoachingSets();
    clearCoachingPlan();
    prepareFreeCoaching();
  } else {
    applySelectedExerciseMode();
  }

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
