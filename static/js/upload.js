// Upload page: show the chosen files, support drag-and-drop, enable the button.
(function () {
  const input = document.getElementById("file-input");
  const dropzone = document.getElementById("dropzone");
  const list = document.getElementById("file-list");
  const button = document.getElementById("upload-button");
  if (!input || !dropzone) return;

  function formatSize(bytes) {
    return bytes > 1024 * 1024 ? (bytes / 1024 / 1024).toFixed(1) + " MB" : Math.round(bytes / 1024) + " KB";
  }

  function renderList() {
    const files = Array.from(input.files);
    list.innerHTML = files.map((file) =>
      `<div class="row between" style="padding:6px 0;border-bottom:1px solid var(--border-tertiary)"><span>${file.name}</span><span class="muted small">${formatSize(file.size)}</span></div>`
    ).join("");
    button.disabled = files.length === 0;
  }

  input.addEventListener("change", renderList);
  ["dragenter", "dragover"].forEach((type) => dropzone.addEventListener(type, (event) => { event.preventDefault(); dropzone.classList.add("is-dragover"); }));
  ["dragleave", "drop"].forEach((type) => dropzone.addEventListener(type, () => dropzone.classList.remove("is-dragover")));
  dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    input.files = event.dataTransfer.files;
    renderList();
  });
})();
