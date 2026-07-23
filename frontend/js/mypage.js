const GOAL_LABELS = {
  WEIGHT_LOSS: "체중 감량",
  MUSCLE_GAIN: "근력 증가",
  BODY_SHAPE: "체형 관리",
  HEALTH: "건강 유지",
};
const LEVEL_LABELS = { BEGINNER: "초급", INTERMEDIATE: "중급", ADVANCED: "고급" };

function installExtendedProfileUI() {
  document.querySelector("#profileLevel")?.closest("div")?.insertAdjacentHTML("afterend", '<div id="profileWeeklyRow"><dt>주간 운동 목표</dt><dd id="profileWeekly">-</dd></div>');
  document.querySelector("#profileLevelSelect")?.closest("label")?.insertAdjacentHTML("afterend", '<label>주간 운동 횟수<select id="profileWeeklySelect" data-gymfit-select required><option value="">선택</option><option value="1">주 1회</option><option value="2">주 2회</option><option value="3">주 3회</option><option value="4">주 4회</option><option value="5">주 5회</option><option value="6">주 6회</option><option value="7">매일</option></select></label>');
  document.querySelector(".profile-info-card")?.insertAdjacentHTML("afterend", '<section class="profile-info-card gym-card"><div class="section-heading"><span>MY GYM</span><h2>내 헬스장</h2></div><div class="gym-current"><div><strong id="currentGymName">소속 헬스장 없음</strong><p id="currentGymAddress">헬스장을 연결하면 이곳에 표시됩니다.</p></div><button type="button" id="openGymSheetButton">등록</button></div><div class="gym-link-grid" id="gymLinkGrid" hidden><a class="gym-detail-link" href="/my-gym">상세보기</a><a class="gym-detail-link secondary" href="/machines">헬스장 머신</a></div><div class="employment-status-row" id="gymEmploymentStatusRow" hidden><span class="employment-status-label">소속 승인 상태</span><span class="employment-status-badge none" id="gymEmploymentStatusBadge">미등록</span><div class="employment-info-wrap"><button class="employment-info-button" type="button" data-employment-info aria-label="헬스장 변경 안내" aria-expanded="false">ⓘ</button><aside class="employment-info-popover" data-employment-popover hidden><h3>헬스장 변경 안내</h3><p>승인 후에도 소속 헬스장을 변경할 수 있습니다. 변경 시 재직·소속 증빙을 다시 제출해야 하며, 관리자 승인 전까지 헬스장 관리 기능이 제한됩니다.</p></aside></div></div></section>');
  document.querySelector("#profileEditOverlay")?.insertAdjacentHTML("afterend", '<div class="sheet-overlay" id="gymEditOverlay" hidden><button class="sheet-backdrop" id="gymEditBackdrop" type="button" aria-label="헬스장 변경 닫기"></button><section class="profile-sheet" role="dialog" aria-modal="true"><header><div><span>GYM SEARCH</span><h2>헬스장 변경</h2></div><button type="button" id="gymEditClose" aria-label="닫기">×</button></header><div class="gym-search" data-gym-search><div class="gym-search-row"><input type="search" data-gym-query placeholder="헬스장명 또는 주소"><button type="button" data-gym-search-button>검색</button></div><p data-gym-status>헬스장을 검색하고 결과에서 선택해 주세요.</p><div class="gym-search-results" data-gym-results hidden></div><div class="selected-gym" data-selected-gym hidden><strong data-selected-gym-name></strong><span data-selected-gym-address></span><button type="button" data-clear-gym>선택 해제</button></div></div><p class="form-message" id="gymSaveMessage" hidden></p><button type="button" class="save-profile-button" id="gymSaveButton">선택한 헬스장 저장</button></section></div>');
}

installExtendedProfileUI();

const profileLoading = document.querySelector("#profileLoading");
const profileError = document.querySelector("#profileError");
const profileErrorMessage = document.querySelector("#profileErrorMessage");
const profileRetryButton = document.querySelector("#profileRetryButton");
const profileContent = document.querySelector("#profileContent");
const profileEditOverlay = document.querySelector("#profileEditOverlay");
const profileEditForm = document.querySelector("#profileEditForm");
const profileNameInput = document.querySelector("#profileNameInput");
const profileEmailInput = document.querySelector("#profileEmailInput");
const profileLevelSelect = document.querySelector("#profileLevelSelect");
const profileGoalChoices = document.querySelector("#profileGoalChoices");
const profileGoalError = document.querySelector("#profileGoalError");
const profileFormMessage = document.querySelector("#profileFormMessage");
const profileSaveButton = document.querySelector("#profileSaveButton");
const profileWeeklySelect = document.querySelector("#profileWeeklySelect");
const logoutOverlay = document.querySelector("#logoutOverlay");
const mypageToast = document.querySelector("#mypageToast");
const passwordChangeOverlay = document.querySelector("#passwordChangeOverlay");
const passwordChangeForm = document.querySelector("#passwordChangeForm");
const passwordChangeMessage = document.querySelector("#passwordChangeMessage");
const passwordChangeButton = document.querySelector("#passwordChangeButton");
const withdrawOverlay = document.querySelector("#withdrawOverlay");
const withdrawForm = document.querySelector("#withdrawForm");
const withdrawMessage = document.querySelector("#withdrawMessage");
const withdrawButton = document.querySelector("#withdrawButton");

let currentUser = null;
let trainerActivity = null;
let isSaving = false;
let isAccountSubmitting = false;
let toastTimer = null;
const gymSearchController = window.createGymSearch(document.querySelector("[data-gym-search]"));

function getSessionUser() {
  try {
    const value = JSON.parse(sessionStorage.getItem("gymfitUser") || "null");
    const userId = Number(value?.user_id ?? value?.userId);
    return Number.isInteger(userId) && userId > 0 ? { ...value, user_id: userId } : null;
  } catch {
    return null;
  }
}

function getErrorMessage(error, fallback) {
  return error instanceof Error && error.message ? error.message : fallback;
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, options);
  let body = null;
  try { body = await response.json(); } catch { body = null; }
  if (!response.ok) {
    const detail = Array.isArray(body?.detail)
      ? body.detail.map((item) => item.msg).filter(Boolean).join(" ")
      : body?.detail;
    throw new Error(detail || "요청을 처리하지 못했습니다.");
  }
  return body;
}

function getDisplayName(user) {
  const name = String(user?.name || "").trim();
  if (name) return name;
  const emailPrefix = String(user?.email || "").split("@")[0].trim();
  return emailPrefix || "GYMFIT 회원";
}

function getRoleLabel(user) {
  if (typeof window.getUserRoleLabel === "function") {
    return window.getUserRoleLabel(user);
  }
  const accountType = String(user?.account_type ?? user?.accountType ?? "").toUpperCase();
  const hasActiveTrainer = user?.has_active_trainer === true || user?.hasActiveTrainer === true;
  if (accountType === "TRAINER") return "트레이너";
  if (accountType === "MEMBER" && hasActiveTrainer) return "PT 회원";
  return "개인 운동자";
}

function formatDate(value) {
  if (!value) return "-";
  const match = String(value).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return match ? `${match[1]}.${match[2]}.${match[3]}` : "-";
}

function showToast(message) {
  window.clearTimeout(toastTimer);
  mypageToast.textContent = message;
  mypageToast.hidden = false;
  toastTimer = window.setTimeout(() => { mypageToast.hidden = true; }, 2400);
}

function createMenuItem(label, action, comingSoon = false, danger = false) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = `menu-item mypage-action-row${danger ? " danger" : ""}`;
  const labelElement = document.createElement("span");
  labelElement.textContent = label;
  button.append(labelElement);
  if (comingSoon) {
    const badge = document.createElement("span");
    badge.className = "coming";
    badge.textContent = "준비 중";
    button.append(badge);
  } else {
    button.insertAdjacentHTML("beforeend", '<svg class="mypage-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="M9 6l6 6-6 6" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path></svg>');
  }
  button.addEventListener("click", action);
  return button;
}

function renderMenus() {
  const commonMenuList = document.querySelector("#commonMenuList");
  commonMenuList.replaceChildren(
    createMenuItem("프로필 수정", openEditSheet),
    createMenuItem("비밀번호 변경", openPasswordChangeSheet),
    createMenuItem("로그아웃", openLogoutDialog, false, true),
    createMenuItem("회원 탈퇴", openWithdrawSheet, false, true),
  );
}

function getFitnessProfileState(user) {
  const goals = (user?.goals || [])
    .map((goal) => goal.goal_name || GOAL_LABELS[goal.goal_code])
    .filter(Boolean);
  return {
    goals,
    hasGoals: goals.length > 0,
    hasLevel: Boolean(user?.exercise_level),
    hasWeeklyGoal: Number(user?.weekly_workout_days) >= 1,
  };
}

function setFitnessValue(element, value, isConfigured) {
  element.textContent = isConfigured ? value : "설정하기";
  element.classList.toggle("fitness-value-unset", !isConfigured);
}

function renderUnsetFitnessProfileState() {
  document.querySelector("#fitnessProfileEmpty").hidden = false;
  document.querySelector("#profileGoalsRow").hidden = true;
  document.querySelector("#profileLevelRow").hidden = true;
  document.querySelector("#profileWeeklyRow").hidden = true;
  const action = document.querySelector("#fitnessProfileAction");
  action.hidden = false;
  action.textContent = "내 운동 프로필 설정";
}

function renderConfiguredFitnessProfile(user, state) {
  document.querySelector("#fitnessProfileEmpty").hidden = true;
  document.querySelector("#profileGoalsRow").hidden = false;
  document.querySelector("#profileLevelRow").hidden = false;
  document.querySelector("#profileWeeklyRow").hidden = false;
  setFitnessValue(document.querySelector("#profileGoals"), state.goals.join(", "), state.hasGoals);
  setFitnessValue(document.querySelector("#profileLevel"), LEVEL_LABELS[user.exercise_level], state.hasLevel);
  const weeklyLabel = user.weekly_workout_days === 7 ? "매일" : `주 ${user.weekly_workout_days}회`;
  setFitnessValue(document.querySelector("#profileWeekly"), weeklyLabel, state.hasWeeklyGoal);
  const action = document.querySelector("#fitnessProfileAction");
  action.hidden = false;
  action.textContent = "운동 프로필 수정";
}

function renderFitnessProfile(user) {
  currentUser = user;
  const name = getDisplayName(currentUser);
  const fitnessState = getFitnessProfileState(currentUser);
  document.querySelector("#profileAvatar").textContent = Array.from(name)[0]?.toUpperCase() || "G";
  document.querySelector("#profileName").textContent = name;
  document.querySelector("#profileEmail").textContent = currentUser.email || "이메일 정보 없음";
  document.querySelector("#profileRole").textContent = getRoleLabel(currentUser);
  if (!fitnessState.hasGoals && !fitnessState.hasLevel && !fitnessState.hasWeeklyGoal) {
    renderUnsetFitnessProfileState();
  } else {
    renderConfiguredFitnessProfile(currentUser, fitnessState);
  }
  document.querySelector("#profileAccountType").textContent = getRoleLabel(currentUser);
  const gymRow = document.querySelector("#profileGymRow");
  gymRow.hidden = false;
  document.querySelector("#profileGym").textContent = currentUser.gym_name || "등록 없음";
  document.querySelector("#currentGymName").textContent = currentUser.gym_name || "소속 헬스장 없음";
  document.querySelector("#currentGymAddress").textContent = currentUser.gym_road_address || (currentUser.gym_name ? "기존 문자열 헬스장 정보" : "헬스장을 연결하면 이곳에 표시됩니다.");
  const isTrainer = currentUser.account_type === "TRAINER";
  const gymButton = document.querySelector("#openGymSheetButton");
  gymButton.disabled = false;
  gymButton.hidden = false;
  gymButton.textContent = currentUser.gym_id ? "변경" : "등록";
  document.querySelector("#gymLinkGrid").hidden = !currentUser.gym_id;
  const employmentLabels = {
    NONE: "미등록",
    PENDING: "승인 대기",
    APPROVED: "승인",
    REJECTED: "승인 거절",
  };
  const employmentStatus = String(currentUser.trainer_employment_status || "NONE").toUpperCase();
  const employmentRow = document.querySelector("#gymEmploymentStatusRow");
  const employmentBadge = document.querySelector("#gymEmploymentStatusBadge");
  employmentRow.hidden = !(isTrainer && currentUser.gym_id);
  employmentBadge.textContent = employmentLabels[employmentStatus] || "미등록";
  employmentBadge.className = `employment-status-badge ${employmentStatus.toLowerCase()}`;
  const dateValue = currentUser.last_login_at || currentUser.created_at;
  document.querySelector("#profileDateLabel").textContent = currentUser.last_login_at ? "마지막 로그인" : "가입일";
  document.querySelector("#profileDate").textContent = formatDate(dateValue);
  document.querySelectorAll(".profile-facts > div").forEach(row => row.classList.add("mypage-info-row"));
  renderMenus();
}

function renderTrainerActivity(user) {
  const card = document.querySelector("#trainerActivityCard");
  const isTrainer = String(user?.account_type || "").toUpperCase() === "TRAINER";
  card.hidden = !isTrainer;
  if (!isTrainer) return;
  const approvalStatus = String(user.trainer_approval_status || "PENDING").toUpperCase();
  const approvalMessage = document.querySelector("#trainerApprovalMessage");
  approvalMessage.textContent = approvalStatus === "APPROVED"
    ? "승인된 트레이너 계정입니다."
    : approvalStatus === "REJECTED"
      ? "승인이 거절되었습니다. 자격증 정보를 보완하면 재검토 상태로 전환됩니다."
      : "관리자 승인 검토 중입니다. 승인 전에는 일부 트레이너 기능이 제한됩니다.";
  document.querySelector("#trainerCareerYears").textContent = user.trainer_career_years == null
    ? "등록 없음"
    : `${user.trainer_career_years}년`;
  document.querySelector("#trainerMemberCount").textContent = trainerActivity?.memberCount ?? "-";
  document.querySelector("#trainerActiveAssignmentCount").textContent = trainerActivity?.activeAssignmentCount ?? "-";
  document.querySelector("#trainerCompletedAssignmentCount").textContent = trainerActivity?.completedAssignmentCount ?? "-";
  const activityMessage = document.querySelector("#trainerActivityMessage");
  activityMessage.hidden = !trainerActivity?.error;
  activityMessage.textContent = trainerActivity?.error || "";
}

function renderProfile() {
  renderFitnessProfile(currentUser);
  renderTrainerActivity(currentUser);
}

async function loadTrainerActivity(user) {
  if (String(user?.account_type || "").toUpperCase() !== "TRAINER") {
    trainerActivity = null;
    return;
  }
  const headers = { "X-User-Id": String(user.user_id) };
  try {
    const [memberData, assignedData, inProgressData, completedData] = await Promise.all([
      requestJson("/api/pt/my-members", { headers }),
      requestJson("/api/pt/assignments/trainer?status=ASSIGNED&limit=1", { headers }),
      requestJson("/api/pt/assignments/trainer?status=IN_PROGRESS&limit=1", { headers }),
      requestJson("/api/pt/assignments/trainer?status=COMPLETED&limit=1", { headers }),
    ]);
    trainerActivity = {
      memberCount: memberData.items.length,
      activeAssignmentCount: Number(assignedData.total) + Number(inProgressData.total),
      completedAssignmentCount: Number(completedData.total),
    };
  } catch (error) {
    trainerActivity = {
      error: getErrorMessage(error, "트레이너 활동 요약을 불러오지 못했습니다."),
    };
  }
}

async function loadProfile() {
  const sessionUser = getSessionUser();
  if (!sessionUser) {
    window.location.replace("/login");
    return;
  }
  profileLoading.hidden = false;
  profileError.hidden = true;
  profileContent.hidden = true;
  try {
    currentUser = await requestJson(`/api/users/${sessionUser.user_id}`);
    updateSessionUser(currentUser);
    window.dispatchEvent(new CustomEvent("gymfitUserUpdated", { detail: currentUser }));
    await loadTrainerActivity(currentUser);
    renderProfile();
    profileContent.hidden = false;
  } catch (error) {
    profileErrorMessage.textContent = getErrorMessage(error, "잠시 후 다시 시도해 주세요.");
    profileError.hidden = false;
  } finally {
    profileLoading.hidden = true;
  }
}

function renderGoalChoices() {
  profileGoalChoices.replaceChildren(...Object.entries(GOAL_LABELS).map(([code, label]) => {
    const choice = document.createElement("label");
    choice.className = "goal-choice";
    const checked = currentUser.goals?.some((goal) => goal.goal_code === code) ? " checked" : "";
    choice.innerHTML = `<input type="checkbox" name="goals" value="${code}"${checked}><span>${label}</span>`;
    return choice;
  }));
}

function openEditSheet() {
  if (!currentUser) return;
  profileNameInput.value = currentUser.name || getDisplayName(currentUser);
  profileEmailInput.value = currentUser.email || "";
  profileLevelSelect.value = currentUser.exercise_level || "BEGINNER";
  profileWeeklySelect.value = currentUser.weekly_workout_days ? String(currentUser.weekly_workout_days) : "";
  window.GymfitDropdown?.refresh(profileLevelSelect);
  window.GymfitDropdown?.refresh(profileWeeklySelect);
  document.querySelector("#memberEditFields").hidden = false;
  renderGoalChoices();
  profileGoalError.hidden = true;
  profileFormMessage.hidden = true;
  profileEditOverlay.hidden = false;
  document.body.classList.add("modal-open");
  profileNameInput.focus();
}

function closeEditSheet() {
  if (isSaving) return;
  window.GymfitDropdown?.closeAll();
  profileEditOverlay.hidden = true;
  profileEditForm.reset();
  profileFormMessage.hidden = true;
  document.body.classList.remove("modal-open");
}

function updateSessionUser(user) {
  if (typeof window.updateGymfitStoredUser === "function") {
    window.updateGymfitStoredUser(user);
    return;
  }
  const previous = getSessionUser() || {};
  sessionStorage.setItem("gymfitUser", JSON.stringify({
    ...previous,
    user_id: user.user_id,
    account_type: user.account_type,
    name: user.name,
    email: user.email,
    login_provider: user.login_provider,
    exercise_level: user.exercise_level,
    goals: user.goals,
    weekly_workout_days: user.weekly_workout_days,
    has_active_trainer: user.has_active_trainer === true,
    pending_pt_request_count: Math.max(
      0,
      Number(user.pending_pt_request_count) || 0
    ),
    gym_id: user.gym_id,
    gym_name: user.gym_name,
    gym_road_address: user.gym_road_address,
    gym_provider: user.gym_provider,
    gym_external_place_id: user.gym_external_place_id,
  }));
}

async function submitProfile(event) {
  event.preventDefault();
  if (isSaving || !currentUser) return;
  const name = profileNameInput.value.trim();
  if (!name) { profileNameInput.setCustomValidity("이름을 입력해 주세요."); profileNameInput.reportValidity(); return; }
  profileNameInput.setCustomValidity("");
  const selectedGoals = [...profileEditForm.querySelectorAll('input[name="goals"]:checked')].map((input) => input.value);
  if (selectedGoals.length === 0) { profileGoalError.hidden = false; return; }
  if (!profileWeeklySelect.value) {
    profileWeeklySelect.setCustomValidity("주간 운동 횟수를 선택해 주세요.");
    profileWeeklySelect.reportValidity();
    return;
  }
  profileWeeklySelect.setCustomValidity("");
  profileGoalError.hidden = true;
  const payload = {
    name,
    exercise_level: profileLevelSelect.value,
    goals: selectedGoals,
    weekly_workout_days: Number(profileWeeklySelect.value),
  };
  isSaving = true;
  profileSaveButton.disabled = true;
  profileSaveButton.textContent = "저장 중...";
  profileFormMessage.hidden = true;
  try {
    currentUser = await requestJson(`/api/users/${currentUser.user_id}`, {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    updateSessionUser(currentUser);
    renderProfile();
    closeEditSheetAfterSave();
    showToast("프로필을 저장했습니다.");
  } catch (error) {
    profileFormMessage.textContent = getErrorMessage(error, "프로필을 저장하지 못했습니다.");
    profileFormMessage.className = "form-message";
    profileFormMessage.hidden = false;
  } finally {
    isSaving = false;
    profileSaveButton.disabled = false;
    profileSaveButton.textContent = "저장하기";
  }
}

function closeEditSheetAfterSave() {
  window.GymfitDropdown?.closeAll();
  profileEditOverlay.hidden = true;
  profileEditForm.reset();
  document.body.classList.remove("modal-open");
}

function openLogoutDialog() { logoutOverlay.hidden = false; document.body.classList.add("modal-open"); }
function closeLogoutDialog() { logoutOverlay.hidden = true; document.body.classList.remove("modal-open"); }
function openPasswordChangeSheet() {
  if (!currentUser) return;
  passwordChangeForm.reset();
  passwordChangeMessage.hidden = true;
  const isLocal = currentUser.login_provider === "LOCAL";
  document.querySelector("#passwordUnavailable").hidden = isLocal;
  passwordChangeForm.hidden = !isLocal;
  passwordChangeOverlay.hidden = false;
  document.body.classList.add("modal-open");
  if (isLocal) document.querySelector("#currentPassword").focus();
}
function closePasswordChangeSheet() {
  if (isAccountSubmitting) return;
  passwordChangeOverlay.hidden = true;
  passwordChangeForm.reset();
  passwordChangeMessage.hidden = true;
  document.body.classList.remove("modal-open");
}
async function submitPasswordChange(event) {
  event.preventDefault();
  if (isAccountSubmitting || currentUser?.login_provider !== "LOCAL") return;
  const currentPassword = document.querySelector("#currentPassword").value;
  const newPassword = document.querySelector("#newPassword").value;
  const newPasswordConfirm = document.querySelector("#newPasswordConfirm").value;
  if (newPassword !== newPasswordConfirm) {
    passwordChangeMessage.textContent = "새 비밀번호가 일치하지 않습니다.";
    passwordChangeMessage.hidden = false;
    document.querySelector("#newPasswordConfirm").focus();
    return;
  }
  if (currentPassword === newPassword) {
    passwordChangeMessage.textContent = "새 비밀번호는 현재 비밀번호와 달라야 합니다.";
    passwordChangeMessage.hidden = false;
    document.querySelector("#newPassword").focus();
    return;
  }
  if (!passwordChangeForm.reportValidity()) return;
  isAccountSubmitting = true;
  passwordChangeButton.disabled = true;
  passwordChangeButton.textContent = "변경 중...";
  passwordChangeMessage.hidden = true;
  try {
    await requestJson("/api/users/me/password", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": String(currentUser.user_id),
      },
      body: JSON.stringify({
        current_password: currentPassword,
        new_password: newPassword,
        new_password_confirm: newPasswordConfirm,
      }),
    });
    isAccountSubmitting = false;
    closePasswordChangeSheet();
    showToast("비밀번호를 변경했습니다.");
  } catch (error) {
    passwordChangeMessage.textContent = getErrorMessage(error, "비밀번호를 변경하지 못했습니다.");
    passwordChangeMessage.hidden = false;
  } finally {
    isAccountSubmitting = false;
    passwordChangeButton.disabled = false;
    passwordChangeButton.textContent = "비밀번호 변경";
  }
}
function openWithdrawSheet() {
  if (!currentUser) return;
  withdrawForm.reset();
  withdrawMessage.hidden = true;
  const needsPassword = currentUser.login_provider === "LOCAL";
  document.querySelector("#withdrawPasswordField").hidden = !needsPassword;
  document.querySelector("#withdrawPassword").required = needsPassword;
  withdrawOverlay.hidden = false;
  document.body.classList.add("modal-open");
  (needsPassword
    ? document.querySelector("#withdrawPassword")
    : document.querySelector("#withdrawPhrase")).focus();
}
function closeWithdrawSheet() {
  if (isAccountSubmitting) return;
  withdrawOverlay.hidden = true;
  withdrawForm.reset();
  withdrawMessage.hidden = true;
  document.body.classList.remove("modal-open");
}
async function submitWithdrawal(event) {
  event.preventDefault();
  if (isAccountSubmitting || !currentUser) return;
  const phrase = document.querySelector("#withdrawPhrase").value.trim();
  if (phrase !== "회원 탈퇴") {
    withdrawMessage.textContent = "확인 문구에 '회원 탈퇴'를 정확히 입력해 주세요.";
    withdrawMessage.hidden = false;
    document.querySelector("#withdrawPhrase").focus();
    return;
  }
  if (!withdrawForm.reportValidity()) return;
  isAccountSubmitting = true;
  withdrawButton.disabled = true;
  withdrawButton.textContent = "탈퇴 처리 중...";
  withdrawMessage.hidden = true;
  try {
    await requestJson("/api/users/me/withdraw", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-User-Id": String(currentUser.user_id),
      },
      body: JSON.stringify({
        confirmation_phrase: phrase,
        current_password: currentUser.login_provider === "LOCAL"
          ? document.querySelector("#withdrawPassword").value
          : null,
      }),
    });
    window.speechSynthesis?.cancel();
    sessionStorage.clear();
    sessionStorage.setItem("gymfitAccountWithdrawn", "1");
    window.history.replaceState(null, "", "/login");
    window.location.replace("/login");
  } catch (error) {
    withdrawMessage.textContent = getErrorMessage(error, "회원 탈퇴를 처리하지 못했습니다.");
    withdrawMessage.hidden = false;
    isAccountSubmitting = false;
    withdrawButton.disabled = false;
    withdrawButton.textContent = "회원 탈퇴";
  }
}
function openGymSheet() {
  if (!currentUser) return;
  document.querySelector("#gymEditOverlay").hidden = false;
  document.body.classList.add("modal-open");
}
function closeGymSheet() {
  window.GymfitDropdown?.closeAll();
  document.querySelector("#gymEditOverlay").hidden = true;
  document.body.classList.remove("modal-open");
}
async function saveSelectedGym() {
  const selected = gymSearchController.getValue();
  const button = document.querySelector("#gymSaveButton");
  const message = document.querySelector("#gymSaveMessage");
  if (!selected) { message.textContent = "검색 결과에서 헬스장을 선택해 주세요."; message.hidden = false; return; }
  button.disabled = true;
  try {
    await requestJson("/api/users/me/gym", {
      method: "PATCH",
      headers: { "Content-Type": "application/json", "X-User-Id": String(currentUser.user_id) },
      body: JSON.stringify(selected),
    });
    closeGymSheet();
    await loadProfile();
    showToast("헬스장을 변경했습니다.");
  } catch (error) {
    message.textContent = getErrorMessage(error, "헬스장 변경에 실패했습니다.");
    message.hidden = false;
  } finally { button.disabled = false; }
}
function logout() {
  ["gymfitUser", "gymfitCoachingPlan", "gymfitCoachingRestSeconds", "gymfitFreeCoachingSets", "gymfitCoachingVoiceEnabled"].forEach((key) => sessionStorage.removeItem(key));
  window.speechSynthesis?.cancel();
  window.location.replace("/login");
}

profileRetryButton.addEventListener("click", loadProfile);
document.querySelector("#profileEditShortcut").addEventListener("click", openEditSheet);
document.querySelector("#fitnessProfileAction").addEventListener("click", openEditSheet);
document.querySelector("#profileEditClose").addEventListener("click", closeEditSheet);
document.querySelector("#profileEditBackdrop").addEventListener("click", closeEditSheet);
profileEditForm.addEventListener("submit", submitProfile);
document.querySelector("#logoutCancelButton").addEventListener("click", closeLogoutDialog);
document.querySelector("#logoutConfirmButton").addEventListener("click", logout);
document.querySelector("#passwordChangeClose").addEventListener("click", closePasswordChangeSheet);
document.querySelector("#passwordChangeBackdrop").addEventListener("click", closePasswordChangeSheet);
passwordChangeForm.addEventListener("submit", submitPasswordChange);
document.querySelector("#withdrawClose").addEventListener("click", closeWithdrawSheet);
document.querySelector("#withdrawBackdrop").addEventListener("click", closeWithdrawSheet);
withdrawForm.addEventListener("submit", submitWithdrawal);
document.querySelector("#openGymSheetButton").addEventListener("click", openGymSheet);
document.querySelector("#gymEditClose").addEventListener("click", closeGymSheet);
document.querySelector("#gymEditBackdrop").addEventListener("click", closeGymSheet);
document.querySelector("#gymSaveButton").addEventListener("click", saveSelectedGym);
window.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!logoutOverlay.hidden) closeLogoutDialog();
  else if (!withdrawOverlay.hidden) closeWithdrawSheet();
  else if (!passwordChangeOverlay.hidden) closePasswordChangeSheet();
  else if (!profileEditOverlay.hidden) closeEditSheet();
});

loadProfile();
