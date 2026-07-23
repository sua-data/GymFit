(function () {
  const sessionUser = (() => {
    try {
      const value = JSON.parse(sessionStorage.getItem("gymfitUser") || "null");
      const userId = Number(value?.user_id ?? value?.userId);
      return userId > 0 ? { ...value, user_id: userId } : null;
    } catch { return null; }
  })();
  if (!sessionUser) {
    window.location.replace("/login");
    return;
  }

  const elements = Object.fromEntries([
    "gymLoading", "gymError", "gymErrorMessage", "gymEmpty", "gymContent",
    "gymName", "gymRoadAddress", "gymAddress", "gymCategory", "gymMapSection", "gymMap",
    "gymMapMessage", "gymPhoneLink", "copyAddressButton", "kakaoPlaceLink",
    "gymChangeButton", "gymDisconnectButton", "gymEditPolicy",
    "gymSearchOverlay", "gymSaveButton", "gymSaveMessage", "disconnectOverlay",
    "disconnectConfirm", "gymToast",
    "employmentCard", "employmentStatus", "employmentMessage",
    "employmentFileName", "employmentEvidenceInput", "employmentUploadLabel",
  ].map((id) => [id, document.getElementById(id)]));

  let currentGym = null;
  let canEdit = true;
  let isSaving = false;
  let isDisconnecting = false;
  let map = null;
  let marker = null;
  let kakaoSdkPromise = null;
  let toastTimer = null;
  let employmentUploading = false;
  const searchController = window.createGymSearch(document.querySelector("[data-gym-search]"));

  async function requestJson(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: { ...(options.headers || {}), "X-User-Id": String(sessionUser.user_id) },
    });
    const body = await response.json().catch(() => null);
    if (!response.ok) {
      const detail = Array.isArray(body?.detail)
        ? body.detail.map((item) => item.msg).filter(Boolean).join(" ")
        : body?.detail;
      throw new Error(detail || "요청을 처리하지 못했습니다.");
    }
    return body;
  }

  function showToast(message) {
    clearTimeout(toastTimer);
    elements.gymToast.textContent = message;
    elements.gymToast.hidden = false;
    toastTimer = setTimeout(() => { elements.gymToast.hidden = true; }, 2400);
  }

  function toggleText(element, value) {
    element.textContent = value || "";
    element.hidden = !value;
  }

  async function loadKakaoSdk() {
    if (window.kakao?.maps) return window.kakao;
    if (kakaoSdkPromise) return kakaoSdkPromise;
    kakaoSdkPromise = (async () => {
      const config = await requestJson("/api/gyms/map-config");
      if (!config?.app_key) throw new Error("지도 API 키가 설정되지 않았습니다.");
      const existing = document.querySelector("script[data-gymfit-kakao-map]");
      if (!existing) {
        await new Promise((resolve, reject) => {
          const script = document.createElement("script");
          script.dataset.gymfitKakaoMap = "true";
          script.src = `https://dapi.kakao.com/v2/maps/sdk.js?appkey=${encodeURIComponent(config.app_key)}&autoload=false`;
          script.onload = resolve;
          script.onerror = () => reject(new Error("지도 SDK를 불러오지 못했습니다."));
          document.head.appendChild(script);
        });
      }
      await new Promise((resolve) => window.kakao.maps.load(resolve));
      return window.kakao;
    })();
    return kakaoSdkPromise;
  }

  async function renderMap(gym) {
    const latitude = Number(gym?.latitude);
    const longitude = Number(gym?.longitude);
    const hasCoordinates = Number.isFinite(latitude) && Number.isFinite(longitude);
    elements.gymMapSection.hidden = !hasCoordinates;
    if (!hasCoordinates) {
      map = null;
      marker = null;
      elements.gymMap.replaceChildren();
      return;
    }
    elements.gymMapMessage.hidden = true;
    try {
      const kakao = await loadKakaoSdk();
      const position = new kakao.maps.LatLng(latitude, longitude);
      if (map && marker) {
        map.setCenter(position);
        marker.setPosition(position);
        map.relayout();
      } else {
        elements.gymMap.replaceChildren();
        map = new kakao.maps.Map(elements.gymMap, { center: position, level: 3 });
        marker = new kakao.maps.Marker({ map, position });
      }
    } catch (error) {
      map = null;
      marker = null;
      elements.gymMap.replaceChildren();
      elements.gymMapMessage.textContent = error instanceof Error ? error.message : "지도를 표시하지 못했습니다.";
      elements.gymMapMessage.hidden = false;
    }
  }

  async function renderGym() {
    const gym = currentGym;
    elements.gymLoading.hidden = true;
    elements.gymError.hidden = true;
    elements.gymEmpty.hidden = Boolean(gym);
    elements.gymContent.hidden = !gym;
    if (!gym) {
      map = null;
      marker = null;
      elements.gymMap.replaceChildren();
      return;
    }
    elements.gymName.textContent = gym.gym_name;
    toggleText(elements.gymRoadAddress, gym.road_address);
    toggleText(elements.gymAddress, gym.address && gym.address !== gym.road_address ? `지번 ${gym.address}` : "");
    toggleText(elements.gymCategory, gym.category_name);
    elements.gymPhoneLink.hidden = !gym.phone;
    if (gym.phone) elements.gymPhoneLink.href = `tel:${gym.phone.replace(/[^\d+]/g, "")}`;
    elements.kakaoPlaceLink.hidden = !gym.place_url;
    if (gym.place_url) elements.kakaoPlaceLink.href = gym.place_url;
    elements.copyAddressButton.hidden = !(gym.road_address || gym.address);
    elements.gymChangeButton.disabled = !canEdit;
    elements.gymDisconnectButton.disabled = !canEdit;
    elements.gymEditPolicy.hidden = canEdit;
    await renderMap(gym);
  }

  async function loadGym() {
    elements.gymLoading.hidden = false;
    elements.gymError.hidden = true;
    try {
      const body = await requestJson("/api/users/me/gym");
      currentGym = body?.gym || null;
      canEdit = body?.can_edit !== false;
      await renderGym();
      await loadEmployment();
    } catch (error) {
      elements.gymLoading.hidden = true;
      elements.gymContent.hidden = true;
      elements.gymEmpty.hidden = true;
      elements.gymErrorMessage.textContent = error instanceof Error ? error.message : "잠시 후 다시 시도해 주세요.";
      elements.gymError.hidden = false;
    }
  }

  async function loadEmployment() {
    const isTrainer = String(sessionUser.account_type || "").toUpperCase() === "TRAINER";
    elements.employmentCard.hidden = !isTrainer || !currentGym;
    if (!isTrainer || !currentGym) return;
    try {
      const data = await requestJson("/api/trainers/me/employment");
      const labels = {
        NONE: "소속 미등록",
        PENDING: "관리자 검토 대기",
        APPROVED: "소속 승인 완료",
        REJECTED: "소속 승인 거절",
      };
      elements.employmentStatus.textContent = labels[data.employment_status] || data.employment_status;
      elements.employmentMessage.textContent = data.employment_status === "APPROVED"
        ? "현재 헬스장의 관리 기능을 사용할 수 있습니다."
        : data.employment_status === "REJECTED"
          ? `새 헬스장의 관리 권한이 없습니다.${data.employment_rejection_reason ? ` 사유: ${data.employment_rejection_reason}` : ""}`
          : "승인 전까지 현재 헬스장의 회원·머신·PT 관리 기능이 제한됩니다.";
      elements.employmentFileName.textContent = data.evidence_original_name || "";
      elements.employmentFileName.hidden = !data.evidence_original_name;
      elements.employmentUploadLabel.textContent = data.has_evidence ? "재직·소속 증빙 교체" : "재직·소속 증빙 등록";
    } catch (error) {
      elements.employmentMessage.textContent = error instanceof Error ? error.message : "소속 승인 정보를 불러오지 못했습니다.";
    }
  }

  async function uploadEmploymentEvidence(file) {
    if (!file || employmentUploading) return;
    employmentUploading = true;
    elements.employmentEvidenceInput.disabled = true;
    const formData = new FormData();
    formData.append("file", file);
    try {
      await requestJson("/api/trainers/me/employment/evidence", {
        method: "POST",
        body: formData,
      });
      await loadEmployment();
      showToast("소속 증빙을 제출했습니다.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "소속 증빙을 제출하지 못했습니다.");
    } finally {
      employmentUploading = false;
      elements.employmentEvidenceInput.disabled = false;
      elements.employmentEvidenceInput.value = "";
    }
  }

  function openOverlay(overlay) {
    overlay.hidden = false;
    document.body.classList.add("modal-open");
  }
  function closeOverlay(overlay) {
    overlay.hidden = true;
    document.body.classList.remove("modal-open");
  }

  async function saveGym() {
    const selected = searchController.getValue();
    if (!selected || isSaving) {
      if (!selected) {
        elements.gymSaveMessage.textContent = "검색 결과에서 헬스장을 선택해 주세요.";
        elements.gymSaveMessage.hidden = false;
      }
      return;
    }
    isSaving = true;
    elements.gymSaveButton.disabled = true;
    elements.gymSaveMessage.hidden = true;
    try {
      await requestJson("/api/users/me/gym", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(selected),
      });
      closeOverlay(elements.gymSearchOverlay);
      await loadGym(); // 저장 응답을 임시 반영하지 않고 서버 최신값으로 전체 갱신한다.
      window.dispatchEvent(new CustomEvent("gymfitGymUpdated", { detail: currentGym }));
      showToast("헬스장을 변경했습니다.");
    } catch (error) {
      elements.gymSaveMessage.textContent = error instanceof Error ? error.message : "헬스장 변경에 실패했습니다.";
      elements.gymSaveMessage.hidden = false;
    } finally {
      isSaving = false;
      elements.gymSaveButton.disabled = false;
    }
  }

  async function disconnectGym() {
    if (isDisconnecting) return;
    isDisconnecting = true;
    elements.disconnectConfirm.disabled = true;
    try {
      await requestJson("/api/users/me/gym", { method: "DELETE" });
      closeOverlay(elements.disconnectOverlay);
      await loadGym();
      window.dispatchEvent(new CustomEvent("gymfitGymUpdated", { detail: null }));
      showToast("헬스장 연결을 해제했습니다.");
    } catch (error) {
      showToast(error instanceof Error ? error.message : "연결 해제에 실패했습니다.");
    } finally {
      isDisconnecting = false;
      elements.disconnectConfirm.disabled = false;
    }
  }

  document.getElementById("gymRetryButton").addEventListener("click", loadGym);
  document.getElementById("gymRegisterButton").addEventListener("click", () => openOverlay(elements.gymSearchOverlay));
  elements.gymChangeButton.addEventListener("click", () => openOverlay(elements.gymSearchOverlay));
  document.getElementById("gymSearchClose").addEventListener("click", () => closeOverlay(elements.gymSearchOverlay));
  document.getElementById("gymSearchBackdrop").addEventListener("click", () => closeOverlay(elements.gymSearchOverlay));
  elements.gymSaveButton.addEventListener("click", saveGym);
  elements.copyAddressButton.addEventListener("click", async () => {
    const address = currentGym?.road_address || currentGym?.address;
    if (!address) return;
    try { await navigator.clipboard.writeText(address); showToast("주소를 복사했습니다."); }
    catch { showToast("주소를 복사하지 못했습니다."); }
  });
  elements.gymDisconnectButton.addEventListener("click", () => openOverlay(elements.disconnectOverlay));
  document.getElementById("disconnectClose").addEventListener("click", () => closeOverlay(elements.disconnectOverlay));
  document.getElementById("disconnectBackdrop").addEventListener("click", () => closeOverlay(elements.disconnectOverlay));
  document.getElementById("disconnectCancel").addEventListener("click", () => closeOverlay(elements.disconnectOverlay));
  elements.disconnectConfirm.addEventListener("click", disconnectGym);
  elements.employmentEvidenceInput.addEventListener("change", () => {
    uploadEmploymentEvidence(elements.employmentEvidenceInput.files?.[0]);
  });
  window.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!elements.disconnectOverlay.hidden) closeOverlay(elements.disconnectOverlay);
    else if (!elements.gymSearchOverlay.hidden) closeOverlay(elements.gymSearchOverlay);
  });
  loadGym();
})();
