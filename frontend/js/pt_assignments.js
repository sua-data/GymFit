(function () {
  const state = document.querySelector("#assignmentState");
  const list = document.querySelector("#assignmentList");
  const manualOverlay = document.querySelector("#manualRecordOverlay");
  const manualForm = document.querySelector("#manualRecordForm");
  const manualError = document.querySelector("#manualRecordError");
  let user = null;
  let statusFilter = "";
  let busy = false;
  let manualAssignment = null;

  function getUser() {
    try {
      const value = JSON.parse(sessionStorage.getItem("gymfitUser") || "null");
      const userId = Number(value?.user_id ?? value?.userId);
      return userId > 0 ? { ...value, user_id: userId } : null;
    } catch {
      return null;
    }
  }

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        "X-User-Id": String(user.user_id),
      },
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.detail || "요청을 처리하지 못했습니다.");
    return body;
  }

  const statusName = value => ({ ASSIGNED: "진행 전", IN_PROGRESS: "진행 중", COMPLETED: "완료", CANCELLED: "취소" }[value] || value);
  const targetText = item => [item.target_sets && `${item.target_sets}세트`, item.target_reps && `${item.target_reps}회`, item.target_minutes && `${item.target_minutes}분`].filter(Boolean).join(" · ");

  function button(label, handler, className = "") {
    const element = document.createElement("button");
    element.type = "button";
    element.className = className;
    element.textContent = label;
    element.addEventListener("click", handler);
    return element;
  }

  async function startAssignment(item) {
    if (busy) return;
    if (!item.ai_coaching_supported) {
      await openManualRecord(item);
      return;
    }
    if (!item.target_sets || !item.target_reps) {
      alert("실시간 코칭에는 목표 세트와 반복 횟수가 필요합니다.");
      return;
    }
    busy = true;
    try {
      if (item.status === "ASSIGNED") {
        await api(`/api/pt/assignments/${item.assignment_id}/start`, { method: "PATCH", body: "{}" });
      }
      const params = new URLSearchParams({
        exercise_code: item.exercise_code,
        sets: String(item.target_sets),
        reps: String(item.target_reps),
        target_minutes: String(item.target_minutes || 0),
        assignment_id: String(item.assignment_id),
        source: "PT_ASSIGNMENT",
      });
      window.location.href = `/coaching?${params.toString()}`;
    } catch (error) {
      alert(error.message);
      busy = false;
    }
  }

  async function openManualRecord(item) {
    if (busy) return;
    busy = true;
    try {
      if (item.status === "ASSIGNED") {
        await api(`/api/pt/assignments/${item.assignment_id}/start`, { method: "PATCH", body: "{}" });
      }
      manualAssignment = { ...item, status: "IN_PROGRESS" };
      manualForm.reset();
      document.querySelector("#manualCompletedSets").value = item.target_sets || 0;
      document.querySelector("#manualRepetitions").value = item.target_reps && item.target_sets ? item.target_reps * item.target_sets : item.target_reps || 0;
      document.querySelector("#manualMinutes").value = item.target_minutes || 0;
      document.querySelector("#manualRecordExercise").textContent = `${item.exercise_name} · 수동 기록`;
      manualError.textContent = "";
      manualOverlay.hidden = false;
      document.body.style.overflow = "hidden";
    } catch (error) {
      manualError.textContent = error.message;
    } finally {
      busy = false;
    }
  }

  function closeManualRecord() {
    if (busy) return;
    manualOverlay.hidden = true;
    manualAssignment = null;
    document.body.style.overflow = "";
  }

  function render(items) {
    list.innerHTML = "";
    state.hidden = items.length > 0;
    list.hidden = items.length === 0;
    if (!items.length) {
      state.innerHTML = "<strong>예정된 PT 숙제가 없습니다.</strong><p>새 숙제가 등록되면 여기에서 확인할 수 있습니다.</p>";
      return;
    }
    items.forEach(item => {
      const card = document.createElement("article");
      card.className = "assignment-item";
      const title = document.createElement("h3");
      title.textContent = item.title;
      card.append(title);
      [
        item.exercise_name,
        `트레이너 ${item.trainer_name}`,
        `목표 ${targetText(item)}`,
        item.weight_kg != null
          ? `사용 중량 ${Number(item.weight_kg)}kg`
          : "맨몸 또는 중량 없음",
        `${item.assigned_date} ~ ${item.due_date || "기한 없음"}`,
        item.description,
      ]
        .filter(Boolean).forEach(text => {
          const paragraph = document.createElement("p");
          paragraph.textContent = text;
          card.append(paragraph);
        });
      const meta = document.createElement("div");
      meta.className = "assignment-meta";
      meta.innerHTML = `<span class="assignment-badge">${statusName(item.status)}</span>${item.is_overdue ? '<span class="assignment-badge overdue">기한 지남</span>' : ""}`;
      card.append(meta);
      if (["ASSIGNED", "IN_PROGRESS"].includes(item.status)) {
        const actions = document.createElement("div");
        actions.className = "assignment-actions";
        actions.append(button(item.ai_coaching_supported ? "숙제 운동 시작" : "숙제 기록 입력", () => startAssignment(item)));
        card.append(actions);
      }
      list.append(card);
    });
  }

  async function load() {
    state.hidden = false;
    list.hidden = true;
    state.textContent = "숙제를 불러오는 중입니다.";
    try {
      const query = statusFilter ? `?status=${statusFilter}` : "";
      render((await api(`/api/pt/assignments/member${query}`)).items);
    } catch (error) {
      state.innerHTML = "<strong>PT 숙제를 불러오지 못했습니다.</strong><p>네트워크 연결을 확인한 뒤 다시 시도해 주세요.</p>";
      const retryButton = button("다시 시도", load);
      retryButton.className = "gymfit-state-action";
      state.append(retryButton);
    }
  }

  document.querySelector("#assignmentFilters")?.addEventListener("click", event => {
    const selected = event.target.closest("button[data-status]");
    if (!selected) return;
    document.querySelectorAll("#assignmentFilters button").forEach(item => {
      const isSelected = item === selected;
      item.classList.toggle("active", isSelected);
      item.setAttribute("aria-selected", String(isSelected));
    });
    statusFilter = selected.dataset.status;
    load();
  });

  manualForm.addEventListener("submit", async event => {
    event.preventDefault();
    if (busy || !manualAssignment) return;
    const payload = {
      completed_sets: Number(document.querySelector("#manualCompletedSets").value || 0),
      repetition_count: Number(document.querySelector("#manualRepetitions").value || 0),
      workout_minutes: Number(document.querySelector("#manualMinutes").value || 0),
      calories: document.querySelector("#manualCalories").value === "" ? null : Number(document.querySelector("#manualCalories").value),
      note: document.querySelector("#manualNote").value.trim() || null,
    };
    if (payload.completed_sets <= 0 && payload.repetition_count <= 0 && payload.workout_minutes <= 0) {
      manualError.textContent = "완료 세트, 반복 횟수, 운동 시간 중 하나 이상을 입력해 주세요.";
      return;
    }
    busy = true;
    document.querySelector("#manualRecordSave").disabled = true;
    try {
      await api(`/api/pt/assignments/${manualAssignment.assignment_id}/manual-record`, { method: "POST", body: JSON.stringify(payload) });
      manualOverlay.hidden = true;
      manualAssignment = null;
      document.body.style.overflow = "";
      await load();
    } catch (error) {
      manualError.textContent = error.message;
    } finally {
      busy = false;
      document.querySelector("#manualRecordSave").disabled = false;
    }
  });
  document.querySelector("#manualRecordCancel").addEventListener("click", closeManualRecord);
  document.querySelector("#manualRecordBackdrop").addEventListener("click", closeManualRecord);

  user = getUser();
  if (!user) { location.replace("/login"); return; }
  if (user.account_type !== "MEMBER") { location.replace("/trainer/assignments"); return; }
  load();
})();
