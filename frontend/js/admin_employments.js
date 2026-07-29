(function () {
  const $ = (id) => document.getElementById(id);
  const user = window.gymfitApi.requireRole("ADMIN");
  if (!user) return;

  const statusLabels = { NONE: "미등록", PENDING: "대기", APPROVED: "승인", REJECTED: "거절" };
  let filter = String(new URLSearchParams(location.search).get("status") || "PENDING").toUpperCase();
  if (!["PENDING", "APPROVED", "REJECTED", "ALL"].includes(filter)) filter = "PENDING";
  let selected = null, busy = false, blobUrl = null, toastTimer;

  async function api(url, options = {}) {
    return window.gymfitApi.request(url, options);
  }
  function el(tag, className, value) { const node = document.createElement(tag); if (className) node.className = className; if (value != null) node.textContent = value; return node; }
  function toast(message) { clearTimeout(toastTimer); $("employmentToast").textContent = message; $("employmentToast").hidden = false; toastTimer = setTimeout(() => { $("employmentToast").hidden = true; }, 2400); }
  function factList(rows) {
    const facts = el("dl", "admin-card-facts");
    rows.forEach(([label, value]) => { const row = el("div"); row.append(el("dt", "", label), el("dd", "", value || "미등록")); facts.append(row); });
    return facts;
  }
  function closeSheet() {
    $("employmentOverlay").hidden = true; document.body.classList.remove("admin-modal-open");
    $("employmentReason").value = ""; $("employmentReasonField").hidden = true; $("employmentError").hidden = true;
  }
  function setActions(item) {
    const footer = $("employmentActions"); footer.replaceChildren(); footer.classList.remove("single");
    if (item.employment_status !== "PENDING") return;
    const reject = el("button", "admin-button-danger", "거절"), approve = el("button", "admin-button-primary", "승인");
    reject.type = approve.type = "button";
    reject.addEventListener("click", () => {
      $("employmentReasonField").hidden = false; $("employmentError").hidden = true; $("employmentReason").focus();
      footer.replaceChildren();
      const cancel = el("button", "admin-button-secondary", "취소"), confirm = el("button", "admin-button-danger", "거절 확인");
      cancel.type = confirm.type = "button"; cancel.addEventListener("click", () => { $("employmentReasonField").hidden = true; setActions(item); });
      confirm.addEventListener("click", () => submit("reject", confirm)); footer.append(cancel, confirm);
    });
    approve.addEventListener("click", () => submit("approve", approve)); footer.append(reject, approve);
  }
  async function load() {
    document.querySelectorAll("[data-status]").forEach((button) => button.classList.toggle("active", button.dataset.status === filter));
    $("employmentLoading").hidden = false; $("employmentEmpty").hidden = true;
    try {
      const data = await api(`/api/admin/employments?status=${encodeURIComponent(filter)}`), items = Array.isArray(data.items) ? data.items : [];
      $("employmentList").replaceChildren(); $("employmentEmpty").hidden = items.length > 0;
      items.forEach((item) => {
        const card = el("article", "admin-application-card"), head = el("div", "admin-card-head"), identity = el("div");
        identity.append(el("h2", "", item.name || "이름 미등록"), el("p", "admin-card-email", item.email || "이메일 미등록"));
        head.append(identity, el("span", `admin-status-badge ${String(item.employment_status || "NONE").toLowerCase()}`, statusLabels[item.employment_status] || "미등록"));
        const detail = el("button", "admin-detail-button", "상세 보기"); detail.type = "button"; detail.addEventListener("click", () => openDetail(item.user_id));
        card.append(head, factList([
          ["헬스장", item.gym?.gym_name],
          ["주소", item.gym?.road_address],
          ["증빙", item.has_employment_evidence ? item.employment_original_name || "제출 완료" : "미제출"],
        ]), detail);
        $("employmentList").append(card);
      });
    } catch (error) {
      $("employmentEmpty").textContent = error.message;
      $("employmentEmpty").hidden = false;
    } finally { $("employmentLoading").hidden = true; }
  }
  function detailSection(title, rows) {
    const section = el("section", "admin-detail-section"); section.append(el("h3", "", title));
    rows.forEach(([label, value]) => section.append(el("p", "", `${label}: ${value || "미등록"}`))); return section;
  }
  async function openDetail(userId) {
    try {
      selected = await api(`/api/admin/employments/${userId}`); const body = $("employmentDetail"); body.replaceChildren();
      body.append(el("h3", "admin-person-name", selected.name || "이름 미등록"), el("p", "admin-person-email", selected.email || "이메일 미등록"));
      body.append(
        detailSection("신청자 정보", [["트레이너", selected.name], ["이메일", selected.email]]),
        detailSection("소속 헬스장", [["헬스장", selected.gym?.gym_name], ["주소", selected.gym?.road_address]]),
      );
      const evidence = el("section", "admin-detail-section admin-evidence-grid"); evidence.append(el("h3", "", "재직·소속 증빙"));
      if (blobUrl) { URL.revokeObjectURL(blobUrl); blobUrl = null; }
      if (selected.employment_evidence_url) {
        const response = await window.gymfitApi.fetch(selected.employment_evidence_url);
        if (response.ok) {
          blobUrl = URL.createObjectURL(await response.blob());
          const image = document.createElement("img"); image.src = blobUrl; image.alt = "재직·소속 증빙"; image.addEventListener("click", () => window.open(blobUrl, "_blank", "noopener,noreferrer")); evidence.append(image);
        } else evidence.append(el("div", "admin-evidence-empty", "제출된 증빙 이미지가 없습니다."));
      } else evidence.append(el("div", "admin-evidence-empty", "제출된 증빙 이미지가 없습니다."));
      body.append(evidence, detailSection("검토 정보", [
        ["상태", statusLabels[selected.employment_status]],
        ["검토일", selected.employment_reviewed_at ? new Intl.DateTimeFormat("ko-KR", { dateStyle: "medium", timeStyle: "short" }).format(new Date(selected.employment_reviewed_at)) : null],
        ["거절 사유", selected.employment_rejection_reason],
      ]));
      $("employmentReason").value = ""; $("employmentReasonField").hidden = true; $("employmentError").hidden = true; setActions(selected);
      $("employmentOverlay").hidden = false; document.body.classList.add("admin-modal-open"); requestAnimationFrame(() => $("employmentClose").focus());
    } catch (error) { toast(error.message); }
  }
  async function submit(action, button) {
    if (!selected || busy) return;
    const reason = $("employmentReason").value.trim();
    if (action === "reject" && !reason) { $("employmentError").textContent = "거절 사유를 입력해 주세요."; $("employmentError").hidden = false; $("employmentReason").focus(); return; }
    busy = true; button.disabled = true;
    try {
      await api(`/api/admin/employments/${selected.user_id}/${action}`, { method: "POST", body: action === "reject" ? JSON.stringify({ reason }) : null });
      closeSheet(); await load(); toast(action === "approve" ? "소속을 승인했습니다." : "소속 승인을 거절했습니다.");
    } catch (error) { $("employmentError").textContent = error.message; $("employmentError").hidden = false; }
    finally { busy = false; button.disabled = false; }
  }
  document.querySelectorAll("[data-status]").forEach((button) => button.addEventListener("click", () => { filter = button.dataset.status; history.replaceState(null, "", `/admin/employments?status=${filter}`); load(); }));
  ["employmentClose", "employmentBackdrop"].forEach((id) => $(id).addEventListener("click", closeSheet));
  $("adminLogout").addEventListener("click", (event) => window.logoutGymfit(event));
  window.addEventListener("keydown", (event) => { if (event.key === "Escape" && !$("employmentOverlay").hidden) closeSheet(); });
  window.addEventListener("beforeunload", () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }); load();
})();
