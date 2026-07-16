const signupForm = document.querySelector("#signupForm");

const backButton = document.querySelector("#backButton");

const nameInput = document.querySelector("#name");
const emailInput = document.querySelector("#signupEmail");

const emailAuthButton = document.querySelector(
  "#emailAuthButton"
);

const emailMessage = document.querySelector(
  "#emailMessage"
);

const verificationArea = document.querySelector(
  "#verificationArea"
);

const verificationCodeInput = document.querySelector(
  "#verificationCode"
);

const verificationButton = document.querySelector(
  "#verificationButton"
);

const verificationMessage = document.querySelector(
  "#verificationMessage"
);

const passwordInput = document.querySelector(
  "#signupPassword"
);

const passwordConfirmInput = document.querySelector(
  "#passwordConfirm"
);

const passwordToggle = document.querySelector(
  "#passwordToggle"
);

const passwordIcon = document.querySelector(
  "#passwordIcon"
);

const passwordConfirmToggle = document.querySelector(
  "#passwordConfirmToggle"
);

const passwordConfirmIcon = document.querySelector(
  "#passwordConfirmIcon"
);

const agreeAll = document.querySelector("#agreeAll");

const agreeTerms = document.querySelector(
  "#agreeTerms"
);

const agreePrivacy = document.querySelector(
  "#agreePrivacy"
);

const agreeMarketing = document.querySelector(
  "#agreeMarketing"
);

const requiredTerms = document.querySelectorAll(
  ".required-term"
);

const termsViewButtons =
  document.querySelectorAll(
    ".agreement-view-button"
  );

const formErrorMessage = document.querySelector(
  "#formErrorMessage"
);

const nextButton = document.querySelector("#nextButton");


const VERIFICATION_TIME = 180;

let remainingSeconds = VERIFICATION_TIME;
let timerId = null;

let verificationSent = false;
let emailVerified = false;


/* =========================
   뒤로가기
========================= */

backButton.addEventListener("click", () => {
  window.location.href = "/signup/type";
});


/* =========================
   메시지
========================= */

function showFormError(
  message,
  inputElement = null
) {
  formErrorMessage.textContent = message;

  if (inputElement) {
    inputElement.focus();
  }
}

function clearFormError() {
  formErrorMessage.textContent = "";
}

function setEmailMessage(
  message,
  isSuccess = false
) {
  emailMessage.textContent = message;

  emailMessage.classList.toggle(
    "success",
    isSuccess
  );
}

function setVerificationMessage(
  message,
  isSuccess = false
) {
  verificationMessage.textContent = message;

  verificationMessage.classList.toggle(
    "success",
    isSuccess
  );
}


/* =========================
   비밀번호 표시
========================= */

function togglePassword(
  inputElement,
  iconElement,
  buttonElement
) {
  const isHidden =
    inputElement.type === "password";

  inputElement.type = isHidden
    ? "text"
    : "password";

  iconElement.src = isHidden
    ? "/static/assets/icons/eye.svg"
    : "/static/assets/icons/eye-off.svg";

  buttonElement.setAttribute(
    "aria-label",
    isHidden
      ? "비밀번호 숨기기"
      : "비밀번호 표시"
  );
}

passwordToggle.addEventListener("click", () => {
  togglePassword(
    passwordInput,
    passwordIcon,
    passwordToggle
  );
});

passwordConfirmToggle.addEventListener(
  "click",
  () => {
    togglePassword(
      passwordConfirmInput,
      passwordConfirmIcon,
      passwordConfirmToggle
    );
  }
);


/* =========================
   이메일 형식
========================= */

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(
    email
  );
}


/* =========================
   인증 타이머
========================= */

function formatTimer(seconds) {
  const minutes = String(
    Math.floor(seconds / 60)
  ).padStart(2, "0");

  const remainSeconds = String(
    seconds % 60
  ).padStart(2, "0");

  return `${minutes}:${remainSeconds}`;
}

function stopTimer() {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }
}

function showResendButton() {
  stopTimer();

  emailAuthButton.classList.remove(
    "timer-mode",
    "success-mode"
  );

  emailAuthButton.disabled = false;
  emailAuthButton.textContent = "↻ 재발송";

  verificationButton.disabled = false;
  verificationButton.textContent = "확인";

  verificationCodeInput.readOnly = false;

  verificationSent = false;
  emailVerified = false;
}

function startTimer() {
  stopTimer();

  remainingSeconds = VERIFICATION_TIME;

  emailAuthButton.classList.remove(
    "success-mode"
  );

  emailAuthButton.classList.add(
    "timer-mode"
  );

  emailAuthButton.disabled = true;

  emailAuthButton.textContent = formatTimer(
    remainingSeconds
  );

  timerId = setInterval(() => {
    remainingSeconds -= 1;

    emailAuthButton.textContent = formatTimer(
      remainingSeconds
    );

    if (remainingSeconds <= 0) {
      showResendButton();

      setVerificationMessage(
        "인증 시간이 만료되었습니다. 인증번호를 다시 받아주세요."
      );
    }
  }, 1000);
}


/* =========================
   인증 상태 초기화
========================= */

function resetVerification() {
  stopTimer();

  verificationArea.hidden = true;

  verificationCodeInput.value = "";
  verificationCodeInput.readOnly = false;

  emailAuthButton.classList.remove(
    "timer-mode",
    "success-mode"
  );

  emailAuthButton.disabled = false;
  emailAuthButton.textContent = "이메일 인증";

  verificationButton.disabled = false;
  verificationButton.textContent = "확인";

  emailInput.readOnly = false;

  emailMessage.textContent = "";
  verificationMessage.textContent = "";

  verificationSent = false;
  emailVerified = false;
}


/* =========================
   이메일 인증 요청
========================= */

emailAuthButton.addEventListener(
  "click",
  async () => {
    clearFormError();

    const email = emailInput.value.trim();

    const isResend =
      emailAuthButton.textContent.includes(
        "재발송"
      );

    if (!email) {
      setEmailMessage(
        "이메일을 입력해 주세요."
      );

      emailInput.focus();
      return;
    }

    if (!isValidEmail(email)) {
      setEmailMessage(
        "올바른 이메일 형식을 입력해 주세요."
      );

      emailInput.focus();
      return;
    }

    emailAuthButton.disabled = true;
    emailAuthButton.textContent = "전송 중...";

    try {
      const response = await fetch(
        "/api/auth/email/send-code",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            email,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "인증메일 전송에 실패했습니다."
        );
      }

      verificationArea.hidden = false;

      verificationSent = true;
      emailVerified = false;

      verificationCodeInput.value = "";
      verificationCodeInput.readOnly = false;

      verificationButton.disabled = false;
      verificationButton.textContent = "확인";

      setEmailMessage(
        isResend
          ? "인증번호를 재전송했습니다."
          : "인증번호를 전송했습니다.",
        true
      );

      setVerificationMessage("");

      startTimer();

      verificationCodeInput.focus();
    } catch (error) {
      emailAuthButton.classList.remove(
        "timer-mode",
        "success-mode"
      );

      emailAuthButton.disabled = false;

      emailAuthButton.textContent = isResend
        ? "↻ 재발송"
        : "이메일 인증";

      setEmailMessage(
        error.message ||
          "인증메일 전송에 실패했습니다."
      );
    }
  }
);


/* =========================
   인증번호 확인
========================= */

verificationButton.addEventListener(
  "click",
  async () => {
    clearFormError();

    const email = emailInput.value.trim();

    const code =
      verificationCodeInput.value.trim();

    if (!verificationSent) {
      setVerificationMessage(
        "이메일 인증번호를 먼저 받아주세요."
      );

      return;
    }

    if (!code) {
      setVerificationMessage(
        "인증번호를 입력해 주세요."
      );

      verificationCodeInput.focus();
      return;
    }

    if (code.length !== 6) {
      setVerificationMessage(
        "인증번호 6자리를 입력해 주세요."
      );

      verificationCodeInput.focus();
      return;
    }

    verificationButton.disabled = true;
    verificationButton.textContent =
      "확인 중...";

    try {
      const response = await fetch(
        "/api/auth/email/verify-code",
        {
          method: "POST",

          headers: {
            "Content-Type":
              "application/json",
          },

          body: JSON.stringify({
            email,
            code,
          }),
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.detail ||
            "인증번호 확인에 실패했습니다."
        );
      }

      stopTimer();

      emailVerified = true;

      emailAuthButton.classList.remove(
        "timer-mode"
      );

      emailAuthButton.classList.add(
        "success-mode"
      );

      emailAuthButton.disabled = true;
      emailAuthButton.textContent =
        "인증 완료";

      verificationButton.disabled = true;
      verificationButton.textContent =
        "확인";

      emailInput.readOnly = true;
      verificationCodeInput.readOnly = true;

      setVerificationMessage(
        "이메일 인증이 완료되었습니다.",
        true
      );
    } catch (error) {
      verificationButton.disabled = false;
      verificationButton.textContent =
        "확인";

      setVerificationMessage(
        error.message ||
          "인증번호 확인에 실패했습니다."
      );
    }
  }
);


/* =========================
   이메일 변경
========================= */

emailInput.addEventListener("input", () => {
  resetVerification();
  clearFormError();
});


/* =========================
   인증번호 숫자만 입력
========================= */

verificationCodeInput.addEventListener(
  "input",
  () => {
    verificationCodeInput.value =
      verificationCodeInput.value.replace(
        /\D/g,
        ""
      );

    setVerificationMessage("");
    clearFormError();
  }
);


/* =========================
   약관
========================= */

agreeAll.addEventListener("change", () => {
  const isChecked = agreeAll.checked;

  agreeTerms.checked = isChecked;
  agreePrivacy.checked = isChecked;
  agreeMarketing.checked = isChecked;

  clearFormError();
});

[
  agreeTerms,
  agreePrivacy,
  agreeMarketing,
].forEach((checkbox) => {
  checkbox.addEventListener("change", () => {
    agreeAll.checked =
      agreeTerms.checked &&
      agreePrivacy.checked &&
      agreeMarketing.checked;

    clearFormError();
  });
});


/* =========================
   약관 보기
========================= */

termsViewButtons.forEach((button) => {
  button.addEventListener("click", () => {
    const termsType = button.dataset.terms;

    const termsTitle = {
      service: "이용약관",
      privacy: "개인정보 수집 및 이용",
      marketing: "마케팅 정보 수신",
    };

    alert(
      `${termsTitle[termsType]} 내용은 추후 연결할 예정입니다.`
    );
  });
});


/* =========================
   입력 시 오류 초기화
========================= */

[
  nameInput,
  passwordInput,
  passwordConfirmInput,
].forEach((input) => {
  input.addEventListener(
    "input",
    clearFormError
  );
});


/* =========================
   다음 단계
========================= */

signupForm.addEventListener(
  "submit",
  (event) => {
    event.preventDefault();

    clearFormError();

    const name = nameInput.value.trim();
    const email = emailInput.value.trim();

    const password = passwordInput.value;

    const passwordConfirm =
      passwordConfirmInput.value;

    if (!name) {
      showFormError(
        "이름을 입력해 주세요.",
        nameInput
      );

      return;
    }

    if (!email) {
      showFormError(
        "이메일을 입력해 주세요.",
        emailInput
      );

      return;
    }

    if (!isValidEmail(email)) {
      showFormError(
        "올바른 이메일 형식을 입력해 주세요.",
        emailInput
      );

      return;
    }

    if (!emailVerified) {
      showFormError(
        "이메일 인증을 완료해 주세요."
      );

      return;
    }

    if (!password) {
      showFormError(
        "비밀번호를 입력해 주세요.",
        passwordInput
      );

      return;
    }

    if (password.length < 8) {
      showFormError(
        "비밀번호는 8자 이상 입력해 주세요.",
        passwordInput
      );

      return;
    }

    if (!passwordConfirm) {
      showFormError(
        "비밀번호 확인을 입력해 주세요.",
        passwordConfirmInput
      );

      return;
    }

    if (password !== passwordConfirm) {
      showFormError(
        "비밀번호가 일치하지 않습니다.",
        passwordConfirmInput
      );

      return;
    }

    const requiredChecked = Array
      .from(requiredTerms)
      .every(
        (checkbox) => checkbox.checked
      );

    if (!requiredChecked) {
      showFormError(
        "필수 약관에 모두 동의해 주세요."
      );

      return;
    }

    const signupData = {
      account_type: "MEMBER",
      name,
      email,
      password,

      agreements: {
        terms: agreeTerms.checked,
        privacy: agreePrivacy.checked,
        marketing: agreeMarketing.checked,
      },
    };

    sessionStorage.setItem(
      "gymfitSignupData",
      JSON.stringify(signupData)
    );

    sessionStorage.setItem(
      "gymfitAccountType",
      "MEMBER"
    );

    nextButton.disabled = true;
    nextButton.textContent = "이동 중...";

    window.location.href =
      "/signup/step2";
  }
);