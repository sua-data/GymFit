const memberServiceMenuItems = [
  {
    label: "내 헬스장",
    path: "/my-gym"
  },
  {
    label: "헬스장 머신",
    path: "/machines"
  }
];

const trainerServiceMenuItems = [
  {
    label: "소속 헬스장",
    path: "/my-gym"
  },
  {
    label: "보유 머신 관리",
    path: "/machines"
  },
  {
    label: "자격증 관리",
    path: "/trainer/certifications"
  }
];

const ptMemberMenuItems = [
  {
    label: "PT 숙제",
    path: "/pt/assignments"
  },
  {
    label: "트레이너 피드백",
    path: "/pt/feedback"
  },
  {
    label: "PT 일정",
    path: "/pt/schedules"
  }
];

const trainerMenuItems = [
  {
    label: "담당 회원",
    path: "/trainer/members"
  },
  {
    label: "PT 숙제 관리",
    path: "/trainer/assignments"
  },
  {
    label: "PT 일정 관리",
    path: "/trainer/schedules"
  }
];

const adminMenuItems = [
  {
    label: "관리자 홈",
    path: "/admin/dashboard"
  },
  {
    label: "트레이너 승인",
    path: "/admin/trainers"
  }
];


function getUserRoleLabel(user) {
  const accountType = String(
    user?.account_type
    ?? user?.accountType
    ?? ""
  ).toUpperCase();
  const hasActiveTrainer =
    user?.has_active_trainer === true
    || user?.hasActiveTrainer === true;

  if (accountType === "TRAINER") {
    return "트레이너";
  }
  if (accountType === "ADMIN") {
    return "관리자";
  }
  if (accountType === "MEMBER" && hasActiveTrainer) {
    return "PT 회원";
  }
  return "개인 운동자";
}

window.getUserRoleLabel = getUserRoleLabel;

const trainerRestrictedMemberPaths = new Set([
  "/dashboard",
  "/routine",
  "/coaching",
  "/records",
  "/pt",
  "/pt/assignments",
  "/pt/feedback",
  "/pt/schedules",
]);

function redirectForAccountType(user) {
  const accountType = String(
    user?.account_type ?? user?.accountType ?? ""
  ).toUpperCase();
  const path = window.location.pathname;
  if (accountType === "ADMIN" && !path.startsWith("/admin/")) {
    window.location.replace("/admin/dashboard");
    return true;
  }
  if (accountType === "TRAINER" && trainerRestrictedMemberPaths.has(path)) {
    window.location.replace("/trainer/members");
    return true;
  }
  return false;
}

window.addEventListener("pageshow", () => {
  const currentUser = getLoginUser();
  if (redirectForAccountType(currentUser)) {
    return;
  }
  const withdrawn = sessionStorage.getItem("gymfitAccountWithdrawn") === "1";
  if (
    withdrawn
    && !getLoginUser()
    && !["/", "/login", "/signup", "/signup/type", "/find-password"].includes(
      window.location.pathname
    )
  ) {
    window.location.replace("/login");
  }
});


function updateGymfitStoredUser(profile) {
  if (window.gymfitApi?.isLoggingOut?.()) {
    return null;
  }
  const previousUser = getLoginUser() || {};
  const hasServerTrainerState = Object.prototype.hasOwnProperty.call(
    profile || {},
    "has_active_trainer"
  );
  const nextUser = {
    ...previousUser,
    ...(profile || {}),
  };

  if (hasServerTrainerState) {
    nextUser.has_active_trainer = profile.has_active_trainer === true;
  } else if (!Object.prototype.hasOwnProperty.call(nextUser, "has_active_trainer")) {
    nextUser.has_active_trainer = nextUser.hasActiveTrainer === true;
  }

  delete nextUser.hasActiveTrainer;
  sessionStorage.setItem("gymfitUser", JSON.stringify(nextUser));
  sessionStorage.removeItem("gymfitAccountWithdrawn");
  return nextUser;
}


let currentUserRefreshPromise = null;
let currentUserRefreshCompleted = false;

async function refreshGymfitCurrentUser(force = false) {
  if (currentUserRefreshCompleted && !force) {
    return getLoginUser();
  }
  if (currentUserRefreshPromise) {
    return currentUserRefreshPromise;
  }

  const storedUser = getLoginUser();
  const userId = Number(storedUser?.user_id ?? storedUser?.userId);
  if (!Number.isInteger(userId) || userId <= 0) {
    return null;
  }

  currentUserRefreshPromise = (async () => {
    const response = await window.gymfitApi.fetch(`/api/users/${userId}`);
    const profile = await response.json().catch(() => null);
    if (window.gymfitApi?.isLoggingOut?.()) {
      return null;
    }
    if (!response.ok) {
      throw new Error(
        typeof profile?.detail === "string"
          ? profile.detail
          : "사용자 정보를 갱신하지 못했습니다."
      );
    }

    const nextUser = updateGymfitStoredUser(profile);
    currentUserRefreshCompleted = true;
    window.dispatchEvent(new CustomEvent("gymfitUserUpdated", {
      detail: nextUser,
    }));
    return nextUser;
  })().finally(() => {
    currentUserRefreshPromise = null;
  });

  return currentUserRefreshPromise;
}


window.updateGymfitStoredUser = updateGymfitStoredUser;
window.refreshGymfitCurrentUser = refreshGymfitCurrentUser;


function getLoginUser() {
  return window.gymfitApi?.getUser?.() || null;
}


async function loadCommonComponent(
  containerSelector,
  componentPath
) {
  const container =
    document.querySelector(
      containerSelector
    );

  if (!container) {
    return;
  }

  const response =
    await fetch(componentPath);

  if (!response.ok) {
    throw new Error(
      `${componentPath} 로딩 실패`
    );
  }

  container.innerHTML =
    await response.text();
}


function createMenuSection(
  title,
  items
) {
  const section =
    document.createElement(
      "section"
    );

  section.className =
    "side-menu-section";

  const sectionTitle =
    document.createElement(
      "span"
    );

  sectionTitle.className =
    "side-menu-section-title";

  sectionTitle.textContent =
    title;

  section.appendChild(
    sectionTitle
  );

  items.forEach((item) => {
    const menuItem = document.createElement(
      item.path ? "a" : "button"
    );

    menuItem.className =
      "side-menu-item";

    if (item.path) {
      menuItem.href = item.path;
      const itemPath = new URL(item.path, window.location.origin).pathname;
      const currentPath = window.location.pathname;
      if (
        itemPath === currentPath
        || (itemPath !== "/" && currentPath.startsWith(`${itemPath}/`))
      ) {
        menuItem.setAttribute("aria-current", "page");
      }
    } else {
      menuItem.type = "button";
      menuItem.addEventListener("click", () => {
        window.alert("준비 중인 기능입니다.");
      });
    }

    const label =
      document.createElement("span");

    label.className = "side-menu-item__label";
    label.textContent =
      item.label;

    const arrow =
      document.createElement("span");

    const badgeCount = Math.max(
      0,
      Number(item.badgeCount) || 0
    );

    arrow.className = badgeCount > 0
      ? "side-menu-count"
      : item.path
        ? ""
        : "side-menu-coming";

    arrow.textContent = badgeCount > 0
      ? String(badgeCount)
      : item.path
        ? "›"
        : "준비 중";

    menuItem.append(
      label,
      arrow
    );

    section.appendChild(menuItem);
  });

  return section;
}


function renderSideMenu() {
  const user =
    getLoginUser();

  if (!user) {
    return;
  }

  const userName =
    document.querySelector(
      "#sideMenuUserName"
    );

  const userType =
    document.querySelector(
      "#sideMenuUserType"
    );

  const menuList =
    document.querySelector(
      "#sideMenuList"
    );

  if (
    !userName
    || !userType
    || !menuList
  ) {
    return;
  }

  menuList.innerHTML = "";

  const normalizedName = String(user.name || "사용자")
    .trim()
    .replace(/(?:님)+$/u, "")
    .trim();
  userName.textContent = `${normalizedName || "사용자"}님`;

  const accountType = String(
    user.account_type
    ?? user.accountType
    ?? ""
  ).toUpperCase();
  const isTrainer = accountType === "TRAINER";
  const isAdmin = accountType === "ADMIN";

  const hasActiveTrainer =
    user.has_active_trainer === true
    || user.hasActiveTrainer === true;

  userType.textContent = getUserRoleLabel(user);

  const appendLogoutButton = () => {
    const logoutButton = document.createElement("button");
    logoutButton.type = "button";
    logoutButton.className = "side-menu-item";
    logoutButton.classList.add("side-menu-logout");
    logoutButton.dataset.gymfitLogout = "true";
    logoutButton.id = "sideMenuLogoutButton";
    const label = document.createElement("span");
    label.className = "side-menu-item__label";
    label.textContent = "로그아웃";
    const icon = document.createElementNS(
      "http://www.w3.org/2000/svg",
      "svg"
    );
    icon.classList.add("side-menu-logout-icon");
    icon.setAttribute("viewBox", "0 0 24 24");
    icon.setAttribute("aria-hidden", "true");
    icon.innerHTML = [
      '<path d="M10 17l5-5-5-5"></path>',
      '<path d="M15 12H3"></path>',
      '<path d="M13 3h6a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2h-6"></path>',
    ].join("");
    logoutButton.append(label, icon);
    menuList.appendChild(logoutButton);
  };

  if (isAdmin) {
    menuList.appendChild(
      createMenuSection(
        "관리자",
        adminMenuItems
      )
    );
    appendLogoutButton();
    return;
  }

  menuList.appendChild(
    createMenuSection(
      "운동 관리",
      isTrainer
        ? trainerServiceMenuItems
        : [
            ...memberServiceMenuItems,
            ...(!hasActiveTrainer ? [{
              label: "PT 연결 요청",
              path: "/pt/requests",
              badgeCount: user.pending_pt_request_count,
            }] : []),
          ]
    )
  );

  if (hasActiveTrainer && !isTrainer) {
    menuList.appendChild(
      createMenuSection(
        "PT 관리",
        ptMemberMenuItems
      )
    );
  }

  if (isTrainer) {
    menuList.appendChild(
      createMenuSection(
        "트레이너 관리",
        trainerMenuItems
      )
    );
  }

  appendLogoutButton();
}


function setupSideMenu() {
  const openButton =
    document.querySelector(
      "#menuButton"
    );

  const closeButton =
    document.querySelector(
      "#sideMenuCloseButton"
    );

  const overlay =
    document.querySelector(
      "#sideMenuOverlay"
    );

  const menu =
    document.querySelector(
      "#sideMenu"
    );

  if (
    !openButton
    || !closeButton
    || !overlay
    || !menu
  ) {
    return;
  }

  let previouslyFocusedElement = null;
  let isOpeningSideMenu = false;

  function getFocusableMenuElements() {
    return Array.from(
      menu.querySelectorAll(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      )
    ).filter((element) => !element.hidden);
  }

  async function openSideMenu() {
    if (isOpeningSideMenu || menu.classList.contains("open")) {
      return;
    }
    isOpeningSideMenu = true;
    previouslyFocusedElement = document.activeElement;

    try {
      await refreshGymfitCurrentUser();
    } catch (error) {
      console.error("메뉴 사용자 정보 동기화 실패:", error);
    }
    renderSideMenu();

    overlay.hidden = false;

    requestAnimationFrame(() => {
      menu.classList.add(
        "open"
      );
      isOpeningSideMenu = false;
      const focusableElements = getFocusableMenuElements();
      (focusableElements[0] || menu).focus();
    });

    menu.setAttribute(
      "aria-hidden",
      "false"
    );

    openButton.setAttribute(
      "aria-expanded",
      "true"
    );

    document.body.classList.add(
      "side-menu-open"
    );

  }

  function closeSideMenu() {
    if (!menu.classList.contains("open")) {
      return;
    }

    menu.classList.remove(
      "open"
    );

    menu.setAttribute(
      "aria-hidden",
      "true"
    );

    openButton.setAttribute(
      "aria-expanded",
      "false"
    );

    document.body.classList.remove(
      "side-menu-open"
    );

    const hideOverlay = () => {
      overlay.hidden = true;
    };
    menu.addEventListener("transitionend", hideOverlay, { once: true });
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      hideOverlay();
    }

    if (previouslyFocusedElement?.isConnected) {
      previouslyFocusedElement.focus();
    } else {
      openButton.focus();
    }
  }

  openButton.addEventListener(
    "click",
    openSideMenu
  );

  closeButton.addEventListener(
    "click",
    closeSideMenu
  );

  overlay.addEventListener(
    "click",
    closeSideMenu
  );

  window.addEventListener(
    "keydown",
    (event) => {
      if (
        event.key === "Escape"
        && menu.classList.contains(
          "open"
        )
      ) {
        closeSideMenu();
        return;
      }

      if (
        event.key === "Tab"
        && menu.classList.contains("open")
      ) {
        const focusableElements = getFocusableMenuElements();
        if (!focusableElements.length) {
          event.preventDefault();
          menu.focus();
          return;
        }

        const firstElement = focusableElements[0];
        const lastElement = focusableElements[focusableElements.length - 1];
        if (event.shiftKey && document.activeElement === firstElement) {
          event.preventDefault();
          lastElement.focus();
        } else if (!event.shiftKey && document.activeElement === lastElement) {
          event.preventDefault();
          firstElement.focus();
        }
      }
    }
  );

}


window.addEventListener(
  "gymfitUserUpdated",
  renderSideMenu
);


function setupBottomNavigation() {
  const user = getLoginUser();
  const accountType = String(
    user?.account_type ?? user?.accountType ?? ""
  ).toUpperCase();
  const navigation = document.querySelector(".bottom-navigation");
  if (accountType === "TRAINER" && navigation) {
    const originalItems = Array.from(navigation.querySelectorAll(".nav-item"));
    const trainerItems = [
      {
        item: originalItems[0],
        path: "/trainer/members",
        label: "회원",
        page: "trainer-members",
      },
      {
        item: originalItems[1],
        path: "/trainer/assignments",
        label: "숙제",
        page: "trainer-assignments",
      },
      {
        item: originalItems[2],
        path: "/trainer/schedules",
        label: "일정",
        page: "trainer-schedules",
      },
      {
        item: originalItems[4],
        path: "/mypage",
        label: "마이",
        page: "mypage",
      },
    ];
    navigation.replaceChildren(...trainerItems.map(({ item, path, label, page }) => {
      item.href = path;
      item.dataset.navPage = page;
      item.querySelector("span:last-child").textContent = label;
      return item;
    }));
    navigation.classList.add("trainer-navigation");
  }

  const currentPath =
    window.location.pathname;

  const navigationItems =
    document.querySelectorAll(
      ".nav-item"
    );

  navigationItems.forEach((item) => {
    const itemPath =
      new URL(
        item.href,
        window.location.origin
      ).pathname;

    const isActive =
      itemPath === currentPath
      || (
        itemPath !== "/"
        && currentPath.startsWith(`${itemPath}/`)
      );

    item.classList.toggle(
      "active",
      isActive
    );

    if (isActive) {
      item.setAttribute(
        "aria-current",
        "page"
      );
    } else {
      item.removeAttribute(
        "aria-current"
      );
    }
  });
}


function setupCommonHeader() {
  const currentPage =
    document.body.dataset.page;

  const logo =
    document.querySelector(
      "#dashboardHeaderLogo"
    );

  const headerText =
    document.querySelector(
      "#commonHeaderText"
    );

  const title =
    document.querySelector(
      "#commonHeaderTitle"
    );

  const subtitle =
    document.querySelector(
      "#commonHeaderSubtitle"
    );

  const headerTitle =
    document.body.dataset.headerTitle
    || "";

  const headerSubtitle =
    document.body.dataset.headerSubtitle
    || "";

  const isDashboard =
    currentPage === "home";

  if (logo) {
    logo.hidden =
      !isDashboard;
  }

  if (headerText) {
    headerText.hidden =
      isDashboard;
  }

  if (!isDashboard) {
    title.textContent =
      headerTitle;

    subtitle.textContent =
      headerSubtitle;

    subtitle.hidden =
      !headerSubtitle;
  }
}


async function refreshNotificationBadge() {
  const user = getLoginUser();
  const badge = document.querySelector("#notificationBadge");
  if (!badge || !user?.user_id) return;
  try {
    const response = await window.gymfitApi.fetch("/api/notifications/unread-count");
    if (!response.ok) throw new Error("알림 개수를 불러오지 못했습니다.");
    const data = await response.json();
    const count = Math.max(0, Number(data.unread_count) || 0);
    badge.textContent = count > 99 ? "99+" : String(count);
    badge.hidden = count === 0;
  } catch (error) {
    badge.hidden = true;
    console.error("알림 배지 조회 실패:", error);
  }
}


function setupNotificationButton() {
  const button = document.querySelector("#notificationButton");
  if (!button) return;
  button.addEventListener("click", () => {
    window.location.href = "/notifications";
  });
  refreshNotificationBadge();
}

function setupAccessibleDialogs() {
  const focusHistory = new WeakMap();

  function getDialog(container) {
    if (container.matches?.('[role="dialog"], [role="alertdialog"]')) {
      return container;
    }
    return container.querySelector?.(
      '[role="dialog"], [role="alertdialog"]'
    ) || null;
  }

  function getFocusableElements(dialog) {
    return Array.from(dialog.querySelectorAll(
      'a[href], button:not([disabled]), input:not([disabled]), '
      + 'select:not([disabled]), textarea:not([disabled]), '
      + '[tabindex]:not([tabindex="-1"])'
    )).filter((element) => (
      !element.hidden
      && element.getAttribute("aria-hidden") !== "true"
    ));
  }

  function handleVisibilityChange(container) {
    const dialog = getDialog(container);
    if (!dialog) return;

    if (!container.hidden) {
      if (!focusHistory.has(container)) {
        focusHistory.set(container, document.activeElement);
      }
      if (!dialog.hasAttribute("tabindex")) {
        dialog.setAttribute("tabindex", "-1");
      }
      requestAnimationFrame(() => {
        const focusableElements = getFocusableElements(dialog);
        (focusableElements[0] || dialog).focus();
      });
      return;
    }

    const previousFocus = focusHistory.get(container);
    focusHistory.delete(container);
    if (previousFocus?.isConnected) {
      previousFocus.focus();
    }
  }

  const dialogContainers = document.querySelectorAll(
    '[hidden]:has([role="dialog"]), [hidden]:has([role="alertdialog"])'
  );
  dialogContainers.forEach((container) => {
    const observer = new MutationObserver(() => {
      handleVisibilityChange(container);
    });
    observer.observe(container, {
      attributes: true,
      attributeFilter: ["hidden"],
    });
  });

  window.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;

    const openDialogs = Array.from(document.querySelectorAll(
      '[role="dialog"], [role="alertdialog"]'
    )).filter((dialog) => (
      !dialog.closest("[hidden]")
      && dialog.getAttribute("aria-hidden") !== "true"
    ));
    const dialog = openDialogs.at(-1);
    if (!dialog) return;

    const focusableElements = getFocusableElements(dialog);
    if (!focusableElements.length) {
      event.preventDefault();
      dialog.focus();
      return;
    }

    const firstElement = focusableElements[0];
    const lastElement = focusableElements.at(-1);
    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault();
      lastElement.focus();
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault();
      firstElement.focus();
    }
  });
}

function setupVisualViewport() {
  const viewport = window.visualViewport;
  if (!viewport) return;

  const syncViewportHeight = () => {
    document.documentElement.style.setProperty(
      "--visual-viewport-height",
      `${Math.round(viewport.height)}px`
    );
  };
  syncViewportHeight();
  viewport.addEventListener("resize", syncViewportHeight);
}


window.addEventListener("gymfitNotificationsUpdated", refreshNotificationBadge);

window.addEventListener(
  "DOMContentLoaded",
  async () => {
    try {
      await Promise.all([
        loadCommonComponent(
          "#topHeaderContainer",
          "/static/components/top_header.html"
        ),

        loadCommonComponent(
          "#sideMenuContainer",
          "/static/components/side_menu.html"
        ),

        loadCommonComponent(
          "#bottomNavigationContainer, #bottomNavContainer",
          "/static/components/bottom_nav.html"
        )
      ]);

      setupCommonHeader();
      setupSideMenu();
      setupBottomNavigation();
      setupNotificationButton();
      setupAccessibleDialogs();
      setupVisualViewport();

      try {
        const currentUser = await refreshGymfitCurrentUser();
        if (redirectForAccountType(currentUser)) {
          return;
        }
      } catch (error) {
        console.error("사용자 프로필 동기화 실패:", error);
      }

      window.dispatchEvent(
        new CustomEvent(
          "commonLayoutReady"
        )
      );

    } catch (error) {
      console.error(
        "공통 레이아웃 로딩 실패:",
        error
      );
    }
  }
);
