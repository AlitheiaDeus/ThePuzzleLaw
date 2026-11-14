export function render(stage, solver, renderState, highlights, editable, onEdit) {
  stage.innerHTML = "";
  const size = renderState?.size || 4;
  const clues = renderState?.cell_clues || [];
  const hEdges = renderState?.h_edges || [];
  const vEdges = renderState?.v_edges || [];

  const cell = Math.max(44, Math.min(72, Math.floor(360 / size)));
  const pad = 28;
  const dim = size * cell + pad * 2;

  const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  svg.setAttribute("width", String(dim));
  svg.setAttribute("height", String(dim));
  svg.style.background = "var(--bg-panel)";
  svg.style.borderRadius = "12px";
  svg.style.border = "1px solid var(--border)";

  const ns = "http://www.w3.org/2000/svg";

  // Cell clues (clickable in Edit mode to cycle None -> 0 -> 1 -> 2 -> 3)
  for (let r = 0; r < size; r++) {
    for (let c = 0; c < size; c++) {
      const val = clues[r]?.[c];
      const txt = document.createElementNS(ns, "text");
      txt.setAttribute("x", String(pad + c * cell + cell / 2));
      txt.setAttribute("y", String(pad + r * cell + cell / 2 + 7));
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("fill", val === null || val === undefined ? "transparent" : "var(--text-main)");
      txt.setAttribute("font-size", "20");
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

  const hl = highlights.edge;

  // Horizontal edges
  for (let r = 0; r <= size; r++) {
    for (let c = 0; c < size; c++) {
      const st = hEdges[r]?.[c] || 0;
      const isHl = hl && hl[0] === "h" && hl[1] === r && hl[2] === c;
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", String(pad + c * cell));
      line.setAttribute("y1", String(pad + r * cell));
      line.setAttribute("x2", String(pad + (c + 1) * cell));
      line.setAttribute("y2", String(pad + r * cell));
      line.setAttribute("stroke", st === 1 ? (isHl ? "var(--accent-secondary)" : "var(--accent-primary)") : "rgba(255,255,255,0.12)");
      line.setAttribute("stroke-width", st === 1 ? "5" : "2");
      line.setAttribute("stroke-linecap", "round");
      svg.appendChild(line);
    }
  }

  // Vertical edges
  for (let r = 0; r < size; r++) {
    for (let c = 0; c <= size; c++) {
      const st = vEdges[r]?.[c] || 0;
      const isHl = hl && hl[0] === "v" && hl[1] === r && hl[2] === c;
      const line = document.createElementNS(ns, "line");
      line.setAttribute("x1", String(pad + c * cell));
      line.setAttribute("y1", String(pad + r * cell));
      line.setAttribute("x2", String(pad + c * cell));
      line.setAttribute("y2", String(pad + (r + 1) * cell));
      line.setAttribute("stroke", st === 1 ? (isHl ? "var(--accent-secondary)" : "var(--accent-primary)") : "rgba(255,255,255,0.12)");
      line.setAttribute("stroke-width", st === 1 ? "5" : "2");
      line.setAttribute("stroke-linecap", "round");
      svg.appendChild(line);
    }
  }

  // Lattice vertices
  for (let r = 0; r <= size; r++) {
    for (let c = 0; c <= size; c++) {
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
