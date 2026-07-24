const loginForm = document.querySelector(
  "#loginForm"
);

const emailInput = document.querySelector(
  "#email"
);

const passwordInput = document.querySelector(
  "#password"
);

const passwordToggle = document.querySelector(
  "#passwordToggle"
);

const passwordIcon = document.querySelector(
  "#passwordIcon"
);

const loginButton = document.querySelector(
  "#loginButton"
);

const googleLoginButton =
  document.querySelector(
    "#googleLoginButton"
  );

const errorMessage = document.querySelector(
  "#errorMessage"
);
const emailError = document.querySelector("#emailError");
const passwordError = document.querySelector("#passwordError");

const googleClientIdMeta =
  document.querySelector(
    'meta[name="google-client-id"]'
  );

let googleCodeClient = null;
let loginNavigationStarted = false;


/* =========================
   비밀번호 표시 / 숨김
========================= */

passwordToggle.addEventListener(
  "click",
  () => {
    const isHidden =
      passwordInput.type === "password";

    passwordInput.type = isHidden
      ? "text"
      : "password";

    passwordIcon.src = isHidden
      ? "/static/assets/icons/eye.svg"
      : "/static/assets/icons/eye-off.svg";

    passwordToggle.setAttribute(
      "aria-label",
      isHidden
        ? "비밀번호 숨기기"
        : "비밀번호 표시"
    );
  }
);


/* =========================
   오류 메시지
========================= */

function showError(
  message,
  inputElement = null
) {
  clearError();
  const fieldError = inputElement === emailInput
    ? emailError
    : inputElement === passwordInput
      ? passwordError
      : errorMessage;
  fieldError.textContent = message;

  if (inputElement) {
    inputElement.setAttribute("aria-invalid", "true");
    inputElement.focus();
  }
}


function clearError() {
  errorMessage.textContent = "";
  emailError.textContent = "";
  passwordError.textContent = "";
  emailInput.removeAttribute("aria-invalid");
  passwordInput.removeAttribute("aria-invalid");
}


emailInput.addEventListener(
  "input",
  clearError
);


passwordInput.addEventListener(
  "input",
  clearError
);


/* =========================
   API 오류 메시지 추출
========================= */

function getErrorMessage(
  data,
  fallbackMessage
) {
  if (typeof data?.detail === "string") {
    return data.detail;
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg)
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
   이메일 로그인 API
========================= */

async function requestLogin(
  email,
  password
) {
  const response = await fetch(
    "/api/auth/login",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",
      },

      body: JSON.stringify({
        email,
        password,
      }),
    }
  );

  const data =
    await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "로그인에 실패했습니다."
      )
    );
  }

  return data;
}


/* =========================
   Google 인증 코드 전송
========================= */

async function requestGoogleCodeLogin(
  code
) {
  const response = await fetch(
    "/api/auth/google/code",
    {
      method: "POST",

      headers: {
        "Content-Type":
          "application/json",

        "X-Requested-With":
          "XmlHttpRequest",
      },

      body: JSON.stringify({
        code,
      }),
    }
  );

  const data =
    await readJsonResponse(response);

  if (!response.ok) {
    throw new Error(
      getErrorMessage(
        data,
        "Google 로그인에 실패했습니다."
      )
    );
  }

  return data;
}


/* =========================
   로그인 사용자 저장
========================= */

function saveLoginUser(data) {
  if (!data.access_token) {
    throw new Error("로그인 응답에 액세스 토큰이 없습니다.");
  }
  if (window.gymfitApi?.setAccessToken) {
    window.gymfitApi.setAccessToken(data.access_token);
  } else {
    sessionStorage.setItem("gymfitAccessToken", data.access_token);
  }
  const loginUser = {
    user_id: data.user_id,
    account_type: data.account_type,
    name: data.name,
    email: data.email,
    must_change_password:
      data.must_change_password ?? false,
    has_active_trainer:
      data.has_active_trainer === true,
    pending_pt_request_count:
      Math.max(0, Number(data.pending_pt_request_count) || 0),
  };

  sessionStorage.setItem(
    "gymfitUser",
    JSON.stringify(loginUser)
  );
}


/* =========================
   Google 신규 가입 정보 저장
========================= */

function saveGoogleSignup(data) {
  const googleSignup = {
    signup_token: data.signup_token,
    name: data.name,
    email: data.email,
  };

  sessionStorage.setItem(
    "googleSignup",
    JSON.stringify(googleSignup)
  );

  sessionStorage.setItem(
    "signupProvider",
    "GOOGLE"
  );
}


/* =========================
   임시 회원가입 정보 삭제
========================= */

function clearSignupSession() {
  sessionStorage.removeItem(
    "googleSignup"
  );

  sessionStorage.removeItem(
    "signupProvider"
  );
}


/* =========================
   로그인 성공 후 이동
========================= */

function moveAfterLogin() {
  if (loginNavigationStarted) {
    return;
  }
  loginNavigationStarted = true;
  let accountType = "";
  try {
    accountType = String(
      JSON.parse(sessionStorage.getItem("gymfitUser") || "null")?.account_type || ""
    ).toUpperCase();
  } catch {
    accountType = "";
  }
  const target = accountType === "ADMIN"
    ? "/admin/dashboard"
    : accountType === "TRAINER"
      ? "/trainer/members"
      : "/dashboard";
  window.location.replace(target);
}


/* =========================
   이메일 로그인
========================= */

loginForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    if (loginForm.dataset.submitting === "true") {
      return;
    }

    clearError();

    const email =
      emailInput.value.trim();

    const password =
      passwordInput.value;

    if (!email) {
      showError(
        "이메일을 입력해 주세요.",
        emailInput
      );

      return;
    }

    if (!emailInput.validity.valid) {
      showError(
        "올바른 이메일 형식을 입력해 주세요.",
        emailInput
      );

      return;
    }

    if (!password) {
      showError(
        "비밀번호를 입력해 주세요.",
        passwordInput
      );

      return;
    }

    if (password.length < 8) {
      showError(
        "비밀번호는 8자 이상 입력해 주세요.",
        passwordInput
      );

      return;
    }

    loginForm.dataset.submitting = "true";
    loginForm.setAttribute("aria-busy", "true");
    loginButton.disabled = true;
    loginButton.textContent =
      "로그인 중...";

    try {
      const data = await requestLogin(
        email,
        password
      );

      clearSignupSession();
      saveLoginUser(data);

      if (data.must_change_password) {
        moveAfterLogin();

        return;
      }

      moveAfterLogin();

    } catch (error) {
      console.error(
        "로그인 실패:",
        error
      );

      showError(
        error.message ||
          "로그인 정보를 확인한 뒤 다시 시도해 주세요."
      );

    } finally {
      delete loginForm.dataset.submitting;
      loginForm.removeAttribute("aria-busy");
      if (!loginNavigationStarted) {
        loginButton.disabled = false;
        loginButton.textContent =
          "로그인";
      }
    }
  }
);


/* =========================
   Google 버튼 상태
========================= */

function setGoogleButtonLoading(
  isLoading
) {
  googleLoginButton.disabled =
    isLoading;

  const buttonText =
    googleLoginButton.querySelector(
      "span"
    );

  if (!buttonText) {
    return;
  }

  buttonText.textContent = isLoading
    ? "Google 로그인 중..."
    : "Google 계정으로 로그인";
}


/* =========================
   Google 인증 응답 처리
========================= */

async function handleGoogleCodeResponse(
  googleResponse
) {
  clearError();

  if (googleResponse?.error) {
    console.error(
      "Google 인증 오류:",
      googleResponse
    );

    showError(
      "Google 인증이 취소되었거나 실패했습니다."
    );

    setGoogleButtonLoading(false);

    return;
  }

  const code =
    googleResponse?.code;

  if (!code) {
    showError(
      "Google 인증 코드를 가져오지 못했습니다."
    );

    setGoogleButtonLoading(false);

    return;
  }

  setGoogleButtonLoading(true);

  try {
    const data =
      await requestGoogleCodeLogin(
        code
      );

    if (data.is_new_user) {
      if (!data.signup_token) {
        throw new Error(
          "신규 가입 토큰을 발급받지 못했습니다."
        );
      }

      saveGoogleSignup(data);

      window.location.href =
        "/signup/type";

      return;
    }

    clearSignupSession();
    saveLoginUser(data);
    moveAfterLogin();

  } catch (error) {
    console.error(
      "Google 로그인 실패:",
      error
    );

    showError(
      error.message ||
        "Google 로그인 중 오류가 발생했습니다."
    );

    setGoogleButtonLoading(false);
  }
}


/* =========================
   Google OAuth 초기화
========================= */

function initializeGoogleLogin() {
  const googleClientId =
    googleClientIdMeta?.content?.trim();

  if (!googleClientId) {
    console.error(
      "Google Client ID가 없습니다."
    );

    showError(
      "Google 로그인 설정을 확인해 주세요."
    );

    googleLoginButton.disabled = true;

    return;
  }

  if (
    !window.google
    || !window.google.accounts
    || !window.google.accounts.oauth2
  ) {
    console.error(
      "Google OAuth 라이브러리를 불러오지 못했습니다."
    );

    showError(
      "Google 로그인 서비스를 불러오지 못했습니다."
    );

    googleLoginButton.disabled = true;

    return;
  }

  googleCodeClient =
    window.google.accounts.oauth2
      .initCodeClient({
        client_id: googleClientId,

        scope: [
          "openid",
          "email",
          "profile",
        ].join(" "),

        ux_mode: "popup",

        callback:
          handleGoogleCodeResponse,

        error_callback: (
          errorResponse
        ) => {
          console.error(
            "Google 팝업 오류:",
            errorResponse
          );

          setGoogleButtonLoading(
            false
          );

          if (
            errorResponse?.type ===
            "popup_closed"
          ) {
            return;
          }

          showError(
            "Google 로그인 팝업을 열지 못했습니다."
          );
        },
      });

  googleLoginButton.disabled = false;
}


/* =========================
   Google 버튼 클릭
========================= */

googleLoginButton.addEventListener(
  "click",
  () => {
    clearError();

    if (!googleCodeClient) {
      showError(
        "Google 로그인을 준비하는 중입니다. 잠시 후 다시 시도해 주세요."
      );

      return;
    }

    setGoogleButtonLoading(true);

    try {
      googleCodeClient.requestCode();
    } catch (error) {
      console.error(
        "Google 인증 요청 실패:",
        error
      );

      showError(
        "Google 로그인 팝업을 열지 못했습니다."
      );

      setGoogleButtonLoading(false);
    }
  }
);


/* =========================
   Google SDK 로딩 대기
========================= */

function waitForGoogleLibrary(
  retryCount = 0
) {
  const maxRetryCount = 50;

  if (
    window.google
    && window.google.accounts
    && window.google.accounts.oauth2
  ) {
    initializeGoogleLogin();

    return;
  }

  if (retryCount >= maxRetryCount) {
    console.error(
      "Google SDK 로딩 시간 초과"
    );

    showError(
      "Google 로그인 서비스를 불러오지 못했습니다."
    );

    googleLoginButton.disabled = true;

    return;
  }

  window.setTimeout(
    () => {
      waitForGoogleLibrary(
        retryCount + 1
      );
    },
    100
  );
}


/* =========================
   초기 실행
========================= */

window.addEventListener(
  "DOMContentLoaded",
  () => {
    googleLoginButton.disabled = true;

    waitForGoogleLibrary();
  }
);
