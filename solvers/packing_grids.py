"""Packing Grids: Nonogram (Picross) line-intersection deduction + backtracking solver."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional

META: Dict[str, Any] = {
    "slug": "packing_grids",
    "name": "Packing Grids (Nonogram)",
    "category": "State",
    "renderer": "grid",
    "description": "Solves Nonogram / Picross grids via line-pattern intersection and backtracking.",
    "grid_meta": {
        "mode": "binary",
        "min_val": 0,
        "max_val": 1,
        "labels": {"0": "", "1": "■"},
        "colors": {"0": "#232629", "1": "#00F5D4"},
        "editable": True,
        "resizable": True,
        "min_dim": 2,
        "max_dim": 10,
    },
    "presets": {
        "5x5": {
            "row_clues": [[1, 1], [5], [5], [3], [1]],
            "col_clues": [[2], [4], [4], [4], [2]],
            "board": [[0] * 5 for _ in range(5)],
        },
        "5x5 Crosshair": {
            "row_clues": [[1], [3], [5], [3], [1]],
            "col_clues": [[1], [3], [5], [3], [1]],
            "board": [[0] * 5 for _ in range(5)],
        },
        "6x6": {
            "row_clues": [[6], [4], [2], [2], [4], [6]],
            "col_clues": [[1, 1], [2, 2], [6], [6], [2, 2], [1, 1]],
            "board": [[0] * 6 for _ in range(6)],
        },
    },
    "params": [],
}


def _line_candidates(length: int, clue: List[int], current: List[int]) -> List[List[int]]:
    clean_clue = [c for c in clue if c > 0]
    if not clean_clue:
        cand = [-1] * length
        return [cand] if all(current[i] in (0, -1) for i in range(length)) else []

    results: List[List[int]] = []

    def gen(idx: int, pos: int, line: List[int]) -> None:
        if idx == len(clean_clue):
            for k in range(pos, length):
                if current[k] == 1:
                    return
                line[k] = -1
            results.append(list(line))
            return

        run = clean_clue[idx]
        min_rem = sum(clean_clue[idx + 1 :]) + (len(clean_clue) - idx - 1)
        max_start = length - run - min_rem
        for start in range(pos, max_start + 1):
            # Prefix must be empty (-1)
            if any(current[k] == 1 for k in range(pos, start)):
                break
            if any(current[k] == -1 for k in range(start, start + run)):
                continue
            if idx < len(clean_clue) - 1 and current[start + run] == 1:
                continue
            for k in range(pos, start):
                line[k] = -1
            for k in range(start, start + run):
                line[k] = 1
            nxt_pos = start + run
            if idx < len(clean_clue) - 1:
                line[nxt_pos] = -1
                nxt_pos += 1
            gen(idx + 1, nxt_pos, line)

    gen(0, 0, [0] * length)
    return results


def _propagate(
    grid: List[List[int]],
    row_clues: List[List[int]],
    col_clues: List[List[int]],
    steps: Optional[List[Tuple[int, int, int, str]]] = None,
) -> bool:
    rows, cols = len(grid), len(grid[0])
    changed = True
    while changed:
        changed = False
        for r in range(rows):
            cands = _line_candidates(cols, row_clues[r], grid[r])
            if not cands:
                return False
            for c in range(cols):
                if grid[r][c] == 0:
                    vals = {cand[c] for cand in cands}
                    if len(vals) == 1:
                        v = next(iter(vals))
                        grid[r][c] = v
                        changed = True
                        if steps is not None and v == 1:
                            steps.append((r, c, 1, f"Row {r + 1} Intersection"))

        for c in range(cols):
            col_line = [grid[r][c] for r in range(rows)]
            cands = _line_candidates(rows, col_clues[c], col_line)
            if not cands:
                return False
            for r in range(rows):
                if grid[r][c] == 0:
                    vals = {cand[r] for cand in cands}
                    if len(vals) == 1:
                        v = next(iter(vals))
                        grid[r][c] = v
                        changed = True
                        if steps is not None and v == 1:
                            steps.append((r, c, 1, f"Col {c + 1} Intersection"))
    return True


def _to_display(grid: List[List[int]]) -> List[List[int]]:
    return [[1 if cell == 1 else 0 for cell in row] for row in grid]


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    row_clues: List[List[int]] = state["row_clues"]
    col_clues: List[List[int]] = state["col_clues"]
    rows, cols = len(row_clues), len(col_clues)
    grid = [[0] * cols for _ in range(rows)]

    def snap(g: List[List[int]]) -> Dict[str, Any]:
        return {"row_clues": row_clues, "col_clues": col_clues, "board": _to_display(g)}

    yield {
        "type": "start",
        "state": snap(grid),
        "highlights": {},
        "desc": f"Loaded {rows}x{cols} Nonogram",
        "stats": {"rows": rows, "cols": cols},
    }

    row_sum = sum(sum(r) for r in row_clues)
    col_sum = sum(sum(c) for c in col_clues)
    if row_sum != col_sum:
        yield {
            "type": "failed",
            "state": snap(grid),
            "highlights": {},
            "desc": f"Pre-solve parity check failed: row clue sum ({row_sum}) != col clue sum ({col_sum}).",
            "stats": {},
        }
        return

    steps: List[Tuple[int, int, int, str]] = []
    if not _propagate(grid, row_clues, col_clues, steps=steps):
        yield {
            "type": "failed",
            "state": snap(grid),
            "highlights": {},
            "desc": "Pre-solve contradiction: line clues cannot be satisfied on this grid.",
            "stats": {},
        }
        return

    replay = [[0] * cols for _ in range(rows)]
    for r, c, val, desc in steps:
        if should_abort():
            return
        replay[r][c] = val
        yield {
            "type": "deduce",
            "state": snap(replay),
            "highlights": {"cells": [[r, c]], "color": "primary"},
            "desc": f"{desc}: fill ({r + 1}, {c + 1})",
            "stats": {},
        }

    def backtrack(cur: List[List[int]]) -> Optional[List[List[int]]]:
        if should_abort():
            return None
        pos = next(((r, c) for r in range(rows) for c in range(cols) if cur[r][c] == 0), None)
        if pos is None:
            return cur
        er, ec = pos
        for cand in (1, -1):
            nxt = [list(r) for r in cur]
            nxt[er][ec] = cand
            if _propagate(nxt, row_clues, col_clues):
                res = backtrack(nxt)
                if res is not None:
                    return res
        return None

    solved = grid
    if any(0 in r for r in grid):
        yield {
            "type": "explore",
            "state": snap(grid),
            "highlights": {},
            "desc": "Line deduction stalled -> entering backtracking search",
            "stats": {},
        }
        res = backtrack(grid)
        if res is None:
            if not should_abort():
                yield {
                    "type": "failed",
                    "state": snap(grid),
                    "highlights": {},
                    "desc": "Mid-solve contradiction: search exhausted all branches.",
                    "stats": {},
                }
            return
        solved = res

    filled = [[r, c] for r in range(rows) for c in range(cols) if solved[r][c] == 1]
    yield {
        "type": "solution",
        "state": snap(solved),
        "highlights": {"cells": filled, "color": "primary"},
        "desc": f"Nonogram solved! ({len(filled)} filled pixels)",
        "stats": {"filled": len(filled)},
    }
