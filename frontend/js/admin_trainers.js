(function () {
  const $ = (id) => document.getElementById(id);
  let user;
  try { user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null"); } catch { user = null; }
  user = user && Number(user.user_id ?? user.userId) > 0 ? { ...user, user_id: Number(user.user_id ?? user.userId) } : null;
  if (!user) { location.replace("/login"); return; }
  if (String(user.account_type || "").toUpperCase() !== "ADMIN") { location.replace("/dashboard"); return; }

  const statusLabels = { PENDING: "대기", APPROVED: "승인", REJECTED: "거절", NONE: "미등록" };
  const specialtyLabels = {
    BODY_CORRECTION: "체형 교정", REHABILITATION: "재활 운동", WEIGHT_LOSS: "체중 감량",
    MUSCLE_GAIN: "근력 강화", GENERAL_FITNESS: "일반 체력", BODYBUILDING: "보디빌딩",
    STRENGTH: "근력 운동", DIET: "다이어트", POSTURE: "자세 교정", PILATES: "필라테스",
    FUNCTIONAL_TRAINING: "기능성 운동", SPORTS_PERFORMANCE: "스포츠 퍼포먼스",
  };
  let filter = String(new URLSearchParams(location.search).get("status") || "PENDING").toUpperCase();
  if (!["PENDING", "APPROVED", "REJECTED", "ALL"].includes(filter)) filter = "PENDING";
  let trainers = [], reviewTarget = null, submitting = false, toastTimer;
  const blobUrls = new Set();

  async function api(url, options = {}) {
    const response = await fetch(url, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}), "X-User-Id": String(user.user_id) } });
    const body = await response.json().catch(() => null);
    if (!response.ok) { const error = new Error(body?.detail || "요청을 처리하지 못했습니다."); error.status = response.status; throw error; }
    return body;
  }
  function el(tag, className, value) { const node = document.createElement(tag); if (className) node.className = className; if (value != null) node.textContent = value; return node; }
  function formatDate(value, withTime = false) { return value ? new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}) }).format(new Date(value)) : "미등록"; }
  function specialtyLabel(code) { return specialtyLabels[String(code || "").toUpperCase()] || String(code || "").replaceAll("_", " "); }
  function toast(message) { clearTimeout(toastTimer); $("adminToast").textContent = message; $("adminToast").hidden = false; toastTimer = setTimeout(() => { $("adminToast").hidden = true; }, 2400); }
  function openSheet(overlay, focus) { overlay.hidden = false; document.body.classList.add("admin-modal-open"); requestAnimationFrame(() => focus?.focus()); }
  function closeSheet(overlay) { overlay.hidden = true; if ($("detailOverlay").hidden && $("reviewOverlay").hidden) document.body.classList.remove("admin-modal-open"); }
  function factList(rows) {
    const facts = el("dl", "admin-card-facts");
    rows.forEach(([label, value]) => { const row = el("div"); row.append(el("dt", "", label), el("dd", "", value || "미등록")); facts.append(row); });
    return facts;
  }
  function render() {
    $("trainerList").replaceChildren(); $("adminEmpty").hidden = trainers.length > 0;
    trainers.forEach((trainer) => {
      const card = el("article", "admin-application-card"); card.id = `trainer-${trainer.user_id}`;
      const head = el("div", "admin-card-head"), identity = el("div");
      identity.append(el("h2", "", trainer.name || "이름 미등록"), el("p", "admin-card-email", trainer.email || "이메일 미등록"));
      head.append(identity, el("span", `admin-status-badge ${String(trainer.approval_status || "NONE").toLowerCase()}`, statusLabels[trainer.approval_status] || "미등록"));
      const detail = el("button", "admin-detail-button", "상세 보기"); detail.type = "button"; detail.addEventListener("click", () => openDetail(trainer.user_id));
      card.append(head, factList([
        ["헬스장", trainer.gym?.gym_name],
        ["신청일", formatDate(trainer.created_at)],
        ["증빙", trainer.has_valid_evidence ? "제출 완료" : "미제출"],
      ]), detail);
      $("trainerList").append(card);
    });
  }
  async function load() {
    document.querySelectorAll("[data-status]").forEach((button) => button.classList.toggle("active", button.dataset.status === filter));
    $("adminLoading").hidden = false; $("adminError").hidden = true; $("adminEmpty").hidden = true;
    try {
      const data = await api(`/api/admin/trainers?status=${encodeURIComponent(filter)}`);
      trainers = Array.isArray(data.items) ? data.items : []; render();
      const match = location.hash.match(/^#trainer-(\d+)$/); if (match) openDetail(Number(match[1]));
    } catch (error) {
      if (error.status === 401) location.replace("/login"); else if (error.status === 403) location.replace("/dashboard");
      else { $("adminErrorMessage").textContent = error.message; $("adminError").hidden = false; }
    } finally { $("adminLoading").hidden = true; }
  }
  function section(title, values, className = "") {
    const valid = values.filter(Boolean); if (!valid.length) return null;
    const result = el("section", `admin-detail-section ${className}`.trim()); result.append(el("h3", "", title));
    valid.forEach((value) => result.append(el("p", "", value))); return result;
  }
  function setDetailActions(trainer) {
    const footer = $("detailActions"); footer.replaceChildren(); footer.classList.remove("single");
    const add = (label, className, action) => { const button = el("button", className, label); button.type = "button"; button.addEventListener("click", () => openReview(trainer, action)); footer.append(button); };
    if (trainer.approval_status === "PENDING") { add("거절", "admin-button-danger", "reject"); add("승인", "admin-button-primary", "approve"); }
    else if (trainer.approval_status === "APPROVED") { footer.classList.add("single"); add("승인 취소", "admin-button-danger", "revoke"); }
  }
  async function appendEvidence(container, certification) {
    if (!certification.has_evidence || !certification.evidence_image_url) return false;
    try {
      const response = await fetch(certification.evidence_image_url, { headers: { "X-User-Id": String(user.user_id) } }); if (!response.ok) return false;
      const url = URL.createObjectURL(await response.blob()); blobUrls.add(url);
      const image = document.createElement("img"); image.src = url; image.alt = `${certification.certification_name} 증빙`; image.addEventListener("click", () => window.open(url, "_blank", "noopener,noreferrer")); container.append(image); return true;
    } catch { return false; }
  }
  async function openDetail(userId) {
    try {
      blobUrls.forEach((url) => URL.revokeObjectURL(url)); blobUrls.clear();
      const trainer = await api(`/api/admin/trainers/${userId}`), body = $("detailContent");
      body.replaceChildren(el("h3", "admin-person-name", trainer.name || "이름 미등록"), el("p", "admin-person-email", trainer.email || "이메일 미등록"));
      [
        section("신청자 정보", [`가입 방식: ${trainer.login_provider || "미등록"}`, `신청일: ${formatDate(trainer.created_at)}`]),
        section("기본 프로필", [`헬스장: ${trainer.gym?.gym_name || "미등록"}`, trainer.gym?.road_address ? `주소: ${trainer.gym.road_address}` : "주소: 미등록", trainer.career_years == null ? "경력: 미등록" : `경력: ${trainer.career_years}년`, trainer.introduction || "소개: 미등록"]),
        section("자격증 정보", (trainer.certifications || []).map((item) => [item.certification_name, item.issuer, item.certification_number, item.acquired_date].filter(Boolean).join(" · "))),
        section("전문 분야", (trainer.specialties || []).map(specialtyLabel)),
      ].filter(Boolean).forEach((item) => body.append(item));
      const evidence = el("section", "admin-detail-section admin-evidence-grid"); evidence.append(el("h3", "", "증빙 이미지"));
      const results = await Promise.all((trainer.certifications || []).map((item) => appendEvidence(evidence, item)));
      if (!results.some(Boolean)) evidence.append(el("div", "admin-evidence-empty", "제출된 증빙 이미지가 없습니다."));
      body.append(evidence);
      const review = section("검토 정보", [`상태: ${statusLabels[trainer.approval_status] || "미등록"}`, trainer.reviewer_name ? `검토자: ${trainer.reviewer_name}` : "검토자: 미등록", trainer.reviewed_at ? `검토일: ${formatDate(trainer.reviewed_at, true)}` : "검토일: 미등록", trainer.rejection_reason ? `거절 사유: ${trainer.rejection_reason}` : null]);
      if (review) body.append(review);
      setDetailActions(trainer); openSheet($("detailOverlay"), $("detailClose"));
    } catch (error) { toast(error.message); }
  }
  function openReview(trainer, action) {
    reviewTarget = { trainer, action }; const needsReason = action !== "approve";
    $("reviewTitle").textContent = { approve: "트레이너 승인", reject: "트레이너 승인 거절", revoke: "트레이너 승인 취소" }[action];
    $("reviewMessage").textContent = action === "revoke" ? `${trainer.name} 트레이너를 재검토 상태로 변경할까요?` : `${trainer.name} 트레이너 신청을 ${action === "approve" ? "승인" : "거절"}할까요?`;
    $("reasonField").hidden = !needsReason; $("reviewReason").value = ""; $("reasonCount").textContent = "0"; $("reviewError").hidden = true;
    $("reviewConfirm").textContent = action === "approve" ? "승인" : action === "reject" ? "거절" : "승인 취소";
    openSheet($("reviewOverlay"), needsReason ? $("reviewReason") : $("reviewCancel"));
  }
  async function submitReview() {
    if (!reviewTarget || submitting) return; const reason = $("reviewReason").value.trim(), needsReason = reviewTarget.action !== "approve";
    if (needsReason && !reason) { $("reviewError").textContent = "사유를 입력해 주세요."; $("reviewError").hidden = false; $("reviewReason").focus(); return; }
    submitting = true; $("reviewConfirm").disabled = true;
    try {
      await api(`/api/admin/trainers/${reviewTarget.trainer.user_id}/${reviewTarget.action}`, { method: "POST", body: needsReason ? JSON.stringify({ reason }) : null });
      closeSheet($("reviewOverlay")); closeSheet($("detailOverlay")); await load(); toast("승인 상태를 변경했습니다.");
    } catch (error) { $("reviewError").textContent = error.message; $("reviewError").hidden = false; }
    finally { submitting = false; $("reviewConfirm").disabled = false; }
  }
  document.querySelectorAll("[data-status]").forEach((button) => button.addEventListener("click", () => { filter = button.dataset.status; history.replaceState(null, "", `/admin/trainers?status=${filter}`); load(); }));
  $("adminRetry").addEventListener("click", load); $("adminLogout").addEventListener("click", (event) => window.logoutGymfit(event));
  [["detailClose", "detailOverlay"], ["detailBackdrop", "detailOverlay"], ["reviewClose", "reviewOverlay"], ["reviewBackdrop", "reviewOverlay"], ["reviewCancel", "reviewOverlay"]].forEach(([button, overlay]) => $(button).addEventListener("click", () => closeSheet($(overlay))));
  $("reviewConfirm").addEventListener("click", submitReview); $("reviewReason").addEventListener("input", (event) => { $("reasonCount").textContent = String(event.target.value.length); });
  window.addEventListener("keydown", (event) => { if (event.key !== "Escape") return; if (!$("reviewOverlay").hidden) closeSheet($("reviewOverlay")); else if (!$("detailOverlay").hidden) closeSheet($("detailOverlay")); });
  window.addEventListener("beforeunload", () => blobUrls.forEach((url) => URL.revokeObjectURL(url))); load();
})();
