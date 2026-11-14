export function renderText(stage, solver, renderState, editable, onEdit) {
  stage.innerHTML = "";
  const root = document.createElement("div");
  root.className = "text-workbench";

  const panes = document.createElement("div");
  panes.className = "text-panes";

  const inPane = document.createElement("div");
  inPane.className = "text-pane";
  const inLbl = document.createElement("label");
  inLbl.textContent = "Input / Ciphertext";
  const inArea = document.createElement("textarea");
  inArea.value = renderState?.text || "";
  inArea.readOnly = !editable;
  if (editable) {
    inArea.addEventListener("change", () => {
      onEdit({ ...renderState, text: inArea.value });
    });
  }
  inPane.appendChild(inLbl);
  inPane.appendChild(inArea);

  const outPane = document.createElement("div");
  outPane.className = "text-pane";
  const outLbl = document.createElement("label");
  outLbl.textContent = "Decoded Output";
  const outArea = document.createElement("textarea");
  outArea.readOnly = true;
  outArea.value = renderState?.output || "";
  outPane.appendChild(outLbl);
  outPane.appendChild(outArea);

  panes.appendChild(inPane);
  panes.appendChild(outPane);
  root.appendChild(panes);

  const cands = renderState?.candidates || [];
  if (cands.length > 0) {
    const box = document.createElement("div");
    box.className = "candidates-box";
    box.innerHTML = `<div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);font-weight:700;margin-bottom:8px;">Candidates (${cands.length})</div>`;
    for (const c of cands) {
      const item = document.createElement("div");
      item.className = "cand-item";
      item.innerHTML = `<span style="color:var(--accent-secondary)">${c.label}</span><span>${c.text}</span>`;
      box.appendChild(item);
    }
    root.appendChild(box);
  }

  const freqs = renderState?.frequencies || [];
  if (freqs.length > 0) {
    const fbox = document.createElement("div");
    fbox.className = "freq-box";
    fbox.innerHTML = `<div style="font-size:11px;text-transform:uppercase;letter-spacing:.8px;color:var(--text-muted);font-weight:700;">Character Frequency</div>`;
    const bars = document.createElement("div");
    bars.className = "freq-bars";
    const maxPct = Math.max(...freqs.map((f) => f.pct), 1);
    for (const f of freqs) {
      const col = document.createElement("div");
      col.className = "freq-col";
      const h = Math.max(6, Math.round((f.pct / maxPct) * 60));
      col.innerHTML = `<span class="freq-label">${f.count}</span><div class="freq-bar" style="height:${h}px"></div><span class="freq-label">${f.char}</span>`;
      bars.appendChild(col);
    }
    fbox.appendChild(bars);
    root.appendChild(fbox);
  }

  stage.appendChild(root);
}
