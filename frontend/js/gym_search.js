(function () {
  function escapeHtml(value) {
    return String(value ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function getGymKey(gym) {
    if (!gym) return "";
    return [gym.provider || "", gym.external_place_id || gym.gym_id || ""].join(":");
  }

  window.createGymSearch = function createGymSearch(root, options = {}) {
    if (!root) {
      return { getValue: () => null, setValue: () => {} };
    }

    const queryInput = root.querySelector("[data-gym-query]");
    const searchButton = root.querySelector("[data-gym-search-button]");
    const status = root.querySelector("[data-gym-status]");
    const results = root.querySelector("[data-gym-results]");
    const selectedBox = root.querySelector("[data-selected-gym]");
    const selectedName = root.querySelector("[data-selected-gym-name]");
    const selectedAddress = root.querySelector("[data-selected-gym-address]");
    const clearButton = root.querySelector("[data-clear-gym]");
    const fieldScope = root.closest(".form-section") || root;
    const hiddenInputs = fieldScope.querySelectorAll("[data-gym-field]");
    let selected = options.initialValue || null;
    let resultItems = [];
    let searching = false;

    function syncHiddenInputs() {
      hiddenInputs.forEach((input) => {
        const field = input.dataset.gymField;
        input.value = selected && field ? String(selected[field] ?? "") : "";
      });
    }

    function renderSelected() {
      if (selectedBox) selectedBox.hidden = !selected;
      if (selected && selectedName) selectedName.textContent = selected.gym_name || "헬스장";
      if (selected && selectedAddress) {
        selectedAddress.textContent = selected.road_address || selected.address || "주소 정보 없음";
      }
    }

    function isSelected(item) {
      const itemKey = getGymKey(item);
      const selectedKey = getGymKey(selected);
      return Boolean(itemKey && selectedKey && itemKey === selectedKey);
    }

    function renderResults() {
      if (!results) return;
      results.replaceChildren();

      resultItems.forEach((item) => {
        const itemSelected = isSelected(item);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "gym-result-item";
        button.classList.toggle("selected", itemSelected);
        button.classList.toggle("active", itemSelected);
        button.setAttribute("aria-pressed", String(itemSelected));
        button.innerHTML =
          `<strong>${escapeHtml(item.gym_name)}</strong>` +
          `<span class="gym-result-address">${escapeHtml(item.road_address || item.address || "주소 정보 없음")}</span>` +
          `<span class="gym-result-action">${itemSelected ? "선택 해제" : "선택"}</span>`;
        button.addEventListener("click", () => {
          if (isSelected(item)) {
            clearSelection(false);
            return;
          }
          setSelected(item);
          status.textContent = "헬스장이 선택되었습니다.";
        });
        results.appendChild(button);
      });

      results.hidden = resultItems.length === 0;
    }

    function notifyChange() {
      options.onChange?.(selected);
    }

    function setSelected(value, notify = true) {
      selected = value || null;
      syncHiddenInputs();
      renderSelected();
      renderResults();
      if (notify) notifyChange();
    }

    function clearSelection(shouldFocus = true) {
      selected = null;
      syncHiddenInputs();
      renderSelected();
      renderResults();
      status.textContent = "선택된 헬스장이 없습니다. 다른 헬스장을 선택해 주세요.";
      if (shouldFocus) queryInput?.focus();
      notifyChange();
    }

    async function search() {
      const query = queryInput?.value.trim() || "";
      if (searching) return;
      if (query.length < 2) {
        status.textContent = "검색어를 두 글자 이상 입력해 주세요.";
        return;
      }

      searching = true;
      searchButton.disabled = true;
      status.textContent = "헬스장을 검색하고 있습니다.";
      try {
        const response = await fetch(`/api/gyms/search?query=${encodeURIComponent(query)}`);
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(body?.detail || "장소 검색에 실패했습니다.");
        resultItems = Array.isArray(body?.items) ? body.items : [];
        renderResults();
        status.textContent = resultItems.length
          ? `${resultItems.length}개의 장소를 찾았습니다.`
          : "검색 결과가 없습니다.";
      } catch (error) {
        resultItems = [];
        renderResults();
        status.textContent = error instanceof Error ? error.message : "장소 검색에 실패했습니다.";
      } finally {
        searching = false;
        searchButton.disabled = false;
      }
    }

    searchButton?.addEventListener("click", search);
    queryInput?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        search();
      }
    });
    clearButton?.addEventListener("click", () => clearSelection());

    setSelected(selected, false);
    return {
      getValue: () => selected,
      setValue: (value) => setSelected(value),
    };
  };
})();
