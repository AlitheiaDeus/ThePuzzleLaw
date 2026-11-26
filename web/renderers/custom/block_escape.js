// Custom merged-block renderer & quick-setup editor for Block Escape

const BRUSHES = [
  { token: "o", label: "Erase", kind: "erase", color: "transparent" },
  { token: "x", label: "Wall (#)", kind: "terrain", color: "#3d434c" },
  { token: "T", label: "Goal (★)", kind: "terrain", color: "rgba(34, 197, 94, 0.35)" },
  { token: "t", label: "Target (Yellow)", kind: "block", color: "#facc15" },
  { token: "g", label: "Omni (Green)", kind: "block", color: "#22c55e" },
  { token: "r", label: "Horiz ↔ (Red)", kind: "block", color: "#ef4444" },
  { token: "b", label: "Vert ↕ (Blue)", kind: "block", color: "#3b82f6" },
  { token: "n", label: "Up ↑ (Purple)", kind: "block", color: "#a855f7" },
  { token: "s", label: "Down ↓ (Purple)", kind: "block", color: "#a855f7" },
  { token: "e", label: "Right → (Purple)", kind: "block", color: "#a855f7" },
  { token: "w", label: "Left ← (Purple)", kind: "block", color: "#a855f7" },
  { token: "__portalA__", label: "Portal A#", kind: "terrain", color: "#a855f7" },
  { token: "__portalB__", label: "Portal B#", kind: "terrain", color: "#ec4899" },
  { token: "__ice__", label: "Ice Toggle ❄️", kind: "tool", color: "#e0f2fe" },
  { token: "__chain_same__", label: "Chain Same 🔗", kind: "tool", color: "#38bdf8" },
  { token: "__chain_invert__", label: "Chain Opp ⇄", kind: "tool", color: "#fb923c" },
];

const PORTAL_COLORS = [
  ["rgba(168, 85, 247, 0.25)", "#a855f7", "#d8b4fe"],
  ["rgba(236, 72, 153, 0.25)", "#ec4899", "#f9a8d4"],
  ["rgba(99, 102, 241, 0.25)", "#6366f1", "#a5b4fc"],
  ["rgba(192, 132, 252, 0.25)", "#c084fc", "#e9d5ff"],
];

function isPortalToken(tok) {
  return /^([ABCD]|[AB]\d+)$/.test(String(tok || ""));
}

function portalStyle(tok) {
  const s = String(tok || "");
  const m = s.match(/^[AB](\d+)$/);
  let idx = 0;
  if (m) {
    idx = (parseInt(m[1], 10) - 1) % PORTAL_COLORS.length;
  } else {
    idx = Math.max(0, "ABCD".indexOf(s)) % PORTAL_COLORS.length;
  }
  return PORTAL_COLORS[idx];
}

const TARGET_DIRS = [
  { token: "t", label: "Omni ✥" },
  { token: "tr", label: "Horiz ↔" },
  { token: "tb", label: "Vert ↕" },
  { token: "tn", label: "Up ↑" },
  { token: "ts", label: "Down ↓" },
  { token: "te", label: "Right →" },
  { token: "tw", label: "Left ←" },
];

const GREEN_SHADES = [
  "#22c55e",
  "#16a34a",
  "#10b981",
  "#4ade80",
  "#059669",
  "#15803d",
  "#34d399",
  "#0d9488",
];

const DIR_GLYPH = {
  t: "★",
  g: "✥",
  r: "↔",
  b: "↕",
  n: "↑",
  s: "↓",
  e: "→",
  w: "←",
};

let activeBrush = "g";
let targetDirToken = "t";
let portalPairNum = 1;
let autoNewPiece = true;
let iceModifier = false;
let lastPieceToken = "g1";
let showTextDrawer = false;
let chainSourceToken = null;

// Drag-painting state (persists across re-renders triggered by onEdit)
let dragActive = false;
let dragErase = false;
let dragToken = null;
let dragVisited = new Set();

function parseTokenMatrix(str, rows, cols) {
  const lines = String(str || "")
    .trim()
    .split(/\r?\n/)
    .filter((l) => l.trim());
  const mat = [];
  for (let r = 0; r < rows; r++) {
    const tokens = lines[r] ? lines[r].trim().split(/\s+/) : [];
    const row = [];
    for (let c = 0; c < cols; c++) {
      row.push(tokens[c] || "o");
    }
    mat.push(row);
  }
  return mat;
}

function serializeTokenMatrix(mat) {
  return mat.map((row) => row.join(" ")).join("\n");
}

function rebuildBoard(tMat, bMat) {
  return tMat.map((tRow, r) =>
    tRow.map((tTok, c) => {
      const bTok = bMat[r][c];
      if (bTok && bTok !== "o") return bTok.toUpperCase();
      if (tTok === "x") return "#";
      if (tTok === "T") return "★";
      if (tTok && tTok !== "o") return tTok;
      return "";
    })
  );
}

function getDimensions(renderState) {
  const board = Array.isArray(renderState.board) ? renderState.board : [];
  if (board.length > 0 && Array.isArray(board[0])) {
    return [board.length, board[0].length];
  }
  const tLines = String(renderState.terrain || "").trim().split(/\r?\n/).filter((l) => l.trim());
  const rows = Math.max(3, tLines.length || 6);
  const cols = Math.max(3, tLines[0] ? tLines[0].trim().split(/\s+/).length : 6);
  return [rows, cols];
}

function nextFreeToken(bMat, baseChar, withIce) {
  const used = new Set();
  for (const row of bMat) {
    for (const cell of row) {
      if (cell && cell !== "o") {
        used.add(cell.replace("'", "").toLowerCase());
      }
    }
  }
  let idx = 1;
  while (used.has(`${baseChar}${idx}`)) {
    idx++;
  }
  return `${baseChar}${idx}${withIce ? "'" : ""}`;
}

function hashStr(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) {
    h = (h * 31 + s.charCodeAt(i)) | 0;
  }
  return Math.abs(h);
}

function pieceColor(baseChar, tokenStr, pieceId) {
  if (baseChar === "t") return "#facc15";
  if (baseChar === "g") {
    const idx = pieceId >= 0 ? pieceId : hashStr(tokenStr || "g");
    return GREEN_SHADES[idx % GREEN_SHADES.length];
  }
  if (baseChar === "r") return "#ef4444";
  if (baseChar === "b") return "#3b82f6";
  if ("nsew".includes(baseChar)) return "#a855f7";
  return "var(--accent-hot)";
}

function addIceDogEar(el, corner) {
  const ear = document.createElement("span");
  ear.style.position = "absolute";
  ear.style.width = "0";
  ear.style.height = "0";
  ear.style.pointerEvents = "none";
  const size = "10px";
  const color = "rgba(224, 242, 254, 0.94)";
  if (corner === "tr") {
    ear.style.top = "0";
    ear.style.right = "0";
    ear.style.borderTop = `${size} solid ${color}`;
    ear.style.borderLeft = `${size} solid transparent`;
  } else if (corner === "tl") {
    ear.style.top = "0";
    ear.style.left = "0";
    ear.style.borderTop = `${size} solid ${color}`;
    ear.style.borderRight = `${size} solid transparent`;
  } else if (corner === "br") {
    ear.style.bottom = "0";
    ear.style.right = "0";
    ear.style.borderBottom = `${size} solid ${color}`;
    ear.style.borderLeft = `${size} solid transparent`;
  } else if (corner === "bl") {
    ear.style.bottom = "0";
    ear.style.left = "0";
    ear.style.borderBottom = `${size} solid ${color}`;
    ear.style.borderRight = `${size} solid transparent`;
  }
  el.appendChild(ear);
}

function computeAnchorCells(rows, cols, getKey) {
  const seen = new Set();
  const anchors = new Set();
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const k = getKey(r, c);
      if (k !== null && !seen.has(k)) {
        seen.add(k);
        anchors.add(`${r},${c}`);
      }
    }
  }
  return anchors;
}

function getConnectedCells(bMat, startR, startC) {
  const rows = bMat.length;
  const cols = bMat[0].length;
  const target = bMat[startR][startC];
  if (!target || target === "o") return [];
  const visited = new Set([`${startR},${startC}`]);
  const q = [[startR, startC]];
  const out = [];
  while (q.length > 0) {
    const [r, c] = q.shift();
    out.push([r, c]);
    for (const [dr, dc] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
      const nr = r + dr;
      const nc = c + dc;
      const key = `${nr},${nc}`;
      if (nr >= 0 && nr < rows && nc >= 0 && nc < cols && !visited.has(key) && bMat[nr][nc] === target) {
        visited.add(key);
        q.push([nr, nc]);
      }
    }
  }
  return out;
}

export function render(stage, solver, renderState, highlights, editable, onEdit) {
  stage.innerHTML = "";

  const [rows, cols] = getDimensions(renderState);
  const tMat = parseTokenMatrix(renderState.terrain, rows, cols);
  const bMat = parseTokenMatrix(renderState.blocks, rows, cols);
  const board = Array.isArray(renderState.board) && renderState.board.length === rows
    ? renderState.board
    : rebuildBoard(tMat, bMat);
  const pieces = Array.isArray(renderState.pieces) && renderState.pieces.length === rows
    ? renderState.pieces
    : null;
  const chains = Array.isArray(renderState.chains) ? renderState.chains : [];

  const canEdit = editable && typeof onEdit === "function";

  const applyCell = (r, c, overrideToken = null) => {
    const next = JSON.parse(JSON.stringify(renderState));
    const nt = parseTokenMatrix(next.terrain, rows, cols);
    const nb = parseTokenMatrix(next.blocks, rows, cols);

    if (dragErase || overrideToken === "o") {
      // If both block and zone exist, erase block first; otherwise erase terrain
      if (nb[r][c] !== "o") {
        nb[r][c] = "o";
      } else {
        nt[r][c] = "o";
      }
    } else {
      const tok = overrideToken || activeBrush;
      if (isPortalToken(tok)) {
        nt[r][c] = tok;
      } else {
        const brushDef = BRUSHES.find((b) => b.token === tok || b.token === tok[0]) || BRUSHES[0];
        if (brushDef.kind === "erase") {
          nt[r][c] = "o";
          nb[r][c] = "o";
        } else if (brushDef.kind === "terrain") {
          nt[r][c] = tok;
          if (tok === "x") nb[r][c] = "o";
        } else {
          nb[r][c] = tok;
          if (nt[r][c] === "x") nt[r][c] = "o";
        }
      }
    }

    next.terrain = serializeTokenMatrix(nt);
    next.blocks = serializeTokenMatrix(nb);
    next.board = rebuildBoard(nt, nb);
    delete next.pieces;
    onEdit(next);
  };

  const toggleIceOnPiece = (r, c) => {
    const curTok = bMat[r]?.[c];
    if (!curTok || curTok === "o") return;
    const next = JSON.parse(JSON.stringify(renderState));
    const nt = parseTokenMatrix(next.terrain, rows, cols);
    const nb = parseTokenMatrix(next.blocks, rows, cols);
    const cells = getConnectedCells(nb, r, c);
    const isIced = curTok.includes("'");
    const newTok = isIced ? curTok.replace("'", "") : `${curTok}'`;
    for (const [cr, cc] of cells) {
      nb[cr][cc] = newTok;
    }
    next.blocks = serializeTokenMatrix(nb);
    next.board = rebuildBoard(nt, nb);
    delete next.pieces;
    onEdit(next);
  };

  const handleChainClick = (r, c, mode) => {
    const curTok = bMat[r]?.[c];
    if (!curTok || curTok === "o") {
      chainSourceToken = null;
      render(stage, solver, renderState, highlights, editable, onEdit);
      return;
    }
    const cleanTok = curTok.replace("'", "").toLowerCase();
    if (!chainSourceToken) {
      chainSourceToken = cleanTok;
      render(stage, solver, renderState, highlights, editable, onEdit);
      return;
    }
    if (chainSourceToken === cleanTok) {
      chainSourceToken = null;
      render(stage, solver, renderState, highlights, editable, onEdit);
      return;
    }

    const next = JSON.parse(JSON.stringify(renderState));
    const nextChains = Array.isArray(next.chains) ? next.chains.slice() : [];
    const pairKey = [chainSourceToken, cleanTok].sort().join("|");
    const existingIdx = nextChains.findIndex(([pair]) => {
      if (!Array.isArray(pair) || pair.length !== 2) return false;
      return [pair[0].toLowerCase(), pair[1].toLowerCase()].sort().join("|") === pairKey;
    });

    if (existingIdx >= 0) {
      if (nextChains[existingIdx][1] === mode) {
        nextChains.splice(existingIdx, 1); // Toggle off
      } else {
        nextChains[existingIdx] = [[chainSourceToken, cleanTok], mode]; // Switch mode
      }
    } else {
      nextChains.push([[chainSourceToken, cleanTok], mode]);
    }
    chainSourceToken = null;
    next.chains = nextChains;
    onEdit(next);
  };

  if (canEdit && !window.__blockEscapePointerBound) {
    window.__blockEscapePointerBound = true;
    window.addEventListener("pointerup", () => {
      dragActive = false;
      dragErase = false;
      dragToken = null;
      dragVisited.clear();
    });
  }

  // 1. Toolbar: Size + Quick Actions
  if (canEdit) {
    const topBar = document.createElement("div");
    topBar.className = "grid-toolbar";
    topBar.style.flexWrap = "wrap";

    const rInput = document.createElement("input");
    rInput.type = "number";
    rInput.min = 3;
    rInput.max = 15;
    rInput.value = rows;
    rInput.className = "dim-input";
    rInput.title = "Rows";

    const xLbl = document.createElement("span");
    xLbl.textContent = "×";
    xLbl.style.color = "var(--text-muted)";

    const cInput = document.createElement("input");
    cInput.type = "number";
    cInput.min = 3;
    cInput.max = 15;
    cInput.value = cols;
    cInput.className = "dim-input";
    cInput.title = "Columns";

    const btnResize = document.createElement("button");
    btnResize.className = "btn";
    btnResize.textContent = "Resize";
    btnResize.addEventListener("click", () => {
      const nr = Math.max(3, Math.min(15, parseInt(rInput.value, 10) || rows));
      const nc = Math.max(3, Math.min(15, parseInt(cInput.value, 10) || cols));
      const nt = parseTokenMatrix(renderState.terrain, nr, nc);
      const nb = parseTokenMatrix(renderState.blocks, nr, nc);
      const next = JSON.parse(JSON.stringify(renderState));
      next.terrain = serializeTokenMatrix(nt);
      next.blocks = serializeTokenMatrix(nb);
      next.board = rebuildBoard(nt, nb);
      delete next.pieces;
      onEdit(next);
    });

    const btnClear = document.createElement("button");
    btnClear.className = "btn";
    btnClear.textContent = "Clear";
    btnClear.addEventListener("click", () => {
      const nt = Array.from({ length: rows }, () => Array(cols).fill("o"));
      const nb = Array.from({ length: rows }, () => Array(cols).fill("o"));
      const next = JSON.parse(JSON.stringify(renderState));
      next.terrain = serializeTokenMatrix(nt);
      next.blocks = serializeTokenMatrix(nb);
      next.board = rebuildBoard(nt, nb);
      next.chains = [];
      chainSourceToken = null;
      delete next.pieces;
      onEdit(next);
    });

    const btnNewPiece = document.createElement("button");
    btnNewPiece.className = "btn" + (autoNewPiece ? " btn-solve" : "");
    btnNewPiece.textContent = autoNewPiece ? "Auto-New Piece: ON" : "Auto-New Piece: OFF";
    btnNewPiece.title = "When ON, each drag stroke creates a separate block ID. Hold Shift to extend the last piece.";
    btnNewPiece.addEventListener("click", () => {
      autoNewPiece = !autoNewPiece;
      render(stage, solver, renderState, highlights, editable, onEdit);
    });

    const btnIceMod = document.createElement("button");
    btnIceMod.className = "btn" + (iceModifier ? " btn-solve" : "");
    btnIceMod.textContent = iceModifier ? "Paint Iced: ON" : "Paint Iced: OFF";
    btnIceMod.addEventListener("click", () => {
      iceModifier = !iceModifier;
      render(stage, solver, renderState, highlights, editable, onEdit);
    });

    const btnText = document.createElement("button");
    btnText.className = "btn" + (showTextDrawer ? " btn-solve" : "");
    btnText.textContent = "Text Import";
    btnText.addEventListener("click", () => {
      showTextDrawer = !showTextDrawer;
      render(stage, solver, renderState, highlights, editable, onEdit);
    });

    topBar.append(rInput, xLbl, cInput, btnResize, btnClear, btnNewPiece, btnIceMod, btnText);
    stage.appendChild(topBar);

    // 2. Brush Bar
    const brushBar = document.createElement("div");
    brushBar.className = "grid-toolbar";
    brushBar.style.flexWrap = "wrap";

    for (const item of BRUSHES) {
      const btn = document.createElement("button");
      const isSelected = activeBrush === item.token;
      btn.className = "btn" + (isSelected ? " btn-solve" : "");
      btn.style.padding = "4px 8px";
      btn.style.fontSize = "11px";
      btn.style.display = "inline-flex";
      btn.style.alignItems = "center";
      btn.style.gap = "5px";

      if (item.color !== "transparent") {
        const dot = document.createElement("span");
        dot.style.width = "10px";
        dot.style.height = "10px";
        dot.style.borderRadius = "2px";
        dot.style.background =
          item.token === "__portalA__" || item.token === "__portalB__"
            ? portalStyle(`A${portalPairNum}`)[1]
            : item.color;
        dot.style.display = "inline-block";
        btn.appendChild(dot);
      }
      const btnText =
        item.token === "__portalA__"
          ? `Portal A${portalPairNum}`
          : item.token === "__portalB__"
          ? `Portal B${portalPairNum}`
          : item.label;
      btn.appendChild(document.createTextNode(btnText));
      btn.addEventListener("click", () => {
        activeBrush = item.token;
        chainSourceToken = null;
        render(stage, solver, renderState, highlights, editable, onEdit);
      });
      brushBar.appendChild(btn);
    }
    stage.appendChild(brushBar);

    if (activeBrush === "__portalA__" || activeBrush === "__portalB__") {
      const pBar = document.createElement("div");
      pBar.className = "grid-toolbar";
      const pLbl = document.createElement("span");
      pLbl.textContent = `Portal Pair #${portalPairNum} (A${portalPairNum} ↔ B${portalPairNum}):`;
      pLbl.style.fontSize = "11px";
      pLbl.style.color = "var(--text-muted)";
      const btnPrev = document.createElement("button");
      btnPrev.className = "btn";
      btnPrev.textContent = "− Pair";
      btnPrev.style.padding = "2px 7px";
      btnPrev.style.fontSize = "11px";
      btnPrev.addEventListener("click", () => {
        portalPairNum = Math.max(1, portalPairNum - 1);
        render(stage, solver, renderState, highlights, editable, onEdit);
      });
      const btnNext = document.createElement("button");
      btnNext.className = "btn";
      btnNext.textContent = "+ Pair";
      btnNext.style.padding = "2px 7px";
      btnNext.style.fontSize = "11px";
      btnNext.addEventListener("click", () => {
        portalPairNum = Math.min(20, portalPairNum + 1);
        render(stage, solver, renderState, highlights, editable, onEdit);
      });
      pBar.append(pLbl, btnPrev, btnNext);
      stage.appendChild(pBar);
    }

    if (activeBrush === "t") {
      const tdBar = document.createElement("div");
      tdBar.className = "grid-toolbar";
      tdBar.style.flexWrap = "wrap";
      const tdLbl = document.createElement("span");
      tdLbl.textContent = "Target Dir:";
      tdLbl.style.fontSize = "11px";
      tdLbl.style.color = "var(--text-muted)";
      tdBar.appendChild(tdLbl);
      for (const td of TARGET_DIRS) {
        const b = document.createElement("button");
        b.className = "btn" + (targetDirToken === td.token ? " btn-solve" : "");
        b.style.padding = "3px 7px";
        b.style.fontSize = "11px";
        b.textContent = td.label;
        b.addEventListener("click", () => {
          targetDirToken = td.token;
          render(stage, solver, renderState, highlights, editable, onEdit);
        });
        tdBar.appendChild(b);
      }
      stage.appendChild(tdBar);
    }

    const tip = document.createElement("div");
    tip.style.fontSize = "11px";
    tip.style.color = "var(--text-muted)";
    tip.style.marginBottom = "6px";
    if (activeBrush === "__ice__") {
      tip.textContent = "Ice Toggle mode: Click any block to toggle Ice (') on the entire piece.";
    } else if (activeBrush === "__chain_same__" || activeBrush === "__chain_invert__") {
      tip.textContent = chainSourceToken
        ? `Selected source: ${chainSourceToken.toUpperCase()} — Now click target piece to toggle chain.`
        : "Chain mode: Click source piece, then click target piece to toggle a chain link.";
    } else {
      tip.textContent = "Drag to paint merged blocks • Zones (★ / A / B) can be drawn under tiles • Shift+drag extends previous piece • Right-click erases";
    }
    stage.appendChild(tip);

    if (showTextDrawer) {
      const drawer = document.createElement("div");
      drawer.style.display = "grid";
      drawer.style.gridTemplateColumns = "1fr 1fr";
      drawer.style.gap = "8px";
      drawer.style.marginBottom = "10px";
      drawer.style.width = "100%";
      drawer.style.maxWidth = "680px";

      const mkArea = (labelText, val) => {
        const wrap = document.createElement("div");
        const lbl = document.createElement("div");
        lbl.textContent = labelText;
        lbl.style.fontSize = "11px";
        lbl.style.color = "var(--text-muted)";
        lbl.style.marginBottom = "3px";
        const ta = document.createElement("textarea");
        ta.value = val;
        ta.rows = Math.min(10, Math.max(4, rows));
        ta.style.width = "100%";
        ta.style.fontFamily = "monospace";
        ta.style.fontSize = "11px";
        ta.style.background = "var(--bg-surface)";
        ta.style.color = "var(--text-main)";
        ta.style.border = "1px solid var(--border)";
        ta.style.borderRadius = "4px";
        ta.style.padding = "6px";
        wrap.append(lbl, ta);
        return { wrap, ta };
      };

      const tBox = mkArea("Terrain (o=empty, x=wall, T=goal, A/B=portal)", renderState.terrain || serializeTokenMatrix(tMat));
      const bBox = mkArea("Blocks (o=empty, t/tr/tb=target, g1/g2=greens, r/b/n/s/e/w)", renderState.blocks || serializeTokenMatrix(bMat));
      drawer.append(tBox.wrap, bBox.wrap);

      const applyBtn = document.createElement("button");
      applyBtn.className = "btn btn-solve";
      applyBtn.textContent = "Apply Text to Board";
      applyBtn.style.gridColumn = "1 / -1";
      applyBtn.addEventListener("click", () => {
        const tLines = tBox.ta.value.trim().split(/\r?\n/).filter((l) => l.trim());
        const bLines = bBox.ta.value.trim().split(/\r?\n/).filter((l) => l.trim());
        const nr = Math.max(3, tLines.length, bLines.length);
        const nc = Math.max(
          3,
          ...tLines.map((l) => l.trim().split(/\s+/).length),
          ...bLines.map((l) => l.trim().split(/\s+/).length)
        );
        const nt = parseTokenMatrix(tBox.ta.value, nr, nc);
        const nb = parseTokenMatrix(bBox.ta.value, nr, nc);
        const next = JSON.parse(JSON.stringify(renderState));
        next.terrain = serializeTokenMatrix(nt);
        next.blocks = serializeTokenMatrix(nb);
        next.board = rebuildBoard(nt, nb);
        delete next.pieces;
        onEdit(next);
      });
      drawer.appendChild(applyBtn);
      stage.appendChild(drawer);
    }
  }

  // 3. Merged-Block Grid (with inset tiles so underlying Goal/Portal zones remain visible)
  const maxDim = Math.max(rows, cols);
  const cellSize = Math.max(30, Math.min(56, Math.floor(560 / maxDim)));

  const gridEl = document.createElement("div");
  gridEl.style.display = "grid";
  gridEl.style.gridTemplateColumns = `repeat(${cols}, ${cellSize}px)`;
  gridEl.style.gridTemplateRows = `repeat(${rows}, ${cellSize}px)`;
  gridEl.style.gap = "0px";
  gridEl.style.background = "var(--bg-main)";
  gridEl.style.border = "2px solid var(--border)";
  gridEl.style.borderRadius = "6px";
  gridEl.style.padding = "4px";
  gridEl.style.userSelect = "none";
  gridEl.style.touchAction = "none";
  gridEl.addEventListener("contextmenu", (e) => e.preventDefault());

  const hlSet = new Set((highlights?.cells || []).map(([r, c]) => `${r},${c}`));

  const getPieceKey = (r, c) => {
    if (r < 0 || r >= rows || c < 0 || c >= cols) return null;
    if (pieces) {
      const pid = pieces[r][c];
      return pid >= 0 ? `p:${pid}` : null;
    }
    const bTok = bMat[r]?.[c];
    if (bTok && bTok !== "o") return `b:${bTok}`;
    const val = String(board[r]?.[c] || "");
    if (val && val !== "#" && val !== "★" && !isPortalToken(val)) {
      return `v:${val}`;
    }
    return null;
  };

  const anchors = computeAnchorCells(rows, cols, getPieceKey);

  // Map chained tokens for quick badge lookup
  const chainBadgeMap = new Map();
  chains.forEach(([pair, mode], idx) => {
    if (!Array.isArray(pair)) return;
    const sym = mode === "invert" ? `⇄${idx + 1}` : `🔗${idx + 1}`;
    for (const tok of pair) {
      const k = String(tok).replace("'", "").toLowerCase();
      chainBadgeMap.set(k, (chainBadgeMap.get(k) ? chainBadgeMap.get(k) + " " : "") + sym);
    }
  });

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const val = String(board[r]?.[c] || "");
      const tTok = tMat[r]?.[c] || "o";
      const pk = getPieceKey(r, c);
      const pid = pieces ? pieces[r][c] : -1;

      const cell = document.createElement("div");
      cell.style.width = `${cellSize}px`;
      cell.style.height = `${cellSize}px`;
      cell.style.boxSizing = "border-box";
      cell.style.position = "relative";
      cell.style.display = "flex";
      cell.style.alignItems = "center";
      cell.style.justifyContent = "center";
      cell.style.cursor = canEdit ? "crosshair" : "default";
      cell.style.border = "1px solid rgba(255, 255, 255, 0.06)";

      // Base terrain / zone layer (drawn UNDER tiles)
      if (tTok === "x" || val === "#") {
        cell.style.background = "#3d434c";
        cell.style.border = "1px solid #22262c";
        cell.style.borderRadius = "3px";
      } else if (tTok === "T" || val === "★") {
        cell.style.background = "rgba(34, 197, 94, 0.22)";
        cell.style.border = "1.5px dashed #22c55e";
        const zLbl = document.createElement("span");
        zLbl.textContent = "★";
        zLbl.style.color = "#22c55e";
        zLbl.style.fontWeight = "700";
        zLbl.style.fontSize = pk !== null ? "10px" : `${Math.max(12, Math.floor(cellSize * 0.4))}px`;
        if (pk !== null) {
          zLbl.style.position = "absolute";
          zLbl.style.top = "1px";
          zLbl.style.left = "2px";
          zLbl.style.zIndex = "1";
        }
        cell.appendChild(zLbl);
      } else if (isPortalToken(tTok) || (pk === null && isPortalToken(val))) {
        const pName = isPortalToken(tTok) ? tTok : val;
        const [pBg, pBorder, pCol] = portalStyle(pName);
        cell.style.background = pBg;
        cell.style.border = `1.5px solid ${pBorder}`;
        const pLbl = document.createElement("span");
        pLbl.textContent = pName;
        pLbl.style.color = pCol;
        pLbl.style.fontWeight = "700";
        pLbl.style.fontSize = pk !== null ? "9px" : `${Math.max(11, Math.floor(cellSize * 0.34))}px`;
        if (pk !== null) {
          pLbl.style.position = "absolute";
          pLbl.style.top = "1px";
          pLbl.style.left = "2px";
          pLbl.style.zIndex = "1";
        }
        cell.appendChild(pLbl);
      } else {
        cell.style.background = "var(--bg-cell)";
      }

      if (hlSet.has(`${r},${c}`) && pk === null) {
        cell.style.boxShadow = "inset 0 0 0 2px #22c55e";
      }

      // Inset merged block tile layer (so Goal/Portal zones peek out underneath)
      if (pk !== null) {
        const cleanTok = (pieces ? val : (bMat[r]?.[c] || val)).replace("'", "").toLowerCase();
        const baseChar = cleanTok[0] || "g";
        const isIce = val.includes("'") || (bMat[r]?.[c] || "").includes("'");
        const bg = pieceColor(baseChar, cleanTok, pid);

        const sameTop = getPieceKey(r - 1, c) === pk;
        const sameBottom = getPieceKey(r + 1, c) === pk;
        const sameLeft = getPieceKey(r, c - 1) === pk;
        const sameRight = getPieceKey(r, c + 1) === pk;

        const insetPx = 5;
        const tile = document.createElement("div");
        tile.style.position = "absolute";
        tile.style.top = sameTop ? "0px" : `${insetPx}px`;
        tile.style.bottom = sameBottom ? "0px" : `${insetPx}px`;
        tile.style.left = sameLeft ? "0px" : `${insetPx}px`;
        tile.style.right = sameRight ? "0px" : `${insetPx}px`;
        tile.style.zIndex = "2";
        tile.style.display = "flex";
        tile.style.alignItems = "center";
        tile.style.justifyContent = "center";
        tile.style.fontWeight = "700";
        tile.style.fontSize = `${Math.max(10, Math.floor(cellSize * 0.32))}px`;
        tile.style.background = bg;
        tile.style.color = "#0b1116";
        tile.style.pointerEvents = "none";

        tile.style.borderTop = sameTop ? "none" : "2px solid rgba(0, 0, 0, 0.72)";
        tile.style.borderBottom = sameBottom ? "none" : "2px solid rgba(0, 0, 0, 0.72)";
        tile.style.borderLeft = sameLeft ? "none" : "2px solid rgba(0, 0, 0, 0.72)";
        tile.style.borderRight = sameRight ? "none" : "2px solid rgba(0, 0, 0, 0.72)";

        const rTL = !sameTop && !sameLeft ? "5px" : "0px";
        const rTR = !sameTop && !sameRight ? "5px" : "0px";
        const rBR = !sameBottom && !sameRight ? "5px" : "0px";
        const rBL = !sameBottom && !sameLeft ? "5px" : "0px";
        tile.style.borderRadius = `${rTL} ${rTR} ${rBR} ${rBL}`;

        if (chainSourceToken && cleanTok === chainSourceToken) {
          tile.style.boxShadow = "0 0 0 2px #38bdf8";
        }

        if (isIce) {
          if (!sameTop && !sameRight) addIceDogEar(tile, "tr");
          if (!sameTop && !sameLeft) addIceDogEar(tile, "tl");
          if (!sameBottom && !sameRight) addIceDogEar(tile, "br");
          if (!sameBottom && !sameLeft) addIceDogEar(tile, "bl");
        }

        if (anchors.has(`${r},${c}`)) {
          let glyph = DIR_GLYPH[baseChar] || baseChar.toUpperCase();
          if (baseChar === "t" && cleanTok.length >= 2 && DIR_GLYPH[cleanTok[1]]) {
            glyph = `★${DIR_GLYPH[cleanTok[1]]}`;
          }
          tile.appendChild(document.createTextNode(glyph));

          const badge = chainBadgeMap.get(cleanTok) || chainBadgeMap.get(baseChar);
          if (badge) {
            const cb = document.createElement("span");
            cb.textContent = badge;
            cb.style.position = "absolute";
            cb.style.bottom = "1px";
            cb.style.left = "2px";
            cb.style.fontSize = "8px";
            tile.appendChild(cb);
          }

          if (cleanTok.length > 1 && !(baseChar === "t" && cleanTok.length === 2 && DIR_GLYPH[cleanTok[1]])) {
            const sub = document.createElement("span");
            sub.textContent = cleanTok.toUpperCase();
            sub.style.position = "absolute";
            sub.style.bottom = "1px";
            sub.style.right = "2px";
            sub.style.fontSize = "8px";
            sub.style.opacity = "0.75";
            tile.appendChild(sub);
          }
        }
        cell.appendChild(tile);
      }

      if (canEdit) {
        cell.addEventListener("pointerdown", (e) => {
          e.preventDefault();
          if (e.button !== 2 && activeBrush === "__ice__") {
            toggleIceOnPiece(r, c);
            return;
          }
          if (e.button !== 2 && (activeBrush === "__chain_same__" || activeBrush === "__chain_invert__")) {
            handleChainClick(r, c, activeBrush === "__chain_invert__" ? "invert" : "same");
            return;
          }

          dragActive = true;
          dragVisited = new Set([`${r},${c}`]);
          dragErase = e.button === 2 || activeBrush === "o";

          if (dragErase) {
            dragToken = "o";
          } else {
            const brushDef = BRUSHES.find((b) => b.token === activeBrush) || BRUSHES[0];
            if (activeBrush === "__portalA__") {
              dragToken = `A${portalPairNum}`;
            } else if (activeBrush === "__portalB__") {
              dragToken = `B${portalPairNum}`;
            } else if (brushDef.kind === "terrain") {
              dragToken = activeBrush;
            } else if (activeBrush === "t") {
              dragToken = `${targetDirToken}${iceModifier ? "'" : ""}`;
              lastPieceToken = dragToken;
            } else {
              if (e.shiftKey || !autoNewPiece) {
                const lastBase = lastPieceToken.replace("'", "")[0];
                dragToken = lastBase === activeBrush ? lastPieceToken : nextFreeToken(bMat, activeBrush, iceModifier);
              } else {
                dragToken = nextFreeToken(bMat, activeBrush, iceModifier);
              }
              lastPieceToken = dragToken;
            }
          }
          applyCell(r, c, dragToken);
        });

        cell.addEventListener("pointerenter", () => {
          if (!dragActive) return;
          const key = `${r},${c}`;
          if (dragVisited.has(key)) return;
          dragVisited.add(key);
          applyCell(r, c, dragToken);
        });
      }

      gridEl.appendChild(cell);
    }
  }

  stage.appendChild(gridEl);

  // Copy Terrain + Blocks button (handy for waypoint chaining from playback steps)
  const copyBar = document.createElement("div");
  copyBar.className = "grid-toolbar";
  copyBar.style.marginTop = "6px";
  const btnCopy = document.createElement("button");
  btnCopy.className = "btn";
  btnCopy.style.fontSize = "11px";
  btnCopy.style.padding = "3px 8px";
  btnCopy.textContent = "Copy Terrain & Blocks";
  btnCopy.addEventListener("click", async () => {
    const curBlocks = Array.isArray(board)
      ? serializeTokenMatrix(
          board.map((row, rr) =>
            row.map((cellVal, cc) => {
              const s = String(cellVal || "");
              const hasPiece = pieces ? pieces[rr][cc] >= 0 : (bMat[rr]?.[cc] && bMat[rr][cc] !== "o");
              if (!s || s === "#" || s === "★" || (!hasPiece && isPortalToken(s))) return "o";
              return s.toLowerCase();
            })
          )
        )
      : serializeTokenMatrix(bMat);
    const payload = `TERRAIN:\n${serializeTokenMatrix(tMat)}\n\nBLOCKS:\n${curBlocks}`;
    try {
      await navigator.clipboard.writeText(payload);
      btnCopy.textContent = "Copied!";
      setTimeout(() => (btnCopy.textContent = "Copy Terrain & Blocks"), 1200);
    } catch {
      btnCopy.textContent = "Copy failed";
    }
  });
  copyBar.appendChild(btnCopy);
  stage.appendChild(copyBar);

  // 4. Active Chains summary (with click-to-remove when editing)
  if (chains.length > 0) {
    const cBar = document.createElement("div");
    cBar.className = "grid-toolbar";
    cBar.style.marginTop = "8px";
    cBar.style.flexWrap = "wrap";
    const lbl = document.createElement("span");
    lbl.textContent = "Chains:";
    lbl.style.fontSize = "11px";
    lbl.style.color = "var(--text-muted)";
    cBar.appendChild(lbl);

    chains.forEach(([pair, mode], idx) => {
      const chip = document.createElement("button");
      chip.className = "btn";
      chip.style.fontSize = "11px";
      chip.style.padding = "2px 7px";
      chip.textContent = `${pair.join(mode === "invert" ? " ⇄ " : " 🔗 ")} (${mode})${canEdit ? " ×" : ""}`;
      if (canEdit) {
        chip.addEventListener("click", () => {
          const next = JSON.parse(JSON.stringify(renderState));
          next.chains = chains.filter((_, i) => i !== idx);
          onEdit(next);
        });
      }
      cBar.appendChild(chip);
    });
    stage.appendChild(cBar);
  }
}
