const trainerProfileForm =
  document.querySelector(
    "#trainerProfileForm"
  );

const backButton =
  document.querySelector(
    "#backButton"
  );

const skipButton =
  document.querySelector(
    "#skipButton"
  );

const completeButton =
  document.querySelector(
    "#completeButton"
  );

const birthDateInput =
  document.querySelector(
    "#birthDate"
  );

const dateText =
  document.querySelector(
    "#dateText"
  );

const gymNameInput =
  document.querySelector(
    "#gymName"
  );

const careerYearsInput =
  document.querySelector(
    "#careerYears"
  );

const certificationInput =
  document.querySelector(
    "#certificationInput"
  );

const addCertificationButton =
  document.querySelector(
    "#addCertificationButton"
  );

const certificationList =
  document.querySelector(
    "#certificationList"
  );

const introductionInput =
  document.querySelector(
    "#introduction"
  );

const characterCount =
  document.querySelector(
    "#characterCount"
  );

const formMessage =
  document.querySelector(
    "#formMessage"
  );

const genderButtons =
  document.querySelectorAll(
    '[data-group="gender"]'
  );

const specialtyButtons =
  document.querySelectorAll(
    "[data-specialty]"
  );

const pageTitle =
  document.querySelector(
    "#pageTitle"
  );

const pageDescription =
  document.querySelector(
    "#pageDescription"
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

const googleTrainerPolicy =
  document.querySelector(
    "#googleTrainerPolicy"
  );

const googleMarketing =
  document.querySelector(
    "#googleMarketing"
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
let selectedSpecialties = [];
let certifications = [];


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
      "트레이너 정보를 설정해 주세요.";
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
      "/signup/trainer";
  }
);


/* =========================
   메시지
========================= */

function showMessage(
  message,
  inputElement = null
) {
  formMessage.textContent =
    message;

  if (inputElement) {
    inputElement.focus();
  }
}


function clearMessage() {
  formMessage.textContent = "";
}


/* =========================
   성별 선택
========================= */

genderButtons.forEach(
  (button) => {
    button.addEventListener(
      "click",
      () => {
        genderButtons.forEach(
          (item) => {
            item.classList.remove(
              "active"
            );
          }
        );

        button.classList.add(
          "active"
        );

        selectedGender =
          button.dataset.value;

        clearMessage();
      }
    );
  }
);


/* =========================
   생년월일
========================= */

function formatBirthDate(value) {
  if (!value) {
    return "생년월일을 선택하세요.";
  }

  const [
    year,
    month,
    day,
  ] = value.split("-");

  return `${year}.${month}.${day}`;
}


birthDateInput.addEventListener(
  "change",
  () => {
    const value =
      birthDateInput.value;

    dateText.textContent =
      formatBirthDate(value);

    dateText.classList.toggle(
      "has-value",
      Boolean(value)
    );

    clearMessage();
  }
);


/* =========================
   전문 분야 선택
========================= */

specialtyButtons.forEach(
  (button) => {
    button.addEventListener(
      "click",
      () => {
        const value =
          button.dataset.specialty;

        button.classList.toggle(
          "active"
        );

        if (
          button.classList.contains(
            "active"
          )
        ) {
          if (
            !selectedSpecialties.includes(
              value
            )
          ) {
            selectedSpecialties.push(
              value
            );
          }
        } else {
          selectedSpecialties =
            selectedSpecialties.filter(
              (item) =>
                item !== value
            );
        }

        clearMessage();
      }
    );
  }
);


/* =========================
   자격증 목록
========================= */

function renderCertifications() {
  certificationList.innerHTML = "";

  certifications.forEach(
    (
      certification,
      index
    ) => {
      const item =
        document.createElement(
          "div"
        );

      item.className =
        "certification-item";

      const nameElement =
        document.createElement(
          "span"
        );

      nameElement.textContent =
        certification;

      const removeButton =
        document.createElement(
          "button"
        );

      removeButton.type = "button";

      removeButton.className =
        "remove-certification-button";

      removeButton.dataset.index =
        String(index);

      removeButton.textContent =
        "삭제";

      item.appendChild(
        nameElement
      );

      item.appendChild(
        removeButton
      );

      certificationList.appendChild(
        item
      );
    }
  );
}


function addCertification() {
  const value =
    certificationInput
      .value
      .trim();

  if (!value) {
    showMessage(
      "추가할 자격증명을 입력해 주세요.",
      certificationInput
    );

    return;
  }

  const alreadyExists =
    certifications.some(
      (item) =>
        item.toLowerCase()
        === value.toLowerCase()
    );

  if (alreadyExists) {
    showMessage(
      "이미 추가된 자격증입니다.",
      certificationInput
    );

    return;
  }

  certifications.push(
    value
  );

  certificationInput.value =
    "";

  renderCertifications();
  clearMessage();

  certificationInput.focus();
}


addCertificationButton.addEventListener(
  "click",
  addCertification
);


certificationInput.addEventListener(
  "keydown",
  (event) => {
    if (event.key !== "Enter") {
      return;
    }

    event.preventDefault();

    addCertification();
  }
);


certificationInput.addEventListener(
  "input",
  clearMessage
);


certificationList.addEventListener(
  "click",
  (event) => {
    const removeButton =
      event.target.closest(
        ".remove-certification-button"
      );

    if (!removeButton) {
      return;
    }

    const index = Number(
      removeButton.dataset.index
    );

    certifications.splice(
      index,
      1
    );

    renderCertifications();
    clearMessage();
  }
);


/* =========================
   자기소개 글자 수
========================= */

introductionInput.addEventListener(
  "input",
  () => {
    const currentLength =
      introductionInput
        .value
        .length;

    characterCount.textContent =
      `${currentLength} / 300`;

    clearMessage();
  }
);


/* =========================
   입력 오류 초기화
========================= */

[
  gymNameInput,
  careerYearsInput,
].forEach(
  (input) => {
    input.addEventListener(
      "input",
      clearMessage
    );
  }
);


googleTerms?.addEventListener(
  "change",
  clearMessage
);

googlePrivacy?.addEventListener(
  "change",
  clearMessage
);

googleTrainerPolicy
  ?.addEventListener(
    "change",
    clearMessage
  );

googleMarketing?.addEventListener(
  "change",
  clearMessage
);


/* =========================
   로컬 가입 Step1 정보
========================= */

function getTrainerStep1Data() {
  const savedData =
    sessionStorage.getItem(
      "gymfitTrainerSignupData"
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
      "트레이너 회원가입 1단계 데이터 파싱 실패:",
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
   경력 검사
========================= */

function validateCareerYears() {
  const value =
    careerYearsInput
      .value
      .trim();

  if (!value) {
    showMessage(
      "경력을 입력해 주세요.",
      careerYearsInput
    );

    return false;
  }

  const careerYears =
    Number(value);

  if (
    Number.isNaN(
      careerYears
    )
    || careerYears < 0
    || careerYears > 50
  ) {
    showMessage(
      "경력은 0년에서 50년 사이로 입력해 주세요.",
      careerYearsInput
    );

    return false;
  }

  return true;
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

  if (
    !googleTrainerPolicy?.checked
  ) {
    showMessage(
      "트레이너 운영정책에 동의해 주세요.",
      googleTrainerPolicy
    );

    return false;
  }

  return true;
}


/* =========================
   약관 데이터 생성
========================= */

function getAgreements() {
  if (isGoogleSignup) {
    return {
      terms:
        googleTerms?.checked
        === true,

      privacy:
        googlePrivacy?.checked
        === true,

      marketing:
        googleMarketing?.checked
        === true,

      trainer_policy:
        googleTrainerPolicy
          ?.checked === true,
    };
  }

  const step1Data =
    getTrainerStep1Data();

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

    trainer_policy:
      step1Data
        ?.agreements
        ?.trainer_policy === true,
  };
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
        (item) =>
          item.msg
      )
      .join("\n");
  }

  return fallbackMessage;
}


/* =========================
   JSON 응답 안전 처리
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
   로컬 트레이너 가입 API
========================= */

async function submitLocalTrainerSignup(
  signupData
) {
  const response = await fetch(
    "/api/auth/signup/trainer",
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
        "트레이너 회원가입에 실패했습니다."
      )
    );
  }

  return data;
}


/* =========================
   Google 트레이너 가입 API
========================= */

async function submitGoogleTrainerSignup(
  signupData
) {
  const response = await fetch(
    "/api/auth/google/signup/trainer",
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
        "Google 트레이너 가입에 실패했습니다."
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
        : birthDateInput.value,

    gym_name:
      skipProfile
        ? null
        : (
          gymNameInput
            .value
            .trim()
          || null
        ),

    career_years:
      skipProfile
        ? null
        : (
          careerYearsInput.value
            ? Number(
                careerYearsInput.value
              )
            : null
        ),

    introduction:
      skipProfile
        ? null
        : (
          introductionInput
            .value
            .trim()
          || null
        ),

    specialties:
      skipProfile
        ? []
        : [
          ...selectedSpecialties,
        ],

    certifications:
      skipProfile
        ? []
        : [
          ...certifications,
        ],

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
    getTrainerStep1Data();

  if (!step1Data) {
    throw new Error(
      "트레이너 회원가입 1단계 정보가 없습니다. 처음부터 다시 진행해 주세요."
    );
  }

  return {
    name: step1Data.name,
    email: step1Data.email,
    password:
      step1Data.password,

    ...profileData,
  };
}


/* =========================
   가입 API 분기
========================= */

async function submitSignup(
  signupData
) {
  if (isGoogleSignup) {
    return await submitGoogleTrainerSignup(
      signupData
    );
  }

  return await submitLocalTrainerSignup(
    signupData
  );
}


/* =========================
   세션 정리
========================= */

function clearSignupSession() {
  sessionStorage.removeItem(
    "gymfitTrainerSignupData"
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
          googleSignup?.name
          || "",

        email:
          result.email,
      })
    );

    alert(
      "트레이너 가입이 완료되었습니다."
    );

    window.location.href =
      "/dashboard";

    return;
  }

  alert(
    "트레이너 회원가입이 완료되었습니다."
  );

  window.location.href =
    "/login";
}


/* =========================
   대기 중인 자격증 추가
========================= */

function addPendingCertification() {
  const pendingCertification =
    certificationInput
      .value
      .trim();

  if (!pendingCertification) {
    return;
  }

  const alreadyExists =
    certifications.some(
      (item) =>
        item.toLowerCase()
        === pendingCertification
          .toLowerCase()
    );

  if (!alreadyExists) {
    certifications.push(
      pendingCertification
    );

    renderCertifications();
  }

  certificationInput.value =
    "";
}

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
            (item) =>
              item.checked
          );

        clearMessage();
      }
    );
  }
);

/* =========================
   가입 완료
========================= */

trainerProfileForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    clearMessage();

    const birthDate =
      birthDateInput.value;

    const gymName =
      gymNameInput
        .value
        .trim();

    if (!selectedGender) {
      showMessage(
        "성별을 선택해 주세요."
      );

      return;
    }

    if (!birthDate) {
      showMessage(
        "생년월일을 선택해 주세요.",
        birthDateInput
      );

      return;
    }

    if (!gymName) {
      showMessage(
        "활동 헬스장을 입력해 주세요.",
        gymNameInput
      );

      return;
    }

    if (!validateCareerYears()) {
      return;
    }

    if (
      selectedSpecialties.length
      === 0
    ) {
      showMessage(
        "전문 분야를 한 개 이상 선택해 주세요."
      );

      return;
    }

    if (
      !validateGoogleAgreements()
    ) {
      return;
    }

    addPendingCertification();

    completeButton.disabled =
      true;

    completeButton.textContent =
      "가입 처리 중...";

    skipButton.disabled =
      true;

    try {
      const signupData =
        createSignupData();

      const result =
        await submitSignup(
          signupData
        );

      console.log(
        "트레이너 가입 완료:",
        result
      );

      handleSignupSuccess(
        result
      );

    } catch (error) {
      console.error(
        "트레이너 가입 실패:",
        error
      );

      showMessage(
        error.message
        || "트레이너 가입 중 오류가 발생했습니다."
      );

      completeButton.disabled =
        false;

      completeButton.textContent =
        "가입 완료";

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

    skipButton.disabled =
      true;

    skipButton.textContent =
      "가입 처리 중...";

    completeButton.disabled =
      true;

    try {
      const signupData =
        createSignupData({
          skipProfile: true,
        });

      const result =
        await submitSignup(
          signupData
        );

      console.log(
        "트레이너 가입 완료:",
        result
      );

      handleSignupSuccess(
        result
      );

    } catch (error) {
      console.error(
        "트레이너 가입 실패:",
        error
      );

      showMessage(
        error.message
        || "트레이너 가입 중 오류가 발생했습니다."
      );

      skipButton.disabled =
        false;

      skipButton.textContent =
        "나중에 설정하기";

      completeButton.disabled =
        false;
    }
  }
);