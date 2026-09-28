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

// Nomes a confirmar: uma pergunta por vez, num card sobre a conferência — ou
// "é a mesma pessoa?" para nomes parecidos, ou "criar um novo cadastro?" para
// quem não casa com ninguém. O submit do formulário só passa quando todas as
// perguntas têm resposta — é o pedido de confirmar uma a uma, feito valer
// também quando alguém dá Enter na página.
(function () {
  const form = document.getElementById("confirm-form");
  const dialog = document.getElementById("merge-dialog");
  if (!form || !dialog) return;
  const questions = Array.from(dialog.querySelectorAll("[data-merge-question]"));
  const step = dialog.querySelector("[data-merge-step]");
  const card = dialog.querySelector(".modal__card");
  const title = dialog.querySelector("#merge-title");
  const lead = dialog.querySelector("[data-merge-lead]");
  const yes = dialog.querySelector('[data-merge-answer="sim"]');
  const no = dialog.querySelector('[data-merge-answer="nao"]');
  const back = dialog.querySelector("[data-merge-back]");
  const link = dialog.querySelector("[data-merge-link]");
  const picker = dialog.querySelector("[data-merge-picker]");
  const search = dialog.querySelector("[data-picker-search]");
  const options = picker ? Array.from(picker.querySelectorAll("[data-picker-option]")) : [];
  const emptyNote = picker ? picker.querySelector("[data-picker-empty]") : null;
  const notice = document.getElementById("merge-notice");
  if (!questions.length) return;

  let current = 0;
  let submitAfter = false;
  let opener = null;

  const inputFor = (question) => form.querySelector(`input[name="${question.dataset.input}"]`);
  const pending = () => questions.findIndex((question) => !inputFor(question).value);

  function show(index) {
    current = Math.max(0, Math.min(index, questions.length - 1));
    questions.forEach((question, position) => { question.hidden = position !== current; });
    // Cada pergunta carrega o próprio texto: o card é um só, a conversa não.
    const data = questions[current].dataset;
    title.textContent = data.title;
    lead.textContent = data.lead;
    yes.textContent = data.yes;
    no.textContent = data.no;
    // "Associar a outro aplicador" só existe na pergunta de criação: numa
    // pergunta de junção o outro cadastro já é a proposta em tela.
    if (link) {
      link.hidden = !data.link;
      link.textContent = data.link || link.textContent;
    }
    closePicker();
    step.textContent = String(current + 1);
    back.disabled = current === 0;
    card.focus();
  }

  function open(index) {
    opener = document.activeElement;
    dialog.hidden = false;
    show(index);
  }

  function close() {
    dialog.hidden = true;
    submitAfter = false;
    closePicker();
    if (opener && opener.focus) opener.focus();
  }

  function closePicker() {
    if (!picker) return;
    picker.hidden = true;
    if (search) search.value = "";
    filterOptions("");
  }

  function filterOptions(term) {
    const needle = term.trim().toLowerCase();
    let shown = 0;
    options.forEach((option) => {
      const match = !needle || option.dataset.name.toLowerCase().includes(needle);
      option.parentElement.hidden = !match;
      if (match) shown += 1;
    });
    if (emptyNote) emptyNote.hidden = shown > 0;
  }

  function answer(value) {
    inputFor(questions[current]).value = value;
    markAnswered(questions[current], value);
    updateNotice();
    const next = pending();
    if (next === -1) {
      close();
      if (submitAfter) form.requestSubmit();
      return;
    }
    show(next);
  }

  function markAnswered(question, value) {
    // O nome escolhido fica escrito na pergunta: quem voltar para revisar
    // precisa ver em qual cadastro aquele pagamento caiu.
    const slot = question.querySelector("[data-merge-chosen]");
    if (!slot) return;
    const option = options.find((candidate) => candidate.dataset.pickerOption === value);
    slot.textContent = option ? `Será lançado no cadastro de ${option.dataset.name}.` : "";
    slot.hidden = !option;
  }

  function updateNotice() {
    if (!notice) return;
    const left = questions.filter((question) => !inputFor(question).value).length;
    notice.classList.toggle("alert--success", left === 0);
    notice.classList.toggle("alert--warning", left > 0);
    const label = notice.querySelector("[data-merge-open]");
    if (label) label.textContent = left ? "Conferir agora" : "Revisar respostas";
  }

  dialog.querySelectorAll("[data-merge-answer]").forEach((button) =>
    button.addEventListener("click", () => answer(button.dataset.mergeAnswer))
  );
  if (link && picker) {
    link.addEventListener("click", () => {
      picker.hidden = !picker.hidden;
      if (!picker.hidden && search) search.focus();
    });
    if (search) search.addEventListener("input", () => filterOptions(search.value));
    options.forEach((option) =>
      option.addEventListener("click", () => answer(option.dataset.pickerOption))
    );
  }
  back.addEventListener("click", () => show(current - 1));
  dialog.querySelectorAll("[data-merge-cancel]").forEach((element) => element.addEventListener("click", close));
  document.addEventListener("keydown", (event) => {
    if (dialog.hidden) return;
    if (event.key === "Escape") { close(); return; }
    // Atalho para a pergunta "é a mesma pessoa?": seta direita confirma
    // (mesma pessoa / criar cadastro), seta esquerda nega. Não dispara
    // dentro da busca de cadastro, onde as setas movem o cursor do texto.
    if (search && event.target === search) return;
    if (event.key === "ArrowRight") { event.preventDefault(); answer("sim"); }
    if (event.key === "ArrowLeft") { event.preventDefault(); answer("nao"); }
  });
  document.querySelectorAll("[data-merge-open]").forEach((button) =>
    button.addEventListener("click", () => open(pending() === -1 ? 0 : pending()))
  );

  form.addEventListener("submit", (event) => {
    const next = pending();
    if (next === -1) return;
    event.preventDefault();
    submitAfter = true;
    open(next);
  });

  updateNotice();
})();