const userName =
  document.querySelector("#userName");

const caloriesValue =
  document.querySelector("#caloriesValue");

const workoutMinutesValue =
  document.querySelector("#workoutMinutesValue");

const completedSetsValue =
  document.querySelector("#completedSetsValue");

const streakValue =
  document.querySelector("#streakValue");

const bestExerciseSelect =
  document.querySelector("#bestExerciseSelect");

const bestFrame =
  document.querySelector("#bestFrame");

const bestFrameImage =
  document.querySelector("#bestFrameImage");

const bestFrameCaption =
  document.querySelector("#bestFrameCaption");

const frameScoreValue =
  document.querySelector("#frameScoreValue");

const exerciseName =
  document.querySelector("#exerciseName");

const repCount =
  document.querySelector("#repCount");

const setCount =
  document.querySelector("#setCount");

const postureScore =
  document.querySelector("#postureScore");

const scoreRingValue =
  document.querySelector("#scoreRingValue");

const scoreRing =
  document.querySelector("#scoreRing");

const feedbackTitle =
  document.querySelector("#feedbackTitle");

const feedbackText =
  document.querySelector("#feedbackText");

const workoutPlanList =
  document.querySelector("#workoutPlanList");

const planTotal =
  document.querySelector("#planTotal");

const coachingButton =
  document.querySelector(".coaching-button");

const weeklyWorkoutDays =
  document.querySelector("#weeklyWorkoutDays");

const weeklyWorkoutMinutes =
  document.querySelector("#weeklyWorkoutMinutes");

const weeklyGoalText =
  document.querySelector("#weeklyGoalText");

const weeklyBars =
  document.querySelector("#weeklyBars");

const weeklyProgressTrack =
  document.querySelector("#weeklyProgressTrack");

const weeklyProgressText =
  document.querySelector("#weeklyProgressText");

const recentWorkoutList =
  document.querySelector("#recentWorkoutList");

const nextPtSchedule =
  document.querySelector("#nextPtSchedule");

const nextPtScheduleCard =
  document.querySelector("#nextPtScheduleCard");

const nextPtScheduleLink =
  document.querySelector("#nextPtScheduleLink");

const imageModal =
  document.querySelector("#imageModal");

const imageModalBackdrop =
  document.querySelector("#imageModalBackdrop");

const imageModalClose =
  document.querySelector("#imageModalClose");

const imageModalPhoto =
  document.querySelector("#imageModalPhoto");

const imageModalCaption =
  document.querySelector("#imageModalCaption");

const bestFramePlaceholder =
  document.querySelector(
    "#bestFramePlaceholder"
  );

const bestBadge =
  document.querySelector("#bestBadge");

const frameScore =
  document.querySelector("#frameScore");

let postureList = [];


/* =========================
   JSON 응답 처리
========================= */

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}


/* =========================
   API 오류 처리
========================= */

function getErrorMessage(
  data,
  fallbackMessage
) {
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  return fallbackMessage;
}


/* =========================
   로그인 사용자 번호
========================= */

function getLoginUserId() {
  const savedUser =
    sessionStorage.getItem("gymfitUser");

  if (!savedUser) {
    return null;
  }

  try {
    const loginUser =
      JSON.parse(savedUser);

    return loginUser.user_id || null;

  } catch {
    return null;
  }
}


/* =========================
   대시보드 API 요청
========================= */

async function requestDashboardData() {
  const userId = getLoginUserId();

  if (!userId) {
    throw new Error(
      "로그인 정보가 없습니다."
    );
  }

  const response = await fetch(
    `/api/dashboard/${userId}`
  );

  const data =
    await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "대시보드 정보를 불러오지 못했습니다."
      )
    );
  }

  return data;
}

/* =========================
   사용자 및 요약
========================= */

function renderSummary(data) {
  userName.textContent =
    data.user?.name || "-";

  caloriesValue.textContent =
    data.summary?.calories ?? 0;

  workoutMinutesValue.textContent =
    data.summary?.workout_minutes ?? 0;

  completedSetsValue.textContent =
    data.summary?.completed_sets ?? 0;

  streakValue.textContent =
    data.summary?.streak_days ?? 0;
}


/* =========================
   종목 선택 목록
========================= */

function renderExerciseOptions(postures) {
  bestExerciseSelect.innerHTML = "";

  postures.forEach((posture) => {
    const option =
      document.createElement("option");

    option.value =
      posture.exercise_code;

    option.textContent =
      posture.exercise_name;

    bestExerciseSelect.appendChild(
      option
    );
  });

  bestExerciseSelect.disabled =
    postures.length === 0;
}


/* =========================
   점수 그래프
========================= */

function updateScoreRing(score) {
  const safeScore = Math.max(
    0,
    Math.min(100, Number(score) || 0)
  );

  scoreRing.style.background = `
    conic-gradient(
      #a8ff35 ${safeScore}%,
      #3a3a3a ${safeScore}% 100%
    )
  `;
}


/* =========================
   베스트 자세 표시
========================= */

function renderBestPosture(
  exerciseCode
) {
  const posture =
    postureList.find(
      (item) =>
        item.exercise_code ===
        exerciseCode
    );

  if (!posture) {
    renderEmptyPosture();
    return;
  }

  if (posture.image_url) {
    bestFrameImage.src =
      posture.image_url;

    bestFrameImage.alt =
      `${posture.exercise_name} 베스트 자세`;

    bestFrameImage.hidden = false;
    bestFramePlaceholder.hidden = true;

    bestBadge.hidden = false;
    frameScore.hidden = false;

  } else {
    bestFrameImage.removeAttribute("src");
    bestFrameImage.hidden = true;

    bestFramePlaceholder.hidden = false;
    bestFramePlaceholder.textContent =
      "저장된 베스트 자세 이미지가 없습니다.";

    bestBadge.hidden = true;
    frameScore.hidden = true;
  }

  bestFrameCaption.textContent =
    `${posture.exercise_name} 베스트 자세`;

  frameScoreValue.textContent =
    posture.posture_score ?? 0;

  exerciseName.textContent =
    posture.exercise_name || "-";

  repCount.textContent =
    posture.repetition_count ?? 0;

  setCount.textContent =
    posture.completed_sets ?? 0;

  postureScore.textContent =
    posture.posture_score ?? 0;

  scoreRingValue.textContent =
    posture.posture_score ?? 0;

  feedbackTitle.textContent =
    posture.feedback_title ||
    "분석 결과가 없습니다.";

  feedbackText.textContent =
    posture.feedback ||
    "운동을 완료하면 자세 분석 결과가 표시됩니다.";

  updateScoreRing(
    posture.posture_score
  );
}


/* =========================
   베스트 자세 없음
========================= */

function renderEmptyPosture() {
  bestFrameImage.removeAttribute("src");
  bestFrameImage.hidden = true;

  bestFramePlaceholder.hidden = false;
  bestFramePlaceholder.textContent =
    "아직 분석 기록이 없습니다.";

  bestFrameCaption.textContent =
    "저장된 베스트 자세가 없습니다.";

  frameScoreValue.textContent = "0";
  exerciseName.textContent = "-";
  repCount.textContent = "0";
  setCount.textContent = "0";
  postureScore.textContent = "0";
  scoreRingValue.textContent = "0";

  feedbackTitle.textContent =
    "아직 분석 기록이 없습니다.";

  feedbackText.textContent =
    "실시간 자세 코칭을 시작해 운동 기록을 만들어 보세요.";

  updateScoreRing(0);
}


/* =========================
   오늘의 운동 계획
========================= */

function renderWorkoutPlan(planData) {
  workoutPlanList.innerHTML = "";

  const items =
    planData?.items || [];

  if (items.length === 0) {
    workoutPlanList.innerHTML = `
      <li class="empty-message">
        오늘 등록된 운동 계획이 없습니다.
      </li>
    `;

    planTotal.textContent =
      "예상 시간 0분";

    return;
  }

  items.forEach((item) => {
    const listItem =
      document.createElement("li");

    listItem.innerHTML = `
      <span class="plan-dot"></span>

      <div>
        <strong>
          ${escapeHtml(item.exercise_name)}
        </strong>

        <small>
          ${Number(item.set_count) || 0}세트
        </small>
      </div>
    `;

    workoutPlanList.appendChild(
      listItem
    );
  });

  planTotal.textContent =
    `예상 시간 ${
      planData.total_minutes ?? 0
    }분`;
}


/* =========================
   주간 기록
========================= */

function renderWeeklyData(data) {
  const workoutDays =
    Number(data?.workout_days) || 0;

  const weeklyGoalDays =
    Number.isInteger(Number(data?.weekly_workout_days))
    && Number(data?.weekly_workout_days) >= 1
    && Number(data?.weekly_workout_days) <= 7
      ? Number(data.weekly_workout_days)
      : null;

  weeklyWorkoutDays.textContent =
    workoutDays;

  weeklyWorkoutMinutes.textContent =
    `총 ${data?.total_minutes ?? 0}분`;

  weeklyGoalText.textContent =
    weeklyGoalDays === null
      ? "주간 목표 미설정"
      : `목표 주 ${weeklyGoalDays}회 · 이번 주 ${workoutDays}회`;

  weeklyBars.innerHTML = "";

  const days =
    data?.days || [];

  days.forEach((day) => {
    const item =
      document.createElement("div");

    const height =
      Math.max(
        6,
        Math.min(
          100,
          Number(day.percent) || 0
        )
      );

    item.innerHTML = `
      <span
        class="${day.completed ? "active" : ""}"
        style="height: ${height}%"
      ></span>

      <small>
        ${escapeHtml(day.label)}
      </small>
    `;

    weeklyBars.appendChild(item);
  });

  const progressPercent =
    weeklyGoalDays !== null
      ? Math.min(
          100,
          workoutDays / weeklyGoalDays * 100
        )
      : 0;

  weeklyProgressTrack.style.width =
    `${progressPercent}%`;

  weeklyProgressText.textContent =
    weeklyGoalDays === null
      ? "목표 미설정"
      : `${workoutDays} / ${weeklyGoalDays}일`;
}


/* =========================
   최근 운동 기록
========================= */

function renderRecentWorkouts(workouts) {
  recentWorkoutList.innerHTML = "";

  if (!workouts?.length) {
    recentWorkoutList.innerHTML = `
      <div class="empty-message">
        최근 운동 기록이 없습니다.
      </div>
    `;

    return;
  }

  workouts.forEach((workout) => {
    const button =
      document.createElement("button");

    button.type = "button";
    button.className =
      "recent-workout-item";

    const isPt = workout.record_type === "PT";
    const imageMarkup = workout.image_url ? `<img
        src="${escapeAttribute(
          workout.image_url
        )}"
        alt="${escapeAttribute(
          workout.exercise_name
        )}"
      >` : "";
    const ptDetail = isPt
      ? [workout.trainer_name && `${workout.trainer_name} 트레이너`, ...(workout.exercise_names || []).slice(0, 2)].filter(Boolean).join(" · ")
      : `${Number(workout.completed_sets) || 0}세트`;

    button.innerHTML = `
      ${imageMarkup}

      <div class="recent-workout-info">
        <strong>
          ${escapeHtml(
            workout.exercise_name
          )}
        </strong>

        <span>
          ${escapeHtml(
            workout.workout_date_text
          )}
          ·
          ${escapeHtml(ptDetail || `${Number(workout.workout_minutes) || 0}분`)}
        </span>
      </div>

      <div class="recent-workout-result">
        <span${isPt ? ' class="pt-record-badge"' : ""}>
          <strong>
            ${isPt ? "PT" : Number(workout.repetition_count) || 0}
          </strong>
          ${isPt ? "" : "회"}
        </span>

        <span>
          ${workout.average_posture_score === null || workout.average_posture_score === undefined
            ? `${Number(workout.workout_minutes) || 0}분`
            : `<strong>${Number(workout.average_posture_score)}</strong>점`}
        </span>
      </div>

      <span class="recent-arrow">
        ›
      </span>
    `;

    button.addEventListener(
      "click",
      () => {
        window.location.href =
          `/records/${workout.workout_id}`;
      }
    );

    recentWorkoutList.appendChild(
      button
    );
  });
}


/* =========================
   이미지 확대
========================= */

function openImageModal() {
  if (
    bestFrameImage.hidden
    || !bestFrameImage.getAttribute("src")
  ) {
    return;
  }

  imageModalPhoto.src =
    bestFrameImage.src;

  imageModalPhoto.alt =
    bestFrameImage.alt;

  imageModalCaption.textContent =
    bestFrameCaption.textContent;

  imageModal.hidden = false;

  document.body.style.overflow =
    "hidden";
}


function closeImageModal() {
  imageModal.hidden = true;
  document.body.style.overflow = "";
}


/* =========================
   HTML 문자 처리
========================= */

function escapeHtml(value) {
  const element =
    document.createElement("div");

  element.textContent =
    value ?? "";

  return element.innerHTML;
}


function escapeAttribute(value) {
  return escapeHtml(value)
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#39;");
}


/* =========================
   전체 렌더링
========================= */

function renderDashboard(data) {
  renderSummary(data);

  postureList =
    data.best_postures || [];

  renderExerciseOptions(
    postureList
  );

  if (postureList.length > 0) {
    renderBestPosture(
      postureList[0].exercise_code
    );
  } else {
    renderEmptyPosture();
  }

  renderWorkoutPlan(
    data.today_plan
  );

  renderWeeklyData(
    data.weekly_summary
  );

  renderRecentWorkouts(
    data.recent_workouts
  );

  renderNextPtSchedule(data);
}


function renderNextPtSchedule(data) {
  if (!nextPtScheduleCard || !nextPtSchedule || !nextPtScheduleLink) return;
  const accountType = String(data.account_type || "").toUpperCase();
  const shouldShow = accountType === "TRAINER"
    || (accountType === "MEMBER" && data.has_active_trainer === true);
  if (!shouldShow) {
    nextPtScheduleCard.remove();
    return;
  }
  nextPtScheduleCard.hidden = false;
  const item = data.next_pt_schedule;
  nextPtScheduleLink.href = item?.target_url || (data.account_type === "TRAINER" ? "/trainer/schedules" : "/pt/schedules");
  nextPtSchedule.replaceChildren();
  if (!item) {
    nextPtSchedule.className = "empty-message";
    nextPtSchedule.textContent = "예정된 PT 일정이 없습니다.";
    return;
  }
  nextPtSchedule.className = "next-pt-dashboard-content";
  const date = new Date(item.start_at);
  const end = new Date(item.end_at);
  const formatter = new Intl.DateTimeFormat("ko-KR", { month:"long", day:"numeric", weekday:"short", hour:"2-digit", minute:"2-digit", hour12:false });
  const timeFormatter = new Intl.DateTimeFormat("ko-KR", { hour:"2-digit", minute:"2-digit", hour12:false });
  const title = document.createElement("strong");
  title.textContent = formatter.format(date);
  const person = document.createElement("p");
  person.textContent = `${item.person_name} ${item.person_label} · ${timeFormatter.format(date)} ~ ${timeFormatter.format(end)}`;
  nextPtSchedule.append(title, person);
  if (item.memo) {
    const detail = document.createElement("p");
    detail.textContent = item.memo;
    nextPtSchedule.append(detail);
  }
}


/* =========================
   이벤트
========================= */

bestExerciseSelect.addEventListener(
  "change",
  (event) => {
    renderBestPosture(
      event.target.value
    );
  }
);


bestFrame.addEventListener(
  "click",
  openImageModal
);


bestFrame.addEventListener(
  "keydown",
  (event) => {
    if (
      event.key === "Enter"
      || event.key === " "
    ) {
      event.preventDefault();
      openImageModal();
    }
  }
);


imageModalClose.addEventListener(
  "click",
  closeImageModal
);


imageModalBackdrop.addEventListener(
  "click",
  closeImageModal
);


window.addEventListener(
  "keydown",
  (event) => {
    if (
      event.key === "Escape"
      && !imageModal.hidden
    ) {
      closeImageModal();
    }
  }
);

/* =========================
   초기 실행
========================= */

window.addEventListener(
  "commonLayoutReady",
  async () => {
    try {
      const data =
        await requestDashboardData();

      renderDashboard(data);

    } catch (error) {
      console.error(
        "대시보드 로딩 실패:",
        error
      );
    }
  }
);


coachingButton.addEventListener(
  "click",
  async (event) => {
    event.preventDefault();

    const userId = getLoginUserId();

    if (!userId) {
      window.location.href = "/login";
      return;
    }

    coachingButton.setAttribute("aria-busy", "true");

    try {
      const response = await fetch(
        `/api/workouts/plans/today/${userId}`
      );

      if (response.ok) {
        const data = await response.json();
        const coachingPlans = (data.items || []).filter(
          (item) =>
            item.ai_coaching_supported
            && Array.isArray(item.sets)
            && item.sets.some(
              (set) => Number(set.repetition_count || 0) > 0
            )
        );

        if (coachingPlans.length === 1) {
          saveCoachingPlan(coachingPlans[0]);
        } else {
          clearCoachingPlan();
        }
      } else {
        clearCoachingPlan();
      }
    } catch (error) {
      console.error("코칭 계획 조회 실패:", error);
      clearCoachingPlan();
    } finally {
      coachingButton.removeAttribute("aria-busy");
      window.location.href = "/coaching";
    }
  }
);
