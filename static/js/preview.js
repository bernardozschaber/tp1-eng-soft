// Preview page: collapse sheet blocks and grey-out excluded ones.
(function () {
  document.querySelectorAll("[data-sheet]").forEach((sheet) => {
    const toggle = sheet.querySelector("[data-sheet-toggle]");
    const collapse = sheet.querySelector("[data-collapse]");
    toggle.addEventListener("change", () => sheet.classList.toggle("is-excluded", !toggle.checked));
    collapse.addEventListener("click", () => sheet.classList.toggle("is-collapsed"));
  });
})();
