// Shell behaviour shared by every page: sidebar toggle persisted per browser.
(function () {
  const SIDEBAR_KEY = "provapay.sidebar.hidden";
  const sidebar = document.getElementById("sidebar");
  const toggle = document.querySelector("[data-toggle-sidebar]");
  if (!sidebar || !toggle) return;

  function readHidden() {
    try { return localStorage.getItem(SIDEBAR_KEY) === "1"; } catch (_) { return false; }
  }
  function writeHidden(hidden) {
    try { localStorage.setItem(SIDEBAR_KEY, hidden ? "1" : "0"); } catch (_) { /* ignore */ }
  }

  sidebar.hidden = readHidden();
  toggle.addEventListener("click", function () {
    sidebar.hidden = !sidebar.hidden;
    writeHidden(sidebar.hidden);
  });
})();
