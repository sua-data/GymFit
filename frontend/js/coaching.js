const exerciseTabs =
  document.querySelectorAll(
    ".exercise-tab"
  );

const targetRepsSelect =
  document.querySelector(
    "#targetRepsSelect"
  );

const targetSetsSelect =
  document.querySelector(
    "#targetSetsSelect"
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


let selectedExerciseCode =
  "SQUAT";

let selectedExerciseName =
  "스쿼트";

let targetReps = 10;
let targetSets = 3;

let currentReps = 0;
let currentSets = 0;

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


/* =========================
   전달받은 운동 및 목표
========================= */

function selectOrAddOption(
  selectElement,
  value,
  suffix
) {
  if (
    !Number.isInteger(value)
    || value <= 0
  ) {
    return null;
  }

  const optionExists =
    Array.from(
      selectElement.options
    ).some(
      (option) =>
        Number(option.value)
        === value
    );

  if (!optionExists) {
    const option =
      document.createElement(
        "option"
      );

    option.value = String(value);
    option.textContent =
      `${value}${suffix}`;

    selectElement.appendChild(
      option
    );
  }

  selectElement.value =
    String(value);

  return value;
}


function applyCoachingQuery() {
  const params =
    new URLSearchParams(
      window.location.search
    );

  const hasExerciseCode =
    params.has("exercise_code");

  const hasReps =
    params.has("reps");

  const hasSets =
    params.has("sets");

  const exerciseCode =
    params.get(
      "exercise_code"
    );

  const requestedReps =
    Number(params.get("reps"));

  const requestedSets =
    Number(params.get("sets"));

  const targetTab =
    Array.from(
      exerciseTabs
    ).find(
      (tab) =>
        tab.dataset.exerciseCode
        === exerciseCode
    );

  if (
    !hasExerciseCode
    || !hasReps
    || !hasSets
    || !targetTab
    || !Number.isInteger(
      requestedReps
    )
    || requestedReps <= 0
    || !Number.isInteger(
      requestedSets
    )
    || requestedSets <= 0
  ) {
    return false;
  }

  exerciseTabs.forEach(
    (tab) => {
      tab.classList.remove(
        "active"
      );
    }
  );

  targetTab.classList.add(
    "active"
  );

  selectedExerciseCode =
    targetTab.dataset.exerciseCode;

  selectedExerciseName =
    targetTab.dataset.exerciseName;

  const appliedReps =
    selectOrAddOption(
      targetRepsSelect,
      requestedReps,
      "회"
    );

  if (appliedReps !== null) {
    targetReps = appliedReps;
  }

  const appliedSets =
    selectOrAddOption(
      targetSetsSelect,
      requestedSets,
      "세트"
    );

  if (appliedSets !== null) {
    targetSets = appliedSets;
  }

  return (
    appliedReps !== null
    && appliedSets !== null
  );
}


async function applyTodaySquatPlan() {
  const userId =
    getLoginUserId();

  if (!userId) {
    return false;
  }

  try {
    const response =
      await fetch(
        `/api/workouts/plans/today/${userId}`
      );

    if (!response.ok) {
      return false;
    }

    const data =
      await response.json();

    const squatPlan =
      data.items?.find(
        (item) =>
          item.exercise_code
          === "SQUAT"
          && item.ai_coaching_supported
      );

    if (!squatPlan) {
      return false;
    }

    const squatTab =
      Array.from(
        exerciseTabs
      ).find(
        (tab) =>
          tab.dataset.exerciseCode
          === "SQUAT"
      );

    if (!squatTab) {
      return false;
    }

    const plannedReps =
      Number(
        squatPlan.repetition_count
      );

    const plannedSets =
      Number(
        squatPlan.set_count
      );

    if (
      !Number.isInteger(plannedReps)
      || plannedReps <= 0
      || !Number.isInteger(plannedSets)
      || plannedSets <= 0
    ) {
      return false;
    }

    const appliedReps =
      selectOrAddOption(
        targetRepsSelect,
        plannedReps,
        "회"
      );

    const appliedSets =
      selectOrAddOption(
        targetSetsSelect,
        plannedSets,
        "세트"
      );

    if (
      appliedReps === null
      || appliedSets === null
    ) {
      return false;
    }

    exerciseTabs.forEach(
      (tab) => {
        tab.classList.remove(
          "active"
        );
      }
    );

    squatTab.classList.add(
      "active"
    );

    selectedExerciseCode =
      squatTab.dataset.exerciseCode;

    selectedExerciseName =
      squatTab.dataset.exerciseName;

    targetReps = appliedReps;
    targetSets = appliedSets;

    return true;

  } catch (error) {
    console.error(
      "오늘의 코칭 목표 조회 실패:",
      error
    );

    return false;
  }
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
  targetReps =
    Number(
      targetRepsSelect.value
    );

  targetSets =
    Number(
      targetSetsSelect.value
    );

  targetRepCount.textContent =
    targetReps;

  targetSetCount.textContent =
    targetSets;
}


function updateCounterDisplay() {
  currentRepCount.textContent =
    currentReps;

  currentSetCount.textContent =
    currentSets;
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
  ) {
    return;
  }

  postureScores.push(score);

  currentReps += 1;

  movementState.textContent =
    `${selectedExerciseName} ${currentReps}회`;

  if (currentReps >= targetReps) {
    currentSets += 1;
    currentReps = 0;

    movementState.textContent =
      `${currentSets}세트 완료`;

    updateCounterDisplay();
    updatePostureFeedback(score);

    if (
      currentSets >= targetSets
    ) {
      finishWorkoutAutomatically();
      return;
    }

    return;
  }

  updateCounterDisplay();
  updatePostureFeedback(score);
}


/* =========================
   스쿼트 분석 API
========================= */

function getPostureScoreFromStatus(
  status
) {
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
    movementState.textContent =
      status.stage === "DOWN"
        ? `${selectedExerciseName} 내려가는 중`
        : `${selectedExerciseName} 일어서는 중`;

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

    const angleTexts = [];

    if (status.average_angle !== null) {
      angleTexts.push(
        `무릎 ${Math.round(
          status.average_angle
        )}도`
      );
    }

    if (status.torso_angle !== null) {
      angleTexts.push(
        `상체 기울기 ${Math.round(
          status.torso_angle
        )}도`
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

  feedbackText.textContent =
    status.person_valid
      ? "엉덩이, 무릎, 발목이 모두 보이도록 위치를 조정하세요."
      : "카메라에 전신이 나오도록 이동하세요.";
}


async function sendFrameForAnalysis() {
  if (
    !isWorkoutActive
    || selectedExerciseCode !== "SQUAT"
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
      "squat-frame.jpg"
    );

    const response =
      await fetch(
        "/api/coaching/squat/analyze",
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
      "스쿼트 자세 분석 실패:",
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


async function resetSquatAnalyzer() {
  const response =
    await fetch(
      "/api/coaching/squat/reset",
      {
        method: "POST"
      }
    );

  const data =
    await response.json();

  if (!response.ok) {
    throw new Error(
      data.detail
      || "스쿼트 분석 상태를 초기화하지 못했습니다."
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
      selectedExerciseCode
      !== "SQUAT"
    ) {
      throw new Error(
        "현재 AI 자세 분석은 스쿼트만 지원합니다."
      );
    }

    currentReps = 0;
    currentSets = 0;

    postureScores = [];

    updateCounterDisplay();

    await startCamera();
    await resetSquatAnalyzer();

    workoutStartedAt =
      new Date();

    isWorkoutActive = true;
    isGoalCompleted = false;

    startPoseAnalysis();

    movementState.textContent =
      "운동 중";

    postureStatus.textContent =
      "ACTIVE";

    feedbackTitle.textContent =
      "자세 분석을 시작합니다.";

    feedbackText.textContent =
      "카메라에 전신이 보이도록 유지하세요.";

    startButton.disabled = true;
    finishButton.disabled = false;

    targetRepsSelect.disabled = true;
    targetSetsSelect.disabled = true;

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
  return (
    currentSets * targetReps
    + currentReps
  );
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


/* =========================
   운동 종료
========================= */

async function finishWorkout() {
  if (!isWorkoutActive) {
    return;
  }

  finishButton.disabled = true;

  stopPoseAnalysis();

  movementState.textContent =
    "저장 중";

  try {
    const result =
      await saveWorkoutRecord();

    isWorkoutActive = false;

    stopCamera();

    alert(
      result.message
      || "운동 기록이 저장되었습니다."
    );

    window.location.href =
      "/dashboard";

  } catch (error) {
    console.error(
      "운동 저장 실패:",
      error
    );

    alert(
      error.message
      || "운동 기록을 저장하지 못했습니다."
    );

    finishButton.disabled = false;

    movementState.textContent =
      "운동 중";

    startPoseAnalysis();
  }
}


/* =========================
   목표 완료
========================= */

function finishWorkoutAutomatically() {
  isGoalCompleted = true;

  stopPoseAnalysis();

  movementState.textContent =
    "운동 완료";

  postureStatus.textContent =
    "COMPLETE";

  feedbackTitle.textContent =
    "목표 운동을 완료했습니다.";

  feedbackText.textContent =
    "운동 종료 버튼을 눌러 기록을 저장하세요.";

  startButton.disabled = true;
  finishButton.disabled = false;
}


/* =========================
   운동 선택
========================= */

exerciseTabs.forEach(
  (tab) => {
    tab.addEventListener(
      "click",
      () => {
        exerciseTabs.forEach(
          (item) => {
            item.classList.remove(
              "active"
            );
          }
        );

        tab.classList.add(
          "active"
        );

        selectedExerciseCode =
          tab.dataset.exerciseCode;

        selectedExerciseName =
          tab.dataset.exerciseName;

        movementState.textContent =
          `${selectedExerciseName} 준비`;
      }
    );
  }
);


/* =========================
   이벤트
========================= */

targetRepsSelect.addEventListener(
  "change",
  updateTargetDisplay
);


targetSetsSelect.addEventListener(
  "change",
  updateTargetDisplay
);


startButton.addEventListener(
  "click",
  startWorkout
);


finishButton.addEventListener(
  "click",
  finishWorkout
);


window.addEventListener(
  "beforeunload",
  (event) => {
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
  const urlTargetApplied =
    applyCoachingQuery();

  if (!urlTargetApplied) {
    await applyTodaySquatPlan();
  }

  updateTargetDisplay();
  updateCounterDisplay();
}


initializeCoachingTargets();
