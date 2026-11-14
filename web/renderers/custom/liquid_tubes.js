const TUBE_COLORS = [
  "#FA8231",
  "#00F5D4",
  "#FF007F",
  "#FFE600",
  "#01CA6B",
  "#B9A7E3",
  "#E76C8F",
  "#3867D6",
];

let activeTubeColor = 0;

export function render(stage, solver, renderState, highlights, editable, onEdit) {
  stage.innerHTML = "";
  const tubes = renderState?.tubes || [];
  const caps = renderState?.capacities || tubes.map(() => 4);
  const defaultCap = caps[0] || 4;

  if (editable) {
    const bar = document.createElement("div");
    bar.className = "grid-toolbar";

    const makeSelect = (labelText, minV, maxV, curV, onChange) => {
      const wrap = document.createElement("label");
      wrap.style.display = "inline-flex";
      wrap.style.alignItems = "center";
      wrap.style.gap = "5px";
      wrap.style.fontSize = "12px";
      wrap.style.color = "var(--text-muted)";
      wrap.textContent = labelText;
      const sel = document.createElement("select");
      for (let v = minV; v <= maxV; v++) {
        const o = document.createElement("option");
        o.value = String(v);
        o.textContent = String(v);
        if (v === curV) o.selected = true;
        sel.appendChild(o);
      }
      sel.addEventListener("change", () => onChange(Number(sel.value)));
      wrap.appendChild(sel);
      return wrap;
    };

    bar.appendChild(
      makeSelect("Tubes", 3, 10, tubes.length, (n) => {
        const next = JSON.parse(JSON.stringify(renderState));
        const nextTubes = [];
        const nextCaps = [];
        for (let i = 0; i < n; i++) {
          nextTubes.push(tubes[i] ? tubes[i].slice() : []);
          nextCaps.push(caps[i] || defaultCap);
        }
        next.tubes = nextTubes;
        next.capacities = nextCaps;
        onEdit(next);
      }),
    );

    bar.appendChild(
      makeSelect("Capacity", 3, 6, defaultCap, (cap) => {
        const next = JSON.parse(JSON.stringify(renderState));
        next.capacities = tubes.map(() => cap);
        next.tubes = tubes.map((t) => t.slice(0, cap));
        onEdit(next);
      }),
    );

    const cLbl = document.createElement("span");
    cLbl.style.fontSize = "12px";
    cLbl.style.color = "var(--text-muted)";
    cLbl.style.marginLeft = "6px";
    cLbl.textContent = "Color:";
    bar.appendChild(cLbl);

    for (let cid = 0; cid < TUBE_COLORS.length; cid++) {
      const sw = document.createElement("button");
      sw.className = "palette-swatch" + (activeTubeColor === cid ? " selected" : "");
      sw.style.background = TUBE_COLORS[cid];
      sw.style.color = "#111";
      sw.style.fontSize = "11px";
      sw.style.fontWeight = "700";
      sw.textContent = String(cid + 1);
      sw.addEventListener("click", () => {
        activeTubeColor = cid;
        render(stage, solver, renderState, highlights, editable, onEdit);
      });
      bar.appendChild(sw);
    }

    stage.appendChild(bar);
  }

  const rack = document.createElement("div");
  rack.className = "tubes-rack";

  tubes.forEach((tube, idx) => {
    const wrap = document.createElement("div");
    wrap.className = "tube-wrap";
    if (highlights.src === idx) wrap.classList.add("src");
    if (highlights.dst === idx) wrap.classList.add("dst");

    const cap = caps[idx] || 4;
    const body = document.createElement("div");
    body.className = "tube-body";
    body.style.height = `${cap * 32 + 16}px`;
    if (editable) {
      body.style.cursor = "pointer";
      body.title = "Click to push color, Right-click (or Pop button) to remove top";
      body.addEventListener("click", () => {
        if (tube.length >= cap) return;
        const next = JSON.parse(JSON.stringify(renderState));
        next.tubes[idx].push(activeTubeColor);
        onEdit(next);
      });
      body.addEventListener("contextmenu", (e) => {
        e.preventDefault();
        if (tube.length === 0) return;
        const next = JSON.parse(JSON.stringify(renderState));
        next.tubes[idx].pop();
        onEdit(next);
      });
    }

    tube.forEach((colorId) => {
      const seg = document.createElement("div");
      seg.className = "tube-seg";
      seg.style.background = TUBE_COLORS[colorId % TUBE_COLORS.length];
      seg.textContent = String(colorId + 1);
      body.appendChild(seg);
    });

    const lbl = document.createElement("div");
    lbl.style.fontSize = "11px";
    lbl.style.color = "var(--text-muted)";
    lbl.textContent = `Tube ${idx + 1} (${tube.length}/${cap})`;

    wrap.appendChild(body);
    wrap.appendChild(lbl);

    if (editable && tube.length > 0) {
      const popBtn = document.createElement("button");
      popBtn.className = "btn";
      popBtn.style.padding = "2px 6px";
      popBtn.style.fontSize = "10px";
      popBtn.textContent = "Pop";
      popBtn.addEventListener("click", () => {
        const next = JSON.parse(JSON.stringify(renderState));
        next.tubes[idx].pop();
        onEdit(next);
      });
      wrap.appendChild(popBtn);
    }

    rack.appendChild(wrap);
  });

  stage.appendChild(rack);
}
