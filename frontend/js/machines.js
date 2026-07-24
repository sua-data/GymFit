(function () {
  const user = (() => {
    try {
      const value = JSON.parse(sessionStorage.getItem("gymfitUser") || "null");
      const id = Number(value?.user_id ?? value?.userId);
      return id > 0 ? { ...value, user_id: id } : null;
    } catch { return null; }
  })();
  if (!user) { window.location.replace("/login"); return; }

  const byId = (id) => document.getElementById(id);
  const elements = Object.fromEntries([
    "machineLoading","machineError","machineErrorMessage","gymRequired","machineContent",
    "machineGymName","machineCount","machineCreateButton","machineSearch","machineFilters",
    "machineEmpty","machineEmptyTitle","machineEmptyDescription","machineEmptyCreate","machineList",
    "machineDetailOverlay","machineDetailBody","machineFormOverlay","machineForm","machineFormTitle",
    "machineNameInput","machineBodyPartInput","machineBrandInput","machineModelInput",
    "machineDescriptionInput","machineUsageInput","machineCautionInput","machineImageInput",
    "machineImagePreview","machineImagePreviewImg","machineFormMessage","machineFormSubmit",
    "machineDeleteOverlay","machineDeleteName","machineDeleteConfirm","machineToast",
  ].map((id) => [id, byId(id)]));

  let machines = [];
  let categories = [];
  let canManage = false;
  let selectedPart = "";
  let editingMachine = null;
  let deletingMachine = null;
  let imageRemoved = false;
  let submitting = false;
  let deleting = false;
  let searchTimer = null;
  let previewUrl = null;
  let formDirty = false;
  let returnFocus = null;
  let toastTimer = null;

  async function api(url, options = {}) {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...(options.body instanceof FormData ? {} : { "Content-Type": "application/json" }),
        ...(options.headers || {}),
        "X-User-Id": String(user.user_id),
      },
    });
    const body = response.status === 204 ? null : await response.json().catch(() => null);
    if (!response.ok) {
      const detail = Array.isArray(body?.detail)
        ? body.detail.map((item) => item.msg).filter(Boolean).join(" ")
        : body?.detail;
      const error = new Error(detail || "요청을 처리하지 못했습니다.");
      error.status = response.status;
      throw error;
    }
    return body;
  }

  function showToast(message) {
    clearTimeout(toastTimer);
    elements.machineToast.textContent = message;
    elements.machineToast.hidden = false;
    toastTimer = setTimeout(() => { elements.machineToast.hidden = true; }, 2400);
  }

  function createText(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    node.textContent = text;
    return node;
  }

  async function loadProtectedImage(image, url) {
    try {
      const response = await fetch(url, {
        headers: { "X-User-Id": String(user.user_id) },
      });
      if (!response.ok) return;
      const objectUrl = URL.createObjectURL(await response.blob());
      image.onload = () => URL.revokeObjectURL(objectUrl);
      image.src = objectUrl;
    } catch {
      image.removeAttribute("src");
    }
  }

  function openSheet(overlay, focusTarget) {
    returnFocus = document.activeElement;
    overlay.hidden = false;
    document.body.classList.add("modal-open");
    requestAnimationFrame(() => focusTarget?.focus());
  }

  function closeSheet(overlay) {
    window.GymfitDropdown?.closeAll();
    overlay.hidden = true;
    if (document.querySelectorAll(".sheet-overlay:not([hidden])").length === 0) {
      document.body.classList.remove("modal-open");
    }
    returnFocus?.focus();
  }

  function closeFormSheet() {
    if (formDirty && !window.confirm("저장하지 않은 변경사항이 있습니다. 닫을까요?")) return;
    formDirty = false;
    closeSheet(elements.machineFormOverlay);
  }

  function imageNode(machine, className) {
    if (!machine.image_url) return createText("div", className, "M");
    const wrapper = document.createElement("div");
    wrapper.className = className;
    const image = document.createElement("img");
    image.alt = `${machine.machine_name} 대표 이미지`;
    image.loading = "lazy";
    loadProtectedImage(image, machine.image_url);
    wrapper.append(image);
    return wrapper;
  }

  function renderFilters() {
    elements.machineFilters.replaceChildren();
    ["", ...categories].forEach((part) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = part || "전체";
      button.classList.toggle("active", selectedPart === part);
      button.setAttribute("aria-pressed", String(selectedPart === part));
      button.addEventListener("click", () => {
        selectedPart = part;
        renderFilters();
        loadMachines();
      });
      elements.machineFilters.append(button);
    });
  }

  function renderCards() {
    elements.machineList.replaceChildren();
    elements.machineCount.textContent = String(machines.length);
    const hasFilter = Boolean(selectedPart || elements.machineSearch.value.trim());
    elements.machineEmpty.hidden = machines.length > 0;
    if (!machines.length) {
      elements.machineEmptyTitle.textContent = hasFilter ? "검색 결과가 없어요." : "아직 등록된 머신이 없어요.";
      elements.machineEmptyDescription.textContent = hasFilter
        ? "검색어나 운동 부위 필터를 변경해 보세요."
        : canManage ? "헬스장에 있는 첫 머신을 등록해보세요." : "헬스장 트레이너가 머신 정보를 등록하면 확인할 수 있어요.";
      elements.machineEmptyCreate.hidden = hasFilter || !canManage;
      return;
    }
    machines.forEach((machine) => {
      const card = document.createElement("article");
      card.className = "machine-card";
      const main = document.createElement("button");
      main.type = "button";
      main.className = "machine-card-main";
      main.setAttribute("aria-label", `${machine.machine_name} 사용법 보기`);
      main.append(imageNode(machine, "machine-card-media"));
      const copy = document.createElement("div");
      copy.className = "machine-card-copy";
      copy.append(createText("span", "machine-part", machine.body_part));
      copy.append(createText("h2", "", machine.machine_name));
      const meta = [machine.brand, machine.model_name].filter(Boolean).join(" · ");
      if (meta) copy.append(createText("p", "machine-meta", meta));
      if (machine.description) copy.append(createText("p", "machine-description", machine.description));
      copy.append(createText("p", "machine-guide-link", "사용법 보기 ›"));
      main.append(copy);
      main.addEventListener("click", () => openDetail(machine, main));
      card.append(main);
      if (canManage) {
        const actions = document.createElement("div");
        actions.className = "machine-card-actions";
        const edit = createText("button", "", "수정");
        edit.type = "button";
        edit.addEventListener("click", () => openForm(machine, edit));
        const remove = createText("button", "", "삭제");
        remove.type = "button";
        remove.addEventListener("click", () => openDelete(machine, remove));
        actions.append(edit, remove);
        card.append(actions);
      }
      elements.machineList.append(card);
    });
  }

  async function loadMachines() {
    elements.machineLoading.hidden = false;
    elements.machineError.hidden = true;
    elements.gymRequired.hidden = true;
    try {
      const params = new URLSearchParams();
      const query = elements.machineSearch.value.trim();
      if (query) params.set("query", query);
      if (selectedPart) params.set("body_part", selectedPart);
      const data = await api(`/api/users/me/gym/machines?${params}`);
      machines = Array.isArray(data.items) ? data.items : [];
      categories = Array.isArray(data.categories) ? data.categories : [];
      canManage = data.can_manage === true;
      elements.machineGymName.textContent = data.gym?.gym_name || "내 헬스장";
      elements.machineCreateButton.hidden = !canManage;
      elements.machineContent.hidden = false;
      renderFilters();
      syncCategoryOptions();
      renderCards();
    } catch (error) {
      elements.machineContent.hidden = true;
      if (error.status === 409) {
        elements.gymRequired.hidden = false;
      } else {
        console.error("머신 목록 조회 실패:", error);
        elements.machineErrorMessage.textContent =
          "네트워크 연결을 확인한 뒤 다시 시도해 주세요.";
        elements.machineError.hidden = false;
      }
    } finally {
      elements.machineLoading.hidden = true;
    }
  }

  function detailSection(title, value) {
    if (!value) return null;
    const section = document.createElement("section");
    section.className = "detail-section";
    section.append(createText("h3", "", title), createText("p", "", value));
    return section;
  }

  function openDetail(machine, trigger) {
    elements.machineDetailBody.replaceChildren();
    if (machine.image_url) {
      const image = document.createElement("img");
      image.className = "detail-image";
      image.alt = `${machine.machine_name} 대표 이미지`;
      loadProtectedImage(image, machine.image_url);
      elements.machineDetailBody.append(image);
    }
    elements.machineDetailBody.append(
      createText("span", "detail-part", machine.body_part),
      createText("h3", "detail-title", machine.machine_name),
    );
    const meta = [machine.brand, machine.model_name].filter(Boolean).join(" · ");
    if (meta) elements.machineDetailBody.append(createText("p", "detail-meta", meta));
    [
      detailSection("설명", machine.description),
      detailSection("사용 방법", machine.usage_guide),
      detailSection("주의사항", machine.caution),
    ].filter(Boolean).forEach((section) => elements.machineDetailBody.append(section));
    if (canManage) {
      const actions = document.createElement("div");
      actions.className = "detail-actions";
      const edit = createText("button", "", "수정");
      edit.type = "button";
      edit.addEventListener("click", () => { closeSheet(elements.machineDetailOverlay); openForm(machine, trigger); });
      const remove = createText("button", "", "삭제");
      remove.type = "button";
      remove.addEventListener("click", () => { closeSheet(elements.machineDetailOverlay); openDelete(machine, trigger); });
      actions.append(edit, remove);
      elements.machineDetailBody.append(actions);
    }
    openSheet(elements.machineDetailOverlay, byId("machineDetailClose"));
  }

  function syncCategoryOptions() {
    const previous = elements.machineBodyPartInput.value;
    elements.machineBodyPartInput.replaceChildren(new Option("운동 부위 선택", ""));
    categories.forEach((category) => elements.machineBodyPartInput.add(new Option(category, category)));
    elements.machineBodyPartInput.value = previous;
    window.GymfitDropdown?.refresh(elements.machineBodyPartInput);
  }

  function revokePreview() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    previewUrl = null;
  }

  function setPreview(src, protectedSource = false) {
    elements.machineImagePreview.hidden = !src;
    if (src && protectedSource) loadProtectedImage(elements.machineImagePreviewImg, src);
    else if (src) elements.machineImagePreviewImg.src = src;
    else elements.machineImagePreviewImg.removeAttribute("src");
  }

  function updateCounts() {
    document.querySelectorAll("[data-count-for]").forEach((counter) => {
      const input = byId(counter.dataset.countFor);
      counter.textContent = String(input.value.length);
    });
  }

  function openForm(machine = null, trigger) {
    editingMachine = machine;
    imageRemoved = false;
    formDirty = false;
    elements.machineForm.reset();
    syncCategoryOptions();
    elements.machineFormTitle.textContent = machine ? "머신 수정" : "머신 등록";
    elements.machineFormMessage.hidden = true;
    elements.machineNameInput.value = machine?.machine_name || "";
    elements.machineBodyPartInput.value = machine?.body_part || "";
    elements.machineBrandInput.value = machine?.brand || "";
    elements.machineModelInput.value = machine?.model_name || "";
    elements.machineDescriptionInput.value = machine?.description || "";
    elements.machineUsageInput.value = machine?.usage_guide || "";
    elements.machineCautionInput.value = machine?.caution || "";
    window.GymfitDropdown?.refresh(elements.machineBodyPartInput);
    revokePreview();
    setPreview(machine?.image_url || "", Boolean(machine?.image_url));
    updateCounts();
    returnFocus = trigger || document.activeElement;
    openSheet(elements.machineFormOverlay, elements.machineNameInput);
  }

  async function submitForm(event) {
    event.preventDefault();
    if (submitting || !elements.machineForm.reportValidity()) return;
    const image = elements.machineImageInput.files[0] || null;
    if (image && image.size > 5 * 1024 * 1024) {
      elements.machineFormMessage.textContent = "이미지는 5MB 이하만 업로드할 수 있습니다.";
      elements.machineFormMessage.hidden = false;
      return;
    }
    const payload = {
      machine_name: elements.machineNameInput.value,
      body_part: elements.machineBodyPartInput.value,
      brand: elements.machineBrandInput.value || null,
      model_name: elements.machineModelInput.value || null,
      description: elements.machineDescriptionInput.value || null,
      usage_guide: elements.machineUsageInput.value || null,
      caution: elements.machineCautionInput.value || null,
    };
    if (editingMachine) payload.remove_image = Boolean(imageRemoved && !image);
    submitting = true;
    elements.machineFormSubmit.disabled = true;
    elements.machineFormMessage.hidden = true;
    try {
      const wasEditing = Boolean(editingMachine);
      const saved = wasEditing
        ? await api(`/api/users/me/gym/machines/${editingMachine.machine_id}`, { method: "PATCH", body: JSON.stringify(payload) })
        : await api("/api/users/me/gym/machines", { method: "POST", body: JSON.stringify(payload) });
      if (image) {
        const data = new FormData();
        data.append("file", image);
        try {
          await api(`/api/users/me/gym/machines/${saved.machine_id}/image`, { method: "POST", body: data });
        } catch (imageError) {
          if (!wasEditing) {
            await api(`/api/users/me/gym/machines/${saved.machine_id}`, { method: "DELETE" }).catch(() => null);
          } else {
            await api(`/api/users/me/gym/machines/${saved.machine_id}`, {
              method: "PATCH",
              body: JSON.stringify({
                machine_name: editingMachine.machine_name,
                body_part: editingMachine.body_part,
                brand: editingMachine.brand,
                model_name: editingMachine.model_name,
                description: editingMachine.description,
                usage_guide: editingMachine.usage_guide,
                caution: editingMachine.caution,
                remove_image: false,
              }),
            }).catch(() => null);
          }
          throw imageError;
        }
      }
      formDirty = false;
      closeSheet(elements.machineFormOverlay);
      await loadMachines();
      showToast(wasEditing ? "머신 정보를 수정했습니다." : "머신을 등록했습니다.");
    } catch (error) {
      elements.machineFormMessage.textContent = error.message;
      elements.machineFormMessage.hidden = false;
    } finally {
      submitting = false;
      elements.machineFormSubmit.disabled = false;
    }
  }

  function openDelete(machine, trigger) {
    deletingMachine = machine;
    elements.machineDeleteName.textContent = machine.machine_name;
    returnFocus = trigger || document.activeElement;
    openSheet(elements.machineDeleteOverlay, byId("machineDeleteCancel"));
  }

  async function confirmDelete() {
    if (!deletingMachine || deleting) return;
    deleting = true;
    elements.machineDeleteConfirm.disabled = true;
    try {
      await api(`/api/users/me/gym/machines/${deletingMachine.machine_id}`, { method: "DELETE" });
      closeSheet(elements.machineDeleteOverlay);
      await loadMachines();
      showToast("머신을 목록에서 삭제했습니다.");
    } catch (error) {
      showToast(error.message);
    } finally {
      deleting = false;
      elements.machineDeleteConfirm.disabled = false;
    }
  }

  elements.machineSearch.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(loadMachines, 250);
  });
  elements.machineCreateButton.addEventListener("click", (event) => openForm(null, event.currentTarget));
  elements.machineEmptyCreate.addEventListener("click", (event) => openForm(null, event.currentTarget));
  byId("machineRetry").addEventListener("click", loadMachines);
  byId("machineDetailClose").addEventListener("click", () => closeSheet(elements.machineDetailOverlay));
  byId("machineDetailBackdrop").addEventListener("click", () => closeSheet(elements.machineDetailOverlay));
  byId("machineFormClose").addEventListener("click", closeFormSheet);
  byId("machineFormBackdrop").addEventListener("click", closeFormSheet);
  elements.machineForm.addEventListener("submit", submitForm);
  elements.machineForm.addEventListener("input", () => { formDirty = true; });
  elements.machineForm.addEventListener("change", () => { formDirty = true; });
  elements.machineImageInput.addEventListener("change", () => {
    revokePreview();
    const file = elements.machineImageInput.files[0];
    if (file) { previewUrl = URL.createObjectURL(file); setPreview(previewUrl); imageRemoved = false; }
  });
  byId("machineImageRemove").addEventListener("click", () => {
    elements.machineImageInput.value = "";
    revokePreview();
    setPreview("");
    imageRemoved = true;
    formDirty = true;
  });
  [elements.machineDescriptionInput, elements.machineUsageInput, elements.machineCautionInput]
    .forEach((input) => input.addEventListener("input", updateCounts));
  byId("machineDeleteClose").addEventListener("click", () => closeSheet(elements.machineDeleteOverlay));
  byId("machineDeleteBackdrop").addEventListener("click", () => closeSheet(elements.machineDeleteOverlay));
  byId("machineDeleteCancel").addEventListener("click", () => closeSheet(elements.machineDeleteOverlay));
  elements.machineDeleteConfirm.addEventListener("click", confirmDelete);
  window.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    if (!elements.machineDeleteOverlay.hidden) closeSheet(elements.machineDeleteOverlay);
    else if (!elements.machineFormOverlay.hidden) closeFormSheet();
    else if (!elements.machineDetailOverlay.hidden) closeSheet(elements.machineDetailOverlay);
  });
  window.addEventListener("pagehide", revokePreview);
  loadMachines();
})();
