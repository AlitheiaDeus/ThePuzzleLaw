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
        "4x4 Starter": {
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
        "5x5 Classic": {
            "size": 5,
            "cell_clues": [
                [None, 3, None, 2, None],
                [2, None, 2, None, 3],
                [None, 1, None, 3, None],
                [3, None, 2, None, 2],
                [None, 2, None, 3, None],
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

    # Build ordered edge list: ("h", r, c) or ("v", r, c)
    edges: List[Tuple[str, int, int]] = []
    for r in range(size + 1):
        for c in range(size):
            edges.append(("h", r, c))
    for r in range(size):
        for c in range(size + 1):
            edges.append(("v", r, c))

    def cell_edges(r: int, c: int) -> List[int]:
        return [h[r][c], h[r + 1][c], v[r][c], v[r][c + 1]]

    def vertex_edges(vr: int, vc: int) -> List[int]:
        out = []
        if vc > 0:
            out.append(h[vr][vc - 1])
        if vc < size:
            out.append(h[vr][vc])
        if vr > 0:
            out.append(v[vr - 1][vc])
        if vr < size:
            out.append(v[vr][vc])
        return out

    def check_local(kind: str, er: int, ec: int) -> bool:
        adj_cells = []
        adj_verts = []
        if kind == "h":
            if er > 0:
                adj_cells.append((er - 1, ec))
            if er < size:
                adj_cells.append((er, ec))
            adj_verts.extend([(er, ec), (er, ec + 1)])
        else:
            if ec > 0:
                adj_cells.append((er, ec - 1))
            if ec < size:
                adj_cells.append((er, ec))
            adj_verts.extend([(er, ec), (er + 1, ec)])

        for r, c in adj_cells:
            clue = clues[r][c]
            if clue is not None:
                vals = cell_edges(r, c)
                ones = vals.count(1)
                unk = vals.count(0)
                if ones > clue or ones + unk < clue:
                    return False

        for vr, vc in adj_verts:
            vals = vertex_edges(vr, vc)
            ones = vals.count(1)
            unk = vals.count(0)
            if ones > 2:
                return False
            if unk == 0 and ones == 1:
                return False
        return True

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

    def backtrack(idx: int) -> bool:
        if should_abort():
            return False
        if idx == len(edges):
            return is_single_loop()
        kind, er, ec = edges[idx]
        arr = h if kind == "h" else v
        for val in (1, -1):
            arr[er][ec] = val
            if check_local(kind, er, ec) and backtrack(idx + 1):
                return True
        arr[er][ec] = 0
        return False

    if backtrack(0):
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
