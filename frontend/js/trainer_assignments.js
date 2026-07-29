(function () {
  const form = document.querySelector("#assignmentForm");
  const formOverlay = document.querySelector("#assignmentFormOverlay");
  const memberSelect = document.querySelector("#assignmentMember");
  const memberCards = document.querySelector("#assignmentMemberCards");
  const memberSummary = document.querySelector("#selectedMemberSummary");
  const exerciseSelect = document.querySelector("#assignmentExercise");
  const exerciseSearch = document.querySelector("#exerciseSearch");
  const categoryFilters = document.querySelector("#exerciseCategoryFilters");
  const exerciseCardList = document.querySelector("#exerciseCardList");
  const selectedExerciseSummary = document.querySelector("#selectedExerciseSummary");
  const customExerciseFields = document.querySelector("#customExerciseFields");
  const state = document.querySelector("#assignmentState");
  const list = document.querySelector("#assignmentList");
  const message = document.querySelector("#assignmentFormMessage");
  const saveButton = document.querySelector("#assignmentSave");
  const cancelEditButton = document.querySelector("#assignmentCancelEdit");
  const openFormButton = document.querySelector("#openAssignmentForm");
  let user = null;
  let members = [];
  let assignments = [];
  let exerciseItems = [];
  let selectedExercise = null;
  let selectedMemberId = null;
  let editingId = null;
  let busy = false;
  let statusFilter = "";
  let exerciseCategory = "전체";

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

  const inputValue = selector => document.querySelector(selector).value.trim();
  const numberOrNull = selector => inputValue(selector) ? Number(inputValue(selector)) : null;
  const optionalWeightKg = () => {
    const rawValue = inputValue("#assignmentWeightKg");
    if (!rawValue) return null;
    const value = Number(rawValue);
    if (!Number.isFinite(value) || value < 0 || value > 9999.99) {
      throw new Error("사용 중량은 0kg 이상 9999.99kg 이하로 입력해 주세요.");
    }
    return value === 0 ? null : value;
  };
  const activeStatuses = new Set(["ASSIGNED", "IN_PROGRESS"]);
  const statusName = value => ({ ASSIGNED: "진행 전", IN_PROGRESS: "진행 중", COMPLETED: "완료", CANCELLED: "취소" }[value] || value);
  const dateValue = value => value ? new Date(value).getTime() || 0 : 0;

  function memberAssignments(memberId = selectedMemberId) {
    return assignments.filter(item => Number(item.member_id) === Number(memberId));
  }

  function countsFor(memberId) {
    const items = memberAssignments(memberId);
    return {
      all: items.length,
      active: items.filter(item => activeStatuses.has(item.status)).length,
      completed: items.filter(item => item.status === "COMPLETED").length,
      cancelled: items.filter(item => item.status === "CANCELLED").length,
      overdue: items.filter(item => item.is_overdue).length,
    };
  }

  function renderMembers() {
    memberCards.replaceChildren();
    memberSelect.innerHTML = '<option value="">회원 선택</option>';
    members.forEach(member => {
      memberSelect.add(new Option(`${member.member_name} (${member.member_email})`, member.member_id));
      const counts = countsFor(member.member_id);
      const card = document.createElement("button");
      card.type = "button";
      card.className = "trainer-member-card";
      card.dataset.memberId = String(member.member_id);
      card.setAttribute("role", "option");
      card.setAttribute("aria-selected", String(Number(member.member_id) === selectedMemberId));
      card.classList.toggle("selected", Number(member.member_id) === selectedMemberId);
      const name = document.createElement("strong");
      name.textContent = member.member_name;
      const email = document.createElement("span");
      email.textContent = member.member_email;
      const summary = document.createElement("small");
      summary.textContent = `진행 ${counts.active} · 기한 초과 ${counts.overdue}`;
      card.append(name, email, summary);
      card.addEventListener("click", () => selectMember(member.member_id));
      memberCards.append(card);
    });
    if (!members.length) {
      const empty = document.createElement("p");
      empty.className = "trainer-member-empty";
      empty.textContent = "현재 연결된 PT 회원이 없습니다.";
      memberCards.append(empty);
    }
    memberSelect.value = selectedMemberId ? String(selectedMemberId) : "";
  }

  function renderMemberSummary() {
    const member = members.find(item => Number(item.member_id) === selectedMemberId);
    memberSummary.hidden = !member;
    openFormButton.disabled = !member;
    if (!member) return;
    const counts = countsFor(member.member_id);
    document.querySelector("#selectedMemberName").textContent = `${member.member_name} 회원`;
    document.querySelector("#selectedMemberEmail").textContent = member.member_email;
    document.querySelector("#selectedMemberActiveCount").textContent = counts.active;
    document.querySelector("#selectedMemberCompletedCount").textContent = counts.completed;
    document.querySelector("#selectedMemberOverdueCount").textContent = counts.overdue;
    document.querySelectorAll("#assignmentFilters button").forEach(button => {
      const count = button.dataset.status === "ACTIVE" ? counts.active
        : button.dataset.status === "COMPLETED" ? counts.completed
          : button.dataset.status === "CANCELLED" ? counts.cancelled : counts.all;
      button.querySelector("span").textContent = count;
    });
  }

  function selectMember(memberId) {
    selectedMemberId = Number(memberId) || null;
    renderMembers();
    renderMemberSummary();
    renderAssignments();
  }

  function filteredAssignments() {
    const items = memberAssignments().filter(item => {
      if (!statusFilter) return true;
      if (statusFilter === "ACTIVE") return activeStatuses.has(item.status);
      return item.status === statusFilter;
    });
    return items.sort((a, b) => {
      const group = item => activeStatuses.has(item.status) ? 0 : item.status === "COMPLETED" ? 1 : 2;
      if (group(a) !== group(b)) return group(a) - group(b);
      if (activeStatuses.has(a.status)) {
        if (a.is_overdue !== b.is_overdue) return a.is_overdue ? -1 : 1;
        return dateValue(a.due_date) - dateValue(b.due_date) || Number(b.assignment_id) - Number(a.assignment_id);
      }
      if (a.status === "COMPLETED") return dateValue(b.completed_at) - dateValue(a.completed_at);
      return dateValue(b.updated_at || b.created_at) - dateValue(a.updated_at || a.created_at);
    });
  }

  function actionButton(label, handler, className = "") {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = label;
    button.className = className;
    button.addEventListener("click", handler);
    return button;
  }

  function renderAssignments() {
    list.replaceChildren();
    if (!selectedMemberId) {
      state.hidden = false;
      list.hidden = true;
      state.innerHTML = members.length
        ? "<strong>담당 회원을 선택해 주세요.</strong><p>회원을 선택하면 숙제와 수행 상태를 확인할 수 있어요.</p>"
        : "<strong>아직 연결된 담당 회원이 없어요.</strong><p>회원 연결 요청이 승인되면 이곳에서 관리할 수 있어요.</p>";
      return;
    }
    const items = filteredAssignments();
    state.hidden = items.length > 0;
    list.hidden = items.length === 0;
    if (!items.length) {
      state.innerHTML = "<strong>선택한 상태의 숙제가 없어요.</strong><p>다른 상태를 선택하거나 새 PT 숙제를 등록해 주세요.</p>";
      return;
    }
    items.forEach(item => {
      const card = document.createElement("article");
      card.className = `trainer-assignment-card status-${String(item.status).toLowerCase()}`;
      card.classList.toggle("overdue", item.is_overdue);
      const heading = document.createElement("div");
      heading.className = "trainer-assignment-card-heading";
      const title = document.createElement("h3");
      title.textContent = item.exercise_name;
      const badges = document.createElement("div");
      badges.className = "trainer-assignment-badges";
      if (item.is_overdue) {
        const overdue = document.createElement("span");
        overdue.className = "assignment-badge overdue";
        overdue.textContent = "기한 지남";
        badges.append(overdue);
      }
      const badge = document.createElement("span");
      badge.className = "assignment-badge";
      badge.textContent = statusName(item.status);
      badges.append(badge);
      heading.append(title, badges);
      const target = [item.target_sets && `${item.target_sets}세트`, item.target_reps && `${item.target_reps}회`, item.target_minutes && `${item.target_minutes}분`].filter(Boolean).join(" × ");
      const targetLine = document.createElement("strong");
      targetLine.className = "trainer-assignment-target";
      targetLine.textContent = target || "목표 미설정";
      const weightLine = document.createElement("p");
      weightLine.className = "trainer-assignment-weight";
      weightLine.textContent = item.weight_kg != null
        ? `사용 중량 ${Number(item.weight_kg)}kg`
        : "맨몸 또는 중량 없음";
      const schedule = document.createElement("p");
      schedule.textContent = `${item.assigned_date} 배정 · ${item.due_date ? `${item.due_date} 마감` : "마감일 없음"}`;
      card.append(heading, targetLine, weightLine, schedule);
      if (item.description) {
        const description = document.createElement("p");
        description.className = "trainer-assignment-description";
        description.textContent = item.description;
        card.append(description);
      }
      const actions = document.createElement("div");
      actions.className = "assignment-actions";
      if (activeStatuses.has(item.status)) {
        actions.append(
          actionButton("수정", () => openEdit(item), "secondary"),
          actionButton("취소", () => cancelAssignment(item.assignment_id), "danger")
        );
      } else if (item.status === "COMPLETED") {
        actions.append(actionButton("결과 보기", () => {
          window.dispatchEvent(new CustomEvent("trainerAssignmentResultRequested", { detail: { assignmentId: item.assignment_id } }));
        }));
      }
      if (actions.childElementCount) card.append(actions);
      list.append(card);
    });
  }

  async function loadData() {
    state.hidden = false;
    list.hidden = true;
    state.textContent = "숙제를 불러오고 있습니다.";
    try {
      const [memberData, assignmentItems] = await Promise.all([
        api("/api/pt/my-members"),
        loadAllAssignments(),
      ]);
      members = memberData.items;
      assignments = assignmentItems;
      if (!members.some(item => Number(item.member_id) === selectedMemberId)) {
        selectedMemberId = members.length ? Number(members[0].member_id) : null;
      }
      renderMembers();
      renderMemberSummary();
      renderAssignments();
    } catch (error) {
      console.error("PT 숙제 관리 정보 조회 실패:", error);
      state.hidden = false;
      state.innerHTML = "<strong>담당 회원과 숙제를 불러오지 못했어요.</strong><p>네트워크 연결을 확인한 뒤 다시 시도해 주세요.</p>";
      const retryButton = actionButton("다시 시도", loadData, "gymfit-state-action");
      state.append(retryButton);
    }
  }

  async function loadAllAssignments() {
    const items = [];
    const limit = 200;
    let total = 0;
    do {
      const page = await api(`/api/pt/assignments/trainer?limit=${limit}&offset=${items.length}`);
      items.push(...page.items);
      total = Number(page.total) || 0;
      if (!page.items.length) break;
    } while (items.length < total);
    return items;
  }

  async function loadExercises(selectedValue = "") {
    exerciseSelect.disabled = true;
    exerciseSelect.innerHTML = '<option value="">운동 선택</option>';
    exerciseItems = [];
    selectedExercise = null;
    updateSelectedExercise();
    exerciseCardList.innerHTML = "<p>운동 목록을 불러오고 있습니다.</p>";
    if (!selectedMemberId) {
      exerciseCardList.innerHTML = "<p>회원을 먼저 선택해 주세요.</p>";
      return false;
    }
    try {
      const data = await api(
        `/api/pt/assignments/exercises?member_id=${selectedMemberId}`
      );
      exerciseItems = Array.isArray(data?.items) ? data.items : [];
      exerciseItems.forEach(item => {
        const value = exerciseValue(item);
        exerciseSelect.add(new Option(item.exercise_name, value));
      });
      exerciseSelect.disabled = false;
      if (selectedValue) {
        selectExercise(selectedValue, false);
      }
      renderExerciseFilters();
      renderExerciseCards();
      return true;
    } catch (error) {
      exerciseSelect.disabled = true;
      exerciseCardList.innerHTML =
        "<p class=\"exercise-load-error\">운동 목록을 불러오지 못했습니다. 잠시 후 다시 시도해 주세요.</p>";
      message.textContent = error.message;
      return false;
    }
  }

  const exerciseValue = item =>
    `${item.exercise_type}:${item.exercise_id ?? item.user_exercise_id}`;

  function selectExercise(value, rerender = true) {
    const next = exerciseItems.find(item => exerciseValue(item) === value) || null;
    selectedExercise = next;
    exerciseSelect.value = next ? value : "";
    updateSelectedExercise();
    if (rerender) renderExerciseCards();
  }

  function updateSelectedExercise() {
    selectedExerciseSummary.classList.toggle("has-selection", Boolean(selectedExercise));
    selectedExerciseSummary.textContent = selectedExercise
      ? `선택됨: ${selectedExercise.exercise_name}${
        selectedExercise.exercise_code ? ` (${selectedExercise.exercise_code})` : ""
      }`
      : "선택한 운동이 없습니다.";
  }

  function renderExerciseFilters() {
    const categories = ["전체", "하체", "가슴", "등", "어깨", "팔", "코어", "유산소", "회원 운동"];
    categoryFilters.replaceChildren();
    categories.forEach(category => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = category;
      button.classList.toggle("active", category === exerciseCategory);
      button.addEventListener("click", () => {
        exerciseCategory = category;
        renderExerciseFilters();
        renderExerciseCards();
      });
      categoryFilters.append(button);
    });
  }

  function renderExerciseCards() {
    const keyword = exerciseSearch.value.trim().toLowerCase();
    const filtered = exerciseItems.filter(item => {
      const categoryMatches = exerciseCategory === "전체"
        || (exerciseCategory === "회원 운동" ? item.exercise_type === "custom" : item.category === exerciseCategory);
      return categoryMatches && (!keyword || item.exercise_name.toLowerCase().includes(keyword) || String(item.exercise_code || "").toLowerCase().includes(keyword));
    });
    exerciseCardList.replaceChildren();
    if (!filtered.length) {
      const empty = document.createElement("p");
      empty.textContent = "조건에 맞는 운동이 없습니다.";
      exerciseCardList.append(empty);
      return;
    }
    filtered.forEach(item => {
      const value = exerciseValue(item);
      const card = document.createElement("button");
      card.type = "button";
      card.className = "exercise-choice-card";
      card.classList.toggle("selected", exerciseSelect.value === value);
      card.setAttribute("role", "option");
      card.setAttribute("aria-selected", String(exerciseSelect.value === value));
      card.dataset.exerciseValue = value;
      const title = document.createElement("strong");
      title.textContent = item.exercise_name;
      const meta = document.createElement("span");
      meta.textContent = `${item.category || "미분류"} · ${item.exercise_type === "custom" ? "회원 운동" : "기본 운동"}`;
      const mode = document.createElement("em");
      mode.textContent = (item.ai_coaching_supported || item.coaching_supported) ? "실시간 코칭" : "기록형 운동";
      card.append(title, meta, mode);
      card.addEventListener("click", () => selectExercise(value));
      exerciseCardList.append(card);
    });
  }

  function resetForm() {
    editingId = null;
    form.reset();
    const today = new Date().toISOString().slice(0, 10);
    document.querySelector("#assignmentDate").value = today;
    document.querySelector("#assignmentDueDate").value = today;
    exerciseSelect.disabled = true;
    exerciseItems = [];
    selectedExercise = null;
    updateSelectedExercise();
    document.querySelector("#assignmentFormTitle").textContent = "새 숙제";
    document.querySelector("#assignmentFormMemberName").textContent = members.find(item => Number(item.member_id) === selectedMemberId)?.member_name || "";
    saveButton.textContent = "숙제 등록";
    cancelEditButton.hidden = true;
    customExerciseFields.hidden = true;
    message.textContent = "";
  }

  async function openCreate() {
    if (!selectedMemberId) return;
    resetForm();
    formOverlay.hidden = false;
    document.body.classList.add("assignment-sheet-open");
    await loadExercises();
  }

  async function openEdit(item) {
    selectedMemberId = Number(item.member_id);
    resetForm();
    editingId = item.assignment_id;
    formOverlay.hidden = false;
    document.body.classList.add("assignment-sheet-open");
    const existingValue =
      `${item.exercise_type}:${item.exercise_id ?? item.user_exercise_id}`;
    await loadExercises(existingValue);
    if (!selectedExercise) {
      const existingExercise = {
        exercise_type: item.exercise_type,
        exercise_id: item.exercise_id,
        user_exercise_id: item.user_exercise_id,
        exercise_code: item.exercise_code || null,
        exercise_name: item.exercise_name,
        category: item.exercise_type === "custom" ? "회원 운동" : "기존 운동",
        coaching_supported: false,
        ai_coaching_supported: false,
      };
      exerciseItems.unshift(existingExercise);
      exerciseSelect.add(
        new Option(existingExercise.exercise_name, existingValue),
        exerciseSelect.options[1] || null
      );
      exerciseSelect.disabled = false;
      selectExercise(existingValue);
    }
    document.querySelector("#assignmentDescription").value = item.description || "";
    document.querySelector("#assignmentDate").value = item.assigned_date;
    document.querySelector("#assignmentDueDate").value = item.due_date || "";
    document.querySelector("#targetSets").value = item.target_sets || "";
    document.querySelector("#targetReps").value = item.target_reps || "";
    document.querySelector("#targetMinutes").value = item.target_minutes || "";
    document.querySelector("#assignmentWeightKg").value = item.weight_kg ?? "";
    document.querySelector("#assignmentFormTitle").textContent = `${item.exercise_name} 숙제 수정`;
    saveButton.textContent = "수정 완료";
    cancelEditButton.hidden = false;
  }

  function closeForm(force = false) {
    if (busy && !force) return;
    formOverlay.hidden = true;
    document.body.classList.remove("assignment-sheet-open");
    resetForm();
  }

  async function mutate(url, payload, method = "PATCH") {
    if (busy) return;
    busy = true;
    saveButton.disabled = true;
    try {
      await api(url, { method, body: JSON.stringify(payload) });
      closeForm(true);
      await loadData();
    } catch (error) {
      message.textContent = error.message;
    } finally {
      busy = false;
      saveButton.disabled = false;
    }
  }

  async function cancelAssignment(assignmentId) {
    if (!window.confirm("이 숙제를 취소하시겠어요?")) return;
    try {
      await api(`/api/pt/assignments/${assignmentId}/cancel`, { method: "PATCH", body: "{}" });
      await loadData();
    } catch (error) {
      window.alert(error.message);
    }
  }

  openFormButton.addEventListener("click", openCreate);
  document.querySelector("#assignmentFormClose").addEventListener("click", () => closeForm());
  document.querySelector("#assignmentFormBackdrop").addEventListener("click", () => closeForm());
  cancelEditButton.addEventListener("click", () => closeForm());
  memberSelect.addEventListener("change", () => selectMember(memberSelect.value));
  exerciseSearch.addEventListener("input", renderExerciseCards);
  document.querySelector("#openCustomExercise").addEventListener("click", () => { customExerciseFields.hidden = !customExerciseFields.hidden; });
  document.querySelector("#saveCustomExercise").addEventListener("click", async () => {
    if (busy || !selectedMemberId) return;
    const exerciseName = document.querySelector("#customExerciseName").value.trim();
    const category = document.querySelector("#customExerciseCategory").value;
    if (!exerciseName) { message.textContent = "직접 입력 운동명을 입력해 주세요."; return; }
    busy = true;
    try {
      const created = await api("/api/pt/assignments/custom-exercises", { method: "POST", body: JSON.stringify({ member_id: selectedMemberId, exercise_name: exerciseName, category: category || null }) });
      await loadExercises(`custom:${created.user_exercise_id}`);
      customExerciseFields.hidden = true;
      document.querySelector("#customExerciseName").value = "";
      message.textContent = "회원 운동을 추가하고 선택했습니다.";
    } catch (error) {
      message.textContent = error.message;
    } finally {
      busy = false;
    }
  });

  form.addEventListener("submit", event => {
    event.preventDefault();
    if (busy) return;
    message.textContent = "";
    let weightKg;
    try {
      weightKg = optionalWeightKg();
    } catch (error) {
      message.textContent = error.message;
      return;
    }
    const targetValues = {
      target_sets: numberOrNull("#targetSets"),
      target_reps: numberOrNull("#targetReps"),
      target_minutes: numberOrNull("#targetMinutes"),
    };
    if (!Object.values(targetValues).some(Boolean)) { message.textContent = "목표값을 하나 이상 입력해 주세요."; return; }
    const selectedValue = selectedExercise
      ? exerciseValue(selectedExercise)
      : exerciseSelect.value;
    const [exerciseType, exerciseId] = selectedValue.split(":");
    if (!selectedExercise || !exerciseType || !exerciseId) {
      message.textContent = "운동을 선택해 주세요.";
      return;
    }
    const payload = {
      exercise_id: exerciseType === "default" ? Number(exerciseId) : null,
      user_exercise_id: exerciseType === "custom" ? Number(exerciseId) : null,
      description: inputValue("#assignmentDescription") || null,
      assigned_date: inputValue("#assignmentDate"),
      due_date: inputValue("#assignmentDueDate") || null,
      weight_kg: weightKg,
      ...targetValues,
    };
    if (editingId) mutate(`/api/pt/assignments/${editingId}`, payload);
    else mutate("/api/pt/assignments", { member_id: selectedMemberId, ...payload }, "POST");
  });

  document.querySelector("#assignmentFilters").addEventListener("click", event => {
    const selected = event.target.closest("button[data-status]");
    if (!selected) return;
    document.querySelectorAll("#assignmentFilters button").forEach(button => {
      const isSelected = button === selected;
      button.classList.toggle("active", isSelected);
      button.setAttribute("aria-selected", String(isSelected));
    });
    statusFilter = selected.dataset.status;
    renderAssignments();
  });

  user = getUser();
  if (!user) { location.replace("/login"); return; }
  if (String(user.account_type).toUpperCase() !== "TRAINER") { location.replace("/pt/assignments"); return; }
  resetForm();
  loadData();
})();
