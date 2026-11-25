const COLORS = [
  { code: "W", name: "White", hex: "#F5F6FA", text: "#111" },
  { code: "Y", name: "Yellow", hex: "#FFE600", text: "#111" },
  { code: "G", name: "Green", hex: "#01CA6B", text: "#111" },
  { code: "B", name: "Blue", hex: "#2E86DE", text: "#fff" },
  { code: "O", name: "Orange", hex: "#FA8231", text: "#111" },
  { code: "R", name: "Red", hex: "#FF3F34", text: "#fff" },
];

const COLOR_MAP = Object.fromEntries(COLORS.map((c) => [c.code, c]));
const FACE_NAMES = ["U", "R", "F", "D", "L", "B"];
const DEFAULT_FACE_COLORS = { U: "W", R: "R", F: "G", D: "Y", L: "O", B: "B" };

// Net layout coordinates: [face, gridCol, gridRow]
const NET_LAYOUT = [
  ["U", 1, 0],
  ["L", 0, 1],
  ["F", 1, 1],
  ["R", 2, 1],
  ["B", 3, 1],
  ["D", 1, 2],
];

const DEFAULT_ROT_X = -28;
const DEFAULT_ROT_Y = -38;
let activeBrush = "W";
let rotX = DEFAULT_ROT_X;
let rotY = DEFAULT_ROT_Y;

function cloneFaces(faces) {
  const out = {};
  for (const f of FACE_NAMES) {
    out[f] = (faces?.[f] || Array.from({ length: 3 }, () => Array(3).fill(DEFAULT_FACE_COLORS[f]))).map(
      (row) => row.slice()
    );
  }
  return out;
}

function solvedFaces() {
  const out = {};
  for (const f of FACE_NAMES) {
    out[f] = Array.from({ length: 3 }, () => Array(3).fill(DEFAULT_FACE_COLORS[f]));
  }
  return out;
}

function makeFaceletPerm(cycles) {
  const p = Array.from({ length: 54 }, (_, i) => i);
  for (const [a, b, c, d] of cycles) {
    p[b] = a;
    p[c] = b;
    p[d] = c;
    p[a] = d;
  }
  return p;
}

function faceCycles(base) {
  return [
    [base + 0, base + 2, base + 8, base + 6],
    [base + 1, base + 5, base + 7, base + 3],
  ];
}

const BASE_PERMS = {
  U: makeFaceletPerm([...faceCycles(0), [18, 36, 45, 9], [19, 37, 46, 10], [20, 38, 47, 11]]),
  D: makeFaceletPerm([...faceCycles(27), [24, 15, 51, 42], [25, 16, 52, 43], [26, 17, 53, 44]]),
  R: makeFaceletPerm([...faceCycles(9), [2, 51, 29, 20], [5, 48, 32, 23], [8, 45, 35, 26]]),
  L: makeFaceletPerm([...faceCycles(36), [0, 18, 27, 53], [3, 21, 30, 50], [6, 24, 33, 47]]),
  F: makeFaceletPerm([...faceCycles(18), [6, 9, 29, 44], [7, 12, 28, 41], [8, 15, 27, 38]]),
  B: makeFaceletPerm([...faceCycles(45), [2, 36, 33, 17], [1, 39, 34, 14], [0, 42, 35, 11]]),
};

function applySingleTurn(faces, move) {
  const face = move[0];
  const suffix = move.slice(1);
  const times = suffix === "2" ? 2 : suffix === "'" ? 3 : 1;
  const perm = BASE_PERMS[face];
  let arr = [];
  for (const f of FACE_NAMES) {
    for (const row of faces[f]) arr.push(...row);
  }
  for (let t = 0; t < times; t++) {
    arr = arr.map((_, i) => arr[perm[i]]);
  }
  const next = {};
  FACE_NAMES.forEach((f, idx) => {
    const base = idx * 9;
    next[f] = [
      arr.slice(base, base + 3),
      arr.slice(base + 3, base + 6),
      arr.slice(base + 6, base + 9),
    ];
  });
  return next;
}

function countColors(faces) {
  const counts = Object.fromEntries(COLORS.map((c) => [c.code, 0]));
  for (const f of FACE_NAMES) {
    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) {
        const val = faces[f][r][c];
        counts[val] = (counts[val] || 0) + 1;
      }
    }
  }
  return counts;
}

function validateStickers(faces) {
  const centers = FACE_NAMES.map((f) => faces[f][1][1]);
  if (new Set(centers).size !== 6) {
    return { valid: false, reason: "All 6 center stickers must be distinct colors." };
  }
  const counts = countColors(faces);
  for (const c of COLORS) {
    if ((counts[c.code] || 0) !== 9) {
      return { valid: false, reason: `Color ${c.code} has ${counts[c.code] || 0}/9 stickers.` };
    }
  }
  return { valid: true, reason: "" };
}

function paintSticker(faces, f, r, c, cycleOnly = false) {
  const next = cloneFaces(faces);
  if (cycleOnly || next[f][r][c] === activeBrush) {
    const idx = COLORS.findIndex((x) => x.code === next[f][r][c]);
    next[f][r][c] = COLORS[(idx + 1) % COLORS.length].code;
  } else {
    next[f][r][c] = activeBrush;
  }
  return next;
}

function build3DFace(faceCode, grid, activeFace, editable, onStickerPaint) {
  const faceEl = document.createElement("div");
  const isHot = activeFace === faceCode;
  faceEl.style.cssText = `
    position: absolute;
    width: 108px;
    height: 108px;
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 3px;
    padding: 4px;
    background: #141619;
    border-radius: 6px;
    box-sizing: border-box;
    border: 2px solid ${isHot ? "var(--accent-warm, #FFE600)" : "#0d0e10"};
    box-shadow: ${isHot ? "0 0 14px var(--accent-warm, #FFE600)" : "none"};
    backface-visibility: hidden;
  `;

  const transforms = {
    F: "translateZ(54px)",
    B: "rotateY(180deg) translateZ(54px)",
    R: "rotateY(90deg) translateZ(54px)",
    L: "rotateY(-90deg) translateZ(54px)",
    U: "rotateX(90deg) translateZ(54px)",
    D: "rotateX(-90deg) translateZ(54px)",
  };
  faceEl.style.transform = transforms[faceCode];

  for (let r = 0; r < 3; r++) {
    for (let c = 0; c < 3; c++) {
      const code = grid[r][c];
      const info = COLOR_MAP[code] || { hex: "#444", text: "#fff" };
      const cell = document.createElement("div");
      cell.style.cssText = `
        background: ${info.hex};
        color: ${info.text};
        border-radius: 4px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 10px;
        font-weight: 700;
        opacity: 0.96;
        cursor: ${editable ? "pointer" : "grab"};
      `;
      if (r === 1 && c === 1) {
        cell.textContent = faceCode;
      }
      if (editable) {
        cell.title = `${faceCode}[${r},${c}] = ${code} (click to paint ${activeBrush}, right-click to cycle)`;
        cell.addEventListener("click", (ev) => {
          ev.stopPropagation();
          onStickerPaint(faceCode, r, c, false);
        });
        cell.addEventListener("contextmenu", (ev) => {
          ev.preventDefault();
          ev.stopPropagation();
          onStickerPaint(faceCode, r, c, true);
        });
      }
      faceEl.appendChild(cell);
    }
  }
  return faceEl;
}

export function render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed) {
  stage.innerHTML = "";
  const faces = cloneFaces(renderState?.faces);
  const counts = countColors(faces);
  const validation = validateStickers(faces);
  if (typeof setSolveAllowed === "function") {
    setSolveAllowed(validation.valid, validation.reason);
  }

  const root = document.createElement("div");
  root.style.cssText = `
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 14px;
    width: 100%;
    padding: 8px 12px;
    box-sizing: border-box;
  `;

  // Top toolbar (Brush palette in EDIT mode, or Move badge in PLAYBACK)
  const topBar = document.createElement("div");
  topBar.className = "grid-toolbar";
  topBar.style.cssText = "display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:8px;";

  if (editable) {
    for (const c of COLORS) {
      const btn = document.createElement("button");
      const n = counts[c.code] || 0;
      const isSelected = activeBrush === c.code;
      btn.className = "btn";
      btn.style.cssText = `
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 9px;
        border: 2px solid ${isSelected ? "var(--accent-primary)" : "var(--border)"};
        box-shadow: ${isSelected ? "0 0 0 1px var(--accent-primary)" : "none"};
        font-size: 12px;
      `;
      const swatch = document.createElement("span");
      swatch.style.cssText = `width:12px; height:12px; border-radius:3px; background:${c.hex}; border:1px solid rgba(0,0,0,0.35);`;
      const label = document.createElement("span");
      label.textContent = `${c.code} (${n}/9)`;
      label.style.color = n === 9 ? "var(--text-main)" : "var(--accent-hot)";
      btn.appendChild(swatch);
      btn.appendChild(label);
      btn.addEventListener("click", () => {
        activeBrush = c.code;
        render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
      });
      topBar.appendChild(btn);
    }

    const btnSolved = document.createElement("button");
    btnSolved.className = "btn";
    btnSolved.textContent = "Solved";
    btnSolved.addEventListener("click", () => onEdit({ faces: solvedFaces() }));
    topBar.appendChild(btnSolved);

    const btnScramble = document.createElement("button");
    btnScramble.className = "btn";
    btnScramble.textContent = "Scramble";
    btnScramble.addEventListener("click", () => {
      const moves = ["U", "U'", "U2", "D", "D'", "D2", "L", "L'", "L2", "R", "R'", "R2", "F", "F'", "F2", "B", "B'", "B2"];
      let cur = cloneFaces(faces);
      let prevFace = "";
      for (let i = 0; i < 18; i++) {
        const choices = moves.filter((m) => m[0] !== prevFace);
        const mv = choices[Math.floor(Math.random() * choices.length)];
        prevFace = mv[0];
        cur = applySingleTurn(cur, mv);
      }
      onEdit({ faces: cur });
    });
    topBar.appendChild(btnScramble);
  } else {
    const moveBadge = document.createElement("div");
    moveBadge.style.cssText = `
      padding: 6px 14px;
      border-radius: 6px;
      background: var(--bg-panel);
      border: 1px solid var(--accent-primary);
      font-weight: 700;
      font-size: 14px;
      color: var(--accent-primary);
    `;
    moveBadge.textContent = highlights?.move ? `Turn: ${highlights.move}` : "Cube State";
    topBar.appendChild(moveBadge);
  }

  const btnResetView = document.createElement("button");
  btnResetView.className = "btn";
  btnResetView.textContent = "Reset 3D";
  btnResetView.title = "Reset 3D camera angle";
  btnResetView.addEventListener("click", () => {
    rotX = DEFAULT_ROT_X;
    rotY = DEFAULT_ROT_Y;
    render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
  });
  topBar.appendChild(btnResetView);
  root.appendChild(topBar);

  // Main visual row: 3D Isometric Cube + 2D Unfolded Net
  const mainRow = document.createElement("div");
  mainRow.style.cssText = `
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 28px;
    width: 100%;
  `;

  // 3D Cube Viewport (drag-to-rotate)
  const cubeStage = document.createElement("div");
  cubeStage.style.cssText = `
    position: relative;
    width: 210px;
    height: 210px;
    display: flex;
    align-items: center;
    justify-content: center;
    perspective: 700px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 12px;
    cursor: grab;
    user-select: none;
    touch-action: none;
  `;
  const cubePivot = document.createElement("div");
  cubePivot.style.cssText = `
    position: relative;
    width: 108px;
    height: 108px;
    transform-style: preserve-3d;
    transform: rotateX(${rotX}deg) rotateY(${rotY}deg);
  `;
  let suppressClick = false;
  const on3DPaint = (f, r, c, cycleOnly) => {
    if (suppressClick) return;
    onEdit({ faces: paintSticker(faces, f, r, c, cycleOnly) });
  };
  for (const f of FACE_NAMES) {
    cubePivot.appendChild(build3DFace(f, faces[f], highlights?.face, editable, on3DPaint));
  }
  cubeStage.appendChild(cubePivot);

  const dragHint = document.createElement("div");
  dragHint.style.cssText = `
    position: absolute;
    bottom: 6px;
    right: 9px;
    font-size: 10px;
    color: var(--text-muted);
    opacity: 0.75;
    pointer-events: none;
  `;
  dragHint.textContent = editable ? "Drag to rotate · Click to paint" : "Drag to rotate";
  cubeStage.appendChild(dragHint);

  let dragging = false;
  let dragDist = 0;
  let lastX = 0;
  let lastY = 0;
  cubeStage.addEventListener("pointerdown", (ev) => {
    if (ev.button !== 0) return;
    dragging = true;
    dragDist = 0;
    suppressClick = false;
    lastX = ev.clientX;
    lastY = ev.clientY;
  });
  cubeStage.addEventListener("pointermove", (ev) => {
    if (!dragging) return;
    const dx = ev.clientX - lastX;
    const dy = ev.clientY - lastY;
    lastX = ev.clientX;
    lastY = ev.clientY;
    dragDist += Math.hypot(dx, dy);
    if (dragDist > 4) {
      suppressClick = true;
      cubeStage.style.cursor = "grabbing";
      if (!cubeStage.hasPointerCapture(ev.pointerId)) {
        cubeStage.setPointerCapture(ev.pointerId);
      }
      rotY += dx * 0.7;
      rotX = Math.max(-89, Math.min(89, rotX - dy * 0.7));
      cubePivot.style.transform = `rotateX(${rotX}deg) rotateY(${rotY}deg)`;
    }
  });
  const endDrag = (ev) => {
    if (!dragging) return;
    dragging = false;
    cubeStage.style.cursor = "grab";
    if (cubeStage.hasPointerCapture(ev.pointerId)) {
      cubeStage.releasePointerCapture(ev.pointerId);
    }
    if (suppressClick) {
      setTimeout(() => {
        suppressClick = false;
      }, 0);
    }
  };
  cubeStage.addEventListener("pointerup", endDrag);
  cubeStage.addEventListener("pointercancel", endDrag);

  mainRow.appendChild(cubeStage);

  // 2D Unfolded Net (4 cols x 3 rows of 3x3 faces)
  const netWrap = document.createElement("div");
  netWrap.style.cssText = `
    display: grid;
    grid-template-columns: repeat(4, auto);
    grid-template-rows: repeat(3, auto);
    gap: 6px;
    padding: 10px;
    background: var(--bg-panel);
    border: 1px solid var(--border);
    border-radius: 12px;
  `;

  for (const [f, gCol, gRow] of NET_LAYOUT) {
    const faceBox = document.createElement("div");
    const isHot = highlights?.face === f;
    faceBox.style.cssText = `
      grid-column: ${gCol + 1};
      grid-row: ${gRow + 1};
      display: grid;
      grid-template-columns: repeat(3, 28px);
      grid-template-rows: repeat(3, 28px);
      gap: 2px;
      padding: 3px;
      border-radius: 6px;
      background: #141619;
      border: 2px solid ${isHot ? "var(--accent-warm, #FFE600)" : "transparent"};
      box-shadow: ${isHot ? "0 0 10px var(--accent-warm, #FFE600)" : "none"};
    `;

    for (let r = 0; r < 3; r++) {
      for (let c = 0; c < 3; c++) {
        const code = faces[f][r][c];
        const info = COLOR_MAP[code] || { hex: "#444", text: "#fff" };
        const sticker = document.createElement("button");
        sticker.type = "button";
        sticker.style.cssText = `
          width: 28px;
          height: 28px;
          border: none;
          border-radius: 4px;
          background: ${info.hex};
          color: ${info.text};
          font-size: 11px;
          font-weight: 700;
          cursor: ${editable ? "pointer" : "default"};
          padding: 0;
          display: flex;
          align-items: center;
          justify-content: center;
        `;
        if (r === 1 && c === 1) {
          sticker.textContent = f;
        }
        if (editable) {
          sticker.title = `${f}[${r},${c}] = ${code} (click to paint ${activeBrush}, right-click to cycle)`;
          sticker.addEventListener("click", () => {
            onEdit({ faces: paintSticker(faces, f, r, c, false) });
          });
          sticker.addEventListener("contextmenu", (ev) => {
            ev.preventDefault();
            onEdit({ faces: paintSticker(faces, f, r, c, true) });
          });
        }
        faceBox.appendChild(sticker);
      }
    }
    netWrap.appendChild(faceBox);
  }
  mainRow.appendChild(netWrap);
  root.appendChild(mainRow);

  // Manual Face-Turn Buttons in EDIT mode
  if (editable) {
    const turnBar = document.createElement("div");
    turnBar.style.cssText = "display:flex; flex-wrap:wrap; justify-content:center; gap:5px;";
    const turns = ["U", "U'", "R", "R'", "F", "F'", "D", "D'", "L", "L'", "B", "B'"];
    for (const mv of turns) {
      const b = document.createElement("button");
      b.className = "btn";
      b.style.cssText = "padding: 4px 8px; font-size: 12px; min-width: 32px;";
      b.textContent = mv;
      b.title = `Apply ${mv} turn`;
      b.addEventListener("click", () => {
        onEdit({ faces: applySingleTurn(faces, mv) });
      });
      turnBar.appendChild(b);
    }
    root.appendChild(turnBar);

    if (!validation.valid) {
      const warn = document.createElement("div");
      warn.style.cssText = "font-size:12px; color:var(--accent-hot); font-weight:600;";
      warn.textContent = validation.reason;
      root.appendChild(warn);
    }
  }

  stage.appendChild(root);
}
