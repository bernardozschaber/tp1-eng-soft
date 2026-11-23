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

// Importações recentes: seleção múltipla e exclusão em lote. O botão só existe
// quando há seleção — uma ação destrutiva não fica à espreita numa barra vazia.
(function () {
  const form = document.getElementById("batches-form");
  const all = document.getElementById("batches-all");
  const button = document.getElementById("bulk-delete");
  if (!form || !all || !button) return;
  const boxes = Array.from(form.querySelectorAll("[data-batch]"));
  const label = button.querySelector("[data-bulk-label]");
  if (!boxes.length) {
    all.disabled = true;
    return;
  }

  function selected() {
    return boxes.filter((box) => box.checked);
  }

  function entriesIn(chosen) {
    return chosen.reduce((total, box) => total + (Number(box.dataset.entries) || 0), 0);
  }

  function sync() {
    const chosen = selected();
    all.checked = chosen.length === boxes.length;
    all.indeterminate = chosen.length > 0 && chosen.length < boxes.length;
    button.hidden = chosen.length === 0;
    if (chosen.length) {
      const entries = entriesIn(chosen);
      label.textContent =
        "Excluir " + chosen.length + " selecionada" + (chosen.length > 1 ? "s" : "") +
        " · " + entries + " lançamento" + (entries === 1 ? "" : "s");
    }
  }

  all.addEventListener("change", () => {
    boxes.forEach((box) => { box.checked = all.checked; });
    sync();
  });
  boxes.forEach((box) => box.addEventListener("change", sync));

  form.addEventListener("submit", (event) => {
    // O X de cada linha tem formaction próprio e já confirmou no clique; esta
    // confirmação é só da exclusão em lote.
    if (event.submitter !== button) return;
    const chosen = selected();
    const entries = entriesIn(chosen);
    const question =
      "Excluir " + chosen.length + " importação(ões) e os " + entries +
      " lançamento(s) que elas criaram?";
    if (!confirm(question)) event.preventDefault();
  });

  sync();
})();
