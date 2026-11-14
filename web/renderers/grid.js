const ZONE_COLORS = [
  "rgba(0, 245, 212, 0.22)",
  "rgba(255, 0, 127, 0.22)",
  "rgba(255, 230, 0, 0.22)",
  "rgba(185, 167, 227, 0.28)",
  "rgba(250, 130, 49, 0.24)",
  "rgba(1, 202, 107, 0.22)",
  "rgba(105, 230, 208, 0.22)",
  "rgba(231, 108, 143, 0.25)",
  "rgba(56, 103, 214, 0.26)",
];

const BLOCK_TOKEN_BRUSHES = [
  { token: "o", label: "Erase", kind: "erase" },
  { token: "x", label: "Wall (#)", kind: "terrain" },
  { token: "T", label: "Goal (★)", kind: "terrain" },
  { token: "t", label: "t", kind: "block" },
  { token: "t'", label: "t'", kind: "block" },
  { token: "g", label: "g", kind: "block" },
  { token: "r", label: "r", kind: "block" },
  { token: "b", label: "b", kind: "block" },
  { token: "A", label: "A", kind: "terrain" },
  { token: "B", label: "B", kind: "terrain" },
];

let activeBrush = 1;
let activeTokenBrush = "x";
let editSubMode = "value"; // "value" | "zone" | "clue"
let activeZoneBrush = 0;
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

function parseTokenMatrix(str, rows, cols) {
  const lines = String(str || "")
    .trim()
    .split(/\r?\n/)
    .filter((l) => l.trim().length > 0)
    .map((l) => l.trim().split(/\s+/));
  const mat = [];
  for (let r = 0; r < rows; r++) {
    const row = [];
    for (let c = 0; c < cols; c++) {
      row.push(lines[r]?.[c] ?? "o");
    }
    mat.push(row);
  }
  return mat;
}

function serializeTokenMatrix(mat) {
  return mat.map((row) => row.join(" ")).join("\n");
}

function rebuildTokenBoard(tMat, bMat) {
  const rows = tMat.length;
  const cols = tMat[0]?.length || 0;
  const board = [];
  for (let r = 0; r < rows; r++) {
    const row = [];
    for (let c = 0; c < cols; c++) {
      const t = tMat[r][c] || "o";
      const b = bMat[r][c] || "o";
      if (b !== "o") {
        row.push(b.toUpperCase());
      } else if (t === "x") {
        row.push("#");
      } else if (t === "T") {
        row.push("★");
      } else if (t !== "o") {
        row.push(t);
      } else {
        row.push("");
      }
    }
    board.push(row);
  }
  return board;
}

function resizeMatrix(mat, rows, cols, fillVal) {
  const out = [];
  for (let r = 0; r < rows; r++) {
    const row = [];
    for (let c = 0; c < cols; c++) {
      const v = mat?.[r]?.[c];
      row.push(v === undefined ? fillVal : v);
    }
    out.push(row);
  }
  return out;
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

  if (editSubMode === "zone" && (!gm.zone_editable || !renderState.zones)) {
    editSubMode = "value";
  }
  if (editSubMode === "clue" && !renderState.clues) {
    editSubMode = "value";
  }

  // Optional resize / layout bar
  if (canEdit && (gm.resizable || Array.isArray(gm.size_layouts))) {
    const dimBar = document.createElement("div");
    dimBar.className = "grid-toolbar";

    if (Array.isArray(gm.size_layouts)) {
      const lbl = document.createElement("label");
      lbl.style.display = "inline-flex";
      lbl.style.alignItems = "center";
      lbl.style.gap = "6px";
      lbl.style.fontSize = "12px";
      lbl.style.color = "var(--text-muted)";
      lbl.textContent = "Grid Layout";

      const sel = document.createElement("select");
      const curBoxW = renderState.box_w || gm.box_w || 0;
      const curBoxH = renderState.box_h || gm.box_h || 0;
      gm.size_layouts.forEach((lay, idx) => {
        const opt = document.createElement("option");
        opt.value = String(idx);
        opt.textContent = lay.label;
        if (lay.dim === rows && lay.box_w === curBoxW && lay.box_h === curBoxH) {
          opt.selected = true;
        }
        sel.appendChild(opt);
      });
      sel.addEventListener("change", () => {
        const lay = gm.size_layouts[Number(sel.value)];
        if (!lay) return;
        const next = JSON.parse(JSON.stringify(renderState));
        const d = lay.dim;
        next.grid_dim = d;
        next.box_w = lay.box_w;
        next.box_h = lay.box_h;
        next.board = Array.from({ length: d }, (_, r) =>
          Array.from({ length: d }, (_, c) => {
            const v = board[r]?.[c] ?? 0;
            return v > d ? 0 : v;
          }),
        );
        onEdit(next);
      });
      lbl.appendChild(sel);
      dimBar.appendChild(lbl);
    }

    if (gm.resizable) {
      const isSquare = gm.resizable === "square";
      const minD = gm.min_dim ?? 2;
      const maxD = gm.max_dim ?? 9;
      const step = gm.dim_step ?? 1;
      const fillVal = gm.empty_val ?? 0;

      const snapDim = (val) => {
        const clamped = Math.max(minD, Math.min(maxD, val));
        return minD + Math.round((clamped - minD) / step) * step;
      };

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
        inp.maxLength = String(maxD).length + 1;
        inp.value = String(curVal);
        inp.style.width = "36px";
        inp.style.textAlign = "center";

        const pad = document.createElement("div");
        pad.style.position = "absolute";
        pad.style.top = "100%";
        pad.style.left = "0";
        pad.style.marginTop = "4px";
        pad.style.display = "none";
        pad.style.gridTemplateColumns = "repeat(4, 30px)";
        pad.style.gap = "3px";
        pad.style.padding = "5px";
        pad.style.background = "var(--bg-panel)";
        pad.style.border = "1px solid var(--border)";
        pad.style.borderRadius = "4px";
        pad.style.zIndex = "30";
        pad.style.boxShadow = "0 4px 12px rgba(0, 0, 0, 0.35)";

        for (let d = minD; d <= Math.min(12, maxD); d += step) {
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
        const rawR = parseInt(rowsCtrl.inp.value, 10);
        const rawC = isSquare ? rawR : parseInt(colsCtrl.inp.value, 10);
        if (!Number.isInteger(rawR) || !Number.isInteger(rawC)) return;
        const cr = snapDim(rawR);
        const cc = isSquare ? cr : snapDim(rawC);
        if (cr === rows && cc === cols) {
          rowsCtrl.inp.value = String(cr);
          if (colsCtrl) colsCtrl.inp.value = String(cc);
          return;
        }
        const next = JSON.parse(JSON.stringify(renderState));
        if (mode === "permutation") {
          permSelected = null;
          permCursor = [0, 0];
          permBuffer = "";
          next.board = makePermutationBoard(cr, cc, fillVal);
        } else if (mode === "token") {
          const tMat = parseTokenMatrix(next.terrain, rows, cols);
          const bMat = parseTokenMatrix(next.blocks, rows, cols);
          const nextT = resizeMatrix(tMat, cr, cc, "o");
          const nextB = resizeMatrix(bMat, cr, cc, "o");
          next.terrain = serializeTokenMatrix(nextT);
          next.blocks = serializeTokenMatrix(nextB);
          next.board = rebuildTokenBoard(nextT, nextB);
        } else {
          next.board = resizeMatrix(board, cr, cc, fillVal);
        }
        if ("rows" in next) next.rows = cr;
        if ("cols" in next) next.cols = cc;
        if (Array.isArray(next.zones)) {
          next.zones = Array.from({ length: cr }, (_, r) => Array(cc).fill(r));
          if (activeZoneBrush >= cr) activeZoneBrush = 0;
        }
        if (Array.isArray(next.clues)) {
          next.clues = resizeMatrix(next.clues, cr, cc, null);
        }
        if (Array.isArray(next.row_clues) && Array.isArray(next.col_clues)) {
          next.row_clues = Array.from({ length: cr }, (_, r) => next.row_clues[r] || []);
          next.col_clues = Array.from({ length: cc }, (_, c) => next.col_clues[c] || []);
          next.board = Array.from({ length: cr }, () => Array(cc).fill(0));
        }
        if (Array.isArray(next.h_walls) && Array.isArray(next.v_walls)) {
          next.h_walls = resizeMatrix(next.h_walls, cr + 1, cc, 0);
          next.v_walls = resizeMatrix(next.v_walls, cr, cc + 1, 0);
        }
        onEdit(next);
      };

      if (isSquare) {
        rowsCtrl = makeDimInput("Size (N×N)", rows, applyDims);
        rowsCtrl.inp.addEventListener("change", applyDims);
        rowsCtrl.inp.addEventListener("keydown", (e) => {
          if (e.key === "Enter") { applyDims(); rowsCtrl.inp.blur(); }
        });
        dimBar.appendChild(rowsCtrl.wrap);
      } else {
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
      }
      stage.appendChild(dimBar);
    } else if (Array.isArray(gm.size_layouts)) {
      stage.appendChild(dimBar);
    }
  }

  // Zone Editing Toolbar (Chess Attack)
  if (canEdit && gm.zone_editable && Array.isArray(renderState.zones)) {
    const zBar = document.createElement("div");
    zBar.className = "grid-toolbar";

    const btnPieces = document.createElement("button");
    btnPieces.className = "btn" + (editSubMode === "value" ? " btn-solve" : "");
    btnPieces.textContent = "Edit Pieces";
    btnPieces.addEventListener("click", () => {
      editSubMode = "value";
      renderGrid(stage, solver, renderState, highlights, editable, onEdit);
    });

    const btnZones = document.createElement("button");
    btnZones.className = "btn" + (editSubMode === "zone" ? " btn-solve" : "");
    btnZones.textContent = "Paint Zones";
    btnZones.addEventListener("click", () => {
      editSubMode = "zone";
      renderGrid(stage, solver, renderState, highlights, editable, onEdit);
    });

    zBar.appendChild(btnPieces);
    zBar.appendChild(btnZones);

    if (editSubMode === "zone") {
      if (activeZoneBrush >= rows) activeZoneBrush = 0;
      for (let z = 0; z < rows; z++) {
        const sw = document.createElement("button");
        sw.className = "palette-swatch" + (activeZoneBrush === z ? " selected" : "");
        sw.style.background = ZONE_COLORS[z % ZONE_COLORS.length];
        sw.style.color = "var(--text-main)";
        sw.style.fontSize = "11px";
        sw.style.fontWeight = "700";
        sw.textContent = String(z + 1);
        sw.title = `Zone ${z + 1}`;
        sw.addEventListener("click", () => {
          activeZoneBrush = z;
          renderGrid(stage, solver, renderState, highlights, editable, onEdit);
        });
        zBar.appendChild(sw);
      }
    }
    stage.appendChild(zBar);
  }

  // Clue Editing Toggle (Urjo)
  if (canEdit && Array.isArray(renderState.clues)) {
    const cBar = document.createElement("div");
    cBar.className = "grid-toolbar";

    const btnVal = document.createElement("button");
    btnVal.className = "btn" + (editSubMode === "value" ? " btn-solve" : "");
    btnVal.textContent = "Edit Colors";
    btnVal.addEventListener("click", () => {
      editSubMode = "value";
      renderGrid(stage, solver, renderState, highlights, editable, onEdit);
    });

    const btnClue = document.createElement("button");
    btnClue.className = "btn" + (editSubMode === "clue" ? " btn-solve" : "");
    btnClue.textContent = "Edit Clues (0-8)";
    btnClue.addEventListener("click", () => {
      editSubMode = "clue";
      renderGrid(stage, solver, renderState, highlights, editable, onEdit);
    });

    cBar.appendChild(btnVal);
    cBar.appendChild(btnClue);
    stage.appendChild(cBar);
  }

  // Token Brush Bar (Block Escape)
  if (canEdit && mode === "token") {
    const tBar = document.createElement("div");
    tBar.className = "grid-toolbar";
    const lbl = document.createElement("span");
    lbl.style.fontSize = "12px";
    lbl.style.color = "var(--text-muted)";
    lbl.textContent = "Brush:";
    tBar.appendChild(lbl);

    for (const item of BLOCK_TOKEN_BRUSHES) {
      const btn = document.createElement("button");
      btn.className = "btn" + (activeTokenBrush === item.token ? " btn-solve" : "");
      btn.style.padding = "3px 7px";
      btn.style.fontSize = "11px";
      btn.textContent = item.label;
      btn.addEventListener("click", () => {
        activeTokenBrush = item.token;
        renderGrid(stage, solver, renderState, highlights, editable, onEdit);
      });
      tBar.appendChild(btn);
    }
    stage.appendChild(tBar);
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

    if (typeof renderState.num_colors === "number") {
      const colWrap = document.createElement("label");
      colWrap.style.display = "inline-flex";
      colWrap.style.alignItems = "center";
      colWrap.style.gap = "5px";
      colWrap.style.marginLeft = "8px";
      colWrap.style.fontSize = "12px";
      colWrap.style.color = "var(--text-muted)";
      colWrap.textContent = "Colors";
      const colSel = document.createElement("select");
      for (let k = 3; k <= 8; k++) {
        const o = document.createElement("option");
        o.value = String(k);
        o.textContent = String(k);
        if (k === renderState.num_colors) o.selected = true;
        colSel.appendChild(o);
      }
      colSel.addEventListener("change", () => {
        const nk = Number(colSel.value);
        const next = JSON.parse(JSON.stringify(renderState));
        next.num_colors = nk;
        next.board = board.map((row) => row.map((v) => v % nk));
        onEdit(next);
      });
      colWrap.appendChild(colSel);
      bar.appendChild(colWrap);
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
        if (editSubMode === "zone" && gm.zone_editable && Array.isArray(renderState.zones)) {
          cell.addEventListener("click", () => {
            const next = JSON.parse(JSON.stringify(renderState));
            next.zones[r][c] = activeZoneBrush;
            onEdit(next);
          });
        } else if (editSubMode === "clue" && Array.isArray(renderState.clues)) {
          cell.tabIndex = 0;
          cell.addEventListener("click", () => {
            const next = JSON.parse(JSON.stringify(renderState));
            const cur = next.clues[r][c];
            next.clues[r][c] = cur === null || cur === undefined ? 0 : cur >= 8 ? null : cur + 1;
            onEdit(next);
          });
          cell.addEventListener("keydown", (e) => {
            if (/^[0-8]$/.test(e.key)) {
              const next = JSON.parse(JSON.stringify(renderState));
              next.clues[r][c] = Number(e.key);
              onEdit(next);
            } else if (e.key === "Backspace" || e.key === "Delete") {
              const next = JSON.parse(JSON.stringify(renderState));
              next.clues[r][c] = null;
              onEdit(next);
            }
          });
        } else if (mode === "token") {
          cell.addEventListener("click", () => {
            const next = JSON.parse(JSON.stringify(renderState));
            const tMat = parseTokenMatrix(next.terrain, rows, cols);
            const bMat = parseTokenMatrix(next.blocks, rows, cols);
            const brushDef = BLOCK_TOKEN_BRUSHES.find((b) => b.token === activeTokenBrush) || BLOCK_TOKEN_BRUSHES[0];
            if (brushDef.kind === "erase") {
              tMat[r][c] = "o";
              bMat[r][c] = "o";
            } else if (brushDef.kind === "terrain") {
              tMat[r][c] = brushDef.token;
              if (brushDef.token === "x") bMat[r][c] = "o";
            } else {
              bMat[r][c] = brushDef.token;
              if (tMat[r][c] === "x") tMat[r][c] = "o";
            }
            next.terrain = serializeTokenMatrix(tMat);
            next.blocks = serializeTokenMatrix(bMat);
            next.board = rebuildTokenBoard(tMat, bMat);
            onEdit(next);
          });
        } else if (mode === "permutation") {
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

  // Optional SVG overlay for Maze Edge Walls + Path / Quarter-Arc curves
  const hasEdgeWalls = Array.isArray(renderState.h_walls) && Array.isArray(renderState.v_walls);
  const hasSvgPath = Array.isArray(highlights.path_svg) && highlights.path_svg.length > 0;
  const hasPath = Array.isArray(highlights.path) && highlights.path.length > 1;

  if (hasEdgeWalls || hasSvgPath || hasPath) {
    const totalW = cols * cellSize + (cols - 1) * 3 + 20;
    const totalH = rows * cellSize + (rows - 1) * 3 + 20;
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("width", String(totalW));
    svg.setAttribute("height", String(totalH));
    svg.style.position = "absolute";
    svg.style.inset = "0";
    svg.style.pointerEvents = hasEdgeWalls && canEdit ? "auto" : "none";

    const gx = (u) => 10 + u * (cellSize + 3) - 1.5;
    const gy = (u) => 10 + u * (cellSize + 3) - 1.5;

    // 1. Edge Walls layer (Maze Navigator)
    if (hasEdgeWalls) {
      const hw = renderState.h_walls;
      const vw = renderState.v_walls;

      for (let r = 1; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          const isOn = hw[r]?.[c] === 1;
          const x1 = gx(c) + 2;
          const x2 = gx(c + 1) - 2;
          const y = gy(r);
          const line = document.createElementNS(ns, "line");
          line.setAttribute("x1", String(x1));
          line.setAttribute("y1", String(y));
          line.setAttribute("x2", String(x2));
          line.setAttribute("y2", String(y));
          line.setAttribute("stroke", isOn ? "var(--accent-hot)" : "transparent");
          line.setAttribute("stroke-width", "5");
          line.setAttribute("stroke-linecap", "round");
          line.style.pointerEvents = "none";
          svg.appendChild(line);

          if (canEdit) {
            const hit = document.createElementNS(ns, "line");
            hit.setAttribute("x1", String(x1));
            hit.setAttribute("y1", String(y));
            hit.setAttribute("x2", String(x2));
            hit.setAttribute("y2", String(y));
            hit.setAttribute("stroke", "transparent");
            hit.setAttribute("stroke-width", "11");
            hit.style.cursor = "pointer";
            hit.addEventListener("mouseenter", () => { if (!isOn) line.setAttribute("stroke", "rgba(255,0,127,0.35)"); });
            hit.addEventListener("mouseleave", () => { if (!isOn) line.setAttribute("stroke", "transparent"); });
            hit.addEventListener("click", (e) => {
              e.stopPropagation();
              const next = JSON.parse(JSON.stringify(renderState));
              next.h_walls[r][c] = isOn ? 0 : 1;
              onEdit(next);
            });
            svg.appendChild(hit);
          }
        }
      }

      for (let r = 0; r < rows; r++) {
        for (let c = 1; c < cols; c++) {
          const isOn = vw[r]?.[c] === 1;
          const x = gx(c);
          const y1 = gy(r) + 2;
          const y2 = gy(r + 1) - 2;
          const line = document.createElementNS(ns, "line");
          line.setAttribute("x1", String(x));
          line.setAttribute("y1", String(y1));
          line.setAttribute("x2", String(x));
          line.setAttribute("y2", String(y2));
          line.setAttribute("stroke", isOn ? "var(--accent-hot)" : "transparent");
          line.setAttribute("stroke-width", "5");
          line.setAttribute("stroke-linecap", "round");
          line.style.pointerEvents = "none";
          svg.appendChild(line);

          if (canEdit) {
            const hit = document.createElementNS(ns, "line");
            hit.setAttribute("x1", String(x));
            hit.setAttribute("y1", String(y1));
            hit.setAttribute("x2", String(x));
            hit.setAttribute("y2", String(y2));
            hit.setAttribute("stroke", "transparent");
            hit.setAttribute("stroke-width", "11");
            hit.style.cursor = "pointer";
            hit.addEventListener("mouseenter", () => { if (!isOn) line.setAttribute("stroke", "rgba(255,0,127,0.35)"); });
            hit.addEventListener("mouseleave", () => { if (!isOn) line.setAttribute("stroke", "transparent"); });
            hit.addEventListener("click", (e) => {
              e.stopPropagation();
              const next = JSON.parse(JSON.stringify(renderState));
              next.v_walls[r][c] = isOn ? 0 : 1;
              onEdit(next);
            });
            svg.appendChild(hit);
          }
        }
      }
    }

    // 2. Path layer (supports curved Quarter-Arc SVG A commands or straight polyline)
    if (hasSvgPath) {
      const dParts = [];
      for (const op of highlights.path_svg) {
        if (op.op === "M") {
          dParts.push(`M ${gx(op.x).toFixed(2)} ${gy(op.y).toFixed(2)}`);
        } else if (op.op === "L") {
          dParts.push(`L ${gx(op.x).toFixed(2)} ${gy(op.y).toFixed(2)}`);
        } else if (op.op === "A") {
          const rad = (op.rx * (cellSize + 3)).toFixed(2);
          dParts.push(`A ${rad} ${rad} 0 0 ${op.sweep} ${gx(op.x).toFixed(2)} ${gy(op.y).toFixed(2)}`);
        }
      }
      const pathEl = document.createElementNS(ns, "path");
      pathEl.setAttribute("d", dParts.join(" "));
      pathEl.setAttribute("fill", "none");
      pathEl.setAttribute("stroke", "var(--accent-primary)");
      pathEl.setAttribute("stroke-width", "5");
      pathEl.setAttribute("stroke-linecap", "round");
      pathEl.setAttribute("stroke-linejoin", "round");
      pathEl.style.pointerEvents = "none";
      svg.appendChild(pathEl);
    } else if (hasPath) {
      const pts = highlights.path
        .map(([pr, pc]) => `${gx(pc + 0.5)},${gy(pr + 0.5)}`)
        .join(" ");
      const poly = document.createElementNS(ns, "polyline");
      poly.setAttribute("points", pts);
      poly.setAttribute("fill", "none");
      poly.setAttribute("stroke", "var(--accent-primary)");
      poly.setAttribute("stroke-width", "5");
      poly.setAttribute("stroke-linecap", "round");
      poly.setAttribute("stroke-linejoin", "round");
      poly.style.pointerEvents = "none";
      svg.appendChild(poly);
    }

    boardEl.appendChild(svg);
  }

  // Nonogram outer clues wrapper (with clickable clue editing in Edit mode)
  if (renderState.row_clues && renderState.col_clues) {
    const wrap = document.createElement("div");
    wrap.className = "board-with-clues";
    wrap.style.gridTemplateColumns = "auto auto";

    const corner = document.createElement("div");
    wrap.appendChild(corner);

    const makeEditableClueChip = (clueList, isCol, idx) => {
      const chip = document.createElement("div");
      chip.className = "clue-chip";
      if (isCol) {
        chip.style.flexDirection = "column";
        chip.innerHTML = (clueList.length ? clueList : [0]).map((n) => `<span>${n}</span>`).join("");
      } else {
        chip.textContent = (clueList.length ? clueList : [0]).join(" ");
      }
      if (canEdit) {
        chip.style.cursor = "pointer";
        chip.title = "Click to edit clue numbers (space-separated)";
        chip.addEventListener("click", () => {
          if (chip.querySelector("input")) return;
          const inp = document.createElement("input");
          inp.type = "text";
          inp.value = clueList.join(" ");
          inp.style.width = isCol ? "44px" : "68px";
          inp.style.textAlign = "center";
          const commit = () => {
            const parsed = inp.value
              .trim()
              .split(/[\s,]+/)
              .map((s) => parseInt(s, 10))
              .filter((n) => Number.isInteger(n) && n > 0);
            const next = JSON.parse(JSON.stringify(renderState));
            if (isCol) next.col_clues[idx] = parsed;
            else next.row_clues[idx] = parsed;
            onEdit(next);
          };
          inp.addEventListener("keydown", (e) => {
            if (e.key === "Enter") commit();
            else if (e.key === "Escape") renderGrid(stage, solver, renderState, highlights, editable, onEdit);
          });
          inp.addEventListener("blur", commit);
          chip.innerHTML = "";
          chip.appendChild(inp);
          inp.focus();
          inp.select();
        });
      }
      return chip;
    };

    const colStrip = document.createElement("div");
    colStrip.className = "clue-col-strip";
    colStrip.style.gridTemplateColumns = `repeat(${cols}, ${cellSize}px)`;
    renderState.col_clues.forEach((cc, cIdx) => {
      colStrip.appendChild(makeEditableClueChip(cc, true, cIdx));
    });
    wrap.appendChild(colStrip);

    const rowStrip = document.createElement("div");
    rowStrip.className = "clue-row-strip";
    rowStrip.style.gridTemplateRows = `repeat(${rows}, ${cellSize}px)`;
    renderState.row_clues.forEach((rc, rIdx) => {
      rowStrip.appendChild(makeEditableClueChip(rc, false, rIdx));
    });
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
