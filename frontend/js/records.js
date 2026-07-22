const recordFilters = document.querySelectorAll("[data-period]");
const recordTotalCount = document.querySelector("#recordTotalCount");
const recordsLoading = document.querySelector("#recordsLoading");
const recordsEmpty = document.querySelector("#recordsEmpty");
const recordsError = document.querySelector("#recordsError");
const recordsErrorMessage = document.querySelector("#recordsErrorMessage");
const recordsRetryButton = document.querySelector("#recordsRetryButton");
const recordsList = document.querySelector("#recordsList");

const recordDetailOverlay = document.querySelector("#recordDetailOverlay");
const recordDetailBackdrop = document.querySelector("#recordDetailBackdrop");
const recordDetailClose = document.querySelector("#recordDetailClose");
const recordDetailTitle = document.querySelector("#recordDetailTitle");
const recordDetailLoading = document.querySelector("#recordDetailLoading");
const recordDetailError = document.querySelector("#recordDetailError");
const recordDetailErrorMessage = document.querySelector("#recordDetailErrorMessage");
const recordDetailContent = document.querySelector("#recordDetailContent");
const detailDate = document.querySelector("#detailDate");
const detailTime = document.querySelector("#detailTime");
const detailScore = document.querySelector("#detailScore");
const detailStartedAt = document.querySelector("#detailStartedAt");
const detailCompletedAt = document.querySelector("#detailCompletedAt");
const detailSets = document.querySelector("#detailSets");
const detailRepetitions = document.querySelector("#detailRepetitions");
const detailMinutes = document.querySelector("#detailMinutes");
const detailCalories = document.querySelector("#detailCalories");
const detailFeedbackTitle = document.querySelector("#detailFeedbackTitle");
const detailFeedback = document.querySelector("#detailFeedback");
const detailImage = document.querySelector("#detailImage");
const detailImageEmpty = document.querySelector("#detailImageEmpty");

let selectedPeriod = "all";
let activeDetailId = null;
let detailRequestId = 0;

function getLoginUserId() {
  const savedUser = sessionStorage.getItem("gymfitUser");
  if (!savedUser) {
    return null;
  }

  try {
    const user = JSON.parse(savedUser);
    const userId = Number(user.user_id ?? user.userId);
    return Number.isInteger(userId) && userId > 0 ? userId : null;
  } catch {
    return null;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function safeNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function parseLocalDateTime(value) {
  const match = String(value || "").match(
    /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})(?::(\d{2}))?/
  );
  if (!match) {
    return null;
  }

  const [, year, month, day, hour, minute, second = "0"] = match;
  return new Date(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
    Number(second)
  );
}

function formatDate(value) {
  const date = parseLocalDateTime(value);
  if (!date) {
    return "날짜 정보 없음";
  }
  return new Intl.DateTimeFormat("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    weekday: "short",
  }).format(date);
}

function formatTime(value) {
  const date = parseLocalDateTime(value);
  if (!date) {
    return "-";
  }
  return new Intl.DateTimeFormat("ko-KR", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);
}

function getErrorMessage(data, fallback) {
  if (typeof data?.detail === "string") {
    return data.detail;
  }
  return fallback;
}

async function readJson(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function setListState(state, message = "") {
  recordsLoading.hidden = state !== "loading";
  recordsEmpty.hidden = state !== "empty";
  recordsError.hidden = state !== "error";
  recordsList.hidden = state !== "ready";
  if (state === "error") {
    recordsErrorMessage.textContent = message || "잠시 후 다시 시도해 주세요.";
  }
}

function renderScore(score) {
  if (score === null || score === undefined) {
    return `
      <div class="record-score unmeasured">
        <b>측정 없음</b>
      </div>
    `;
  }

  return `
    <div class="record-score">
      <b>${Math.round(safeNumber(score))}</b>
      <span>점</span>
    </div>
  `;
}

function renderRecords(data) {
  recordTotalCount.textContent = String(safeNumber(data.total));
  recordsList.innerHTML = "";

  if (!Array.isArray(data.items) || data.items.length === 0) {
    setListState("empty");
    return;
  }

  data.items.forEach((item) => {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "record-card";
    card.dataset.recordId = String(item.workout_record_id);
    card.innerHTML = `
      <div class="record-card-heading">
        <span>${escapeHtml(item.exercise_code || "WORKOUT")}</span>
        <h2>${escapeHtml(item.exercise_name || "운동 기록")}</h2>
        <p>${escapeHtml(formatDate(item.started_at))} · ${escapeHtml(formatTime(item.started_at))}</p>
      </div>
      ${renderScore(item.posture_score)}
      <div class="record-card-metrics">
        <span><b>${safeNumber(item.completed_sets)}</b>세트</span>
        <span><b>${safeNumber(item.repetition_count)}</b>회</span>
        <span><b>${safeNumber(item.workout_minutes)}</b>분</span>
        <span><b>${safeNumber(item.calories)}</b>kcal</span>
        <span><b>${escapeHtml(formatTime(item.completed_at))}</b>종료</span>
        <span><b>›</b>상세</span>
      </div>
    `;
    card.addEventListener("click", () => openRecordDetail(item.workout_record_id));
    recordsList.appendChild(card);
  });

  setListState("ready");
}

async function loadRecords() {
  const userId = getLoginUserId();
  if (!userId) {
    window.location.href = "/login";
    return;
  }

  setListState("loading");
  const params = new URLSearchParams({
    user_id: String(userId),
    period: selectedPeriod,
    limit: "100",
    offset: "0",
  });

  try {
    const response = await fetch(`/api/workouts/records?${params.toString()}`);
    const data = await readJson(response);
    if (!response.ok) {
      throw new Error(getErrorMessage(data, "운동 기록을 불러오지 못했습니다."));
    }
    renderRecords(data);
  } catch (error) {
    console.error("운동 기록 조회 실패:", error);
    setListState("error", error.message);
  }
}

function setDetailState(state, message = "") {
  recordDetailLoading.hidden = state !== "loading";
  recordDetailError.hidden = state !== "error";
  recordDetailContent.hidden = state !== "ready";
  if (state === "error") {
    recordDetailErrorMessage.textContent = message || "잠시 후 다시 시도해 주세요.";
  }
}

function setDetailImage(imageUrl, exerciseName) {
  detailImage.removeAttribute("src");
  detailImage.hidden = true;
  detailImageEmpty.hidden = false;

  if (!imageUrl) {
    return;
  }

  detailImage.onload = () => {
    detailImage.hidden = false;
    detailImageEmpty.hidden = true;
  };
  detailImage.onerror = () => {
    detailImage.removeAttribute("src");
    detailImage.hidden = true;
    detailImageEmpty.hidden = false;
  };
  detailImage.alt = `${exerciseName || "운동"} 베스트 자세 이미지`;
  detailImage.src = imageUrl;
}

function renderRecordDetail(item) {
  const exerciseName = item.exercise_name || "운동 기록";
  recordDetailTitle.textContent = exerciseName;
  detailDate.textContent = formatDate(item.started_at);
  detailTime.textContent = formatTime(item.started_at);
  detailStartedAt.textContent = formatTime(item.started_at);
  detailCompletedAt.textContent = formatTime(item.completed_at);
  detailSets.textContent = `${safeNumber(item.completed_sets)}세트`;
  detailRepetitions.textContent = `${safeNumber(item.repetition_count)}회`;
  detailMinutes.textContent = `${safeNumber(item.workout_minutes)}분`;
  detailCalories.textContent = `${safeNumber(item.calories)}kcal`;

  if (item.posture_score === null || item.posture_score === undefined) {
    detailScore.textContent = "자세 점수 측정 없음";
    detailScore.classList.add("unmeasured");
  } else {
    detailScore.textContent = `${Math.round(safeNumber(item.posture_score))}점`;
    detailScore.classList.remove("unmeasured");
  }

  detailFeedbackTitle.textContent = item.feedback_title || "저장된 피드백이 없습니다.";
  detailFeedback.textContent = item.feedback || "자세 피드백 내용이 저장되지 않았습니다.";
  setDetailImage(item.image_url, exerciseName);
  setDetailState("ready");
}

async function requestRecordDetail(recordId) {
  const userId = getLoginUserId();
  if (!userId) {
    window.location.href = "/login";
    return;
  }

  const requestId = ++detailRequestId;
  setDetailState("loading");

  try {
    const params = new URLSearchParams({ user_id: String(userId) });
    const response = await fetch(
      `/api/workouts/records/${recordId}?${params.toString()}`
    );
    const data = await readJson(response);
    if (!response.ok) {
      throw new Error(getErrorMessage(data, "상세 기록을 불러오지 못했습니다."));
    }
    if (requestId !== detailRequestId) {
      return;
    }
    renderRecordDetail(data);
  } catch (error) {
    if (requestId !== detailRequestId) {
      return;
    }
    console.error("운동 기록 상세 조회 실패:", error);
    setDetailState("error", error.message);
  }
}

function openRecordDetail(recordId, updateHistory = true) {
  const numericId = Number(recordId);
  if (!Number.isInteger(numericId) || numericId <= 0) {
    return;
  }

  activeDetailId = numericId;
  recordDetailOverlay.hidden = false;
  document.body.classList.add("detail-open");
  if (updateHistory) {
    window.history.pushState({ recordId: numericId }, "", `/records/${numericId}`);
  }
  requestRecordDetail(numericId);
}

function closeRecordDetail(updateHistory = true) {
  detailRequestId += 1;
  activeDetailId = null;
  recordDetailOverlay.hidden = true;
  document.body.classList.remove("detail-open");
  detailImage.removeAttribute("src");

  if (updateHistory && window.location.pathname !== "/records") {
    window.history.pushState({}, "", "/records");
  }
}

function getPathRecordId() {
  const match = window.location.pathname.match(/^\/records\/(\d+)\/?$/);
  return match ? Number(match[1]) : null;
}

recordFilters.forEach((button) => {
  button.addEventListener("click", () => {
    if (selectedPeriod === button.dataset.period) {
      return;
    }
    selectedPeriod = button.dataset.period;
    recordFilters.forEach((item) => item.classList.toggle("active", item === button));
    loadRecords();
  });
});

recordsRetryButton.addEventListener("click", loadRecords);
recordDetailClose.addEventListener("click", () => closeRecordDetail());
recordDetailBackdrop.addEventListener("click", () => closeRecordDetail());

window.addEventListener("popstate", () => {
  const recordId = getPathRecordId();
  if (recordId) {
    openRecordDetail(recordId, false);
  } else {
    closeRecordDetail(false);
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && activeDetailId !== null) {
    closeRecordDetail();
  }
});

document.addEventListener("DOMContentLoaded", () => {
  loadRecords();
  const recordId = getPathRecordId();
  if (recordId) {
    openRecordDetail(recordId, false);
  }
});
