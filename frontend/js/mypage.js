const GOAL_LABELS = {
  WEIGHT_LOSS: "체중 감량",
  MUSCLE_GAIN: "근력 증가",
  BODY_SHAPE: "체형 관리",
  HEALTH: "건강 유지",
};
const LEVEL_LABELS = { BEGINNER: "초급", INTERMEDIATE: "중급", ADVANCED: "고급" };

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
const logoutOverlay = document.querySelector("#logoutOverlay");
const mypageToast = document.querySelector("#mypageToast");

let currentUser = null;
let isSaving = false;
let toastTimer = null;

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
  const roleMenuSection = document.querySelector("#roleMenuSection");
  const roleMenuList = document.querySelector("#roleMenuList");
  const roleMenuTitle = document.querySelector("#roleMenuTitle");
  commonMenuList.replaceChildren(
    createMenuItem("프로필 수정", openEditSheet),
    createMenuItem("운동 목표·수준 변경", currentUser.account_type === "TRAINER" ? comingSoon : openEditSheet, currentUser.account_type === "TRAINER"),
    createMenuItem("내 헬스장", comingSoon, true),
    createMenuItem("보유 머신 관리", comingSoon, true),
    createMenuItem("알림 설정", comingSoon, true),
    createMenuItem("앱 정보", comingSoon, true),
    createMenuItem("로그아웃", openLogoutDialog, false, true),
  );

  const isTrainer = currentUser.account_type === "TRAINER";
  const hasTrainer = Boolean(getSessionUser()?.has_active_trainer);
  roleMenuSection.hidden = !isTrainer && !hasTrainer;
  if (isTrainer) {
    roleMenuTitle.textContent = "트레이너 메뉴";
    roleMenuList.replaceChildren(
      createMenuItem("담당 회원 관리", comingSoon, true),
      createMenuItem("회원별 운동 계획·PT 숙제 관리", comingSoon, true),
    );
  } else if (hasTrainer) {
    roleMenuTitle.textContent = "PT 회원 메뉴";
    roleMenuList.replaceChildren(
      createMenuItem("PT 숙제", comingSoon, true),
      createMenuItem("담당 트레이너·PT 정보", comingSoon, true),
    );
  }
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
  document.querySelector("#profileAccountType").textContent = getRoleLabel(currentUser);
  const gymRow = document.querySelector("#profileGymRow");
  gymRow.hidden = currentUser.account_type !== "TRAINER";
  document.querySelector("#profileGym").textContent = currentUser.gym_name || "등록 없음";
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
  profileGoalError.hidden = true;
  const payload = { name };
  if (currentUser.account_type !== "TRAINER") {
    payload.exercise_level = profileLevelSelect.value;
    payload.goals = selectedGoals;
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
window.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  if (!logoutOverlay.hidden) closeLogoutDialog();
  else if (!profileEditOverlay.hidden) closeEditSheet();
});

loadProfile();
