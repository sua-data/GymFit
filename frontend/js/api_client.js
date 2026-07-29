(function initializeGymfitApiClient() {
  "use strict";

  const TOKEN_KEY = "gymfitAccessToken";
  const USER_KEY = "gymfitUser";
  const rawFetch = window.fetch.bind(window);
  let redirecting = false;
  let isLoggingOut = false;
  let forbiddenNoticeVisible = false;
  let authCheckController = null;
  let authStateVersion = 0;
  const authPendingStyle = document.createElement("style");
  authPendingStyle.textContent =
    "html.auth-pending body{visibility:hidden!important}";
  document.head.appendChild(authPendingStyle);
  document.documentElement.classList.add("auth-pending");

  function markAuthPending() {
    document.documentElement.classList.add("auth-pending");
  }

  function markAuthReady() {
    document.documentElement.classList.remove("auth-pending");
  }

  function getAccessToken() {
    return sessionStorage.getItem(TOKEN_KEY);
  }

  function getStoredUser() {
    try {
      const value = JSON.parse(sessionStorage.getItem(USER_KEY) || "null");
      if (!value) return null;
      const userId = Number(value.user_id ?? value.userId);
      return Number.isInteger(userId) && userId > 0
        ? {
            ...value,
            user_id: userId,
            account_type: String(
              value.account_type ?? value.accountType ?? ""
            ).toUpperCase(),
          }
        : null;
    } catch {
      return null;
    }
  }

  function showForbidden(message = "접근 권한이 없습니다.") {
    if (forbiddenNoticeVisible) return;
    forbiddenNoticeVisible = true;
    window.alert(message);
    window.setTimeout(() => {
      forbiddenNoticeVisible = false;
    }, 1500);
  }

  function homeForRole(accountType) {
    if (accountType === "ADMIN") return "/admin/dashboard";
    if (accountType === "TRAINER") return "/trainer/members";
    return "/dashboard";
  }

  function requireRole(allowedRoles) {
    const user = getStoredUser();
    if (!getAccessToken() || !user) {
      redirectToLogin();
      return null;
    }
    const roles = (Array.isArray(allowedRoles) ? allowedRoles : [allowedRoles])
      .filter(Boolean)
      .map((role) => String(role).toUpperCase());
    if (roles.length && !roles.includes(user.account_type)) {
      showForbidden();
      window.location.replace(homeForRole(user.account_type));
      return null;
    }
    return user;
  }

  function clearAuthentication() {
    authStateVersion += 1;
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
    sessionStorage.removeItem("coachingSession");
    sessionStorage.removeItem("gymfitCoachingSessionId");
    sessionStorage.removeItem("gymfitCoachingPlan");
    sessionStorage.removeItem("gymfitCoachingRestSeconds");
    sessionStorage.removeItem("gymfitFreeCoachingSets");
    sessionStorage.removeItem("gymfitCoachingVoiceEnabled");
    sessionStorage.removeItem("gymfitCoachingRestPreset");
    sessionStorage.removeItem("googleSignup");
  }

  function redirectToLogin() {
    if (redirecting || window.location.pathname === "/login") return;
    redirecting = true;
    const next = `${window.location.pathname}${window.location.search}`;
    window.location.replace(`/login?next=${encodeURIComponent(next)}`);
  }

  function logout(event) {
    event?.preventDefault?.();
    event?.stopPropagation?.();
    if (isLoggingOut) return;
    isLoggingOut = true;
    markAuthPending();
    authCheckController?.abort();
    clearAuthentication();
    window.location.replace("/login");
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
    const requestToken = getAccessToken();
    if (requestToken && isApiRequest(input)) {
      headers.set("Authorization", `Bearer ${requestToken}`);
    }
    const response = await rawFetch(input, { ...init, headers });
    if (
      response.status === 401
      && isApiRequest(input)
      && (!requestToken || getAccessToken() === requestToken)
    ) {
      clearAuthentication();
      redirectToLogin();
    }
    if (response.status === 403 && isApiRequest(input)) {
      response.clone().json().catch(() => null).then((data) => {
        showForbidden(
          typeof data?.detail === "string"
            ? data.detail
            : "접근 권한이 없습니다."
        );
      });
    }
    return response;
  }

  async function requestJson(input, init = {}) {
    const headers = new Headers(init.headers);
    let body = init.body;
    if (
      body
      && !(body instanceof FormData)
      && !(body instanceof URLSearchParams)
    ) {
      if (!headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
      }
      if (typeof body !== "string") {
        body = JSON.stringify(body);
      }
    }
    const response = await authenticatedFetch(input, { ...init, headers, body });
    const data = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = Array.isArray(data?.detail)
        ? data.detail.map((item) => item?.msg).filter(Boolean).join(" ")
        : data?.detail;
      if (response.status === 403) {
        showForbidden(
          typeof detail === "string" && detail
            ? detail
            : "접근 권한이 없습니다."
        );
      }
      const error = new Error(
        typeof detail === "string" && detail
          ? detail
          : "요청을 처리하지 못했습니다."
      );
      error.status = response.status;
      error.data = data;
      throw error;
    }
    return data;
  }

  async function verifyGymfitAuth() {
    const token = getAccessToken();
    const version = authStateVersion;
    if (!token || isLoggingOut) return false;
    try {
      const response = await rawFetch("/api/auth/me", {
        cache: "no-store",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (
        isLoggingOut
        || version !== authStateVersion
        || getAccessToken() !== token
      ) {
        return false;
      }
      if (!response.ok) {
        if (getAccessToken() === token) clearAuthentication();
        return false;
      }
      const user = await response.json();
      if (
        isLoggingOut
        || version !== authStateVersion
        || getAccessToken() !== token
      ) {
        return false;
      }
      const previous = JSON.parse(sessionStorage.getItem(USER_KEY) || "{}");
      sessionStorage.setItem(USER_KEY, JSON.stringify({ ...previous, ...user }));
      return true;
    } catch {
      return false;
    }
  }

  window.fetch = authenticatedFetch;
  window.gymfitApi = {
    fetch: authenticatedFetch,
    request: requestJson,
    getAccessToken,
    getUser: getStoredUser,
    requireRole,
    showForbidden,
    setAccessToken(token) {
      if (typeof token !== "string" || !token) {
        throw new Error("유효한 액세스 토큰이 필요합니다.");
      }
      isLoggingOut = false;
      authStateVersion += 1;
      sessionStorage.setItem(TOKEN_KEY, token);
    },
    clearAuthentication,
    logout,
    isLoggingOut: () => isLoggingOut,
    verifyAuth: verifyGymfitAuth,
  };
  window.clearGymfitSession = clearAuthentication;
  window.logoutGymfit = logout;
  window.verifyGymfitAuth = verifyGymfitAuth;

  document.addEventListener("click", (event) => {
    const button = event.target.closest(
      "[data-gymfit-logout], #sideMenuLogoutButton"
    );
    if (button) logout(event);
  });

  window.addEventListener("pageshow", async (event) => {
    const token = getAccessToken();
    if (!token) {
      if (window.location.pathname === "/login") {
        markAuthReady();
      } else {
        markAuthPending();
        redirectToLogin();
      }
      return;
    }
    if (!event.persisted) return;

    markAuthPending();
    const isValid = await verifyGymfitAuth();
    if (!isValid) {
      redirectToLogin();
      return;
    }
    if (window.location.pathname === "/login") {
      const user = JSON.parse(sessionStorage.getItem(USER_KEY) || "{}");
      window.location.replace(
        user.account_type === "ADMIN"
          ? "/admin/dashboard"
          : user.account_type === "TRAINER"
            ? "/trainer/members"
            : "/dashboard"
      );
      return;
    }
    markAuthReady();
  });

  if (!getAccessToken()) {
    if (window.location.pathname === "/login") {
      markAuthReady();
    }
    redirectToLogin();
    return;
  }

  const checkedToken = getAccessToken();
  const checkedVersion = authStateVersion;
  authCheckController = new AbortController();
  authenticatedFetch("/api/auth/me", { signal: authCheckController.signal })
    .then(async (response) => {
      if (
        isLoggingOut
        || checkedVersion !== authStateVersion
        || getAccessToken() !== checkedToken
      ) {
        if (!isLoggingOut && window.location.pathname === "/login") {
          markAuthReady();
        }
        return;
      }
      if (!response.ok) {
        if (window.location.pathname === "/login") {
          markAuthReady();
        } else {
          markAuthPending();
          redirectToLogin();
        }
        return;
      }
      const user = await response.json();
      if (
        isLoggingOut
        || checkedVersion !== authStateVersion
        || getAccessToken() !== checkedToken
      ) {
        if (!isLoggingOut && window.location.pathname === "/login") {
          markAuthReady();
        }
        return;
      }
      const previous = JSON.parse(sessionStorage.getItem(USER_KEY) || "{}");
      sessionStorage.setItem(USER_KEY, JSON.stringify({ ...previous, ...user }));
      if (window.location.pathname === "/login") {
        window.location.replace(
          user.account_type === "ADMIN"
            ? "/admin/dashboard"
            : user.account_type === "TRAINER"
              ? "/trainer/members"
              : "/dashboard"
        );
        return;
      }
      markAuthReady();
      window.dispatchEvent(new CustomEvent("gymfitAuthReady", { detail: user }));
    })
    .catch(() => {
      if (isLoggingOut) return;
      if (window.location.pathname === "/login") {
        markAuthReady();
      } else {
        markAuthPending();
        redirectToLogin();
      }
    })
    .finally(() => {
      authCheckController = null;
    });
})();
