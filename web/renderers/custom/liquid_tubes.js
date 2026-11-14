const TUBE_COLORS = [
  "#FA8231",
  "#00F5D4",
  "#FF007F",
  "#FFE600",
  "#01CA6B",
  "#B9A7E3",
  "#E76C8F",
  "#3867D6",
];

export function render(stage, solver, renderState, highlights) {
  stage.innerHTML = "";
  const tubes = renderState?.tubes || [];
  const caps = renderState?.capacities || tubes.map(() => 4);

  const rack = document.createElement("div");
  rack.className = "tubes-rack";

  tubes.forEach((tube, idx) => {
    const wrap = document.createElement("div");
    wrap.className = "tube-wrap";
    if (highlights.src === idx) wrap.classList.add("src");
    if (highlights.dst === idx) wrap.classList.add("dst");

    const cap = caps[idx] || 4;
    const body = document.createElement("div");
    body.className = "tube-body";
    body.style.height = `${cap * 32 + 16}px`;

    tube.forEach((colorId) => {
      const seg = document.createElement("div");
      seg.className = "tube-seg";
      seg.style.background = TUBE_COLORS[colorId % TUBE_COLORS.length];
      seg.textContent = String(colorId + 1);
      body.appendChild(seg);
    });

    const lbl = document.createElement("div");
    lbl.style.fontSize = "11px";
    lbl.style.color = "var(--text-muted)";
    lbl.textContent = `Tube ${idx + 1} (${tube.length}/${cap})`;

    wrap.appendChild(body);
    wrap.appendChild(lbl);
    rack.appendChild(wrap);
  });

  stage.appendChild(rack);
}
