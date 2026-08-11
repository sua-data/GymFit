const profileForm = document.querySelector(
  "#profileForm"
);

const backButton = document.querySelector(
  "#backButton"
);

const skipButton = document.querySelector(
  "#skipButton"
);

const completeButton = document.querySelector(
  "#completeButton"
);

const birthDateInput = document.querySelector(
  "#birthDate"
);

const heightInput = document.querySelector(
  "#height"
);

const weightInput = document.querySelector(
  "#weight"
);

const formMessage = document.querySelector(
  "#formMessage"
);

const selectButtons =
  document.querySelectorAll(
    "[data-group]"
  );

const googleAgreementArea =
  document.querySelector(
    "#googleAgreementArea"
  );

const googleTerms =
  document.querySelector(
    "#googleTerms"
  );

const googlePrivacy =
  document.querySelector(
    "#googlePrivacy"
  );

const googleMarketing =
  document.querySelector(
    "#googleMarketing"
  );

const pageTitle =
  document.querySelector(
    "#pageTitle"
  );

const pageDescription =
  document.querySelector(
    "#pageDescription"
  );

const googleAgreeAll =
  document.querySelector(
    "#googleAgreeAll"
  );

const googleAgreementCheckboxes =
  document.querySelectorAll(
    ".google-agreement-checkbox"
  );

/* =========================
   가입 방식 확인
========================= */

const signupProvider =
  sessionStorage.getItem(
    "signupProvider"
  );

const isGoogleSignup =
  signupProvider === "GOOGLE";


let selectedGender = null;
let selectedGoal = null;
let selectedLevel = null;
let selectedWeeklyDays = null;
const birthDateController = typeof window.setupBirthDateInput === "function"
  ? window.setupBirthDateInput({
      textInputId: "birthDate",
      pickerId: "birthDatePicker",
      hiddenInputId: "birthDateValue",
      errorId: "birthDateError",
      calendarButtonId: "birthCalendarButton",
    })
  : null;


/* =========================
   Google 가입 화면 처리
========================= */

if (isGoogleSignup) {
  if (pageTitle) {
    pageTitle.textContent =
      "추가 정보 입력";
  }

  if (pageDescription) {
    pageDescription.textContent =
      "운동 정보를 설정해 주세요.";
  }

  if (googleAgreementArea) {
    googleAgreementArea.hidden = false;
  }
}


/* =========================
   이전 단계
========================= */

backButton.addEventListener(
  "click",
  () => {
    if (isGoogleSignup) {
      window.location.href =
        "/signup/type";

      return;
    }

    window.location.href =
      "/signup";
  }
);


/* =========================
   선택 버튼
========================= */

selectButtons.forEach(
  (button) => {
    button.addEventListener(
      "click",
      () => {
        const group =
          button.dataset.group;

        const value =
          button.dataset.value;

        const groupButtons =
          document.querySelectorAll(
            `[data-group="${group}"]`
          );

        groupButtons.forEach(
          (item) => {
            item.classList.remove(
              "active"
            );
            item.setAttribute("aria-pressed", "false");
          }
        );

        button.classList.add(
          "active"
        );
        button.setAttribute("aria-pressed", "true");

        if (group === "gender") {
          selectedGender = value;
        }

        if (group === "goal") {
          selectedGoal = value;
        }

        if (group === "level") {
          selectedLevel = value;
        }

        if (group === "weekly") {
          selectedWeeklyDays = Number(value);
        }

        clearMessage();
      }
    );
  }
);


/* =========================
   생년월일
========================= */

/* =========================
   메시지
========================= */

function showMessage(
  message,
  inputElement = null
) {
  window.gymfitAuthValidation?.show(
    inputElement,
    message,
    formMessage
  );

  if (inputElement) {
    inputElement.setAttribute("aria-invalid", "true");
    inputElement.focus();
  }
}


function clearMessage() {
  formMessage.textContent = "";
  window.gymfitAuthValidation?.clearAll(profileForm);
}


heightInput.addEventListener(
  "input",
  clearMessage
);

weightInput.addEventListener(
  "input",
  clearMessage
);

googleTerms?.addEventListener(
  "change",
  clearMessage
);

googlePrivacy?.addEventListener(
  "change",
  clearMessage
);

googleMarketing?.addEventListener(
  "change",
  clearMessage
);


/* =========================
   유효성 검사
========================= */

function validateOptionalBodyInfo() {
  const height =
    heightInput.value
      ? Number(heightInput.value)
      : null;

  const weight =
    weightInput.value
      ? Number(weightInput.value)
      : null;

  if (
    height !== null
    && (
      height < 100
      || height > 250
    )
  ) {
    showMessage(
      "키는 100cm에서 250cm 사이로 입력해 주세요.",
      heightInput
    );

    return false;
  }

  if (
    weight !== null
    && (
      weight < 30
      || weight > 300
    )
  ) {
    showMessage(
      "몸무게는 30kg에서 300kg 사이로 입력해 주세요.",
      weightInput
    );

    return false;
  }

  return true;
}


/* =========================
   일반 가입 Step1 정보
========================= */

function getStep1Data() {
  const savedData =
    sessionStorage.getItem(
      "gymfitSignupData"
    );

  if (!savedData) {
    return null;
  }

  try {
    return JSON.parse(
      savedData
    );
  } catch (error) {
    console.error(
      "회원가입 1단계 데이터 파싱 실패:",
      error
    );

    return null;
  }
}


/* =========================
   Google 가입 정보
========================= */

function getGoogleSignupData() {
  const savedData =
    sessionStorage.getItem(
      "googleSignup"
    );

  if (!savedData) {
    return null;
  }

  try {
    return JSON.parse(
      savedData
    );
  } catch (error) {
    console.error(
      "Google 가입 데이터 파싱 실패:",
      error
    );

    return null;
  }
}


/* =========================
   약관 정보 생성
========================= */

function getAgreements() {
  if (isGoogleSignup) {
    return {
      terms:
        googleTerms?.checked === true,

      privacy:
        googlePrivacy?.checked === true,

      marketing:
        googleMarketing?.checked === true,

      trainer_policy: false,
    };
  }

  const step1Data =
    getStep1Data();

  return {
    terms:
      step1Data
        ?.agreements
        ?.terms === true,

    privacy:
      step1Data
        ?.agreements
        ?.privacy === true,

    marketing:
      step1Data
        ?.agreements
        ?.marketing === true,

    trainer_policy: false,
  };
}


/* =========================
   Google 필수 약관 검사
========================= */

function validateGoogleAgreements() {
  if (!isGoogleSignup) {
    return true;
  }

  if (!googleTerms?.checked) {
    showMessage(
      "이용약관에 동의해 주세요.",
      googleTerms
    );

    return false;
  }

  if (!googlePrivacy?.checked) {
    showMessage(
      "개인정보 처리방침에 동의해 주세요.",
      googlePrivacy
    );

    return false;
  }

  return true;
}


/* =========================
   API 오류 메시지
========================= */

function getErrorMessage(
  data,
  fallbackMessage
) {
  if (
    typeof data?.detail
    === "string"
  ) {
    return data.detail;
  }

  if (
    Array.isArray(
      data?.detail
    )
  ) {
    return data.detail
      .map(
        (item) => item.msg
      )
      .join("\n");
  }

  return fallbackMessage;
}


/* =========================
   응답 JSON 안전 처리
========================= */

async function readJsonResponse(
  response
) {
  try {
    return await response.json();
  } catch {
    return {};
  }
}


/* =========================
   일반 회원가입 API
========================= */

async function submitLocalMemberSignup(
  signupData
) {
  const response = await fetch(
    "/api/auth/signup/member",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify(
        signupData
      ),
    }
  );

  const data =
    await readJsonResponse(
      response
    );

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "회원가입에 실패했습니다."
      )
    );
  }

  return data;
}


/* =========================
   Google 회원가입 API
========================= */

async function submitGoogleMemberSignup(
  signupData
) {
  const response = await fetch(
    "/api/auth/google/signup/member",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify(
        signupData
      ),
    }
  );

  const data =
    await readJsonResponse(
      response
    );

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "Google 회원가입에 실패했습니다."
      )
    );
  }

  return data;
}


/* =========================
   입력 데이터 생성
========================= */

function createProfileData({
  skipProfile = false,
} = {}) {
  return {
    gender:
      skipProfile
        ? "NONE"
        : selectedGender,

    birth_date:
      skipProfile
        ? null
        : birthDateController?.getValue() || null,

    height_cm:
      skipProfile
        ? null
        : (
          heightInput.value
            ? Number(
                heightInput.value
              )
            : null
        ),

    weight_kg:
      skipProfile
        ? null
        : (
          weightInput.value
            ? Number(
                weightInput.value
              )
            : null
        ),

    exercise_level:
      skipProfile
        ? null
        : selectedLevel,

    weekly_workout_days:
      skipProfile ? null : selectedWeeklyDays,

    goals:
      skipProfile
        ? []
        : [selectedGoal],

    agreements:
      getAgreements(),
  };
}


/* =========================
   회원가입 요청 데이터 생성
========================= */

function createSignupData({
  skipProfile = false,
} = {}) {
  const profileData =
    createProfileData({
      skipProfile,
    });

  if (isGoogleSignup) {
    const googleSignup =
      getGoogleSignupData();

    if (
      !googleSignup
      || !googleSignup.signup_token
    ) {
      throw new Error(
        "Google 가입 정보가 없습니다. 다시 로그인해 주세요."
      );
    }

    return {
      signup_token:
        googleSignup.signup_token,

      ...profileData,
    };
  }

  const step1Data =
    getStep1Data();

  if (!step1Data) {
    throw new Error(
      "회원가입 1단계 정보가 없습니다. 처음부터 다시 진행해 주세요."
    );
  }

  return {
    name: step1Data.name,
    email: step1Data.email,
    password: step1Data.password,

    ...profileData,
  };
}


/* =========================
   회원가입 API 분기
========================= */

async function submitSignup(
  signupData
) {
  if (isGoogleSignup) {
    return await submitGoogleMemberSignup(
      signupData
    );
  }

  return await submitLocalMemberSignup(
    signupData
  );
}


/* =========================
   세션 정리
========================= */

function clearSignupSession() {
  sessionStorage.removeItem(
    "gymfitSignupData"
  );

  sessionStorage.removeItem(
    "gymfitAccountType"
  );

  sessionStorage.removeItem(
    "signupAccountType"
  );

  sessionStorage.removeItem(
    "googleSignup"
  );

  sessionStorage.removeItem(
    "signupProvider"
  );
}


/* =========================
   가입 완료 처리
========================= */

function handleSignupSuccess(
  result
) {
  const googleSignup =
    getGoogleSignupData();

  clearSignupSession();

  if (isGoogleSignup) {
    sessionStorage.setItem(
      "gymfitUser",
      JSON.stringify({
        user_id:
          result.user_id,

        account_type:
          result.account_type,

        name:
          googleSignup?.name || "",

        email:
          result.email,
      })
    );

    alert(
      "가입이 완료되었습니다."
    );

    window.location.href =
      "/dashboard";

    return;
  }

  alert(
    "회원가입이 완료되었습니다."
  );

  window.location.href =
    "/login";
}


/* =========================
   가입 완료
========================= */

profileForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    clearMessage();

    const birthDate = birthDateController?.getValue() || "";

    if (!selectedGender) {
      showMessage(
        "성별을 선택해 주세요."
      );

      return;
    }

    if (!birthDate) {
      showMessage(
        birthDateController?.validate() || "생년월일을 입력해 주세요.",
        birthDateInput
      );

      return;
    }

    if (!selectedGoal) {
      showMessage(
        "운동 목표를 선택해 주세요."
      );

      return;
    }

    if (!selectedLevel) {
      showMessage(
        "운동 수준을 선택해 주세요."
      );

      return;
    }

    if (!selectedWeeklyDays) {
      showMessage("주간 운동 횟수를 선택해 주세요.");
      return;
    }

    if (
      !validateOptionalBodyInfo()
    ) {
      return;
    }

    if (
      !validateGoogleAgreements()
    ) {
      return;
    }

    completeButton.disabled = true;

    completeButton.textContent =
      "가입 처리 중...";

    skipButton.disabled = true;

    try {
      const signupData =
        createSignupData();

      const result =
        await submitSignup(
          signupData
        );

      handleSignupSuccess(
        result
      );

    } catch (error) {
      console.error(
        "회원가입 실패:",
        error
      );

      showMessage(
        error.message
        || "회원가입 중 오류가 발생했습니다."
      );

      completeButton.disabled =
        false;

      completeButton.textContent =
        "운동 설정 완료";

      skipButton.disabled =
        false;
    }
  }
);


/* =========================
   나중에 설정
========================= */

skipButton.addEventListener(
  "click",
  async () => {
    clearMessage();

    if (
      !validateGoogleAgreements()
    ) {
      return;
    }

    skipButton.disabled = true;

    skipButton.textContent =
      "가입 처리 중...";

    completeButton.disabled = true;

    try {
      const signupData =
        createSignupData({
          skipProfile: true,
        });

      const result =
        await submitSignup(
          signupData
        );

      handleSignupSuccess(
        result
      );

    } catch (error) {
      console.error(
        "회원가입 실패:",
        error
      );

      showMessage(
        error.message
        || "회원가입 중 오류가 발생했습니다."
      );

      skipButton.disabled =
        false;

      skipButton.textContent =
        "나중에 설정";

      completeButton.disabled =
        false;
    }
  }
);

/* =========================
   Google 약관 전체 동의
========================= */

googleAgreeAll?.addEventListener(
  "change",
  () => {
    googleAgreementCheckboxes.forEach(
      (checkbox) => {
        checkbox.checked =
          googleAgreeAll.checked;
      }
    );

    clearMessage();
  }
);

googleAgreementCheckboxes.forEach(
  (checkbox) => {
    checkbox.addEventListener(
      "change",
      () => {
        googleAgreeAll.checked =
          Array.from(
            googleAgreementCheckboxes
          ).every(
            (item) => item.checked
          );

        clearMessage();
      }
    );
  }
);
