(function () {
  const instances = new Map();
  let openInstance = null;

  const chevron = '<svg class="gymfit-select-chevron" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 9l5 5 5-5" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"></path></svg>';

  function optionsOf(select) {
    return Array.from(select.options);
  }

  function selectedOption(select) {
    return optionsOf(select).find(option => option.value === select.value) || select.options[select.selectedIndex] || null;
  }

  function getLabel(select) {
    if (select.getAttribute("aria-label")) return select.getAttribute("aria-label");
    const label = select.id ? document.querySelector(`label[for="${CSS.escape(select.id)}"]`) : null;
    const parentLabel = select.closest("label");
    return (label || parentLabel)?.textContent?.trim() || "선택";
  }

  function refresh(select) {
    const instance = instances.get(select);
    if (!instance) return;
    const option = selectedOption(select);
    instance.value.textContent = option?.textContent?.trim() || "선택";
    instance.wrapper.classList.toggle("is-placeholder", !option || option.value === "");
    instance.trigger.disabled = select.disabled;
    instance.trigger.setAttribute("aria-disabled", String(select.disabled));
    instance.wrapper.classList.toggle("is-invalid", select.matches(":invalid") && select.dataset.gymfitTouched === "true");
    if (openInstance === instance) renderPanel(instance);
  }

  function close(instance, restoreFocus = false) {
    if (!instance || openInstance !== instance) return;
    instance.portal?.remove();
    instance.portal = null;
    instance.wrapper.classList.remove("is-open");
    instance.trigger.setAttribute("aria-expanded", "false");
    openInstance = null;
    if (restoreFocus) instance.trigger.focus();
  }

  function closeAll() {
    if (openInstance) close(openInstance);
  }

  function positionPanel(instance) {
    if (!instance.portal) return;
    const rect = instance.trigger.getBoundingClientRect();
    const gap = 6;
    const padding = 12;
    const viewportHeight = window.innerHeight;
    const viewportWidth = window.innerWidth;
    const preferredHeight = Math.min(300, Math.max(54, instance.portal.scrollHeight + 12));
    const spaceBelow = viewportHeight - rect.bottom - padding;
    const spaceAbove = rect.top - padding;
    const openUpward = spaceBelow < preferredHeight && spaceAbove > spaceBelow;
    const available = Math.max(96, (openUpward ? spaceAbove : spaceBelow) - gap);
    const panelHeight = Math.min(preferredHeight, available);
    const maxWidth = Math.max(1, Math.floor(viewportWidth - padding * 2));
    const width = Math.max(1, Math.min(Math.floor(rect.width), maxWidth));
    const maxLeft = Math.max(padding, Math.floor(viewportWidth - padding - width));
    const left = Math.min(Math.max(Math.round(rect.left), padding), maxLeft);
    const top = openUpward ? Math.max(padding, rect.top - panelHeight - gap) : rect.bottom + gap;
    Object.assign(instance.portal.style, {
      left: `${left}px`,
      top: `${top}px`,
      width: `${width}px`,
      maxHeight: `${panelHeight}px`,
    });
  }

  function focusOption(instance, index) {
    const enabled = Array.from(instance.portal.querySelectorAll('.gymfit-select-option:not([aria-disabled="true"])'));
    if (!enabled.length) return;
    const nextIndex = Math.max(0, Math.min(index, enabled.length - 1));
    enabled.forEach(option => option.classList.remove("is-active"));
    enabled[nextIndex].classList.add("is-active");
    enabled[nextIndex].focus({ preventScroll: true });
    enabled[nextIndex].scrollIntoView({ block: "nearest" });
  }

  function choose(instance, option) {
    if (option.disabled) return;
    instance.select.value = option.value;
    instance.select.dataset.gymfitTouched = "true";
    instance.select.dispatchEvent(new Event("change", { bubbles: true }));
    refresh(instance.select);
    close(instance, true);
  }

  function renderPanel(instance) {
    if (!instance.portal) return;
    instance.portal.replaceChildren();
    optionsOf(instance.select).forEach((option, index) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "gymfit-select-option";
      button.id = `${instance.id}-option-${index}`;
      button.setAttribute("role", "option");
      button.setAttribute("aria-selected", String(option.value === instance.select.value));
      button.setAttribute("aria-disabled", String(option.disabled));
      button.dataset.optionIndex = String(index);
      button.textContent = option.textContent.trim();
      button.addEventListener("click", () => choose(instance, option));
      instance.portal.append(button);
    });
    positionPanel(instance);
  }

  function open(instance) {
    if (instance.select.disabled) return;
    if (openInstance && openInstance !== instance) close(openInstance);
    if (openInstance === instance) { close(instance); return; }
    const portal = document.createElement("div");
    portal.className = "gymfit-select-portal";
    portal.id = `${instance.id}-listbox`;
    portal.setAttribute("role", "listbox");
    portal.setAttribute("aria-label", getLabel(instance.select));
    document.body.append(portal);
    portal.addEventListener("keydown", event => handleKeydown(instance, event));
    instance.portal = portal;
    openInstance = instance;
    instance.wrapper.classList.add("is-open");
    instance.trigger.setAttribute("aria-expanded", "true");
    instance.trigger.setAttribute("aria-controls", portal.id);
    renderPanel(instance);
    const enabled = Array.from(portal.querySelectorAll('.gymfit-select-option:not([aria-disabled="true"])'));
    const selectedIndex = enabled.findIndex(option => option.getAttribute("aria-selected") === "true");
    focusOption(instance, selectedIndex >= 0 ? selectedIndex : 0);
  }

  function handleKeydown(instance, event) {
    if (["Enter", " ", "ArrowDown", "ArrowUp"].includes(event.key) && openInstance !== instance) {
      event.preventDefault();
      open(instance);
      return;
    }
    if (openInstance !== instance) return;
    const enabled = Array.from(instance.portal.querySelectorAll('.gymfit-select-option:not([aria-disabled="true"])'));
    const current = Math.max(0, enabled.indexOf(document.activeElement));
    if (event.key === "Escape") { event.preventDefault(); event.stopPropagation(); close(instance, true); }
    else if (event.key === "Tab") close(instance);
    else if (event.key === "ArrowDown") { event.preventDefault(); focusOption(instance, current + 1); }
    else if (event.key === "ArrowUp") { event.preventDefault(); focusOption(instance, current - 1); }
    else if (event.key === "Home") { event.preventDefault(); focusOption(instance, 0); }
    else if (event.key === "End") { event.preventDefault(); focusOption(instance, enabled.length - 1); }
    else if ((event.key === "Enter" || event.key === " ") && document.activeElement?.classList.contains("gymfit-select-option")) {
      event.preventDefault();
      const option = instance.select.options[Number(document.activeElement.dataset.optionIndex)];
      choose(instance, option);
    }
  }

  function initSelect(select) {
    if (!(select instanceof HTMLSelectElement) || instances.has(select) || select.classList.contains("assignment-native-select")) return;
    const wrapper = document.createElement("div");
    wrapper.className = "gymfit-select";
    const trigger = document.createElement("button");
    trigger.type = "button";
    trigger.className = "gymfit-select-trigger";
    trigger.setAttribute("aria-haspopup", "listbox");
    trigger.setAttribute("aria-expanded", "false");
    trigger.setAttribute("aria-label", getLabel(select));
    const value = document.createElement("span");
    value.className = "gymfit-select-value";
    trigger.append(value);
    trigger.insertAdjacentHTML("beforeend", chevron);
    select.insertAdjacentElement("afterend", wrapper);
    wrapper.append(trigger);
    select.classList.add("gymfit-select-native");
    const instance = { id: `gymfit-select-${instances.size + 1}`, select, wrapper, trigger, value, portal: null, observer: null, tabIndex: select.tabIndex };
    instances.set(select, instance);
    select.tabIndex = -1;
    trigger.addEventListener("click", () => open(instance));
    trigger.addEventListener("keydown", event => handleKeydown(instance, event));
    select.addEventListener("focus", () => trigger.focus());
    select.addEventListener("change", () => refresh(select));
    select.addEventListener("invalid", () => { select.dataset.gymfitTouched = "true"; refresh(select); trigger.focus(); });
    select.form?.addEventListener("reset", () => window.setTimeout(() => refresh(select)));
    instance.observer = new MutationObserver(() => refresh(select));
    instance.observer.observe(select, { childList: true, subtree: true, attributes: true, attributeFilter: ["disabled", "selected", "label"] });
    refresh(select);
  }

  function init(root = document) {
    root.querySelectorAll("select[data-gymfit-select]").forEach(initSelect);
  }

  function destroy(select) {
    const instance = instances.get(select);
    if (!instance) return;
    if (openInstance === instance) close(instance);
    instance.observer?.disconnect();
    instance.wrapper.remove();
    select.classList.remove("gymfit-select-native");
    select.tabIndex = instance.tabIndex;
    instances.delete(select);
  }

  document.addEventListener("pointerdown", event => {
    if (!openInstance) return;
    if (!openInstance.wrapper.contains(event.target) && !openInstance.portal?.contains(event.target)) close(openInstance);
  }, true);
  window.addEventListener("resize", closeAll);
  window.addEventListener("scroll", event => {
    if (openInstance?.portal && event.target === openInstance.portal) return;
    closeAll();
  }, true);
  window.addEventListener("pagehide", () => { closeAll(); instances.forEach((_, select) => destroy(select)); });
  document.addEventListener("DOMContentLoaded", () => init());
  window.GymfitDropdown = { init, refresh, destroy, closeAll };
})();
