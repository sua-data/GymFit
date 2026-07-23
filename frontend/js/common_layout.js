const memberServiceMenuItems = [
  {
    label: "내 헬스장"
  },
  {
    label: "머신 사용법"
  }
];

const trainerServiceMenuItems = [
  {
    label: "내 헬스장"
  },
  {
    label: "보유 머신 관리"
  },
  {
    label: "머신 사용법"
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
    label: "PT 숙제",
    path: "/trainer/assignments"
  },
  {
    label: "PT 일정",
    path: "/trainer/schedules"
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
  if (accountType === "MEMBER" && hasActiveTrainer) {
    return "PT 회원";
  }
  return "개인 운동자";
}

window.getUserRoleLabel = getUserRoleLabel;

window.addEventListener("pageshow", () => {
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
    const response = await fetch(`/api/users/${userId}`, {
      headers: { "X-User-Id": String(userId) },
    });
    const profile = await response.json().catch(() => null);
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
  const savedUser =
    sessionStorage.getItem(
      "gymfitUser"
    );

  if (!savedUser) {
    return null;
  }

  try {
    return JSON.parse(
      savedUser
    );
  } catch {
    return null;
  }
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
    } else {
      menuItem.type = "button";
      menuItem.addEventListener("click", () => {
        window.alert("준비 중인 기능입니다.");
      });
    }

    const label =
      document.createElement("span");

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

  userName.textContent =
    `${user.name || "사용자"}님`;

  const accountType = String(
    user.account_type
    ?? user.accountType
    ?? ""
  ).toUpperCase();
  const isTrainer = accountType === "TRAINER";

  const hasActiveTrainer =
    user.has_active_trainer === true
    || user.hasActiveTrainer === true;

  userType.textContent = getUserRoleLabel(user);

  menuList.appendChild(
    createMenuSection(
      "운동 관리",
      isTrainer
        ? trainerServiceMenuItems
        : [
            ...memberServiceMenuItems,
            {
              label: "PT 요청",
              path: "/pt/requests",
              badgeCount: user.pending_pt_request_count,
            },
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

  async function openSideMenu() {
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

    window.setTimeout(() => {
      overlay.hidden = true;
    }, 250);
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
      }
    }
  );

}


window.addEventListener(
  "gymfitUserUpdated",
  renderSideMenu
);


function setupBottomNavigation() {
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
    const response = await fetch("/api/notifications/unread-count", {
      headers: { "X-User-Id": String(user.user_id) },
    });
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
          "#bottomNavigationContainer",
          "/static/components/bottom_nav.html"
        )
      ]);

      setupCommonHeader();
      setupSideMenu();
      setupBottomNavigation();
      setupNotificationButton();

      try {
        await refreshGymfitCurrentUser();
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
