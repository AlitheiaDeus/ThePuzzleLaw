const ZONE_COLORS = [
  "rgba(0, 245, 212, 0.22)",
  "rgba(255, 0, 127, 0.22)",
  "rgba(255, 230, 0, 0.22)",
  "rgba(185, 167, 227, 0.28)",
  "rgba(250, 130, 49, 0.24)",
  "rgba(1, 202, 107, 0.22)",
  "rgba(105, 230, 208, 0.22)",
  "rgba(231, 108, 143, 0.25)",
];

let activeBrush = 1;

export function renderGrid(stage, solver, renderState, highlights, editable, onEdit) {
  stage.innerHTML = "";
  const board = renderState?.board;
  if (!Array.isArray(board) || board.length === 0) {
    stage.innerHTML = `<p style="color:var(--text-muted)">No board matrix in state.</p>`;
    return;
  }

  const rows = board.length;
  const cols = board[0].length;
  const gm = solver.grid_meta || {};
  const mode = gm.mode || "number";
  const colors = gm.colors || {};
  const labels = gm.labels || {};
  const canEdit = editable && gm.editable !== false;

  // Optional brush toolbar for palette mode (Flood, Flow)
  if (mode === "palette" && canEdit) {
    const bar = document.createElement("div");
    bar.className = "grid-toolbar";
    const maxVal = renderState.num_colors ? renderState.num_colors - 1 : (gm.max_val ?? 5);
    const minVal = gm.min_val ?? 0;
    if (activeBrush < minVal || activeBrush > maxVal) activeBrush = minVal;

    const lbl = document.createElement("span");
    lbl.style.fontSize = "12px";
    lbl.style.color = "var(--text-muted)";
    lbl.textContent = "Brush:";
    bar.appendChild(lbl);

    for (let v = minVal; v <= maxVal; v++) {
      const sw = document.createElement("button");
      sw.className = "palette-swatch" + (activeBrush === v ? " selected" : "");
      sw.style.background = colors[String(v)] || "#555";
      sw.title = `Value ${v}`;
      sw.addEventListener("click", () => {
        activeBrush = v;
        renderGrid(stage, solver, renderState, highlights, editable, onEdit);
      });
      bar.appendChild(sw);
    }
    stage.appendChild(bar);
  }

  const hlSet = new Set((highlights.cells || []).map(([r, c]) => `${r},${c}`));
  const hlClass = `hl-${highlights.color || "primary"}`;

  const cellSize = Math.max(30, Math.min(54, Math.floor(460 / Math.max(rows, cols))));
  const boardEl = document.createElement("div");
  boardEl.className = "board-frame";
  boardEl.style.gridTemplateColumns = `repeat(${cols}, ${cellSize}px)`;

  const boxW = renderState.box_w || gm.box_w || 0;
  const boxH = renderState.box_h || gm.box_h || 0;
  const zones = renderState.zones || null;
  const clues = renderState.clues || null;

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const val = board[r][c];
      const cell = document.createElement("div");
      cell.className = "grid-cell";
      cell.style.width = `${cellSize}px`;
      cell.style.height = `${cellSize}px`;
      cell.style.fontSize = `${Math.max(12, Math.floor(cellSize * 0.42))}px`;

      if (hlSet.has(`${r},${c}`)) {
        cell.classList.add(hlClass);
      }
      if (boxW > 0 && (c + 1) % boxW === 0 && c < cols - 1) {
        cell.classList.add("box-right");
      }
      if (boxH > 0 && (r + 1) % boxH === 0 && r < rows - 1) {
        cell.classList.add("box-bottom");
      }

      // Color styling
      if (zones && zones[r] && zones[r][c] !== undefined) {
        cell.style.background = ZONE_COLORS[zones[r][c] % ZONE_COLORS.length];
      } else if (colors[String(val)]) {
        cell.style.background = colors[String(val)];
        if (val !== 0 && mode !== "binary" && mode !== "cycle") {
          cell.style.color = "#111";
        }
      }

      // Token mode styling (Block Escape)
      if (mode === "token") {
        if (val === "#") {
          cell.style.background = "#474d56";
          cell.textContent = "▓";
        } else if (val === "★") {
          cell.style.background = "rgba(1, 202, 107, 0.22)";
          cell.style.color = "var(--accent-primary)";
          cell.textContent = "★";
        } else if (val) {
          cell.textContent = String(val);
          if (String(val).startsWith("T")) {
            cell.style.background = "var(--accent-primary)";
            cell.style.color = "#111";
          } else if (["A", "B", "C", "D"].includes(String(val))) {
            cell.style.background = "rgba(185, 167, 227, 0.25)";
            cell.style.color = "var(--accent-secondary)";
          } else {
            cell.style.background = "var(--accent-hot)";
            cell.style.color = "#fff";
          }
        }
      } else {
        const key = String(val);
        if (key in labels) {
          cell.textContent = labels[key];
        } else {
          cell.textContent = val === 0 ? "" : String(val);
        }
      }

      // Urjo corner clue
      if (clues && clues[r] && clues[r][c] !== null && clues[r][c] !== undefined) {
        const sub = document.createElement("span");
        sub.className = "cell-subclue";
        sub.textContent = String(clues[r][c]);
        cell.appendChild(sub);
      }

      if (canEdit) {
        cell.tabIndex = 0;
        cell.addEventListener("click", () => {
          const next = JSON.parse(JSON.stringify(renderState));
          if (mode === "palette") {
            next.board[r][c] = activeBrush;
          } else if (mode === "cycle" || mode === "binary") {
            const minV = gm.min_val ?? 0;
            const maxV = gm.max_val ?? 1;
            next.board[r][c] = val >= maxV ? minV : val + 1;
          } else if (mode === "number") {
            const maxV = renderState.grid_dim || (rows * cols - 1) || gm.max_val || 9;
            next.board[r][c] = val >= maxV ? 0 : val + 1;
          }
          onEdit(next);
        });
        cell.addEventListener("keydown", (e) => {
          if (mode !== "number") return;
          if (/^[0-9]$/.test(e.key)) {
            const d = Number(e.key);
            const maxV = renderState.grid_dim || rows * cols - 1;
            if (d <= maxV) {
              const next = JSON.parse(JSON.stringify(renderState));
              next.board[r][c] = d;
              onEdit(next);
            }
          } else if (e.key === "Backspace" || e.key === "Delete") {
            const next = JSON.parse(JSON.stringify(renderState));
            next.board[r][c] = 0;
            onEdit(next);
          }
        });
      }

      boardEl.appendChild(cell);
    }
  }

  // Optional SVG path overlay (Maze / Flow)
  if (Array.isArray(highlights.path) && highlights.path.length > 1) {
    const totalW = cols * cellSize + (cols - 1) * 3 + 20;
    const totalH = rows * cellSize + (rows - 1) * 3 + 20;
    const svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("width", String(totalW));
    svg.setAttribute("height", String(totalH));
    svg.style.position = "absolute";
    svg.style.inset = "0";
    svg.style.pointerEvents = "none";

    const pts = highlights.path
      .map(([pr, pc]) => {
        const x = 10 + pc * (cellSize + 3) + cellSize / 2;
        const y = 10 + pr * (cellSize + 3) + cellSize / 2;
        return `${x},${y}`;
      })
      .join(" ");

    const poly = document.createElementNS("http://www.w3.org/2000/svg", "polyline");
    poly.setAttribute("points", pts);
    poly.setAttribute("fill", "none");
    poly.setAttribute("stroke", "var(--accent-primary)");
    poly.setAttribute("stroke-width", "5");
    poly.setAttribute("stroke-linecap", "round");
    poly.setAttribute("stroke-linejoin", "round");
    svg.appendChild(poly);
    boardEl.appendChild(svg);
  }

  // Nonogram outer clues wrapper
  if (renderState.row_clues && renderState.col_clues) {
    const wrap = document.createElement("div");
    wrap.className = "board-with-clues";
    wrap.style.gridTemplateColumns = "auto auto";

    const corner = document.createElement("div");
    wrap.appendChild(corner);

    const colStrip = document.createElement("div");
    colStrip.className = "clue-col-strip";
    colStrip.style.gridTemplateColumns = `repeat(${cols}, ${cellSize}px)`;
    for (const cc of renderState.col_clues) {
      const chip = document.createElement("div");
      chip.className = "clue-chip";
      chip.style.flexDirection = "column";
      chip.innerHTML = (cc.length ? cc : [0]).map((n) => `<span>${n}</span>`).join("");
      colStrip.appendChild(chip);
    }
    wrap.appendChild(colStrip);

    const rowStrip = document.createElement("div");
    rowStrip.className = "clue-row-strip";
    rowStrip.style.gridTemplateRows = `repeat(${rows}, ${cellSize}px)`;
    for (const rc of renderState.row_clues) {
      const chip = document.createElement("div");
      chip.className = "clue-chip";
      chip.textContent = (rc.length ? rc : [0]).join(" ");
      rowStrip.appendChild(chip);
    }
    wrap.appendChild(rowStrip);
    wrap.appendChild(boardEl);
    stage.appendChild(wrap);
  } else {
    stage.appendChild(boardEl);
  }
}
