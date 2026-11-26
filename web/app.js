import { renderGrid } from "/renderers/grid.js";
import { renderText } from "/renderers/text.js";

const state = {
  solvers: [],
  activeSolver: null,
  activePresetName: "",
  editState: null,
  params: {},
  steps: [],
  stepIdx: 0,
  playing: false,
  playTimer: null,
  activeJobId: null,
  abortController: null,
  customRendererCache: new Map(),
};

const els = {
  solverFilter: document.getElementById("solver-filter"),
  solverList: document.getElementById("solver-list"),
  solverTitle: document.getElementById("solver-title"),
  presetSelect: document.getElementById("preset-select"),
  dynamicParams: document.getElementById("dynamic-params"),
  stage: document.getElementById("stage"),
  modePill: document.getElementById("mode-pill"),
  scrubTrack: document.getElementById("scrub-track"),
  scrubSlider: document.getElementById("scrub-slider"),
  stepCounter: document.getElementById("step-counter"),
  speedSlider: document.getElementById("speed-slider"),
  btnFirst: document.getElementById("btn-first"),
  btnPrev: document.getElementById("btn-prev"),
  btnPlay: document.getElementById("btn-play"),
  btnNext: document.getElementById("btn-next"),
  btnLast: document.getElementById("btn-last"),
  btnSolve: document.getElementById("btn-solve"),
  btnAbort: document.getElementById("btn-abort"),
  btnClear: document.getElementById("btn-clear"),
  btnReset: document.getElementById("btn-reset"),
  btnTheme: document.getElementById("btn-theme"),
  btnLogs: document.getElementById("btn-logs"),
  logDrawer: document.getElementById("log-drawer"),
  logEntries: document.getElementById("log-entries"),
  stepDescLive: document.getElementById("step-desc-live"),
  stepStatsLive: document.getElementById("step-stats-live"),
  btnJson: document.getElementById("btn-json"),
  jsonModal: document.getElementById("json-modal"),
  jsonTextarea: document.getElementById("json-textarea"),
  btnJsonApply: document.getElementById("btn-json-apply"),
  btnJsonClose: document.getElementById("btn-json-close"),
};

function deepClone(obj) {
  return JSON.parse(JSON.stringify(obj));
}

const DRAFT_PREFIX = "tpl_draft_";
const ACTIVE_SOLVER_KEY = "tpl_active_solver";

function saveDraft() {
  if (!state.activeSolver || !state.editState) return;
  try {
    localStorage.setItem(
      DRAFT_PREFIX + state.activeSolver.slug,
      JSON.stringify({
        activePresetName: state.activePresetName,
        editState: state.editState,
        params: state.params,
      })
    );
  } catch {
    // Ignore storage quota errors
  }
}

function loadDraft(slug) {
  try {
    const raw = localStorage.getItem(DRAFT_PREFIX + slug);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

function clearDraft(slug) {
  try {
    localStorage.removeItem(DRAFT_PREFIX + slug);
  } catch {
    // Ignore
  }
}

function isPlaybackMode() {
  return state.steps.length > 0;
}

function stopPlayback() {
  state.playing = false;
  if (state.playTimer) {
    clearTimeout(state.playTimer);
    state.playTimer = null;
  }
  els.btnPlay.textContent = "Play";
}

function clearPlayback() {
  stopPlayback();
  state.steps = [];
  state.stepIdx = 0;
  updateTransport();
}

function stepTypeColor(type) {
  if (type === "backtrack" || type === "failed") return "var(--accent-hot)";
  if (type === "explore") return "var(--accent-secondary)";
  if (type === "solution") return "var(--accent-warm)";
  if (type === "deduce") return "var(--accent-primary)";
  return "var(--border)";
}

function updateScrubTrack() {
  const total = state.steps.length;
  if (total <= 1) {
    els.scrubTrack.style.background = "";
    return;
  }
  const stops = [];
  let startIdx = 0;
  let curColor = stepTypeColor(state.steps[0].type);
  for (let i = 1; i <= total; i++) {
    const nextColor = i < total ? stepTypeColor(state.steps[i].type) : null;
    if (nextColor !== curColor) {
      const p0 = ((startIdx / total) * 100).toFixed(2);
      const p1 = ((i / total) * 100).toFixed(2);
      stops.push(`${curColor} ${p0}%`, `${curColor} ${p1}%`);
      startIdx = i;
      curColor = nextColor;
    }
  }
  els.scrubTrack.style.background = `linear-gradient(to right, ${stops.join(", ")})`;
}

function updateTransport() {
  const total = state.steps.length;
  els.scrubSlider.max = Math.max(0, total - 1);
  els.scrubSlider.value = total ? state.stepIdx : 0;
  els.scrubSlider.disabled = total <= 1;
  els.stepCounter.textContent = total ? `${state.stepIdx + 1} / ${total}` : "0 / 0";
  updateScrubTrack();

  const hasSteps = total > 0;
  els.btnFirst.disabled = !hasSteps || state.stepIdx === 0;
  els.btnPrev.disabled = !hasSteps || state.stepIdx === 0;
  els.btnNext.disabled = !hasSteps || state.stepIdx >= total - 1;
  els.btnLast.disabled = !hasSteps || state.stepIdx >= total - 1;
  els.btnPlay.disabled = total <= 1;

  if (hasSteps) {
    els.modePill.textContent = "PLAYBACK · Edit";
    els.modePill.className = "mode-tag playback";
    els.modePill.style.cursor = "pointer";
    els.modePill.title = "Click to exit playback and edit your board";
    const step = state.steps[state.stepIdx];
    els.stepDescLive.textContent = step.desc || "";
    const statsEntries = Object.entries(step.stats || {});
    els.stepStatsLive.innerHTML = statsEntries
      .map(([k, v]) => `<span>${k}: <b>${v}</b></span>`)
      .join(" ");
  } else {
    els.modePill.textContent = "EDIT";
    els.modePill.className = "mode-tag edit";
    els.modePill.style.cursor = "default";
    els.modePill.title = "";
    els.stepDescLive.textContent = "Ready. Edit the puzzle or click Solve.";
    els.stepStatsLive.innerHTML = "";
  }
}

function appendLog(text, type = "info") {
  const line = document.createElement("div");
  line.className = `log-line ${type}`;
  line.textContent = text;
  els.logEntries.appendChild(line);
  els.logEntries.scrollTop = els.logEntries.scrollHeight;
}

async function renderStage() {
  if (!state.activeSolver) return;
  const solver = state.activeSolver;
  const currentStep = isPlaybackMode() ? state.steps[state.stepIdx] : null;
  const renderState = currentStep ? currentStep.state : state.editState;
  const highlights = currentStep ? currentStep.highlights || {} : {};
  const editable = !isPlaybackMode();

  const onEdit = (newState) => {
    clearPlayback();
    state.editState = newState;
    saveDraft();
    renderStage();
  };

  const setSolveAllowed = (valid, reason = "") => {
    if (!editable) {
      els.btnSolve.disabled = false;
      els.btnSolve.title = "";
      return;
    }
    els.btnSolve.disabled = !valid;
    els.btnSolve.title = valid ? "" : reason;
  };

  // Default to enabled before renderer runs; custom renderers can restrict via setSolveAllowed.
  els.btnSolve.disabled = false;
  els.btnSolve.title = "";

  if (solver.renderer === "text") {
    renderText(els.stage, solver, renderState, editable, onEdit);
  } else if (solver.renderer === "custom" && solver.custom_view) {
    let mod = state.customRendererCache.get(solver.custom_view);
    if (!mod) {
      mod = await import(solver.custom_view);
      state.customRendererCache.set(solver.custom_view, mod);
    }
    mod.render(els.stage, solver, renderState, highlights, editable, onEdit, setSolveAllowed);
  } else {
    renderGrid(els.stage, solver, renderState, highlights, editable, onEdit);
  }
  updateTransport();
}

function renderSidebar(filterText = "") {
  const q = filterText.trim().toLowerCase();
  const grouped = new Map();
  for (const s of state.solvers) {
    if (q && !s.name.toLowerCase().includes(q) && !s.category.toLowerCase().includes(q)) {
      continue;
    }
    if (!grouped.has(s.category)) grouped.set(s.category, []);
    grouped.get(s.category).push(s);
  }

  els.solverList.innerHTML = "";
  for (const [cat, items] of grouped.entries()) {
    const label = document.createElement("div");
    label.className = "category-label";
    label.textContent = cat;
    els.solverList.appendChild(label);

    for (const s of items) {
      const btn = document.createElement("button");
      btn.className = "solver-item" + (state.activeSolver?.slug === s.slug ? " active" : "");
      btn.innerHTML = `<span>${s.name}</span><span class="solver-tag">${s.renderer}</span>`;
      btn.addEventListener("click", () => selectSolver(s.slug));
      els.solverList.appendChild(btn);
    }
  }
}

function extractPresetParams(solver, presetState) {
  if (!presetState) return null;
  const out = {};
  for (const p of solver.params || []) {
    if (p.key in presetState) {
      out[p.key] = presetState[p.key];
    }
  }
  return Object.keys(out).length > 0 ? out : null;
}

function renderParams(solver, savedParams = null) {
  els.dynamicParams.innerHTML = "";
  state.params = {};

  for (const p of solver.params || []) {
    if (p.type === "textarea") continue; // Handled inside JSON/custom or preset
    const initVal = savedParams && p.key in savedParams ? savedParams[p.key] : p.default;
    state.params[p.key] = initVal;
    const wrap = document.createElement("label");
    wrap.textContent = p.label + " ";

    if (p.type === "select") {
      const sel = document.createElement("select");
      for (const opt of p.options || []) {
        const o = document.createElement("option");
        o.value = opt;
        o.textContent = opt;
        if (opt === initVal) o.selected = true;
        sel.appendChild(o);
      }
      sel.addEventListener("change", () => {
        state.params[p.key] = sel.value;
        if (state.editState && typeof state.editState === "object") {
          state.editState[p.key] = sel.value;
          if (p.key === "maze_type") {
            const b = state.editState.board;
            const rows = Array.isArray(b) ? b.length : 0;
            const cols = rows > 0 && Array.isArray(b[0]) ? b[0].length : 0;
            if (sel.value === "Edge Walls" && rows > 0 && cols > 0) {
              if (!Array.isArray(state.editState.h_walls)) {
                state.editState.h_walls = Array.from({ length: rows + 1 }, () => Array(cols).fill(0));
              }
              if (!Array.isArray(state.editState.v_walls)) {
                state.editState.v_walls = Array.from({ length: rows }, () => Array(cols + 1).fill(0));
              }
            } else if (sel.value === "Tile Walls") {
              delete state.editState.h_walls;
              delete state.editState.v_walls;
            }
            if (!isPlaybackMode()) renderStage();
          } else if (p.key === "geometry") {
            const movWrap = els.dynamicParams.querySelector('[data-param-key="movement"]');
            if (movWrap) {
              movWrap.style.display = sel.value === "Hexagonal (6-Way)" ? "none" : "";
            }
            if (!isPlaybackMode()) renderStage();
          } else if (p.key === "num_colors" && !isPlaybackMode()) {
            renderStage();
          }
        }
        saveDraft();
      });
      wrap.appendChild(sel);
      wrap.dataset.paramKey = p.key;
      if (solver.slug === "maze_navigator" && p.key === "movement" && state.params.geometry === "Hexagonal (6-Way)") {
        wrap.style.display = "none";
      }
    } else if (p.type === "bool") {
      const cb = document.createElement("input");
      cb.type = "checkbox";
      cb.checked = Boolean(initVal);
      cb.addEventListener("change", () => {
        state.params[p.key] = cb.checked;
        if (state.editState && typeof state.editState === "object") {
          state.editState[p.key] = cb.checked;
        }
        saveDraft();
        if (!isPlaybackMode()) renderStage();
      });
      wrap.appendChild(cb);
    } else {
      const inp = document.createElement("input");
      inp.type = "text";
      inp.value = initVal ?? "";
      inp.style.width = "100px";
      inp.addEventListener("input", () => {
        state.params[p.key] = inp.value;
        saveDraft();
      });
      wrap.appendChild(inp);
    }
    els.dynamicParams.appendChild(wrap);
  }
}

function selectSolver(slug) {
  const solver = state.solvers.find((s) => s.slug === slug);
  if (!solver) return;

  if (state.activeSolver) {
    saveDraft();
  }

  if (state.abortController) {
    state.abortController.abort();
  }
  clearPlayback();
  els.logEntries.innerHTML = "";

  state.activeSolver = solver;
  try {
    localStorage.setItem(ACTIVE_SOLVER_KEY, slug);
  } catch {
    // Ignore
  }
  els.solverTitle.textContent = solver.name;
  els.solverTitle.title = solver.description || "";

  const presetNames = Object.keys(solver.presets || {});
  els.presetSelect.innerHTML = "";
  for (const name of presetNames) {
    const o = document.createElement("option");
    o.value = name;
    o.textContent = name;
    els.presetSelect.appendChild(o);
  }

  const draft = loadDraft(slug);
  if (draft && draft.editState) {
    state.activePresetName = draft.activePresetName && presetNames.includes(draft.activePresetName)
      ? draft.activePresetName
      : (presetNames[0] || "");
    els.presetSelect.value = state.activePresetName;
    state.editState = draft.editState;
    renderParams(solver, draft.params || null);
  } else {
    state.activePresetName = presetNames[0] || "";
    state.editState = state.activePresetName ? deepClone(solver.presets[state.activePresetName]) : {};
    renderParams(solver, extractPresetParams(solver, state.editState));
  }
  renderSidebar(els.solverFilter.value);
  renderStage();
}

async function runSolve() {
  if (!state.activeSolver || els.btnSolve.disabled) return;
  clearPlayback();
  els.logEntries.innerHTML = "";
  els.btnSolve.classList.add("hidden");
  els.btnAbort.classList.remove("hidden");

  const controller = new AbortController();
  state.abortController = controller;

  try {
    const resp = await fetch(`/api/solve/${state.activeSolver.slug}/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ state: state.editState, params: state.params }),
      signal: controller.signal,
    });

    const reader = resp.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() || "";

      for (const block of blocks) {
        let evName = "message";
        let dataStr = "";
        for (const line of block.split("\n")) {
          if (line.startsWith("event: ")) evName = line.slice(7).trim();
          else if (line.startsWith("data: ")) dataStr += line.slice(6);
        }
        if (!dataStr) continue;
        const payload = JSON.parse(dataStr);

        if (evName === "job") {
          state.activeJobId = payload.job_id;
        } else if (evName === "step") {
          state.steps.push(payload);
          appendLog(`[${payload.type.toUpperCase()}] ${payload.desc}`, payload.type);
        } else if (evName === "error") {
          appendLog(`[ERROR] ${payload.error}`, "failed");
        } else if (evName === "done") {
          appendLog(`Finished in ${payload.elapsed_ms} ms (${payload.steps} steps).`, "solution");
        }
      }
    }

    if (state.steps.length > 0) {
      // Jump to final state for instant solve, or let user scrub from 0!
      state.stepIdx = state.steps.length - 1;
      await renderStage();
    }
  } catch (err) {
    if (err.name !== "AbortError") {
      appendLog(`Request failed: ${err.message}`, "failed");
    }
  } finally {
    state.activeJobId = null;
    state.abortController = null;
    els.btnAbort.classList.add("hidden");
    els.btnSolve.classList.remove("hidden");
  }
}

function scheduleNextFrame() {
  if (!state.playing) return;
  if (state.stepIdx >= state.steps.length - 1) {
    stopPlayback();
    return;
  }
  const delay = Math.max(30, 830 - Number(els.speedSlider.value));
  state.playTimer = setTimeout(async () => {
    state.stepIdx += 1;
    await renderStage();
    scheduleNextFrame();
  }, delay);
}

// Event bindings
els.solverFilter.addEventListener("input", () => renderSidebar(els.solverFilter.value));

els.presetSelect.addEventListener("change", () => {
  if (!state.activeSolver) return;
  clearPlayback();
  state.activePresetName = els.presetSelect.value;
  state.editState = deepClone(state.activeSolver.presets[state.activePresetName] || {});
  renderParams(state.activeSolver, extractPresetParams(state.activeSolver, state.editState));
  saveDraft();
  renderStage();
});

function clearBoardState(solver, curState) {
  const next = deepClone(curState || {});
  const gm = solver?.grid_meta || {};
  const emptyVal = gm.empty_val ?? 0;

  if (Array.isArray(next.board)) {
    next.board = next.board.map((row) =>
      Array.isArray(row) ? row.map((v) => (typeof v === "string" ? "" : emptyVal)) : row
    );
  }
  if (Array.isArray(next.clues)) {
    next.clues = next.clues.map((row) => row.map(() => null));
  }
  if (Array.isArray(next.cell_clues)) {
    next.cell_clues = next.cell_clues.map((row) => row.map(() => null));
  }
  if (Array.isArray(next.h_edges)) {
    next.h_edges = next.h_edges.map((row) => row.map(() => 0));
  }
  if (Array.isArray(next.v_edges)) {
    next.v_edges = next.v_edges.map((row) => row.map(() => 0));
  }
  if (Array.isArray(next.h_walls)) {
    next.h_walls = next.h_walls.map((row) => row.map(() => 0));
  }
  if (Array.isArray(next.v_walls)) {
    next.v_walls = next.v_walls.map((row) => row.map(() => 0));
  }
  if (Array.isArray(next.hex_walls)) {
    next.hex_walls = [];
  }
  if (typeof next.terrain === "string" && typeof next.blocks === "string") {
    const rows = Array.isArray(next.board) ? next.board.length : 6;
    const cols = Array.isArray(next.board) && Array.isArray(next.board[0]) ? next.board[0].length : 6;
    const emptyGrid = Array.from({ length: rows }, () => Array(cols).fill("o").join(" ")).join("\n");
    next.terrain = emptyGrid;
    next.blocks = emptyGrid;
    next.chains = [];
    delete next.pieces;
  }
  if (Array.isArray(next.tubes)) {
    next.tubes = next.tubes.map(() => []);
  }
  if (next.faces && typeof next.faces === "object") {
    const defaults = { U: "W", R: "R", F: "G", D: "Y", L: "O", B: "B" };
    for (const f of Object.keys(defaults)) {
      if (Array.isArray(next.faces[f])) {
        next.faces[f] = next.faces[f].map((row) => row.map(() => defaults[f]));
      }
    }
  }
  if (Array.isArray(next.row_clues)) {
    next.row_clues = next.row_clues.map(() => []);
  }
  if (Array.isArray(next.col_clues)) {
    next.col_clues = next.col_clues.map(() => []);
  }
  for (const key of ["text", "ciphertext", "morse", "input"]) {
    if (typeof next[key] === "string") next[key] = "";
  }
  return next;
}

els.btnClear.addEventListener("click", () => {
  if (!state.activeSolver) return;
  clearPlayback();
  state.editState = clearBoardState(state.activeSolver, state.editState);
  renderParams(state.activeSolver, extractPresetParams(state.activeSolver, state.editState));
  saveDraft();
  renderStage();
  els.stepDescLive.textContent = "Cleared board for manual setup.";
});

els.btnReset.addEventListener("click", () => {
  if (!state.activeSolver) return;
  clearPlayback();
  clearDraft(state.activeSolver.slug);
  state.editState = deepClone(state.activeSolver.presets[state.activePresetName] || {});
  renderParams(state.activeSolver, extractPresetParams(state.activeSolver, state.editState));
  renderStage();
});

const THEMES = [
  { id: "chalk", label: "Theme: Chalk" },
  { id: "plum", label: "Theme: Plum" },
  { id: "slate", label: "Theme: Slate" },
  { id: "forge", label: "Theme: Forge" },
  { id: "ramapillar", label: "Theme: Ramapillar" },
];

function updateThemeFavicon() {
  const link = document.querySelector('link[rel="icon"]');
  if (!link) return;
  const cs = getComputedStyle(document.documentElement);
  const bg = cs.getPropertyValue("--bg-main").trim() || "#0F1412";
  const border = cs.getPropertyValue("--border").trim() || "#3A4D45";
  const c1 = cs.getPropertyValue("--accent-primary").trim() || "#00F5D4";
  const c2 = cs.getPropertyValue("--accent-secondary").trim() || "#B5FF4D";
  const c3 = cs.getPropertyValue("--accent-hot").trim() || "#FF4D80";
  const c4 = cs.getPropertyValue("--accent-warm").trim() || "#FFB800";
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">`
    + `<rect x="1" y="1" width="30" height="30" rx="6" fill="${bg}" stroke="${border}" stroke-width="1.5"/>`
    + `<path d="M 4 4 H 16 V 8 A 2.4 2.4 0 1 1 16 12.8 V 16 H 12.8 A 2.4 2.4 0 1 0 8 16 H 4 Z" fill="${c1}" stroke="${bg}" stroke-width="1.2" stroke-linejoin="round"/>`
    + `<path d="M 16 4 H 28 V 16 H 24 A 2.4 2.4 0 1 1 19.2 16 H 16 V 12.8 A 2.4 2.4 0 1 0 16 8 Z" fill="${c2}" stroke="${bg}" stroke-width="1.2" stroke-linejoin="round"/>`
    + `<path d="M 4 16 H 8 A 2.4 2.4 0 1 1 12.8 16 H 16 V 19.2 A 2.4 2.4 0 1 0 16 24 V 28 H 4 Z" fill="${c3}" stroke="${bg}" stroke-width="1.2" stroke-linejoin="round"/>`
    + `<path d="M 16 16 H 19.2 A 2.4 2.4 0 1 0 24 16 H 28 V 28 H 16 V 24 A 2.4 2.4 0 1 1 16 19.2 Z" fill="${c4}" stroke="${bg}" stroke-width="1.2" stroke-linejoin="round"/>`
    + `</svg>`;
  link.href = "data:image/svg+xml," + encodeURIComponent(svg);
}

function applyTheme(theme) {
  const found = THEMES.find((t) => t.id === theme) || THEMES[0];
  document.documentElement.setAttribute("data-theme", found.id);
  localStorage.setItem("tpl_theme", found.id);
  els.btnTheme.textContent = found.label;
  updateThemeFavicon();
}

els.btnTheme.addEventListener("click", () => {
  const cur = document.documentElement.getAttribute("data-theme");
  const idx = THEMES.findIndex((t) => t.id === cur);
  const next = THEMES[(idx + 1) % THEMES.length];
  applyTheme(next.id);
});

els.btnLogs.addEventListener("click", () => {
  els.logDrawer.classList.toggle("collapsed");
});

els.modePill.addEventListener("click", () => {
  if (isPlaybackMode()) {
    clearPlayback();
    renderStage();
  }
});

els.btnSolve.addEventListener("click", runSolve);

els.btnAbort.addEventListener("click", async () => {
  if (state.activeJobId) {
    await fetch(`/api/abort/${state.activeJobId}`, { method: "POST" });
  }
  if (state.abortController) state.abortController.abort();
});

els.btnFirst.addEventListener("click", () => {
  stopPlayback();
  state.stepIdx = 0;
  renderStage();
});
els.btnPrev.addEventListener("click", () => {
  stopPlayback();
  state.stepIdx = Math.max(0, state.stepIdx - 1);
  renderStage();
});
els.btnNext.addEventListener("click", () => {
  stopPlayback();
  state.stepIdx = Math.min(state.steps.length - 1, state.stepIdx + 1);
  renderStage();
});
els.btnLast.addEventListener("click", () => {
  stopPlayback();
  state.stepIdx = Math.max(0, state.steps.length - 1);
  renderStage();
});
els.btnPlay.addEventListener("click", () => {
  if (state.playing) {
    stopPlayback();
  } else if (state.steps.length > 1) {
    if (state.stepIdx >= state.steps.length - 1) state.stepIdx = 0;
    state.playing = true;
    els.btnPlay.textContent = "Pause";
    renderStage().then(scheduleNextFrame);
  }
});
els.scrubSlider.addEventListener("input", () => {
  stopPlayback();
  state.stepIdx = Number(els.scrubSlider.value);
  renderStage();
});

// JSON Modal
els.btnJson.addEventListener("click", () => {
  const current = isPlaybackMode() ? state.steps[state.stepIdx].state : state.editState;
  els.jsonTextarea.value = JSON.stringify(current, null, 2);
  els.jsonModal.classList.remove("hidden");
});
els.btnJsonClose.addEventListener("click", () => els.jsonModal.classList.add("hidden"));
els.btnJsonApply.addEventListener("click", () => {
  try {
    const parsed = JSON.parse(els.jsonTextarea.value);
    clearPlayback();
    state.editState = parsed;
    saveDraft();
    els.jsonModal.classList.add("hidden");
    renderStage();
  } catch (e) {
    alert("Invalid JSON: " + e.message);
  }
});

async function init() {
  const urlTheme = new URLSearchParams(window.location.search).get("theme");
  const savedTheme = localStorage.getItem("tpl_theme");
  applyTheme(urlTheme || savedTheme || "chalk");

  const resp = await fetch("/api/solvers");
  const data = await resp.json();
  state.solvers = data.solvers || [];
  renderSidebar();
  if (state.solvers.length > 0) {
    let savedSlug = null;
    try {
      savedSlug = localStorage.getItem(ACTIVE_SOLVER_KEY);
    } catch {
      // Ignore
    }
    const target = state.solvers.find((s) => s.slug === savedSlug) || state.solvers[0];
    selectSolver(target.slug);
  }
}

init();
