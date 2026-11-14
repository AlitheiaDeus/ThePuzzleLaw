"""Flood-It optimal minimum-move solver using component contraction + IDA*."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

COLOR_PALETTE = {
    "0": "#FA8231",
    "1": "#FF4757",
    "2": "#2ED573",
    "3": "#FED330",
    "4": "#3867D6",
    "5": "#8854D0",
    "6": "#FF3385",
    "7": "#00D2D3",
}
COLOR_NAMES = ["Orange", "Red", "Green", "Yellow", "Blue", "Purple", "Magenta", "Cyan"]

META: Dict[str, Any] = {
    "slug": "flood",
    "name": "Flood",
    "category": "Grid / Graph Search",
    "renderer": "grid",
    "description": "Optimal Flood-It solver using planar component contraction and IDA*.",
    "grid_meta": {
        "mode": "palette",
        "min_val": 0,
        "max_val": 5,
        "colors": COLOR_PALETTE,
        "editable": True,
    },
    "presets": {
        "6x6": {
            "num_colors": 5,
            "board": [
                [0, 1, 2, 3, 4, 0],
                [0, 2, 2, 1, 4, 3],
                [1, 3, 0, 1, 2, 3],
                [4, 3, 0, 4, 2, 1],
                [4, 2, 1, 3, 0, 1],
                [2, 2, 3, 4, 0, 4],
            ],
        },
        "8x8": {
            "num_colors": 6,
            "board": [
                [0, 0, 1, 2, 3, 4, 5, 1],
                [2, 1, 1, 3, 3, 4, 0, 1],
                [2, 4, 5, 5, 0, 2, 0, 3],
                [4, 4, 2, 1, 0, 2, 5, 3],
                [3, 5, 2, 1, 4, 4, 5, 2],
                [3, 0, 0, 2, 5, 1, 3, 2],
                [1, 0, 4, 3, 5, 1, 0, 4],
                [1, 5, 4, 3, 2, 0, 0, 4],
            ],
        },
    },
    "params": [],
}


def _flooded_region(grid: List[List[int]]) -> List[List[int]]:
    rows, cols = len(grid), len(grid[0])
    anchor = grid[0][0]
    visited = {(0, 0)}
    q = deque([(0, 0)])
    while q:
        r, c = q.popleft()
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in visited and grid[nr][nc] == anchor:
                visited.add((nr, nc))
                q.append((nr, nc))
    return [[r, c] for r, c in visited]


def _apply_flood(grid: List[List[int]], new_color: int) -> List[List[int]]:
    out = [list(row) for row in grid]
    for r, c in _flooded_region(out):
        out[r][c] = new_color
    return out


def _extract_components(grid: List[List[int]]):
    rows, cols = len(grid), len(grid[0])
    comp_map = [[-1] * cols for _ in range(rows)]
    components = []
    cid = 0
    for sr in range(rows):
        for sc in range(cols):
            if comp_map[sr][sc] != -1:
                continue
            col = grid[sr][sc]
            cells = []
            q = deque([(sr, sc)])
            comp_map[sr][sc] = cid
            while q:
                r, c = q.popleft()
                cells.append((r, c))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols and comp_map[nr][nc] == -1 and grid[nr][nc] == col:
                        comp_map[nr][nc] = cid
                        q.append((nr, nc))
            components.append({"color": col, "size": len(cells), "adj": set()})
            cid += 1

    for r in range(rows):
        for c in range(cols):
            u = comp_map[r][c]
            for dr, dc in [(1, 0), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols:
                    v = comp_map[nr][nc]
                    if u != v:
                        components[u]["adj"].add(v)
                        components[v]["adj"].add(u)
    return components


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    grid = [list(row) for row in state["board"]]
    rows, cols = len(grid), len(grid[0])
    total = rows * cols
    num_colors = int(state.get("num_colors") or (max(max(r) for r in grid) + 1))

    start_region = _flooded_region(grid)
    yield {
        "type": "start",
        "state": {"num_colors": num_colors, "board": [list(r) for r in grid]},
        "highlights": {"cells": start_region, "color": "primary"},
        "desc": f"Anchor (0,0) covers {len(start_region)}/{total} cells",
        "stats": {"move": 0, "coverage_pct": round(len(start_region) / total * 100, 1)},
    }

    if len(start_region) == total:
        yield {
            "type": "solution",
            "state": {"num_colors": num_colors, "board": [list(r) for r in grid]},
            "highlights": {"cells": start_region, "color": "primary"},
            "desc": "Already uniform! Solved in 0 moves.",
            "stats": {"move": 0, "coverage_pct": 100.0},
        }
        return

    components = _extract_components(grid)
    num_comp = len(components)
    comp_colors = [c["color"] for c in components]
    comp_sizes = [c["size"] for c in components]
    comp_adj = [list(c["adj"]) for c in components]

    dist_matrix = [[9999] * num_comp for _ in range(num_comp)]
    for i in range(num_comp):
        dist_matrix[i][i] = 0
        q = deque([i])
        while q:
            u = q.popleft()
            d = dist_matrix[i][u]
            for v in comp_adj[u]:
                if dist_matrix[i][v] > d + 1:
                    dist_matrix[i][v] = d + 1
                    q.append(v)

    start_merged = 1
    init_dists = tuple(dist_matrix[0][v] for v in range(num_comp))
    start_boundary = 0
    for v in comp_adj[0]:
        start_boundary |= 1 << v
    full_mask = (1 << num_comp) - 1

    init_counts = [0] * max(num_colors, max(comp_colors) + 1)
    for c in comp_colors:
        init_counts[c] += 1
    init_counts[comp_colors[0]] -= 1

    nodes = [0]
    tt: Dict[Tuple[int, int], int] = {}

    def calc_h(merged: int, dists: Tuple[int, ...], counts: Tuple[int, ...]) -> int:
        max_d = max((dists[v] for v in range(num_comp) if not (merged & (1 << v))), default=0)
        rem_c = sum(1 for cnt in counts if cnt > 0)
        return max(max_d, rem_c)

    def ida(
        merged: int,
        cur_col: int,
        boundary: int,
        dists: Tuple[int, ...],
        counts: Tuple[int, ...],
        g: int,
        limit: int,
        path: List[int],
    ) -> Tuple[int, Optional[List[int]]]:
        nodes[0] += 1
        if should_abort():
            return -1, None
        h = calc_h(merged, dists, counts)
        f = g + h
        if f > limit:
            return f, None
        if merged == full_mask:
            return g, path

        key = (merged, cur_col)
        if key in tt and tt[key] <= g:
            return 999999, None

        by_color: Dict[int, List[int]] = {}
        for v in range(num_comp):
            if boundary & (1 << v):
                by_color.setdefault(comp_colors[v], []).append(v)

        cands = []
        for col, comps in by_color.items():
            absorbed = 0
            gained = 0
            for cid in comps:
                absorbed |= 1 << cid
                gained += comp_sizes[cid]
            n_merged = merged | absorbed
            n_boundary = boundary & ~n_merged
            for cid in comps:
                for nxt in comp_adj[cid]:
                    if not (n_merged & (1 << nxt)):
                        n_boundary |= 1 << nxt
            n_dists = list(dists)
            for cid in comps:
                row = dist_matrix[cid]
                for v in range(num_comp):
                    if not (n_merged & (1 << v)) and row[v] < n_dists[v]:
                        n_dists[v] = row[v]
            n_counts = list(counts)
            for cid in comps:
                n_counts[comp_colors[cid]] -= 1
            nd_t, nc_t = tuple(n_dists), tuple(n_counts)
            cands.append((calc_h(n_merged, nd_t, nc_t), -gained, col, n_merged, n_boundary, nd_t, nc_t))

        cands.sort(key=lambda x: (x[0], x[1]))
        min_exc = 999999
        for _, _, col, n_merged, n_boundary, nd_t, nc_t in cands:
            t, res = ida(n_merged, col, n_boundary, nd_t, nc_t, g + 1, limit, path + [col])
            if res is not None:
                return t, res
            if should_abort():
                return -1, None
            if t < min_exc:
                min_exc = t
        tt[key] = g
        return min_exc, None

    threshold = calc_h(start_merged, init_dists, tuple(init_counts))
    optimal_seq: Optional[List[int]] = None
    while not should_abort():
        tt.clear()
        t, found = ida(start_merged, comp_colors[0], start_boundary, init_dists, tuple(init_counts), 0, threshold, [])
        if found is not None:
            optimal_seq = found
            break
        if t >= 999999 or t == -1:
            break
        threshold = t

    if should_abort():
        return
    if optimal_seq is None:
        yield {
            "type": "failed",
            "state": {"num_colors": num_colors, "board": grid},
            "highlights": {},
            "desc": "Could not find an optimal Flood sequence.",
            "stats": {"nodes": nodes[0]},
        }
        return

    cur_grid = grid
    for step_idx, col in enumerate(optimal_seq, 1):
        cur_grid = _apply_flood(cur_grid, col)
        region = _flooded_region(cur_grid)
        cname = COLOR_NAMES[col] if col < len(COLOR_NAMES) else f"Color {col}"
        is_last = step_idx == len(optimal_seq)
        yield {
            "type": "solution" if is_last else "deduce",
            "state": {"num_colors": num_colors, "board": [list(r) for r in cur_grid]},
            "highlights": {"cells": region, "color": "primary"},
            "desc": f"Move {step_idx}/{len(optimal_seq)}: Flood {cname} ({len(region)}/{total} cells)",
            "stats": {
                "move": step_idx,
                "total_moves": len(optimal_seq),
                "nodes": nodes[0],
                "coverage_pct": round(len(region) / total * 100, 1),
            },
        }
