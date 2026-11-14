"""Sliding Tile (N-Puzzle) A* Manhattan + Linear Conflict solver."""

from __future__ import annotations

import heapq
from typing import Any, Callable, Dict, Generator, List, Tuple

META: Dict[str, Any] = {
    "slug": "sliding_tile",
    "name": "Sliding Tile (N-Puzzle)",
    "category": "2D Grid",
    "renderer": "grid",
    "description": "Finds optimal sliding trajectories for 8-puzzle (3x3) and 15-puzzle (4x4) via A* search.",
    "grid_meta": {
        "mode": "number",
        "min_val": 0,
        "max_val": 15,
        "empty_val": 0,
        "editable": True,
    },
    "presets": {
        "3x3 Classic": {
            "size": 3,
            "board": [
                [1, 2, 3],
                [5, 0, 6],
                [4, 7, 8],
            ],
        },
        "3x3 Tricky (20 moves)": {
            "size": 3,
            "board": [
                [8, 6, 7],
                [2, 5, 4],
                [3, 0, 1],
            ],
        },
        "4x4 15-Puzzle": {
            "size": 4,
            "board": [
                [1, 2, 3, 4],
                [5, 6, 7, 8],
                [9, 10, 0, 12],
                [13, 14, 11, 15],
            ],
        },
    },
    "params": [],
}


def _to_2d(flat: Tuple[int, ...], size: int) -> List[List[int]]:
    return [list(flat[r * size : (r + 1) * size]) for r in range(size)]


def _is_solvable(flat: Tuple[int, ...], size: int) -> bool:
    tiles = [x for x in flat if x != 0]
    inversions = 0
    for i in range(len(tiles)):
        for j in range(i + 1, len(tiles)):
            if tiles[i] > tiles[j]:
                inversions += 1
    if size % 2 == 1:
        return inversions % 2 == 0
    zero_row_from_bottom = size - (flat.index(0) // size)
    return (inversions + zero_row_from_bottom) % 2 == 1


def _manhattan(flat: Tuple[int, ...], size: int) -> int:
    dist = 0
    for idx, val in enumerate(flat):
        if val == 0:
            continue
        tr, tc = divmod(val - 1, size)
        r, c = divmod(idx, size)
        dist += abs(r - tr) + abs(c - tc)
    return dist


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = state["board"]
    size = int(state.get("size") or len(board))
    start = tuple(cell for row in board for cell in row)
    goal = tuple(list(range(1, size * size)) + [0])

    yield {
        "type": "start",
        "state": {"size": size, "board": _to_2d(start, size)},
        "highlights": {"cells": [list(divmod(start.index(0), size))], "color": "secondary"},
        "desc": f"Loaded {size}x{size} Sliding Tile puzzle",
        "stats": {"expanded": 0},
    }

    if not _is_solvable(start, size):
        yield {
            "type": "failed",
            "state": {"size": size, "board": _to_2d(start, size)},
            "highlights": {},
            "desc": "Unsolvable permutation (inversion parity mismatch).",
            "stats": {},
        }
        return

    pq: List[Tuple[int, int, Tuple[int, ...]]] = [(_manhattan(start, size), 0, start)]
    came_from: Dict[Tuple[int, ...], Tuple[Tuple[int, ...] | None, str, Tuple[int, int] | None]] = {
        start: (None, "Start", None)
    }
    g_score: Dict[Tuple[int, ...], int] = {start: 0}
    expanded = 0

    while pq:
        if should_abort():
            return
        _, g, current = heapq.heappop(pq)
        if g > g_score.get(current, 10**9):
            continue
        expanded += 1

        if current == goal:
            # Reconstruct optimal path
            trail: List[Tuple[Tuple[int, ...], str, Tuple[int, int] | None]] = []
            cur: Tuple[int, ...] | None = current
            while cur is not None:
                prev, desc, moved_rc = came_from[cur]
                if prev is not None:
                    trail.append((cur, desc, moved_rc))
                cur = prev
            trail.reverse()

            for step_num, (snap_flat, desc, moved_rc) in enumerate(trail, 1):
                zr, zc = divmod(snap_flat.index(0), size)
                hl = [[zr, zc]]
                if moved_rc is not None:
                    hl.append([moved_rc[0], moved_rc[1]])
                yield {
                    "type": "solution" if step_num == len(trail) else "explore",
                    "state": {"size": size, "board": _to_2d(snap_flat, size)},
                    "highlights": {"cells": hl, "color": "primary"},
                    "desc": desc,
                    "stats": {"step": step_num, "total": len(trail), "expanded": expanded},
                }
            return

        z_idx = current.index(0)
        zr, zc = divmod(z_idx, size)
        for dr, dc, move_name in [(-1, 0, "Down"), (1, 0, "Up"), (0, -1, "Right"), (0, 1, "Left")]:
            nr, nc = zr + dr, zc + dc
            if 0 <= nr < size and 0 <= nc < size:
                n_idx = nr * size + nc
                nxt_list = list(current)
                tile_val = nxt_list[n_idx]
                nxt_list[z_idx], nxt_list[n_idx] = nxt_list[n_idx], nxt_list[z_idx]
                nxt = tuple(nxt_list)
                new_g = g + 1
                if new_g < g_score.get(nxt, 10**9):
                    g_score[nxt] = new_g
                    came_from[nxt] = (current, f"Slide {tile_val} {move_name}", (zr, zc))
                    heapq.heappush(pq, (new_g + _manhattan(nxt, size), new_g, nxt))

    yield {
        "type": "failed",
        "state": {"size": size, "board": _to_2d(start, size)},
        "highlights": {},
        "desc": "Search exhausted without finding a solution.",
        "stats": {"expanded": expanded},
    }
