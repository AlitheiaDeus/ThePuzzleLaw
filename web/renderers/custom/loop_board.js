const PALISADE_ZONE_COLORS = [
  "rgba(0, 245, 212, 0.16)",
  "rgba(255, 0, 127, 0.16)",
  "rgba(255, 230, 0, 0.16)",
  "rgba(185, 167, 227, 0.22)",
  "rgba(250, 130, 49, 0.18)",
  "rgba(1, 202, 107, 0.16)",
  "rgba(105, 230, 208, 0.16)",
  "rgba(231, 108, 143, 0.18)",
  "rgba(56, 103, 214, 0.20)",
];

function validDivisors(total) {
  const out = [];
  for (let k = 2; k <= total; k++) {
    if (total % k === 0) out.push(k);
  }
  return out;
}

function resize2D(mat, rows, cols, fillVal) {
  return Array.from({ length: rows }, (_, r) =>
    Array.from({ length: cols }, (_, c) => (mat?.[r]?.[c] !== undefined ? mat[r][c] : fillVal)),
  );
}

export function render(stage, solver, renderState, highlights, editable, onEdit) {
  stage.innerHTML = "";
  const clues = renderState?.cell_clues || [];
  const rows = renderState?.rows || renderState?.size || clues.length || 4;
  const cols = renderState?.cols || renderState?.size || clues[0]?.length || 4;
  const hEdges = renderState?.h_edges || [];
  const vEdges = renderState?.v_edges || [];
  const zones = renderState?.zones || null;
  const hasRegionSize = renderState?.region_size !== undefined;

  if (editable) {
    const bar = document.createElement("div");
    bar.className = "grid-toolbar";

    const makeNum = (labelText, curVal, onPick) => {
      const wrap = document.createElement("label");
      wrap.style.display = "inline-flex";
      wrap.style.alignItems = "center";
      wrap.style.gap = "5px";
      wrap.style.fontSize = "12px";
      wrap.style.color = "var(--text-muted)";
      wrap.textContent = labelText;
      const sel = document.createElement("select");
      for (let d = 2; d <= 9; d++) {
        const o = document.createElement("option");
        o.value = String(d);
        o.textContent = String(d);
        if (d === curVal) o.selected = true;
        sel.appendChild(o);
      }
      sel.addEventListener("change", () => onPick(Number(sel.value)));
      wrap.appendChild(sel);
      return wrap;
    };

    const applyResize = (nr, nc, newK = null) => {
      const next = JSON.parse(JSON.stringify(renderState));
      next.rows = nr;
      next.cols = nc;
      if ("size" in next) next.size = nr === nc ? nr : Math.max(nr, nc);
      next.cell_clues = resize2D(clues, nr, nc, null);
      next.h_edges = Array.from({ length: nr + 1 }, () => Array(nc).fill(0));
      next.v_edges = Array.from({ length: nr }, () => Array(nc + 1).fill(0));
      delete next.zones;
      if (hasRegionSize) {
        const divs = validDivisors(nr * nc);
        const curK = newK ?? renderState.region_size;
        next.region_size = divs.includes(curK)
          ? curK
          : divs.reduce((a, b) => (Math.abs(b - curK) < Math.abs(a - curK) ? b : a), divs[0] || nr);
      }
      onEdit(next);
    };

    bar.appendChild(makeNum("Rows", rows, (nr) => applyResize(nr, cols)));
    bar.appendChild(makeNum("Columns", cols, (nc) => applyResize(rows, nc)));

    if (hasRegionSize) {
      const kWrap = document.createElement("label");
      kWrap.style.display = "inline-flex";
      kWrap.style.alignItems = "center";
      kWrap.style.gap = "5px";
      kWrap.style.fontSize = "12px";
      kWrap.style.color = "var(--text-muted)";
      kWrap.textContent = "Region Size (K)";
      const kSel = document.createElement("select");
      const divs = validDivisors(rows * cols);
      const curK = renderState.region_size;
      const opts = divs.includes(curK) ? divs : [curK, ...divs];
      for (const k of opts) {
        const o = document.createElement("option");
        o.value = String(k);
        o.textContent = String(k);
        if (k === curK) o.selected = true;
        kSel.appendChild(o);
      }
      kSel.addEventListener("change", () => applyResize(rows, cols, Number(kSel.value)));
      kWrap.appendChild(kSel);
      bar.appendChild(kWrap);
    }

    stage.appendChild(bar);
  }

  const maxSpan = Math.max(rows, cols);
  const cell = Math.max(40, Math.min(72, Math.floor(380 / maxSpan)));
  const pad = 28;
  const width = cols * cell + pad * 2;
  const height = rows * cell + pad * 2;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.style.background = "var(--bg-panel)";
  svg.style.borderRadius = "12px";
  svg.style.border = "1px solid var(--border)";

  const ns = "http://www.w3.org/2000/svg";

  // Cell zone tint (Palisade regions) + clickable clues (0-3)
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      if (zones && zones[r] && zones[r][c] !== undefined && zones[r][c] >= 0) {
        const rect = document.createElementNS(ns, "rect");
        rect.setAttribute("x", String(pad + c * cell));
        rect.setAttribute("y", String(pad + r * cell));
        rect.setAttribute("width", String(cell));
        rect.setAttribute("height", String(cell));
        rect.setAttribute("fill", PALISADE_ZONE_COLORS[zones[r][c] % PALISADE_ZONE_COLORS.length]);
        svg.appendChild(rect);
      }

      const val = clues[r]?.[c];
      const txt = document.createElementNS(ns, "text");
      txt.setAttribute("x", String(pad + c * cell + cell / 2));
      txt.setAttribute("y", String(pad + r * cell + cell / 2 + 7));
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("fill", val === null || val === undefined ? "transparent" : "var(--text-main)");
      txt.setAttribute("font-size", String(Math.max(15, Math.floor(cell * 0.34))));
      txt.setAttribute("font-weight", "700");
      txt.textContent = val === null || val === undefined ? "·" : String(val);
      if (editable) {
        txt.style.cursor = "pointer";
        txt.addEventListener("click", () => {
          const next = JSON.parse(JSON.stringify(renderState));
          const cur = next.cell_clues[r][c];
          next.cell_clues[r][c] = cur === null || cur === undefined ? 0 : cur >= 3 ? null : cur + 1;
          onEdit(next);
        });
      }
      svg.appendChild(txt);
    }
  }

  const hlList = Array.isArray(highlights.edges) ? highlights.edges : (highlights.edge ? [highlights.edge] : []);
  const isEdgeHl = (k, r, c) => hlList.some((e) => e[0] === k && e[1] === r && e[2] === c);

  // Horizontal edges
  for (let r = 0; r <= rows; r++) {
    for (let c = 0; c < cols; c++) {
      const st = hEdges[r]?.[c] || 0;
      const isHl = isEdgeHl("h", r, c);
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", String(pad + c * cell));
      line.setAttribute("y1", String(pad + r * cell));
      line.setAttribute("x2", String(pad + (c + 1) * cell));
      line.setAttribute("y2", String(pad + r * cell));
      line.setAttribute(
        "stroke",
        st === 1
          ? (isHl ? "var(--accent-secondary)" : "var(--accent-primary)")
          : st === -1
            ? (isHl ? "var(--accent-hot)" : "rgba(255,255,255,0.06)")
            : (isHl ? "var(--accent-hot)" : "rgba(255,255,255,0.16)"),
      );
      line.setAttribute("stroke-width", st === 1 ? "5" : isHl ? "3" : "2");
      if (st === -1) line.setAttribute("stroke-dasharray", "3 5");
      line.setAttribute("stroke-linecap", "round");
      svg.appendChild(line);

      if (editable) {
        const hit = document.createElementNS(ns, "line");
        hit.setAttribute("x1", String(pad + c * cell + 5));
        hit.setAttribute("y1", String(pad + r * cell));
        hit.setAttribute("x2", String(pad + (c + 1) * cell - 5));
        hit.setAttribute("y2", String(pad + r * cell));
        hit.setAttribute("stroke", "transparent");
        hit.setAttribute("stroke-width", "12");
        hit.style.cursor = "pointer";
        hit.addEventListener("click", () => {
          const next = JSON.parse(JSON.stringify(renderState));
          const cur = next.h_edges?.[r]?.[c] || 0;
          next.h_edges[r][c] = cur === 0 ? 1 : cur === 1 ? -1 : 0;
          onEdit(next);
        });
        svg.appendChild(hit);
      }
    }
  }

  // Vertical edges
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c <= cols; c++) {
      const st = vEdges[r]?.[c] || 0;
      const isHl = isEdgeHl("v", r, c);
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", String(pad + c * cell));
      line.setAttribute("y1", String(pad + r * cell));
      line.setAttribute("x2", String(pad + c * cell));
      line.setAttribute("y2", String(pad + (r + 1) * cell));
      line.setAttribute(
        "stroke",
        st === 1
          ? (isHl ? "var(--accent-secondary)" : "var(--accent-primary)")
          : st === -1
            ? (isHl ? "var(--accent-hot)" : "rgba(255,255,255,0.06)")
            : (isHl ? "var(--accent-hot)" : "rgba(255,255,255,0.16)"),
      );
      line.setAttribute("stroke-width", st === 1 ? "5" : isHl ? "3" : "2");
      if (st === -1) line.setAttribute("stroke-dasharray", "3 5");
      line.setAttribute("stroke-linecap", "round");
      svg.appendChild(line);

      if (editable) {
        const hit = document.createElementNS(ns, "line");
        hit.setAttribute("x1", String(pad + c * cell));
        hit.setAttribute("y1", String(pad + r * cell + 5));
        hit.setAttribute("x2", String(pad + c * cell));
        hit.setAttribute("y2", String(pad + (r + 1) * cell - 5));
        hit.setAttribute("stroke", "transparent");
        hit.setAttribute("stroke-width", "12");
        hit.style.cursor = "pointer";
        hit.addEventListener("click", () => {
          const next = JSON.parse(JSON.stringify(renderState));
          const cur = next.v_edges?.[r]?.[c] || 0;
          next.v_edges[r][c] = cur === 0 ? 1 : cur === 1 ? -1 : 0;
          onEdit(next);
        });
        svg.appendChild(hit);
      }
    }
  }

  // Lattice vertices
  for (let r = 0; r <= rows; r++) {
    for (let c = 0; c <= cols; c++) {
      const dot = document.createElementNS(ns, "circle");
      dot.setAttribute("cx", String(pad + c * cell));
      dot.setAttribute("cy", String(pad + r * cell));
      dot.setAttribute("r", "4");
      dot.setAttribute("fill", "var(--text-muted)");
      svg.appendChild(dot);
    }
  }

  stage.appendChild(svg);
}
