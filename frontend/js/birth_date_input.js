(function () {
  const controllers = new WeakMap();

  function digitsOnly(value) {
    return String(value || "").replace(/\D/g, "").slice(0, 8);
  }

  function formatDigits(digits) {
    const parts = [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6, 8)];
    return parts.filter(Boolean).join(".");
  }

  function parseDigits(digits) {
    if (digits.length !== 8) return { value: "", error: "생년월일 8자리를 모두 입력해 주세요." };
    const year = Number(digits.slice(0, 4));
    const month = Number(digits.slice(4, 6));
    const day = Number(digits.slice(6, 8));
    if (year < 1900) return { value: "", error: "생년월일은 1900년 이후로 입력해 주세요." };
    const date = new Date(year, month - 1, day);
    if (date.getFullYear() !== year || date.getMonth() !== month - 1 || date.getDate() !== day) {
      return { value: "", error: "실제로 존재하는 날짜를 입력해 주세요." };
    }
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (date > today) return { value: "", error: "미래 날짜는 입력할 수 없습니다." };
    return {
      value: `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`,
      error: "",
    };
  }

  window.setupBirthDateInput = function setupBirthDateInput(options = {}) {
    const textInput = document.getElementById(options.textInputId || "birthDate");
    const picker = document.getElementById(options.pickerId || "birthDatePicker");
    const hiddenInput = document.getElementById(options.hiddenInputId || "birthDateValue");
    const errorElement = document.getElementById(options.errorId || "birthDateError");
    const calendarButton = document.getElementById(options.calendarButtonId || "birthCalendarButton");
    if (!textInput || !picker || !hiddenInput) return null;
    if (controllers.has(textInput)) return controllers.get(textInput);

    let composing = false;

    function setError(message) {
      if (!errorElement) return;
      errorElement.textContent = message;
      errorElement.hidden = !message;
    }

    function syncFromText({ showError = false } = {}) {
      const digits = digitsOnly(textInput.value);
      textInput.value = formatDigits(digits);
      const parsed = parseDigits(digits);
      hiddenInput.value = parsed.value;
      picker.value = parsed.value;
      if (showError && digits.length > 0) setError(parsed.error);
      else setError("");
      return parsed;
    }

    function handleInput() {
      if (!composing) syncFromText();
    }

    textInput.addEventListener("compositionstart", () => { composing = true; });
    textInput.addEventListener("compositionend", () => { composing = false; syncFromText(); });
    textInput.addEventListener("input", handleInput);
    textInput.addEventListener("blur", () => syncFromText({ showError: true }));
    picker.addEventListener("change", () => {
      const parsed = parseDigits(digitsOnly(picker.value));
      hiddenInput.value = parsed.value;
      textInput.value = parsed.value ? parsed.value.replaceAll("-", ".") : "";
      setError(parsed.error);
    });
    calendarButton?.addEventListener("click", () => {
      if (typeof picker.showPicker === "function") picker.showPicker();
      else picker.click();
    });

    const controller = {
      getValue() { return hiddenInput.value; },
      validate() {
        const parsed = syncFromText({ showError: true });
        return parsed.error;
      },
    };
    controllers.set(textInput, controller);
    syncFromText();
    return controller;
  };
})();
