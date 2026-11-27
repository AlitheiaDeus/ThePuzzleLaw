"""Unruly (Takuzu / 0h h1) binary puzzle solver with constraint propagation."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "unruly",
    "name": "Unruly",
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
    unique_lines: bool = True,
) -> Tuple[bool, str]:
    half_row = cols // 2
    half_col = rows // 2
    changed = True
    while changed:
        changed = False
        for r in range(rows):
            if not _is_line_valid(b[r], half_row):
                return False, f"Row {r + 1} violates 3-in-a-row or N/2 quota"
        for c in range(cols):
            if not _is_line_valid([b[r][c] for r in range(rows)], half_col):
                return False, f"Col {c + 1} violates 3-in-a-row or N/2 quota"

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

        if changed:
            continue

        # Quota Lookahead (1 remaining of color v -> placing v must not force triple of 3-v in remaining empties)
        for r in range(rows):
            empties = [c for c in range(cols) if b[r][c] == 0]
            if len(empties) >= 3:
                for v in (1, 2):
                    need_v = half_row - b[r].count(v)
                    if need_v == 1:
                        opp = 3 - v
                        for ec in empties:
                            test = list(b[r])
                            for c2 in empties:
                                test[c2] = v if c2 == ec else opp
                            if not _is_line_valid(test, half_row):
                                b[r][ec] = opp
                                if collector is not None:
                                    collector.append((r, ec, opp, "Row Quota Triple Prevention"))
                                changed = True
                                break
                    if changed:
                        break
                if changed:
                    break
        if changed:
            continue

        for c in range(cols):
            col = [b[r][c] for r in range(rows)]
            empties = [r for r in range(rows) if col[r] == 0]
            if len(empties) >= 3:
                for v in (1, 2):
                    need_v = half_col - col.count(v)
                    if need_v == 1:
                        opp = 3 - v
                        for er in empties:
                            test = list(col)
                            for r2 in empties:
                                test[r2] = v if r2 == er else opp
                            if not _is_line_valid(test, half_col):
                                b[er][c] = opp
                                if collector is not None:
                                    collector.append((er, c, opp, "Col Quota Triple Prevention"))
                                changed = True
                                break
                    if changed:
                        break
                if changed:
                    break
        if changed:
            continue

        # Unique Rows & Cols Elimination
        if unique_lines:
            full_rows = [tuple(b[r]) for r in range(rows) if 0 not in b[r]]
            if len(full_rows) != len(set(full_rows)):
                return False, "Duplicate completed rows (Unique Rows & Cols enabled)"
            for r in range(rows):
                empties = [c for c in range(cols) if b[r][c] == 0]
                if len(empties) == 2:
                    c1, c2 = empties
                    for fr in full_rows:
                        if all(b[r][k] == fr[k] for k in range(cols) if k not in (c1, c2)):
                            if fr[c1] != fr[c2]:
                                b[r][c1], b[r][c2] = fr[c2], fr[c1]
                                if collector is not None:
                                    collector.append((r, c1, b[r][c1], "Unique Row Elimination"))
                                    collector.append((r, c2, b[r][c2], "Unique Row Elimination"))
                                changed = True
                                break
                    if changed:
                        break
            if changed:
                continue

            full_cols = [tuple(b[r][c] for r in range(rows)) for c in range(cols)]
            done_cols = [col for col in full_cols if 0 not in col]
            if len(done_cols) != len(set(done_cols)):
                return False, "Duplicate completed columns (Unique Rows & Cols enabled)"
            for c in range(cols):
                col = full_cols[c]
                empties = [r for r in range(rows) if col[r] == 0]
                if len(empties) == 2:
                    r1, r2 = empties
                    for fc in done_cols:
                        if all(col[k] == fc[k] for k in range(rows) if k not in (r1, r2)):
                            if fc[r1] != fc[r2]:
                                b[r1][c], b[r2][c] = fc[r2], fc[r1]
                                if collector is not None:
                                    collector.append((r1, c, b[r1][c], "Unique Col Elimination"))
                                    collector.append((r2, c, b[r2][c], "Unique Col Elimination"))
                                changed = True
                                break
                    if changed:
                        break
    return True, ""


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
    ok, fail_reason = _propagate(board, rows, cols, collector=logic_steps, unique_lines=unique_lines)

    replay = [list(r) for r in state["board"]]
    ded_count = 0
    for r, c, val, reason in logic_steps:
        if should_abort():
            return
        replay[r][c] = val
        ded_count += 1
        yield {
            "type": "deduce",
            "state": {"board": [list(row) for row in replay], "unique_rows_cols": unique_lines},
            "highlights": {"cells": [[r, c]], "color": "primary"},
            "desc": f"{reason}: ({r + 1}, {c + 1}) = {'A' if val == 1 else 'B'}",
            "stats": {"deductions": ded_count},
        }

    if not ok:
        yield {
            "type": "failed",
            "state": {"board": [list(row) for row in replay], "unique_rows_cols": unique_lines},
            "highlights": {},
            "desc": f"Contradiction: {fail_reason}.",
            "stats": {"deductions": ded_count},
        }
        return

    stats = {"deductions": ded_count, "branches": 0, "backtracks": 0}
    stalled_emitted = False

    def backtrack_gen(cur: List[List[int]]) -> Generator[Dict[str, Any], None, Optional[List[List[int]]]]:
        nonlocal stalled_emitted
        if should_abort():
            return None
        pos = next(((r, c) for r in range(rows) for c in range(cols) if cur[r][c] == 0), None)
        if pos is None:
            if unique_lines:
                if len({tuple(r) for r in cur}) != rows or len({tuple(cur[r][c] for r in range(rows)) for c in range(cols)}) != cols:
                    return None
            return cur
        er, ec = pos
        for cand in (1, 2):
            if should_abort():
                return None
            stats["branches"] += 1
            nxt = [list(row) for row in cur]
            nxt[er][ec] = cand
            prefix = "Deduction stalled -> " if not stalled_emitted else ""
            stalled_emitted = True
            yield {
                "type": "explore",
                "state": {"board": [list(row) for row in nxt], "unique_rows_cols": unique_lines},
                "highlights": {"cells": [[er, ec]], "color": "secondary"},
                "desc": f"{prefix}Branch ({er + 1}, {ec + 1}) = {'A' if cand == 1 else 'B'}",
                "stats": dict(stats),
            }
            sub_steps: List[Tuple[int, int, int, str]] = []
            sub_ok, sub_err = _propagate(nxt, rows, cols, collector=sub_steps, unique_lines=unique_lines)
            b_replay = [list(row) for row in cur]
            b_replay[er][ec] = cand
            for sr, sc, sval, sreason in sub_steps:
                b_replay[sr][sc] = sval
                stats["deductions"] += 1
                yield {
                    "type": "deduce",
                    "state": {"board": [list(row) for row in b_replay], "unique_rows_cols": unique_lines},
                    "highlights": {"cells": [[sr, sc]], "color": "primary"},
                    "desc": f"{sreason}: ({sr + 1}, {sc + 1}) = {'A' if sval == 1 else 'B'}",
                    "stats": dict(stats),
                }
            if sub_ok:
                res = yield from backtrack_gen(nxt)
                if res is not None:
                    return res
            else:
                stats["backtracks"] += 1
                yield {
                    "type": "backtrack",
                    "state": {"board": [list(row) for row in cur], "unique_rows_cols": unique_lines},
                    "highlights": {"cells": [[er, ec]], "color": "hot"},
                    "desc": f"Contradiction ({sub_err}) -> backtrack ({er + 1}, {ec + 1})",
                    "stats": dict(stats),
                }
        return None

    solved_board = board
    if any(0 in row for row in board):
        res = yield from backtrack_gen(board)
        if res is None:
            if not should_abort():
                yield {
                    "type": "failed",
                    "state": {"board": board, "unique_rows_cols": unique_lines},
                    "highlights": {},
                    "desc": "No valid Unruly solution exists.",
                    "stats": dict(stats),
                }
            return
        solved_board = res

    yield {
        "type": "solution",
        "state": {"board": solved_board, "unique_rows_cols": unique_lines},
        "highlights": {},
        "desc": "Unruly solved! All parity & run-length rules satisfied.",
        "stats": dict(stats),
    }
