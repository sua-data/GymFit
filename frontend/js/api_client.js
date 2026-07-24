(function initializeGymfitApiClient() {
  "use strict";

  const TOKEN_KEY = "gymfitAccessToken";
  const USER_KEY = "gymfitUser";
  const rawFetch = window.fetch.bind(window);
  let redirecting = false;
  document.documentElement.style.visibility = "hidden";

  function getAccessToken() {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  function clearAuthentication() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    sessionStorage.removeItem("coachingSession");
    sessionStorage.removeItem("googleSignup");
  }

  function redirectToLogin() {
    if (redirecting || window.location.pathname === "/login") return;
    redirecting = true;
    const next = `${window.location.pathname}${window.location.search}`;
    window.location.replace(`/login?next=${encodeURIComponent(next)}`);
  }

  function isApiRequest(input) {
    const value = typeof input === "string" ? input : input?.url;
    if (!value) return false;
    const url = new URL(value, window.location.origin);
    return url.origin === window.location.origin && url.pathname.startsWith("/api/");
  }

  async function authenticatedFetch(input, init = {}) {
    const headers = new Headers(
      init.headers || (input instanceof Request ? input.headers : undefined)
    );
    const token = getAccessToken();
    if (token && isApiRequest(input)) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    const response = await rawFetch(input, { ...init, headers });
    if (response.status === 401 && isApiRequest(input)) {
      clearAuthentication();
      redirectToLogin();
    }
    return response;
  }

  async function requestJson(input, init = {}) {
    const headers = new Headers(init.headers);
    let body = init.body;
    if (
      body
      && !(body instanceof FormData)
      && typeof body !== "string"
      && !(body instanceof URLSearchParams)
    ) {
      headers.set("Content-Type", "application/json");
      body = JSON.stringify(body);
    }
    const response = await authenticatedFetch(input, { ...init, headers, body });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const error = new Error(
        typeof data?.detail === "string" ? data.detail : "요청을 처리하지 못했습니다."
      );
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  window.fetch = authenticatedFetch;
  window.gymfitApi = {
    fetch: authenticatedFetch,
    request: requestJson,
    getAccessToken,
    setAccessToken(token) {
      if (typeof token !== "string" || !token) {
        throw new Error("유효한 액세스 토큰이 필요합니다.");
      }
      sessionStorage.setItem(TOKEN_KEY, token);
    },
    clearAuthentication,
    logout() {
      clearAuthentication();
      window.location.replace("/login");
    },
  };

  if (!getAccessToken()) {
    if (window.location.pathname === "/login") {
      document.documentElement.style.visibility = "";
    }
    redirectToLogin();
    return;
  }

  authenticatedFetch("/api/auth/me")
    .then(async (response) => {
      if (!response.ok) {
        document.documentElement.style.visibility = "";
        return;
      }
      const user = await response.json();
      const previous = JSON.parse(sessionStorage.getItem(USER_KEY) || "{}");
      sessionStorage.setItem(USER_KEY, JSON.stringify({ ...previous, ...user }));
      if (window.location.pathname === "/login") {
        window.location.replace(
          user.account_type === "ADMIN" ? "/admin/dashboard" : "/dashboard"
        );
        return;
      }
      document.documentElement.style.visibility = "";
      window.dispatchEvent(new CustomEvent("gymfitAuthReady", { detail: user }));
    })
    .catch(() => {
      // 네트워크 장애는 로그아웃으로 오인하지 않는다. 개별 화면이 오류를 표시한다.
      document.documentElement.style.visibility = "";
    });
})();
