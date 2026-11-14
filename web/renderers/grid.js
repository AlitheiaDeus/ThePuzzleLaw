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
let permInputMode = "swap"; // "swap" | "type"
let permSelected = null;
let permCursor = [0, 0];
let permBuffer = "";
let permFocusAfterRender = false;

function makePermutationBoard(rows, cols, emptyVal = 0) {
  const board = [];
  let n = 1;
  for (let r = 0; r < rows; r++) {
    const row = [];
    for (let c = 0; c < cols; c++) {
      row.push(r === rows - 1 && c === cols - 1 ? emptyVal : n++);
    }
    board.push(row);
  }
  return board;
}

function swapBoardCells(board, r1, c1, r2, c2) {
  const next = board.map((row) => row.slice());
  const tmp = next[r1][c1];
  next[r1][c1] = next[r2][c2];
  next[r2][c2] = tmp;
  return next;
}

function placePermBySwap(board, tr, tc, val) {
  for (let r = 0; r < board.length; r++) {
    for (let c = 0; c < board[0].length; c++) {
      if (board[r][c] === val) {
        return swapBoardCells(board, tr, tc, r, c);
      }
    }
  }
  const next = board.map((row) => row.slice());
  next[tr][tc] = val;
  return next;
}

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

  // Optional Rows x Columns resize toolbar for grid_meta.resizable
  if (gm.resizable && canEdit) {
    const dimBar = document.createElement("div");
    dimBar.className = "grid-toolbar";
    const minD = gm.min_dim ?? 2;
    const maxD = gm.max_dim ?? 9;
    const fillVal = gm.empty_val ?? 0;

    const makeDimInput = (labelText, curVal, onPick) => {
      const wrap = document.createElement("label");
      wrap.style.position = "relative";
      wrap.style.display = "inline-flex";
      wrap.style.alignItems = "center";
      wrap.style.gap = "5px";
      wrap.style.fontSize = "12px";
      wrap.style.color = "var(--text-muted)";
      wrap.textContent = labelText;

      const inp = document.createElement("input");
      inp.type = "text";
      inp.inputMode = "numeric";
      inp.maxLength = String(maxD).length;
      inp.value = String(curVal);
      inp.style.width = "32px";
      inp.style.textAlign = "center";

      const pad = document.createElement("div");
      pad.style.position = "absolute";
      pad.style.top = "100%";
      pad.style.left = "0";
      pad.style.marginTop = "4px";
      pad.style.display = "none";
      pad.style.gridTemplateColumns = "repeat(4, 28px)";
      pad.style.gap = "3px";
      pad.style.padding = "5px";
      pad.style.background = "var(--bg-panel)";
      pad.style.border = "1px solid var(--border)";
      pad.style.borderRadius = "4px";
      pad.style.zIndex = "30";
      pad.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.35)";

      for (let d = minD; d <= Math.min(9, maxD); d++) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "btn" + (d === curVal ? " btn-solve" : "");
        btn.style.padding = "3px 0";
        btn.style.fontSize = "12px";
        btn.textContent = String(d);
        btn.addEventListener("mousedown", (e) => {
          e.preventDefault();
          inp.value = String(d);
          pad.style.display = "none";
          onPick();
        });
        pad.appendChild(btn);
      }

      inp.addEventListener("focus", () => { pad.style.display = "grid"; });
      inp.addEventListener("click", () => { inp.select(); pad.style.display = "grid"; });
      inp.addEventListener("blur", () => { pad.style.display = "none"; });

      wrap.appendChild(inp);
      wrap.appendChild(pad);
      return { wrap, inp };
    };

    let rowsCtrl;
    let colsCtrl;
    const applyDims = () => {
      const r = parseInt(rowsCtrl.inp.value, 10);
      const c = parseInt(colsCtrl.inp.value, 10);
      if (!Number.isInteger(r) || !Number.isInteger(c)) return;
      const cr = Math.max(minD, Math.min(maxD, r));
      const cc = Math.max(minD, Math.min(maxD, c));
      if (cr === rows && cc === cols) {
        rowsCtrl.inp.value = String(cr);
        colsCtrl.inp.value = String(cc);
        return;
      }
      const next = JSON.parse(JSON.stringify(renderState));
      if (mode === "permutation") {
        permSelected = null;
        permCursor = [0, 0];
        permBuffer = "";
        next.board = makePermutationBoard(cr, cc, fillVal);
      } else {
        const newBoard = [];
        for (let rr = 0; rr < cr; rr++) {
          const row = [];
          for (let cc2 = 0; cc2 < cc; cc2++) {
            row.push(board[rr]?.[cc2] ?? fillVal);
          }
          newBoard.push(row);
        }
        next.board = newBoard;
      }
      if ("rows" in next) next.rows = cr;
      if ("cols" in next) next.cols = cc;
      onEdit(next);
    };

    rowsCtrl = makeDimInput("Rows", rows, applyDims);
    colsCtrl = makeDimInput("Columns", cols, applyDims);
    for (const inp of [rowsCtrl.inp, colsCtrl.inp]) {
      inp.addEventListener("change", applyDims);
      inp.addEventListener("keydown", (e) => {
        if (e.key === "Enter") { applyDims(); inp.blur(); }
      });
    }
    dimBar.appendChild(rowsCtrl.wrap);
    dimBar.appendChild(colsCtrl.wrap);
    stage.appendChild(dimBar);
  }

  // Optional permutation toolbar (Swap Mode, Type Entry, Reset Order)
  if (mode === "permutation" && canEdit) {
    const maxPerm = rows * cols - 1;
    if (permCursor[0] >= rows || permCursor[1] >= cols) {
      permCursor = [0, 0];
      permBuffer = "";
    }
    if (permSelected && (permSelected[0] >= rows || permSelected[1] >= cols)) {
      permSelected = null;
    }

    const pBar = document.createElement("div");
    pBar.className = "grid-toolbar";

    const btnSwap = document.createElement("button");
    btnSwap.className = "btn" + (permInputMode === "swap" ? " btn-solve" : "");
    btnSwap.textContent = "Swap Mode";
    btnSwap.addEventListener("click", () => {
      permInputMode = "swap";
      permBuffer = "";
      renderGrid(stage, solver, renderState, highlights, editable, onEdit);
    });

    const btnType = document.createElement("button");
    btnType.className = "btn" + (permInputMode === "type" ? " btn-solve" : "");
    btnType.textContent = "Type Entry";
    btnType.addEventListener("click", () => {
      permInputMode = "type";
      permSelected = null;
      permCursor = [0, 0];
      permBuffer = "";
      permFocusAfterRender = true;
      renderGrid(stage, solver, renderState, highlights, editable, onEdit);
    });

    const btnResetOrder = document.createElement("button");
    btnResetOrder.className = "btn";
    btnResetOrder.textContent = "Reset Order";
    btnResetOrder.addEventListener("click", () => {
      permSelected = null;
      permCursor = [0, 0];
      permBuffer = "";
      const next = JSON.parse(JSON.stringify(renderState));
      next.board = makePermutationBoard(rows, cols, gm.empty_val ?? 0);
      onEdit(next);
    });

    const hint = document.createElement("span");
    hint.style.fontSize = "12px";
    hint.style.color = "var(--text-muted)";
    hint.style.marginLeft = "6px";
    hint.textContent =
      permInputMode === "swap"
        ? "Click two tiles or drag to swap."
        : maxPerm < 10
          ? `Type 1-${maxPerm} (0/Space = blank)`
          : `Type 1-${maxPerm} + Enter/Space (Space = blank)${permBuffer ? ` | typing: ${permBuffer}_` : ""}`;

    pBar.appendChild(btnSwap);
    pBar.appendChild(btnType);
    pBar.appendChild(btnResetOrder);
    pBar.appendChild(hint);
    stage.appendChild(pBar);
  }

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

  const availW = Math.max(320, (stage.clientWidth || 640) - 80);
  const availH = Math.max(320, (stage.clientHeight || 540) - 90);
  const cellSize = Math.max(28, Math.min(96, Math.floor(Math.min(availW / cols, availH / rows)) - 4));
  const boardEl = document.createElement("div");
  boardEl.className = "board-frame";
  boardEl.style.gridTemplateColumns = `repeat(${cols}, ${cellSize}px)`;

  if (mode === "permutation" && canEdit && permInputMode === "type") {
    const maxPerm = rows * cols - 1;
    boardEl.tabIndex = 0;
    boardEl.style.outline = "none";

    const advancePermCursor = (delta) => {
      const idx = permCursor[0] * cols + permCursor[1] + delta;
      if (idx >= rows * cols) {
        permInputMode = "swap";
        permCursor = [0, 0];
        permBuffer = "";
        permFocusAfterRender = false;
        return false;
      }
      const clamped = Math.max(0, idx);
      permCursor = [Math.floor(clamped / cols), clamped % cols];
      return true;
    };

    const commitPermValue = (val) => {
      if (val < 0 || val > maxPerm) return;
      const [cr, cc] = permCursor;
      const next = JSON.parse(JSON.stringify(renderState));
      next.board = placePermBySwap(board, cr, cc, val);
      permBuffer = "";
      permFocusAfterRender = advancePermCursor(1);
      onEdit(next);
    };

    boardEl.addEventListener("keydown", (e) => {
      if (e.key >= "0" && e.key <= "9") {
        e.preventDefault();
        if (maxPerm < 10) {
          const num = Number(e.key);
          if (num <= maxPerm) commitPermValue(num);
          return;
        }
        const candidate = permBuffer === "0" ? e.key : permBuffer + e.key;
        const num = Number(candidate);
        if (num <= maxPerm) {
          permBuffer = candidate;
          permFocusAfterRender = true;
          renderGrid(stage, solver, renderState, highlights, editable, onEdit);
        }
      } else if (e.key === "Enter" || e.key === " " || e.key === "Tab") {
        e.preventDefault();
        if (permBuffer !== "") {
          commitPermValue(Number(permBuffer));
        } else if (e.key === " ") {
          commitPermValue(gm.empty_val ?? 0);
        } else {
          permFocusAfterRender = advancePermCursor(1);
          renderGrid(stage, solver, renderState, highlights, editable, onEdit);
        }
      } else if (e.key === "Backspace") {
        e.preventDefault();
        if (permBuffer.length > 0) permBuffer = permBuffer.slice(0, -1);
        else advancePermCursor(-1);
        permFocusAfterRender = true;
        renderGrid(stage, solver, renderState, highlights, editable, onEdit);
      } else if (e.key === "ArrowRight") {
        e.preventDefault(); permBuffer = ""; advancePermCursor(1); permFocusAfterRender = true;
        renderGrid(stage, solver, renderState, highlights, editable, onEdit);
      } else if (e.key === "ArrowLeft") {
        e.preventDefault(); permBuffer = ""; advancePermCursor(-1); permFocusAfterRender = true;
        renderGrid(stage, solver, renderState, highlights, editable, onEdit);
      } else if (e.key === "ArrowDown") {
        e.preventDefault(); permBuffer = ""; permCursor = [Math.min(rows - 1, permCursor[0] + 1), permCursor[1]]; permFocusAfterRender = true;
        renderGrid(stage, solver, renderState, highlights, editable, onEdit);
      } else if (e.key === "ArrowUp") {
        e.preventDefault(); permBuffer = ""; permCursor = [Math.max(0, permCursor[0] - 1), permCursor[1]]; permFocusAfterRender = true;
        renderGrid(stage, solver, renderState, highlights, editable, onEdit);
      }
    });
  }

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

      if (mode === "permutation" && val === (gm.empty_val ?? 0)) {
        cell.style.background = "transparent";
        cell.style.borderStyle = "dashed";
        cell.style.opacity = "0.55";
      }

      if (mode === "permutation" && canEdit && permInputMode === "swap" && permSelected && permSelected[0] === r && permSelected[1] === c) {
        cell.style.outline = "3px solid var(--accent-primary)";
        cell.style.outlineOffset = "-3px";
      }

      if (mode === "permutation" && canEdit && permInputMode === "type" && permCursor[0] === r && permCursor[1] === c) {
        cell.style.outline = "3px solid var(--accent-secondary)";
        cell.style.outlineOffset = "-3px";
        if (permBuffer) {
          cell.textContent = permBuffer + "_";
          cell.style.opacity = "1";
          cell.style.color = "var(--accent-secondary)";
        }
      }

      if (canEdit) {
        if (mode === "permutation") {
          if (permInputMode === "swap") {
            cell.draggable = true;
            cell.addEventListener("dragstart", (e) => {
              e.dataTransfer.setData("text/plain", `${r},${c}`);
              permSelected = [r, c];
            });
            cell.addEventListener("dragover", (e) => e.preventDefault());
            cell.addEventListener("drop", (e) => {
              e.preventDefault();
              const [sr, sc] = e.dataTransfer.getData("text/plain").split(",").map(Number);
              if (Number.isInteger(sr) && Number.isInteger(sc) && (sr !== r || sc !== c)) {
                permSelected = null;
                const next = JSON.parse(JSON.stringify(renderState));
                next.board = swapBoardCells(board, sr, sc, r, c);
                onEdit(next);
              }
            });
            cell.addEventListener("click", () => {
              if (!permSelected) {
                permSelected = [r, c];
                renderGrid(stage, solver, renderState, highlights, editable, onEdit);
              } else if (permSelected[0] === r && permSelected[1] === c) {
                permSelected = null;
                renderGrid(stage, solver, renderState, highlights, editable, onEdit);
              } else {
                const [sr, sc] = permSelected;
                permSelected = null;
                const next = JSON.parse(JSON.stringify(renderState));
                next.board = swapBoardCells(board, sr, sc, r, c);
                onEdit(next);
              }
            });
          } else {
            cell.addEventListener("click", () => {
              permCursor = [r, c];
              permBuffer = "";
              permFocusAfterRender = true;
              renderGrid(stage, solver, renderState, highlights, editable, onEdit);
            });
          }
        } else {
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
              const maxV = renderState.grid_dim ?? gm.max_val ?? (rows * cols - 1);
              next.board[r][c] = val >= maxV ? 0 : val + 1;
            }
            onEdit(next);
          });
          cell.addEventListener("keydown", (e) => {
            if (mode !== "number") return;
            if (/^[0-9]$/.test(e.key)) {
              const d = Number(e.key);
              const maxV = renderState.grid_dim ?? gm.max_val ?? (rows * cols - 1);
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

  if (mode === "permutation" && canEdit && permInputMode === "type" && permFocusAfterRender) {
    permFocusAfterRender = false;
    boardEl.focus();
  }
}
