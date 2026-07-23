(function () {
  const byId = (id) => document.getElementById(id);
  let user;
  try { user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null"); } catch { user = null; }
  user = user && Number(user.user_id ?? user.userId) > 0
    ? { ...user, user_id: Number(user.user_id ?? user.userId) } : null;
  if (!user) { location.replace("/login"); return; }
  if (String(user.account_type || "").toUpperCase() !== "ADMIN") { location.replace("/dashboard"); return; }

  const formatDate = (value) => value
    ? new Intl.DateTimeFormat("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" }).format(new Date(value))
    : "";

  async function load() {
    byId("dashboardLoading").hidden = false;
    byId("dashboardError").hidden = true;
    byId("dashboardContent").hidden = true;
    try {
      const response = await fetch("/api/admin/dashboard", { headers: { "X-User-Id": String(user.user_id) } });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const error = new Error(data?.detail || "관리자 정보를 불러오지 못했습니다.");
        error.status = response.status;
        throw error;
      }
      const counts = data.status_counts || {};
      byId("pendingCount").textContent = String(Number(counts.PENDING ?? data.pending_count) || 0);
      byId("approvedCount").textContent = String(Number(counts.APPROVED) || 0);
      byId("rejectedCount").textContent = String(Number(counts.REJECTED) || 0);
      const list = byId("recentList");
      const items = Array.isArray(data.recent_applications) ? data.recent_applications : [];
      list.replaceChildren(...items.map((trainer) => {
        const link = document.createElement("a");
        link.className = "recent-item";
        link.href = `/admin/trainers?status=PENDING#trainer-${trainer.user_id}`;
        const copy = document.createElement("div");
        const name = document.createElement("strong");
        name.textContent = trainer.name || "이름 없음";
        const gym = document.createElement("p");
        gym.textContent = trainer.gym?.gym_name || "등록 헬스장 없음";
        copy.append(name, gym);
        const time = document.createElement("time");
        time.textContent = formatDate(trainer.created_at);
        link.append(copy, time);
        return link;
      }));
      byId("recentEmpty").hidden = items.length > 0;
      byId("dashboardContent").hidden = false;
    } catch (error) {
      if (error.status === 401) location.replace("/login");
      else if (error.status === 403) location.replace("/dashboard");
      else {
        byId("dashboardErrorMessage").textContent = error.message;
        byId("dashboardError").hidden = false;
      }
    } finally {
      byId("dashboardLoading").hidden = true;
    }
  }
  byId("dashboardRetry").addEventListener("click", load);
  byId("adminLogout").addEventListener("click", () => { sessionStorage.clear(); location.replace("/login"); });
  load();
})();
