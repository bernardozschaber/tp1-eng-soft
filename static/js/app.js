// Shell behaviour shared by every page: sidebar toggle persisted per browser.
// Below 1024px the sidebar is an overlay drawer, so it always starts closed,
// gets a backdrop, and closes on Escape or an outside click.
(function () {
  const SIDEBAR_KEY = "bernoullipay.sidebar.hidden";
  const sidebar = document.getElementById("sidebar");
  const toggle = document.querySelector("[data-toggle-sidebar]");
  if (!sidebar || !toggle) return;

  const drawer = window.matchMedia("(max-width: 1024px)");
  let backdrop = null;

  function readHidden() {
    try { return localStorage.getItem(SIDEBAR_KEY) === "1"; } catch (_) { return false; }
  }
  function writeHidden(hidden) {
    try { localStorage.setItem(SIDEBAR_KEY, hidden ? "1" : "0"); } catch (_) { /* ignore */ }
  }

  function syncBackdrop() {
    const needed = drawer.matches && !sidebar.hidden;
    if (needed && !backdrop) {
      backdrop = document.createElement("button");
      backdrop.type = "button";
      backdrop.className = "sidebar-backdrop";
      backdrop.setAttribute("aria-label", "Fechar barra lateral");
      backdrop.addEventListener("click", () => setHidden(true, true));
      document.body.appendChild(backdrop);
    } else if (!needed && backdrop) {
      backdrop.remove();
      backdrop = null;
    }
  }

  function setHidden(hidden, restoreFocus) {
    sidebar.hidden = hidden;
    toggle.setAttribute("aria-expanded", String(!hidden));
    if (!drawer.matches) writeHidden(hidden);
    syncBackdrop();
    if (hidden && restoreFocus) toggle.focus();
  }

  // On the drawer breakpoint the stored desktop preference must not leak in.
  setHidden(drawer.matches ? true : readHidden(), false);
  drawer.addEventListener("change", () => setHidden(drawer.matches ? true : readHidden(), false));

  toggle.addEventListener("click", () => setHidden(!sidebar.hidden, false));
  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && drawer.matches && !sidebar.hidden) setHidden(true, true);
  });
})();