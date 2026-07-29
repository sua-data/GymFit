const findPasswordForm = document.querySelector(
  "#findPasswordForm"
);

const backButton = document.querySelector(
  "#backButton"
);

const emailInput = document.querySelector(
  "#email"
);

const formMessage = document.querySelector(
  "#formMessage"
);

const sendButton = document.querySelector(
  "#sendButton"
);

const requestView = document.querySelector(
  "#requestView"
);

const successView = document.querySelector(
  "#successView"
);

const sentEmail = document.querySelector(
  "#sentEmail"
);

const loginMoveButton = document.querySelector(
  "#loginMoveButton"
);

const resendButton = document.querySelector(
  "#resendButton"
);


/* =========================
   뒤로가기
========================= */

backButton.addEventListener("click", () => {
  if (!successView.hidden) {
    showRequestView();
    return;
  }

  window.location.href = "/login";
});


/* =========================
   메시지
========================= */

function showMessage(message, isSuccess = false) {
  formMessage.textContent = message;

  formMessage.classList.toggle(
    "success",
    isSuccess
  );
}

function clearMessage() {
  formMessage.textContent = "";
  formMessage.classList.remove("success");
}


/* =========================
   이메일 검사
========================= */

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}


/* =========================
   화면 전환
========================= */

function showRequestView() {
  successView.hidden = true;
  requestView.hidden = false;

  clearMessage();

  sendButton.disabled = false;
  sendButton.textContent = "임시 비밀번호 발급";

  emailInput.focus();
}

function showSuccessView(email) {
  requestView.hidden = true;
  successView.hidden = false;

  sentEmail.textContent = email;

  window.scrollTo({
    top: 0,
    behavior: "smooth",
  });
}


/* =========================
   이메일 입력
========================= */

emailInput.addEventListener("input", () => {
  clearMessage();
});


/* =========================
   로그인 이동
========================= */

loginMoveButton.addEventListener("click", () => {
  window.location.href = "/login";
});


/* =========================
   다시 발급
========================= */

resendButton.addEventListener("click", () => {
  emailInput.value = "";

  showRequestView();
});


/* =========================
   임시 비밀번호 발급
========================= */

findPasswordForm.addEventListener(
  "submit",
  async (event) => {
    event.preventDefault();

    clearMessage();

    const email = emailInput.value.trim();

    if (!email) {
      showMessage("이메일을 입력해 주세요.");

      emailInput.focus();
      return;
    }

    if (!isValidEmail(email)) {
      showMessage(
        "올바른 이메일 형식을 입력해 주세요."
      );

      emailInput.focus();
      return;
    }

    sendButton.disabled = true;
    sendButton.textContent = "전송 중...";

    try {
      const response = await fetch(
        "/api/auth/password/temporary",
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
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
          "임시 비밀번호를 발급하지 못했습니다."
        );
      }

      showSuccessView(email);

    } catch (error) {
      console.error(
        "임시 비밀번호 발급 실패:",
        error
      );

      showMessage(
        error.message ||
        "임시 비밀번호를 발급하지 못했습니다."
      );

      sendButton.disabled = false;
      sendButton.textContent =
        "임시 비밀번호 발급";
    }
  }
);
