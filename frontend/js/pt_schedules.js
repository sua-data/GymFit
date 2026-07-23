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
    const response = await fetch(url, { ...options, headers: { ...(options.body ? { "Content-Type": "application/json" } : {}), "X-User-Id": String(user.user_id) } });
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

  function renderList() {
    const items = filteredItems();
    list.replaceChildren(); list.hidden = !items.length; stateBox.hidden = !!items.length;
    if (!items.length) { stateBox.textContent = selectedMemberId || !isTrainerPage ? "선택한 조건에 해당하는 PT 일정이 없습니다." : "회원을 선택해 주세요."; return; }
    items.forEach(item => {
      const card = document.createElement("article");
      card.id = `schedule-${item.schedule_id}`;
      const cardState = item.status === "CANCELLED" ? "cancelled" : item.status === "COMPLETED" ? "completed" : isPast(item) ? "past incomplete" : "";
      card.className = `schedule-card ${cardState}`;
      const heading = makeText("div", "", "schedule-card-heading");
      heading.append(makeText("h3", `${dateTime(item.start_at)} ~ ${timeOnly(item.end_at)}`), makeText("span", statusText(item), "schedule-badge"));
      card.append(heading, makeText("p", `${isTrainerPage ? item.member_name + " 회원" : item.trainer_name + " 트레이너"}${item.location ? ` · ${item.location}` : ""}`));
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
    content.append(makeText("strong", dateTime(item.start_at)), makeText("p", `${item.trainer_name} 트레이너 · ${timeOnly(item.start_at)} ~ ${timeOnly(item.end_at)}${item.location ? `\n${item.location}` : ""}${item.memo ? `\n${item.memo}` : ""}`));
    box.append(content);
  }

  function renderMembers() {
    memberSelect.innerHTML = '<option value="">회원 선택</option>';
    members.forEach(member => memberSelect.add(new Option(`${member.member_name} (${member.member_email})`, member.member_id)));
    if (selectedMemberId) memberSelect.value = String(selectedMemberId);
    document.querySelector("#openScheduleForm").disabled = !selectedMemberId;
  }

  async function load() {
    stateBox.hidden = false; list.hidden = true; stateBox.textContent = "일정을 불러오고 있습니다.";
    try {
      if (isTrainerPage) {
        const [memberData, scheduleData] = await Promise.all([api("/api/pt/my-members"), api("/api/pt/schedules/trainer")]);
        members = memberData.items || []; schedules = scheduleData.items || [];
        if (!members.some(item => Number(item.member_id) === selectedMemberId)) selectedMemberId = members[0] ? Number(members[0].member_id) : null;
        renderMembers();
      } else schedules = (await api("/api/pt/schedules/member")).items || [];
      renderNext(); renderList();
    } catch (error) { stateBox.hidden = false; stateBox.textContent = error.message; }
  }

  tabs.addEventListener("click", event => {
    const button = event.target.closest("button[data-filter]"); if (!button) return;
    filter = button.dataset.filter; tabs.querySelectorAll("button").forEach(item => item.classList.toggle("active", item === button)); renderList();
  });

  if (isTrainerPage) {
    const overlay = document.querySelector("#scheduleFormOverlay"), form = document.querySelector("#scheduleForm"), message = document.querySelector("#scheduleFormMessage");
    const localInput = value => { const date = new Date(value); date.setMinutes(date.getMinutes() - date.getTimezoneOffset()); return date.toISOString().slice(0,16); };
    function closeForm() { if (busy) return; overlay.hidden = true; document.body.classList.remove("schedule-sheet-open"); form.reset(); editingId = null; message.textContent = ""; }
    function openForm(item = null) {
      editingId = item?.schedule_id || null; form.reset(); message.textContent = "";
      const base = item ? new Date(item.start_at) : new Date(Date.now() + 3600000); base.setMinutes(Math.ceil(base.getMinutes()/30)*30,0,0);
      document.querySelector("#scheduleStart").value = item ? localInput(item.start_at) : localInput(base);
      document.querySelector("#scheduleEnd").value = item ? localInput(item.end_at) : localInput(new Date(base.getTime()+3600000));
      document.querySelector("#scheduleLocation").value = item?.location || ""; document.querySelector("#scheduleMemo").value = item?.memo || "";
      document.querySelector("#scheduleFormTitle").textContent = item ? "PT 일정 수정" : "새 PT 일정";
      document.querySelector("#scheduleSave").textContent = item ? "수정 완료" : "일정 등록";
      overlay.hidden = false; document.body.classList.add("schedule-sheet-open");
    }
    cancelSchedule = async function (item) {
      if (!confirm(`${dateTime(item.start_at)} 일정을 취소하시겠어요?`)) return;
      try { await api(`/api/pt/schedules/${item.schedule_id}/cancel`, { method:"PATCH", body:"{}" }); await load(); } catch (error) { alert(error.message); }
    };
    completeSchedule = async function (item) {
      if (!confirm(`${dateTime(item.start_at)} PT를 완료 처리하시겠어요?`)) return;
      try {
        await api(`/api/pt/schedules/${item.schedule_id}/complete`, { method:"PATCH", body:"{}" });
        await load();
      } catch (error) {
        alert(error.message);
      }
    };
    document.querySelector("#openScheduleForm").addEventListener("click", () => openForm());
    document.querySelector("#scheduleFormClose").addEventListener("click", closeForm); document.querySelector("#scheduleFormBackdrop").addEventListener("click", closeForm);
    memberSelect.addEventListener("change", () => { selectedMemberId = Number(memberSelect.value) || null; document.querySelector("#openScheduleForm").disabled = !selectedMemberId; renderList(); });
    form.addEventListener("submit", async event => {
      event.preventDefault(); if (busy) return;
      const start = document.querySelector("#scheduleStart").value, end = document.querySelector("#scheduleEnd").value;
      if (!start || !end || new Date(start) >= new Date(end)) { message.textContent = "종료 시간은 시작 시간보다 늦어야 합니다."; return; }
      const payload = { start_at:start, end_at:end, location:document.querySelector("#scheduleLocation").value.trim() || null, memo:document.querySelector("#scheduleMemo").value.trim() || null };
      if (!editingId) payload.member_id = selectedMemberId;
      busy = true; document.querySelector("#scheduleSave").disabled = true;
      try { await api(editingId ? `/api/pt/schedules/${editingId}` : "/api/pt/schedules", { method:editingId ? "PATCH" : "POST", body:JSON.stringify(payload) }); busy = false; closeForm(); await load(); }
      catch (error) { message.textContent = error.message; busy = false; }
      finally { document.querySelector("#scheduleSave").disabled = false; }
    });
  }

  window.addEventListener("commonLayoutReady", async () => {
    user = currentUser(); if (!user) { location.href = "/login"; return; }
    if ((isTrainerPage && user.account_type !== "TRAINER") || (!isTrainerPage && user.account_type === "TRAINER")) { location.href = "/dashboard"; return; }
    await load();
  });
})();
