(function () {
  const agreements = {
    terms: {
      title: "서비스 이용약관",
      sections: [
        ["제1조 목적", "본 약관은 GYMFIT이 제공하는 운동 관리, 운동 자세 코칭, 운동 기록, 루틴, 헬스장 및 PT 연계 서비스의 이용 조건과 회원의 권리·의무를 정하는 것을 목적으로 합니다."],
        ["제2조 서비스 내용", "GYMFIT은 개인 맞춤 운동 루틴, 운동 자세 분석 및 코칭, 운동 기록과 통계, 헬스장 및 운동기구 정보, 트레이너와 회원 간 PT 일정·운동 과제·피드백 서비스를 제공합니다."],
        ["제3조 회원가입", "회원은 정확한 정보를 제공해야 하며 타인의 정보를 도용하거나 허위 정보를 등록해서는 안 됩니다."],
        ["제4조 계정 관리", "회원은 자신의 계정 정보를 안전하게 관리해야 하며 계정의 부정 사용을 발견한 경우 즉시 서비스에 알려야 합니다."],
        ["제5조 이용 제한", "타인의 개인정보 도용, 서비스 운영 방해, 허위 자격정보 제출, 다른 이용자에게 피해를 주는 행위가 확인되면 서비스 이용이 제한될 수 있습니다."],
        ["제6조 트레이너 서비스", "트레이너 기능은 자격 및 헬스장 소속 검토가 완료된 계정에 한해 제공될 수 있습니다. 자격증 또는 소속 정보 변경 시 재검토 기간 동안 일부 관리 기능이 제한될 수 있습니다."],
        ["제7조 운동 코칭 정보", "GYMFIT의 자세 분석 및 운동 피드백은 운동 보조 정보이며 의료 진단이나 치료를 대신하지 않습니다. 통증이나 부상이 있는 경우 전문가의 진료 또는 지도를 받아야 합니다."],
        ["제8조 서비스 변경 및 중단", "점검, 장애 또는 운영상 필요에 따라 서비스 일부가 변경되거나 일시 중단될 수 있습니다."],
        ["제9조 회원 탈퇴", "회원은 서비스에서 탈퇴를 요청할 수 있으며 관련 법령과 개인정보 처리 기준에 따라 데이터가 처리됩니다."],
        ["제10조 책임 제한", "회원이 자신의 건강 상태를 고려하지 않고 운동하거나 안내를 잘못 적용해 발생한 손해에 대해서는 서비스의 고의 또는 중대한 과실이 없는 한 책임이 제한될 수 있습니다."],
      ],
    },
    privacy: {
      title: "개인정보 수집·이용 동의",
      sections: [
        ["수집 목적", ["회원가입 및 본인 확인", "계정과 서비스 제공", "운동 루틴 및 운동 기록 관리", "트레이너 자격 및 헬스장 소속 검토", "고객 문의와 서비스 운영", "부정 이용 방지"]],
        ["수집 항목", ["이름", "이메일", "비밀번호 해시 또는 소셜 로그인 식별정보", "회원 유형", "서비스 이용 기록", "회원이 직접 입력한 운동 정보", "운동 목표 및 운동 수준", "소속 헬스장 정보", "트레이너 자격증 및 소속 증빙 정보"]],
        ["보유 기간", ["회원 탈퇴 시까지", "관계 법령에서 별도 보관을 요구하는 경우 해당 기간까지", "심사 자료는 검토 및 분쟁 대응에 필요한 기간 동안 보관 후 삭제"]],
        ["동의 거부 권리", "개인정보 수집·이용 동의를 거부할 수 있으나 필수 정보 수집에 동의하지 않으면 회원가입 및 서비스 이용이 제한될 수 있습니다."],
      ],
    },
    marketing: {
      title: "마케팅 정보 수신 동의",
      sections: [
        ["수신 목적", ["신규 기능 안내", "운동 콘텐츠 및 이벤트 안내", "혜택 및 프로모션 정보 제공"]],
        ["수신 채널", ["이메일", "서비스 내 알림"]],
        ["안내", "마케팅 정보 수신에 동의하지 않아도 기본 서비스는 이용할 수 있습니다. 동의 후에도 마이페이지 알림 설정에서 철회할 수 있습니다."],
      ],
    },
    trainerPolicy: {
      title: "트레이너 운영정책",
      sections: [
        ["트레이너 서비스", "트레이너 기능은 자격 및 헬스장 소속 검토가 완료된 계정에 한해 제공될 수 있습니다. 자격증 또는 소속 정보 변경 시 재검토 기간 동안 일부 관리 기능이 제한될 수 있습니다."],
      ],
    },
  };
  const aliases = { service: "terms", trainer: "trainerPolicy", "trainer-policy": "trainerPolicy" };
  let returnFocus = null;

  const overlay = document.createElement("div");
  overlay.className = "agreement-modal-overlay";
  overlay.id = "agreementModal";
  overlay.hidden = true;
  overlay.innerHTML = `
    <section class="agreement-modal" role="dialog" aria-modal="true" aria-labelledby="agreementModalTitle">
      <header class="agreement-modal-header">
        <div><span>AGREEMENT</span><h2 id="agreementModalTitle"></h2></div>
        <button class="agreement-modal-close" id="agreementModalClose" type="button" aria-label="약관 닫기">×</button>
      </header>
      <div class="agreement-modal-body" id="agreementModalBody"></div>
      <footer class="agreement-modal-footer">
        <button class="agreement-modal-confirm" id="agreementModalConfirm" type="button">확인</button>
      </footer>
    </section>`;
  document.body.append(overlay);

  const title = overlay.querySelector("#agreementModalTitle");
  const body = overlay.querySelector("#agreementModalBody");
  const closeButton = overlay.querySelector("#agreementModalClose");
  const confirmButton = overlay.querySelector("#agreementModalConfirm");

  function renderSection([heading, content]) {
    const section = document.createElement("section");
    section.className = "agreement-modal-section";
    const sectionTitle = document.createElement("h3");
    sectionTitle.textContent = heading;
    section.append(sectionTitle);
    if (Array.isArray(content)) {
      const list = document.createElement("ul");
      content.forEach((value) => {
        const item = document.createElement("li");
        item.textContent = value;
        list.append(item);
      });
      section.append(list);
    } else {
      const paragraph = document.createElement("p");
      paragraph.textContent = content;
      section.append(paragraph);
    }
    return section;
  }
  function openAgreement(type, trigger) {
    const normalized = aliases[type] || type;
    const agreement = agreements[normalized];
    if (!agreement) return;
    returnFocus = trigger;
    title.textContent = agreement.title;
    body.replaceChildren(...agreement.sections.map(renderSection));
    body.scrollTop = 0;
    overlay.hidden = false;
    document.body.classList.add("agreement-modal-open");
    requestAnimationFrame(() => closeButton.focus());
  }
  function closeAgreement() {
    overlay.hidden = true;
    document.body.classList.remove("agreement-modal-open");
    returnFocus?.focus();
  }
  document.addEventListener("click", (event) => {
    const button = event.target.closest(".agreement-view-button");
    if (!button) return;
    const type = button.dataset.agreement || button.dataset.terms;
    openAgreement(type, button);
  });
  overlay.addEventListener("click", (event) => {
    if (event.target === overlay) closeAgreement();
  });
  closeButton.addEventListener("click", closeAgreement);
  confirmButton.addEventListener("click", closeAgreement);
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && !overlay.hidden) closeAgreement();
  });
})();
