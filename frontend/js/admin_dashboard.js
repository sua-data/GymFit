(function () {
  const $ = (id) => document.getElementById(id);
  let user;
  try { user = JSON.parse(sessionStorage.getItem("gymfitUser") || "null"); } catch { user = null; }
  user = user && Number(user.user_id ?? user.userId) > 0 ? { ...user, user_id: Number(user.user_id ?? user.userId) } : null;
  if (!user) { location.replace("/login"); return; }
  if (String(user.account_type || "").toUpperCase() !== "ADMIN") { location.replace("/dashboard"); return; }

  async function api(url) {
    const response = await fetch(url, { headers: { "X-User-Id": String(user.user_id) } });
    const body = await response.json().catch(() => null);
    if (!response.ok) { const error = new Error(body?.detail || "관리자 정보를 불러오지 못했습니다."); error.status = response.status; throw error; }
    return body;
  }
  const formatDate = (value) => value ? new Intl.DateTimeFormat("ko-KR", { month: "2-digit", day: "2-digit" }).format(new Date(value)) : "";
  function renderRecent(container, empty, items, type) {
    container.replaceChildren(...items.slice(0, 5).map((item) => {
      const link = document.createElement("a");
      link.className = "admin-recent-item";
      link.href = type === "trainer"
        ? `/admin/trainers?status=PENDING#trainer-${item.user_id}`
        : `/admin/employments?status=PENDING`;
      const copy = document.createElement("div");
      const name = document.createElement("strong"); name.textContent = item.name || "이름 미등록";
      const gym = document.createElement("p"); gym.textContent = item.gym?.gym_name || "헬스장 미등록";
      copy.append(name, gym);
      const time = document.createElement("time"); time.textContent = formatDate(item.created_at);
      link.append(copy, time); return link;
    }));
    container.hidden = items.length === 0; empty.hidden = items.length > 0;
  }
  async function load() {
    $("dashboardLoading").hidden = false; $("dashboardError").hidden = true; $("dashboardContent").hidden = true;
    try {
      const [dashboard, employmentPending, employmentApproved, employmentRejected] = await Promise.all([
        api("/api/admin/dashboard"),
        api("/api/admin/employments?status=PENDING"),
        api("/api/admin/employments?status=APPROVED"),
        api("/api/admin/employments?status=REJECTED"),
      ]);
      const trainerCounts = dashboard.status_counts || {};
      $("trainerPendingCount").textContent = String(Number(trainerCounts.PENDING ?? dashboard.pending_count) || 0);
      $("trainerApprovedCount").textContent = String(Number(trainerCounts.APPROVED) || 0);
      $("trainerRejectedCount").textContent = String(Number(trainerCounts.REJECTED) || 0);
      $("employmentPendingCount").textContent = String(Number(employmentPending.total) || 0);
      $("employmentApprovedCount").textContent = String(Number(employmentApproved.total) || 0);
      $("employmentRejectedCount").textContent = String(Number(employmentRejected.total) || 0);
      renderRecent($("trainerRecentList"), $("trainerRecentEmpty"), dashboard.recent_applications || [], "trainer");
      renderRecent($("employmentRecentList"), $("employmentRecentEmpty"), employmentPending.items || [], "employment");
      $("dashboardContent").hidden = false;
    } catch (error) {
      if (error.status === 401) location.replace("/login");
      else if (error.status === 403) location.replace("/dashboard");
      else { $("dashboardErrorMessage").textContent = error.message; $("dashboardError").hidden = false; }
    } finally { $("dashboardLoading").hidden = true; }
  }
  $("dashboardRetry").addEventListener("click", load);
  $("adminLogout").addEventListener("click", () => { sessionStorage.clear(); location.replace("/login"); });
  load();
})();
