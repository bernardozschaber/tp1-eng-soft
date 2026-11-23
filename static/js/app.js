// Theme. The attribute is already on <html> (set pre-paint in base.html); this
// only handles the toggle and keeps following the OS while the user has not
// made an explicit choice.
(function () {
  const THEME_KEY = "bernoullipay.theme";
  const root = document.documentElement;
  const system = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function stored() {
    try {
      const v = localStorage.getItem(THEME_KEY);
      return v === "dark" || v === "light" ? v : null;
    } catch (_) { return null; }
  }

  function apply(theme) {
    root.setAttribute("data-theme", theme);
    const dark = theme === "dark";
    document.querySelectorAll("[data-theme-toggle]").forEach((el) => {
      el.setAttribute("aria-pressed", String(dark));
      const label = dark ? "Usar modo claro" : "Usar modo escuro";
      el.setAttribute("aria-label", label);
      el.setAttribute("title", label);
    });
  }

  apply(stored() || root.getAttribute("data-theme") || "light");

  if (system) {
    system.addEventListener("change", () => { if (!stored()) apply(system.matches ? "dark" : "light"); });
  }

  document.addEventListener("click", (event) => {
    if (!event.target.closest("[data-theme-toggle]")) return;
    const next = root.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try { localStorage.setItem(THEME_KEY, next); } catch (_) { /* ignore */ }
    apply(next);
  });
})();

// Seletor de página: trocar a opção já navega. O botão "Ir" fica para quem
// está sem JS — com script, ele some para não sobrar um passo a mais.
(function () {
  document.querySelectorAll("[data-autosubmit]").forEach((select) => {
    const form = select.form;
    if (!form) return;
    select.addEventListener("change", () => form.requestSubmit());
    form.querySelectorAll("[data-autosubmit-go]").forEach((button) => { button.hidden = true; });
  });
})();
