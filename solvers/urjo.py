"""Urjo binary puzzle solver: line balance, adjacent line disparity, and Moore neighborhood clues."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "urjo",
    "name": "Urjo",
    "category": "State",
    "renderer": "grid",
    "description": "Dual-color grid with Moore neighborhood clues (0-8), row/col balance, and adjacent line disparity.",
    "grid_meta": {
        "mode": "cycle",
        "min_val": 0,
        "max_val": 2,
        "labels": {"0": "", "1": "B", "2": "R"},
        "colors": {"0": "#232629", "1": "#3498DB", "2": "#E74C3C"},
        "editable": True,
        "resizable": True,
        "dim_step": 2,
        "min_dim": 4,
        "max_dim": 8,
    },
    "presets": {
        "6x6": {
            "board": [
                [2, 0, 0, 0, 1, 0],
                [0, 1, 0, 0, 0, 0],
                [0, 0, 1, 2, 0, 0],
                [0, 0, 2, 1, 0, 0],
                [2, 0, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 1],
            ],
            "clues": [
                [2, None, None, None, 3, None],
                [None, 3, None, None, None, None],
                [None, None, 4, 4, None, None],
                [None, None, 3, 4, None, None],
                [1, None, None, None, 3, None],
                [None, None, None, None, None, 1],
            ],
        },
        "4x4": {
            "board": [
                [2, 0, 0, 0],
                [0, 2, 1, 0],
                [0, 0, 0, 0],
                [0, 0, 0, 2],
            ],
            "clues": [
                [1, None, None, None],
                [None, 4, 4, None],
                [None, None, None, None],
                [None, None, None, 1],
            ],
        },
    },
    "params": [],
}


def _neighbors(r: int, c: int, rows: int, cols: int) -> List[Tuple[int, int]]:
    out = []
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                out.append((nr, nc))
    return out


def _propagate(
    b: List[List[int]],
    clues: List[List[Optional[int]]],
    rows: int,
    cols: int,
    collector: Optional[List[Tuple[int, int, int, str]]] = None,
) -> bool:
    half_row = cols // 2
    half_col = rows // 2
    changed = True
    while changed:
        changed = False
        # 1. Line balance
        for r in range(rows):
            cr, cb = b[r].count(1), b[r].count(2)
            if cr > half_row or cb > half_row:
                return False
            fill = 2 if cr == half_row and cb < half_row else (1 if cb == half_row and cr < half_row else 0)
            if fill:
                for c in range(cols):
                    if b[r][c] == 0:
                        b[r][c] = fill
                        if collector is not None:
                            collector.append((r, c, fill, f"Row {r + 1} Balance"))
                        changed = True

        for c in range(cols):
            col = [b[r][c] for r in range(rows)]
            cr, cb = col.count(1), col.count(2)
            if cr > half_col or cb > half_col:
                return False
            fill = 2 if cr == half_col and cb < half_col else (1 if cb == half_col and cr < half_col else 0)
            if fill:
                for r in range(rows):
                    if b[r][c] == 0:
                        b[r][c] = fill
                        if collector is not None:
                            collector.append((r, c, fill, f"Col {c + 1} Balance"))
                        changed = True

        # 2. Adjacent line disparity
        for r in range(rows - 1):
            r1, r2 = b[r], b[r + 1]
            if 0 not in r1 and 0 not in r2 and r1 == r2:
                return False
            e1 = [c for c in range(cols) if r1[c] == 0]
            e2 = [c for c in range(cols) if r2[c] == 0]
            if len(e1) == 1 and not e2:
                c = e1[0]
                if all(r1[i] == r2[i] for i in range(cols) if i != c):
                    b[r][c] = 3 - r2[c]
                    if collector is not None:
                        collector.append((r, c, b[r][c], f"Adjacent Row Disparity {r + 1}-{r + 2}"))
                    changed = True
            elif len(e2) == 1 and not e1:
                c = e2[0]
                if all(r1[i] == r2[i] for i in range(cols) if i != c):
                    b[r + 1][c] = 3 - r1[c]
                    if collector is not None:
                        collector.append((r + 1, c, b[r + 1][c], f"Adjacent Row Disparity {r + 1}-{r + 2}"))
                    changed = True

        for c in range(cols - 1):
            c1 = [b[r][c] for r in range(rows)]
            c2 = [b[r][c + 1] for r in range(rows)]
            if 0 not in c1 and 0 not in c2 and c1 == c2:
                return False
            e1 = [r for r in range(rows) if c1[r] == 0]
            e2 = [r for r in range(rows) if c2[r] == 0]
            if len(e1) == 1 and not e2:
                r = e1[0]
                if all(c1[i] == c2[i] for i in range(rows) if i != r):
                    b[r][c] = 3 - c2[r]
                    if collector is not None:
                        collector.append((r, c, b[r][c], f"Adjacent Col Disparity {c + 1}-{c + 2}"))
                    changed = True
            elif len(e2) == 1 and not e1:
                r = e2[0]
                if all(c1[i] == c2[i] for i in range(rows) if i != r):
                    b[r][c + 1] = 3 - c1[r]
                    if collector is not None:
                        collector.append((r, c + 1, b[r][c + 1], f"Adjacent Col Disparity {c + 1}-{c + 2}"))
                    changed = True

        # 3. Moore neighborhood clues
        for r in range(rows):
            for c in range(cols):
                k = clues[r][c]
                if k is None:
                    continue
                nbrs = _neighbors(r, c, rows, cols)
                col = b[r][c]
                if col == 0:
                    r_same = sum(1 for nr, nc in nbrs if b[nr][nc] == 1)
                    r_emp = sum(1 for nr, nc in nbrs if b[nr][nc] == 0)
                    b_same = sum(1 for nr, nc in nbrs if b[nr][nc] == 2)
                    b_emp = sum(1 for nr, nc in nbrs if b[nr][nc] == 0)
                    r_ok = r_same <= k <= r_same + r_emp
                    b_ok = b_same <= k <= b_same + b_emp
                    if not r_ok and not b_ok:
                        return False
                    if r_ok and not b_ok:
                        b[r][c] = col = 1
                        if collector is not None:
                            collector.append((r, c, 1, f"Clue {k} Forces Blue"))
                        changed = True
                    elif b_ok and not r_ok:
                        b[r][c] = col = 2
                        if collector is not None:
                            collector.append((r, c, 2, f"Clue {k} Forces Red"))
                        changed = True

                if col != 0:
                    same = sum(1 for nr, nc in nbrs if b[nr][nc] == col)
                    emp_nbrs = [(nr, nc) for nr, nc in nbrs if b[nr][nc] == 0]
                    if same > k or same + len(emp_nbrs) < k:
                        return False
                    opp = 3 - col
                    if same == k and emp_nbrs:
                        for nr, nc in emp_nbrs:
                            b[nr][nc] = opp
                            if collector is not None:
                                collector.append((nr, nc, opp, f"Clue ({r + 1},{c + 1})={k} Saturated"))
                            changed = True
                    elif same + len(emp_nbrs) == k and emp_nbrs:
                        for nr, nc in emp_nbrs:
                            b[nr][nc] = col
                            if collector is not None:
                                collector.append((nr, nc, col, f"Clue ({r + 1},{c + 1})={k} Demands"))
                            changed = True

        # 4. Coupled constraints (clue <-> clue and clue <-> row/col balance)
        constraints: List[Tuple[str, set[Tuple[int, int]], int]] = []
        for r in range(rows):
            for c in range(cols):
                k = clues[r][c]
                col = b[r][c]
                if k is None or col == 0:
                    continue
                nbrs = _neighbors(r, c, rows, cols)
                emp = {(nr, nc) for nr, nc in nbrs if b[nr][nc] == 0}
                if not emp:
                    continue
                same = sum(1 for nr, nc in nbrs if b[nr][nc] == col)
                need_same = k - same
                need_blue = need_same if col == 1 else len(emp) - need_same
                constraints.append((f"Clue ({r + 1},{c + 1})", emp, need_blue))

        for r in range(rows):
            emp_r = {(r, c) for c in range(cols) if b[r][c] == 0}
            if emp_r:
                constraints.append((f"Row {r + 1}", emp_r, half_row - b[r].count(1)))
        for c in range(cols):
            emp_c = {(r, c) for r in range(rows) if b[r][c] == 0}
            if emp_c:
                constraints.append((f"Col {c + 1}", emp_c, half_col - sum(1 for r in range(rows) if b[r][c] == 1)))

        forced_any = False
        for la, ea, na in constraints:
            for lb, eb, nb in constraints:
                if la == lb:
                    continue
                shared = ea & eb
                rem_b = eb - shared
                if not shared or not rem_b:
                    continue
                min_s = max(0, na - len(ea - shared))
                max_s = min(len(shared), na)
                min_rem = nb - max_s
                max_rem = nb - min_s
                if min_rem > len(rem_b) or max_rem < 0:
                    return False
                fill = 1 if min_rem == len(rem_b) else (2 if max_rem == 0 else 0)
                if fill:
                    reason = f"Coupled {la} & {lb}"
                    for nr, nc in sorted(rem_b):
                        if b[nr][nc] == 0:
                            b[nr][nc] = fill
                            if collector is not None:
                                collector.append((nr, nc, fill, reason))
                            changed = True
                            forced_any = True
            if forced_any:
                break
    return True


def _is_solved(b: List[List[int]], clues: List[List[Optional[int]]], rows: int, cols: int) -> bool:
    half_row = cols // 2
    half_col = rows // 2
    for r in range(rows):
        if 0 in b[r] or b[r].count(1) != half_row:
            return False
        if r < rows - 1 and b[r] == b[r + 1]:
            return False
    for c in range(cols):
        col = [b[r][c] for r in range(rows)]
        if col.count(1) != half_col:
            return False
        if c < cols - 1 and col == [b[r][c + 1] for r in range(rows)]:
            return False
    for r in range(rows):
        for c in range(cols):
            k = clues[r][c]
            if k is not None:
                same = sum(1 for nr, nc in _neighbors(r, c, rows, cols) if b[nr][nc] == b[r][c])
                if same != k:
                    return False
    return True


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = [list(r) for r in state["board"]]
    rows, cols = len(board), len(board[0])
    raw_clues = state.get("clues") or []
    clues: List[List[Optional[int]]] = [
        [raw_clues[r][c] if r < len(raw_clues) and c < len(raw_clues[r]) else None for c in range(cols)]
        for r in range(rows)
    ]

    yield {
        "type": "start",
        "state": {"board": [list(r) for r in board], "clues": clues},
        "highlights": {},
        "desc": f"Initial Urjo {rows}x{cols} setup",
        "stats": {"rows": rows, "cols": cols},
    }

    if rows < 2 or cols < 2 or rows % 2 != 0 or cols % 2 != 0:
        yield {
            "type": "failed",
            "state": {"board": board, "clues": clues},
            "highlights": {},
            "desc": f"Pre-solve check failed: grid dimensions {rows}x{cols} must both be even.",
            "stats": {},
        }
        return

    logic_steps: List[Tuple[int, int, int, str]] = []
    if not _propagate(board, clues, rows, cols, collector=logic_steps):
        yield {
            "type": "failed",
            "state": {"board": board, "clues": clues},
            "highlights": {},
            "desc": "Pre-solve contradiction: initial clues violate adjacency or row/col N/2 parity.",
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
            "state": {"board": [list(row) for row in replay], "clues": clues},
            "highlights": {"cells": [[r, c]], "color": "primary"},
            "desc": f"{reason}: ({r + 1}, {c + 1}) = {'Blue' if val == 1 else 'Red'}",
            "stats": {"deductions": len(logic_steps)},
        }

    def backtrack(
        cur: List[List[int]], depth: int = 0
    ) -> Generator[Dict[str, Any], None, Optional[List[List[int]]]]:
        if should_abort():
            return None
        row_empties = [cur[r].count(0) for r in range(rows)]
        col_empties = [sum(1 for r in range(rows) if cur[r][c] == 0) for c in range(cols)]
        best = None
        best_score: Tuple[int, int, int, int] = (-1, -1, -1, -1)
        for r in range(rows):
            for c in range(cols):
                if cur[r][c] == 0:
                    nbrs = _neighbors(r, c, rows, cols)
                    own = 1 if clues[r][c] is not None else 0
                    adj_active = sum(1 for nr, nc in nbrs if clues[nr][nc] is not None and cur[nr][nc] != 0)
                    adj_all = sum(1 for nr, nc in nbrs if clues[nr][nc] is not None)
                    tightness = max(cols - row_empties[r], rows - col_empties[c])
                    score = (own, adj_active, tightness, adj_all)
                    if score > best_score:
                        best_score = score
                        best = (r, c)
        if best is None:
            return cur if _is_solved(cur, clues, rows, cols) else None

        er, ec = best
        for cand in (1, 2):
            if should_abort():
                return None
            nxt = [list(row) for row in cur]
            nxt[er][ec] = cand
            label = "Blue" if cand == 1 else "Red"
            prefix = "Deduction stalled -> " if depth == 0 and cand == 1 else ""
            yield {
                "type": "explore",
                "state": {"board": [list(row) for row in nxt], "clues": clues},
                "highlights": {"cells": [[er, ec]], "color": "secondary"},
                "desc": f"{prefix}Branch d={depth + 1}: ({er + 1}, {ec + 1}) = {label}",
                "stats": {"depth": depth + 1},
            }

            branch_steps: List[Tuple[int, int, int, str]] = []
            replay_branch = [list(row) for row in nxt]
            ok = _propagate(nxt, clues, rows, cols, collector=branch_steps)
            for sr, sc, sval, reason in branch_steps:
                if should_abort():
                    return None
                replay_branch[sr][sc] = sval
                yield {
                    "type": "deduce",
                    "state": {"board": [list(row) for row in replay_branch], "clues": clues},
                    "highlights": {"cells": [[sr, sc]], "color": "primary"},
                    "desc": f"[d={depth + 1}] {reason}: ({sr + 1}, {sc + 1}) = {'Blue' if sval == 1 else 'Red'}",
                    "stats": {"depth": depth + 1},
                }

            if ok:
                res = yield from backtrack(nxt, depth + 1)
                if res is not None:
                    return res
                if should_abort():
                    return None

            yield {
                "type": "backtrack",
                "state": {"board": [list(row) for row in cur], "clues": clues},
                "highlights": {"cells": [[er, ec]], "color": "hot"},
                "desc": f"[d={depth + 1}] {'Contradiction' if not ok else 'Dead end'} for ({er + 1}, {ec + 1}) = {label} -> backtrack",
                "stats": {"depth": depth + 1},
            }
        return None

    solved_board = board
    if any(0 in row for row in board):
        res = yield from backtrack(board)
        if res is None:
            if not should_abort():
                yield {
                    "type": "failed",
                    "state": {"board": board, "clues": clues},
                    "highlights": {},
                    "desc": "No valid Urjo solution exists.",
                    "stats": {},
                }
            return
        solved_board = res

    yield {
        "type": "solution",
        "state": {"board": solved_board, "clues": clues},
        "highlights": {},
        "desc": "Urjo solved! All clues, parity & disparity rules satisfied.",
        "stats": {},
    }
