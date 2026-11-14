"""Sudoku hybrid solver: Naked/Hidden Singles + MRV recursive backtracking."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

META: Dict[str, Any] = {
    "slug": "sudoku",
    "name": "Sudoku",
    "category": "Constraint Grids",
    "renderer": "grid",
    "description": "Solves 4x4, 6x6, or 9x9 Sudoku grids using Naked/Hidden Singles followed by MRV backtracking.",
    "grid_meta": {
        "mode": "number",
        "min_val": 0,
        "max_val": 9,
        "empty_val": 0,
        "editable": True,
    },
    "presets": {
        "9x9": {
            "grid_dim": 9,
            "box_w": 3,
            "box_h": 3,
            "board": [
                [5, 3, 0, 0, 7, 0, 0, 0, 0],
                [6, 0, 0, 1, 9, 5, 0, 0, 0],
                [0, 9, 8, 0, 0, 0, 0, 6, 0],
                [8, 0, 0, 0, 6, 0, 0, 0, 3],
                [4, 0, 0, 8, 0, 3, 0, 0, 1],
                [7, 0, 0, 0, 2, 0, 0, 0, 6],
                [0, 6, 0, 0, 0, 0, 2, 8, 0],
                [0, 0, 0, 4, 1, 9, 0, 0, 5],
                [0, 0, 0, 0, 8, 0, 0, 7, 9],
            ],
        },
        "9x9 Hard": {
            "grid_dim": 9,
            "box_w": 3,
            "box_h": 3,
            "board": [
                [8, 0, 0, 0, 0, 0, 0, 0, 0],
                [0, 0, 3, 6, 0, 0, 0, 0, 0],
                [0, 7, 0, 0, 9, 0, 2, 0, 0],
                [0, 5, 0, 0, 0, 7, 0, 0, 0],
                [0, 0, 0, 0, 4, 5, 7, 0, 0],
                [0, 0, 0, 1, 0, 0, 0, 3, 0],
                [0, 0, 1, 0, 0, 0, 0, 6, 8],
                [0, 0, 8, 5, 0, 0, 0, 1, 0],
                [0, 9, 0, 0, 0, 0, 4, 0, 0],
            ],
        },
        "4x4": {
            "grid_dim": 4,
            "box_w": 2,
            "box_h": 2,
            "board": [
                [1, 0, 0, 4],
                [0, 0, 1, 0],
                [0, 3, 0, 0],
                [2, 0, 0, 3],
            ],
        },
    },
    "params": [],
}


def _clone_board(board: List[List[int]]) -> List[List[int]]:
    return [list(row) for row in board]


def _get_peers(r: int, c: int, dim: int, box_w: int, box_h: int) -> Set[Tuple[int, int]]:
    peers: Set[Tuple[int, int]] = set()
    for i in range(dim):
        if i != c:
            peers.add((r, i))
        if i != r:
            peers.add((i, c))
    sr, sc = r - (r % box_h), c - (c % box_w)
    for dr in range(box_h):
        for dc in range(box_w):
            if (sr + dr, sc + dc) != (r, c):
                peers.add((sr + dr, sc + dc))
    return peers


def _all_units(dim: int, box_w: int, box_h: int) -> List[List[Tuple[int, int]]]:
    units: List[List[Tuple[int, int]]] = []
    for r in range(dim):
        units.append([(r, c) for c in range(dim)])
    for c in range(dim):
        units.append([(r, c) for r in range(dim)])
    for sr in range(0, dim, box_h):
        for sc in range(0, dim, box_w):
            units.append([(sr + dr, sc + dc) for dr in range(box_h) for dc in range(box_w)])
    return units


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = _clone_board(state["board"])
    dim = int(state.get("grid_dim") or len(board))
    box_w = int(state.get("box_w") or (2 if dim == 4 else 3))
    box_h = int(state.get("box_h") or (2 if dim in (4, 6) else 3))

    def snap(b: List[List[int]]) -> Dict[str, Any]:
        return {"grid_dim": dim, "box_w": box_w, "box_h": box_h, "board": _clone_board(b)}

    yield {
        "type": "start",
        "state": snap(board),
        "highlights": {},
        "desc": f"Initial {dim}x{dim} Sudoku grid loaded",
        "stats": {"logic_deductions": 0, "backtracks": 0},
    }

    peers_map = {
        (r, c): _get_peers(r, c, dim, box_w, box_h)
        for r in range(dim)
        for c in range(dim)
    }

    # Validate initial givens
    for r in range(dim):
        for c in range(dim):
            val = board[r][c]
            if val != 0:
                for pr, pc in peers_map[(r, c)]:
                    if board[pr][pc] == val:
                        yield {
                            "type": "failed",
                            "state": snap(board),
                            "highlights": {"cells": [[r, c], [pr, pc]], "color": "hot"},
                            "desc": f"Conflict: duplicate {val} at ({r + 1}, {c + 1}) and ({pr + 1}, {pc + 1})",
                            "stats": {},
                        }
                        return

    candidates: List[List[Set[int]]] = [[set() for _ in range(dim)] for _ in range(dim)]
    for r in range(dim):
        for c in range(dim):
            if board[r][c] == 0:
                possible = set(range(1, dim + 1))
                for pr, pc in peers_map[(r, c)]:
                    if board[pr][pc] != 0:
                        possible.discard(board[pr][pc])
                candidates[r][c] = possible

    logic_count = 0
    backtrack_count = 0
    units = _all_units(dim, box_w, box_h)

    # Phase 1: Naked & Hidden Singles
    stalled = False
    while not stalled:
        if should_abort():
            return
        stalled = True

        for r in range(dim):
            for c in range(dim):
                if board[r][c] == 0 and len(candidates[r][c]) == 1:
                    num = next(iter(candidates[r][c]))
                    board[r][c] = num
                    candidates[r][c].clear()
                    logic_count += 1
                    stalled = False
                    for pr, pc in peers_map[(r, c)]:
                        candidates[pr][pc].discard(num)
                    yield {
                        "type": "deduce",
                        "state": snap(board),
                        "highlights": {"cells": [[r, c]], "color": "primary"},
                        "desc": f"Naked Single: ({r + 1}, {c + 1}) = {num}",
                        "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                    }

        if stalled:
            for unit in units:
                for num in range(1, dim + 1):
                    places = [(r, c) for r, c in unit if board[r][c] == 0 and num in candidates[r][c]]
                    if len(places) == 1:
                        r, c = places[0]
                        board[r][c] = num
                        candidates[r][c].clear()
                        logic_count += 1
                        stalled = False
                        for pr, pc in peers_map[(r, c)]:
                            candidates[pr][pc].discard(num)
                        yield {
                            "type": "deduce",
                            "state": snap(board),
                            "highlights": {"cells": [[r, c]], "color": "secondary"},
                            "desc": f"Hidden Single: ({r + 1}, {c + 1}) = {num}",
                            "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                        }

    # Phase 2: MRV Backtracking
    steps_to_confirm: List[Tuple[List[List[int]], int, int, int]] = []

    def is_safe(num: int, r: int, c: int) -> bool:
        return all(board[pr][pc] != num for pr, pc in peers_map[(r, c)])

    def find_mrv() -> Optional[Tuple[int, int]]:
        best = None
        best_count = dim + 1
        for r in range(dim):
            for c in range(dim):
                if board[r][c] == 0:
                    opts = sum(1 for n in range(1, dim + 1) if is_safe(n, r, c))
                    if opts < best_count:
                        best_count = opts
                        best = (r, c)
                        if opts <= 1:
                            return best
        return best

    def backtrack() -> bool:
        nonlocal backtrack_count
        if should_abort():
            return False
        cell = find_mrv()
        if cell is None:
            return True
        r, c = cell
        for num in range(1, dim + 1):
            if is_safe(num, r, c):
                backtrack_count += 1
                board[r][c] = num
                if backtrack():
                    steps_to_confirm.append((_clone_board(board), r, c, num))
                    return True
                board[r][c] = 0
        return False

    if any(0 in row for row in board):
        if not backtrack():
            if not should_abort():
                yield {
                    "type": "failed",
                    "state": snap(board),
                    "highlights": {},
                    "desc": "No valid Sudoku solution exists.",
                    "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                }
            return
        for b_snap, r, c, num in reversed(steps_to_confirm):
            yield {
                "type": "explore",
                "state": snap(b_snap),
                "highlights": {"cells": [[r, c]], "color": "secondary"},
                "desc": f"MRV Branch Confirmed: ({r + 1}, {c + 1}) = {num}",
                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
            }

    yield {
        "type": "solution",
        "state": snap(board),
        "highlights": {},
        "desc": f"Solved {dim}x{dim} Sudoku ({logic_count} deductions, {backtrack_count} guesses)",
        "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
    }
