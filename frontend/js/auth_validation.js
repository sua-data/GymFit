(function () {
  function errorAnchor(input) {
    return input.closest(
      ".input-group, .birth-date-field, .form-field, .field-group, label"
    ) || input;
  }

  function clearField(input) {
    if (!input) return;
    input.removeAttribute("aria-invalid");
    const errorId = input.dataset.authErrorId;
    if (!errorId) return;
    document.getElementById(errorId)?.remove();
    delete input.dataset.authErrorId;
  }

  function clearAll(form) {
    form?.querySelectorAll("[data-auth-error-id]").forEach(clearField);
  }

  function show(input, message, fallback = null) {
    if (!input) {
      if (fallback) fallback.textContent = message;
      return;
    }
    clearField(input);
    if (fallback) fallback.textContent = "";
    const error = document.createElement("p");
    const baseId = input.id || input.name || "field";
    error.id = `${baseId}InlineError`;
    error.className = "auth-inline-error";
    error.setAttribute("role", "alert");
    error.textContent = message;
    errorAnchor(input).insertAdjacentElement("afterend", error);
    input.dataset.authErrorId = error.id;
    input.setAttribute("aria-invalid", "true");
  }

  function clearFromEvent(event) {
    if (event.target.matches("input, select, textarea")) clearField(event.target);
  }

  document.addEventListener("input", clearFromEvent);
  document.addEventListener("change", clearFromEvent);
  window.gymfitAuthValidation = { show, clearField, clearAll };
})();
