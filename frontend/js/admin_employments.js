(function () {
  const $ = (id) => document.getElementById(id);
  let user; try { user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null"); } catch { user = null; }
  user = user && Number(user.user_id ?? user.userId) > 0 ? { ...user, user_id: Number(user.user_id ?? user.userId) } : null;
  if (!user) { location.replace("/login"); return; }
  if (String(user.account_type || "").toUpperCase() !== "ADMIN") { location.replace("/dashboard"); return; }
  let filter = new URLSearchParams(location.search).get("status") || "PENDING", selected, action, busy = false, blobUrl;
  const labels = { NONE: "미등록", PENDING: "승인 대기", APPROVED: "승인", REJECTED: "거절" };
  async function api(url, options = {}) {
    const response = await fetch(url, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), "X-User-Id": String(user.user_id) } });
    const body = await response.json().catch(() => null); if (!response.ok) throw new Error(body?.detail || "요청을 처리하지 못했습니다."); return body;
  }
  function el(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
  async function load() {
    document.querySelectorAll("[data-status]").forEach((button) => button.classList.toggle("active", button.dataset.status === filter)); $("employmentLoading").hidden = false;
    try {
      const data = await api(`/api/admin/employments?status=${filter}`), items = data.items || []; $("employmentList").replaceChildren(); $("employmentEmpty").hidden = items.length > 0;
      items.forEach((item) => {
        const card = el("article", "trainer-card"), heading = el("div", "trainer-heading"), identity = el("div");
        identity.append(el("h2", "", item.name), el("p", "", item.email)); heading.append(identity, el("span", `status-badge ${item.employment_status.toLowerCase()}`, labels[item.employment_status]));
        const facts = el("dl", "trainer-facts");
        [["헬스장", item.gym?.gym_name || "없음"], ["주소", item.gym?.road_address], ["증빙", item.has_employment_evidence ? item.employment_original_name || "제출됨" : "미제출"]].forEach(([key, value]) => { if (!value) return; const row = el("div"); row.append(el("dt", "", key), el("dd", "", value)); facts.append(row); });
        const detail = el("button", "detail-button", "상세 보기"); detail.onclick = () => openDetail(item.user_id); card.append(heading, facts, detail); $("employmentList").append(card);
      });
    } catch (error) { $("employmentEmpty").textContent = error.message; $("employmentEmpty").hidden = false; } finally { $("employmentLoading").hidden = true; }
  }
  async function openDetail(id) {
    selected = await api(`/api/admin/employments/${id}`); action = null; const box = $("employmentDetail"); box.replaceChildren();
    [["트레이너", selected.name], ["이메일", selected.email], ["헬스장", selected.gym?.gym_name], ["주소", selected.gym?.road_address], ["상태", labels[selected.employment_status]], ["거절 사유", selected.employment_rejection_reason]].forEach(([key, value]) => { if (value) box.append(el("p", "", `${key}: ${value}`)); });
    if (blobUrl) URL.revokeObjectURL(blobUrl);
    if (selected.employment_evidence_url) { const response = await fetch(selected.employment_evidence_url, { headers: { "X-User-Id": String(user.user_id) } }); if (response.ok) { blobUrl = URL.createObjectURL(await response.blob()); const image = document.createElement("img"); image.src = blobUrl; image.alt = "재직·소속 증빙"; const section = el("section", "application-section evidence-section"); section.append(el("h3", "", "재직·소속 증빙"), image); box.append(section); } }
    if (selected.employment_status === "PENDING") { const buttons = el("div", "trainer-actions"), approve = el("button", "approve", "승인"), reject = el("button", "reject", "거절"); approve.onclick = () => choose("approve"); reject.onclick = () => choose("reject"); buttons.append(approve, reject); box.append(buttons); }
    $("employmentReasonField").hidden = true; $("employmentConfirmActions").hidden = true; $("employmentError").hidden = true; $("employmentOverlay").hidden = false;
  }
  function choose(next) { action = next; $("employmentReasonField").hidden = next !== "reject"; $("employmentConfirmActions").hidden = false; $("employmentConfirm").textContent = next === "approve" ? "승인" : "거절"; }
  async function submit() {
    if (!selected || !action || busy) return; const reason = $("employmentReason").value.trim();
    if (action === "reject" && !reason) { $("employmentError").textContent = "거절 사유를 입력해 주세요."; $("employmentError").hidden = false; return; }
    busy = true; try { await api(`/api/admin/employments/${selected.user_id}/${action}`, { method: "POST", body: action === "reject" ? JSON.stringify({ reason }) : null }); $("employmentOverlay").hidden = true; await load(); } catch (error) { $("employmentError").textContent = error.message; $("employmentError").hidden = false; } finally { busy = false; }
  }
  document.querySelectorAll("[data-status]").forEach((button) => button.onclick = () => { filter = button.dataset.status; history.replaceState(null, "", `?status=${filter}`); load(); });
  $("employmentConfirm").onclick = submit; ["employmentClose", "employmentBackdrop", "employmentCancel"].forEach((id) => $(id).onclick = () => { $("employmentOverlay").hidden = true; });
  $("adminLogout").onclick = () => { sessionStorage.clear(); location.replace("/login"); }; window.addEventListener("beforeunload", () => { if (blobUrl) URL.revokeObjectURL(blobUrl); }); load();
})();
