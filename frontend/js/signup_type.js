const accountCards =
  document.querySelectorAll(
    ".account-card"
  );

const backButton =
  document.querySelector(
    "#backButton"
  );

const pageTitle =
  document.querySelector(
    "#pageTitle"
  );

const pageDescription =
  document.querySelector(
    "#pageDescription"
  );

const loginGuide =
  document.querySelector(
    "#loginGuide"
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


/* =========================
   Google 신규 가입 화면 처리
========================= */

if (isGoogleSignup) {
  pageTitle.textContent =
    "계정 유형 선택";

  pageDescription.textContent =
    "GYMFIT을 어떻게 이용하시나요?";

  loginGuide.hidden = true;
}


/* =========================
   뒤로가기
========================= */

backButton.addEventListener(
  "click",
  () => {
    if (isGoogleSignup) {
      sessionStorage.removeItem(
        "googleSignup"
      );

      sessionStorage.removeItem(
        "signupProvider"
      );
    }

    window.location.href =
      "/login";
  }
);


/* =========================
   계정 유형 저장
========================= */

function saveAccountType(
  accountType
) {
  sessionStorage.setItem(
    "gymfitAccountType",
    accountType
  );

  sessionStorage.setItem(
    "signupAccountType",
    accountType
  );
}


/* =========================
   선택 후 이동
========================= */

function moveToSignupPage(
  accountType
) {
  if (accountType === "MEMBER") {
    if (isGoogleSignup) {
      window.location.href =
        "/signup/step2";

      return;
    }

    window.location.href =
      "/signup";

    return;
  }

  if (accountType === "TRAINER") {
    if (isGoogleSignup) {
      window.location.href =
        "/signup/trainer/step2";

      return;
    }

    window.location.href =
      "/signup/trainer";
  }
}


/* =========================
   계정 유형 선택
========================= */

accountCards.forEach(
  (card) => {
    card.addEventListener(
      "click",
      () => {
        const accountType =
          card.dataset.type;

        if (!accountType) {
          return;
        }

        accountCards.forEach(
          (item) => {
            item.classList.remove(
              "selected"
            );
          }
        );

        card.classList.add(
          "selected"
        );

        saveAccountType(
          accountType
        );

        window.setTimeout(
          () => {
            moveToSignupPage(
              accountType
            );
          },
          180
        );
      }
    );
  }
);