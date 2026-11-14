"""Slitherlink single-loop solver using vertex-degree & clue backtracking."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "loop_games",
    "name": "Loop Family (Slitherlink)",
    "category": "State",
    "renderer": "custom",
    "custom_view": "/renderers/custom/loop_board.js",
    "description": "Solves Slitherlink single-loop lattice puzzles with numerical cell clues (0-3).",
    "presets": {
        "4x4": {
            "rows": 4,
            "cols": 4,
            "cell_clues": [
                [2, 2, 2, None],
                [2, None, 2, 2],
                [2, 2, None, 2],
                [None, 2, 2, 2],
            ],
            "h_edges": [[0] * 4 for _ in range(5)],
            "v_edges": [[0] * 5 for _ in range(4)],
        },
        "5x5": {
            "rows": 5,
            "cols": 5,
            "cell_clues": [
                [2, None, 2, None, 1],
                [None, 3, None, 2, None],
                [2, None, 2, None, 2],
                [None, 2, None, 3, None],
                [1, None, 2, None, 2],
            ],
            "h_edges": [[0] * 5 for _ in range(6)],
            "v_edges": [[0] * 6 for _ in range(5)],
        },
    },
    "params": [],
}


def _solve_slitherlink(
    rows: int,
    cols: int,
    clues: List[List[Optional[int]]],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    h = [[0] * cols for _ in range(rows + 1)]
    v = [[0] * (cols + 1) for _ in range(rows)]

    def cell_coords(r: int, c: int) -> List[Tuple[str, int, int]]:
        return [("h", r, c), ("h", r + 1, c), ("v", r, c), ("v", r, c + 1)]

    def vertex_coords(vr: int, vc: int) -> List[Tuple[str, int, int]]:
        out: List[Tuple[str, int, int]] = []
        if vc > 0:
            out.append(("h", vr, vc - 1))
        if vc < cols:
            out.append(("h", vr, vc))
        if vr > 0:
            out.append(("v", vr - 1, vc))
        if vr < rows:
            out.append(("v", vr, vc))
        return out

    def get_edge(kind: str, er: int, ec: int) -> int:
        return h[er][ec] if kind == "h" else v[er][ec]

    def set_edge(kind: str, er: int, ec: int, val: int) -> None:
        if kind == "h":
            h[er][ec] = val
        else:
            v[er][ec] = val

    def is_single_loop() -> bool:
        adj: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        for r in range(rows + 1):
            for c in range(cols):
                if h[r][c] == 1:
                    adj.setdefault((r, c), []).append((r, c + 1))
                    adj.setdefault((r, c + 1), []).append((r, c))
        for r in range(rows):
            for c in range(cols + 1):
                if v[r][c] == 1:
                    adj.setdefault((r, c), []).append((r + 1, c))
                    adj.setdefault((r + 1, c), []).append((r, c))
        if not adj:
            return False
        if any(len(nbrs) != 2 for nbrs in adj.values()):
            return False
        start = next(iter(adj))
        seen = {start}
        q = deque([start])
        while q:
            u = q.popleft()
            for w in adj[u]:
                if w not in seen:
                    seen.add(w)
                    q.append(w)
        return len(seen) == len(adj)

    def has_premature_loop() -> bool:
        """Detect if any closed loop exists while other 1-edges or positive clues remain outside it."""
        adj: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
        edge_count = 0
        for r in range(rows + 1):
            for c in range(cols):
                if h[r][c] == 1:
                    edge_count += 1
                    adj.setdefault((r, c), []).append((r, c + 1))
                    adj.setdefault((r, c + 1), []).append((r, c))
        for r in range(rows):
            for c in range(cols + 1):
                if v[r][c] == 1:
                    edge_count += 1
                    adj.setdefault((r, c), []).append((r + 1, c))
                    adj.setdefault((r + 1, c), []).append((r, c))
        if edge_count == 0:
            return False
        seen_verts: set[Tuple[int, int]] = set()
        for start in adj:
            if start in seen_verts:
                continue
            comp: List[Tuple[int, int]] = []
            q = deque([start])
            seen_verts.add(start)
            while q:
                u = q.popleft()
                comp.append(u)
                for w in adj[u]:
                    if w not in seen_verts:
                        seen_verts.add(w)
                        q.append(w)
            if all(len(adj[u]) == 2 for u in comp):
                comp_edges = sum(len(adj[u]) for u in comp) // 2
                if comp_edges < edge_count:
                    return True
                for r in range(rows):
                    for c in range(cols):
                        clue = clues[r][c]
                        if clue is not None and clue > 0:
                            vals = [get_edge(k, er, ec) for k, er, ec in cell_coords(r, c)]
                            if vals.count(1) < clue:
                                return True
        return False

    def propagate(trail: List[Tuple[str, int, int]]) -> Tuple[bool, List[Tuple[str, int, int, int, str]], str]:
        """Propagate cell clue and vertex degree constraints, recording assigned edges and reasons."""
        events: List[Tuple[str, int, int, int, str]] = []
        changed = True
        while changed:
            changed = False
            for r in range(rows):
                for c in range(cols):
                    clue = clues[r][c]
                    if clue is None:
                        continue
                    coords = cell_coords(r, c)
                    vals = [get_edge(k, er, ec) for k, er, ec in coords]
                    ones = vals.count(1)
                    unk = vals.count(0)
                    if ones > clue:
                        return False, events, f"Cell ({r + 1},{c + 1})={clue} exceeded ({ones} ON edges)"
                    if ones + unk < clue:
                        return False, events, f"Cell ({r + 1},{c + 1})={clue} starved (only {ones + unk} possible)"
                    if unk > 0:
                        if ones == clue:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, -1)
                                    trail.append((k, er, ec))
                                    events.append((k, er, ec, -1, f"Cell ({r + 1},{c + 1})={clue} satisfied -> {k.upper()}({er},{ec}) OFF"))
                                    changed = True
                        elif ones + unk == clue:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, 1)
                                    trail.append((k, er, ec))
                                    events.append((k, er, ec, 1, f"Cell ({r + 1},{c + 1})={clue} needs {unk} remaining -> {k.upper()}({er},{ec}) ON"))
                                    changed = True

            for vr in range(rows + 1):
                for vc in range(cols + 1):
                    coords = vertex_coords(vr, vc)
                    vals = [get_edge(k, er, ec) for k, er, ec in coords]
                    ones = vals.count(1)
                    unk = vals.count(0)
                    if ones > 2:
                        return False, events, f"Vertex ({vr},{vc}) degree {ones} > 2"
                    if unk == 0 and ones == 1:
                        return False, events, f"Vertex ({vr},{vc}) dead-end (degree 1)"
                    if unk > 0:
                        if ones == 2:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, -1)
                                    trail.append((k, er, ec))
                                    events.append((k, er, ec, -1, f"Vertex ({vr},{vc}) degree 2 -> {k.upper()}({er},{ec}) OFF"))
                                    changed = True
                        elif ones == 1 and unk == 1:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, 1)
                                    trail.append((k, er, ec))
                                    events.append((k, er, ec, 1, f"Vertex ({vr},{vc}) degree 1 with 1 open edge -> {k.upper()}({er},{ec}) ON"))
                                    changed = True
                        elif ones == 0 and unk == 1:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, -1)
                                    trail.append((k, er, ec))
                                    events.append((k, er, ec, -1, f"Vertex ({vr},{vc}) isolated (1 open edge) -> {k.upper()}({er},{ec}) OFF"))
                                    changed = True
        if has_premature_loop():
            return False, events, "Premature closed loop detected"
        return True, events, ""

    def pick_next_edge() -> Optional[Tuple[str, int, int]]:
        best: Optional[Tuple[int, str, int, int]] = None
        for r in range(rows + 1):
            for c in range(cols):
                if h[r][c] == 0:
                    score = 0
                    if r > 0 and clues[r - 1][c] is not None:
                        score += 4 - abs(clues[r - 1][c] - 2)
                    if r < rows and clues[r][c] is not None:
                        score += 4 - abs(clues[r][c] - 2)
                    if any(get_edge(k, er, ec) == 1 for k, er, ec in vertex_coords(r, c) + vertex_coords(r, c + 1)):
                        score += 10
                    cand = (-score, "h", r, c)
                    if best is None or cand < best:
                        best = cand
        for r in range(rows):
            for c in range(cols + 1):
                if v[r][c] == 0:
                    score = 0
                    if c > 0 and clues[r][c - 1] is not None:
                        score += 4 - abs(clues[r][c - 1] - 2)
                    if c < cols and clues[r][c] is not None:
                        score += 4 - abs(clues[r][c] - 2)
                    if any(get_edge(k, er, ec) == 1 for k, er, ec in vertex_coords(r, c) + vertex_coords(r + 1, c)):
                        score += 10
                    cand = (-score, "v", r, c)
                    if best is None or cand < best:
                        best = cand
        return (best[1], best[2], best[3]) if best is not None else None

    def snap() -> Dict[str, Any]:
        return {
            "rows": rows,
            "cols": cols,
            "size": rows if rows == cols else max(rows, cols),
            "cell_clues": clues,
            "h_edges": [list(row) for row in h],
            "v_edges": [list(row) for row in v],
        }

    def count_on() -> int:
        return sum(row.count(1) for row in h) + sum(row.count(1) for row in v)

    yield {
        "type": "start",
        "state": snap(),
        "highlights": {},
        "desc": f"Loaded {rows}x{cols} Slitherlink lattice",
        "stats": {"rows": rows, "cols": cols, "segments": 0, "branches": 0, "backtracks": 0},
    }

    stats = {"branches": 0, "backtracks": 0}
    stalled_emitted = False

    def solve_gen() -> Generator[Tuple[str, Optional[Tuple[str, int, int]], str], None, bool]:
        nonlocal stalled_emitted
        nxt = pick_next_edge()
        if nxt is None:
            return is_single_loop()
        kind, er, ec = nxt
        for val in (1, -1):
            if should_abort():
                return False
            stats["branches"] += 1
            trail: List[Tuple[str, int, int]] = [(kind, er, ec)]
            set_edge(kind, er, ec, val)
            label = "ON" if val == 1 else "OFF"
            prefix = "Deduction stalled -> " if not stalled_emitted else ""
            stalled_emitted = True
            yield ("explore", (kind, er, ec), f"{prefix}Branch {kind.upper()}({er},{ec}) = {label}")
            ok, events, err = propagate(trail)
            for k, r, c, ev_val, reason in events:
                if ev_val == 1:
                    yield ("deduce", (k, r, c), reason)
            if ok:
                solved = yield from solve_gen()
                if solved:
                    return True
            else:
                stats["backtracks"] += 1
                yield ("backtrack", (kind, er, ec), f"Contradiction ({err}) -> backtrack {kind.upper()}({er},{ec})")
            for tk, tr, tc in trail:
                set_edge(tk, tr, tc, 0)
        return False

    init_trail: List[Tuple[str, int, int]] = []
    ok, init_events, init_err = propagate(init_trail)
    for k, r, c, ev_val, reason in init_events:
        if should_abort():
            return
        if ev_val == 1:
            yield {
                "type": "deduce",
                "state": snap(),
                "highlights": {"edge": [k, r, c]},
                "desc": reason,
                "stats": {"segments": count_on(), "branches": 0, "backtracks": 0},
            }

    if not ok:
        yield {
            "type": "failed",
            "state": snap(),
            "highlights": {},
            "desc": f"Pre-search contradiction: {init_err}.",
            "stats": stats,
        }
        return

    found = False
    gen = solve_gen()
    try:
        while True:
            if should_abort():
                return
            stype, edge_ref, desc = next(gen)
            yield {
                "type": stype,
                "state": snap(),
                "highlights": {"edge": list(edge_ref)} if edge_ref else {},
                "desc": desc,
                "stats": {"segments": count_on(), **stats},
            }
    except StopIteration as stop:
        found = bool(stop.value)

    if should_abort():
        return

    if not found:
        yield {
            "type": "failed",
            "state": snap(),
            "highlights": {},
            "desc": "No valid single-loop Slitherlink solution exists (search exhausted).",
            "stats": stats,
        }
        return

    yield {
        "type": "solution",
        "state": snap(),
        "highlights": {},
        "desc": f"Solved {rows}x{cols} Slitherlink ({count_on()} segments, {stats['branches']} branches, {stats['backtracks']} backtracks)",
        "stats": {"segments": count_on(), **stats},
    }


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    clues = state["cell_clues"]
    rows = int(state.get("rows") or state.get("size") or len(clues))
    cols = int(state.get("cols") or state.get("size") or (len(clues[0]) if clues else rows))
    yield from _solve_slitherlink(rows, cols, clues, should_abort)
