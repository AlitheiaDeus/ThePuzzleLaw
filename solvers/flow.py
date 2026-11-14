"""Flow Free (Numberlink) & Checkpoint Saturation Path solver.
Supports multi-color endpoint pairs AND ordered checkpoint saturation (from flow_solver.py).
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

FLOW_COLORS = {
    "0": "#232629",
    "1": "#FF4757",
    "2": "#00F5D4",
    "3": "#FFE600",
    "4": "#3867D6",
    "5": "#B7016B",
    "6": "#01CA6B",
}

META: Dict[str, Any] = {
    "slug": "flow",
    "name": "Flow Free / Numberlink",
    "category": "Path",
    "renderer": "grid",
    "description": "Solves Numberlink (multi-pair color routing) and Checkpoint Saturation Flow.",
    "grid_meta": {
        "mode": "palette",
        "min_val": 0,
        "max_val": 6,
        "colors": FLOW_COLORS,
        "editable": True,
        "resizable": True,
        "min_dim": 3,
        "max_dim": 9,
    },
    "presets": {
        "5x5": {
            "mode": "numberlink",
            "board": [
                [1, 0, 0, 0, 2],
                [3, 4, 0, 0, 0],
                [0, 0, 1, 3, 0],
                [0, 0, 4, 0, 0],
                [0, 0, 0, 0, 2],
            ],
        },
        "5x5 Checkpoints": {
            "mode": "checkpoints",
            "board": [
                [1, 0, 0, 0, 0],
                [0, 0, 0, 2, 0],
                [0, 0, 0, 0, 0],
                [0, 3, 0, 0, 0],
                [0, 0, 0, 0, 4],
            ],
        },
    },
    "params": [
        {
            "key": "mode",
            "label": "Flow Mode",
            "type": "select",
            "default": "numberlink",
            "options": ["numberlink", "checkpoints"],
        }
    ],
}


def _solve_checkpoints(
    board: List[List[int]],
    should_abort: Callable[[], bool],
) -> Optional[List[Tuple[int, int]]]:
    rows, cols = len(board), len(board[0])
    total = rows * cols
    cps = {board[r][c]: (r, c) for r in range(rows) for c in range(cols) if board[r][c] > 0}
    if 1 not in cps:
        return None
    max_cp = max(cps.keys())

    def region_connected(path_set: set) -> bool:
        unvisited = [(r, c) for r in range(rows) for c in range(cols) if (r, c) not in path_set]
        if not unvisited:
            return True
        q = deque([unvisited[0]])
        seen = {unvisited[0]}
        while q:
            r, c = q.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in path_set and (nr, nc) not in seen:
                    seen.add((nr, nc))
                    q.append((nr, nc))
        return len(seen) == len(unvisited)

    path = [cps[1]]
    path_set = {cps[1]}
    cp_coords = set(cps.values())

    def dfs(target_cp: int) -> bool:
        if should_abort():
            return False
        if target_cp > max_cp:
            return len(path) == total
        if len(path) == total:
            return False
        r, c = path[-1]
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            nxt = (nr, nc)
            if not (0 <= nr < rows and 0 <= nc < cols) or nxt in path_set:
                continue
            if nxt == cps.get(target_cp):
                next_cp = target_cp + 1
            elif nxt in cp_coords:
                continue
            else:
                next_cp = target_cp
            path.append(nxt)
            path_set.add(nxt)
            if region_connected(path_set) and dfs(next_cp):
                return True
            path.pop()
            path_set.remove(nxt)
        return False

    return path if dfs(2) else None


def _solve_numberlink(
    board: List[List[int]],
    should_abort: Callable[[], bool],
) -> Optional[Tuple[List[List[int]], List[Tuple[int, int, int]]]]:
    rows, cols = len(board), len(board[0])
    endpoints: Dict[int, List[Tuple[int, int]]] = {}
    for r in range(rows):
        for c in range(cols):
            v = board[r][c]
            if v > 0:
                endpoints.setdefault(v, []).append((r, c))

    colors = sorted(endpoints.keys())
    if any(len(endpoints[col]) != 2 for col in colors):
        return None

    grid = [list(r) for r in board]
    trail: List[Tuple[int, int, int]] = []

    def can_reach(start: Tuple[int, int], target: Tuple[int, int]) -> bool:
        q = deque([start])
        seen = {start}
        while q:
            r, c = q.popleft()
            if (r, c) == target:
                return True
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in seen:
                    if grid[nr][nc] == 0 or (nr, nc) == target:
                        seen.add((nr, nc))
                        q.append((nr, nc))
        return False

    def route(color_idx: int, pos: Tuple[int, int]) -> bool:
        if should_abort():
            return False
        if color_idx == len(colors):
            return all(cell != 0 for row in grid for cell in row)

        col = colors[color_idx]
        target = endpoints[col][1]
        if pos == target:
            if color_idx + 1 < len(colors):
                nxt_start = endpoints[colors[color_idx + 1]][0]
                return route(color_idx + 1, nxt_start)
            return all(cell != 0 for row in grid for cell in row)

        if not can_reach(pos, target):
            return False

        r, c = pos
        # Order neighbors closer to target first
        nbrs = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                if (nr, nc) == target or grid[nr][nc] == 0:
                    dist = abs(nr - target[0]) + abs(nc - target[1])
                    nbrs.append((dist, nr, nc))
        nbrs.sort()

        for _, nr, nc in nbrs:
            is_target = (nr, nc) == target
            if not is_target:
                grid[nr][nc] = col
                trail.append((nr, nc, col))
            if route(color_idx, (nr, nc)):
                return True
            if not is_target:
                grid[nr][nc] = 0
                trail.pop()
        return False

    if not colors:
        return None
    if route(0, endpoints[colors[0]][0]):
        return grid, trail
    return None


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = [list(r) for r in state["board"]]
    mode = str(params.get("mode") or state.get("mode") or "numberlink")

    yield {
        "type": "start",
        "state": {"mode": mode, "board": [list(r) for r in board]},
        "highlights": {},
        "desc": f"Loaded {len(board)}x{len(board[0])} Flow ({mode}) board",
        "stats": {"mode": mode},
    }

    if mode == "checkpoints":
        path = _solve_checkpoints(board, should_abort)
        if should_abort():
            return
        if path is None:
            yield {
                "type": "failed",
                "state": {"mode": mode, "board": board},
                "highlights": {},
                "desc": "No full-grid checkpoint path found.",
                "stats": {},
            }
            return
        replay = [list(r) for r in board]
        for idx, (r, c) in enumerate(path, 1):
            if replay[r][c] == 0:
                replay[r][c] = 2
            is_last = idx == len(path)
            yield {
                "type": "solution" if is_last else "explore",
                "state": {"mode": mode, "board": [list(row) for row in replay]},
                "highlights": {"path": [[pr, pc] for pr, pc in path[:idx]], "cells": [[r, c]], "color": "primary"},
                "desc": f"Step {idx}/{len(path)}: Visit ({r + 1}, {c + 1})",
                "stats": {"step": idx, "total": len(path)},
            }
        return

    res = _solve_numberlink(board, should_abort)
    if should_abort():
        return
    if res is None:
        yield {
            "type": "failed",
            "state": {"mode": mode, "board": board},
            "highlights": {},
            "desc": "No full-saturation Numberlink solution found.",
            "stats": {},
        }
        return

    solved_grid, trail = res
    replay = [list(r) for r in board]
    for idx, (r, c, col) in enumerate(trail, 1):
        replay[r][c] = col
        is_last = idx == len(trail)
        yield {
            "type": "solution" if is_last else "explore",
            "state": {"mode": mode, "board": [list(row) for row in replay]},
            "highlights": {"cells": [[r, c]], "color": "primary"},
            "desc": f"Route Color {col} through ({r + 1}, {c + 1})",
            "stats": {"step": idx, "total": len(trail)},
        }
    if not trail:
        yield {
            "type": "solution",
            "state": {"mode": mode, "board": solved_grid},
            "highlights": {},
            "desc": "Already saturated!",
            "stats": {},
        }
