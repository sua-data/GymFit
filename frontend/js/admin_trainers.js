(function () {
  const $ = (id) => document.getElementById(id);
  let user;
  try { user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null"); } catch { user = null; }
  user = user && Number(user.user_id ?? user.userId) > 0 ? { ...user, user_id: Number(user.user_id ?? user.userId) } : null;
  if (!user) { location.replace("/login"); return; }
  if (String(user.account_type || "").toUpperCase() !== "ADMIN") { location.replace("/dashboard"); return; }

  const labels = { PENDING: "승인 대기", APPROVED: "승인", REJECTED: "거절" };
  let filter = String(new URLSearchParams(location.search).get("status") || "PENDING").toUpperCase();
  if (!["PENDING", "APPROVED", "REJECTED", "ALL"].includes(filter)) filter = "PENDING";
  let trainers = [], target = null, submitting = false, toastTimer;
  const blobUrls = new Set();
  async function api(url, options = {}) {
    const response = await fetch(url, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}), "X-User-Id": String(user.user_id) } });
    const body = await response.json().catch(() => null);
    if (!response.ok) { const error = new Error(body?.detail || "요청을 처리하지 못했습니다."); error.status = response.status; throw error; }
    return body;
  }
  function el(tag, className, value) { const n = document.createElement(tag); if (className) n.className = className; if (value != null) n.textContent = value; return n; }
  function date(value, withTime = false) { return value ? new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit", ...(withTime ? { hour: "2-digit", minute: "2-digit" } : {}) }).format(new Date(value)) : ""; }
  function toast(message) { clearTimeout(toastTimer); $("adminToast").textContent = message; $("adminToast").hidden = false; toastTimer = setTimeout(() => { $("adminToast").hidden = true; }, 2400); }
  function open(overlay, focus) { overlay.hidden = false; document.body.classList.add("modal-open"); requestAnimationFrame(() => focus?.focus()); }
  function close(overlay) { overlay.hidden = true; if ($("detailOverlay").hidden && $("reviewOverlay").hidden) document.body.classList.remove("modal-open"); }
  function actionButtons(trainer) {
    const wrap = el("div", "trainer-actions");
    const add = (action, className, text) => { const button = el("button", className, text); button.type = "button"; button.addEventListener("click", () => openReview(trainer, action)); wrap.append(button); };
    if (trainer.approval_status === "PENDING") { add("approve", "approve", "승인"); add("reject", "reject", "거절"); }
    if (trainer.approval_status === "APPROVED") add("revoke", "reject full", "승인 취소");
    return wrap.childElementCount ? wrap : null;
  }
  function render() {
    $("trainerList").replaceChildren(); $("adminEmpty").hidden = trainers.length > 0;
    trainers.forEach((trainer) => {
      const card = el("article", "trainer-card"); card.id = `trainer-${trainer.user_id}`;
      const heading = el("div", "trainer-heading"), identity = el("div");
      identity.append(el("h2", "", trainer.name), el("p", "", trainer.email));
      heading.append(identity, el("span", `status-badge ${String(trainer.approval_status).toLowerCase()}`, labels[trainer.approval_status] || trainer.approval_status));
      const facts = el("dl", "trainer-facts");
      [["헬스장", trainer.gym?.gym_name], ["경력", trainer.career_years == null ? null : `${trainer.career_years}년`], ["신청일", date(trainer.created_at)], ["증빙", trainer.has_valid_evidence ? "제출 완료" : "미제출"]].forEach(([key, value]) => {
        if (!value) return; const row = el("div"); row.append(el("dt", "", key), el("dd", "", value)); facts.append(row);
      });
      const detail = el("button", "detail-button", "상세 보기"); detail.type = "button"; detail.addEventListener("click", () => openDetail(trainer.user_id));
      card.append(heading, facts, detail); const actions = actionButtons(trainer); if (actions) card.append(actions); $("trainerList").append(card);
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
  function section(title, values) { const valid = values.filter(Boolean); if (!valid.length) return null; const result = el("section", "application-section"); result.append(el("h3", "", title)); valid.forEach((value) => result.append(el("p", "", value))); return result; }
  async function appendEvidence(container, cert) {
    if (!cert.has_evidence || !cert.evidence_image_url) return;
    try {
      const response = await fetch(cert.evidence_image_url, { headers: { "X-User-Id": String(user.user_id) } }); if (!response.ok) return;
      const url = URL.createObjectURL(await response.blob()); blobUrls.add(url);
      const image = document.createElement("img"); image.src = url; image.alt = `${cert.certification_name} 증빙`; container.append(image);
    } catch { /* 나머지 상세 정보는 유지 */ }
  }
  async function openDetail(userId) {
    try {
      blobUrls.forEach((url) => URL.revokeObjectURL(url)); blobUrls.clear();
      const trainer = await api(`/api/admin/trainers/${userId}`), content = $("detailContent");
      content.replaceChildren(el("h3", "application-name", trainer.name), el("p", "application-email", trainer.email));
      [
        section("기본 프로필", [trainer.gym?.gym_name, trainer.gym?.road_address, trainer.career_years == null ? null : `경력 ${trainer.career_years}년`, trainer.introduction]),
        section("전문 분야", trainer.specialties || []),
        section("검토 정보", [`상태: ${labels[trainer.approval_status] || trainer.approval_status}`, trainer.reviewer_name ? `검토자: ${trainer.reviewer_name}` : null, trainer.reviewed_at ? `검토일: ${date(trainer.reviewed_at, true)}` : null, trainer.rejection_reason ? `거절 사유: ${trainer.rejection_reason}` : null]),
        section("자격증", (trainer.certifications || []).map((item) => [item.certification_name, item.issuer, item.certification_number, item.acquired_date].filter(Boolean).join(" · "))),
      ].filter(Boolean).forEach((item) => content.append(item));
      const evidence = el("section", "application-section evidence-section"); evidence.append(el("h3", "", "자격증 증빙"));
      await Promise.all((trainer.certifications || []).map((cert) => appendEvidence(evidence, cert))); if (evidence.children.length > 1) content.append(evidence);
      const actions = actionButtons(trainer); if (actions) content.append(actions); open($("detailOverlay"), $("detailClose"));
    } catch (error) { toast(error.message); }
  }
  function openReview(trainer, action) {
    target = { trainer, action }; const needsReason = action !== "approve";
    $("reviewTitle").textContent = { approve: "트레이너 승인", reject: "트레이너 승인 거절", revoke: "트레이너 승인 취소" }[action];
    $("reviewMessage").textContent = action === "revoke" ? `${trainer.name} 트레이너를 재검토 상태로 변경할까요? 기존 관계와 기록은 유지됩니다.` : `${trainer.name} 트레이너의 신청을 ${action === "approve" ? "승인" : "거절"}할까요?`;
    $("reasonField").hidden = !needsReason; $("reviewReason").value = ""; $("reasonCount").textContent = "0"; $("reviewError").hidden = true;
    $("reviewConfirm").textContent = action === "approve" ? "승인" : action === "reject" ? "거절" : "승인 취소"; open($("reviewOverlay"), needsReason ? $("reviewReason") : $("reviewCancel"));
  }
  async function submit() {
    if (!target || submitting) return; const reason = $("reviewReason").value.trim(), needsReason = target.action !== "approve";
    if (needsReason && !reason) { $("reviewError").textContent = "사유를 입력해 주세요."; $("reviewError").hidden = false; return; }
    submitting = true; $("reviewConfirm").disabled = true;
    try {
      await api(`/api/admin/trainers/${target.trainer.user_id}/${target.action}`, { method: "POST", body: needsReason ? JSON.stringify({ reason }) : null });
      close($("reviewOverlay")); if (!$("detailOverlay").hidden) close($("detailOverlay")); await load();
      toast(target.action === "approve" ? "승인했습니다." : target.action === "reject" ? "거절했습니다." : "승인을 취소하고 재검토 상태로 변경했습니다.");
    } catch (error) { $("reviewError").textContent = error.message; $("reviewError").hidden = false; }
    finally { submitting = false; $("reviewConfirm").disabled = false; }
  }
  document.querySelectorAll("[data-status]").forEach((button) => button.addEventListener("click", () => { filter = button.dataset.status; history.replaceState(null, "", `/admin/trainers?status=${filter}`); load(); }));
  $("adminRetry").addEventListener("click", load); $("adminLogout").addEventListener("click", () => { sessionStorage.clear(); location.replace("/login"); });
  [["detailClose", "detailOverlay"], ["detailBackdrop", "detailOverlay"], ["reviewClose", "reviewOverlay"], ["reviewBackdrop", "reviewOverlay"], ["reviewCancel", "reviewOverlay"]].forEach(([button, overlay]) => $(button).addEventListener("click", () => close($(overlay))));
  $("reviewConfirm").addEventListener("click", submit); $("reviewReason").addEventListener("input", (event) => { $("reasonCount").textContent = String(event.target.value.length); });
  window.addEventListener("beforeunload", () => blobUrls.forEach((url) => URL.revokeObjectURL(url))); load();
})();
