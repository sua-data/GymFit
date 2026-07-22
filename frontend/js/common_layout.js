const commonMenuItems = [
  {
    label: "내 헬스장",
    path: "/my-gym"
  },
  {
    label: "보유 머신 관리",
    path: "/my-gym/machines"
  },
  {
    label: "머신 사용법",
    path: "/machines"
  },
  {
    label: "알림",
    path: "/notifications"
  },
  {
    label: "설정",
    path: "/settings"
  }
];

const ptMemberMenuItems = [
  {
    label: "PT 숙제",
    path: "/pt-homework"
  },
  {
    label: "트레이너 피드백",
    path: "/trainer-feedback"
  },
  {
    label: "PT 일정",
    path: "/pt-schedule"
  }
];

const trainerMenuItems = [
  {
    label: "담당 회원 관리",
    path: "/trainer/members"
  },
  {
    label: "PT 숙제 관리",
    path: "/trainer/homework"
  },
  {
    label: "회원 피드백",
    path: "/trainer/feedback"
  },
  {
    label: "PT 일정 관리",
    path: "/trainer/schedule"
  }
];


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
    const link =
      document.createElement("a");

    link.className =
      "side-menu-item";

    link.href =
      item.path;

    const label =
      document.createElement("span");

    label.textContent =
      item.label;

    const arrow =
      document.createElement("span");

    arrow.textContent =
      "›";

    link.append(
      label,
      arrow
    );

    section.appendChild(link);
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

  const isTrainer =
    user.account_type === "TRAINER";

  const hasActiveTrainer =
    Boolean(
      user.has_active_trainer
    );

  if (isTrainer) {
    userType.textContent =
      "트레이너";
  } else if (hasActiveTrainer) {
    userType.textContent =
      "PT 회원";
  } else {
    userType.textContent =
      "개인 운동자";
  }

  menuList.appendChild(
    createMenuSection(
      "운동 관리",
      commonMenuItems
    )
  );

  if (hasActiveTrainer) {
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

  const logoutButton =
    document.querySelector(
      "#logoutButton"
    );

  if (
    !openButton
    || !closeButton
    || !overlay
    || !menu
  ) {
    return;
  }

  function openSideMenu() {
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

  logoutButton?.addEventListener(
    "click",
    () => {
      if (!window.confirm("로그아웃하시겠어요?")) {
        return;
      }

      [
        "gymfitUser",
        "gymfitCoachingPlan",
        "gymfitCoachingRestSeconds",
        "gymfitFreeCoachingSets",
        "gymfitCoachingVoiceEnabled"
      ].forEach((key) => {
        sessionStorage.removeItem(key);
      });

      window.speechSynthesis?.cancel();
      window.location.replace("/login");
    }
  );
}


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
