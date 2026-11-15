const TUBE_COLORS = [
  "#FA8231",
  "#00F5D4",
  "#FF007F",
  "#FFE600",
  "#01CA6B",
  "#B9A7E3",
  "#E76C8F",
  "#3867D6",
  "#FF4D4D",
  "#45AAF2",
  "#A3CB38",
  "#FDA7DF",
  "#20BF6B",
  "#F7B731",
  "#8854D0",
  "#D1D8E0",
];

const COLOR_INITIAL_HINTS = {
  r: "#FF4D4D",
  o: "#FA8231",
  y: "#FFE600",
  g: "#01CA6B",
  c: "#00F5D4",
  b: "#3867D6",
  p: "#B9A7E3",
  m: "#FF007F",
  w: "#EAE6DF",
  k: "#747D8C",
  l: "#A3CB38",
  t: "#20BF6B",
  v: "#8854D0",
};

const ERASER_TOKEN = "__ERASER__";
const MAX_TUBES = 24;
const MAX_CAP = 10;

let activeBrush = 0;
let labelStyle = "123"; // "123" | "ABC" for integer tokens
let cursor = null; // { tubeIdx, slotIdx }
let focusRackAfterRender = false;
let customBrushes = [];

function isBlankSlot(v) {
  return v === null || v === undefined || v === "";
}

function tokenKey(v) {
  return `${typeof v}:${String(v)}`;
}

function displayLabel(val, style = labelStyle) {
  if (typeof val === "number") {
    if (style === "ABC") {
      return val < 26 ? String.fromCharCode(65 + val) : String(val + 1);
    }
    return String(val + 1);
  }
  return String(val);
}

function hslFallback(idx) {
  const hue = (idx * 137.508) % 360;
  return `hsl(${Math.round(hue)}, 75%, 60%)`;
}

function contrastTextColor(bg) {
  if (!bg || !bg.startsWith("#") || bg.length !== 7) return "#111";
  const r = parseInt(bg.slice(1, 3), 16);
  const g = parseInt(bg.slice(3, 5), 16);
  const b = parseInt(bg.slice(5, 7), 16);
  const lum = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return lum < 0.48 ? "#fff" : "#111";
}

function buildColorMap(tokens) {
  const map = new Map();
  const used = new Set();

  // First pass: assign integer tokens deterministically by index
  for (const tok of tokens) {
    if (typeof tok === "number") {
      const color = tok < TUBE_COLORS.length ? TUBE_COLORS[tok] : hslFallback(tok);
      map.set(tokenKey(tok), color);
      used.add(color);
    }
  }

  // Second pass: assign single-letter color hints if unused
  for (const tok of tokens) {
    const key = tokenKey(tok);
    if (map.has(key)) continue;
    if (typeof tok === "string" && tok.length === 1) {
      const hint = COLOR_INITIAL_HINTS[tok.toLowerCase()];
      if (hint && !used.has(hint)) {
        map.set(key, hint);
        used.add(hint);
      }
    }
  }

  // Third pass: assign remaining tokens from palette or HSL fallback
  let nextIdx = 0;
  for (const tok of tokens) {
    const key = tokenKey(tok);
    if (map.has(key)) continue;
    let picked = null;
    while (nextIdx < TUBE_COLORS.length) {
      const cand = TUBE_COLORS[nextIdx++];
      if (!used.has(cand)) {
        picked = cand;
        break;
      }
    }
    if (!picked) {
      picked = hslFallback(nextIdx++);
    }
    map.set(key, picked);
    used.add(picked);
  }
  return map;
}

function trimTrailingNulls(arr) {
  const out = arr.slice();
  while (out.length > 0 && isBlankSlot(out[out.length - 1])) {
    out.pop();
  }
  return out;
}

function setSlotValue(renderState, tubeIdx, slotIdx, val) {
  const next = JSON.parse(JSON.stringify(renderState));
  const tube = Array.isArray(next.tubes[tubeIdx]) ? next.tubes[tubeIdx].slice() : [];
  while (tube.length <= slotIdx) {
    tube.push(null);
  }
  tube[slotIdx] = val;
  next.tubes[tubeIdx] = trimTrailingNulls(tube);
  return next;
}

function serializeNotation(tubes, caps) {
  return tubes
    .map((tube, idx) => {
      const cap = caps[idx] || 4;
      const slots = [];
      for (let s = 0; s < cap; s++) {
        const v = tube[s];
        slots.push(isBlankSlot(v) ? "." : displayLabel(v));
      }
      return slots.join(",");
    })
    .join("/");
}

function parseNotation(text, fallbackCaps) {
  const raw = String(text || "").trim();
  if (!raw) {
    return { error: "Notation is empty." };
  }
  const parts = raw.split(/\/|\r?\n/);
  if (parts.length > 1 && parts[parts.length - 1].trim() === "") {
    parts.pop();
  }
  if (parts.length < 2) {
    return { error: "Provide at least 2 tubes separated by '/' or newlines." };
  }
  if (parts.length > MAX_TUBES) {
    return { error: `Maximum ${MAX_TUBES} tubes supported.` };
  }

  const tubes = [];
  const capacities = [];
  for (let i = 0; i < parts.length; i++) {
    const seg = parts[i].trim();
    if (seg === "" || seg === "-") {
      tubes.push([]);
      capacities.push(fallbackCaps[i] || fallbackCaps[0] || 4);
      continue;
    }
    const items = seg.split(",").map((s) => s.trim());
    if (items.length > MAX_CAP) {
      return { error: `Tube ${i + 1} has ${items.length} slots (max ${MAX_CAP}).` };
    }
    const slots = items.map((tok) => (tok === "." || tok === "_" || tok === "" ? null : tok));
    capacities.push(Math.max(1, slots.length));
    tubes.push(trimTrailingNulls(slots));
  }
  return { tubes, capacities };
}

function canMatchSingleTubes(counts, capacities) {
  const capAvail = new Map();
  for (const c of capacities) {
    capAvail.set(c, (capAvail.get(c) || 0) + 1);
  }
  for (const cnt of counts) {
    const cur = capAvail.get(cnt) || 0;
    if (cur <= 0) return false;
    capAvail.set(cnt, cur - 1);
  }
  return true;
}

function canPartitionCapacities(counts, capacities) {
  const totalTiles = counts.reduce((a, b) => a + b, 0);
  const totalCap = capacities.reduce((a, b) => a + b, 0);
  if (totalTiles === 0 || totalTiles > totalCap) return false;

  const sortedCounts = counts.slice().sort((a, b) => b - a);
  const sortedCaps = capacities.slice().sort((a, b) => b - a);
  const used = new Array(sortedCaps.length).fill(false);
  let steps = 0;
  const MAX_SEARCH_STEPS = 50000;

  function assignColor(colorIdx, remainingSum, startCapIdx) {
    if (++steps > MAX_SEARCH_STEPS) return true; // Safety bail-out on huge boards
    if (remainingSum === 0) {
      if (colorIdx + 1 === sortedCounts.length) return true;
      return assignColor(colorIdx + 1, sortedCounts[colorIdx + 1], 0);
    }
    let prevTried = -1;
    for (let i = startCapIdx; i < sortedCaps.length; i++) {
      if (used[i]) continue;
      const cap = sortedCaps[i];
      if (cap === prevTried || cap > remainingSum) continue;
      prevTried = cap;
      used[i] = true;
      if (assignColor(colorIdx, remainingSum - cap, i + 1)) return true;
      used[i] = false;
    }
    return false;
  }

  return assignColor(0, sortedCounts[0], 0);
}

function validateBoard(tubes, caps, allowSplit) {
  const errors = [];
  const floatingSet = new Set();
  const counts = new Map();
  const labelByKey = new Map();
  let totalTiles = 0;

  if (tubes.length < 2) {
    errors.push("At least 2 tubes are required.");
  }

  const floatingTubes = [];
  const overflowTubes = [];

  for (let i = 0; i < tubes.length; i++) {
    const tube = tubes[i] || [];
    const cap = caps[i] ?? 4;
    if (cap < 1) {
      errors.push(`Tube ${i + 1} capacity must be at least 1.`);
    }

    let seenEmpty = false;
    let tubeHasFloating = false;
    let lastFilledIdx = -1;

    for (let s = 0; s < tube.length; s++) {
      const val = tube[s];
      if (isBlankSlot(val)) {
        seenEmpty = true;
      } else {
        lastFilledIdx = s;
        if (seenEmpty) {
          floatingSet.add(`${i},${s}`);
          tubeHasFloating = true;
        }
        totalTiles += 1;
        const k = tokenKey(val);
        counts.set(k, (counts.get(k) || 0) + 1);
        labelByKey.set(k, displayLabel(val));
      }
    }
    if (tubeHasFloating) floatingTubes.push(i + 1);
    if (lastFilledIdx >= cap) overflowTubes.push(i + 1);
  }

  if (floatingTubes.length > 0) {
    errors.push(`Floating tile(s) above empty slot in Tube ${floatingTubes.join(", ")}.`);
  }
  if (overflowTubes.length > 0) {
    errors.push(`Tube ${overflowTubes.join(", ")} exceeds capacity.`);
  }
  if (totalTiles === 0) {
    errors.push("Board is empty — place some tiles to solve.");
  }

  if (totalTiles > 0 && tubes.length >= 2) {
    const countsArr = Array.from(counts.values());
    if (!allowSplit) {
      if (countsArr.length > tubes.length) {
        errors.push(`${countsArr.length} distinct colors/labels exceed ${tubes.length} tubes (enable Allow Split Colors or add tubes).`);
      } else if (!canMatchSingleTubes(countsArr, caps)) {
        const detail = Array.from(counts.entries())
          .map(([k, cnt]) => `${labelByKey.get(k)}:${cnt}`)
          .join(", ");
        errors.push(`Counts (${detail}) cannot each fill a distinct tube capacity [${caps.join(",")}] completely.`);
      }
    } else if (!canPartitionCapacities(countsArr, caps)) {
      const detail = Array.from(counts.entries())
        .map(([k, cnt]) => `${labelByKey.get(k)}:${cnt}`)
        .join(", ");
      errors.push(`Counts (${detail}) cannot partition into full 1-color or empty tubes [${caps.join(",")}].`);
    }
  }

  return { errors, floatingSet, colorCount: counts.size, totalTiles };
}

function collectBoardTokens(tubes) {
  const seen = new Set();
  const ordered = [];
  for (const t of tubes) {
    for (const v of t || []) {
      if (!isBlankSlot(v)) {
        const k = tokenKey(v);
        if (!seen.has(k)) {
          seen.add(k);
          ordered.push(v);
        }
      }
    }
  }
  return ordered;
}

export function render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed) {
  stage.innerHTML = "";
  const tubes = Array.isArray(renderState?.tubes) ? renderState.tubes : [];
  const caps = Array.isArray(renderState?.capacities)
    ? renderState.capacities.slice(0, tubes.length)
    : tubes.map(() => 4);
  while (caps.length < tubes.length) {
    caps.push(caps[caps.length - 1] || 4);
  }
  const allowSplit = Boolean(renderState?.allow_split_colors);

  const boardTokens = collectBoardTokens(tubes);
  const hasStringTokens = boardTokens.some((t) => typeof t === "string");

  // Build palette list: board tokens + custom brushes + default 0..7 when using numeric tokens (or if board empty)
  const paletteTokens = [];
  const paletteSeen = new Set();
  const pushBrush = (tok) => {
    const k = tokenKey(tok);
    if (!paletteSeen.has(k)) {
      paletteSeen.add(k);
      paletteTokens.push(tok);
    }
  };

  for (const tok of boardTokens) pushBrush(tok);
  for (const tok of customBrushes) pushBrush(tok);
  if (!hasStringTokens) {
    for (let i = 0; i < 8; i++) pushBrush(i);
  } else if (paletteTokens.length === 0) {
    for (let i = 0; i < 8; i++) pushBrush(i);
  }

  // Ensure activeBrush points to something valid
  if (activeBrush !== ERASER_TOKEN && !paletteSeen.has(tokenKey(activeBrush))) {
    activeBrush = paletteTokens[0] ?? 0;
  }

  const colorMap = buildColorMap(paletteTokens);
  const validation = validateBoard(tubes, caps, allowSplit);
  if (typeof setSolveAllowed === "function") {
    if (editable) {
      setSolveAllowed(validation.errors.length === 0, validation.errors[0] || "");
    } else {
      setSolveAllowed(true, "");
    }
  }

  if (cursor) {
    if (cursor.tubeIdx >= tubes.length) {
      cursor = tubes.length > 0 ? { tubeIdx: tubes.length - 1, slotIdx: 0 } : null;
    } else {
      const maxS = Math.max(0, (caps[cursor.tubeIdx] || 1) - 1);
      if (cursor.slotIdx > maxS) cursor.slotIdx = maxS;
    }
  }

  if (editable) {
    // Row 1: Action & Palette Bar
    const bar = document.createElement("div");
    bar.className = "grid-toolbar";

    const btnEmpty = document.createElement("button");
    btnEmpty.type = "button";
    btnEmpty.className = "btn";
    btnEmpty.textContent = "Empty";
    btnEmpty.title = "Clear all tiles while keeping tube count and capacities";
    btnEmpty.disabled = validation.totalTiles === 0;
    btnEmpty.addEventListener("click", () => {
      const next = JSON.parse(JSON.stringify(renderState));
      next.tubes = tubes.map(() => []);
      next.capacities = caps.slice();
      cursor = tubes.length > 0 ? { tubeIdx: 0, slotIdx: 0 } : null;
      onEdit(next);
    });
    bar.appendChild(btnEmpty);

    if (!hasStringTokens) {
      const btnLabels = document.createElement("button");
      btnLabels.type = "button";
      btnLabels.className = "btn";
      btnLabels.textContent = labelStyle === "123" ? "Labels: 123" : "Labels: ABC";
      btnLabels.title = "Toggle numeric (1,2,3) vs letter (A,B,C) display for numeric presets";
      btnLabels.addEventListener("click", () => {
        labelStyle = labelStyle === "123" ? "ABC" : "123";
        render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
      });
      bar.appendChild(btnLabels);
    }

    const pLbl = document.createElement("span");
    pLbl.style.fontSize = "12px";
    pLbl.style.color = "var(--text-muted)";
    pLbl.style.marginLeft = "4px";
    pLbl.textContent = "Brush:";
    bar.appendChild(pLbl);

    const eraserBtn = document.createElement("button");
    eraserBtn.type = "button";
    eraserBtn.className = "btn" + (activeBrush === ERASER_TOKEN ? " btn-solve" : "");
    eraserBtn.style.padding = "3px 8px";
    eraserBtn.style.fontSize = "11px";
    eraserBtn.textContent = "Erase";
    eraserBtn.title = "Eraser (or Right-click any slot)";
    eraserBtn.addEventListener("click", () => {
      activeBrush = ERASER_TOKEN;
      render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
    });
    bar.appendChild(eraserBtn);

    for (const tok of paletteTokens) {
      const bg = colorMap.get(tokenKey(tok)) || "#888";
      const sw = document.createElement("button");
      sw.type = "button";
      const isSelected = activeBrush !== ERASER_TOKEN && tokenKey(activeBrush) === tokenKey(tok);
      sw.className = "palette-swatch" + (isSelected ? " selected" : "");
      sw.style.background = bg;
      sw.style.color = contrastTextColor(bg);
      sw.style.fontSize = "11px";
      sw.style.fontWeight = "700";
      sw.style.width = "auto";
      sw.style.minWidth = "24px";
      sw.style.padding = "0 5px";
      sw.textContent = displayLabel(tok);
      sw.addEventListener("click", () => {
        activeBrush = tok;
        render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
      });
      bar.appendChild(sw);
    }

    // Quick custom brush adder for letters/numbers
    const addTokWrap = document.createElement("form");
    addTokWrap.style.display = "inline-flex";
    addTokWrap.style.alignItems = "center";
    addTokWrap.style.gap = "4px";
    addTokWrap.style.marginLeft = "4px";
    const tokInput = document.createElement("input");
    tokInput.type = "text";
    tokInput.placeholder = "+Tag";
    tokInput.maxLength = 4;
    tokInput.title = "Add a custom letter/number brush (e.g. A, r, 12)";
    tokInput.style.width = "48px";
    tokInput.style.textAlign = "center";
    const tokAddBtn = document.createElement("button");
    tokAddBtn.type = "submit";
    tokAddBtn.className = "btn";
    tokAddBtn.style.padding = "3px 7px";
    tokAddBtn.style.fontSize = "11px";
    tokAddBtn.textContent = "+";
    addTokWrap.appendChild(tokInput);
    addTokWrap.appendChild(tokAddBtn);
    addTokWrap.addEventListener("submit", (e) => {
      e.preventDefault();
      const rawTok = tokInput.value.trim();
      if (!rawTok || rawTok === "." || rawTok === "_" || rawTok === "/") return;
      if (!paletteSeen.has(tokenKey(rawTok))) {
        customBrushes.push(rawTok);
      }
      activeBrush = rawTok;
      render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
    });
    bar.appendChild(addTokWrap);

    stage.appendChild(bar);

    // Row 2: Compact Comma/Period/Slash Notation Panel
    const notePanel = document.createElement("div");
    notePanel.className = "notation-panel";

    const noteRow = document.createElement("div");
    noteRow.className = "notation-row";

    const noteInput = document.createElement("input");
    noteInput.type = "text";
    noteInput.className = "notation-input";
    noteInput.spellcheck = false;
    noteInput.value = serializeNotation(tubes, caps);
    noteInput.placeholder = "p,p,p,./1,1,./p,1,.,.";

    const noteApply = document.createElement("button");
    noteApply.type = "button";
    noteApply.className = "btn btn-solve";
    noteApply.textContent = "Apply";

    const noteErr = document.createElement("div");
    noteErr.className = "notation-hint";
    noteErr.textContent = "Bottom→Top: ',' separates slots · '.' empty slot · '/' separates tubes (e.g. p,p,p,./1,1,./p,1,.,.) · Or click a slot & type.";

    const applyNotationText = () => {
      const parsed = parseNotation(noteInput.value, caps);
      if (parsed.error) {
        noteErr.style.color = "var(--accent-hot)";
        noteErr.textContent = parsed.error;
        return;
      }
      const next = JSON.parse(JSON.stringify(renderState));
      next.tubes = parsed.tubes;
      next.capacities = parsed.capacities;
      const newTokens = collectBoardTokens(parsed.tubes);
      if (newTokens.length > 0) {
        activeBrush = newTokens[0];
      }
      cursor = { tubeIdx: 0, slotIdx: 0 };
      onEdit(next);
    };

    noteApply.addEventListener("click", applyNotationText);
    noteInput.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        applyNotationText();
      }
    });

    noteRow.appendChild(noteInput);
    noteRow.appendChild(noteApply);
    notePanel.appendChild(noteRow);
    notePanel.appendChild(noteErr);
    stage.appendChild(notePanel);
  }

  // Tubes Rack
  const rack = document.createElement("div");
  rack.className = "tubes-rack";
  if (editable) {
    rack.tabIndex = 0;
  }

  const makeInsertBtn = (insertIdx) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "tube-insert-btn";
    btn.textContent = "+";
    btn.title = `Insert tube at position ${insertIdx + 1}`;
    btn.disabled = tubes.length >= MAX_TUBES;
    btn.addEventListener("click", () => {
      if (tubes.length >= MAX_TUBES) return;
      const next = JSON.parse(JSON.stringify(renderState));
      const newCap = caps[insertIdx] ?? caps[insertIdx - 1] ?? 4;
      next.tubes.splice(insertIdx, 0, []);
      next.capacities = caps.slice();
      next.capacities.splice(insertIdx, 0, newCap);
      cursor = { tubeIdx: insertIdx, slotIdx: 0 };
      onEdit(next);
    });
    return btn;
  };

  if (editable) {
    rack.appendChild(makeInsertBtn(0));
  }

  tubes.forEach((tube, idx) => {
    const wrap = document.createElement("div");
    wrap.className = "tube-wrap";
    if (highlights.src === idx) wrap.classList.add("src");
    if (highlights.dst === idx) wrap.classList.add("dst");

    const cap = caps[idx] || 4;

    if (editable) {
      const ctrls = document.createElement("div");
      ctrls.className = "tube-controls";

      const btnDec = document.createElement("button");
      btnDec.type = "button";
      btnDec.className = "tube-ctrl-btn";
      btnDec.textContent = "-";
      btnDec.title = "Decrease tube capacity";
      btnDec.disabled = cap <= 1;
      btnDec.addEventListener("click", () => {
        if (cap <= 1) return;
        const next = JSON.parse(JSON.stringify(renderState));
        const newCap = cap - 1;
        next.capacities = caps.slice();
        next.capacities[idx] = newCap;
        next.tubes[idx] = trimTrailingNulls((next.tubes[idx] || []).slice(0, newCap));
        onEdit(next);
      });

      const btnInc = document.createElement("button");
      btnInc.type = "button";
      btnInc.className = "tube-ctrl-btn";
      btnInc.textContent = "+";
      btnInc.title = "Increase tube capacity";
      btnInc.disabled = cap >= MAX_CAP;
      btnInc.addEventListener("click", () => {
        if (cap >= MAX_CAP) return;
        const next = JSON.parse(JSON.stringify(renderState));
        next.capacities = caps.slice();
        next.capacities[idx] = cap + 1;
        onEdit(next);
      });

      const btnDel = document.createElement("button");
      btnDel.type = "button";
      btnDel.className = "tube-ctrl-btn del";
      btnDel.textContent = "×";
      btnDel.title = "Delete this tube";
      btnDel.disabled = tubes.length <= 2;
      btnDel.addEventListener("click", () => {
        if (tubes.length <= 2) return;
        const next = JSON.parse(JSON.stringify(renderState));
        next.tubes.splice(idx, 1);
        next.capacities = caps.slice();
        next.capacities.splice(idx, 1);
        onEdit(next);
      });

      ctrls.appendChild(btnDec);
      ctrls.appendChild(btnInc);
      ctrls.appendChild(btnDel);
      wrap.appendChild(ctrls);
    }

    const body = document.createElement("div");
    body.className = "tube-body";
    body.style.height = `${cap * 31 + 12}px`;

    let filledCount = 0;
    for (let s = 0; s < cap; s++) {
      const val = tube[s];
      const hasVal = !isBlankSlot(val);
      if (hasVal) filledCount += 1;

      const slotEl = document.createElement("div");
      slotEl.className = "tube-slot";
      if (editable) slotEl.classList.add("editable");
      if (editable && cursor && cursor.tubeIdx === idx && cursor.slotIdx === s) {
        slotEl.classList.add("cursor");
      }

      if (hasVal) {
        const bg = colorMap.get(tokenKey(val)) || "#888";
        slotEl.style.background = bg;
        slotEl.style.color = contrastTextColor(bg);
        slotEl.textContent = displayLabel(val);
        if (validation.floatingSet.has(`${idx},${s}`)) {
          slotEl.classList.add("floating-err");
          slotEl.title = "Floating tile: empty slot underneath";
        }
      } else {
        slotEl.classList.add("empty");
      }

      if (editable) {
        slotEl.addEventListener("click", () => {
          cursor = { tubeIdx: idx, slotIdx: s };
          focusRackAfterRender = true;
          let nextVal;
          if (activeBrush === ERASER_TOKEN) {
            nextVal = null;
          } else if (hasVal && tokenKey(val) === tokenKey(activeBrush)) {
            nextVal = null;
          } else {
            nextVal = activeBrush;
          }
          onEdit(setSlotValue(renderState, idx, s, nextVal));
        });
        slotEl.addEventListener("contextmenu", (e) => {
          e.preventDefault();
          cursor = { tubeIdx: idx, slotIdx: s };
          focusRackAfterRender = true;
          if (!hasVal) return;
          onEdit(setSlotValue(renderState, idx, s, null));
        });
      }

      body.appendChild(slotEl);
    }

    const lbl = document.createElement("div");
    lbl.style.fontSize = "11px";
    lbl.style.color = "var(--text-muted)";
    lbl.textContent = `#${idx + 1} (${filledCount}/${cap})`;

    wrap.appendChild(body);
    wrap.appendChild(lbl);
    rack.appendChild(wrap);

    if (editable) {
      rack.appendChild(makeInsertBtn(idx + 1));
    }
  });

  if (editable) {
    rack.addEventListener("keydown", (e) => {
      if (e.target && e.target !== rack && e.target.closest("input, textarea, select")) {
        return;
      }
      if (!cursor) {
        cursor = { tubeIdx: 0, slotIdx: 0 };
      }
      const { tubeIdx, slotIdx } = cursor;
      const cap = caps[tubeIdx] || 4;

      if (e.key === "ArrowUp") {
        e.preventDefault();
        cursor = { tubeIdx, slotIdx: Math.min(cap - 1, slotIdx + 1) };
        focusRackAfterRender = true;
        render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        cursor = { tubeIdx, slotIdx: Math.max(0, slotIdx - 1) };
        focusRackAfterRender = true;
        render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
      } else if (e.key === "ArrowRight" || (e.key === "Tab" && !e.shiftKey)) {
        e.preventDefault();
        const nextTube = (tubeIdx + 1) % tubes.length;
        const nextCap = caps[nextTube] || 4;
        cursor = {
          tubeIdx: nextTube,
          slotIdx: e.key === "Tab" ? 0 : Math.min(slotIdx, nextCap - 1),
        };
        focusRackAfterRender = true;
        render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
      } else if (e.key === "ArrowLeft" || (e.key === "Tab" && e.shiftKey)) {
        e.preventDefault();
        const prevTube = (tubeIdx - 1 + tubes.length) % tubes.length;
        const prevCap = caps[prevTube] || 4;
        cursor = {
          tubeIdx: prevTube,
          slotIdx: e.key === "Tab" ? 0 : Math.min(slotIdx, prevCap - 1),
        };
        focusRackAfterRender = true;
        render(stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
      } else if (e.key === "Backspace") {
        e.preventDefault();
        cursor = { tubeIdx, slotIdx: Math.max(0, slotIdx - 1) };
        focusRackAfterRender = true;
        onEdit(setSlotValue(renderState, tubeIdx, slotIdx, null));
      } else if (e.key === "Delete" || e.key === " " || e.key === "." || e.key === "_") {
        e.preventDefault();
        if (e.key !== "Delete") {
          if (slotIdx + 1 < cap) {
            cursor = { tubeIdx, slotIdx: slotIdx + 1 };
          } else if (tubeIdx + 1 < tubes.length) {
            cursor = { tubeIdx: tubeIdx + 1, slotIdx: 0 };
          }
        }
        focusRackAfterRender = true;
        onEdit(setSlotValue(renderState, tubeIdx, slotIdx, null));
      } else if (/^[a-zA-Z0-9]$/.test(e.key) && !e.ctrlKey && !e.metaKey && !e.altKey) {
        e.preventDefault();
        let val;
        if (!hasStringTokens && /^[1-9]$/.test(e.key)) {
          val = Number(e.key) - 1;
        } else {
          val = e.key;
          if (!paletteSeen.has(tokenKey(val))) {
            customBrushes.push(val);
          }
        }
        activeBrush = val;
        if (slotIdx + 1 < cap) {
          cursor = { tubeIdx, slotIdx: slotIdx + 1 };
        } else if (tubeIdx + 1 < tubes.length) {
          cursor = { tubeIdx: tubeIdx + 1, slotIdx: 0 };
        }
        focusRackAfterRender = true;
        onEdit(setSlotValue(renderState, tubeIdx, slotIdx, val));
      }
    });
  }

  stage.appendChild(rack);

  if (editable) {
    const banner = document.createElement("div");
    if (validation.errors.length > 0) {
      banner.className = "validation-banner error";
      banner.textContent = validation.errors.join(" · ");
    } else {
      banner.className = "validation-banner ok";
      banner.textContent = `Valid board: ${tubes.length} tubes · ${validation.colorCount} colors · ${validation.totalTiles} tiles`;
    }
    stage.appendChild(banner);

    if (focusRackAfterRender) {
      focusRackAfterRender = false;
      rack.focus({ preventScroll: true });
    }
  }
}
