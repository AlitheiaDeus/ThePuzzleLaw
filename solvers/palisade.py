"""Palisade (Five Cells) region-partitioning solver using Union-Find propagation + MRV backtracking."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "palisade",
    "name": "Palisade",
    "category": "State",
    "renderer": "custom",
    "custom_view": "/renderers/custom/loop_board.js",
    "description": (
        "Partitions an R x C grid into orthogonally connected regions of exact size K, "
        "where each clue (0-3) equals the cell's count of boundary walls."
    ),
    "presets": {
        "4x4 (K=4)": {
            "rows": 4,
            "cols": 4,
            "region_size": 4,
            "cell_clues": [
                [2, 3, None, 3],
                [None, 3, 2, None],
                [3, None, 3, None],
                [3, None, 3, 2],
            ],
            "h_edges": [[0] * 4 for _ in range(5)],
            "v_edges": [[0] * 5 for _ in range(4)],
        },
        "5x5 (K=5)": {
            "rows": 5,
            "cols": 5,
            "region_size": 5,
            "cell_clues": [
                [2, None, 2, None, 2],
                [3, 3, 3, None, 1],
                [None, 2, None, 3, 3],
                [2, None, 2, None, 2],
                [3, 3, None, 1, 2],
            ],
            "h_edges": [[0] * 5 for _ in range(6)],
            "v_edges": [[0] * 6 for _ in range(5)],
        },
        "4x6 (K=4)": {
            "rows": 4,
            "cols": 6,
            "region_size": 4,
            "cell_clues": [
                [2, 3, None, 3, None, 3],
                [None, 3, 2, None, 2, None],
                [3, None, 3, 2, 3, None],
                [3, None, 3, None, 3, 2],
            ],
            "h_edges": [[0] * 6 for _ in range(5)],
            "v_edges": [[0] * 7 for _ in range(4)],
        },
        "6x6 (K=6)": {
            "rows": 6,
            "cols": 6,
            "region_size": 6,
            "cell_clues": [
                [2, None, 2, None, 2, 2],
                [2, 3, 3, 3, 3, None],
                [3, 1, None, 2, 1, 3],
                [None, 2, 3, 1, 2, 3],
                [3, 2, 1, 3, None, 1],
                [3, 1, 2, 3, 1, 2],
            ],
            "h_edges": [[0] * 6 for _ in range(7)],
            "v_edges": [[0] * 7 for _ in range(6)],
        },
    },
    "params": [],
}


def _build_zones(
    rows: int,
    cols: int,
    h: List[List[int]],
    v: List[List[int]],
    solved_only: bool = False,
) -> Optional[List[List[int]]]:
    """Return component zone ids per cell connected by open (-1) edges."""
    comp = [[-1] * cols for _ in range(rows)]
    cid = 0
    for sr in range(rows):
        for sc in range(cols):
            if comp[sr][sc] != -1:
                continue
            q = deque([(sr, sc)])
            comp[sr][sc] = cid
            while q:
                r, c = q.popleft()
                if r > 0 and h[r][c] == -1 and comp[r - 1][c] == -1:
                    comp[r - 1][c] = cid
                    q.append((r - 1, c))
                if r + 1 < rows and h[r + 1][c] == -1 and comp[r + 1][c] == -1:
                    comp[r + 1][c] = cid
                    q.append((r + 1, c))
                if c > 0 and v[r][c] == -1 and comp[r][c - 1] == -1:
                    comp[r][c - 1] = cid
                    q.append((r, c - 1))
                if c + 1 < cols and v[r][c + 1] == -1 and comp[r][c + 1] == -1:
                    comp[r][c + 1] = cid
                    q.append((r, c + 1))
            cid += 1
    if solved_only and cid != (rows * cols):
        return comp
    return comp


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    clues: List[List[Optional[int]]] = state["cell_clues"]
    rows = int(state.get("rows") or len(clues))
    cols = int(state.get("cols") or (len(clues[0]) if clues else rows))
    region_size = int(state.get("region_size") or params.get("region_size") or cols)

    # Outer border edges are ALWAYS boundaries (= 1)
    h = [[0] * cols for _ in range(rows + 1)]
    v = [[0] * (cols + 1) for _ in range(rows)]
    raw_h = state.get("h_edges") or []
    raw_v = state.get("v_edges") or []
    for r in range(rows + 1):
        for c in range(cols):
            if r == 0 or r == rows:
                h[r][c] = 1
            elif r < len(raw_h) and c < len(raw_h[r]) and raw_h[r][c] in (1, -1):
                h[r][c] = int(raw_h[r][c])
    for r in range(rows):
        for c in range(cols + 1):
            if c == 0 or c == cols:
                v[r][c] = 1
            elif r < len(raw_v) and c < len(raw_v[r]) and raw_v[r][c] in (1, -1):
                v[r][c] = int(raw_v[r][c])

    def cell_coords(r: int, c: int) -> List[Tuple[str, int, int]]:
        return [("h", r, c), ("h", r + 1, c), ("v", r, c), ("v", r, c + 1)]

    def edge_cells(kind: str, er: int, ec: int) -> Optional[Tuple[Tuple[int, int], Tuple[int, int]]]:
        if kind == "h":
            if 1 <= er < rows:
                return ((er - 1, ec), (er, ec))
            return None
        if 1 <= ec < cols:
            return ((er, ec - 1), (er, ec))
        return None

    def get_e(kind: str, er: int, ec: int) -> int:
        return h[er][ec] if kind == "h" else v[er][ec]

    def set_e(kind: str, er: int, ec: int, val: int) -> None:
        if kind == "h":
            h[er][ec] = val
        else:
            v[er][ec] = val

    def snap(with_zones: bool = False) -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "rows": rows,
            "cols": cols,
            "region_size": region_size,
            "cell_clues": clues,
            "h_edges": [list(row) for row in h],
            "v_edges": [list(row) for row in v],
        }
        if with_zones:
            out["zones"] = _build_zones(rows, cols, h, v)
        return out

    def count_walls() -> int:
        internal_h = sum(row.count(1) for row in h[1:rows])
        internal_v = sum(row[1:cols].count(1) for row in v)
        return internal_h + internal_v

    yield {
        "type": "start",
        "state": snap(False),
        "highlights": {},
        "desc": f"Loaded {rows}x{cols} Palisade (target region size K={region_size})",
        "stats": {"rows": rows, "cols": cols, "K": region_size, "walls": count_walls()},
    }

    if region_size < 2 or (rows * cols) % region_size != 0:
        yield {
            "type": "failed",
            "state": snap(False),
            "highlights": {},
            "desc": (
                f"Pre-solve divisibility check failed: {rows}x{cols} = {rows * cols} cells "
                f"cannot be partitioned into regions of size K={region_size}."
            ),
            "stats": {},
        }
        return

    for r in range(rows):
        for c in range(cols):
            cl = clues[r][c]
            if cl is not None and (cl < 0 or cl > 3):
                yield {
                    "type": "failed",
                    "state": snap(False),
                    "highlights": {},
                    "desc": f"Pre-solve check failed: cell ({r + 1}, {c + 1}) clue {cl} must be in 0..3 for K >= 2.",
                    "stats": {},
                }
                return

    def compute_components():
        comp_id = [[-1] * cols for _ in range(rows)]
        comps: List[List[Tuple[int, int]]] = []
        cid = 0
        for sr in range(rows):
            for sc in range(cols):
                if comp_id[sr][sc] != -1:
                    continue
                cells: List[Tuple[int, int]] = []
                q = deque([(sr, sc)])
                comp_id[sr][sc] = cid
                while q:
                    r, c = q.popleft()
                    cells.append((r, c))
                    if r > 0 and h[r][c] == -1 and comp_id[r - 1][c] == -1:
                        comp_id[r - 1][c] = cid
                        q.append((r - 1, c))
                    if r + 1 < rows and h[r + 1][c] == -1 and comp_id[r + 1][c] == -1:
                        comp_id[r + 1][c] = cid
                        q.append((r + 1, c))
                    if c > 0 and v[r][c] == -1 and comp_id[r][c - 1] == -1:
                        comp_id[r][c - 1] = cid
                        q.append((r, c - 1))
                    if c + 1 < cols and v[r][c + 1] == -1 and comp_id[r][c + 1] == -1:
                        comp_id[r][c + 1] = cid
                        q.append((r, c + 1))
                comps.append(cells)
                cid += 1
        return comp_id, comps

    def is_solved() -> bool:
        _, comps = compute_components()
        if any(len(c) != region_size for c in comps):
            return False
        for r in range(rows):
            for c in range(cols):
                cl = clues[r][c]
                if cl is not None:
                    walls = sum(1 for k, er, ec in cell_coords(r, c) if get_e(k, er, ec) == 1)
                    if walls != cl:
                        return False
        return True

    def propagate(trail: List[Tuple[str, int, int]]) -> Tuple[bool, List[Tuple[str, int, int, int, str]], str]:
        events: List[Tuple[str, int, int, int, str]] = []
        changed = True
        while changed:
            changed = False
            # 1. Cell wall clues
            for r in range(rows):
                for c in range(cols):
                    cl = clues[r][c]
                    if cl is None:
                        continue
                    coords = cell_coords(r, c)
                    vals = [get_e(k, er, ec) for k, er, ec in coords]
                    ones = vals.count(1)
                    unk = vals.count(0)
                    if ones > cl:
                        return False, events, f"Cell ({r + 1},{c + 1})={cl} exceeded ({ones} walls)"
                    if ones + unk < cl:
                        return False, events, f"Cell ({r + 1},{c + 1})={cl} starved (only {ones + unk} possible)"
                    if unk > 0:
                        if ones == cl:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_e(k, er, ec, -1)
                                    trail.append((k, er, ec))
                                    events.append((k, er, ec, -1, f"Cell ({r + 1},{c + 1})={cl} satisfied -> open {k.upper()}({er},{ec})"))
                                    changed = True
                        elif ones + unk == cl:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_e(k, er, ec, 1)
                                    trail.append((k, er, ec))
                                    events.append((k, er, ec, 1, f"Cell ({r + 1},{c + 1})={cl} needs {unk} wall(s) -> lock {k.upper()}({er},{ec})"))
                                    changed = True

            # 2. Region Union-Find size & connectivity constraints
            comp_id, comps = compute_components()
            for cid, cells in enumerate(comps):
                if len(cells) > region_size:
                    return False, events, f"Connected region grew to {len(cells)} > K={region_size}"

            # Check internal edges between cells
            for kind, max_r, max_c, start_r, start_c in (("h", rows, cols, 1, 0), ("v", rows, cols, 0, 1)):
                for er in range(start_r, max_r):
                    for ec in range(start_c, max_c):
                        if get_e(kind, er, ec) != 0:
                            continue
                        pair = edge_cells(kind, er, ec)
                        if pair is None:
                            continue
                        (r1, c1), (r2, c2) = pair
                        id1, id2 = comp_id[r1][c1], comp_id[r2][c2]
                        if id1 == id2:
                            # Same region must not have an interior boundary wall
                            set_e(kind, er, ec, -1)
                            trail.append((kind, er, ec))
                            events.append((kind, er, ec, -1, f"Same-region cycle prevention -> open {kind.upper()}({er},{ec})"))
                            changed = True
                        elif len(comps[id1]) + len(comps[id2]) > region_size:
                            set_e(kind, er, ec, 1)
                            trail.append((kind, er, ec))
                            events.append((
                                kind,
                                er,
                                ec,
                                1,
                                f"Merge {len(comps[id1])}+{len(comps[id2])} > K={region_size} -> wall {kind.upper()}({er},{ec})",
                            ))
                            changed = True

            if changed:
                continue

            # 3. Exact-size seal, single-exit growth, reachability & bridge-articulation must-open
            comp_id, comps = compute_components()
            for cid, cells in enumerate(comps):
                csize = len(cells)
                if csize == region_size:
                    for r, c in cells:
                        for k, er, ec in cell_coords(r, c):
                            if get_e(k, er, ec) == 0:
                                set_e(k, er, ec, 1)
                                trail.append((k, er, ec))
                                events.append((k, er, ec, 1, f"Completed region K={region_size} -> seal {k.upper()}({er},{ec})"))
                                changed = True
                    continue
                # Find undecided boundary edges out of this component to compatible neighbor components
                exits: List[Tuple[str, int, int]] = []
                for r, c in cells:
                    for k, er, ec in cell_coords(r, c):
                        if get_e(k, er, ec) == 0:
                            pair = edge_cells(k, er, ec)
                            if pair is None:
                                continue
                            u, w = pair
                            oid = comp_id[w[0]][w[1]] if u == (r, c) else comp_id[u[0]][u[1]]
                            if oid != cid and csize + len(comps[oid]) <= region_size:
                                exits.append((k, er, ec))
                if not exits:
                    return False, events, f"Region of size {csize} < K={region_size} trapped with 0 exits"
                if len(exits) == 1:
                    ek, eer, eec = exits[0]
                    set_e(ek, eer, eec, -1)
                    trail.append((ek, eer, eec))
                    events.append((ek, eer, eec, -1, f"Region size {csize} < K={region_size} single exit -> open {ek.upper()}({eer},{eec})"))
                    changed = True
                    break

                def reachable_without(blocked_edge: Optional[Tuple[str, int, int]]) -> int:
                    seen_comps = {cid}
                    reach_total = csize
                    qc = deque([cid])
                    while qc:
                        cur_c = qc.popleft()
                        for rr, cc in comps[cur_c]:
                            for k, er, ec in cell_coords(rr, cc):
                                if blocked_edge == (k, er, ec) or get_e(k, er, ec) == 1:
                                    continue
                                pair = edge_cells(k, er, ec)
                                if pair is None:
                                    continue
                                u, w = pair
                                oid = comp_id[w[0]][w[1]] if u == (rr, cc) else comp_id[u[0]][u[1]]
                                if oid not in seen_comps:
                                    seen_comps.add(oid)
                                    reach_total += len(comps[oid])
                                    qc.append(oid)
                    return reach_total

                if reachable_without(None) < region_size:
                    return False, events, f"Stranded cluster < K={region_size} cells"

                # Bridge / Articulation Check: if closing exit e strands component < K, e MUST be OPEN
                for ex in exits:
                    if reachable_without(ex) < region_size:
                        ek, eer, eec = ex
                        set_e(ek, eer, eec, -1)
                        trail.append((ek, eer, eec))
                        events.append((ek, eer, eec, -1, f"Mandatory bridge for size {csize} < K={region_size} -> open {ek.upper()}({eer},{eec})"))
                        changed = True
                        break
                if changed:
                    break

        return True, events, ""

    def pick_next_edge() -> Optional[Tuple[str, int, int]]:
        best: Optional[Tuple[int, str, int, int]] = None
        for r in range(1, rows):
            for c in range(cols):
                if h[r][c] == 0:
                    score = (1 if clues[r - 1][c] is not None else 0) + (1 if clues[r][c] is not None else 0)
                    cand = (-score, "h", r, c)
                    if best is None or cand < best:
                        best = cand
        for r in range(rows):
            for c in range(1, cols):
                if v[r][c] == 0:
                    score = (1 if clues[r][c - 1] is not None else 0) + (1 if clues[r][c] is not None else 0)
                    cand = (-score, "v", r, c)
                    if best is None or cand < best:
                        best = cand
        return (best[1], best[2], best[3]) if best is not None else None

    init_trail: List[Tuple[str, int, int]] = []
    ok, init_events, init_err = propagate(init_trail)
    for k, r, c, ev_val, reason in init_events:
        if should_abort():
            return
        if ev_val == 1 or "open" in reason:
            yield {
                "type": "deduce",
                "state": snap(False),
                "highlights": {"edge": [k, r, c]},
                "desc": reason,
                "stats": {"walls": count_walls(), "K": region_size},
            }

    if not ok:
        yield {
            "type": "failed",
            "state": snap(False),
            "highlights": {},
            "desc": f"Pre-search contradiction: {init_err}.",
            "stats": {},
        }
        return

    stats = {"branches": 0, "backtracks": 0}
    stalled_emitted = False

    def solve_gen() -> Generator[Tuple[str, Optional[Tuple[str, int, int]], str], None, bool]:
        nonlocal stalled_emitted
        nxt = pick_next_edge()
        if nxt is None:
            return is_solved()
        kind, er, ec = nxt
        for val in (1, -1):
            if should_abort():
                return False
            stats["branches"] += 1
            trail: List[Tuple[str, int, int]] = [(kind, er, ec)]
            set_e(kind, er, ec, val)
            label = "WALL" if val == 1 else "OPEN"
            prefix = "Deduction stalled -> " if not stalled_emitted else ""
            stalled_emitted = True
            yield ("explore", (kind, er, ec), f"{prefix}Branch {kind.upper()}({er},{ec}) = {label}")
            ok_sub, events, err = propagate(trail)
            for k, r, c, ev_val, reason in events:
                if ev_val == 1:
                    yield ("deduce", (k, r, c), reason)
            if ok_sub:
                solved = yield from solve_gen()
                if solved:
                    return True
            else:
                stats["backtracks"] += 1
                yield ("backtrack", (kind, er, ec), f"Contradiction ({err}) -> backtrack {kind.upper()}({er},{ec})")
            for tk, tr, tc in trail:
                set_e(tk, tr, tc, 0)
        return False

    found = False
    gen = solve_gen()
    try:
        while True:
            if should_abort():
                return
            stype, edge_ref, desc = next(gen)
            yield {
                "type": stype,
                "state": snap(False),
                "highlights": {"edge": list(edge_ref)} if edge_ref else {},
                "desc": desc,
                "stats": {"walls": count_walls(), **stats},
            }
    except StopIteration as stop:
        found = bool(stop.value)

    if should_abort():
        return

    if not found:
        yield {
            "type": "failed",
            "state": snap(False),
            "highlights": {},
            "desc": "No valid Palisade partition exists.",
            "stats": stats,
        }
        return

    yield {
        "type": "solution",
        "state": snap(True),
        "highlights": {},
        "desc": f"Solved {rows}x{cols} Palisade (K={region_size}, {count_walls()} internal walls, {stats['branches']} branches)",
        "stats": {"walls": count_walls(), "K": region_size, **stats},
    }
