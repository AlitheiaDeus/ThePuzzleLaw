"""Slitherlink single-loop solver using vertex-degree & clue backtracking."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "loop_games",
    "name": "Loop Family (Slitherlink)",
    "category": "Loops & Boundaries",
    "renderer": "custom",
    "custom_view": "/renderers/custom/loop_board.js",
    "description": "Solves Slitherlink single-loop lattice puzzles with numerical cell clues (0-3).",
    "presets": {
        "4x4": {
            "size": 4,
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
            "size": 5,
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
    size: int,
    clues: List[List[Optional[int]]],
    should_abort: Callable[[], bool],
) -> Optional[Tuple[List[List[int]], List[List[int]]]]:
    h = [[0] * size for _ in range(size + 1)]
    v = [[0] * (size + 1) for _ in range(size)]

    def cell_coords(r: int, c: int) -> List[Tuple[str, int, int]]:
        return [("h", r, c), ("h", r + 1, c), ("v", r, c), ("v", r, c + 1)]

    def vertex_coords(vr: int, vc: int) -> List[Tuple[str, int, int]]:
        out: List[Tuple[str, int, int]] = []
        if vc > 0:
            out.append(("h", vr, vc - 1))
        if vc < size:
            out.append(("h", vr, vc))
        if vr > 0:
            out.append(("v", vr - 1, vc))
        if vr < size:
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
        for r in range(size + 1):
            for c in range(size):
                if h[r][c] == 1:
                    adj.setdefault((r, c), []).append((r, c + 1))
                    adj.setdefault((r, c + 1), []).append((r, c))
        for r in range(size):
            for c in range(size + 1):
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
        for r in range(size + 1):
            for c in range(size):
                if h[r][c] == 1:
                    edge_count += 1
                    adj.setdefault((r, c), []).append((r, c + 1))
                    adj.setdefault((r, c + 1), []).append((r, c))
        for r in range(size):
            for c in range(size + 1):
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
                # Closed loop found! Valid only if it uses ALL 1-edges and all remaining cells can be 0
                comp_edges = sum(len(adj[u]) for u in comp) // 2
                if comp_edges < edge_count:
                    return True
                # Also if any clue > 0 has 0 edges in this loop and no way to be satisfied without a second loop
                for r in range(size):
                    for c in range(size):
                        clue = clues[r][c]
                        if clue is not None and clue > 0:
                            vals = [get_edge(k, er, ec) for k, er, ec in cell_coords(r, c)]
                            if vals.count(1) < clue:
                                return True
        return False

    def propagate(trail: List[Tuple[str, int, int]]) -> bool:
        """Propagate cell clue and vertex degree constraints, recording assigned edges in trail."""
        changed = True
        while changed:
            changed = False
            for r in range(size):
                for c in range(size):
                    clue = clues[r][c]
                    if clue is None:
                        continue
                    coords = cell_coords(r, c)
                    vals = [get_edge(k, er, ec) for k, er, ec in coords]
                    ones = vals.count(1)
                    unk = vals.count(0)
                    if ones > clue or ones + unk < clue:
                        return False
                    if unk > 0:
                        if ones == clue:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, -1)
                                    trail.append((k, er, ec))
                                    changed = True
                        elif ones + unk == clue:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, 1)
                                    trail.append((k, er, ec))
                                    changed = True

            for vr in range(size + 1):
                for vc in range(size + 1):
                    coords = vertex_coords(vr, vc)
                    vals = [get_edge(k, er, ec) for k, er, ec in coords]
                    ones = vals.count(1)
                    unk = vals.count(0)
                    if ones > 2 or (unk == 0 and ones == 1):
                        return False
                    if unk > 0:
                        if ones == 2:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, -1)
                                    trail.append((k, er, ec))
                                    changed = True
                        elif ones == 1 and unk == 1:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, 1)
                                    trail.append((k, er, ec))
                                    changed = True
                        elif ones == 0 and unk == 1:
                            for (k, er, ec), val in zip(coords, vals):
                                if val == 0:
                                    set_edge(k, er, ec, -1)
                                    trail.append((k, er, ec))
                                    changed = True
        return not has_premature_loop()

    def pick_next_edge() -> Optional[Tuple[str, int, int]]:
        best: Optional[Tuple[int, str, int, int]] = None
        for r in range(size + 1):
            for c in range(size):
                if h[r][c] == 0:
                    score = 0
                    if r > 0 and clues[r - 1][c] is not None:
                        score += 4 - abs(clues[r - 1][c] - 2)
                    if r < size and clues[r][c] is not None:
                        score += 4 - abs(clues[r][c] - 2)
                    if any(get_edge(k, er, ec) == 1 for k, er, ec in vertex_coords(r, c) + vertex_coords(r, c + 1)):
                        score += 10
                    cand = (-score, "h", r, c)
                    if best is None or cand < best:
                        best = cand
        for r in range(size):
            for c in range(size + 1):
                if v[r][c] == 0:
                    score = 0
                    if c > 0 and clues[r][c - 1] is not None:
                        score += 4 - abs(clues[r][c - 1] - 2)
                    if c < size and clues[r][c] is not None:
                        score += 4 - abs(clues[r][c] - 2)
                    if any(get_edge(k, er, ec) == 1 for k, er, ec in vertex_coords(r, c) + vertex_coords(r + 1, c)):
                        score += 10
                    cand = (-score, "v", r, c)
                    if best is None or cand < best:
                        best = cand
        return (best[1], best[2], best[3]) if best is not None else None

    def backtrack() -> bool:
        if should_abort():
            return False
        nxt = pick_next_edge()
        if nxt is None:
            return is_single_loop()
        kind, er, ec = nxt
        for val in (1, -1):
            trail: List[Tuple[str, int, int]] = [(kind, er, ec)]
            set_edge(kind, er, ec, val)
            if propagate(trail) and backtrack():
                return True
            for tk, tr, tc in trail:
                set_edge(tk, tr, tc, 0)
        return False

    init_trail: List[Tuple[str, int, int]] = []
    if not propagate(init_trail):
        return None
    if backtrack():
        return h, v
    return None


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    clues = state["cell_clues"]
    size = int(state.get("size") or len(clues))
    empty_h = [[0] * size for _ in range(size + 1)]
    empty_v = [[0] * (size + 1) for _ in range(size)]

    yield {
        "type": "start",
        "state": {"size": size, "cell_clues": clues, "h_edges": empty_h, "v_edges": empty_v},
        "highlights": {},
        "desc": f"Loaded {size}x{size} Slitherlink lattice",
        "stats": {"size": size},
    }

    res = _solve_slitherlink(size, clues, should_abort)
    if should_abort():
        return
    if res is None:
        yield {
            "type": "failed",
            "state": {"size": size, "cell_clues": clues, "h_edges": empty_h, "v_edges": empty_v},
            "highlights": {},
            "desc": "No valid single-loop Slitherlink solution exists.",
            "stats": {},
        }
        return

    h_sol, v_sol = res
    cur_h = [[0] * size for _ in range(size + 1)]
    cur_v = [[0] * (size + 1) for _ in range(size)]

    edge_coords = [
        ("h", r, c) for r in range(size + 1) for c in range(size) if h_sol[r][c] == 1
    ] + [
        ("v", r, c) for r in range(size) for c in range(size + 1) if v_sol[r][c] == 1
    ]

    for idx, (kind, r, c) in enumerate(edge_coords, 1):
        if should_abort():
            return
        if kind == "h":
            cur_h[r][c] = 1
        else:
            cur_v[r][c] = 1
        is_last = idx == len(edge_coords)
        yield {
            "type": "solution" if is_last else "deduce",
            "state": {
                "size": size,
                "cell_clues": clues,
                "h_edges": [list(row) for row in cur_h],
                "v_edges": [list(row) for row in cur_v],
            },
            "highlights": {"edge": [kind, r, c]},
            "desc": f"Loop segment {idx}/{len(edge_coords)}: {kind.upper()}({r}, {c})",
            "stats": {"segments": idx, "total": len(edge_coords)},
        }
