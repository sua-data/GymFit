import os
import secrets
import smtplib
from email.message import EmailMessage
from email.utils import (
    formataddr,
    formatdate,
    make_msgid,
)
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent.parent
load_dotenv(BASE_DIR / ".env")


MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv(
    "MAIL_FROM",
    MAIL_USERNAME,
)
MAIL_FROM_NAME = os.getenv(
    "MAIL_FROM_NAME",
    "GYMFIT",
)
MAIL_SERVER = os.getenv(
    "MAIL_SERVER",
    "smtp.gmail.com",
)
MAIL_PORT = int(
    os.getenv("MAIL_PORT", "587")
)


def generate_verification_code() -> str:
    """6자리 이메일 인증번호 생성"""
    return f"{secrets.randbelow(1_000_000):06d}"


def validate_mail_settings() -> None:
    """메일 환경변수 설정 확인"""
    required_values = {
        "MAIL_USERNAME": MAIL_USERNAME,
        "MAIL_PASSWORD": MAIL_PASSWORD,
        "MAIL_FROM": MAIL_FROM,
    }

    missing_keys = [
        key
        for key, value in required_values.items()
        if not value
    ]

    if missing_keys:
        raise RuntimeError(
            "메일 환경변수가 없습니다: "
            + ", ".join(missing_keys)
        )


def get_logo_path() -> Path:
    """메일용 GYMFIT 로고 경로 반환"""
    logo_path = (
        BASE_DIR
        / "frontend"
        / "assets"
        / "icons"
        / "GYMFIT_text.png"
    )

    if not logo_path.exists():
        raise FileNotFoundError(
            "메일 로고 파일을 찾을 수 없습니다: "
            f"{logo_path}"
        )

    return logo_path


def send_verification_email(
    recipient_email: str,
    verification_code: str,
) -> None:
    """회원가입 이메일 인증번호 전송"""
    validate_mail_settings()

    message = EmailMessage()

    # 이메일 제목 설정
    message["Subject"] = (
        "[GYMFIT] 인증번호 안내"
    )

    message["From"] = formataddr(
        (
            MAIL_FROM_NAME,
            MAIL_FROM,
        )
    )

    message["To"] = recipient_email
    message["Date"] = formatdate(localtime=True)

    # 메일마다 고유한 ID 생성
    message["Message-ID"] = make_msgid(
        domain="gymfit.local"
    )

    # HTML 메일을 지원하지 않는 환경용 텍스트
    message.set_content(
        f"""
GYMFIT 이메일 인증번호입니다.

인증번호: {verification_code}

인증번호는 3분 동안 유효합니다.
본인이 요청하지 않았다면 이 메일을 무시해 주세요.
""".strip()
    )

    # HTML 메일
    message.add_alternative(
        f"""
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="color-scheme" content="only light">
  <meta name="supported-color-schemes" content="light">

  <meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
  >

  <title>GYMFIT 이메일 인증</title>
</head>

<body
  bgcolor="#000000"
  style="
    margin: 0;
    padding: 0;
    color: #ffffff !important;
    background-color: #000000 !important;
    font-family: Arial, Helvetica, sans-serif;
  "
>
  <table
    role="presentation"
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    bgcolor="#000000"
    style="
      width: 100%;
      margin: 0;
      padding: 0;
      background-color: #000000 !important;
    "
  >
    <tr>
      <td
        align="center"
        style="
          padding: 32px 16px;
        "
      >
        <table
          role="presentation"
          width="100%"
          cellpadding="0"
          cellspacing="0"
          border="0"
          bgcolor="#1F1F1F"
          style="
            width: 100%;
            max-width: 520px;
            color: #ffffff !important;
            background-color: #1F1F1F !important;
            border: 1px solid #333333;
            border-radius: 22px;
          "
        >
          <tr>
            <td
              bgcolor="#1F1F1F"
              style="
                padding: 36px 30px;
                color: #ffffff !important;
                background-color: #1F1F1F !important;
              "
            >
              <!-- GYMFIT 로고 -->
              <div style="
                margin: 0 0 24px;
                padding: 0;
                text-align: left;
              ">
                <img
                  src="cid:gymfit-logo"
                  alt="GYMFIT"
                  width="130"
                  style="
                    display: block;
                    width: 130px;
                    max-width: 100%;
                    height: auto;
                    margin: 0;
                    padding: 0;
                    border: 0;
                    outline: none;
                    text-decoration: none;
                  "
                >
              </div>

              <!-- 제목 -->
              <h1 style="
                margin: 0;
                color: #ffffff !important;
                -webkit-text-fill-color: #ffffff !important;
              ">
                이메일 인증번호
              </h1>

              <!-- 설명 -->
              <p style="
                color: #bcbcbc !important;
                -webkit-text-fill-color: #bcbcbc !important;
              ">
                아래 인증번호를<br>
                GYMFIT 회원가입 화면에 입력해 주세요.
              </p>

              <!-- 인증번호 -->
              <table
                role="presentation"
                width="100%"
                cellpadding="0"
                cellspacing="0"
                border="0"
                bgcolor="#111111"
                style="
                  width: 100%;
                  margin: 26px 0;
                  background-color: #111111 !important;
                  border: 1px solid #A8FF35;
                  border-radius: 16px;
                "
              >
                <tr>
                  <td
                    align="center"
                    bgcolor="#111111"
                    style="
                      padding: 22px 14px;

                      color: #A8FF35 !important;
                      background-color: #111111 !important;

                      font-family:
                        Arial,
                        Helvetica,
                        sans-serif;

                      font-size: 32px;
                      font-weight: 800;
                      letter-spacing: 8px;
                      line-height: 1.2;

                      -webkit-text-fill-color:
                        #A8FF35 !important;
                    "
                  >
                    {verification_code}
                  </td>
                </tr>
              </table>

              <!-- 안내 -->
              <p style="
                margin: 0;
                padding: 0;
                color: #888888 !important;
                -webkit-text-fill-color: #888888 !important;
                font-size: 13px;
                line-height: 1.7;
              ">
                인증번호는 3분 동안 유효합니다.<br>
                본인이 요청하지 않았다면 이 메일을
                무시해 주세요.
              </p>

              <!-- 하단 -->
              <div style="
                margin: 28px 0 0;
                padding-top: 18px;
                border-top: 1px solid #333333;
              ">
                <p style="
                  margin: 0;
                  padding: 0;
                  color: #666666 !important;
                  -webkit-text-fill-color: #666666 !important;
                  font-size: 12px;
                  line-height: 1.6;
                ">
                  Move Better, Get Stronger.<br>
                  © GYMFIT
                </p>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""".strip(),
        subtype="html",
    )

    # PNG 로고를 메일 본문에 첨부
    logo_path = get_logo_path()

    with open(logo_path, "rb") as logo_file:
        logo_data = logo_file.read()

    html_part = message.get_payload()[-1]

    html_part.add_related(
        logo_data,
        maintype="image",
        subtype="png",
        cid="<gymfit-logo>",
        filename="GYMFIT_text.png",
        disposition="inline",
    )

    # Gmail SMTP 전송
    with smtplib.SMTP(
        MAIL_SERVER,
        MAIL_PORT,
        timeout=20,
    ) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        smtp.login(
            MAIL_USERNAME,
            MAIL_PASSWORD,
        )

        smtp.send_message(message)

def send_temporary_password_email(
    recipient_email: str,
    temporary_password: str,
) -> None:
    """임시 비밀번호 이메일 전송"""
    validate_mail_settings()

    message = EmailMessage()

    message["Subject"] = (
        "[GYMFIT] 임시 비밀번호 안내"
    )

    message["From"] = formataddr(
        (
            MAIL_FROM_NAME,
            MAIL_FROM,
        )
    )

    message["To"] = recipient_email
    message["Date"] = formatdate(localtime=True)

    message["Message-ID"] = make_msgid(
        domain="gymfit.local"
    )

    message.set_content(
        f"""
GYMFIT 임시 비밀번호입니다.

임시 비밀번호: {temporary_password}

임시 비밀번호는 30분 동안 유효합니다.
로그인 후 새로운 비밀번호로 변경해 주세요.

본인이 요청하지 않았다면 고객센터에 문의해 주세요.
""".strip()
    )

    message.add_alternative(
        f"""
<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta
    name="viewport"
    content="width=device-width, initial-scale=1.0"
  >
  <title>GYMFIT 임시 비밀번호</title>
</head>

<body
  bgcolor="#000000"
  style="
    margin: 0;
    padding: 0;
    background-color: #000000;
    font-family: Arial, Helvetica, sans-serif;
  "
>
  <table
    role="presentation"
    width="100%"
    cellpadding="0"
    cellspacing="0"
    border="0"
    bgcolor="#000000"
  >
    <tr>
      <td
        align="center"
        style="padding: 32px 16px;"
      >
        <table
          role="presentation"
          width="100%"
          cellpadding="0"
          cellspacing="0"
          border="0"
          bgcolor="#1F1F1F"
          style="
            width: 100%;
            max-width: 520px;
            background-color: #1F1F1F;
            border: 1px solid #333333;
            border-radius: 22px;
          "
        >
          <tr>
            <td style="padding: 36px 30px;">
              <div style="margin-bottom: 24px;">
                <img
                  src="cid:gymfit-logo"
                  alt="GYMFIT"
                  width="130"
                  style="
                    display: block;
                    width: 130px;
                    height: auto;
                    border: 0;
                  "
                >
              </div>

              <h1
                style="
                  margin: 0;
                  color: #ffffff;
                  font-size: 26px;
                "
              >
                임시 비밀번호
              </h1>

              <p
                style="
                  margin: 16px 0 0;
                  color: #bcbcbc;
                  line-height: 1.7;
                "
              >
                아래 임시 비밀번호로 로그인한 뒤<br>
                새로운 비밀번호로 변경해 주세요.
              </p>

              <table
                role="presentation"
                width="100%"
                cellpadding="0"
                cellspacing="0"
                border="0"
                bgcolor="#111111"
                style="
                  width: 100%;
                  margin: 26px 0;
                  background-color: #111111;
                  border: 1px solid #A8FF35;
                  border-radius: 16px;
                "
              >
                <tr>
                  <td
                    align="center"
                    style="
                      padding: 22px 14px;
                      color: #A8FF35;
                      font-size: 25px;
                      font-weight: 800;
                      letter-spacing: 3px;
                    "
                  >
                    {temporary_password}
                  </td>
                </tr>
              </table>

              <p
                style="
                  margin: 0;
                  color: #888888;
                  font-size: 13px;
                  line-height: 1.7;
                "
              >
                임시 비밀번호는 30분 동안 유효합니다.<br>
                본인이 요청하지 않았다면 이 메일을
                무시해 주세요.
              </p>

              <div
                style="
                  margin-top: 28px;
                  padding-top: 18px;
                  border-top: 1px solid #333333;
                "
              >
                <p
                  style="
                    margin: 0;
                    color: #666666;
                    font-size: 12px;
                    line-height: 1.6;
                  "
                >
                  Move Better, Get Stronger.<br>
                  © GYMFIT
                </p>
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
""".strip(),
        subtype="html",
    )

    logo_path = get_logo_path()

    with open(logo_path, "rb") as logo_file:
        logo_data = logo_file.read()

    html_part = message.get_payload()[-1]

    html_part.add_related(
        logo_data,
        maintype="image",
        subtype="png",
        cid="<gymfit-logo>",
        filename="GYMFIT_text.png",
        disposition="inline",
    )

    with smtplib.SMTP(
        MAIL_SERVER,
        MAIL_PORT,
        timeout=20,
    ) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.ehlo()

        smtp.login(
            MAIL_USERNAME,
            MAIL_PASSWORD,
        )

        smtp.send_message(message)