const routineDate = document.querySelector("#routineDate");
const routineProgress = document.querySelector("#routineProgress");
const exerciseCount = document.querySelector("#exerciseCount");
const totalMinutes = document.querySelector("#totalMinutes");
const routineMessage = document.querySelector("#routineMessage");
const routineList = document.querySelector("#routineList");
const routineAddButton = document.querySelector("#routineAddButton");
const routineCalendarPrev = document.querySelector("#routineCalendarPrev");
const routineCalendarNext = document.querySelector("#routineCalendarNext");
const routineCalendarDays = document.querySelector("#routineCalendarDays");
const routineSheetOverlay = document.querySelector("#routineSheetOverlay");
const routineSheetCloseButton = document.querySelector(
  "#routineSheetCloseButton"
);
const routineCancelButton = document.querySelector("#routineCancelButton");
const routineForm = document.querySelector("#routineForm");
const routineFormError = document.querySelector("#routineFormError");
const routineSaveButton = document.querySelector("#routineSaveButton");
const routineExerciseSelect = document.querySelector(
  "#routineExerciseSelect"
);
const exerciseLoadMessage = document.querySelector(
  "#exerciseLoadMessage"
);
const exerciseRetryButton = document.querySelector(
  "#exerciseRetryButton"
);
const exerciseSearchInput = document.querySelector("#exerciseSearchInput");
const exerciseCategoryFilters = document.querySelector(
  "#exerciseCategoryFilters"
);
const exerciseAiFilter = document.querySelector("#exerciseAiFilter");
const exerciseOptionList = document.querySelector("#exerciseOptionList");
const exerciseEmptyState = document.querySelector("#exerciseEmptyState");
const exerciseDirectInput = document.querySelector("#exerciseDirectInput");
const routineSheetTitle = document.querySelector(
  "#routineSheetTitle"
);
const routineExerciseSelectField = document.querySelector(
  "#routineExerciseSelectField"
);
const routineExerciseNameField = document.querySelector(
  "#routineExerciseNameField"
);
const routineExerciseName = document.querySelector(
  "#routineExerciseName"
);
const routinePlanDate = document.querySelector(
  "#routinePlanDate"
);
const exerciseLoadState = document.querySelector(
  "#exerciseLoadState"
);
const customExerciseNameField = document.querySelector(
  "#customExerciseNameField"
);
const customExerciseName = document.querySelector(
  "#customExerciseName"
);
const routineSetRows = document.querySelector("#routineSetRows");
const routineAddSetButton = document.querySelector(
  "#routineAddSetButton"
);
const recommendationButton = document.querySelector("#recommendationButton");
const recommendationStatus = document.querySelector("#recommendationStatus");
const recommendationResult = document.querySelector("#recommendationResult");
const recommendationResultClose = document.querySelector("#recommendationResultClose");
const recommendationSummary = document.querySelector("#recommendationSummary");
const recommendationDays = document.querySelector("#recommendationDays");
const recommendationResultError = document.querySelector("#recommendationResultError");
const recommendationRegenerate = document.querySelector("#recommendationRegenerate");
const recommendationApply = document.querySelector("#recommendationApply");
const completionSheetOverlay = document.querySelector("#completionSheetOverlay");
const completionSheetClose = document.querySelector("#completionSheetClose");
const completionCancel = document.querySelector("#completionCancel");
const completionForm = document.querySelector("#completionForm");
const completionFormError = document.querySelector("#completionFormError");
const completionSave = document.querySelector("#completionSave");
const completionExerciseName = document.querySelector("#completionExerciseName");

let activePlanDate = null;
let calendarStartDate = null;
let calendarPlanCounts = new Map();
let calendarRequestController = null;
let calendarRequestVersion = 0;
let planRequestController = null;
let planRequestVersion = 0;
let isSavingPlan = false;
let completingPlanId = null;
let deletingPlanId = null;
let exerciseListState = "idle";
let formMode = "create";
let editingPlan = null;
let currentRecommendation = null;
let recommendationVariant = 0;
let recommendationRequestInFlight = false;
let recommendationApplyInFlight = false;
let recommendationRequestController = null;
let recommendationRequestVersion = 0;
let completingItem = null;
let completionIntensityChanged = false;
let availableExercises = [];
let selectedExerciseValue = "";
let selectedExerciseCategory = "all";
let aiCoachingOnly = false;

function getLoginUserId() {
  const savedUser = sessionStorage.getItem("gymfitUser");

  if (!savedUser) {
    return null;
  }

  try {
    const user = JSON.parse(savedUser);
    return user.user_id ?? user.userId ?? user.id ?? null;
  } catch {
    return null;
  }
}

function invalidateDashboard() {
  sessionStorage.setItem(
    "gymfitDashboardInvalidatedAt",
    String(Date.now())
  );
}

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value ?? "";
  return element.innerHTML;
}

const adjustmentLabels = {
  BASE: "기본 추천", MAINTAIN: "강도 유지", PROGRESS: "강도 증가",
  POSTURE_CORRECTION: "자세 교정", PERFORMANCE_DOWN: "수행량 조정",
  REPEATED_FEEDBACK: "반복 피드백",
};

function setRecommendationUi(message = "") {
  const busy = recommendationRequestInFlight || recommendationApplyInFlight;
  recommendationButton.disabled = busy;
  recommendationRegenerate.disabled = busy;
  recommendationApply.disabled = busy || !currentRecommendation;
  recommendationApply.setAttribute(
    "aria-busy", String(recommendationApplyInFlight)
  );
  recommendationStatus.hidden = !message;
  recommendationStatus.textContent = message;
}

function resetRecommendationState({ hideResult = true } = {}) {
  recommendationRequestController?.abort();
  recommendationRequestController = null;
  recommendationRequestVersion += 1;
  recommendationRequestInFlight = false;
  recommendationApplyInFlight = false;
  recommendationVariant = 0;
  currentRecommendation = null;
  recommendationResultError.hidden = true;
  recommendationResultError.textContent = "";
  if (hideResult) recommendationResult.hidden = true;
  setRecommendationUi();
}

function buildRecommendationPayload(userId, variant) {
  return {
    user_id: Number(userId),
    workout_minutes: 40,
    variant,
  };
}

function renderRecommendation(data) {
  currentRecommendation = data;
  recommendationResult.hidden = false;
  recommendationResultError.hidden = true;
  recommendationSummary.innerHTML = `
    <p><strong>${data.days_per_week}일</strong> · 회당 ${data.workout_minutes}분 · ${escapeHtml(data.level)}</p>
    <span>하루 ${Number(data.daily_exercise_count) || 0}개 · ${escapeHtml(data.recommendation_reason || "기록과 자세 결과 반영")}</span>`;
  const grouped = data.items.reduce((result, item) => {
    (result[item.workout_date] ||= []).push(item);
    return result;
  }, {});
  recommendationDays.innerHTML = Object.entries(grouped).map(([workoutDate, items]) => `
    <section class="recommendation-day">
      <h3>${escapeHtml(formatPlanDate(workoutDate))}</h3>
      ${items.map((item) => `
        <article class="recommendation-exercise">
          <div class="recommendation-exercise-heading">
            <strong>${escapeHtml(item.exercise_name)}</strong>
            <span class="adjustment-badge adjustment-${item.adjustment_type.toLowerCase()}">
              ${escapeHtml(adjustmentLabels[item.adjustment_type] || item.adjustment_type)}
            </span>
          </div>
          <div class="recommendation-meta">
            <span>${item.recommended_sets}세트 × ${item.recommended_reps}회</span>
            <span>난이도 ${escapeHtml(item.difficulty)}</span>
            <span>${item.coaching_supported ? "AI 코칭 지원" : "직접 기록"}</span>
          </div>
          <p>${escapeHtml(item.recommendation_reason)}</p>
        </article>`).join("")}
    </section>`).join("");
  recommendationApply.textContent = data.status === "APPLIED" ? "적용 완료" : "내 루틴에 적용";
  setRecommendationUi();
  recommendationResult.scrollIntoView({ behavior: "smooth", block: "start" });
}

async function requestRecommendation(regenerate = false) {
  const userId = getLoginUserId();
  if (!userId || recommendationRequestInFlight || recommendationApplyInFlight) {
    return;
  }
  if (regenerate) {
    recommendationVariant += 1;
  } else {
    recommendationVariant = 0;
    currentRecommendation = null;
  }
  recommendationRequestController?.abort();
  recommendationRequestController = new AbortController();
  const requestVersion = ++recommendationRequestVersion;
  recommendationRequestInFlight = true;
  setRecommendationUi("맞춤 루틴을 구성하고 있습니다.");
  try {
    const response = await fetch(
      regenerate ? "/api/routine/recommendations/regenerate" : "/api/routine/recommendations",
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(
          buildRecommendationPayload(userId, recommendationVariant)
        ),
        cache: "no-store",
        signal: recommendationRequestController.signal,
      }
    );
    const data = await readJsonResponse(response);
    if (!response.ok) throw new Error(getErrorMessage(data, "추천을 생성하지 못했습니다."));
    if (requestVersion !== recommendationRequestVersion) return;
    recommendationRequestInFlight = false;
    recommendationStatus.hidden = true;
    renderRecommendation(data);
  } catch (error) {
    if (requestVersion !== recommendationRequestVersion) return;
    recommendationRequestInFlight = false;
    if (error.name === "AbortError") return;
    if (regenerate) recommendationVariant = Math.max(0, recommendationVariant - 1);
    setRecommendationUi(error.message || "추천을 생성하지 못했습니다.");
  } finally {
    if (requestVersion === recommendationRequestVersion) {
      recommendationRequestController = null;
    }
  }
}

async function applyRecommendation() {
  if (
    !currentRecommendation
    || recommendationRequestInFlight
    || recommendationApplyInFlight
  ) return;
  recommendationApplyInFlight = true;
  setRecommendationUi("추천 루틴을 적용하고 있습니다.");
  recommendationResultError.hidden = true;
  try {
    const response = await fetch(
      `/api/routine/recommendations/${currentRecommendation.recommendation_id}/apply`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ replace_existing_recommendations: true }),
        cache: "no-store",
      }
    );
    const data = await readJsonResponse(response);
    if (!response.ok) throw new Error(getErrorMessage(data, "추천을 적용하지 못했습니다."));
    if (!Number(data.created_count)) {
      throw new Error(
        "적용할 수 있는 새 운동이 없습니다. 기존 루틴과 날짜가 겹치는지 확인해주세요."
      );
    }
    invalidateDashboard();
    const targetDate = (data.affected_dates || []).includes(getLocalDateValue())
      ? getLocalDateValue()
      : data.affected_dates?.[0] || activePlanDate;
    currentRecommendation = null;
    recommendationVariant = 0;
    recommendationResult.hidden = true;
    recommendationApplyInFlight = false;
    activePlanDate = targetDate;
    calendarStartDate = startOfCalendarRange(targetDate);
    calendarPlanCounts = new Map();
    setPlanDateToUrl(targetDate);
    renderRoutineCalendar();
    let refreshFailed = false;
    try {
      await Promise.all([
        loadPlan(getLoginUserId(), targetDate),
        loadCalendarPlanCounts(),
      ]);
    } catch (refreshError) {
      refreshFailed = true;
      console.error("추천 적용 후 루틴 목록 갱신 실패:", refreshError);
    }
    setRecommendationUi(
      refreshFailed
        ? "추천은 적용됐지만 목록을 새로고침하지 못했습니다. 페이지를 새로고침해주세요."
        : `${data.created_count}개 계획을 적용했습니다.${data.skipped_count ? ` 기존 계획 ${data.skipped_count}개는 유지했습니다.` : ""}`
    );
  } catch (error) {
    recommendationApplyInFlight = false;
    setRecommendationUi();
    recommendationResultError.hidden = false;
    recommendationResultError.textContent = error.message || "추천을 적용하지 못했습니다.";
  }
}

function formatPlanDate(value) {
  const date = new Date(`${value}T00:00:00`);

  return new Intl.DateTimeFormat(
    "ko-KR",
    {
      month: "long",
      day: "numeric",
      weekday: "short",
    }
  ).format(date);
}

function getKstDateString(date = new Date()) {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(date);
}

function getLocalDateValue() {
  return getKstDateString();
}

function parseDateValue(value) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(String(value || ""))) return null;
  const [year, month, day] = value.split("-").map(Number);
  const parsed = new Date(year, month - 1, day);
  return (
    parsed.getFullYear() === year
    && parsed.getMonth() === month - 1
    && parsed.getDate() === day
  ) ? parsed : null;
}

function addDays(value, days) {
  const source = typeof value === "string" ? parseDateValue(value) : value;
  const result = new Date(source.getFullYear(), source.getMonth(), source.getDate());
  result.setDate(result.getDate() + days);
  return result;
}

function formatDateValue(date) {
  return [
    date.getFullYear(),
    String(date.getMonth() + 1).padStart(2, "0"),
    String(date.getDate()).padStart(2, "0"),
  ].join("-");
}

function startOfCalendarRange(planDate) {
  const today = getKstDateString();
  const todayEnd = formatDateValue(addDays(today, 6));
  return planDate >= today && planDate <= todayEnd ? today : planDate;
}

function getPlanDateFromUrl() {
  const value = new URL(window.location.href).searchParams.get("plan_date");
  return parseDateValue(value) ? value : null;
}

function setPlanDateToUrl(planDate) {
  const url = new URL(window.location.href);
  url.searchParams.set("plan_date", planDate);
  window.history.replaceState(
    { ...(window.history.state || {}), planDate },
    "",
    `${url.pathname}${url.search}`
  );
}

function getErrorMessage(data, fallbackMessage) {
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg)
      .filter(Boolean)
      .join(", ")
      || fallbackMessage;
  }

  return fallbackMessage;
}

async function readJsonResponse(response) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}

function renderRoutineCalendar() {
  const today = getKstDateString();
  const weekdayFormatter = new Intl.DateTimeFormat("ko-KR", {
    weekday: "short",
  });
  routineCalendarDays.replaceChildren();
  for (let offset = 0; offset < 7; offset += 1) {
    const date = addDays(calendarStartDate, offset);
    const planDate = formatDateValue(date);
    const counts = calendarPlanCounts.get(planDate) || {
      total_count: 0,
      completed_count: 0,
    };
    const active = planDate === activePlanDate;
    const isToday = planDate === today;
    const hasPlan = counts.total_count > 0;
    const completed = hasPlan
      && counts.completed_count === counts.total_count;
    const button = document.createElement("button");
    button.type = "button";
    button.className = [
      "routine-calendar-day",
      active ? "active" : "",
      isToday ? "today" : "",
      hasPlan ? "has-plan" : "",
      completed ? "completed" : "",
    ].filter(Boolean).join(" ");
    button.dataset.planDate = planDate;
    button.role = "tab";
    button.setAttribute("aria-selected", String(active));
    button.setAttribute(
      "aria-label",
      `${isToday ? "오늘, " : ""}${formatPlanDate(planDate)}, `
      + (hasPlan
        ? `${counts.completed_count}/${counts.total_count}개 완료`
        : "운동 계획 없음")
    );
    button.innerHTML = `
      <span class="routine-calendar-weekday">${
        isToday ? "오늘" : weekdayFormatter.format(date)
      }</span>
      <strong class="routine-calendar-number">${date.getDate()}</strong>
      ${hasPlan ? `<span class="routine-calendar-indicator">${
        completed ? "✓" : `${counts.completed_count}/${counts.total_count}`
      }</span>` : '<span class="routine-calendar-indicator" aria-hidden="true"></span>'}
    `;
    button.addEventListener("click", () => selectRoutineDate(planDate));
    routineCalendarDays.appendChild(button);
  }
}

async function loadCalendarPlanCounts() {
  const userId = getLoginUserId();
  if (!userId || !calendarStartDate) return;
  calendarRequestController?.abort();
  calendarRequestController = new AbortController();
  const requestVersion = ++calendarRequestVersion;
  const startDate = calendarStartDate;
  const endDate = formatDateValue(addDays(startDate, 6));
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });
  try {
    const response = await fetch(
      `/api/workouts/plans/calendar/${userId}?${params.toString()}`,
      {
        cache: "no-store",
        signal: calendarRequestController.signal,
      }
    );
    const data = await readJsonResponse(response);
    if (!response.ok) {
      throw new Error(getErrorMessage(data, "날짜별 계획을 불러오지 못했습니다."));
    }
    if (requestVersion !== calendarRequestVersion) return;
    calendarPlanCounts = new Map(
      (data.days || []).map((item) => [item.plan_date, item])
    );
    renderRoutineCalendar();
  } catch (error) {
    if (error.name !== "AbortError") {
      console.error("날짜별 계획 개수 조회 실패:", error);
    }
  } finally {
    if (requestVersion === calendarRequestVersion) {
      calendarRequestController = null;
    }
  }
}

async function selectRoutineDate(planDate, { updateUrl = true } = {}) {
  const userId = getLoginUserId();
  if (!userId) {
    window.location.href = "/login";
    return;
  }
  if (!parseDateValue(planDate)) return;
  activePlanDate = planDate;
  const rangeEnd = formatDateValue(addDays(calendarStartDate, 6));
  if (planDate < calendarStartDate || planDate > rangeEnd) {
    calendarStartDate = startOfCalendarRange(planDate);
    calendarPlanCounts = new Map();
    loadCalendarPlanCounts();
  }
  if (updateUrl) setPlanDateToUrl(planDate);
  renderRoutineCalendar();
  try {
    await loadPlan(userId, planDate);
  } catch (error) {
    if (error.name === "AbortError") return;
    console.error("날짜별 루틴 조회 실패:", error);
    routineList.replaceChildren();
    routineMessage.hidden = false;
    routineMessage.textContent = error.message || "운동 계획을 불러오지 못했습니다.";
  }
}

async function moveCalendarRange(days) {
  calendarStartDate = formatDateValue(addDays(calendarStartDate, days));
  calendarPlanCounts = new Map();
  await Promise.all([
    loadCalendarPlanCounts(),
    selectRoutineDate(calendarStartDate),
  ]);
}

async function requestPlan(userId, planDate = null, signal = undefined) {
  const params = new URLSearchParams();

  if (planDate) {
    params.set("plan_date", planDate);
  }

  const query = params.toString();

  const response = await fetch(
    `/api/workouts/plans/today/${userId}${
      query ? `?${query}` : ""
    }`,
    { cache: "no-store", signal }
  );

  const data = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "운동 계획을 불러오지 못했습니다."
      )
    );
  }

  return data;
}

async function loadPlan(userId, planDate = null) {
  planRequestController?.abort();
  planRequestController = new AbortController();
  const requestVersion = ++planRequestVersion;
  const data = await requestPlan(
    userId, planDate, planRequestController.signal
  );
  if (requestVersion !== planRequestVersion) return null;
  activePlanDate = data.plan_date;
  renderPlan(data);
  renderRoutineCalendar();
  return data;
}

async function requestActiveExercises(userId) {
  const params = new URLSearchParams({
    user_id: String(userId),
  });
  const response = await fetch(
    `/api/workouts/exercises?${params.toString()}`
  );

  const data = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "운동 목록을 불러오지 못했습니다."
      )
    );
  }

  return data.items || [];
}

function updateSaveButtonState() {
  routineSaveButton.disabled =
    isSavingPlan
    || (
      formMode === "create"
      && (
        exerciseListState !== "ready"
        || !selectedExerciseValue
      )
    );
}

function setExerciseLoadState(state, message) {
  exerciseListState = state;
  exerciseLoadMessage.textContent = message;
  exerciseLoadMessage.classList.toggle(
    "error",
    state === "error"
  );
  exerciseSearchInput.disabled = state !== "ready";
  exerciseAiFilter.disabled = state !== "ready";
  exerciseDirectInput.disabled = state !== "ready";
  exerciseRetryButton.hidden =
    state !== "error";

  updateSaveButtonState();
}

function renderExerciseOptions(exercises) {
  routineExerciseSelect.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  routineExerciseSelect.appendChild(placeholder);

  exercises.forEach((exercise) => {
    const option = document.createElement("option");

    option.value = exercise.exercise_type === "custom"
      ? `custom:${exercise.user_exercise_id}`
      : `default:${exercise.exercise_id}`;
    option.textContent = exercise.exercise_type === "custom"
      ? `${exercise.exercise_name} (내 운동)`
      : exercise.exercise_name;

    routineExerciseSelect.appendChild(option);
  });

  const customOption = document.createElement("option");
  customOption.value = "custom:new";
  customOption.textContent = "직접 입력";
  routineExerciseSelect.appendChild(customOption);
  routineExerciseSelect.value = selectedExerciseValue;
  syncCustomExerciseField();
}

function exerciseValue(exercise) {
  return exercise.exercise_type === "custom"
    ? `custom:${exercise.user_exercise_id}`
    : `default:${exercise.exercise_id}`;
}

function exerciseCategory(exercise) {
  return String(exercise.category || "").trim() || "__uncategorized__";
}

function categoryDisplayName(category) {
  return category === "__uncategorized__" ? "기타" : category;
}

function normalizedExerciseSearch(value) {
  return String(value || "").trim().toLocaleLowerCase("ko-KR");
}

function filterExercises() {
  const search = normalizedExerciseSearch(exerciseSearchInput.value);
  return availableExercises.filter((exercise) => {
    const name = normalizedExerciseSearch(exercise.exercise_name);
    const code = normalizedExerciseSearch(exercise.exercise_code);
    const categoryMatches = selectedExerciseCategory === "all"
      || exerciseCategory(exercise) === selectedExerciseCategory;
    const aiMatches = !aiCoachingOnly
      || exercise.ai_coaching_supported === true;
    return (!search || name.includes(search) || code.includes(search))
      && categoryMatches
      && aiMatches;
  });
}

function selectExercise(value) {
  selectedExerciseValue = value;
  routineExerciseSelect.value = value;
  exerciseDirectInput.classList.toggle("selected", value === "custom:new");
  exerciseDirectInput.setAttribute(
    "aria-pressed", String(value === "custom:new")
  );
  syncCustomExerciseField();
  renderExerciseOptionsList();
  updateSaveButtonState();
}

function renderExerciseOptionsList() {
  const exercises = filterExercises();
  exerciseOptionList.replaceChildren();
  exercises.forEach((exercise) => {
    const value = exerciseValue(exercise);
    const button = document.createElement("button");
    const selected = value === selectedExerciseValue;
    button.type = "button";
    button.className = `exercise-option-card${selected ? " selected" : ""}`;
    button.dataset.exerciseValue = value;
    button.setAttribute("role", "radio");
    button.setAttribute("aria-checked", String(selected));
    button.innerHTML = `
      <span class="exercise-option-copy">
        <strong>${escapeHtml(exercise.exercise_name)}</strong>
        <small>${escapeHtml(categoryDisplayName(exerciseCategory(exercise)))}</small>
      </span>
      ${exercise.exercise_type === "custom"
        ? '<span class="exercise-kind-badge custom">내 운동</span>'
        : exercise.ai_coaching_supported
          ? '<span class="exercise-kind-badge ai">AI 코칭</span>'
          : '<span class="exercise-kind-badge general">일반 기록</span>'}
    `;
    button.addEventListener("click", () => selectExercise(value));
    exerciseOptionList.appendChild(button);
  });
  const noCatalogExercises = availableExercises.length === 0;
  exerciseEmptyState.querySelector("strong").textContent = noCatalogExercises
    ? "선택 가능한 운동이 없습니다."
    : "검색 결과가 없습니다.";
  exerciseEmptyState.querySelector("p").textContent = noCatalogExercises
    ? "직접 입력 운동을 추가하거나 다시 시도해주세요."
    : "다른 운동 이름이나 부위를 선택해보세요.";
  exerciseEmptyState.hidden = exercises.length > 0;
}

function renderExerciseFilters() {
  const categories = [...new Set(
    availableExercises.map(exerciseCategory)
  )].sort((left, right) => categoryDisplayName(left).localeCompare(
    categoryDisplayName(right), "ko"
  ));
  const filters = ["all", ...categories];
  exerciseCategoryFilters.replaceChildren();
  filters.forEach((category) => {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = category === "all"
      ? "전체"
      : categoryDisplayName(category);
    button.className = category === selectedExerciseCategory ? "active" : "";
    button.setAttribute(
      "aria-pressed",
      String(category === selectedExerciseCategory)
    );
    button.addEventListener("click", () => {
      selectedExerciseCategory = category;
      renderExerciseFilters();
      renderExerciseOptionsList();
    });
    exerciseCategoryFilters.appendChild(button);
  });
}

function renderExercisePicker() {
  renderExerciseOptions(availableExercises);
  renderExerciseFilters();
  renderExerciseOptionsList();
}

function syncCustomExerciseField() {
  const isDirectInput = routineExerciseSelect.value === "custom:new";
  customExerciseNameField.hidden = !isDirectInput;
  customExerciseName.required = isDirectInput;
  if (!isDirectInput) {
    customExerciseName.value = "";
  }
}

async function loadActiveExercises() {
  const userId = getLoginUserId();

  if (!userId) {
    window.location.href = "/login";
    return;
  }
  setExerciseLoadState(
    "loading",
    "운동 목록을 불러오는 중입니다."
  );

  exerciseOptionList.replaceChildren();
  exerciseEmptyState.hidden = true;

  try {
    availableExercises = await requestActiveExercises(userId);
    renderExercisePicker();

    setExerciseLoadState(
      "ready",
      availableExercises.length
        ? `${availableExercises.length}개의 운동을 선택할 수 있습니다.`
        : "등록된 운동이 없습니다. 직접 입력해 주세요."
    );
  } catch (error) {
    console.error("운동 목록 조회 실패:", error);

    availableExercises = [];
    renderExercisePicker();

    setExerciseLoadState(
      "error",
      "운동 목록을 불러오지 못했습니다. 다시 시도해주세요."
    );
  }
}

function showFormError(message) {
  routineFormError.textContent = message;
  routineFormError.hidden = false;
}

function clearFormError() {
  routineFormError.textContent = "";
  routineFormError.hidden = true;
}

function normalizeOptionalNumber(value) {
  const text = String(value ?? "").trim();
  return text === "" ? null : Number(text);
}

function createSetRow(setData = {}, copyPrevious = false) {
  const previousRow = routineSetRows.lastElementChild;
  const previousValues = previousRow
    ? {
        weight_kg: previousRow.querySelector(
          '[data-set-field="weight_kg"]'
        ).value,
        repetition_count: previousRow.querySelector(
          '[data-set-field="repetition_count"]'
        ).value,
        duration_seconds: previousRow.querySelector(
          '[data-set-field="duration_seconds"]'
        ).value,
      }
    : {};
  const values = copyPrevious ? previousValues : setData;
  const row = document.createElement("div");
  row.className = "routine-set-row";
  row.innerHTML = `
    <strong class="routine-set-order"></strong>
    <label>
      <span>무게 kg</span>
      <input
        type="number"
        min="0"
        max="99999.99"
        step="0.01"
        inputmode="decimal"
        data-set-field="weight_kg"
        value="${escapeHtml(values.weight_kg ?? "")}"
      >
    </label>
    <label>
      <span>반복 회</span>
      <input
        type="number"
        min="1"
        max="10000"
        inputmode="numeric"
        data-set-field="repetition_count"
        value="${escapeHtml(values.repetition_count ?? "")}"
      >
    </label>
    <label>
      <span>시간 초</span>
      <input
        type="number"
        min="1"
        max="86400"
        inputmode="numeric"
        data-set-field="duration_seconds"
        value="${escapeHtml(values.duration_seconds ?? "")}"
      >
    </label>
    <button type="button" class="routine-set-delete">삭제</button>
  `;
  row.querySelector(".routine-set-delete").addEventListener(
    "click",
    () => {
      if (routineSetRows.children.length <= 1) {
        showFormError("최소 1세트가 필요합니다.");
        return;
      }
      row.remove();
      updateSetOrders();
    }
  );
  routineSetRows.appendChild(row);
  updateSetOrders();
}

function updateSetOrders() {
  Array.from(routineSetRows.children).forEach((row, index) => {
    row.querySelector(".routine-set-order").textContent =
      `${index + 1}세트`;
  });
}

function renderSetRows(sets) {
  routineSetRows.innerHTML = "";
  const sourceSets = sets?.length
    ? sets
    : [{ repetition_count: 10 }];
  sourceSets.forEach((setData) => createSetRow(setData));
}

function collectSetPayload() {
  const rows = Array.from(routineSetRows.children);
  if (!rows.length) {
    throw new Error("최소 1세트가 필요합니다.");
  }

  return rows.map((row, index) => {
    const weightKg = normalizeOptionalNumber(
      row.querySelector('[data-set-field="weight_kg"]').value
    );
    const repetitionCount = normalizeOptionalNumber(
      row.querySelector('[data-set-field="repetition_count"]').value
    );
    const durationSeconds = normalizeOptionalNumber(
      row.querySelector('[data-set-field="duration_seconds"]').value
    );

    if (repetitionCount === null && durationSeconds === null) {
      throw new Error(
        `${index + 1}세트에 반복 횟수 또는 유지 시간을 입력해 주세요.`
      );
    }
    if (
      (weightKg !== null && !Number.isFinite(weightKg))
      || (
        repetitionCount !== null
        && !Number.isInteger(repetitionCount)
      )
      || (
        durationSeconds !== null
        && !Number.isInteger(durationSeconds)
      )
      || (weightKg !== null && weightKg < 0)
      || (repetitionCount !== null && repetitionCount <= 0)
      || (durationSeconds !== null && durationSeconds <= 0)
    ) {
      throw new Error(`${index + 1}세트 입력값을 확인해 주세요.`);
    }

    return {
      weight_kg: weightKg,
      repetition_count: repetitionCount,
      duration_seconds: durationSeconds,
    };
  });
}

function resetRoutineForm() {
  formMode = "create";
  editingPlan = null;

  routineForm.reset();
  routineSheetTitle.textContent = "루틴 추가";
  routineSaveButton.textContent = "저장";
  routineExerciseSelectField.hidden = false;
  exerciseLoadState.hidden = false;
  routineExerciseNameField.hidden = true;
  routineExerciseName.value = "";
  customExerciseNameField.hidden = true;
  customExerciseName.required = false;
  customExerciseName.value = "";
  selectedExerciseValue = "";
  selectedExerciseCategory = "all";
  aiCoachingOnly = false;
  exerciseSearchInput.value = "";
  exerciseAiFilter.setAttribute("aria-pressed", "false");
  exerciseAiFilter.classList.remove("active");
  exerciseDirectInput.classList.remove("selected");
  exerciseDirectInput.setAttribute("aria-pressed", "false");
  routineExerciseSelect.disabled = false;
  if (exerciseListState === "ready") {
    renderExercisePicker();
  }
  routinePlanDate.disabled = false;
  renderSetRows([{ repetition_count: 10 }]);

  clearFormError();
  updateSaveButtonState();
}

function showRoutineSheet() {
  routineSheetOverlay.hidden = false;
  document.body.classList.add("routine-sheet-open");
}

function openCreateRoutineSheet() {
  resetRoutineForm();
  clearFormError();
  routineForm.elements.plan_date.value =
    activePlanDate || getLocalDateValue();
  showRoutineSheet();

  if (
    exerciseListState === "idle"
    || exerciseListState === "error"
  ) {
    loadActiveExercises();
  }
}

function openEditRoutineSheet(item) {
  formMode = "edit";
  editingPlan = item;

  routineSheetTitle.textContent = "루틴 수정";
  routineSaveButton.textContent = "수정 완료";
  routineExerciseSelectField.hidden = true;
  exerciseLoadState.hidden = true;
  routineExerciseNameField.hidden = false;
  routineExerciseName.value = item.exercise_name;
  routineExerciseSelect.disabled = true;
  routinePlanDate.value = activePlanDate;
  routinePlanDate.disabled = true;
  routineForm.elements.estimated_minutes.value =
    item.estimated_minutes;
  renderSetRows(
    item.sets?.length
      ? item.sets
      : Array.from(
          { length: item.set_count },
          () => ({ repetition_count: item.repetition_count })
        )
  );

  clearFormError();
  updateSaveButtonState();
  showRoutineSheet();
}

function closeRoutineSheet() {
  if (isSavingPlan) {
    return;
  }

  routineSheetOverlay.hidden = true;
  document.body.classList.remove("routine-sheet-open");
  resetRoutineForm();
}

async function createOrUpdatePlan(userId, payload) {
  const response = await fetch(
    "/api/workouts/plans",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        ...payload,
      }),
    }
  );

  const data = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "운동 계획을 저장하지 못했습니다."
      )
    );
  }

  return data;
}

async function createCustomExercise(userId, exerciseName) {
  const response = await fetch(
    "/api/workouts/exercises/custom",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        exercise_name: exerciseName,
      }),
    }
  );
  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw new Error(
      getErrorMessage(data, "사용자 운동을 등록하지 못했습니다.")
    );
  }
  return data.item;
}

async function updatePlan(
  userId,
  workoutPlanId,
  payload
) {
  const response = await fetch(
    `/api/workouts/plans/${workoutPlanId}`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        ...payload,
      }),
    }
  );

  const data = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "운동 계획을 수정하지 못했습니다."
      )
    );
  }

  return data;
}

async function completePlan(userId, workoutPlanId, completion = {}) {
  const response = await fetch(
    `/api/workouts/plans/${workoutPlanId}/complete`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
        ...completion,
      }),
    }
  );

  const data = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "운동 계획을 완료 처리하지 못했습니다."
      )
    );
  }

  return data;
}

async function uncompletePlan(workoutPlanId) {
  const response = await fetch(
    `/api/workouts/plans/${workoutPlanId}/uncomplete`,
    { method: "PATCH" }
  );
  const data = await readJsonResponse(response);
  if (!response.ok) {
    throw new Error(
      getErrorMessage(data, "운동 완료를 취소하지 못했습니다.")
    );
  }
  return data;
}

function plannedCompletionValues(item) {
  const sets = item.sets || [];
  return {
    completedSets: Number(sets.length || item.set_count || 0),
    repetitions: sets.length
      ? sets.reduce(
          (sum, setItem) => sum + Number(setItem.repetition_count || 0),
          0
        )
      : Number(item.repetition_count || 0) * Number(item.set_count || 0),
  };
}

function showCompletionError(message) {
  completionFormError.textContent = message;
  completionFormError.hidden = false;
}

function clearCompletionError() {
  completionFormError.textContent = "";
  completionFormError.hidden = true;
}

function openCompletionSheet(item) {
  const initial = plannedCompletionValues(item);
  completingItem = item;
  completionIntensityChanged = false;
  completionForm.reset();
  completionExerciseName.textContent = item.exercise_name;
  completionForm.elements.completed_sets.value = String(initial.completedSets);
  completionForm.elements.repetition_count.value = String(initial.repetitions);
  completionForm.elements.exercise_intensity.value = "MODERATE";
  clearCompletionError();
  completionSheetOverlay.hidden = false;
  document.body.classList.add("routine-sheet-open");
  completionForm.elements.workout_minutes.focus();
}

function closeCompletionSheet() {
  if (completingPlanId !== null) {
    return;
  }
  completionSheetOverlay.hidden = true;
  document.body.classList.remove("routine-sheet-open");
  completionForm.reset();
  completingItem = null;
  completionIntensityChanged = false;
  clearCompletionError();
}

async function submitCompletion(event) {
  event.preventDefault();
  if (!completingItem || completingPlanId !== null) {
    return;
  }

  const minutesText = completionForm.elements.workout_minutes.value.trim();
  const workoutMinutes = Number(minutesText);
  if (
    minutesText === ""
    || !Number.isInteger(workoutMinutes)
    || workoutMinutes < 1
  ) {
    showCompletionError("운동시간을 1분 이상 입력해주세요.");
    completionForm.elements.workout_minutes.focus();
    return;
  }

  const completedSets = Number(completionForm.elements.completed_sets.value);
  const repetitionCount = Number(completionForm.elements.repetition_count.value);
  const weightText = completionForm.elements.weight_kg.value.trim();
  const weightKg = weightText === "" ? null : Number(weightText);
  if (
    !Number.isInteger(completedSets) || completedSets < 0
    || !Number.isInteger(repetitionCount) || repetitionCount < 0
    || (weightKg !== null && (!Number.isFinite(weightKg) || weightKg <= 0))
  ) {
    showCompletionError("완료 세트, 반복 횟수와 사용 중량을 확인해주세요.");
    return;
  }

  const userId = getLoginUserId();
  if (!userId) {
    window.location.href = "/login";
    return;
  }

  clearCompletionError();
  completingPlanId = completingItem.workout_plan_id;
  completionSave.disabled = true;
  completionSave.textContent = "저장 중";

  try {
    await completePlan(userId, completingItem.workout_plan_id, {
      workout_minutes: workoutMinutes,
      exercise_intensity: completionIntensityChanged
        ? completionForm.elements.exercise_intensity.value
        : null,
      weight_kg: weightKg,
      completed_sets: completedSets,
      repetition_count: repetitionCount,
    });
    invalidateDashboard();
    completionSheetOverlay.hidden = true;
    document.body.classList.remove("routine-sheet-open");
    completingItem = null;
    try {
      await Promise.all([
        loadPlan(userId, activePlanDate),
        loadCalendarPlanCounts(),
      ]);
    } catch (refreshError) {
      console.error("완료 후 루틴 목록 갱신 실패:", refreshError);
      alert("운동 기록은 저장됐지만 목록을 새로고침하지 못했습니다.");
    }
  } catch (error) {
    console.error("운동 완료 저장 실패:", error);
    showCompletionError(
      error.message || "운동 완료 기록을 저장하지 못했습니다."
    );
  } finally {
    completingPlanId = null;
    completionSave.disabled = false;
    completionSave.textContent = "운동 완료 저장";
  }
}

async function deletePlan(userId, workoutPlanId) {
  const params = new URLSearchParams({
    user_id: String(userId),
  });

  const response = await fetch(
    `/api/workouts/plans/${workoutPlanId}?${params.toString()}`,
    {
      method: "DELETE",
    }
  );

  const data = await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "운동 계획을 삭제하지 못했습니다."
      )
    );
  }

  return data;
}

function moveToCoaching(item) {
  saveCoachingPlan(item);
  const repetitions = Number(
    item.sets?.[0]?.repetition_count
    ?? item.repetition_count
    ?? 0
  );
  const sets = Number(item.sets?.length ?? item.set_count ?? 0);
  const params = new URLSearchParams({
    exercise_code: String(item.exercise_code || ""),
    reps: String(repetitions),
    sets: String(sets),
  });
  window.location.href = `/coaching?${params.toString()}`;
}

function getButtonState(item) {
  if (item.is_completed) {
    return {
      label: "완료 취소",
      disabled: false,
      action: "uncomplete",
    };
  }

  if (
    item.ai_coaching_supported
    && Number(
      item.sets?.[0]?.repetition_count
      ?? item.repetition_count
    ) > 0
  ) {
    return {
      label: "코칭 시작",
      disabled: false,
      action: "coaching",
    };
  }

  return {
    label: "완료 처리",
    disabled: false,
    action: "complete",
  };
}

function renderPlan(data) {
  routineDate.textContent = formatPlanDate(data.plan_date);
  routineProgress.textContent =
    `${data.completed_count} / ${data.total_count} 완료`;
  exerciseCount.textContent = data.total_count;
  totalMinutes.textContent = data.total_minutes;
  routineList.innerHTML = "";

  if (!data.items.length) {
    routineMessage.hidden = false;
    routineMessage.textContent =
      "오늘 등록된 운동 계획이 없습니다.";
    return;
  }

  routineMessage.hidden = true;

  data.items.forEach((item, index) => {
    const buttonState = getButtonState(item);
    const card = document.createElement("article");
    const isTrainerRoutine = String(item.plan_source || "").toUpperCase() === "TRAINER";
    const firstWeightedSet = (item.sets || []).find(
      (setItem) => setItem.weight_kg != null
    );
    const weightLabel = firstWeightedSet
      ? `${Number(firstWeightedSet.weight_kg)}kg`
      : "맨몸";

    card.className =
      `routine-card${item.is_completed ? " completed" : ""}${isTrainerRoutine ? " trainer-routine" : ""}`;

    const setDetails = (item.sets || []).map((setItem) => {
      const details = [];
      if (setItem.weight_kg !== null) {
        details.push(`${Number(setItem.weight_kg)}kg`);
      }
      if (setItem.repetition_count !== null) {
        details.push(`${setItem.repetition_count}회`);
      }
      if (setItem.duration_seconds !== null) {
        details.push(`${setItem.duration_seconds}초`);
      }
      return `
        <li>
          <strong>${setItem.set_order}세트</strong>
          <span>${details.join(" × ")}</span>
        </li>
      `;
    }).join("");

    card.innerHTML = `
      <div class="routine-card-index">
        ${item.is_completed ? "✓" : String(index + 1).padStart(2, "0")}
      </div>

      <div class="routine-card-content">
        <div class="routine-card-heading">
          <div class="routine-card-labels">
            <span>${item.is_completed ? "완료" : "오늘의 운동"}</span>
            ${isTrainerRoutine ? '<span class="routine-trainer-badge">트레이너 숙제</span>' : ""}
          </div>
          <h2>${escapeHtml(item.exercise_name)}</h2>
        </div>

        <div class="routine-meta">
          <span><small>세트</small><strong>${Number(item.set_count) || 0}</strong></span>
          <span><small>반복</small><strong>${Number(item.repetition_count) || 0}<b>회</b></strong></span>
          <span><small>중량</small><strong>${weightLabel}</strong></span>
        </div>

        <p class="routine-duration">예상 운동 시간 <strong>${Number(item.estimated_minutes) || 0}분</strong></p>

        <ol class="routine-set-summary">
          ${setDetails}
        </ol>

        <div class="routine-card-actions">
          <button
            type="button"
            class="routine-start-button${buttonState.action === "uncomplete" ? " routine-undo-button" : ""}"
            ${buttonState.disabled ? "disabled" : ""}
          >
            ${buttonState.label}
          </button>

          <button
            type="button"
            class="routine-edit-button"
            aria-label="${escapeHtml(item.exercise_name)} 계획 수정"
          >
            수정
          </button>

          <button
            type="button"
            class="routine-delete-button"
            aria-label="${escapeHtml(item.exercise_name)} 계획 삭제"
          >
            ×
          </button>
        </div>
      </div>
    `;

    const actionButton = card.querySelector(".routine-start-button");

    if (buttonState.action === "coaching") {
      actionButton.addEventListener(
        "click",
        () => moveToCoaching(item)
      );
    }

    if (buttonState.action === "complete") {
      actionButton.addEventListener("click", () => openCompletionSheet(item));
    }

    if (buttonState.action === "uncomplete") {
      actionButton.addEventListener("click", async () => {
        if (!window.confirm("운동 완료를 취소하시겠어요?\n일반 완료로 생성된 운동 기록은 함께 삭제됩니다.")) {
          return;
        }
        actionButton.disabled = true;
        actionButton.textContent = "취소 중";
        try {
          await uncompletePlan(item.workout_plan_id);
          invalidateDashboard();
          await Promise.all([
            loadPlan(getLoginUserId(), activePlanDate),
            loadCalendarPlanCounts(),
          ]);
        } catch (error) {
          console.error("운동 완료 취소 실패:", error);
          alert(error.message || "운동 완료를 취소하지 못했습니다.");
          actionButton.disabled = false;
          actionButton.textContent = "완료 취소";
        }
      });
    }

    const editButton = card.querySelector(".routine-edit-button");

    editButton.addEventListener(
      "click",
      () => openEditRoutineSheet(item)
    );

    const deleteButton = card.querySelector(".routine-delete-button");

    deleteButton.addEventListener("click", async () => {
      if (
        !window.confirm(
          `${item.exercise_name} 계획을 삭제할까요?`
        )
      ) {
        return;
      }

      if (deletingPlanId !== null) {
        return;
      }

      const userId = getLoginUserId();

      if (!userId) {
        window.location.href = "/login";
        return;
      }

      deletingPlanId = item.workout_plan_id;
      deleteButton.disabled = true;

      try {
        await deletePlan(userId, item.workout_plan_id);
        invalidateDashboard();
        await Promise.all([
          loadPlan(userId, activePlanDate),
          loadCalendarPlanCounts(),
        ]);
      } catch (error) {
        console.error("운동 계획 삭제 실패:", error);
        alert(
          error.message
          || "운동 계획을 삭제하지 못했습니다."
        );
        deleteButton.disabled = false;
      } finally {
        deletingPlanId = null;
      }
    });

    routineList.appendChild(card);
  });
}

routineAddButton.addEventListener("click", openCreateRoutineSheet);
routineCalendarPrev.addEventListener(
  "click", () => moveCalendarRange(-7)
);
routineCalendarNext.addEventListener(
  "click", () => moveCalendarRange(7)
);
routineSheetCloseButton.addEventListener("click", closeRoutineSheet);
routineCancelButton.addEventListener("click", closeRoutineSheet);
exerciseRetryButton.addEventListener("click", loadActiveExercises);
routineAddSetButton.addEventListener(
  "click",
  () => createSetRow({}, true)
);
exerciseSearchInput.addEventListener("input", () => {
  renderExerciseOptionsList();
});
exerciseAiFilter.addEventListener("click", () => {
  aiCoachingOnly = !aiCoachingOnly;
  exerciseAiFilter.classList.toggle("active", aiCoachingOnly);
  exerciseAiFilter.setAttribute("aria-pressed", String(aiCoachingOnly));
  renderExerciseOptionsList();
});
exerciseDirectInput.addEventListener(
  "click",
  () => selectExercise("custom:new")
);
recommendationButton.addEventListener("click", () => requestRecommendation(false));
recommendationRegenerate.addEventListener("click", () => requestRecommendation(true));
recommendationApply.addEventListener("click", applyRecommendation);
recommendationResultClose.addEventListener(
  "click",
  () => resetRecommendationState()
);
completionSheetClose.addEventListener("click", closeCompletionSheet);
completionCancel.addEventListener("click", closeCompletionSheet);
completionForm.addEventListener("submit", submitCompletion);
completionForm.querySelectorAll('input[name="exercise_intensity"]').forEach(
  (input) => input.addEventListener("change", () => {
    completionIntensityChanged = true;
  })
);
completionSheetOverlay.addEventListener("click", (event) => {
  if (event.target === completionSheetOverlay) {
    closeCompletionSheet();
  }
});

routineSheetOverlay.addEventListener("click", (event) => {
  if (event.target === routineSheetOverlay) {
    closeRoutineSheet();
  }
});

window.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !completionSheetOverlay.hidden) {
    closeCompletionSheet();
    return;
  }
  if (
    event.key === "Escape"
    && !routineSheetOverlay.hidden
  ) {
    closeRoutineSheet();
  }
});

routineForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (
    isSavingPlan
    || (
      formMode === "create"
      && exerciseListState !== "ready"
    )
  ) {
    return;
  }

  const userId = getLoginUserId();

  if (!userId) {
    window.location.href = "/login";
    return;
  }

  if (!routineForm.reportValidity()) {
    return;
  }

  if (
    formMode === "edit"
    && (
      !editingPlan
      || !editingPlan.workout_plan_id
    )
  ) {
    console.error(
      "운동 계획 수정 정보가 올바르지 않습니다.",
      editingPlan
    );

    showFormError(
      "수정할 운동 계획 정보를 확인할 수 없습니다."
    );

    return;
  }

  clearFormError();

  const formData = new FormData(routineForm);
  let sets;

  try {
    sets = collectSetPayload();
  } catch (error) {
    showFormError(error.message);
    return;
  }

  const editablePayload = {
    estimated_minutes: Number(formData.get("estimated_minutes")),
    sets,
  };

  isSavingPlan = true;
  routineSaveButton.textContent =
    formMode === "edit"
      ? "수정 중"
      : "저장 중";
  updateSaveButtonState();

  try {
    if (
      formMode === "edit"
      && editingPlan
    ) {
      await updatePlan(
        userId,
        editingPlan.workout_plan_id,
        editablePayload
      );
    } else {
      const selection = formData.get("exercise_selection");
      const [exerciseType, exerciseIdentifier] = String(
        selection || ""
      ).split(":");

      let exercisePayload;

      if (exerciseType === "custom" && exerciseIdentifier === "new") {
        const createdExercise = await createCustomExercise(
          userId,
          customExerciseName.value.trim()
        );
        exercisePayload = {
          exercise_type: "custom",
          user_exercise_id: createdExercise.user_exercise_id,
        };
      } else if (exerciseType === "custom") {
        exercisePayload = {
          exercise_type: "custom",
          user_exercise_id: Number(exerciseIdentifier),
        };
      } else if (exerciseType === "default") {
        exercisePayload = {
          exercise_type: "default",
          exercise_id: Number(exerciseIdentifier),
        };
      } else {
        throw new Error("운동을 선택해 주세요.");
      }

      const createPayload = {
        ...exercisePayload,
        plan_date: formData.get("plan_date"),
        ...editablePayload,
      };

      await createOrUpdatePlan(userId, createPayload);
      activePlanDate = createPayload.plan_date;
    }

    invalidateDashboard();

    isSavingPlan = false;
    updateSaveButtonState();
    closeRoutineSheet();

    calendarStartDate = startOfCalendarRange(activePlanDate);
    setPlanDateToUrl(activePlanDate);
    await Promise.all([
      loadPlan(userId, activePlanDate),
      loadCalendarPlanCounts(),
    ]);
  } catch (error) {
    console.error(
      formMode === "edit"
        ? "운동 계획 수정 실패:"
        : "운동 계획 저장 실패:",
      error
    );
    showFormError(
      error.message
      || (
        formMode === "edit"
          ? "운동 계획을 수정하지 못했습니다."
          : "운동 계획을 저장하지 못했습니다."
      )
    );
  } finally {
    isSavingPlan = false;
    routineSaveButton.textContent =
      formMode === "edit"
        ? "수정 완료"
        : "저장";
    updateSaveButtonState();
  }
});

async function initializeRoutine() {
  const userId = getLoginUserId();

  if (!userId) {
    window.location.href = "/login";
    return;
  }

  const initialDate = getPlanDateFromUrl() || getKstDateString();
  activePlanDate = initialDate;
  calendarStartDate = startOfCalendarRange(initialDate);
  setPlanDateToUrl(initialDate);
  renderRoutineCalendar();

  try {
    await Promise.all([
      loadCalendarPlanCounts(),
      loadPlan(userId, initialDate),
    ]);
  } catch (error) {
    if (error.name === "AbortError") return;
    console.error("루틴 초기화 실패:", error);
    routineMessage.hidden = false;
    routineMessage.textContent =
      error.message
      || "운동 계획을 불러오지 못했습니다.";
  }
}

window.addEventListener("popstate", () => {
  const planDate = getPlanDateFromUrl() || getKstDateString();
  selectRoutineDate(planDate, { updateUrl: false });
});

initializeRoutine();
