const GOAL_LABELS = {
  WEIGHT_LOSS: "체중 감량",
  MUSCLE_GAIN: "근력 증가",
  BODY_SHAPE: "체형 관리",
  HEALTH: "건강 유지",
};
const LEVEL_LABELS = { BEGINNER: "초급", INTERMEDIATE: "중급", ADVANCED: "고급" };

function installExtendedProfileUI() {
  document.querySelector("#profileLevel")?.closest("div")?.insertAdjacentHTML("afterend", '<div id="profileWeeklyRow"><dt>주간 운동 목표</dt><dd id="profileWeekly">미설정</dd></div>');
  document.querySelector("#profileLevelSelect")?.closest("label")?.insertAdjacentHTML("afterend", '<label>주간 운동 횟수<select id="profileWeeklySelect" required><option value="">선택</option><option value="1">주 1회</option><option value="2">주 2회</option><option value="3">주 3회</option><option value="4">주 4회</option><option value="5">주 5회</option><option value="6">주 6회</option><option value="7">매일</option></select></label>');
  document.querySelector(".profile-info-card")?.insertAdjacentHTML("afterend", '<section class="profile-info-card gym-card"><div class="section-heading"><span>MY GYM</span><h2>내 헬스장</h2></div><div class="gym-current"><div><strong id="currentGymName">소속 헬스장 없음</strong><p id="currentGymAddress">헬스장을 연결하면 이곳에 표시됩니다.</p></div><button type="button" id="openGymSheetButton">변경</button></div><button type="button" class="disconnect-gym-button" id="disconnectGymButton" hidden>연결 해제</button><p class="gym-policy-message" id="gymPolicyMessage" hidden>승인 완료 후에는 소속 헬스장을 직접 변경할 수 없습니다.</p></section>');
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

let currentUser = null;
let isSaving = false;
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
  if (user?.account_type === "TRAINER") return "트레이너";
  return getSessionUser()?.has_active_trainer ? "PT 회원" : "일반 회원";
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
  button.className = `menu-item${danger ? " danger" : ""}`;
  button.innerHTML = `<span>${label}</span>${comingSoon ? '<span class="coming">준비 중</span>' : '<span class="arrow">›</span>'}`;
  button.addEventListener("click", action);
  return button;
}

function comingSoon() { showToast("준비 중인 기능입니다."); }

function renderMenus() {
  const commonMenuList = document.querySelector("#commonMenuList");
  commonMenuList.replaceChildren(
    createMenuItem("프로필 수정", openEditSheet),
    createMenuItem("알림 설정", comingSoon, true),
    createMenuItem("비밀번호 변경", comingSoon, true),
    createMenuItem("로그아웃", openLogoutDialog, false, true),
    createMenuItem("회원 탈퇴", comingSoon, true, true),
  );
}

function renderProfile() {
  const name = getDisplayName(currentUser);
  const goals = (currentUser.goals || []).map((goal) => goal.goal_name || GOAL_LABELS[goal.goal_code]).filter(Boolean);
  document.querySelector("#profileAvatar").textContent = Array.from(name)[0]?.toUpperCase() || "G";
  document.querySelector("#profileName").textContent = name;
  document.querySelector("#profileEmail").textContent = currentUser.email || "이메일 정보 없음";
  document.querySelector("#profileRole").textContent = getRoleLabel(currentUser);
  document.querySelector("#profileGoals").textContent = goals.length ? goals.join(", ") : "설정 없음";
  document.querySelector("#profileLevel").textContent = LEVEL_LABELS[currentUser.exercise_level] || "설정 없음";
  document.querySelector("#profileWeekly").textContent = currentUser.weekly_workout_days ? (currentUser.weekly_workout_days === 7 ? "매일" : `주 ${currentUser.weekly_workout_days}회`) : "미설정";
  document.querySelector("#profileAccountType").textContent = getRoleLabel(currentUser);
  const gymRow = document.querySelector("#profileGymRow");
  gymRow.hidden = currentUser.account_type !== "TRAINER";
  document.querySelector("#profileGym").textContent = currentUser.gym_name || "등록 없음";
  document.querySelector("#currentGymName").textContent = currentUser.gym_name || "소속 헬스장 없음";
  document.querySelector("#currentGymAddress").textContent = currentUser.gym_road_address || (currentUser.gym_name ? "기존 문자열 헬스장 정보" : "헬스장을 연결하면 이곳에 표시됩니다.");
  const gymLocked = currentUser.account_type === "TRAINER" && currentUser.trainer_approval_status === "APPROVED";
  document.querySelector("#openGymSheetButton").disabled = gymLocked;
  document.querySelector("#disconnectGymButton").hidden = !currentUser.gym_id || gymLocked;
  document.querySelector("#gymPolicyMessage").hidden = !gymLocked;
  const dateValue = currentUser.last_login_at || currentUser.created_at;
  document.querySelector("#profileDateLabel").textContent = currentUser.last_login_at ? "마지막 로그인" : "가입일";
  document.querySelector("#profileDate").textContent = formatDate(dateValue);
  renderMenus();
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
  document.querySelector("#memberEditFields").hidden = currentUser.account_type === "TRAINER";
  renderGoalChoices();
  profileGoalError.hidden = true;
  profileFormMessage.hidden = true;
  profileEditOverlay.hidden = false;
  document.body.classList.add("modal-open");
  profileNameInput.focus();
}

function closeEditSheet() {
  if (isSaving) return;
  profileEditOverlay.hidden = true;
  profileEditForm.reset();
  profileFormMessage.hidden = true;
  document.body.classList.remove("modal-open");
}

function updateSessionUser(user) {
  const previous = getSessionUser() || {};
  sessionStorage.setItem("gymfitUser", JSON.stringify({
    ...previous,
    user_id: user.user_id,
    account_type: user.account_type,
    name: user.name,
    email: user.email,
    exercise_level: user.exercise_level,
    goals: user.goals,
    weekly_workout_days: user.weekly_workout_days,
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
  if (currentUser.account_type !== "TRAINER" && selectedGoals.length === 0) { profileGoalError.hidden = false; return; }
  if (currentUser.account_type !== "TRAINER" && !profileWeeklySelect.value) {
    profileWeeklySelect.setCustomValidity("주간 운동 횟수를 선택해 주세요.");
    profileWeeklySelect.reportValidity();
    return;
  }
  profileWeeklySelect.setCustomValidity("");
  profileGoalError.hidden = true;
  const payload = { name };
  if (currentUser.account_type !== "TRAINER") {
    payload.exercise_level = profileLevelSelect.value;
    payload.goals = selectedGoals;
    payload.weekly_workout_days = Number(profileWeeklySelect.value);
  }
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
  profileEditOverlay.hidden = true;
  profileEditForm.reset();
  document.body.classList.remove("modal-open");
}

function openLogoutDialog() { logoutOverlay.hidden = false; document.body.classList.add("modal-open"); }
function closeLogoutDialog() { logoutOverlay.hidden = true; document.body.classList.remove("modal-open"); }
function openGymSheet() {
  if (!currentUser || (currentUser.account_type === "TRAINER" && currentUser.trainer_approval_status === "APPROVED")) return;
  document.querySelector("#gymEditOverlay").hidden = false;
  document.body.classList.add("modal-open");
}
function closeGymSheet() {
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
    const gym = await requestJson("/api/gyms/select", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(selected) });
    currentUser = await requestJson(`/api/users/${currentUser.user_id}/gym`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ gym_id: gym.gym_id }) });
    updateSessionUser(currentUser);
    renderProfile();
    closeGymSheet();
    showToast("헬스장을 변경했습니다.");
  } catch (error) {
    message.textContent = getErrorMessage(error, "헬스장 변경에 실패했습니다.");
    message.hidden = false;
  } finally { button.disabled = false; }
}
async function disconnectGym() {
  if (!currentUser?.gym_id || !window.confirm("헬스장 연결을 해제하시겠어요?")) return;
  try {
    currentUser = await requestJson(`/api/users/${currentUser.user_id}/gym`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ gym_id: null }) });
    updateSessionUser(currentUser);
    renderProfile();
    showToast("헬스장 연결을 해제했습니다.");
  } catch (error) { showToast(getErrorMessage(error, "연결 해제에 실패했습니다.")); }
}
function logout() {
  ["gymfitUser", "gymfitCoachingPlan", "gymfitCoachingRestSeconds", "gymfitFreeCoachingSets", "gymfitCoachingVoiceEnabled"].forEach((key) => sessionStorage.removeItem(key));
  window.speechSynthesis?.cancel();
  window.location.replace("/login");
}

profileRetryButton.addEventListener("click", loadProfile);
document.querySelector("#profileEditShortcut").addEventListener("click", openEditSheet);
document.querySelector("#profileEditClose").addEventListener("click", closeEditSheet);
document.querySelector("#profileEditBackdrop").addEventListener("click", closeEditSheet);
profileEditForm.addEventListener("submit", submitProfile);
document.querySelector("#logoutCancelButton").addEventListener("click", closeLogoutDialog);
document.querySelector("#logoutConfirmButton").addEventListener("click", logout);
document.querySelector("#openGymSheetButton").addEventListener("click", openGymSheet);
document.querySelector("#gymEditClose").addEventListener("click", closeGymSheet);
document.querySelector("#gymEditBackdrop").addEventListener("click", closeGymSheet);
document.querySelector("#gymSaveButton").addEventListener("click", saveSelectedGym);
document.querySelector("#disconnectGymButton").addEventListener("click", disconnectGym);
window.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!logoutOverlay.hidden) closeLogoutDialog();
  else if (!profileEditOverlay.hidden) closeEditSheet();
});

loadProfile();
