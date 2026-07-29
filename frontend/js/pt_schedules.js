(function () {
  const isTrainerPage = document.body.dataset.page === "trainer-schedules";
  const list = document.querySelector("#scheduleList");
  const stateBox = document.querySelector("#scheduleState");
  const tabs = document.querySelector("#scheduleTabs");
  const memberSelect = document.querySelector("#scheduleMember");
  let user = null, schedules = [], members = [], selectedMemberId = null, filter = isTrainerPage ? "all" : "upcoming";
  let editingId = null, busy = false;
  let cancelSchedule = async () => {};
  let completeSchedule = async () => {};

  function currentUser() {
    try {
      const value = JSON.parse(sessionStorage.getItem("gymfitUser") || "null");
      const id = Number(value?.user_id ?? value?.userId);
      return id > 0 ? { ...value, user_id: id, account_type: String(value.account_type ?? value.accountType ?? "").toUpperCase() } : null;
    } catch { return null; }
  }

  async function api(url, options = {}) {
    const response = await fetch(url, { ...options, headers: { ...(options.body && !(options.body instanceof FormData) ? { "Content-Type": "application/json" } : {}), "X-User-Id": String(user.user_id) } });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = Array.isArray(body?.detail) ? body.detail.map(item => item.msg).join("\n") : body?.detail;
      throw new Error(detail || "요청을 처리하지 못했습니다.");
    }
    return body;
  }

  const now = () => Date.now();
  const timeValue = value => new Date(value).getTime();
  const isUpcoming = item => item.status === "SCHEDULED" && timeValue(item.end_at) >= now();
  const isPast = item => item.status === "COMPLETED" || (item.status === "SCHEDULED" && timeValue(item.end_at) < now());
  const dateTime = value => new Intl.DateTimeFormat("ko-KR", { month:"long", day:"numeric", weekday:"short", hour:"2-digit", minute:"2-digit", hour12:false }).format(new Date(value));
  const timeOnly = value => new Intl.DateTimeFormat("ko-KR", { hour:"2-digit", minute:"2-digit", hour12:false }).format(new Date(value));
  const statusText = item => item.status === "CANCELLED" ? "취소" : item.status === "COMPLETED" ? "완료" : isPast(item) ? "지난 일정" : "예정";

  function filteredItems() {
    return schedules.filter(item => {
      if (selectedMemberId && Number(item.member_id) !== selectedMemberId) return false;
      if (filter === "upcoming") return isUpcoming(item);
      if (filter === "past") return isPast(item);
      if (filter === "cancelled") return item.status === "CANCELLED";
      return true;
    }).sort((a, b) => timeValue(a.start_at) - timeValue(b.start_at));
  }

  function makeText(tag, text, className) { const el = document.createElement(tag); el.textContent = text; if (className) el.className = className; return el; }
  const esc = value => String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;").replaceAll("'", "&#39;");

  function renderList() {
    const items = filteredItems();
    list.replaceChildren(); list.hidden = !items.length; stateBox.hidden = !!items.length;
    if (!items.length) {
      stateBox.innerHTML = selectedMemberId || !isTrainerPage
        ? "<strong>예정된 PT 일정이 없습니다.</strong><p>다른 일정 구분을 선택해 확인해 보세요.</p>"
        : "<strong>담당 회원을 선택해 주세요.</strong><p>회원을 선택하면 PT 일정을 확인하고 등록할 수 있어요.</p>";
      return;
    }
    items.forEach(item => {
      const card = document.createElement("article");
      card.id = `schedule-${item.schedule_id}`;
      const cardState = item.status === "CANCELLED" ? "cancelled" : item.status === "COMPLETED" ? "completed" : isPast(item) ? "past incomplete" : "";
      card.className = `schedule-card ${cardState}`;
      const heading = makeText("div", "", "schedule-card-heading");
      heading.append(makeText("h3", `${dateTime(item.start_at)} ~ ${timeOnly(item.end_at)}`), makeText("span", statusText(item), "schedule-badge"));
      card.append(heading, makeText("p", `${isTrainerPage ? item.member_name + " 회원" : item.trainer_name + " 트레이너"}`));
      if (item.memo) card.append(makeText("p", item.memo));
      if (isTrainerPage && item.status === "SCHEDULED") {
        const actions = makeText("div", "", "schedule-actions");
        if (timeValue(item.start_at) <= now()) {
          const complete = makeText("button", "PT 완료", "complete");
          complete.type = "button";
          complete.addEventListener("click", () => completeSchedule(item));
          actions.append(complete);
        } else {
          const edit = makeText("button", "수정"); edit.type = "button"; edit.addEventListener("click", () => openForm(item));
          const cancel = makeText("button", "취소", "danger"); cancel.type = "button"; cancel.addEventListener("click", () => cancelSchedule(item));
          actions.append(edit, cancel);
        }
        card.append(actions);
      }
      list.append(card);
    });
    if (location.hash) document.querySelector(location.hash)?.scrollIntoView({ behavior:"smooth", block:"center" });
  }

  function renderNext() {
    const box = document.querySelector("#nextSchedule"); if (!box) return;
    const item = schedules.filter(isUpcoming).sort((a,b) => timeValue(a.start_at)-timeValue(b.start_at))[0];
    box.replaceChildren();
    if (!item) { box.textContent = "예정된 PT 일정이 없습니다."; return; }
    const content = makeText("div", "", "next-schedule-content");
    content.append(makeText("strong", dateTime(item.start_at)), makeText("p", `${item.trainer_name} 트레이너 · ${timeOnly(item.start_at)} ~ ${timeOnly(item.end_at)}${item.memo ? `\n${item.memo}` : ""}`));
    box.append(content);
  }

  function renderMembers() {
    memberSelect.innerHTML = '<option value="">회원 선택</option>';
    members.forEach(member => memberSelect.add(new Option(`${member.member_name} (${member.member_email})`, member.member_id)));
    if (selectedMemberId) memberSelect.value = String(selectedMemberId);
    document.querySelector("#openScheduleForm").disabled = !selectedMemberId;
  }

  async function load() {
    stateBox.hidden = false; list.hidden = true; stateBox.textContent = "일정을 불러오는 중입니다.";
    try {
      if (isTrainerPage) {
        const [memberData, scheduleData] = await Promise.all([api("/api/pt/my-members"), api("/api/pt/schedules/trainer")]);
        members = memberData.items || []; schedules = scheduleData.items || [];
        if (!members.some(item => Number(item.member_id) === selectedMemberId)) selectedMemberId = members[0] ? Number(members[0].member_id) : null;
        renderMembers();
      } else schedules = (await api("/api/pt/schedules/member")).items || [];
      renderNext(); renderList();
    } catch (error) {
      stateBox.hidden = false;
      stateBox.innerHTML = "<strong>PT 일정을 불러오지 못했습니다.</strong><p>네트워크 연결을 확인한 뒤 다시 시도해 주세요.</p>";
      const retryButton = makeText("button", "다시 시도", "gymfit-state-action");
      retryButton.type = "button";
      retryButton.addEventListener("click", load);
      stateBox.append(retryButton);
    }
  }

  tabs.addEventListener("click", event => {
    const button = event.target.closest("button[data-filter]"); if (!button) return;
    filter = button.dataset.filter;
    tabs.querySelectorAll("button").forEach(item => {
      const isSelected = item === button;
      item.classList.toggle("active", isSelected);
      item.setAttribute("aria-selected", String(isSelected));
    });
    renderList();
  });

  if (isTrainerPage) {
    const overlay = document.querySelector("#scheduleFormOverlay"), form = document.querySelector("#scheduleForm"), message = document.querySelector("#scheduleFormMessage");
    const scheduleSaveButton = document.querySelector("#scheduleSave");
    const completeOverlay = document.querySelector("#ptCompleteOverlay"), completeForm = document.querySelector("#ptCompleteForm"), completeMessage = document.querySelector("#ptCompleteMessage");
    let completingItem = null, completeDirty = false, completeMediaUrls = [];
    const localInput = value => { const date = new Date(value); date.setMinutes(date.getMinutes() - date.getTimezoneOffset()); return date.toISOString().slice(0,16); };
    function closeForm() { if (busy) return; overlay.hidden = true; document.body.classList.remove("schedule-sheet-open"); form.reset(); editingId = null; message.textContent = ""; }
    function openForm(item = null) {
      editingId = item?.schedule_id || null; form.reset(); message.textContent = "";
      const base = item ? new Date(item.start_at) : new Date(Date.now() + 3600000); base.setMinutes(Math.ceil(base.getMinutes()/30)*30,0,0);
      document.querySelector("#scheduleStart").value = item ? localInput(item.start_at) : localInput(base);
      document.querySelector("#scheduleEnd").value = item ? localInput(item.end_at) : localInput(new Date(base.getTime()+3600000));
      document.querySelector("#scheduleMemo").value = item?.memo || "";
      document.querySelector("#scheduleFormTitle").textContent = item ? "PT 일정 수정" : "새 PT 일정";
      scheduleSaveButton.textContent = item ? "변경사항 저장" : "PT 일정 저장";
      scheduleSaveButton.disabled = false;
      overlay.hidden = false; document.body.classList.add("schedule-sheet-open");
    }
    cancelSchedule = async function (item) {
      if (!confirm(`${dateTime(item.start_at)} 일정을 취소하시겠어요?`)) return;
      try { await api(`/api/pt/schedules/${item.schedule_id}/cancel`, { method:"PATCH", body:"{}" }); await load(); } catch (error) { alert(error.message); }
    };
    function refreshCompleteItems() {
      const editors = [...document.querySelector("#ptCompleteItemList").children];
      editors.forEach((editor, index) => {
        editor.querySelector("[data-item-number]").textContent = `운동 ${index + 1}`;
        editor.querySelector("[data-up]").disabled = index === 0;
        editor.querySelector("[data-down]").disabled = index === editors.length - 1;
      });
      document.querySelector("#ptCompleteItemCount").textContent = `${editors.length}개`;
      document.querySelector("#ptCompleteEmptyGuide").hidden = editors.length > 0;
    }
    function clearCompleteMediaUrls() { completeMediaUrls.forEach(URL.revokeObjectURL); completeMediaUrls = []; }
    function completeItemEditor() {
      const editor = document.createElement("article");
      editor.className = "pt-complete-item";
      editor.innerHTML = `<header><strong data-item-number>운동</strong><div><button type="button" data-up aria-label="운동 순서 위로">↑</button><button type="button" data-down aria-label="운동 순서 아래로">↓</button><button type="button" data-remove aria-label="운동 삭제">삭제</button></div></header><label class="pt-exercise-name">운동명 <small>필수</small><input data-field="exercise_name" maxlength="100" required></label><div class="pt-complete-grid"><label>무게 <small>선택</small><span class="unit-input"><input data-field="weight_value" type="number" inputmode="decimal" min="0" step="0.1"><i>kg</i></span></label><label>횟수 <small>선택</small><span class="unit-input"><input data-field="repetitions" type="number" inputmode="numeric" min="1"><i>회</i></span></label><label>세트 <small>선택</small><span class="unit-input"><input data-field="completed_sets" type="number" inputmode="numeric" min="1"><i>세트</i></span></label><label>RPE <small>선택</small><input data-field="rpe" type="number" inputmode="numeric" min="1" max="10"></label></div><label>운동 시간 <small>선택</small><span class="unit-input"><input data-field="workout_minutes" type="number" inputmode="numeric" min="1"><i>분</i></span></label><label>운동 메모 <small>선택</small><textarea data-field="memo" rows="2"></textarea></label><section class="pt-media-picker"><div><strong>사진·영상</strong><span data-media-count>0개 선택</span></div><label class="pt-media-button">파일 선택<input data-media type="file" multiple accept="video/mp4,video/webm,image/jpeg,image/png,image/webp"></label><p>이미지 또는 짧은 영상 파일을 첨부할 수 있습니다.</p><div class="pt-media-preview" data-media-preview></div></section>`;
      const mediaInput = editor.querySelector("[data-media]");
      function renderMediaPreview() {
        const preview = editor.querySelector("[data-media-preview]"); preview.replaceChildren();
        editor.querySelector("[data-media-count]").textContent = `${mediaInput.files.length}개 선택`;
        [...mediaInput.files].forEach((file, fileIndex) => {
          const tile = document.createElement("div"), url = URL.createObjectURL(file); completeMediaUrls.push(url);
          tile.className = "pt-media-tile";
          const media = document.createElement(file.type.startsWith("video/") ? "video" : "img"); media.src = url; media.alt = ""; if (media.tagName === "VIDEO") media.muted = true;
          const name = document.createElement("span"); name.textContent = file.name;
          const remove = document.createElement("button"); remove.type = "button"; remove.textContent = "×"; remove.setAttribute("aria-label", `${file.name} 첨부 제거`); remove.addEventListener("click", () => { const transfer = new DataTransfer(); [...mediaInput.files].forEach((candidate, index) => { if (index !== fileIndex) transfer.items.add(candidate); }); mediaInput.files = transfer.files; renderMediaPreview(); });
          tile.append(media, name, remove); preview.append(tile);
        });
      }
      mediaInput.addEventListener("change", renderMediaPreview);
      editor.querySelector("[data-remove]").onclick = () => { editor.remove(); refreshCompleteItems(); };
      editor.querySelector("[data-up]").onclick = () => { if (editor.previousElementSibling) editor.parentNode.insertBefore(editor, editor.previousElementSibling); refreshCompleteItems(); };
      editor.querySelector("[data-down]").onclick = () => { if (editor.nextElementSibling) editor.parentNode.insertBefore(editor.nextElementSibling, editor); refreshCompleteItems(); };
      return editor;
    }
    function closeComplete(force = false) {
      if (busy) return;
      if (!force && completeDirty && !confirm("저장하지 않은 PT 운동 기록을 닫으시겠어요?")) return;
      completeOverlay.hidden = true;
      document.body.classList.remove("schedule-sheet-open");
      completeForm.reset();
      document.querySelector("#ptCompleteItemList").replaceChildren();
      clearCompleteMediaUrls(); refreshCompleteItems(); completeDirty = false;
      completingItem = null;
    }
    completeSchedule = async function (item) {
      completingItem = item;
      completeForm.reset();
      document.querySelector("#ptCompleteRecordTitle").value = "PT 수업";
      document.querySelector("#ptCompleteMemo").value = item.memo || "";
      document.querySelector("#ptCompleteItemList").replaceChildren();
      const duration = Math.max(0, Math.round((timeValue(item.end_at) - timeValue(item.start_at)) / 60000));
      document.querySelector("#ptCompleteSummary").innerHTML = `<div><span>회원</span><strong>${esc(item.member_name)} 회원</strong></div><div><span>PT 날짜</span><strong>${esc(dateTime(item.start_at))}</strong></div><div><span>수업 시간</span><strong>${esc(timeOnly(item.start_at))} ~ ${esc(timeOnly(item.end_at))}</strong></div><div><span>예정 시간</span><strong>${duration}분</strong></div>`;
      completeMessage.textContent = "";
      completeDirty = false; refreshCompleteItems();
      completeOverlay.hidden = false;
      document.body.classList.add("schedule-sheet-open");
    };
    const completeValue = (editor, name) => editor.querySelector(`[data-field="${name}"]`)?.value.trim() || null;
    const completeNumber = (editor, name) => completeValue(editor, name) === null ? null : Number(completeValue(editor, name));
    document.querySelector("#addPtCompleteItem").addEventListener("click", () => { const editor = completeItemEditor(); document.querySelector("#ptCompleteItemList").append(editor); refreshCompleteItems(); editor.scrollIntoView({ behavior:"smooth", block:"nearest" }); editor.querySelector('[data-field="exercise_name"]').focus(); });
    completeForm.addEventListener("input", () => { completeDirty = true; });
    completeForm.addEventListener("change", () => { completeDirty = true; });
    document.querySelector("#ptCompleteClose").addEventListener("click", () => closeComplete());
    document.querySelector("#ptCompleteBackdrop").addEventListener("click", () => closeComplete());
    document.querySelector("#ptCompleteCancel").addEventListener("click", () => closeComplete());
    completeForm.addEventListener("submit", async event => {
      event.preventDefault(); if (busy || !completingItem) return;
      const editors = [...document.querySelector("#ptCompleteItemList").children];
      const items = editors.map(editor => ({
        exercise_name: completeValue(editor, "exercise_name"), weight_value: completeNumber(editor, "weight_value"),
        weight_text: completeValue(editor, "weight_text"), repetitions: completeNumber(editor, "repetitions"),
        completed_sets: completeNumber(editor, "completed_sets"), rpe: completeNumber(editor, "rpe"),
        workout_minutes: completeNumber(editor, "workout_minutes"), memo: completeValue(editor, "memo"),
      }));
      busy = true; const saveButton = document.querySelector("#ptCompleteSave"); saveButton.disabled = true; saveButton.textContent = "저장 중..."; completeMessage.textContent = "";
      try {
        const result = await api(`/api/pt/schedules/${completingItem.schedule_id}/complete`, { method:"PATCH", body:JSON.stringify({
          title:document.querySelector("#ptCompleteRecordTitle").value.trim() || null,
          workout_part:document.querySelector("#ptCompletePart").value.trim() || null,
          memo:document.querySelector("#ptCompleteMemo").value.trim() || null, items,
        }) });
        const mediaErrors = [];
        for (let index = 0; index < editors.length; index++) {
          for (const file of editors[index].querySelector("[data-media]").files) {
            try {
              const mediaForm = new FormData(); mediaForm.append("file", file);
              await api(`/api/workout-sessions/items/${result.workout_item_ids[index]}/media`, { method:"POST", body:mediaForm });
            } catch (error) { mediaErrors.push(`운동 ${index + 1}: ${error.message}`); }
          }
        }
        busy = false; completeDirty = false; closeComplete(true); await load();
        if (mediaErrors.length) { stateBox.hidden = false; stateBox.textContent = `PT 완료 기록은 저장됐지만 일부 미디어를 업로드하지 못했습니다. ${mediaErrors.join(" / ")}`; }
      } catch (error) { completeMessage.textContent = error.message; busy = false; }
      finally { saveButton.disabled = false; saveButton.textContent = "PT 완료 저장"; }
    });
    document.querySelector("#openScheduleForm").addEventListener("click", () => openForm());
    document.querySelector("#scheduleFormClose").addEventListener("click", closeForm); document.querySelector("#scheduleFormBackdrop").addEventListener("click", closeForm);
    memberSelect.addEventListener("change", () => { selectedMemberId = Number(memberSelect.value) || null; document.querySelector("#openScheduleForm").disabled = !selectedMemberId; renderList(); });
    form.addEventListener("submit", async event => {
      event.preventDefault(); if (busy) return;
      const start = document.querySelector("#scheduleStart").value, end = document.querySelector("#scheduleEnd").value;
      if (!start || !end || new Date(start) >= new Date(end)) { message.textContent = "종료 시간은 시작 시간보다 늦어야 합니다."; return; }
      const payload = { start_at:start, end_at:end, memo:document.querySelector("#scheduleMemo").value.trim() || null };
      if (!editingId) payload.member_id = selectedMemberId;
      const saveLabel = scheduleSaveButton.textContent;
      busy = true;
      scheduleSaveButton.disabled = true;
      scheduleSaveButton.textContent = "저장 중...";
      scheduleSaveButton.setAttribute("aria-busy", "true");
      try { await api(editingId ? `/api/pt/schedules/${editingId}` : "/api/pt/schedules", { method:editingId ? "PATCH" : "POST", body:JSON.stringify(payload) }); busy = false; closeForm(); await load(); }
      catch (error) { message.textContent = error.message; busy = false; }
      finally {
        scheduleSaveButton.disabled = false;
        scheduleSaveButton.textContent = saveLabel;
        scheduleSaveButton.removeAttribute("aria-busy");
      }
    });
  }

  window.addEventListener("commonLayoutReady", async () => {
    user = currentUser(); if (!user) { location.href = "/login"; return; }
    if ((isTrainerPage && user.account_type !== "TRAINER") || (!isTrainerPage && user.account_type === "TRAINER")) { location.href = "/dashboard"; return; }
    await load();
  });
  window.addEventListener("keydown", event => { if (event.key === "Escape") { if (!document.querySelector("#ptCompleteOverlay")?.hidden) document.querySelector("#ptCompleteClose")?.click(); else if (!document.querySelector("#scheduleFormOverlay")?.hidden) document.querySelector("#scheduleFormClose")?.click(); } });
})();
