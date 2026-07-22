(function () {
  const loading = document.querySelector("#notificationsLoading");
  const errorView = document.querySelector("#notificationsError");
  const errorMessage = document.querySelector("#notificationsErrorMessage");
  const emptyView = document.querySelector("#notificationsEmpty");
  const list = document.querySelector("#notificationList");
  const readAllButton = document.querySelector("#readAllButton");
  let user = null;

  function getSessionUser() {
    try {
      const value = JSON.parse(sessionStorage.getItem("gymfitUser") || "null");
      const userId = Number(value?.user_id ?? value?.userId);
      return Number.isInteger(userId) && userId > 0 ? { ...value, user_id: userId } : null;
    } catch { return null; }
  }

  async function requestJson(url, options = {}) {
    const response = await fetch(url, { ...options, headers: { "X-User-Id": String(user.user_id), ...(options.headers || {}) } });
    const body = await response.json().catch(() => null);
    if (!response.ok) throw new Error(body?.detail || "알림 요청을 처리하지 못했습니다.");
    return body;
  }

  function formatTime(value) {
    if (!value) return "";
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return new Intl.DateTimeFormat("ko-KR", { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }).format(date);
  }

  function typeLabel(type) {
    if (type?.startsWith("PT_")) return "PT";
    if (type === "WELCOME") return "HI";
    if (type === "WORKOUT_PLAN") return "운동";
    return "GYM";
  }

  async function openNotification(item) {
    try {
      if (!item.is_read) await requestJson(`/api/notifications/${item.notification_id}/read`, { method: "PATCH" });
      window.dispatchEvent(new CustomEvent("gymfitNotificationsUpdated"));
      if (item.target_url) window.location.href = item.target_url;
      else await loadNotifications();
    } catch (error) {
      errorMessage.textContent = error.message;
      errorView.hidden = false;
    }
  }

  function render(items) {
    list.replaceChildren();
    emptyView.hidden = items.length !== 0;
    list.hidden = items.length === 0;
    readAllButton.disabled = !items.some((item) => !item.is_read);
    items.forEach((item) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = `notification-item${item.is_read ? "" : " unread"}`;
      const head = document.createElement("div");
      head.className = "notification-head";
      const icon = document.createElement("span");
      icon.className = "notification-icon";
      icon.textContent = typeLabel(item.notification_type);
      const title = document.createElement("strong");
      title.textContent = item.title || "알림";
      head.append(icon, title);
      if (!item.is_read) {
        const dot = document.createElement("span");
        dot.className = "unread-dot";
        head.appendChild(dot);
      }
      const message = document.createElement("p");
      message.textContent = item.message || "";
      const time = document.createElement("time");
      time.textContent = formatTime(item.created_at);
      button.append(head, message, time);
      button.addEventListener("click", () => openNotification(item));
      list.appendChild(button);
    });
  }

  async function loadNotifications() {
    errorView.hidden = true;
    try {
      const data = await requestJson("/api/notifications");
      render(Array.isArray(data.items) ? data.items : []);
    } catch (error) {
      errorMessage.textContent = error.message;
      errorView.hidden = false;
    } finally { loading.hidden = true; }
  }

  readAllButton.addEventListener("click", async () => {
    readAllButton.disabled = true;
    try {
      await requestJson("/api/notifications/read-all", { method: "PATCH" });
      window.dispatchEvent(new CustomEvent("gymfitNotificationsUpdated"));
      await loadNotifications();
    } catch (error) {
      errorMessage.textContent = error.message;
      errorView.hidden = false;
    }
  });
  document.querySelector("#notificationsRetryButton").addEventListener("click", loadNotifications);
  user = getSessionUser();
  if (!user) window.location.replace("/login");
  else loadNotifications();
})();
