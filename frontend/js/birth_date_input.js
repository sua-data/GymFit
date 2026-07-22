(function () {
  function parseDigits(digits) {
    if (digits.length !== 8) return null;
    const year = Number(digits.slice(0, 4));
    const month = Number(digits.slice(4, 6));
    const day = Number(digits.slice(6, 8));
    const value = new Date(year, month - 1, day);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    if (year < 1900 || value.getFullYear() !== year || value.getMonth() !== month - 1 || value.getDate() !== day || value > today) return null;
    return `${String(year).padStart(4, "0")}-${String(month).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
  }

  function formatDigits(value) {
    const digits = value.replace(/\D/g, "").slice(0, 8);
    return [digits.slice(0, 4), digits.slice(4, 6), digits.slice(6, 8)].filter(Boolean).join(".");
  }

  window.setupBirthDateInput = function setupBirthDateInput() {
    const textInput = document.querySelector("#birthDate");
    const picker = document.querySelector("#birthDatePicker");
    if (!textInput || !picker) return null;
    let apiValue = "";
    textInput.addEventListener("input", () => {
      textInput.value = formatDigits(textInput.value);
      apiValue = parseDigits(textInput.value.replace(/\D/g, "")) || "";
      if (apiValue) picker.value = apiValue;
    });
    picker.addEventListener("change", () => {
      const digits = picker.value.replace(/\D/g, "");
      apiValue = parseDigits(digits) || "";
      textInput.value = apiValue ? formatDigits(digits) : "";
      textInput.dispatchEvent(new Event("input", { bubbles: true }));
    });
    return {
      getValue() { return apiValue; },
      validate() {
        const digits = textInput.value.replace(/\D/g, "");
        if (digits.length !== 8) return "생년월일 8자리를 모두 입력해 주세요.";
        if (!parseDigits(digits)) return "1900년 이후의 실제 생년월일을 입력해 주세요.";
        return "";
      },
    };
  };
})();
