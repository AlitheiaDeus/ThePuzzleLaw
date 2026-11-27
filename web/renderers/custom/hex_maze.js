import { renderGrid } from "/renderers/grid.js";

const BRUSHES = [
  { val: 0, label: "Empty", color: "#232629" },
  { val: 1, label: "Wall (█)", color: "#621D19" },
  { val: 2, label: "Start (S)", color: "#01CA6B" },
  { val: 3, label: "Goal (G)", color: "#FFE600" },
  { val: 4, label: "2× Mud", color: "#4E4326" },
  { val: 5, label: "4× Swamp", color: "#61324A" },
];

const HEX_EVEN_DIRS = [
  [-1, -1],
  [-1, 0],
  [0, -1],
  [0, 1],
  [1, -1],
  [1, 0],
];
const HEX_ODD_DIRS = [
  [-1, 0],
  [-1, 1],
  [0, -1],
  [0, 1],
  [1, 0],
  [1, 1],
];

let activeHexBrush = 1;
let hexEditMode = "tiles"; // "tiles" | "edges"

function hexEdgeKey(r1, c1, r2, c2) {
  const first = r1 < r2 || (r1 === r2 && c1 < c2);
  const [ar, ac, br, bc] = first ? [r1, c1, r2, c2] : [r2, c2, r1, c1];
  return `${ar},${ac}|${br},${bc}`;
}

function hexVertices(cx, cy, radius) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    pts.push([cx + radius * Math.cos(angle), cy + radius * Math.sin(angle)]);
  }
  return pts;
}

function hexPointsStr(verts) {
  return verts.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ");
}

function sharedSegment(vertsA, vertsB) {
  // Find the two closest vertex pairs between adjacent hexes A and B
  const pairs = [];
  for (let i = 0; i < 6; i++) {
    for (let j = 0; j < 6; j++) {
      const d = Math.hypot(vertsA[i][0] - vertsB[j][0], vertsA[i][1] - vertsB[j][1]);
      pairs.push({ d, pt: [(vertsA[i][0] + vertsB[j][0]) * 0.5, (vertsA[i][1] + vertsB[j][1]) * 0.5] });
    }
  }
  pairs.sort((a, b) => a.d - b.d);
  return [pairs[0].pt, pairs[1].pt];
}

function resizeBoard(board, nr, nc) {
  const out = Array.from({ length: nr }, (_, r) =>
    Array.from({ length: nc }, (_, c) => (board?.[r]?.[c] !== undefined ? board[r][c] : 0))
  );
  if (!out.some((row) => row.includes(2))) out[0][0] = 2;
  if (!out.some((row) => row.includes(3))) out[nr - 1][nc - 1] = 3;
  return out;
}

export function render(stage, solver, renderState, highlights, editable, onEdit) {
  if (renderState?.geometry !== "Hexagonal (6-Way)") {
    return renderGrid(stage, solver, renderState, highlights, editable, onEdit);
  }

  stage.innerHTML = "";
  const board = renderState?.board || [];
  const rows = board.length;
  const cols = board[0]?.length || 0;
  if (!rows || !cols) return;

  const gm = solver.grid_meta || {};
  const colors = gm.colors || {};
  const labels = gm.labels || {};
  const hexWalls = new Set(Array.isArray(renderState.hex_walls) ? renderState.hex_walls : []);

  const root = document.createElement("div");
  root.style.cssText = "display:flex; flex-direction:column; align-items:center; gap:12px; width:100%;";

  if (editable) {
    const bar = document.createElement("div");
    bar.className = "grid-toolbar";
    bar.style.cssText = "display:flex; flex-wrap:wrap; align-items:center; justify-content:center; gap:8px;";

    const makeDimSelect = (labelText, curVal, onPick) => {
      const wrap = document.createElement("label");
      wrap.style.cssText = "display:inline-flex; align-items:center; gap:5px; font-size:12px; color:var(--text-muted);";
      wrap.textContent = labelText;
      const sel = document.createElement("select");
      for (let d = 2; d <= 12; d++) {
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

    bar.appendChild(
      makeDimSelect("Rows", rows, (nr) => {
        onEdit({ ...renderState, board: resizeBoard(board, nr, cols) });
      })
    );
    bar.appendChild(
      makeDimSelect("Cols", cols, (nc) => {
        onEdit({ ...renderState, board: resizeBoard(board, rows, nc) });
      })
    );

    // Setup mode toggle: Tiles vs Edges
    const btnTiles = document.createElement("button");
    btnTiles.className = "btn" + (hexEditMode === "tiles" ? " btn-solve" : "");
    btnTiles.textContent = "Edit: Tiles";
    btnTiles.addEventListener("click", () => {
      hexEditMode = "tiles";
      render(stage, solver, renderState, highlights, editable, onEdit);
    });
    bar.appendChild(btnTiles);

    const btnEdges = document.createElement("button");
    btnEdges.className = "btn" + (hexEditMode === "edges" ? " btn-solve" : "");
    btnEdges.textContent = "Edit: Edges";
    btnEdges.addEventListener("click", () => {
      hexEditMode = "edges";
      render(stage, solver, renderState, highlights, editable, onEdit);
    });
    bar.appendChild(btnEdges);

    if (hexWalls.size > 0) {
      const btnClearEdges = document.createElement("button");
      btnClearEdges.className = "btn";
      btnClearEdges.textContent = "Clear Edges";
      btnClearEdges.addEventListener("click", () => {
        const next = { ...renderState };
        delete next.hex_walls;
        onEdit(next);
      });
      bar.appendChild(btnClearEdges);
    }

    if (hexEditMode === "tiles") {
      for (const b of BRUSHES) {
        const btn = document.createElement("button");
        btn.className = "btn";
        const selected = activeHexBrush === b.val;
        btn.style.cssText = `
          display:inline-flex; align-items:center; gap:5px; padding:4px 8px; font-size:12px;
          border:2px solid ${selected ? "var(--accent-primary)" : "var(--border)"};
        `;
        const sw = document.createElement("span");
        sw.style.cssText = `width:11px; height:11px; border-radius:3px; background:${colors[String(b.val)] || b.color};`;
        const txt = document.createElement("span");
        txt.textContent = b.label;
        btn.appendChild(sw);
        btn.appendChild(txt);
        btn.addEventListener("click", () => {
          activeHexBrush = b.val;
          render(stage, solver, renderState, highlights, editable, onEdit);
        });
        bar.appendChild(btn);
      }
    }

    root.appendChild(bar);
  }

  const radius = Math.max(18, Math.min(30, Math.floor(380 / Math.max(rows, cols))));
  const hexW = Math.sqrt(3) * radius;
  const hexH = 2 * radius;
  const pad = radius + 8;
  const svgW = Math.ceil(cols * hexW + hexW * 0.5 + pad * 2);
  const svgH = Math.ceil((rows - 1) * (hexH * 0.75) + hexH + pad * 2);

  const centerOf = (r, c) => [
    pad + c * hexW + (r % 2 === 1 ? hexW * 0.5 : 0) + hexW * 0.5,
    pad + r * (hexH * 0.75) + radius,
  ];

  const hiSet = new Set((highlights?.cells || []).map(([r, c]) => `${r},${c}`));
  const hiColor =
    highlights?.color === "hot"
      ? "var(--accent-hot)"
      : highlights?.color === "secondary"
      ? "var(--accent-secondary)"
      : "var(--accent-primary)";

  const svgNS = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(svgNS, "svg");
  svg.setAttribute("class", "puzzle-svg-board hex-maze-svg");
  svg.setAttribute("viewBox", `0 0 ${svgW} ${svgH}`);
  svg.style.cssText = `width:min(100%, ${svgW}px); height:auto; max-height:460px; padding:6px;`;

  const fillLayer = document.createElementNS(svgNS, "g");
  fillLayer.setAttribute("class", "theme-fill-layer");
  const strokeLayer = document.createElementNS(svgNS, "g");
  strokeLayer.setAttribute("class", "theme-stroke-layer");
  const textLayer = document.createElementNS(svgNS, "g");
  textLayer.setAttribute("class", "theme-text-layer");
  const hitLayer = document.createElementNS(svgNS, "g");
  hitLayer.setAttribute("class", "theme-hit-layer");
  svg.append(fillLayer, strokeLayer, textLayer, hitLayer);

  const vertsGrid = Array.from({ length: rows }, (_, r) =>
    Array.from({ length: cols }, (_, c) => {
      const [cx, cy] = centerOf(r, c);
      return hexVertices(cx, cy, radius - 1.5);
    })
  );

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const val = board[r][c];
      const [cx, cy] = centerOf(r, c);
      const isHi = hiSet.has(`${r},${c}`);
      const ptsStr = hexPointsStr(vertsGrid[r][c]);

      const polyFill = document.createElementNS(svgNS, "polygon");
      polyFill.setAttribute("points", ptsStr);
      polyFill.setAttribute("fill", val === 0 ? "var(--bg-cell)" : (colors[String(val)] || "var(--bg-cell)"));
      polyFill.setAttribute("stroke", "none");
      fillLayer.appendChild(polyFill);

      const polyOutline = document.createElementNS(svgNS, "polygon");
      polyOutline.setAttribute("points", ptsStr);
      polyOutline.setAttribute("fill", "none");
      polyOutline.setAttribute("stroke", isHi ? hiColor : "var(--border)");
      polyOutline.setAttribute("stroke-width", isHi ? "3" : "1.5");
      strokeLayer.appendChild(polyOutline);

      if (editable && hexEditMode === "tiles") {
        const polyHit = document.createElementNS(svgNS, "polygon");
        polyHit.setAttribute("points", ptsStr);
        polyHit.setAttribute("fill", "transparent");
        polyHit.style.cursor = "pointer";
        polyHit.addEventListener("click", () => {
          const nextBoard = board.map((row) => row.slice());
          if (activeHexBrush === 2 || activeHexBrush === 3) {
            for (let rr = 0; rr < rows; rr++) {
              for (let cc = 0; cc < cols; cc++) {
                if (nextBoard[rr][cc] === activeHexBrush) nextBoard[rr][cc] = 0;
              }
            }
          }
          nextBoard[r][c] = nextBoard[r][c] === activeHexBrush ? 0 : activeHexBrush;
          onEdit({ ...renderState, board: nextBoard });
        });
        hitLayer.appendChild(polyHit);
      }

      const lbl = labels[String(val)] ?? "";
      if (lbl) {
        const text = document.createElementNS(svgNS, "text");
        text.setAttribute("x", String(cx));
        text.setAttribute("y", String(cy + 4));
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("font-size", String(Math.max(10, Math.round(radius * 0.48))));
        text.setAttribute("font-weight", "700");
        text.setAttribute("fill", val === 2 || val === 3 ? "#111" : "var(--text-main)");
        text.style.pointerEvents = "none";
        text.textContent = lbl;
        textLayer.appendChild(text);
      }
    }
  }

  // Render interior hex edges (visible when blocked, and clickable when hexEditMode === "edges")
  const drawnEdges = new Set();
  for (let r = 0; r < rows; r++) {
    const dirs = r % 2 === 1 ? HEX_ODD_DIRS : HEX_EVEN_DIRS;
    for (let c = 0; c < cols; c++) {
      for (const [dr, dc] of dirs) {
        const nr = r + dr;
        const nc = c + dc;
        if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue;
        const key = hexEdgeKey(r, c, nr, nc);
        if (drawnEdges.has(key)) continue;
        drawnEdges.add(key);

        const isWall = hexWalls.has(key);
        const showInteractive = editable && hexEditMode === "edges";
        if (!isWall && !showInteractive) continue;

        const [p1, p2] = sharedSegment(vertsGrid[r][c], vertsGrid[nr][nc]);
        if (isWall) {
          const wallLine = document.createElementNS(svgNS, "line");
          wallLine.setAttribute("x1", p1[0].toFixed(2));
          wallLine.setAttribute("y1", p1[1].toFixed(2));
          wallLine.setAttribute("x2", p2[0].toFixed(2));
          wallLine.setAttribute("y2", p2[1].toFixed(2));
          wallLine.setAttribute("stroke", "var(--accent-hot, #FF4D4D)");
          wallLine.setAttribute("stroke-width", "5");
          wallLine.setAttribute("stroke-linecap", "round");
          wallLine.style.pointerEvents = "none";
          strokeLayer.appendChild(wallLine);
        }

        if (showInteractive) {
          const hit = document.createElementNS(svgNS, "line");
          hit.setAttribute("x1", p1[0].toFixed(2));
          hit.setAttribute("y1", p1[1].toFixed(2));
          hit.setAttribute("x2", p2[0].toFixed(2));
          hit.setAttribute("y2", p2[1].toFixed(2));
          hit.setAttribute("stroke", isWall ? "transparent" : "var(--grid-line, rgba(255,255,255,0.14))");
          hit.setAttribute("stroke-width", "9");
          hit.setAttribute("stroke-linecap", "round");
          hit.style.cursor = "pointer";
          hit.addEventListener("click", () => {
            const nextWalls = new Set(hexWalls);
            if (nextWalls.has(key)) nextWalls.delete(key);
            else nextWalls.add(key);
            const nextState = { ...renderState };
            if (nextWalls.size > 0) nextState.hex_walls = Array.from(nextWalls).sort();
            else delete nextState.hex_walls;
            onEdit(nextState);
          });
          hitLayer.appendChild(hit);
        }
      }
    }
  }

  if (Array.isArray(highlights?.tied_paths_svg) && highlights.tied_paths_svg.length > 0) {
    const toPx = (nx, ny) => [pad + hexW * 0.5 + nx * hexW, pad + radius + ny * hexW];
    for (const ops of highlights.tied_paths_svg) {
      const d = ops
        .map((op) => {
          const [px, py] = toPx(op.x, op.y);
          if (op.op === "M") return `M ${px.toFixed(2)} ${py.toFixed(2)}`;
          if (op.op === "A") {
            const rx = (op.rx * hexW).toFixed(2);
            const ry = (op.ry * hexW).toFixed(2);
            return `A ${rx} ${ry} 0 0 ${op.sweep} ${px.toFixed(2)} ${py.toFixed(2)}`;
          }
          return `L ${px.toFixed(2)} ${py.toFixed(2)}`;
        })
        .join(" ");
      const tEl = document.createElementNS(svgNS, "path");
      tEl.setAttribute("d", d);
      tEl.setAttribute("fill", "none");
      tEl.setAttribute("stroke", "var(--accent-secondary)");
      tEl.setAttribute("stroke-opacity", "0.45");
      tEl.setAttribute("stroke-dasharray", "5 4");
      tEl.setAttribute("stroke-width", "2.5");
      tEl.setAttribute("stroke-linecap", "round");
      tEl.setAttribute("stroke-linejoin", "round");
      tEl.style.pointerEvents = "none";
      strokeLayer.appendChild(tEl);
    }
  }

  if (Array.isArray(highlights?.path_svg) && highlights.path_svg.length > 0) {
    const toPx = (nx, ny) => [pad + hexW * 0.5 + nx * hexW, pad + radius + ny * hexW];
    const d = highlights.path_svg
      .map((op) => {
        const [px, py] = toPx(op.x, op.y);
        if (op.op === "M") return `M ${px.toFixed(2)} ${py.toFixed(2)}`;
        if (op.op === "A") {
          const rx = (op.rx * hexW).toFixed(2);
          const ry = (op.ry * hexW).toFixed(2);
          return `A ${rx} ${ry} 0 0 ${op.sweep} ${px.toFixed(2)} ${py.toFixed(2)}`;
        }
        return `L ${px.toFixed(2)} ${py.toFixed(2)}`;
      })
      .join(" ");
    const pathEl = document.createElementNS(svgNS, "path");
    pathEl.setAttribute("d", d);
    pathEl.setAttribute("fill", "none");
    pathEl.setAttribute("stroke", "var(--accent-primary)");
    pathEl.setAttribute("stroke-width", "3.5");
    pathEl.setAttribute("stroke-linecap", "round");
    pathEl.setAttribute("stroke-linejoin", "round");
    pathEl.style.pointerEvents = "none";
    strokeLayer.appendChild(pathEl);
  } else if (Array.isArray(highlights?.path) && highlights.path.length > 1) {
    const polyline = document.createElementNS(svgNS, "polyline");
    const pts = highlights.path.map(([r, c]) => centerOf(r, c).join(",")).join(" ");
    polyline.setAttribute("points", pts);
    polyline.setAttribute("fill", "none");
    polyline.setAttribute("stroke", "var(--accent-primary)");
    polyline.setAttribute("stroke-width", "3.5");
    polyline.setAttribute("stroke-linecap", "round");
    polyline.setAttribute("stroke-linejoin", "round");
    polyline.style.pointerEvents = "none";
    strokeLayer.appendChild(polyline);
  }

  root.appendChild(svg);
  stage.appendChild(root);
}
