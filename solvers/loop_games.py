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
    "params": [
        {
            "key": "assume_unique",
            "label": "Assume Unique Solution",
            "type": "bool",
            "default": False,
        }
    ],
}


def _solve_slitherlink(
    rows: int,
    cols: int,
    clues: List[List[Optional[int]]],
    should_abort: Callable[[], bool],
    assume_unique: bool = False,
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

    def propagate(
        trail: List[Tuple[str, int, int]],
        allow_lookahead: bool = True,
        record_events: bool = True,
    ) -> Tuple[bool, List[Tuple[str, int, int, int, str, Optional[Dict[str, Any]], int]], str]:
        """Propagate cell clues, vertex degrees, and Slitherlink theorems one tier at a time."""
        events: List[Tuple[str, int, int, int, str, Optional[Dict[str, Any]], int]] = []

        def force(kind: str, er: int, ec: int, val: int, reason: str) -> Optional[bool]:
            cur_v = get_edge(kind, er, ec)
            if cur_v == val:
                return False
            if cur_v == -val:
                return None  # contradiction
            set_edge(kind, er, ec, val)
            trail.append((kind, er, ec))
            if record_events:
                events.append((kind, er, ec, val, reason, snap(), count_on()))
            return True

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
                                    res = force(k, er, ec, -1, f"Cell ({r + 1},{c + 1})={clue} satisfied -> {k.upper()}({er},{ec}) OFF")
                                    if res is None:
                                        return False, events, "Contradiction"
                                    if res:
                                        changed = True
                        elif ones + unk == clue:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    res = force(k, er, ec, 1, f"Cell ({r + 1},{c + 1})={clue} needs {unk} remaining -> {k.upper()}({er},{ec}) ON")
                                    if res is None:
                                        return False, events, "Contradiction"
                                    if res:
                                        changed = True

            # Tier 1b: Base Vertex Degree Rules (Tails dissolve, 1-open connects, deg-2 caps)
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
                                    r_f = force(k, er, ec, -1, f"Vertex ({vr},{vc}) degree 2 -> {k.upper()}({er},{ec}) OFF")
                                    if r_f is None: return False, events, "Contradiction"
                                    if r_f: changed = True
                        elif ones == 1 and unk == 1:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    r_f = force(k, er, ec, 1, f"Vertex ({vr},{vc}) degree 1 with 1 open edge -> {k.upper()}({er},{ec}) ON")
                                    if r_f is None: return False, events, "Contradiction"
                                    if r_f: changed = True
                        elif ones == 0 and unk == 1:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    r_f = force(k, er, ec, -1, f"Vertex ({vr},{vc}) isolated (1 open edge) -> {k.upper()}({er},{ec}) OFF")
                                    if r_f is None: return False, events, "Contradiction"
                                    if r_f: changed = True

            if changed:
                continue

            # Slitherlink deterministic theorems (Tier 2: only when Tier 1 base sweep made no changes)
            # A. Grid Corners (for rows >= 2 and cols >= 2)
            if rows >= 2 and cols >= 2:
                corners = [
                    (0, 0, ("h", 0, 0), ("v", 0, 0), ("h", 0, 1), ("v", 1, 0)),
                    (0, cols - 1, ("h", 0, cols - 1), ("v", 0, cols), ("h", 0, cols - 2), ("v", 1, cols)),
                    (rows - 1, 0, ("h", rows, 0), ("v", rows - 1, 0), ("h", rows, 1), ("v", rows - 2, 0)),
                    (rows - 1, cols - 1, ("h", rows, cols - 1), ("v", rows - 1, cols), ("h", rows, cols - 2), ("v", rows - 2, cols)),
                ]
                for cr, cc, e_h, e_v, adj_h, adj_v in corners:
                    cl = clues[cr][cc]
                    if cl == 3:
                        for ek, er, ec in (e_h, e_v):
                            r_f = force(ek, er, ec, 1, f"Corner 3 at ({cr+1},{cc+1}) -> outer {ek.upper()}({er},{ec}) ON")
                            if r_f is None: return False, events, f"Corner 3 contradiction at ({cr+1},{cc+1})"
                            if r_f: changed = True
                    elif cl == 1:
                        for ek, er, ec in (e_h, e_v):
                            r_f = force(ek, er, ec, -1, f"Corner 1 at ({cr+1},{cc+1}) -> outer {ek.upper()}({er},{ec}) OFF")
                            if r_f is None: return False, events, f"Corner 1 contradiction at ({cr+1},{cc+1})"
                            if r_f: changed = True
                    elif cl == 2:
                        for ek, er, ec in (adj_h, adj_v):
                            r_f = force(ek, er, ec, 1, f"Corner 2 at ({cr+1},{cc+1}) -> adjacent outer {ek.upper()}({er},{ec}) ON")
                            if r_f is None: return False, events, f"Corner 2 contradiction at ({cr+1},{cc+1})"
                            if r_f: changed = True

            # B. Adjacent 3-3 (Horizontal & Vertical) and Diagonal 3-3
            for r in range(rows):
                for c in range(cols):
                    if clues[r][c] != 3:
                        continue
                    # Horizontal 3-3
                    if c + 1 < cols and clues[r][c + 1] == 3:
                        reqs = [("v", r, c, 1), ("v", r, c + 1, 1), ("v", r, c + 2, 1)]
                        if r > 0:
                            reqs.append(("v", r - 1, c + 1, -1))
                        if r + 1 < rows:
                            reqs.append(("v", r + 1, c + 1, -1))
                        for ek, er, ec, ev in reqs:
                            r_f = force(ek, er, ec, ev, f"Adjacent 3-3 at ({r+1},{c+1})-({r+1},{c+2})")
                            if r_f is None: return False, events, f"Adjacent 3-3 contradiction at ({r+1},{c+1})"
                            if r_f: changed = True
                    # Vertical 3-3
                    if r + 1 < rows and clues[r + 1][c] == 3:
                        reqs = [("h", r, c, 1), ("h", r + 1, c, 1), ("h", r + 2, c, 1)]
                        if c > 0:
                            reqs.append(("h", r + 1, c - 1, -1))
                        if c + 1 < cols:
                            reqs.append(("h", r + 1, c + 1, -1))
                        for ek, er, ec, ev in reqs:
                            r_f = force(ek, er, ec, ev, f"Adjacent 3-3 at ({r+1},{c+1})-({r+2},{c+1})")
                            if r_f is None: return False, events, f"Adjacent 3-3 contradiction at ({r+1},{c+1})"
                            if r_f: changed = True
                    # Diagonal 3-3 (down-right & down-left)
                    if r + 1 < rows and c + 1 < cols and clues[r + 1][c + 1] == 3:
                        for ek, er, ec in (("h", r, c), ("v", r, c), ("h", r + 2, c + 1), ("v", r + 1, c + 2)):
                            r_f = force(ek, er, ec, 1, f"Diagonal 3-3 outer edge {ek.upper()}({er},{ec}) ON")
                            if r_f is None: return False, events, "Diagonal 3-3 contradiction"
                            if r_f: changed = True
                    if r + 1 < rows and c - 1 >= 0 and clues[r + 1][c - 1] == 3:
                        for ek, er, ec in (("h", r, c), ("v", r, c + 1), ("h", r + 2, c - 1), ("v", r + 1, c - 1)):
                            r_f = force(ek, er, ec, 1, f"Diagonal 3-3 outer edge {ek.upper()}({er},{ec}) ON")
                            if r_f is None: return False, events, "Diagonal 3-3 contradiction"
                            if r_f: changed = True

                    # C. 3, 2, 1 Corner Theorems (Umbrella, Bite, Impossible Quota, 2-Symmetry)
                    cell_set = set(cell_coords(r, c))
                    v_checks = [
                        (r, c, (r + 1, c + 1), [("h", r + 1, c), ("v", r, c + 1)]),
                        (r, c + 1, (r + 1, c), [("h", r + 1, c), ("v", r, c)]),
                        (r + 1, c, (r, c + 1), [("h", r, c), ("v", r, c + 1)]),
                        (r + 1, c + 1, (r, c), [("h", r, c), ("v", r, c)]),
                    ]
                    for vr, vc, opp_v, opp_edges in v_checks:
                        ext_edges = [e for e in vertex_coords(vr, vc) if e not in cell_set]
                        in_edges = [e for e in vertex_coords(vr, vc) if e in cell_set]
                        ext_vals = [get_edge(ek, er, ec) for ek, er, ec in ext_edges]
                        if any(ev == 1 for ev in ext_vals):
                            # Umbrella on 3: opposite 2 cell edges ON, and other external edges at this corner OFF
                            for ek, er, ec in opp_edges:
                                r_f = force(ek, er, ec, 1, f"3 Umbrella at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) ON")
                                if r_f is None: return False, events, f"3 Umbrella contradiction at ({r+1},{c+1})"
                                if r_f: changed = True
                            for (ek, er, ec), ev in zip(ext_edges, ext_vals):
                                if ev == 0:
                                    r_f = force(ek, er, ec, -1, f"3 Umbrella at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) OFF")
                                    if r_f is None: return False, events, f"3 Umbrella contradiction at ({r+1},{c+1})"
                                    if r_f: changed = True
                        elif ext_edges and all(ev == -1 for ev in ext_vals):
                            # Both external edges at vertex (vr, vc) are OFF -> both cell edges at (vr, vc) must be ON!
                            for ek, er, ec in in_edges:
                                r_f = force(ek, er, ec, 1, f"3 Isolated Vertex ({vr},{vc}) -> {ek.upper()}({er},{ec}) ON")
                                if r_f is None: return False, events, f"3 Isolated Vertex contradiction at ({r+1},{c+1})"
                                if r_f: changed = True

            # D. General Cell Corner Theorems (1 Bite/Quota, 2 Symmetry, remaining==1 Quota)
            for r in range(rows):
                for c in range(cols):
                    cl = clues[r][c]
                    if cl is None or cl == 0:
                        continue
                    c_coords = cell_coords(r, c)
                    cell_set = set(c_coords)
                    v_corners = [
                        (r, c, (r + 1, c + 1), [("h", r + 1, c), ("v", r, c + 1)]),
                        (r, c + 1, (r + 1, c), [("h", r + 1, c), ("v", r, c)]),
                        (r + 1, c, (r, c + 1), [("h", r, c), ("v", r, c + 1)]),
                        (r + 1, c + 1, (r, c), [("h", r, c), ("v", r, c)]),
                    ]
                    for vr, vc, (ovr, ovc), opp_edges in v_corners:
                        ext_edges = [e for e in vertex_coords(vr, vc) if e not in cell_set]
                        in_edges = [e for e in vertex_coords(vr, vc) if e in cell_set]
                        ext_vals = [get_edge(ek, er, ec) for ek, er, ec in ext_edges]
                        in_vals = [get_edge(ek, er, ec) for ek, er, ec in in_edges]
                        ext_ones = ext_vals.count(1)
                        ext_offs = ext_vals.count(-1)

                        # Isolated corner (all external edges OFF -> in_edges must be both ON or both OFF)
                        if ext_edges and ext_offs == len(ext_edges):
                            if cl == 1:
                                for ek, er, ec in in_edges:
                                    r_f = force(ek, er, ec, -1, f"1 Bite at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) OFF")
                                    if r_f is None: return False, events, f"1 Bite contradiction at ({r+1},{c+1})"
                                    if r_f: changed = True
                            elif cl == 2:
                                if any(iv == 1 for iv in in_vals):
                                    for ek, er, ec in in_edges:
                                        r_f = force(ek, er, ec, 1, f"2 Corner Pair at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) ON")
                                        if r_f is None: return False, events, f"2 Corner contradiction at ({r+1},{c+1})"
                                        if r_f: changed = True
                                elif any(iv == -1 for iv in in_vals):
                                    for ek, er, ec in in_edges:
                                        r_f = force(ek, er, ec, -1, f"2 Corner Pair at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) OFF")
                                        if r_f is None: return False, events, f"2 Corner contradiction at ({r+1},{c+1})"
                                        if r_f: changed = True
                                    for ek, er, ec in opp_edges:
                                        r_f = force(ek, er, ec, 1, f"2 Corner Pair at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) ON")
                                        if r_f is None: return False, events, f"2 Corner contradiction at ({r+1},{c+1})"
                                        if r_f: changed = True

                        # Forced chain entering corner (exactly 1 ext ON, all other ext OFF -> in_edges contribute 1 ON)
                        if ext_ones == 1 and ext_ones + ext_offs == len(ext_edges):
                            if cl == 1:
                                for ek, er, ec in opp_edges:
                                    r_f = force(ek, er, ec, -1, f"1 Quota at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) OFF")
                                    if r_f is None: return False, events, f"1 Quota contradiction at ({r+1},{c+1})"
                                    if r_f: changed = True
                            elif cl == 2:
                                opp_ext = [e for e in vertex_coords(ovr, ovc) if e not in cell_set]
                                opp_ext_vals = [get_edge(ek, er, ec) for ek, er, ec in opp_ext]
                                if opp_ext_vals.count(-1) == len(opp_ext) - 1 and opp_ext_vals.count(0) == 1:
                                    for (ek, er, ec), ev in zip(opp_ext, opp_ext_vals):
                                        if ev == 0:
                                            r_f = force(ek, er, ec, 1, f"2 Symmetry branch at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) ON")
                                            if r_f is None: return False, events, f"2 Symmetry contradiction at ({r+1},{c+1})"
                                            if r_f: changed = True
                                elif opp_ext and opp_ext_vals.count(-1) == len(opp_ext):
                                    return False, events, f"2 Symmetry contradiction at ({r+1},{c+1})"

                        # Any external ON edge touching a 2 whose opposite corner is isolated forces opposite corner ON
                        if cl == 2 and ext_ones >= 1:
                            opp_ext = [e for e in vertex_coords(ovr, ovc) if e not in cell_set]
                            if opp_ext and all(get_edge(ek, er, ec) == -1 for ek, er, ec in opp_ext):
                                for ek, er, ec in opp_edges:
                                    r_f = force(ek, er, ec, 1, f"2 Corner-Push at ({r+1},{c+1}) -> {ek.upper()}({er},{ec}) ON")
                                    if r_f is None: return False, events, f"2 Corner-Push contradiction at ({r+1},{c+1})"
                                    if r_f: changed = True

            if changed:
                continue

            # Tier 3: Topological Helpers (Inside/Outside parity, Pangea, Connecting Rivers, Cycle-Bridge, Premature Loop)

            # E. Inside/Outside (Jordan Curve 2-Color Parity)
            ext_node = rows * cols
            uf_parent = list(range(ext_node + 1))
            uf_parity = [0] * (ext_node + 1)

            def uf_find(x: int) -> Tuple[int, int]:
                p = 0
                while uf_parent[x] != x:
                    p ^= uf_parity[x]
                    x = uf_parent[x]
                return x, p

            def uf_union(u: int, v: int, w: int) -> bool:
                ru, pu = uf_find(u)
                rv, pv = uf_find(v)
                if ru == rv:
                    return (pu ^ pv) == w
                uf_parent[rv] = ru
                uf_parity[rv] = pu ^ pv ^ w
                return True

            for r in range(rows + 1):
                for c in range(cols):
                    if h[r][c] != 0:
                        u = (r - 1) * cols + c if r > 0 else ext_node
                        v_n = r * cols + c if r < rows else ext_node
                        w = 1 if h[r][c] == 1 else 0
                        if not uf_union(u, v_n, w):
                            return False, events, f"Inside/Outside parity contradiction at H({r},{c})"
            for r in range(rows):
                for c in range(cols + 1):
                    if v[r][c] != 0:
                        u = r * cols + (c - 1) if c > 0 else ext_node
                        v_n = r * cols + c if c < cols else ext_node
                        w = 1 if v[r][c] == 1 else 0
                        if not uf_union(u, v_n, w):
                            return False, events, f"Inside/Outside parity contradiction at V({r},{c})"

            for r in range(rows + 1):
                for c in range(cols):
                    if h[r][c] == 0:
                        u = (r - 1) * cols + c if r > 0 else ext_node
                        v_n = r * cols + c if r < rows else ext_node
                        ru, pu = uf_find(u)
                        rv, pv = uf_find(v_n)
                        if ru == rv:
                            val = 1 if (pu ^ pv) == 1 else -1
                            lbl = "ON" if val == 1 else "OFF"
                            r_f = force("h", r, c, val, f"Inside/Outside parity -> H({r},{c}) {lbl}")
                            if r_f is None: return False, events, "Inside/Outside parity contradiction"
                            if r_f: changed = True
            for r in range(rows):
                for c in range(cols + 1):
                    if v[r][c] == 0:
                        u = r * cols + (c - 1) if c > 0 else ext_node
                        v_n = r * cols + c if c < cols else ext_node
                        ru, pu = uf_find(u)
                        rv, pv = uf_find(v_n)
                        if ru == rv:
                            val = 1 if (pu ^ pv) == 1 else -1
                            lbl = "ON" if val == 1 else "OFF"
                            r_f = force("v", r, c, val, f"Inside/Outside parity -> V({r},{c}) {lbl}")
                            if r_f is None: return False, events, "Inside/Outside parity contradiction"
                            if r_f: changed = True

            # E2. Same-Color Neighbor Coupling & Opposite-Color Pair on cell quotas
            for r in range(rows):
                for c in range(cols):
                    cl = clues[r][c]
                    if cl is None:
                        continue
                    c_coords = cell_coords(r, c)
                    ones_c = sum(1 for k, er, ec in c_coords if get_edge(k, er, ec) == 1)
                    unk_es = [(k, er, ec) for k, er, ec in c_coords if get_edge(k, er, ec) == 0]
                    unk_cnt = len(unk_es)
                    if unk_cnt < 2:
                        continue
                    rem = cl - ones_c
                    by_color: Dict[Tuple[int, int], List[Tuple[str, int, int]]] = {}
                    seen_pair: Dict[int, List[Tuple[Tuple[str, int, int], int]]] = {}
                    opp_pair: Optional[Tuple[Tuple[str, int, int], Tuple[str, int, int]]] = None
                    for ek, er, ec in unk_es:
                        if ek == "h":
                            nb = (er - 1) * cols + ec if er == r + 0 and er > 0 else (er * cols + ec if er == r + 1 and er < rows else ext_node)
                        else:
                            nb = r * cols + (ec - 1) if ec == c and ec > 0 else (r * cols + ec if ec == c + 1 and ec < cols else ext_node)
                        rn, pn = uf_find(nb)
                        by_color.setdefault((rn, pn), []).append((ek, er, ec))
                        lst = seen_pair.setdefault(rn, [])
                        if opp_pair is None:
                            for oedge, op in lst:
                                if op != pn:
                                    opp_pair = (oedge, (ek, er, ec))
                                    break
                        lst.append(((ek, er, ec), pn))

                    for same_es in by_color.values():
                        k_same = len(same_es)
                        if k_same >= 2:
                            if rem < k_same:
                                for ek, er, ec in same_es:
                                    rf = force(ek, er, ec, -1, f"Same-color coupling at ({r+1},{c+1})={cl} -> {ek.upper()}({er},{ec}) OFF")
                                    if rf is None: return False, events, "Same-color coupling contradiction"
                                    if rf: changed = True
                            elif unk_cnt - rem < k_same:
                                for ek, er, ec in same_es:
                                    rf = force(ek, er, ec, 1, f"Same-color coupling at ({r+1},{c+1})={cl} -> {ek.upper()}({er},{ec}) ON")
                                    if rf is None: return False, events, "Same-color coupling contradiction"
                                    if rf: changed = True

                    if opp_pair is not None and unk_cnt > 2:
                        if rem == 1:
                            for ek, er, ec in unk_es:
                                if (ek, er, ec) not in opp_pair and get_edge(ek, er, ec) == 0:
                                    rf = force(ek, er, ec, -1, f"A|B parity pair at ({r+1},{c+1})={cl} -> {ek.upper()}({er},{ec}) OFF")
                                    if rf is None: return False, events, "A|B parity pair contradiction"
                                    if rf: changed = True
                        elif unk_cnt - rem == 1:
                            for ek, er, ec in unk_es:
                                if (ek, er, ec) not in opp_pair and get_edge(ek, er, ec) == 0:
                                    rf = force(ek, er, ec, 1, f"A|B parity pair at ({r+1},{c+1})={cl} -> {ek.upper()}({er},{ec}) ON")
                                    if rf is None: return False, events, "A|B parity pair contradiction"
                                    if rf: changed = True

            # F. Premature Loop Avoidance on open chain endpoints
            adj_on: Dict[Tuple[int, int], List[Tuple[int, int]]] = {}
            total_on = 0
            for r in range(rows + 1):
                for c in range(cols):
                    if h[r][c] == 1:
                        total_on += 1
                        adj_on.setdefault((r, c), []).append((r, c + 1))
                        adj_on.setdefault((r, c + 1), []).append((r, c))
            for r in range(rows):
                for c in range(cols + 1):
                    if v[r][c] == 1:
                        total_on += 1
                        adj_on.setdefault((r, c), []).append((r + 1, c))
                        adj_on.setdefault((r + 1, c), []).append((r, c))

            if total_on > 0:
                comp_id: Dict[Tuple[int, int], int] = {}
                comp_edges_cnt: Dict[int, int] = {}
                cid = 0
                for start_v in adj_on:
                    if start_v in comp_id:
                        continue
                    stack = [start_v]
                    comp_id[start_v] = cid
                    ecount = 0
                    while stack:
                        cur = stack.pop()
                        for nb in adj_on[cur]:
                            ecount += 1
                            if nb not in comp_id:
                                comp_id[nb] = cid
                                stack.append(nb)
                    comp_edges_cnt[cid] = ecount // 2
                    cid += 1

                any_clue_unsat = any(
                    clues[r][c] is not None and clues[r][c] > 0
                    and sum(1 for k, er, ec in cell_coords(r, c) if get_edge(k, er, ec) == 1) < clues[r][c]
                    for r in range(rows) for c in range(cols)
                )
                for r in range(rows + 1):
                    for c in range(cols):
                        if h[r][c] == 0:
                            u, v_pt = (r, c), (r, c + 1)
                            if u in comp_id and comp_id.get(v_pt) == comp_id[u]:
                                if comp_edges_cnt[comp_id[u]] < total_on or any_clue_unsat:
                                    r_f = force("h", r, c, -1, f"Avoid premature loop -> H({r},{c}) OFF")
                                    if r_f is None: return False, events, "Premature loop contradiction"
                                    if r_f: changed = True
                for r in range(rows):
                    for c in range(cols + 1):
                        if v[r][c] == 0:
                            u, v_pt = (r, c), (r + 1, c)
                            if u in comp_id and comp_id.get(v_pt) == comp_id[u]:
                                if comp_edges_cnt[comp_id[u]] < total_on or any_clue_unsat:
                                    r_f = force("v", r, c, -1, f"Avoid premature loop -> V({r},{c}) OFF")
                                    if r_f is None: return False, events, "Premature loop contradiction"
                                    if r_f: changed = True

            # G. Pangea (No-Islands Connectivity + A|B Inside/Outside Reachability + Bridge Check)
            pass_adj: List[List[Tuple[int, Optional[Tuple[str, int, int]]]]] = [[] for _ in range(ext_node + 1)]
            for r in range(rows + 1):
                for c in range(cols):
                    if h[r][c] != 1:
                        u = (r - 1) * cols + c if r > 0 else ext_node
                        v_n = r * cols + c if r < rows else ext_node
                        eref = ("h", r, c) if h[r][c] == 0 else None
                        pass_adj[u].append((v_n, eref))
                        pass_adj[v_n].append((u, eref))
            for r in range(rows):
                for c in range(cols + 1):
                    if v[r][c] != 1:
                        u = r * cols + (c - 1) if c > 0 else ext_node
                        v_n = r * cols + c if c < cols else ext_node
                        eref = ("v", r, c) if v[r][c] == 0 else None
                        pass_adj[u].append((v_n, eref))
                        pass_adj[v_n].append((u, eref))

            known_state = [-1] * (ext_node + 1)  # -1 = unknown, 0 = OUTSIDE, 1 = INSIDE
            known_state[ext_node] = 0
            ab_groups: Dict[int, Tuple[List[int], List[int]]] = {}
            in_cells: List[int] = []
            out_cells: List[int] = []
            for cell_id in range(ext_node):
                rc, pc = uf_find(cell_id)
                if rc == ext_node:
                    known_state[cell_id] = pc
                    if pc == 1:
                        in_cells.append(cell_id)
                    else:
                        out_cells.append(cell_id)
                else:
                    g0, g1 = ab_groups.setdefault(rc, ([], []))
                    (g1 if pc == 1 else g0).append(cell_id)

            def bfs_passable(start: int, forbidden: int) -> List[bool]:
                vis = [False] * (ext_node + 1)
                if known_state[start] == forbidden:
                    return vis
                vis[start] = True
                q = [start]
                qi = 0
                while qi < len(q):
                    cur = q[qi]
                    qi += 1
                    for nb, _ in pass_adj[cur]:
                        if not vis[nb] and known_state[nb] != forbidden:
                            vis[nb] = True
                            q.append(nb)
                return vis

            reach_ext = bfs_passable(ext_node, 1)
            for oc in out_cells:
                if not reach_ext[oc]:
                    return False, events, f"Isolated OUTSIDE cell ({oc // cols + 1},{oc % cols + 1})"

            reach_in: Optional[List[bool]] = None
            if in_cells:
                reach_in = bfs_passable(in_cells[0], 0)
                for ic in in_cells[1:]:
                    if not reach_in[ic]:
                        return False, events, f"Disconnected INSIDE island at ({ic // cols + 1},{ic % cols + 1})"

            def resolve_uf_edges(why_prefix: str) -> bool:
                nonlocal changed
                for r in range(rows + 1):
                    for c in range(cols):
                        if h[r][c] == 0:
                            u = (r - 1) * cols + c if r > 0 else ext_node
                            v_n = r * cols + c if r < rows else ext_node
                            ru, pu = uf_find(u)
                            rv, pv = uf_find(v_n)
                            if ru == rv:
                                val = 1 if (pu ^ pv) == 1 else -1
                                lbl = "ON" if val == 1 else "OFF"
                                r_f = force("h", r, c, val, f"{why_prefix} -> H({r},{c}) {lbl}")
                                if r_f is None: return False
                                if r_f: changed = True
                for r in range(rows):
                    for c in range(cols + 1):
                        if v[r][c] == 0:
                            u = r * cols + (c - 1) if c > 0 else ext_node
                            v_n = r * cols + c if c < cols else ext_node
                            ru, pu = uf_find(u)
                            rv, pv = uf_find(v_n)
                            if ru == rv:
                                val = 1 if (pu ^ pv) == 1 else -1
                                lbl = "ON" if val == 1 else "OFF"
                                r_f = force("v", r, c, val, f"{why_prefix} -> V({r},{c}) {lbl}")
                                if r_f is None: return False
                                if r_f: changed = True
                return True

            # Resolve A|B components that cannot reach EXTERIOR (must be INSIDE) or INSIDE (must be OUTSIDE)
            ab_resolved = False
            for root_c, (g0, g1) in ab_groups.items():
                g0_can_out = all(reach_ext[x] for x in g0)
                g1_can_out = all(reach_ext[x] for x in g1)
                g0_can_in = True if reach_in is None else all(reach_in[x] for x in g0)
                g1_can_in = True if reach_in is None else all(reach_in[x] for x in g1)

                force_g0: Optional[int] = None
                if not g0_can_out and not g1_can_out:
                    return False, events, "Pangea A|B contradiction: neither polarity can reach EXTERIOR"
                if not g0_can_in and not g1_can_in:
                    return False, events, "Pangea A|B contradiction: neither polarity can reach INSIDE"
                if not g0_can_out or not g1_can_in:
                    force_g0 = 1
                elif not g1_can_out or not g0_can_in:
                    force_g0 = 0
                if force_g0 is not None:
                    if uf_union(root_c, ext_node, force_g0):
                        ab_resolved = True
                        for x in g0:
                            known_state[x] = force_g0
                            (in_cells if force_g0 == 1 else out_cells).append(x)
                        for x in g1:
                            known_state[x] = 1 - force_g0
                            (in_cells if (1 - force_g0) == 1 else out_cells).append(x)
                    else:
                        return False, events, "Pangea A|B parity contradiction"

            # Connecting Rivers / Cut-Vertex Check:
            # 1) On LandGraph (known_state != 0): if unknown cell w is a cut-vertex separating two INSIDE cells, w MUST be INSIDE!
            # 2) On WaterGraph (known_state != 1): if unknown cell w is a cut-vertex separating an OUTSIDE cell from ext_node, w MUST be OUTSIDE!
            cut_resolved = False
            if len(in_cells) >= 2:
                l_disc = [-1] * ext_node
                l_low = [0] * ext_node
                l_sub_in = [0] * ext_node
                lt = [0]
                total_in_now = len(in_cells)
                land_cuts: List[int] = []

                def tarjan_land_cut(u: int, p: int) -> None:
                    l_disc[u] = l_low[u] = lt[0]
                    lt[0] += 1
                    l_sub_in[u] = 1 if known_state[u] == 1 else 0
                    separates_in = False
                    for nb, _ in pass_adj[u]:
                        if nb == ext_node or known_state[nb] == 0 or nb == p:
                            continue
                        if l_disc[nb] == -1:
                            tarjan_land_cut(nb, u)
                            l_low[u] = min(l_low[u], l_low[nb])
                            l_sub_in[u] += l_sub_in[nb]
                            if p != -1 and l_low[nb] >= l_disc[u] and 0 < l_sub_in[nb] < total_in_now:
                                separates_in = True
                        else:
                            l_low[u] = min(l_low[u], l_disc[nb])
                    if known_state[u] == -1 and separates_in:
                        land_cuts.append(u)

                tarjan_land_cut(in_cells[0], -1)
                for w in land_cuts:
                    if not uf_union(w, ext_node, 1):
                        return False, events, "Pangea river-cut contradiction"
                    known_state[w] = 1
                    in_cells.append(w)
                    cut_resolved = True

            if out_cells:
                w_disc = [-1] * (ext_node + 1)
                w_low = [0] * (ext_node + 1)
                w_sub_out = [0] * (ext_node + 1)
                wt = [0]
                water_cuts: List[int] = []

                def tarjan_water_cut(u: int, p: int) -> None:
                    w_disc[u] = w_low[u] = wt[0]
                    wt[0] += 1
                    w_sub_out[u] = 1 if (u != ext_node and known_state[u] == 0) else 0
                    separates_out = False
                    for nb, _ in pass_adj[u]:
                        if known_state[nb] == 1 or nb == p:
                            continue
                        if w_disc[nb] == -1:
                            tarjan_water_cut(nb, u)
                            w_low[u] = min(w_low[u], w_low[nb])
                            w_sub_out[u] += w_sub_out[nb]
                            if p != -1 and w_low[nb] >= w_disc[u] and w_sub_out[nb] > 0:
                                separates_out = True
                        else:
                            w_low[u] = min(w_low[u], w_disc[nb])
                    if u != ext_node and known_state[u] == -1 and separates_out:
                        water_cuts.append(u)

                tarjan_water_cut(ext_node, -1)
                for w in water_cuts:
                    if not uf_union(w, ext_node, 0):
                        return False, events, "Pangea land-cut contradiction"
                    known_state[w] = 0
                    out_cells.append(w)
                    cut_resolved = True

            if ab_resolved or cut_resolved:
                if not resolve_uf_edges("Pangea river-cut"):
                    return False, events, "Pangea parity contradiction"

            # Tarjan Bridges on passable (!= 1) graph: an edge separating OUTSIDE from EXTERIOR or INSIDE from INSIDE must be OFF
            total_in_cnt = len(in_cells)
            disc = [-1] * (ext_node + 1)
            low = [0] * (ext_node + 1)
            sub_out = [0] * (ext_node + 1)
            sub_in = [0] * (ext_node + 1)
            t_timer = [0]
            pangea_bridges: List[Tuple[str, int, int, str]] = []

            def tarjan_pangea(u: int, pe_idx: int) -> None:
                disc[u] = low[u] = t_timer[0]
                t_timer[0] += 1
                sub_out[u] = 1 if (u != ext_node and known_state[u] == 0) else 0
                sub_in[u] = 1 if known_state[u] == 1 else 0
                for idx_e, (nb, eref) in enumerate(pass_adj[u]):
                    # Use (min(u,nb), max(u,nb), eref) identity? Grid has at most 1 edge except border-to-ext!
                    # Identify parent edge by (nb, eref) vs parent
                    if idx_e == pe_idx:
                        continue
                    if disc[nb] == -1:
                        # Find reverse index for (nb -> u) matching same eref
                        rev_idx = -1
                        for r_i, (r_nb, r_eref) in enumerate(pass_adj[nb]):
                            if r_nb == u and r_eref == eref and r_i != rev_idx:
                                rev_idx = r_i
                                break
                        tarjan_pangea(nb, rev_idx)
                        low[u] = min(low[u], low[nb])
                        sub_out[u] += sub_out[nb]
                        sub_in[u] += sub_in[nb]
                        if low[nb] > disc[u] and eref is not None:
                            if sub_out[nb] > 0:
                                pangea_bridges.append((eref[0], eref[1], eref[2], "Pangea water bridge"))
                            elif 0 < sub_in[nb] < total_in_cnt:
                                pangea_bridges.append((eref[0], eref[1], eref[2], "Pangea land bridge"))
                    else:
                        low[u] = min(low[u], disc[nb])

            # Note: multiple edges can exist between a corner cell and ext_node; skip only the exact reverse edge!
            # Wait: pass_adj[u] index isn't symmetric unless we track edge_id! Let's use explicit edge_id in pass_adj if needed.
            # Actually, border cells can have 2 edges to ext_node! So let's guard with edge_id to be 100% exact.
            tarjan_pangea(ext_node, -1)
            for ek, er, ec, why in pangea_bridges:
                r_f = force(ek, er, ec, -1, f"{why} -> {ek.upper()}({er},{ec}) OFF")
                if r_f is None: return False, events, f"{why} contradiction"
                if r_f: changed = True

            # H. Cycle-Bridge Check on vertex (!= -1) graph: no ON edge or cycle edge can ever be a bridge!
            v_count = (rows + 1) * (cols + 1)
            v_adj: List[List[Tuple[int, int, str, int, int, int]]] = [[] for _ in range(v_count)]
            eid = 0
            for r in range(rows + 1):
                for c in range(cols):
                    if h[r][c] != -1:
                        u = r * (cols + 1) + c
                        w = u + 1
                        v_adj[u].append((w, eid, "h", r, c, h[r][c]))
                        v_adj[w].append((u, eid, "h", r, c, h[r][c]))
                        eid += 1
            for r in range(rows):
                for c in range(cols + 1):
                    if v[r][c] != -1:
                        u = r * (cols + 1) + c
                        w = u + (cols + 1)
                        v_adj[u].append((w, eid, "v", r, c, v[r][c]))
                        v_adj[w].append((u, eid, "v", r, c, v[r][c]))
                        eid += 1

            v_disc = [-1] * v_count
            v_low = [0] * v_count
            vt = [0]
            cycle_bridges: List[Tuple[str, int, int, int]] = []

            def tarjan_cycle(u: int, peid: int) -> None:
                v_disc[u] = v_low[u] = vt[0]
                vt[0] += 1
                for nb, cur_eid, ek, er, ec, eval_ in v_adj[u]:
                    if cur_eid == peid:
                        continue
                    if v_disc[nb] == -1:
                        tarjan_cycle(nb, cur_eid)
                        v_low[u] = min(v_low[u], v_low[nb])
                        if v_low[nb] > v_disc[u]:
                            cycle_bridges.append((ek, er, ec, eval_))
                    else:
                        v_low[u] = min(v_low[u], v_disc[nb])

            for start_vn in range(v_count):
                if v_disc[start_vn] == -1 and v_adj[start_vn]:
                    tarjan_cycle(start_vn, -1)

            for ek, er, ec, eval_ in cycle_bridges:
                if eval_ == 1:
                    return False, events, f"Stranded bridge ON edge {ek.upper()}({er},{ec})"
                if eval_ == 0:
                    r_f = force(ek, er, ec, -1, f"Stranded bridge (cannot form cycle) -> {ek.upper()}({er},{ec}) OFF")
                    if r_f is None: return False, events, "Stranded bridge contradiction"
                    if r_f: changed = True
        if has_premature_loop():
            return False, events, "Premature closed loop detected"

        # I. 1-Ply Contradiction Lookahead (Nishio): if testing an edge ON/OFF immediately fails propagation, force the opposite
        if allow_lookahead:
            while True:
                if should_abort():
                    return True, events, ""
                cands: List[Tuple[int, str, int, int]] = []
                for r in range(rows + 1):
                    for c in range(cols):
                        if h[r][c] == 0:
                            pr = 0
                            if any(get_edge(k, er, ec) == 1 for k, er, ec in vertex_coords(r, c) + vertex_coords(r, c + 1)):
                                pr += 10
                            if (r > 0 and clues[r - 1][c] is not None) or (r < rows and clues[r][c] is not None):
                                pr += 2
                            cands.append((-pr, "h", r, c))
                for r in range(rows):
                    for c in range(cols + 1):
                        if v[r][c] == 0:
                            pr = 0
                            if any(get_edge(k, er, ec) == 1 for k, er, ec in vertex_coords(r, c) + vertex_coords(r + 1, c)):
                                pr += 10
                            if (c > 0 and clues[r][c - 1] is not None) or (c < cols and clues[r][c] is not None):
                                pr += 2
                            cands.append((-pr, "v", r, c))
                cands.sort()
                forced_any = False
                for _, ek, er, ec in cands:
                    if should_abort():
                        return True, events, ""
                    if get_edge(ek, er, ec) != 0:
                        continue
                    ok_vals: List[int] = []
                    fail_reasons: Dict[int, str] = {}
                    for test_v in (1, -1):
                        tmp_trail: List[Tuple[str, int, int]] = [(ek, er, ec)]
                        set_edge(ek, er, ec, test_v)
                        t_ok, _, t_err = propagate(tmp_trail, allow_lookahead=False, record_events=False)
                        for tk, tr, tc in tmp_trail:
                            set_edge(tk, tr, tc, 0)
                        if t_ok:
                            ok_vals.append(test_v)
                        else:
                            fail_reasons[test_v] = t_err
                    if not ok_vals:
                        return False, events, f"1-ply contradiction on {ek.upper()}({er},{ec})"
                    if len(ok_vals) == 1:
                        win_v = ok_vals[0]
                        lose_lbl = "OFF" if win_v == 1 else "ON"
                        win_lbl = "ON" if win_v == 1 else "OFF"
                        r_f = force(ek, er, ec, win_v, f"Lookahead ({ek.upper()}({er},{ec})={lose_lbl} -> {fail_reasons[-win_v]}) -> {win_lbl}")
                        if r_f is None:
                            return False, events, "Lookahead contradiction"
                        if r_f:
                            sub_ok, sub_ev, sub_err = propagate(trail, allow_lookahead=False, record_events=True)
                            events.extend(sub_ev)
                            if not sub_ok:
                                return False, events, sub_err
                            forced_any = True
                            break
                if not forced_any:
                    break
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

    def group_events(
        raw: List[Tuple[str, int, int, int, str, Optional[Dict[str, Any]], int]]
    ) -> List[Tuple[List[Tuple[str, int, int]], str, Dict[str, Any], int]]:
        """Group consecutive deductions from the same local rule firing into a single step."""
        no_group = {"Inside/Outside parity", "Stranded bridge (cannot form cycle)", "Avoid premature loop", "Pangea river-cut"}
        grouped: List[Tuple[List[Tuple[str, int, int]], str, Dict[str, Any], int]] = []
        cur_key: Optional[str] = None
        cur_edges: List[Tuple[str, int, int]] = []
        cur_labels: List[str] = []
        cur_snap: Dict[str, Any] = {}
        cur_seg = 0
        for k, r, c, ev_val, reason, ev_snap, ev_seg in raw:
            prefix = reason.split(" -> ")[0]
            can_group = prefix not in no_group
            lbl = f"{k.upper()}({r},{c}) {'ON' if ev_val == 1 else 'OFF'}"
            if can_group and cur_key == prefix:
                cur_edges.append((k, r, c))
                cur_labels.append(lbl)
                cur_snap = ev_snap or snap()
                cur_seg = ev_seg
            else:
                if cur_edges:
                    desc = f"{cur_key} -> {', '.join(cur_labels)}" if len(cur_edges) > 1 else cur_first_reason
                    grouped.append((cur_edges, desc, cur_snap, cur_seg))
                cur_key = prefix if can_group else None
                cur_first_reason = reason
                cur_edges = [(k, r, c)]
                cur_labels = [lbl]
                cur_snap = ev_snap or snap()
                cur_seg = ev_seg
        if cur_edges:
            desc = f"{cur_key} -> {', '.join(cur_labels)}" if (cur_key and len(cur_edges) > 1) else cur_first_reason
            grouped.append((cur_edges, desc, cur_snap, cur_seg))
        return grouped

    yield {
        "type": "start",
        "state": snap(),
        "highlights": {},
        "desc": f"Loaded {rows}x{cols} Slitherlink lattice",
        "stats": {"rows": rows, "cols": cols, "segments": 0, "branches": 0, "backtracks": 0},
    }

    stats = {"branches": 0, "backtracks": 0}
    stalled_emitted = False

    def solve_gen() -> Generator[Tuple[str, List[Tuple[str, int, int]], str, Dict[str, Any], int], None, bool]:
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
            yield ("explore", [(kind, er, ec)], f"{prefix}Branch {kind.upper()}({er},{ec}) = {label}", snap(), count_on())
            ok, events, err = propagate(trail)
            for edges_grp, reason, ev_snap, ev_seg in group_events(events):
                yield ("deduce", edges_grp, reason, ev_snap, ev_seg)
            if ok:
                solved = yield from solve_gen()
                if solved:
                    return True
            else:
                stats["backtracks"] += 1
                yield ("backtrack", [(kind, er, ec)], f"Contradiction ({err}) -> backtrack {kind.upper()}({er},{ec})", snap(), count_on())
            for tk, tr, tc in trail:
                set_edge(tk, tr, tc, 0)
        return False

    init_trail: List[Tuple[str, int, int]] = []
    ok, init_events, init_err = propagate(init_trail)
    for edges_grp, reason, ev_snap, ev_seg in group_events(init_events):
        if should_abort():
            return
        yield {
            "type": "deduce",
            "state": ev_snap,
            "highlights": {"edges": [list(e) for e in edges_grp]},
            "desc": reason,
            "stats": {"segments": ev_seg, "branches": 0, "backtracks": 0},
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
            stype, edge_refs, desc, step_snap, step_seg = next(gen)
            yield {
                "type": stype,
                "state": step_snap,
                "highlights": {"edges": [list(e) for e in edge_refs]} if edge_refs else {},
                "desc": desc,
                "stats": {"segments": step_seg, **stats},
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
    assume_unique = bool(params.get("assume_unique", False))
    yield from _solve_slitherlink(rows, cols, clues, should_abort, assume_unique=assume_unique)
