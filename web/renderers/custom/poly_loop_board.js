const SQRT3 = Math.sqrt(3);

function buildTilingJS(tiling, rows, cols) {
  const rCount = Math.max(1, Math.min(8, Number(rows) || 3));
  const cCount = Math.max(1, Math.min(8, Number(cols) || 3));
  const vertMap = new Map();
  const vertices = [];
  const edgeMap = new Map();
  const edges = [];
  const faceSigs = new Set();
  const faces = [];

  const getVid = (x, y) => {
    const key = `${Math.round(x * 10000)},${Math.round(y * 10000)}`;
    if (vertMap.has(key)) return vertMap.get(key);
    const id = vertices.length;
    vertMap.set(key, id);
    vertices.push([Math.round(x * 100000) / 100000, Math.round(y * 100000) / 100000]);
    return id;
  };

  const getEid = (u, v) => {
    const a = Math.min(u, v);
    const b = Math.max(u, v);
    const key = `${a},${b}`;
    if (edgeMap.has(key)) return edgeMap.get(key);
    const id = edges.length;
    edgeMap.set(key, id);
    edges.push([a, b]);
    return id;
  };

  const addPoly = (pts) => {
    const vids = pts.map(([px, py]) => getVid(px, py));
    const sig = [...vids].sort((a, b) => a - b).join(",");
    if (faceSigs.has(sig)) return;
    faceSigs.add(sig);
    const eids = vids.map((u, i) => getEid(u, vids[(i + 1) % vids.length]));
    faces.push({ verts: vids, edges: eids, clue: null });
  };

  if (tiling === "hex") {
    for (let r = 0; r < rCount; r++) {
      for (let c = 0; c < cCount; c++) {
        const cx = 1.5 * c;
        const cy = SQRT3 * (r + 0.5 * (c % 2));
        const pts = [];
        for (let k = 0; k < 6; k++) {
          const rad = ((60 * k) * Math.PI) / 180;
          pts.push([cx + Math.cos(rad), cy + Math.sin(rad)]);
        }
        addPoly(pts);
      }
    }
  } else if (tiling === "square") {
    for (let r = 0; r < rCount; r++) {
      for (let c = 0; c < cCount; c++) {
        addPoly([[c, r], [c + 1, r], [c + 1, r + 1], [c, r + 1]]);
      }
    }
  } else if (tiling === "tri") {
    const hTri = SQRT3 / 2;
    for (let r = 0; r < rCount; r++) {
      for (let c = 0; c < cCount; c++) {
        const x0 = 0.5 * c;
        const x1 = x0 + 0.5;
        const x2 = x0 + 1.0;
        const yTop = r * hTri;
        const yBot = (r + 1) * hTri;
        if ((r + c) % 2 === 0) {
          addPoly([[x0, yBot], [x2, yBot], [x1, yTop]]);
        } else {
          addPoly([[x0, yTop], [x2, yTop], [x1, yBot]]);
        }
      }
    }
  } else {
    const D = SQRT3 + 1;
    const hexMap = new Map();
    for (let r = 0; r < rCount; r++) {
      for (let c = 0; c < cCount; c++) {
        const cx = D * (SQRT3 / 2) * c;
        const cy = D * (r + 0.5 * (c % 2));
        const hPts = [];
        for (let k = 0; k < 6; k++) {
          const rad = ((60 * k) * Math.PI) / 180;
          hPts.push([cx + Math.cos(rad), cy + Math.sin(rad)]);
        }
        hexMap.set(`${Math.round(cx * 1000)},${Math.round(cy * 1000)}`, { cx, cy, hPts });
        addPoly(hPts);
      }
    }
    for (const { cx, cy, hPts } of hexMap.values()) {
      for (let k = 0; k < 6; k++) {
        const ang = ((30 + 60 * k) * Math.PI) / 180;
        const nx = Math.cos(ang);
        const ny = Math.sin(ang);
        const nbKey = `${Math.round((cx + D * nx) * 1000)},${Math.round((cy + D * ny) * 1000)}`;
        if (hexMap.has(nbKey)) {
          const p1 = hPts[k];
          const p2 = hPts[(k + 1) % 6];
          addPoly([p1, p2, [p2[0] + nx, p2[1] + ny], [p1[0] + nx, p1[1] + ny]]);
        }
      }
      for (let k = 0; k < 6; k++) {
        const a1 = ((60 * k - 30) * Math.PI) / 180;
        const a2 = ((60 * k + 30) * Math.PI) / 180;
        const k1 = `${Math.round((cx + D * Math.cos(a1)) * 1000)},${Math.round((cy + D * Math.sin(a1)) * 1000)}`;
        const k2 = `${Math.round((cx + D * Math.cos(a2)) * 1000)},${Math.round((cy + D * Math.sin(a2)) * 1000)}`;
        if (hexMap.has(k1) && hexMap.has(k2)) {
          const p0 = hPts[k];
          addPoly([p0, [p0[0] + Math.cos(a1), p0[1] + Math.sin(a1)], [p0[0] + Math.cos(a2), p0[1] + Math.sin(a2)]]);
        }
      }
    }
  }

  if (vertices.length > 0) {
    const xs = vertices.map((p) => p[0]);
    const ys = vertices.map((p) => p[1]);
    const mx = (Math.min(...xs) + Math.max(...xs)) / 2;
    const my = (Math.min(...ys) + Math.max(...ys)) / 2;
    for (const p of vertices) {
      p[0] = Math.round((p[0] - mx) * 100000) / 100000;
      p[1] = Math.round((p[1] - my) * 100000) / 100000;
    }
  }

  return {
    tiling,
    rows: rCount,
    cols: cCount,
    vertices,
    edges,
    faces,
    edge_values: Array(edges.length).fill(0),
  };
}

export function render(stage, solver, renderState, highlights, editable, onEdit) {
  stage.innerHTML = "";
  const tiling = renderState?.tiling || "hex";
  const rows = renderState?.rows || 3;
  const cols = renderState?.cols || 3;
  const vertices = renderState?.vertices || [];
  const edges = renderState?.edges || [];
  const faces = renderState?.faces || [];
  const edgeValues = renderState?.edge_values || [];

  if (editable) {
    const bar = document.createElement("div");
    bar.className = "grid-toolbar";

    const tWrap = document.createElement("label");
    tWrap.style.display = "inline-flex";
    tWrap.style.alignItems = "center";
    tWrap.style.gap = "5px";
    tWrap.style.fontSize = "12px";
    tWrap.style.color = "var(--text-muted)";
    tWrap.textContent = "Tiling";
    const tSel = document.createElement("select");
    for (const [val, lbl] of [
      ["square", "Square"],
      ["hex", "Hexagonal"],
      ["tri", "Triangular"],
      ["3464", "3-4-6-4 (Great Honeycomb)"],
    ]) {
      const o = document.createElement("option");
      o.value = val;
      o.textContent = lbl;
      if (val === tiling) o.selected = true;
      tSel.appendChild(o);
    }
    tSel.addEventListener("change", () => onEdit(buildTilingJS(tSel.value, rows, cols)));
    tWrap.appendChild(tSel);
    bar.appendChild(tWrap);

    const makeNum = (labelText, curVal, onPick) => {
      const wrap = document.createElement("label");
      wrap.style.display = "inline-flex";
      wrap.style.alignItems = "center";
      wrap.style.gap = "5px";
      wrap.style.fontSize = "12px";
      wrap.style.color = "var(--text-muted)";
      wrap.textContent = labelText;
      const sel = document.createElement("select");
      for (let d = 1; d <= 8; d++) {
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

    bar.appendChild(makeNum("Rows", rows, (nr) => onEdit(buildTilingJS(tiling, nr, cols))));
    bar.appendChild(makeNum("Cols", cols, (nc) => onEdit(buildTilingJS(tiling, rows, nc))));

    stage.appendChild(bar);
  }

  if (!vertices.length || !faces.length) return;

  const xs = vertices.map((p) => p[0]);
  const ys = vertices.map((p) => p[1]);
  const minX = Math.min(...xs);
  const maxX = Math.max(...xs);
  const minY = Math.min(...ys);
  const maxY = Math.max(...ys);
  const span = Math.max(maxX - minX, maxY - minY, 1);
  const targetPx = 420;
  const scale = targetPx / span;
  const pad = 28;
  const width = Math.round((maxX - minX) * scale + pad * 2);
  const height = Math.round((maxY - minY) * scale + pad * 2);

  const toPx = ([vx, vy]) => [
    pad + (vx - minX) * scale,
    pad + (vy - minY) * scale,
  ];

  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("class", "puzzle-svg-board");
  svg.setAttribute("width", String(width));
  svg.setAttribute("height", String(height));
  svg.style.userSelect = "none";

  const strokeLayer = document.createElementNS(ns, "g");
  strokeLayer.setAttribute("class", "theme-stroke-layer");
  const textLayer = document.createElementNS(ns, "g");
  textLayer.setAttribute("class", "theme-text-layer");
  const hitLayer = document.createElementNS(ns, "g");
  hitLayer.setAttribute("class", "theme-hit-layer");
  svg.append(strokeLayer, textLayer, hitLayer);

  const hlSet = new Set(
    Array.isArray(highlights?.edge_indices)
      ? highlights.edge_indices
      : highlights?.edge_idx !== undefined
        ? [highlights.edge_idx]
        : [],
  );

  // 1. Faces (polygons + clue labels)
  faces.forEach((f, fi) => {
    const pts = f.verts.map((vid) => toPx(vertices[vid]));
    const cx = pts.reduce((a, p) => a + p[0], 0) / pts.length;
    const cy = pts.reduce((a, p) => a + p[1], 0) / pts.length;

    const poly = document.createElementNS(ns, "polygon");
    poly.setAttribute("points", pts.map((p) => `${p[0].toFixed(1)},${p[1].toFixed(1)}`).join(" "));
    poly.setAttribute("fill", "transparent");
    if (editable) {
      poly.style.cursor = "pointer";
      const cycleClue = (delta) => {
        const maxClue = Math.max(0, f.edges.length - 1);
        const cur = f.clue;
        let nextVal;
        if (delta > 0) {
          nextVal = cur === null || cur === undefined ? 0 : cur >= maxClue ? null : cur + 1;
        } else {
          nextVal = cur === null || cur === undefined ? maxClue : cur <= 0 ? null : cur - 1;
        }
        const next = JSON.parse(JSON.stringify(renderState));
        next.faces[fi].clue = nextVal;
        onEdit(next);
      };
      poly.addEventListener("click", () => cycleClue(1));
      poly.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        cycleClue(-1);
      });
    }
    hitLayer.appendChild(poly);

    if (f.clue !== null && f.clue !== undefined) {
      const txt = document.createElementNS(ns, "text");
      txt.setAttribute("x", cx.toFixed(1));
      txt.setAttribute("y", (cy + 5).toFixed(1));
      txt.setAttribute("text-anchor", "middle");
      txt.setAttribute("fill", "var(--text-main)");
      txt.setAttribute("font-size", String(Math.max(11, Math.min(18, Math.round(scale * 0.34)))));
      txt.setAttribute("font-weight", "700");
      txt.setAttribute("font-family", "var(--font-mono)");
      txt.style.pointerEvents = "none";
      txt.textContent = String(f.clue);
      textLayer.appendChild(txt);
    }
  });

  // 2. Edges
  edges.forEach(([u, v], ei) => {
    const [x1, y1] = toPx(vertices[u]);
    const [x2, y2] = toPx(vertices[v]);
    const val = edgeValues[ei] || 0;
    const isHl = hlSet.has(ei);

    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", x1.toFixed(1));
    line.setAttribute("y1", y1.toFixed(1));
    line.setAttribute("x2", x2.toFixed(1));
    line.setAttribute("y2", y2.toFixed(1));
    if (val === 1) {
      line.setAttribute("stroke", isHl ? "var(--accent-hot)" : "var(--accent-primary)");
      line.setAttribute("stroke-width", "4");
      line.setAttribute("stroke-linecap", "round");
    } else if (val === -1) {
      line.setAttribute("stroke", isHl ? "var(--accent-hot)" : "var(--text-muted)");
      line.setAttribute("stroke-width", isHl ? "2.6" : "1.4");
      line.setAttribute("stroke-dasharray", "3 4");
      line.setAttribute("opacity", isHl ? "0.9" : "0.45");
    } else {
      line.setAttribute("stroke", isHl ? "var(--accent-hot)" : "var(--border)");
      line.setAttribute("stroke-width", isHl ? "3" : "1.8");
      line.setAttribute("opacity", "0.75");
    }
    strokeLayer.appendChild(line);

    if (editable) {
      const hit = document.createElementNS(ns, "line");
      hit.setAttribute("x1", x1.toFixed(1));
      hit.setAttribute("y1", y1.toFixed(1));
      hit.setAttribute("x2", x2.toFixed(1));
      hit.setAttribute("y2", y2.toFixed(1));
      hit.setAttribute("stroke", "transparent");
      hit.setAttribute("stroke-width", "12");
      hit.style.cursor = "pointer";
      hit.addEventListener("click", () => {
        const next = JSON.parse(JSON.stringify(renderState));
        next.edge_values[ei] = val === 0 ? 1 : val === 1 ? -1 : 0;
        onEdit(next);
      });
      hit.addEventListener("contextmenu", (ev) => {
        ev.preventDefault();
        const next = JSON.parse(JSON.stringify(renderState));
        next.edge_values[ei] = val === -1 ? 0 : -1;
        onEdit(next);
      });
      hitLayer.appendChild(hit);
    }
  });

  // 3. Vertex dots
  for (const pt of vertices) {
    const [cx, cy] = toPx(pt);
    const dot = document.createElementNS(ns, "circle");
    dot.setAttribute("cx", cx.toFixed(1));
    dot.setAttribute("cy", cy.toFixed(1));
    dot.setAttribute("r", "2.6");
    dot.setAttribute("fill", "var(--text-muted)");
    dot.style.pointerEvents = "none";
    strokeLayer.appendChild(dot);
  }

  stage.appendChild(svg);
}
