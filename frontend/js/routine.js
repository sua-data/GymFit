const routineDate = document.querySelector("#routineDate");
const routineProgress = document.querySelector("#routineProgress");
const exerciseCount = document.querySelector("#exerciseCount");
const totalMinutes = document.querySelector("#totalMinutes");
const routineMessage = document.querySelector("#routineMessage");
const routineList = document.querySelector("#routineList");
const routineAddButton = document.querySelector("#routineAddButton");
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

let activePlanDate = null;
let isSavingPlan = false;
let completingPlanId = null;
let deletingPlanId = null;
let exerciseListState = "idle";
let formMode = "create";
let editingPlan = null;

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

function escapeHtml(value) {
  const element = document.createElement("div");
  element.textContent = value ?? "";
  return element.innerHTML;
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

function getLocalDateValue() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(
    now.getMonth() + 1
  ).padStart(2, "0");
  const day = String(
    now.getDate()
  ).padStart(2, "0");

  return `${year}-${month}-${day}`;
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

async function requestPlan(userId, planDate = null) {
  const params = new URLSearchParams();

  if (planDate) {
    params.set("plan_date", planDate);
  }

  const query = params.toString();

  const response = await fetch(
    `/api/workouts/plans/today/${userId}${
      query ? `?${query}` : ""
    }`
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
  const data = await requestPlan(userId, planDate);

  activePlanDate = data.plan_date;
  renderPlan(data);
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
      && exerciseListState !== "ready"
    );
}

function setExerciseLoadState(state, message) {
  exerciseListState = state;
  exerciseLoadMessage.textContent = message;
  exerciseLoadMessage.classList.toggle(
    "error",
    state === "error"
  );
  routineExerciseSelect.disabled =
    state !== "ready";
  exerciseRetryButton.hidden =
    state !== "error";

  updateSaveButtonState();
}

function renderExerciseOptions(exercises) {
  routineExerciseSelect.innerHTML = "";

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
  syncCustomExerciseField();
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

  routineExerciseSelect.innerHTML = `
    <option value="">
      운동 목록을 불러오는 중입니다.
    </option>
  `;

  try {
    const exercises = await requestActiveExercises(userId);

    renderExerciseOptions(exercises);

    setExerciseLoadState(
      "ready",
      exercises.length
        ? `${exercises.length}개의 운동을 선택할 수 있습니다.`
        : "등록된 운동이 없습니다. 직접 입력해 주세요."
    );
  } catch (error) {
    console.error("운동 목록 조회 실패:", error);

    routineExerciseSelect.innerHTML = `
      <option value="">
        운동 목록 조회 실패
      </option>
    `;

    setExerciseLoadState(
      "error",
      error.message
      || "운동 목록을 불러오지 못했습니다."
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
  routineExerciseSelect.disabled =
    exerciseListState !== "ready";
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

async function completePlan(userId, workoutPlanId) {
  const response = await fetch(
    `/api/workouts/plans/${workoutPlanId}/complete`,
    {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        user_id: userId,
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
  // 현재 코칭 카운터는 세트별 목표 변경을 지원하지 않으므로
  // 첫 번째 세트의 반복 횟수를 전체 세트의 targetReps로 사용합니다.
  const firstSetReps = item.sets?.[0]?.repetition_count;
  const params =
    new URLSearchParams({
      exercise_code:
        item.exercise_code,
      reps:
        String(firstSetReps || item.repetition_count),
      sets:
        String(item.sets?.length || item.set_count),
    });

  window.location.href =
    `/coaching?${params.toString()}`;
}

function getButtonState(item) {
  if (item.is_completed) {
    return {
      label: "운동 완료",
      disabled: true,
      action: "none",
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

    card.className =
      `routine-card${item.is_completed ? " completed" : ""}`;

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
          <span>${item.is_completed ? "완료" : "오늘의 운동"}</span>
          <h2>${escapeHtml(item.exercise_name)}</h2>
        </div>

        <div class="routine-meta">
          <span>${Number(item.set_count) || 0}세트</span>
          <span>${Number(item.repetition_count) || 0}회</span>
          <span>${Number(item.estimated_minutes) || 0}분</span>
        </div>

        <ol class="routine-set-summary">
          ${setDetails}
        </ol>

        <div class="routine-card-actions">
          <button
            type="button"
            class="routine-start-button"
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
      actionButton.addEventListener("click", async () => {
        if (
          !window.confirm(
            `${item.exercise_name} 운동을 완료 처리할까요?\n`
            + "운동 기록은 생성되지 않습니다."
          )
        ) {
          return;
        }

        if (completingPlanId !== null) {
          return;
        }

        const userId = getLoginUserId();

        if (!userId) {
          window.location.href = "/login";
          return;
        }

        completingPlanId = item.workout_plan_id;
        actionButton.disabled = true;
        actionButton.textContent = "처리 중";

        try {
          await completePlan(userId, item.workout_plan_id);
          await loadPlan(userId, activePlanDate);
        } catch (error) {
          console.error("운동 계획 완료 처리 실패:", error);
          alert(
            error.message
            || "운동 계획을 완료 처리하지 못했습니다."
          );
          actionButton.disabled = false;
          actionButton.textContent = buttonState.label;
        } finally {
          completingPlanId = null;
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
        await loadPlan(userId, activePlanDate);
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
routineSheetCloseButton.addEventListener("click", closeRoutineSheet);
routineCancelButton.addEventListener("click", closeRoutineSheet);
exerciseRetryButton.addEventListener("click", loadActiveExercises);
routineAddSetButton.addEventListener(
  "click",
  () => createSetRow({}, true)
);
routineExerciseSelect.addEventListener("change", () => {
  syncCustomExerciseField();
});

routineSheetOverlay.addEventListener("click", (event) => {
  if (event.target === routineSheetOverlay) {
    closeRoutineSheet();
  }
});

window.addEventListener("keydown", (event) => {
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

    isSavingPlan = false;
    updateSaveButtonState();
    closeRoutineSheet();

    await loadPlan(userId, activePlanDate);
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

  try {
    await loadPlan(userId);
  } catch (error) {
    console.error("오늘의 루틴 조회 실패:", error);
    routineMessage.hidden = false;
    routineMessage.textContent =
      error.message
      || "오늘의 운동 계획을 불러오지 못했습니다.";
  }
}

initializeRoutine();
