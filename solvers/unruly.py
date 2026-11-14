"""Unruly (Takuzu / 0h h1) binary puzzle solver with constraint propagation."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "unruly",
    "name": "Unruly (Binary Puzzle)",
    "category": "State",
    "renderer": "grid",
    "description": "Solves even-sized binary grids: no 3-in-a-row, equal row/col counts, and optional unique lines.",
    "grid_meta": {
        "mode": "cycle",
        "min_val": 0,
        "max_val": 2,
        "labels": {"0": "", "1": "A", "2": "B"},
        "colors": {"0": "#232629", "1": "#69E6D0", "2": "#E76C8F"},
        "editable": True,
        "resizable": True,
        "dim_step": 2,
        "min_dim": 4,
        "max_dim": 10,
    },
    "presets": {
        "6x6": {
            "unique_rows_cols": True,
            "board": [
                [0, 1, 0, 1, 0, 0],
                [0, 0, 0, 0, 2, 0],
                [0, 2, 0, 0, 0, 0],
                [0, 0, 1, 0, 0, 0],
                [2, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 1],
            ],
        },
        "4x4": {
            "unique_rows_cols": True,
            "board": [
                [1, 0, 0, 0],
                [0, 0, 2, 0],
                [0, 1, 0, 0],
                [0, 0, 0, 2],
            ],
        },
    },
    "params": [
        {"key": "unique_rows_cols", "label": "Unique Rows & Cols", "type": "bool", "default": True}
    ],
}


def _is_line_valid(line: List[int], half: int) -> bool:
    for i in range(len(line) - 2):
        if line[i] != 0 and line[i] == line[i + 1] == line[i + 2]:
            return False
    return line.count(1) <= half and line.count(2) <= half


def _propagate(
    b: List[List[int]],
    rows: int,
    cols: int,
    collector: Optional[List[Tuple[int, int, int, str]]] = None,
) -> bool:
    half_row = cols // 2
    half_col = rows // 2
    changed = True
    while changed:
        changed = False
        for r in range(rows):
            if not _is_line_valid(b[r], half_row):
                return False
        for c in range(cols):
            if not _is_line_valid([b[r][c] for r in range(rows)], half_col):
                return False

        # Rows
        for r in range(rows):
            for c in range(cols - 1):
                if b[r][c] != 0 and b[r][c] == b[r][c + 1]:
                    other = 3 - b[r][c]
                    if c > 0 and b[r][c - 1] == 0:
                        b[r][c - 1] = other
                        if collector is not None:
                            collector.append((r, c - 1, other, "Avoid Triple"))
                        changed = True
                    if c < cols - 2 and b[r][c + 2] == 0:
                        b[r][c + 2] = other
                        if collector is not None:
                            collector.append((r, c + 2, other, "Avoid Triple"))
                        changed = True
            for c in range(cols - 2):
                if b[r][c] != 0 and b[r][c] == b[r][c + 2] and b[r][c + 1] == 0:
                    other = 3 - b[r][c]
                    b[r][c + 1] = other
                    if collector is not None:
                        collector.append((r, c + 1, other, "Fill Sandwich"))
                    changed = True
            ca, cb = b[r].count(1), b[r].count(2)
            fill = 2 if ca == half_row and cb < half_row else (1 if cb == half_row and ca < half_row else 0)
            if fill:
                for c in range(cols):
                    if b[r][c] == 0:
                        b[r][c] = fill
                        if collector is not None:
                            collector.append((r, c, fill, "Row Balance"))
                        changed = True

        # Columns
        for c in range(cols):
            for r in range(rows - 1):
                if b[r][c] != 0 and b[r][c] == b[r + 1][c]:
                    other = 3 - b[r][c]
                    if r > 0 and b[r - 1][c] == 0:
                        b[r - 1][c] = other
                        if collector is not None:
                            collector.append((r - 1, c, other, "Avoid Triple"))
                        changed = True
                    if r < rows - 2 and b[r + 2][c] == 0:
                        b[r + 2][c] = other
                        if collector is not None:
                            collector.append((r + 2, c, other, "Avoid Triple"))
                        changed = True
            for r in range(rows - 2):
                if b[r][c] != 0 and b[r][c] == b[r + 2][c] and b[r + 1][c] == 0:
                    other = 3 - b[r][c]
                    b[r + 1][c] = other
                    if collector is not None:
                        collector.append((r + 1, c, other, "Fill Sandwich"))
                    changed = True
            col = [b[r][c] for r in range(rows)]
            ca, cb = col.count(1), col.count(2)
            fill = 2 if ca == half_col and cb < half_col else (1 if cb == half_col and ca < half_col else 0)
            if fill:
                for r in range(rows):
                    if b[r][c] == 0:
                        b[r][c] = fill
                        if collector is not None:
                            collector.append((r, c, fill, "Col Balance"))
                        changed = True
    return True


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = [list(r) for r in state["board"]]
    rows, cols = len(board), len(board[0])
    unique_lines = bool(params.get("unique_rows_cols", state.get("unique_rows_cols", True)))

    yield {
        "type": "start",
        "state": {"board": [list(r) for r in board], "unique_rows_cols": unique_lines},
        "highlights": {},
        "desc": f"Loaded {rows}x{cols} Unruly board",
        "stats": {"rows": rows, "cols": cols},
    }

    if rows < 2 or cols < 2 or rows % 2 != 0 or cols % 2 != 0:
        yield {
            "type": "failed",
            "state": {"board": board},
            "highlights": {},
            "desc": f"Pre-solve check failed: grid dimensions {rows}x{cols} must both be even.",
            "stats": {},
        }
        return

    logic_steps: List[Tuple[int, int, int, str]] = []
    if not _propagate(board, rows, cols, collector=logic_steps):
        yield {
            "type": "failed",
            "state": {"board": board},
            "highlights": {},
            "desc": "Pre-solve contradiction: initial givens violate 3-in-a-row or row/col N/2 quota.",
            "stats": {},
        }
        return

    replay = [list(r) for r in state["board"]]
    for r, c, val, reason in logic_steps:
        if should_abort():
            return
        replay[r][c] = val
        yield {
            "type": "deduce",
            "state": {"board": [list(row) for row in replay], "unique_rows_cols": unique_lines},
            "highlights": {"cells": [[r, c]], "color": "primary"},
            "desc": f"{reason}: ({r + 1}, {c + 1}) = {'A' if val == 1 else 'B'}",
            "stats": {"deductions": len(logic_steps)},
        }

    branch_snapshots: List[Tuple[List[List[int]], int, int, int]] = []

    def backtrack(cur: List[List[int]]) -> Optional[List[List[int]]]:
        if should_abort():
            return None
        pos = next(((r, c) for r in range(rows) for c in range(cols) if cur[r][c] == 0), None)
        if pos is None:
            if unique_lines:
                if len({tuple(r) for r in cur}) != rows:
                    return None
                if len({tuple(cur[r][c] for r in range(rows)) for c in range(cols)}) != cols:
                    return None
            return cur
        er, ec = pos
        for cand in (1, 2):
            nxt = [list(row) for row in cur]
            nxt[er][ec] = cand
            if _propagate(nxt, rows, cols):
                res = backtrack(nxt)
                if res is not None:
                    branch_snapshots.append(([list(row) for row in nxt], er, ec, cand))
                    return res
        return None

    solved_board = board
    if any(0 in row for row in board):
        res = backtrack(board)
        if res is None:
            if not should_abort():
                yield {
                    "type": "failed",
                    "state": {"board": board},
                    "highlights": {},
                    "desc": "No valid Unruly solution exists.",
                    "stats": {},
                }
            return
        for idx, (snap_b, r, c, val) in enumerate(reversed(branch_snapshots)):
            prefix = "Deduction stalled -> " if idx == 0 else ""
            yield {
                "type": "explore",
                "state": {"board": snap_b, "unique_rows_cols": unique_lines},
                "highlights": {"cells": [[r, c]], "color": "secondary"},
                "desc": f"{prefix}Branch ({r + 1}, {c + 1}) = {'A' if val == 1 else 'B'}",
                "stats": {},
            }
        solved_board = res

    yield {
        "type": "solution",
        "state": {"board": solved_board, "unique_rows_cols": unique_lines},
        "highlights": {},
        "desc": "Unruly solved! All parity & run-length rules satisfied.",
        "stats": {},
    }
