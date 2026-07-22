(function () {
  const loading = document.querySelector("#ptLoading");
  const errorView = document.querySelector("#ptError");
  const errorMessage = document.querySelector("#ptErrorMessage");
  const trainerView = document.querySelector("#trainerView");
  const memberView = document.querySelector("#memberView");
  let sessionUser = null;
  let busy = false;

  function getSessionUser() {
    try {
      const user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null");
      const userId = Number(user?.user_id ?? user?.userId);
      return Number.isInteger(userId) && userId > 0 ? { ...user, user_id: userId } : null;
    } catch {
      return null;
    }
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        "X-User-Id": String(sessionUser.user_id),
        ...(options.headers || {}),
      },
    });
    if (response.status === 204) return null;
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.detail || "요청을 처리하지 못했습니다.");
    return body;
  }

  function empty(message) {
    const element = document.createElement("p");
    element.className = "empty";
    element.textContent = message;
    return element;
  }

  function makeItem(title, lines, actions = [], statusText = "") {
    const item = document.createElement("article");
    item.className = "pt-item";
    const strong = document.createElement("strong");
    strong.textContent = title || "이름 없음";
    item.appendChild(strong);
    lines.filter(Boolean).forEach((line) => {
      const paragraph = document.createElement("p");
      paragraph.textContent = line;
      item.appendChild(paragraph);
    });
    if (statusText) {
      const badge = document.createElement("span");
      badge.className = "status-badge";
      badge.textContent = statusText;
      item.appendChild(badge);
    }
    if (actions.length) {
      const actionRow = document.createElement("div");
      actionRow.className = "pt-actions";
      actions.forEach((action) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `pt-action ${action.className || ""}`.trim();
        button.textContent = action.label;
        button.disabled = Boolean(action.disabled);
        button.addEventListener("click", action.onClick);
        actionRow.appendChild(button);
      });
      item.appendChild(actionRow);
    }
    return item;
  }

  async function refreshSessionUser() {
    if (typeof window.refreshGymfitCurrentUser === "function") {
      const refreshedUser = await window.refreshGymfitCurrentUser(true);
      if (refreshedUser) sessionUser = refreshedUser;
      return;
    }
    const user = await requestJson(`/api/users/${sessionUser.user_id}`);
    sessionUser = typeof window.updateGymfitStoredUser === "function"
      ? window.updateGymfitStoredUser(user)
      : { ...sessionUser, ...user };
    sessionStorage.setItem("gymfitUser", JSON.stringify(sessionUser));
    window.dispatchEvent(new CustomEvent("gymfitUserUpdated", { detail: sessionUser }));
  }

  async function runAction(url, method = "PATCH", body, successMessage = "") {
    if (busy) return;
    busy = true;
    try {
      await requestJson(url, { method, body: body ? JSON.stringify(body) : undefined });
      await refreshSessionUser();
      window.dispatchEvent(new CustomEvent("gymfitNotificationsUpdated"));
      await loadData();
      if (method === "DELETE") {
        document.querySelector("#memberSearchForm")?.requestSubmit();
      }
      if (successMessage) window.alert(successMessage);
    } catch (error) {
      window.alert(error.message);
    } finally {
      busy = false;
    }
  }

  function renderRelationships(container, items, type) {
    container.replaceChildren();
    if (!items.length) {
      const message = type === "active"
        ? "연결된 회원이 없습니다."
        : type === "received"
          ? "받은 PT 연결 요청이 없습니다."
          : "요청이 없습니다.";
      container.appendChild(empty(message));
      return;
    }
    items.forEach((item) => {
      const isTrainerView = sessionUser.account_type === "TRAINER";
      const title = isTrainerView ? item.member_name : item.trainer_name;
      const email = isTrainerView ? item.member_email : item.trainer_email;
      const gymName = type === "sent"
        ? item.member_gym_name
        : type === "received"
          ? item.trainer_gym_name
          : item.gym_name;
      const careerYears = type === "received"
        ? item.trainer_career_years
        : type === "active" && !isTrainerView
          ? item.career_years
          : null;
      const lines = [
        email,
        gymName ? `헬스장 · ${gymName}` : null,
        careerYears != null ? `경력 · ${careerYears}년` : null,
      ];
      const actions = [];
      if (type === "received") {
        actions.push(
          { label: "수락", onClick: () => runAction(`/api/pt/requests/${item.trainer_member_id}/accept`) },
          { label: "거절", className: "secondary", onClick: () => runAction(`/api/pt/requests/${item.trainer_member_id}/reject`) },
        );
      } else if (type === "sent") {
        actions.push({
          label: "요청 취소",
          className: "danger",
          onClick: async (event) => {
            if (busy) return;
            if (window.confirm(`${item.member_name}님에게 보낸 PT 연결 요청을 취소하시겠습니까?`)) {
              const button = event.currentTarget;
              button.disabled = true;
              button.textContent = "취소 중...";
              await runAction(
                `/api/pt/requests/${item.trainer_member_id}`,
                "DELETE",
                undefined,
                "PT 연결 요청을 취소했습니다.",
              );
              if (button.isConnected) {
                button.disabled = false;
                button.textContent = "요청 취소";
              }
            }
          },
        });
      } else if (type === "active") {
        actions.push({ label: "연결 종료", className: "danger", onClick: () => {
          if (window.confirm("PT 연결을 종료하시겠어요?")) runAction(`/api/pt/relationships/${item.trainer_member_id}/end`);
        }});
      }
      container.appendChild(makeItem(title, lines, actions, item.status === "PENDING" ? "요청 중" : "연결됨"));
    });
  }

  async function loadTrainerData() {
    const [sent, active] = await Promise.all([
      requestJson("/api/pt/requests/sent"),
      requestJson("/api/pt/my-members"),
    ]);
    renderRelationships(document.querySelector("#sentRequestList"), sent.items || [], "sent");
    renderRelationships(document.querySelector("#activeMemberList"), active.items || [], "active");
  }

  async function loadMemberData() {
    const [received, trainer] = await Promise.all([
      requestJson("/api/pt/requests/received"),
      requestJson("/api/pt/my-trainer"),
    ]);
    renderRelationships(document.querySelector("#receivedRequestList"), received.items || [], "received");
    const trainerContainer = document.querySelector("#myTrainerCard");
    renderRelationships(trainerContainer, trainer.item ? [trainer.item] : [], "active");
    if (!trainer.item) trainerContainer.replaceChildren(empty("현재 연결된 트레이너가 없습니다."));
  }

  async function loadData() {
    errorView.hidden = true;
    try {
      if (sessionUser.account_type === "TRAINER") await loadTrainerData();
      else await loadMemberData();
      trainerView.hidden = sessionUser.account_type !== "TRAINER";
      memberView.hidden = sessionUser.account_type === "TRAINER";
    } catch (error) {
      errorMessage.textContent = error.message;
      errorView.hidden = false;
    } finally {
      loading.hidden = true;
    }
  }

  document.querySelector("#memberSearchForm").addEventListener("submit", async (event) => {
    event.preventDefault();
    const query = document.querySelector("#memberEmailInput").value.trim();
    const message = document.querySelector("#memberSearchMessage");
    const results = document.querySelector("#memberSearchResults");
    if (query.length < 2) return;
    try {
      const data = await requestJson(`/api/pt/members/search?email=${encodeURIComponent(query)}`);
      results.replaceChildren();
      if (!data.items?.length) results.appendChild(empty("검색 결과가 없습니다."));
      (data.items || []).forEach((member) => {
        const pending = member.relationship_status === "PENDING";
        const active = member.relationship_status === "ACTIVE";
        results.appendChild(makeItem(member.name, [member.email], [{
          label: pending ? "요청 중" : active ? "연결됨" : "연결 요청",
          disabled: pending || active,
          onClick: () => runAction("/api/pt/requests", "POST", { member_id: member.user_id }),
        }], pending ? "요청 중" : active ? "연결됨" : ""));
      });
      message.textContent = `${data.items?.length || 0}명의 회원을 찾았습니다.`;
    } catch (error) {
      message.textContent = error.message;
    }
  });

  document.querySelector("#ptRetryButton").addEventListener("click", loadData);
  sessionUser = getSessionUser();
  if (!sessionUser) window.location.replace("/login");
  else if (
    window.location.pathname === "/pt/requests"
    && sessionUser.account_type === "TRAINER"
  ) {
    window.location.replace("/trainer/members");
  } else loadData();
})();
