(function () {
  const $ = (id) => document.getElementById(id);
  let user;
  try { user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null"); } catch { user = null; }
  user = user && Number(user.user_id ?? user.userId) > 0 ? { ...user, user_id: Number(user.user_id ?? user.userId) } : null;
  if (!user) { location.replace("/login"); return; }
  if (String(user.account_type || "").toUpperCase() !== "TRAINER") { location.replace("/mypage"); return; }
  let items = [], editing = null, busy = false, toastTimer;
  async function api(url, options = {}) {
    const response = await fetch(url, { ...options, headers: { ...(options.body instanceof FormData ? {} : options.body ? { "Content-Type": "application/json" } : {}), ...(options.headers || {}), "X-User-Id": String(user.user_id) } });
    const body = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.detail || "요청을 처리하지 못했습니다.");
    return body;
  }
  function toast(message) { clearTimeout(toastTimer); $("certToast").textContent = message; $("certToast").hidden = false; toastTimer = setTimeout(() => { $("certToast").hidden = true; }, 2200); }
  function statusCopy(status, reason) {
    if (status === "APPROVED") return ["승인된 트레이너 계정", "자격증 정보를 변경하면 재검토 상태로 전환됩니다."];
    if (status === "REJECTED") return ["승인이 거절되었습니다.", reason ? `거절 사유: ${reason} 자격 정보를 보완하면 재검토를 요청할 수 있습니다.` : "자격 정보를 보완하면 재검토를 요청할 수 있습니다."];
    return ["관리자 검토 대기 중", "승인이 완료될 때까지 일부 트레이너 관리 기능이 제한됩니다."];
  }
  function render(data) {
    items = data.items || []; const copy = statusCopy(data.approval_status, data.rejection_reason);
    $("certStatus").replaceChildren(Object.assign(document.createElement("strong"), { textContent: copy[0] }), document.createTextNode(copy[1]));
    $("certList").replaceChildren(); $("certEmpty").hidden = items.length > 0;
    items.forEach((item) => {
      const card = document.createElement("article"); card.className = "cert-card";
      const title = document.createElement("h2"); title.textContent = item.certification_name;
      const facts = document.createElement("p"); facts.textContent = [item.issuer, item.certification_number, item.acquired_date].filter(Boolean).join(" · ") || "추가 정보 없음";
      const evidence = document.createElement("p"); evidence.textContent = item.evidence_image_url ? `증빙: ${item.evidence_original_name || "등록됨"}` : "증빙 미등록";
      const actions = document.createElement("div"); actions.className = "cert-actions";
      const edit = document.createElement("button"); edit.type = "button"; edit.textContent = "수정"; edit.addEventListener("click", () => openForm(item));
      const remove = document.createElement("button"); remove.type = "button"; remove.className = "danger"; remove.textContent = "삭제"; remove.addEventListener("click", () => removeItem(item));
      const label = document.createElement("label"); label.className = "evidence-label"; label.textContent = item.evidence_image_url ? "증빙 교체" : "증빙 이미지 등록";
      const input = document.createElement("input"); input.type = "file"; input.accept = ".jpg,.jpeg,.png,.webp"; input.addEventListener("change", () => upload(item, input.files?.[0])); label.append(input);
      actions.append(edit, remove, label);
      if (item.evidence_image_url) { const clear = document.createElement("button"); clear.type = "button"; clear.className = "danger"; clear.textContent = "증빙 삭제"; clear.addEventListener("click", () => removeEvidence(item)); actions.append(clear); }
      card.append(title, facts, evidence, actions); $("certList").append(card);
    });
  }
  async function load() { $("certLoading").hidden = false; try { render(await api("/api/trainers/me/certifications")); } catch (error) { toast(error.message); } finally { $("certLoading").hidden = true; } }
  function openForm(item = null) {
    editing = item; $("certFormTitle").textContent = item ? "자격증 수정" : "자격증 추가";
    $("certName").value = item?.certification_name || ""; $("certIssuer").value = item?.issuer || ""; $("certNumber").value = item?.certification_number || ""; $("certDate").value = item?.acquired_date || "";
    $("certError").hidden = true; $("certOverlay").hidden = false; document.body.classList.add("modal-open"); $("certName").focus();
  }
  function closeForm() { $("certOverlay").hidden = true; document.body.classList.remove("modal-open"); }
  async function save(event) {
    event.preventDefault(); if (busy) return; busy = true; $("certSubmit").disabled = true;
    const payload = { certification_name: $("certName").value.trim(), issuer: $("certIssuer").value.trim() || null, certification_number: $("certNumber").value.trim() || null, acquired_date: $("certDate").value || null };
    try { await api(editing ? `/api/trainers/me/certifications/${editing.certification_id}` : "/api/trainers/me/certifications", { method: editing ? "PATCH" : "POST", body: JSON.stringify(payload) }); closeForm(); await load(); toast("자격증 정보를 저장했습니다."); }
    catch (error) { $("certError").textContent = error.message; $("certError").hidden = false; } finally { busy = false; $("certSubmit").disabled = false; }
  }
  async function removeItem(item) { if (busy || !confirm(`${item.certification_name} 자격증을 삭제할까요?`)) return; busy = true; try { await api(`/api/trainers/me/certifications/${item.certification_id}`, { method: "DELETE" }); await load(); toast("자격증을 삭제했습니다."); } catch (error) { toast(error.message); } finally { busy = false; } }
  async function upload(item, file) { if (!file || busy) return; busy = true; const data = new FormData(); data.append("file", file); try { await api(`/api/trainers/me/certifications/${item.certification_id}/evidence`, { method: "POST", body: data }); await load(); toast("증빙 이미지를 저장했습니다."); } catch (error) { toast(error.message); } finally { busy = false; } }
  async function removeEvidence(item) { if (busy || !confirm("등록된 증빙 이미지를 삭제할까요?")) return; busy = true; try { await api(`/api/trainers/me/certifications/${item.certification_id}/evidence`, { method: "DELETE" }); await load(); toast("증빙 이미지를 삭제했습니다."); } catch (error) { toast(error.message); } finally { busy = false; } }
  $("addCertification").addEventListener("click", () => openForm()); $("certClose").addEventListener("click", closeForm); $("certBackdrop").addEventListener("click", closeForm); $("certForm").addEventListener("submit", save); load();
})();
