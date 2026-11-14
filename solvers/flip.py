"""Flip (Lights Out) linear algebra solver over GF(2)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "flip",
    "name": "Flip (Lights Out)",
    "category": "Matrix Toggle",
    "renderer": "grid",
    "description": "Exact Gaussian elimination over GF(2) for Lights Out toggle matrices.",
    "grid_meta": {
        "mode": "binary",
        "min_val": 0,
        "max_val": 1,
        "labels": {"0": "", "1": "●"},
        "colors": {"0": "#25292E", "1": "#00F5D4"},
        "editable": True,
    },
    "presets": {
        "3x3": {
            "board": [
                [1, 0, 1],
                [0, 0, 0],
                [1, 0, 1],
            ]
        },
        "5x5": {
            "board": [
                [0, 0, 1, 0, 0],
                [0, 1, 1, 1, 0],
                [1, 1, 0, 1, 1],
                [0, 1, 1, 1, 0],
                [0, 0, 1, 0, 0],
            ]
        },
        "5x5 Full": {
            "board": [[1] * 5 for _ in range(5)],
        },
        "9x9": {
            "board": [[1] * 9 for _ in range(9)],
        },
    },
    "params": [],
}


def _solve_gf2(rows: int, cols: int, grid: List[List[int]]) -> Optional[List[int]]:
    size = rows * cols
    mat = [[0] * (size + 1) for _ in range(size)]
    for r in range(rows):
        for c in range(cols):
            idx = r * cols + c
            mat[idx][idx] = 1
            if r > 0:
                mat[idx - cols][idx] = 1
            if r < rows - 1:
                mat[idx + cols][idx] = 1
            if c > 0:
                mat[idx - 1][idx] = 1
            if c < cols - 1:
                mat[idx + 1][idx] = 1
            mat[idx][size] = 1 if grid[r][c] else 0

    pivot_row = 0
    for col in range(size):
        if pivot_row >= size:
            break
        sel = pivot_row
        while sel < size and mat[sel][col] == 0:
            sel += 1
        if sel == size:
            continue
        mat[pivot_row], mat[sel] = mat[sel], mat[pivot_row]
        for k in range(pivot_row + 1, size):
            if mat[k][col] == 1:
                for l in range(col, size + 1):
                    mat[k][l] ^= mat[pivot_row][l]
        pivot_row += 1

    for i in range(pivot_row, size):
        if mat[i][size] == 1:
            return None

    x = [0] * size
    for i in range(pivot_row - 1, -1, -1):
        pcol = next((j for j in range(size) if mat[i][j] == 1), -1)
        if pcol != -1:
            val = mat[i][size]
            for j in range(pcol + 1, size):
                val ^= mat[i][j] * x[j]
            x[pcol] = val
    return x


def _toggle(grid: List[List[int]], r: int, c: int) -> None:
    rows, cols = len(grid), len(grid[0])
    for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            grid[nr][nc] ^= 1


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    grid = [list(row) for row in state["board"]]
    rows, cols = len(grid), len(grid[0])

    sol = _solve_gf2(rows, cols, grid)
    if sol is None:
        yield {
            "type": "failed",
            "state": {"board": [list(r) for r in grid]},
            "highlights": {},
            "desc": "Configuration is mathematically unsolvable over GF(2).",
            "stats": {},
        }
        return

    presses: List[Tuple[int, int]] = [divmod(idx, cols) for idx, v in enumerate(sol) if v == 1]

    yield {
        "type": "start",
        "state": {"board": [list(r) for r in grid]},
        "highlights": {"cells": [[r, c] for r, c in presses], "color": "secondary"},
        "desc": f"GF(2) solution requires {len(presses)} button press(es)",
        "stats": {"total_presses": len(presses)},
    }

    if not presses:
        yield {
            "type": "solution",
            "state": {"board": [list(r) for r in grid]},
            "highlights": {},
            "desc": "Already solved (0 presses needed)!",
            "stats": {"total_presses": 0},
        }
        return

    for idx, (r, c) in enumerate(presses, 1):
        if should_abort():
            return
        _toggle(grid, r, c)
        is_last = idx == len(presses)
        yield {
            "type": "solution" if is_last else "deduce",
            "state": {"board": [list(r_row) for r_row in grid]},
            "highlights": {"cells": [[r, c]], "color": "hot"},
            "desc": f"Press ({r + 1}, {c + 1}) [{idx}/{len(presses)}]",
            "stats": {"step": idx, "total_presses": len(presses)},
        }
