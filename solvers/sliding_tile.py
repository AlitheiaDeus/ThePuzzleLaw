"""Sliding Tile (N-Puzzle) solver supporting rectangular RxC grids up to 9x9+."""

from __future__ import annotations

import heapq
from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

META: Dict[str, Any] = {
    "slug": "sliding_tile",
    "name": "Sliding Tile (N-Puzzle)",
    "category": "Path",
    "renderer": "grid",
    "grid_meta": {
        "mode": "permutation",
        "empty_val": 0,
        "editable": True,
        "resizable": True,
        "min_dim": 2,
        "max_dim": 9,
    },
    "description": (
        "Solves rectangular R x C sliding tile puzzles. Uses exact A* (Manhattan + Linear Conflict) "
        "for small boards and layer-by-layer reduction + A* for larger boards up to 9x9."
    ),
    "presets": {
        "3x3": {
            "rows": 3,
            "cols": 3,
            "board": [
                [1, 2, 3],
                [5, 0, 6],
                [4, 7, 8],
            ],
        },
        "4x4": {
            "rows": 4,
            "cols": 4,
            "board": [
                [1, 2, 3, 4],
                [5, 6, 7, 8],
                [9, 10, 0, 12],
                [13, 14, 11, 15],
            ],
        },
        "5x5": {
            "rows": 5,
            "cols": 5,
            "board": [
                [1, 2, 3, 4, 5],
                [6, 7, 8, 9, 10],
                [11, 12, 13, 14, 15],
                [16, 17, 18, 0, 20],
                [21, 22, 23, 19, 24],
            ],
        },
        "6x6": {
            "rows": 6,
            "cols": 6,
            "board": [
                [1, 2, 3, 4, 5, 6],
                [7, 8, 9, 10, 11, 12],
                [13, 14, 15, 16, 17, 18],
                [19, 20, 21, 22, 23, 24],
                [25, 26, 27, 28, 0, 30],
                [31, 32, 33, 34, 29, 35],
            ],
        },
        "7x7": {
            "rows": 7,
            "cols": 7,
            "board": [
                [1, 2, 3, 4, 5, 6, 7],
                [8, 9, 10, 11, 12, 13, 14],
                [15, 16, 17, 18, 19, 20, 21],
                [22, 23, 24, 25, 26, 27, 28],
                [29, 30, 31, 32, 33, 34, 35],
                [36, 37, 38, 39, 40, 0, 42],
                [43, 44, 45, 46, 47, 41, 48],
            ],
        },
        "8x8": {
            "rows": 8,
            "cols": 8,
            "board": [
                [1, 2, 3, 4, 5, 6, 7, 8],
                [9, 10, 11, 12, 13, 14, 15, 16],
                [17, 18, 19, 20, 21, 22, 23, 24],
                [25, 26, 27, 28, 29, 30, 31, 32],
                [33, 34, 35, 36, 37, 38, 39, 40],
                [41, 42, 43, 44, 45, 46, 47, 48],
                [49, 50, 51, 52, 53, 54, 0, 56],
                [57, 58, 59, 60, 61, 62, 55, 63],
            ],
        },
        "9x9": {
            "rows": 9,
            "cols": 9,
            "board": [
                [1, 2, 3, 4, 5, 6, 7, 8, 9],
                [10, 11, 12, 13, 14, 15, 16, 17, 18],
                [19, 20, 21, 22, 23, 24, 25, 26, 27],
                [28, 29, 30, 31, 32, 33, 34, 35, 36],
                [37, 38, 39, 40, 41, 42, 43, 44, 45],
                [46, 47, 48, 49, 50, 51, 52, 53, 54],
                [55, 56, 57, 58, 59, 60, 61, 62, 63],
                [64, 65, 66, 67, 68, 69, 70, 0, 72],
                [73, 74, 75, 76, 77, 78, 79, 71, 80],
            ],
        },
    },
    "params": [],
}


def _to_2d(flat: List[int] | Tuple[int, ...], rows: int, cols: int) -> List[List[int]]:
    return [list(flat[r * cols : (r + 1) * cols]) for r in range(rows)]


def _parity_error(flat: Tuple[int, ...], rows: int, cols: int) -> Optional[str]:
    tiles = [x for x in flat if x != 0]
    inversions = 0
    for i in range(len(tiles)):
        ti = tiles[i]
        for j in range(i + 1, len(tiles)):
            if ti > tiles[j]:
                inversions += 1
    if cols % 2 == 1:
        if inversions % 2 != 0:
            return f"Pre-solve parity failed: {inversions} inversions on odd-width {rows}x{cols} grid (must be even)."
        return None
    zero_row_from_bottom = rows - (flat.index(0) // cols)
    total = inversions + zero_row_from_bottom
    if total % 2 != 1:
        return (
            f"Pre-solve parity failed: inversions ({inversions}) + blank row from bottom ({zero_row_from_bottom}) "
            f"= {total} on even-width {rows}x{cols} grid (must be odd)."
        )
    return None


def _is_solvable(flat: Tuple[int, ...], rows: int, cols: int) -> bool:
    return _parity_error(flat, rows, cols) is None


def _heuristic(flat: Tuple[int, ...], rows: int, cols: int) -> int:
    """Manhattan distance + Linear Conflict (admissible and consistent)."""
    dist = 0
    # Manhattan
    for idx, val in enumerate(flat):
        if val == 0:
            continue
        tr, tc = divmod(val - 1, cols)
        r, c = divmod(idx, cols)
        dist += abs(r - tr) + abs(c - tc)

    # Row linear conflicts
    for r in range(rows):
        row_start = r * cols
        max_tc = -1
        for c in range(cols):
            val = flat[row_start + c]
            if val != 0:
                tr, tc = divmod(val - 1, cols)
                if tr == r:
                    if tc > max_tc:
                        max_tc = tc
                    else:
                        dist += 2

    # Column linear conflicts
    for c in range(cols):
        max_tr = -1
        for r in range(rows):
            val = flat[r * cols + c]
            if val != 0:
                tr, tc = divmod(val - 1, cols)
                if tc == c:
                    if tr > max_tr:
                        max_tr = tr
                    else:
                        dist += 2

    return dist


def _astar_solve(
    start: Tuple[int, ...],
    rows: int,
    cols: int,
    should_abort: Callable[[], bool],
    max_expanded: Optional[int] = None,
) -> Optional[Tuple[List[Tuple[Tuple[int, ...], str, Tuple[int, int]]], int]]:
    """Exact A* search with Manhattan + Linear Conflict. Returns (trail, expanded) or None."""
    goal = tuple(list(range(1, rows * cols)) + [0])
    if start == goal:
        return [], 0

    pq: List[Tuple[int, int, Tuple[int, ...]]] = [(_heuristic(start, rows, cols), 0, start)]
    came_from: Dict[Tuple[int, ...], Tuple[Optional[Tuple[int, ...]], str, Optional[Tuple[int, int]]]] = {
        start: (None, "Start", None)
    }
    g_score: Dict[Tuple[int, ...], int] = {start: 0}
    expanded = 0

    while pq:
        if should_abort():
            return None
        if max_expanded is not None and expanded >= max_expanded:
            return None
        _, g, current = heapq.heappop(pq)
        if g > g_score.get(current, 10**9):
            continue
        expanded += 1

        if current == goal:
            trail: List[Tuple[Tuple[int, ...], str, Tuple[int, int]]] = []
            cur: Optional[Tuple[int, ...]] = current
            while cur is not None:
                prev, desc, moved_rc = came_from[cur]
                if prev is not None and moved_rc is not None:
                    trail.append((cur, desc, moved_rc))
                cur = prev
            trail.reverse()
            return trail, expanded

        z_idx = current.index(0)
        zr, zc = divmod(z_idx, cols)
        for dr, dc, move_name in [(-1, 0, "Down"), (1, 0, "Up"), (0, -1, "Right"), (0, 1, "Left")]:
            nr, nc = zr + dr, zc + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                n_idx = nr * cols + nc
                nxt_list = list(current)
                tile_val = nxt_list[n_idx]
                nxt_list[z_idx], nxt_list[n_idx] = nxt_list[n_idx], nxt_list[z_idx]
                nxt = tuple(nxt_list)
                new_g = g + 1
                if new_g < g_score.get(nxt, 10**9):
                    g_score[nxt] = new_g
                    came_from[nxt] = (current, f"Slide {tile_val} {move_name}", (zr, zc))
                    heapq.heappush(pq, (new_g + _heuristic(nxt, rows, cols), new_g, nxt))

    return None


def _layer_reduce_solve(
    start: Tuple[int, ...],
    rows: int,
    cols: int,
    should_abort: Callable[[], bool],
) -> Optional[Tuple[List[Tuple[List[int], str, Tuple[int, int]]], int]]:
    """Solve arbitrary RxC boards by reducing rows/cols down to <=3x3, then running exact A*."""
    board = list(start)
    trail: List[Tuple[List[int], str, Tuple[int, int]]] = []
    locked: Set[Tuple[int, int]] = set()
    ops = 0

    def idx(r: int, c: int) -> int:
        return r * cols + c

    def find_val(val: int) -> Tuple[int, int]:
        i = board.index(val)
        return divmod(i, cols)

    def slide_blank_to(target_rc: Tuple[int, int], extra_locked: Set[Tuple[int, int]] | None = None) -> bool:
        """BFS to move blank to target_rc without touching locked or extra_locked cells."""
        zr, zc = find_val(0)
        if (zr, zc) == target_rc:
            return True
        blocked = locked | (extra_locked or set())
        q = deque([(zr, zc)])
        parent: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {(zr, zc): None}
        while q:
            if should_abort():
                return False
            r, c = q.popleft()
            if (r, c) == target_rc:
                path: List[Tuple[int, int]] = []
                cur: Optional[Tuple[int, int]] = (r, c)
                while cur is not None:
                    path.append(cur)
                    cur = parent[cur]
                path.reverse()
                for k in range(1, len(path)):
                    pr, pc = path[k - 1]
                    nr, nc = path[k]
                    pi, ni = idx(pr, pc), idx(nr, nc)
                    tile_val = board[ni]
                    board[pi], board[ni] = board[ni], board[pi]
                    dr, dc = nr - pr, nc - pc
                    mname = {(-1, 0): "Down", (1, 0): "Up", (0, -1): "Right", (0, 1): "Left"}[(dr, dc)]
                    trail.append((list(board), f"Slide {tile_val} {mname}", (pr, pc)))
                return True
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and (nr, nc) not in blocked and (nr, nc) not in parent:
                    parent[(nr, nc)] = (r, c)
                    q.append((nr, nc))
        return False

    def move_tile(val: int, target_rc: Tuple[int, int]) -> bool:
        """Move tile `val` to `target_rc` using BFS over (tile_rc, blank_rc) states."""
        nonlocal ops
        tr, tc = find_val(val)
        if (tr, tc) == target_rc:
            return True
        zr, zc = find_val(0)
        start_st = (tr, tc, zr, zc)
        q = deque([start_st])
        parent: Dict[Tuple[int, int, int, int], Optional[Tuple[int, int, int, int]]] = {start_st: None}
        goal_state: Optional[Tuple[int, int, int, int]] = None

        while q:
            if should_abort():
                return False
            ops += 1
            ctr, ctc, czr, czc = q.popleft()
            if (ctr, ctc) == target_rc:
                goal_state = (ctr, ctc, czr, czc)
                break
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nzr, nzc = czr + dr, czc + dc
                if not (0 <= nzr < rows and 0 <= nzc < cols) or (nzr, nzc) in locked:
                    continue
                if (nzr, nzc) == (ctr, ctc):
                    nxt = (czr, czc, nzr, nzc)
                else:
                    nxt = (ctr, ctc, nzr, nzc)
                if nxt not in parent:
                    parent[nxt] = (ctr, ctc, czr, czc)
                    q.append(nxt)

        if goal_state is None:
            return False

        states: List[Tuple[int, int, int, int]] = []
        cur: Optional[Tuple[int, int, int, int]] = goal_state
        while cur is not None:
            states.append(cur)
            cur = parent[cur]
        states.reverse()

        for k in range(1, len(states)):
            _, _, pzr, pzc = states[k - 1]
            _, _, nzr, nzc = states[k]
            pi, ni = idx(pzr, pzc), idx(nzr, nzc)
            tile_val = board[ni]
            board[pi], board[ni] = board[ni], board[pi]
            dr, dc = nzr - pzr, nzc - pzc
            mname = {(-1, 0): "Down", (1, 0): "Up", (0, -1): "Right", (0, 1): "Left"}[(dr, dc)]
            trail.append((list(board), f"Slide {tile_val} {mname}", (pzr, pzc)))
        return True

    top_r = 0
    left_c = 0
    while (rows - top_r) > 3 or (cols - left_c) > 3:
        if should_abort():
            return None
        rem_r = rows - top_r
        rem_c = cols - left_c
        if rem_r >= rem_c and rem_r > 3:
            # Solve row top_r (columns left_c .. cols - 1)
            for c in range(left_c, cols - 2):
                val = top_r * cols + c + 1
                if not move_tile(val, (top_r, c)):
                    return None
                locked.add((top_r, c))

            # Last two tiles of row top_r
            a_val = top_r * cols + (cols - 2) + 1
            b_val = top_r * cols + (cols - 1) + 1
            if find_val(a_val) != (top_r, cols - 2) or find_val(b_val) != (top_r, cols - 1):
                if find_val(b_val) in ((top_r, cols - 2), (top_r, cols - 1)):
                    if not move_tile(b_val, (top_r + 2, cols - 2)):
                        return None
                if not move_tile(a_val, (top_r, cols - 1)):
                    return None
                while find_val(b_val) == (top_r, cols - 2) or (
                    find_val(0) == (top_r, cols - 2) and find_val(b_val) == (top_r + 1, cols - 2)
                ):
                    if find_val(0) == (top_r, cols - 2):
                        if not slide_blank_to((top_r + 1, cols - 2)):
                            return None
                    if not slide_blank_to((top_r + 1, cols - 2), {(top_r, cols - 2), (top_r, cols - 1)}):
                        return None
                    for target_rc in [(top_r, cols - 2), (top_r, cols - 1), (top_r + 1, cols - 1)]:
                        if not slide_blank_to(target_rc):
                            return None
                    if not move_tile(b_val, (top_r + 2, cols - 1)):
                        return None
                    if not move_tile(a_val, (top_r, cols - 1)):
                        return None
                locked.add((top_r, cols - 1))
                if not move_tile(b_val, (top_r + 1, cols - 1)):
                    return None
                locked.add((top_r + 1, cols - 1))
                if not slide_blank_to((top_r, cols - 2)):
                    return None
                locked.remove((top_r, cols - 1))
                locked.remove((top_r + 1, cols - 1))
                # Slide A left, then B up
                for target_rc in [(top_r, cols - 1), (top_r + 1, cols - 1)]:
                    if not slide_blank_to(target_rc):
                        return None
            locked.add((top_r, cols - 2))
            locked.add((top_r, cols - 1))
            top_r += 1
        else:
            # Solve column left_c (rows top_r .. rows - 1)
            for r in range(top_r, rows - 2):
                val = r * cols + left_c + 1
                if not move_tile(val, (r, left_c)):
                    return None
                locked.add((r, left_c))

            # Last two tiles of col left_c
            a_val = (rows - 2) * cols + left_c + 1
            b_val = (rows - 1) * cols + left_c + 1
            if find_val(a_val) != (rows - 2, left_c) or find_val(b_val) != (rows - 1, left_c):
                if find_val(b_val) in ((rows - 2, left_c), (rows - 1, left_c)):
                    if not move_tile(b_val, (rows - 2, left_c + 2)):
                        return None
                if not move_tile(a_val, (rows - 1, left_c)):
                    return None
                while find_val(b_val) == (rows - 2, left_c) or (
                    find_val(0) == (rows - 2, left_c) and find_val(b_val) == (rows - 2, left_c + 1)
                ):
                    if find_val(0) == (rows - 2, left_c):
                        if not slide_blank_to((rows - 2, left_c + 1)):
                            return None
                    if not slide_blank_to((rows - 2, left_c + 1), {(rows - 2, left_c), (rows - 1, left_c)}):
                        return None
                    for target_rc in [(rows - 2, left_c), (rows - 1, left_c), (rows - 1, left_c + 1)]:
                        if not slide_blank_to(target_rc):
                            return None
                    if not move_tile(b_val, (rows - 1, left_c + 2)):
                        return None
                    if not move_tile(a_val, (rows - 1, left_c)):
                        return None
                locked.add((rows - 1, left_c))
                if not move_tile(b_val, (rows - 1, left_c + 1)):
                    return None
                locked.add((rows - 1, left_c + 1))
                if not slide_blank_to((rows - 2, left_c)):
                    return None
                locked.remove((rows - 1, left_c))
                locked.remove((rows - 1, left_c + 1))
                # Slide A up, then B left
                for target_rc in [(rows - 1, left_c), (rows - 1, left_c + 1)]:
                    if not slide_blank_to(target_rc):
                        return None
            locked.add((rows - 2, left_c))
            locked.add((rows - 1, left_c))
            left_c += 1

    # Solve the remaining <=3x3 subgrid with exact A*
    sub_r = rows - top_r
    sub_c = cols - left_c
    val_to_sub: Dict[int, int] = {0: 0}
    sub_to_val: Dict[int, int] = {0: 0}
    sub_list: List[int] = []
    for r in range(top_r, rows):
        for c in range(left_c, cols):
            expected_val = r * cols + c + 1
            sub_idx = (r - top_r) * sub_c + (c - left_c) + 1
            if r == rows - 1 and c == cols - 1:
                sub_idx = 0
            else:
                val_to_sub[expected_val] = sub_idx
                sub_to_val[sub_idx] = expected_val
            sub_list.append(board[idx(r, c)])

    sub_start = tuple(val_to_sub[v] for v in sub_list)
    sub_res = _astar_solve(sub_start, sub_r, sub_c, should_abort)
    if sub_res is None:
        return None
    sub_trail, sub_exp = sub_res
    ops += sub_exp

    for sub_snap, desc, (szr, szc) in sub_trail:
        # Map sub_snap back into full board
        for sr in range(sub_r):
            for sc in range(sub_c):
                board[idx(top_r + sr, left_c + sc)] = sub_to_val[sub_snap[sr * sub_c + sc]]
        # Replace sub_val in desc if needed? desc uses sub_val, let's compute actual moved tile
        zr, zc = top_r + szr, left_c + szc
        # The tile that moved into (zr, zc) is now at the *new* blank? No, (szr, szc) is where blank WAS before moving,
        # so board[idx(zr, zc)] is the tile that just slid!
        moved_tile = board[idx(zr, zc)]
        dir_word = desc.rsplit(" ", 1)[-1]
        trail.append((list(board), f"Slide {moved_tile} {dir_word}", (zr, zc)))

    return trail, ops


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = state.get("board", [])
    rows = len(board)
    cols = len(board[0]) if rows > 0 else 0
    if rows < 2 or cols < 2 or any(len(r) != cols for r in board):
        yield {
            "type": "start",
            "state": {"rows": rows, "cols": cols, "board": board},
            "highlights": {},
            "desc": "Invalid Sliding Tile dimensions.",
            "stats": {},
        }
        yield {
            "type": "failed",
            "state": {"rows": rows, "cols": cols, "board": board},
            "highlights": {},
            "desc": "Board must be a rectangular matrix of at least 2x2.",
            "stats": {},
        }
        return

    start = tuple(int(cell) for row in board for cell in row)
    expected = set(range(rows * cols))

    yield {
        "type": "start",
        "state": {"rows": rows, "cols": cols, "board": _to_2d(start, rows, cols)},
        "highlights": {"cells": [list(divmod(start.index(0), cols))] if 0 in start else [], "color": "secondary"},
        "desc": f"Loaded {rows}x{cols} Sliding Tile puzzle",
        "stats": {"expanded": 0},
    }

    if set(start) != expected:
        yield {
            "type": "failed",
            "state": {"rows": rows, "cols": cols, "board": _to_2d(start, rows, cols)},
            "highlights": {},
            "desc": f"Board must contain each number 0..{rows * cols - 1} exactly once.",
            "stats": {},
        }
        return

    parity_err = _parity_error(start, rows, cols)
    if parity_err is not None:
        yield {
            "type": "failed",
            "state": {"rows": rows, "cols": cols, "board": _to_2d(start, rows, cols)},
            "highlights": {},
            "desc": parity_err,
            "stats": {},
        }
        return

    goal = tuple(list(range(1, rows * cols)) + [0])
    if start == goal:
        yield {
            "type": "solution",
            "state": {"rows": rows, "cols": cols, "board": _to_2d(start, rows, cols)},
            "highlights": {},
            "desc": "Puzzle is already solved!",
            "stats": {"step": 0, "total": 0, "expanded": 0, "h": 0},
        }
        return

    res = None
    strategy = "A* (Manhattan + Linear Conflict)"
    if rows * cols <= 12:
        res = _astar_solve(start, rows, cols, should_abort)
    else:
        # Try exact A* with a fast budget for easy/medium 4x4+, then fall back to layer reduction
        if rows * cols <= 16:
            res = _astar_solve(start, rows, cols, should_abort, max_expanded=15000)
        if res is None and not should_abort():
            strategy = "Layer reduction + A*"
            res = _layer_reduce_solve(start, rows, cols, should_abort)

    if should_abort():
        return

    if res is None:
        yield {
            "type": "failed",
            "state": {"rows": rows, "cols": cols, "board": _to_2d(start, rows, cols)},
            "highlights": {},
            "desc": f"Search exhausted ({strategy}) without finding a solution.",
            "stats": {},
        }
        return

    trail, expanded = res
    for step_num, (snap_flat, desc, moved_rc) in enumerate(trail, 1):
        if should_abort():
            return
        zr, zc = divmod(snap_flat.index(0), cols)
        hl = [[zr, zc], [moved_rc[0], moved_rc[1]]]
        yield {
            "type": "solution" if step_num == len(trail) else "explore",
            "state": {"rows": rows, "cols": cols, "board": _to_2d(snap_flat, rows, cols)},
            "highlights": {"cells": hl, "color": "primary"},
            "desc": f"{desc} [{strategy}]" if step_num == len(trail) else desc,
            "stats": {
                "step": step_num,
                "total": len(trail),
                "expanded": expanded,
                "h": _heuristic(tuple(snap_flat), rows, cols),
            },
        }
