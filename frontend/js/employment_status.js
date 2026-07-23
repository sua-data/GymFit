(function () {
  function closeAll(except = null) {
    document.querySelectorAll("[data-employment-popover]").forEach((popover) => {
      if (popover === except) return;
      popover.hidden = true;
      popover.closest(".employment-info-wrap")?.querySelector("[data-employment-info]")?.setAttribute("aria-expanded", "false");
    });
  }
  document.addEventListener("click", (event) => {
    const button = event.target.closest("[data-employment-info]");
    if (button) {
      const wrap = button.closest(".employment-info-wrap");
      const popover = wrap?.querySelector("[data-employment-popover]");
      if (!popover) return;
      const willOpen = popover.hidden;
      closeAll(popover);
      popover.hidden = !willOpen;
      button.setAttribute("aria-expanded", String(willOpen));
      return;
    }
    if (!event.target.closest("[data-employment-popover]")) closeAll();
  });
  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeAll();
  });
})();
