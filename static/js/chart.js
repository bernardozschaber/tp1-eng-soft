// Minimal dependency-free line chart with gradient fill, in the style of the
// Maybe net-worth chart. Reads `data-chart='[{"date":"2026-01-05","value":123}]'`.
(function () {
  const NS = "http://www.w3.org/2000/svg";
  const GREEN = "#10a861";

  function el(name, attrs) {
    const node = document.createElementNS(NS, name);
    Object.keys(attrs || {}).forEach((key) => node.setAttribute(key, attrs[key]));
    return node;
  }

  function formatDate(iso) {
    const [year, month, day] = iso.split("-");
    return `${day}/${month}/${year}`;
  }

  function render(container) {
    let points;
    try { points = JSON.parse(container.dataset.chart); } catch (_) { return; }
    if (!points || points.length === 0) return;
    if (points.length === 1) points = [{ ...points[0] }, points[0]];

    const width = 800, height = 220, padY = 12;
    const values = points.map((p) => p.value);
    const min = Math.min(0, ...values), max = Math.max(...values) || 1;
    const x = (i) => (i / (points.length - 1)) * width;
    const y = (v) => height - padY - ((v - min) / (max - min || 1)) * (height - padY * 2);

    const path = points.map((p, i) => `${i === 0 ? "M" : "L"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`).join(" ");
    const area = `${path} L${width},${height} L0,${height} Z`;

    const svg = el("svg", { viewBox: `0 0 ${width} ${height}`, preserveAspectRatio: "none" });
    const defs = el("defs");
    const gradient = el("linearGradient", { id: "chart-fill", x1: 0, y1: 0, x2: 0, y2: 1 });
    gradient.appendChild(el("stop", { offset: "0%", "stop-color": GREEN, "stop-opacity": 0.12 }));
    gradient.appendChild(el("stop", { offset: "100%", "stop-color": GREEN, "stop-opacity": 0 }));
    defs.appendChild(gradient);
    svg.appendChild(defs);
    svg.appendChild(el("path", { d: area, fill: "url(#chart-fill)" }));
    svg.appendChild(el("path", { d: path, fill: "none", stroke: GREEN, "stroke-width": 2, "vector-effect": "non-scaling-stroke" }));
    container.appendChild(svg);

    const axis = document.createElement("div");
    axis.className = "chart__axis";
    axis.innerHTML = `<span>${formatDate(points[0].date)}</span><span>${formatDate(points[points.length - 1].date)}</span>`;
    container.after(axis);
  }

  document.querySelectorAll("[data-chart]").forEach(render);

  // Ten-tick weight indicators used in allocation tables.
  document.querySelectorAll("[data-ticks]").forEach((node) => {
    const filled = Math.round(Number(node.dataset.ticks) / 10);
    for (let i = 0; i < 10; i += 1) {
      const tick = document.createElement("i");
      if (i < filled) tick.style.background = "var(--tick-color)";
      node.appendChild(tick);
    }
  });
})();
