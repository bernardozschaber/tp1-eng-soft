// Ficha do aplicador: Esc fecha, como em qualquer coisa que abre por cima.
(function () {
  const overlay = document.querySelector("[data-card-overlay]");
  if (!overlay) return;
  const back = overlay.querySelector(".sheet-overlay__backdrop");
  if (!back) return;
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") window.location.assign(back.getAttribute("href"));
  });
})();
