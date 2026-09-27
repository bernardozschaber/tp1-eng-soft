// Preview page: collapse sheet blocks and grey-out excluded ones.
(function () {
  document.querySelectorAll("[data-sheet]").forEach((sheet) => {
    const toggle = sheet.querySelector("[data-sheet-toggle]");
    const collapse = sheet.querySelector("[data-collapse]");
    // Guard each independently: one malformed block must not stop the rest
    // of the sheets on the page from wiring up.
    if (toggle) {
      toggle.addEventListener("change", () => sheet.classList.toggle("is-excluded", !toggle.checked));
    }
    if (collapse) {
      collapse.setAttribute("aria-expanded", "true");
      collapse.addEventListener("click", () => {
        const collapsed = sheet.classList.toggle("is-collapsed");
        collapse.setAttribute("aria-expanded", String(!collapsed));
      });
    }
  });
})();