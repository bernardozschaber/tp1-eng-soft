// Upload page: show the chosen files, support drag-and-drop, enable the button.
(function () {
  const input = document.getElementById("file-input");
  const dropzone = document.getElementById("dropzone");
  const list = document.getElementById("file-list");
  const button = document.getElementById("upload-button");
  if (!input || !dropzone || !list || !button) return;

  function formatSize(bytes) {
    return bytes > 1024 * 1024 ? (bytes / 1024 / 1024).toFixed(1) + " MB" : Math.round(bytes / 1024) + " KB";
  }

  function renderList() {
    const files = Array.from(input.files);
    list.textContent = "";
    files.forEach((file) => {
      // File names are untrusted input: build nodes and set text rather than
      // interpolating into innerHTML.
      const row = document.createElement("div");
      row.className = "row between file-row";
      const name = document.createElement("span");
      name.textContent = file.name;
      const size = document.createElement("span");
      size.className = "muted small";
      size.textContent = formatSize(file.size);
      row.append(name, size);
      list.appendChild(row);
    });
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