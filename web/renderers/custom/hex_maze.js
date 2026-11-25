import { renderGrid } from "/renderers/grid.js";

const BRUSHES = [
  { val: 0, label: "Empty", color: "#232629" },
  { val: 1, label: "Wall (█)", color: "#621D19" },
  { val: 2, label: "Start (S)", color: "#01CA6B" },
  { val: 3, label: "Goal (G)", color: "#FFE600" },
  { val: 4, label: "2× Mud", color: "#4E4326" },
  { val: 5, label: "4× Swamp", color: "#61324A" },
];

let activeHexBrush = 1;

function hexPoints(cx, cy, radius) {
  const pts = [];
  for (let i = 0; i < 6; i++) {
    const angle = (Math.PI / 180) * (60 * i - 30);
    pts.push(`${(cx + radius * Math.cos(angle)).toFixed(2)},${(cy + radius * Math.sin(angle)).toFixed(2)}`);
  }
  return pts.join(" ");
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
  svg.setAttribute("viewBox", `0 0 ${svgW} ${svgH}`);
  svg.style.cssText = `width:min(100%, ${svgW}px); height:auto; max-height:460px;`;

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const val = board[r][c];
      const [cx, cy] = centerOf(r, c);
      const isHi = hiSet.has(`${r},${c}`);

      const poly = document.createElementNS(svgNS, "polygon");
      poly.setAttribute("points", hexPoints(cx, cy, radius - 1.5));
      poly.setAttribute("fill", colors[String(val)] || "#232629");
      poly.setAttribute("stroke", isHi ? hiColor : "var(--border)");
      poly.setAttribute("stroke-width", isHi ? "3" : "1.5");
      if (editable) {
        poly.style.cursor = "pointer";
        poly.addEventListener("click", () => {
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
      }
      svg.appendChild(poly);

      const lbl = labels[String(val)] ?? "";
      if (lbl) {
        const text = document.createElementNS(svgNS, "text");
        text.setAttribute("x", String(cx));
        text.setAttribute("y", String(cy + 4));
        text.setAttribute("text-anchor", "middle");
        text.setAttribute("font-size", String(Math.max(10, Math.round(radius * 0.48))));
        text.setAttribute("font-weight", "700");
        text.setAttribute("fill", val === 2 || val === 3 ? "#111" : "#EAE6DF");
        text.style.pointerEvents = "none";
        text.textContent = lbl;
        svg.appendChild(text);
      }
    }
  }

  if (Array.isArray(highlights?.path) && highlights.path.length > 1) {
    const polyline = document.createElementNS(svgNS, "polyline");
    const pts = highlights.path.map(([r, c]) => centerOf(r, c).join(",")).join(" ");
    polyline.setAttribute("points", pts);
    polyline.setAttribute("fill", "none");
    polyline.setAttribute("stroke", "var(--accent-primary)");
    polyline.setAttribute("stroke-width", "3.5");
    polyline.setAttribute("stroke-linecap", "round");
    polyline.setAttribute("stroke-linejoin", "round");
    polyline.style.pointerEvents = "none";
    svg.appendChild(polyline);
  }

  root.appendChild(svg);
  stage.appendChild(root);
}
