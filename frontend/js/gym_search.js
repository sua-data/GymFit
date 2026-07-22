(function () {
  function escapeHtml(value) {
    return String(value ?? "").replaceAll("&", "&amp;").replaceAll("<", "&lt;").replaceAll(">", "&gt;").replaceAll('"', "&quot;");
  }

  window.createGymSearch = function createGymSearch(root, options = {}) {
    const queryInput = root.querySelector("[data-gym-query]");
    const searchButton = root.querySelector("[data-gym-search-button]");
    const status = root.querySelector("[data-gym-status]");
    const results = root.querySelector("[data-gym-results]");
    const selectedBox = root.querySelector("[data-selected-gym]");
    const selectedName = root.querySelector("[data-selected-gym-name]");
    const selectedAddress = root.querySelector("[data-selected-gym-address]");
    const clearButton = root.querySelector("[data-clear-gym]");
    let selected = options.initialValue || null;
    let searching = false;

    function renderSelected() {
      selectedBox.hidden = !selected;
      if (selected) {
        selectedName.textContent = selected.gym_name || "헬스장";
        selectedAddress.textContent = selected.road_address || "주소 정보 없음";
      }
      options.onChange?.(selected);
    }

    async function search() {
      const query = queryInput.value.trim();
      if (searching || query.length < 2) {
        status.textContent = "검색어를 두 글자 이상 입력해 주세요.";
        return;
      }
      searching = true;
      searchButton.disabled = true;
      status.textContent = "헬스장을 검색하고 있습니다.";
      results.hidden = true;
      try {
        const response = await fetch(`/api/gyms/search?query=${encodeURIComponent(query)}`);
        const body = await response.json().catch(() => null);
        if (!response.ok) throw new Error(body?.detail || "장소 검색에 실패했습니다.");
        const items = Array.isArray(body?.items) ? body.items : [];
        results.replaceChildren();
        if (!items.length) {
          status.textContent = "검색 결과가 없습니다.";
          return;
        }
        items.forEach((item) => {
          const button = document.createElement("button");
          button.type = "button";
          button.className = "gym-result-item";
          button.innerHTML = `<strong>${escapeHtml(item.gym_name)}</strong><span>${escapeHtml(item.road_address || item.address)}</span>`;
          button.addEventListener("click", () => {
            selected = item;
            results.hidden = true;
            status.textContent = "헬스장이 선택되었습니다.";
            renderSelected();
          });
          results.appendChild(button);
        });
        results.hidden = false;
        status.textContent = `${items.length}개의 장소를 찾았습니다.`;
      } catch (error) {
        status.textContent = error instanceof Error ? error.message : "장소 검색에 실패했습니다.";
      } finally {
        searching = false;
        searchButton.disabled = false;
      }
    }

    searchButton.addEventListener("click", search);
    queryInput.addEventListener("keydown", (event) => {
      if (event.key === "Enter") { event.preventDefault(); search(); }
    });
    clearButton.addEventListener("click", () => {
      selected = null;
      selectedBox.hidden = true;
      status.textContent = "헬스장을 다시 검색해 주세요.";
      queryInput.focus();
      options.onChange?.(null);
    });
    renderSelected();
    return { getValue: () => selected, setValue: (value) => { selected = value; renderSelected(); } };
  };
})();
