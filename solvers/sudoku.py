"""Sudoku hybrid solver: Naked/Hidden Singles + MRV recursive backtracking."""

from __future__ import annotations

from itertools import combinations
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

META: Dict[str, Any] = {
    "slug": "sudoku",
    "name": "Sudoku",
    "category": "State",
    "renderer": "grid",
    "description": "Solves 4x4, 6x6, or 9x9 Sudoku grids using Naked/Hidden Singles followed by MRV backtracking.",
    "grid_meta": {
        "mode": "number",
        "min_val": 0,
        "max_val": 9,
        "empty_val": 0,
        "editable": True,
        "size_layouts": [
            {"label": "4x4 (2x2)", "dim": 4, "box_w": 2, "box_h": 2},
            {"label": "6x6 (3x2)", "dim": 6, "box_w": 3, "box_h": 2},
            {"label": "6x6 (2x3)", "dim": 6, "box_w": 2, "box_h": 3},
            {"label": "9x9 (3x3)", "dim": 9, "box_w": 3, "box_h": 3},
        ],
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
    row_units = units[:dim]
    col_units = units[dim : 2 * dim]
    box_units = units[2 * dim :]

    def place_digit(r: int, c: int, num: int, reason: str, color: str = "primary") -> Dict[str, Any]:
        nonlocal logic_count
        board[r][c] = num
        candidates[r][c].clear()
        logic_count += 1
        for pr, pc in peers_map[(r, c)]:
            candidates[pr][pc].discard(num)
        return {
            "type": "deduce",
            "state": snap(board),
            "highlights": {"cells": [[r, c]], "color": color},
            "desc": reason,
            "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
        }

    # Phase 1: Singles, Locked Candidates, Naked/Hidden Subsets, X-Wing/Swordfish, XY-Wing
    stalled = False
    while not stalled:
        if should_abort():
            return
        stalled = True

        # Check contradiction
        for r in range(dim):
            for c in range(dim):
                if board[r][c] == 0 and not candidates[r][c]:
                    yield {
                        "type": "failed",
                        "state": snap(board),
                        "highlights": {"cells": [[r, c]], "color": "hot"},
                        "desc": f"Contradiction at ({r + 1},{c + 1}): 0 candidates remaining.",
                        "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                    }
                    return

        # 1. Naked Singles
        for r in range(dim):
            for c in range(dim):
                if board[r][c] == 0 and len(candidates[r][c]) == 1:
                    num = next(iter(candidates[r][c]))
                    stalled = False
                    yield place_digit(r, c, num, f"Naked Single at ({r + 1},{c + 1}): only candidate {{{num}}}", "primary")

        if not stalled:
            continue

        # 2. Hidden Singles
        for unit in units:
            for num in range(1, dim + 1):
                places = [(r, c) for r, c in unit if board[r][c] == 0 and num in candidates[r][c]]
                if len(places) == 1:
                    r, c = places[0]
                    stalled = False
                    yield place_digit(r, c, num, f"Hidden Single at ({r + 1},{c + 1}): only place for {num} in unit", "secondary")
                    break
            if not stalled:
                break
        if not stalled:
            continue

        # 3. Locked Candidates (Pointing Pairs/Triples & Box-Line Claiming)
        for b_idx, box in enumerate(box_units):
            box_set = set(box)
            for num in range(1, dim + 1):
                places = [(r, c) for r, c in box if board[r][c] == 0 and num in candidates[r][c]]
                if len(places) >= 2:
                    rs = {r for r, _ in places}
                    if len(rs) == 1:
                        rr = next(iter(rs))
                        killed = [(rr, c) for c in range(dim) if (rr, c) not in box_set and num in candidates[rr][c]]
                        if killed:
                            for kr, kc in killed:
                                candidates[kr][kc].discard(num)
                            logic_count += 1
                            stalled = False
                            yield {
                                "type": "deduce",
                                "state": snap(board),
                                "highlights": {"cells": [[r, c] for r, c in killed], "color": "secondary"},
                                "desc": f"Pointing (Box {b_idx + 1} -> Row {rr + 1}): eliminated {num} from {len(killed)} cell(s)",
                                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                            }
                            break
                    cs = {c for _, c in places}
                    if len(cs) == 1:
                        cc = next(iter(cs))
                        killed = [(r, cc) for r in range(dim) if (r, cc) not in box_set and num in candidates[r][cc]]
                        if killed:
                            for kr, kc in killed:
                                candidates[kr][kc].discard(num)
                            logic_count += 1
                            stalled = False
                            yield {
                                "type": "deduce",
                                "state": snap(board),
                                "highlights": {"cells": [[r, c] for r, c in killed], "color": "secondary"},
                                "desc": f"Pointing (Box {b_idx + 1} -> Col {cc + 1}): eliminated {num} from {len(killed)} cell(s)",
                                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                            }
                            break
            if not stalled:
                break
        if not stalled:
            continue

        # Box-Line Claiming
        for line_kind, line_units in (("Row", row_units), ("Col", col_units)):
            for l_idx, line in enumerate(line_units):
                line_set = set(line)
                for num in range(1, dim + 1):
                    places = [(r, c) for r, c in line if board[r][c] == 0 and num in candidates[r][c]]
                    if len(places) >= 2:
                        boxes_hit = {(r // box_h, c // box_w) for r, c in places}
                        if len(boxes_hit) == 1:
                            br_i, bc_i = next(iter(boxes_hit))
                            box = box_units[br_i * (dim // box_w) + bc_i]
                            killed = [(r, c) for r, c in box if (r, c) not in line_set and num in candidates[r][c]]
                            if killed:
                                for kr, kc in killed:
                                    candidates[kr][kc].discard(num)
                                logic_count += 1
                                stalled = False
                                yield {
                                    "type": "deduce",
                                    "state": snap(board),
                                    "highlights": {"cells": [[r, c] for r, c in killed], "color": "secondary"},
                                    "desc": f"Claiming ({line_kind} {l_idx + 1}): eliminated {num} from {len(killed)} box cell(s)",
                                    "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                                }
                                break
                if not stalled:
                    break
            if not stalled:
                break
        if not stalled:
            continue

        # 4. Naked Subsets (Pairs, Triples, Quads)
        subset_names = {2: "Pair", 3: "Triple", 4: "Quad"}
        for unit in units:
            open_cells = [(r, c) for r, c in unit if board[r][c] == 0]
            for k in (2, 3, 4):
                eligible = [(r, c) for r, c in open_cells if 2 <= len(candidates[r][c]) <= k]
                if len(eligible) < k:
                    continue
                for combo in combinations(eligible, k):
                    union = set().union(*(candidates[r][c] for r, c in combo))
                    if len(union) == k:
                        combo_set = set(combo)
                        killed = [(r, c) for r, c in open_cells if (r, c) not in combo_set and (candidates[r][c] & union)]
                        if killed:
                            for kr, kc in killed:
                                candidates[kr][kc] -= union
                            logic_count += 1
                            stalled = False
                            yield {
                                "type": "deduce",
                                "state": snap(board),
                                "highlights": {"cells": [[r, c] for r, c in combo], "color": "secondary"},
                                "desc": f"Naked {subset_names[k]} {{{','.join(str(d) for d in sorted(union))}}}: eliminated from {len(killed)} peer(s)",
                                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                            }
                            break
                if not stalled:
                    break
            if not stalled:
                break
        if not stalled:
            continue

        # 5. Hidden Subsets (Pairs, Triples)
        for unit in units:
            open_cells = [(r, c) for r, c in unit if board[r][c] == 0]
            digit_pos = {
                d: [(r, c) for r, c in open_cells if d in candidates[r][c]]
                for d in range(1, dim + 1)
            }
            for k in (2, 3):
                elig_digits = [d for d, ps in digit_pos.items() if 2 <= len(ps) <= k]
                if len(elig_digits) < k:
                    continue
                for d_combo in combinations(elig_digits, k):
                    cells_union = set().union(*(digit_pos[d] for d in d_combo))
                    if len(cells_union) == k:
                        d_set = set(d_combo)
                        stripped = [(r, c) for r, c in cells_union if candidates[r][c] - d_set]
                        if stripped:
                            for sr, sc in stripped:
                                candidates[sr][sc] &= d_set
                            logic_count += 1
                            stalled = False
                            yield {
                                "type": "deduce",
                                "state": snap(board),
                                "highlights": {"cells": [[r, c] for r, c in stripped], "color": "secondary"},
                                "desc": f"Hidden {subset_names[k]} {{{','.join(str(d) for d in d_combo)}}}: restricted {len(stripped)} cell(s)",
                                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                            }
                            break
                if not stalled:
                    break
            if not stalled:
                break
        if not stalled:
            continue

        # 6. X-Wing & Swordfish (rows -> cols and cols -> rows)
        fish_names = {2: "X-Wing", 3: "Swordfish"}
        for num in range(1, dim + 1):
            for k in (2, 3):
                # Row-based fish
                row_cols = {
                    r: {c for c in range(dim) if board[r][c] == 0 and num in candidates[r][c]}
                    for r in range(dim)
                }
                elig_r = [r for r, cs in row_cols.items() if 2 <= len(cs) <= k]
                for r_combo in combinations(elig_r, k):
                    cols_u = set().union(*(row_cols[r] for r in r_combo))
                    if len(cols_u) == k:
                        r_set = set(r_combo)
                        killed = [(r, c) for r in range(dim) if r not in r_set for c in cols_u if board[r][c] == 0 and num in candidates[r][c]]
                        if killed:
                            for kr, kc in killed:
                                candidates[kr][kc].discard(num)
                            logic_count += 1
                            stalled = False
                            yield {
                                "type": "deduce",
                                "state": snap(board),
                                "highlights": {"cells": [[r, c] for r, c in killed], "color": "secondary"},
                                "desc": f"{fish_names[k]} ({num}) on Rows {','.join(str(r+1) for r in r_combo)}: eliminated {len(killed)} cell(s)",
                                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                            }
                            break
                if not stalled:
                    break
                # Col-based fish
                col_rows = {
                    c: {r for r in range(dim) if board[r][c] == 0 and num in candidates[r][c]}
                    for c in range(dim)
                }
                elig_c = [c for c, rs in col_rows.items() if 2 <= len(rs) <= k]
                for c_combo in combinations(elig_c, k):
                    rows_u = set().union(*(col_rows[c] for c in c_combo))
                    if len(rows_u) == k:
                        c_set = set(c_combo)
                        killed = [(r, c) for c in range(dim) if c not in c_set for r in rows_u if board[r][c] == 0 and num in candidates[r][c]]
                        if killed:
                            for kr, kc in killed:
                                candidates[kr][kc].discard(num)
                            logic_count += 1
                            stalled = False
                            yield {
                                "type": "deduce",
                                "state": snap(board),
                                "highlights": {"cells": [[r, c] for r, c in killed], "color": "secondary"},
                                "desc": f"{fish_names[k]} ({num}) on Cols {','.join(str(c+1) for c in c_combo)}: eliminated {len(killed)} cell(s)",
                                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                            }
                            break
                if not stalled:
                    break
            if not stalled:
                break
        if not stalled:
            continue

        # 7. XY-Wing
        bivalue = [(r, c) for r in range(dim) for c in range(dim) if board[r][c] == 0 and len(candidates[r][c]) == 2]
        for pr, pc in bivalue:
            x_val, y_val = sorted(candidates[pr][pc])
            p_peers = peers_map[(pr, pc)]
            pincers_x = [(r, c) for r, c in bivalue if (r, c) in p_peers and x_val in candidates[r][c] and y_val not in candidates[r][c]]
            pincers_y = [(r, c) for r, c in bivalue if (r, c) in p_peers and y_val in candidates[r][c] and x_val not in candidates[r][c]]
            for r1, c1 in pincers_x:
                z_cand = next(iter(candidates[r1][c1] - {x_val}))
                for r2, c2 in pincers_y:
                    if candidates[r2][c2] == {y_val, z_cand}:
                        common_peers = peers_map[(r1, c1)] & peers_map[(r2, c2)]
                        killed = [(r, c) for r, c in common_peers if (r, c) != (pr, pc) and board[r][c] == 0 and z_cand in candidates[r][c]]
                        if killed:
                            for kr, kc in killed:
                                candidates[kr][kc].discard(z_cand)
                            logic_count += 1
                            stalled = False
                            yield {
                                "type": "deduce",
                                "state": snap(board),
                                "highlights": {"cells": [[pr, pc], [r1, c1], [r2, c2]], "color": "secondary"},
                                "desc": f"XY-Wing pivot ({pr+1},{pc+1}) {{{x_val},{y_val}}} -> eliminated {z_cand} from {len(killed)} cell(s)",
                                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                            }
                            break
                if not stalled:
                    break
            if not stalled:
                break

    # Phase 2: MRV Backtracking
    steps_to_confirm: List[Tuple[List[List[int]], int, int, int, int]] = []

    def is_safe(num: int, r: int, c: int) -> bool:
        return all(board[pr][pc] != num for pr, pc in peers_map[(r, c)])

    def find_mrv() -> Optional[Tuple[int, int, int]]:
        best = None
        best_count = dim + 1
        for r in range(dim):
            for c in range(dim):
                if board[r][c] == 0:
                    opts = sum(1 for n in range(1, dim + 1) if is_safe(n, r, c))
                    if opts < best_count:
                        best_count = opts
                        best = (r, c, opts)
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
        r, c, opts = cell
        if opts == 0:
            return False
        for num in range(1, dim + 1):
            if is_safe(num, r, c):
                backtrack_count += 1
                board[r][c] = num
                if backtrack():
                    steps_to_confirm.append((_clone_board(board), r, c, num, opts))
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
                    "desc": "Mid-solve contradiction: search exhausted all MRV branches with no valid solution.",
                    "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
                }
            return
        for idx, (b_snap, r, c, num, opts) in enumerate(reversed(steps_to_confirm)):
            prefix = "Deduction stalled -> " if idx == 0 else ""
            yield {
                "type": "explore",
                "state": snap(b_snap),
                "highlights": {"cells": [[r, c]], "color": "secondary"},
                "desc": f"{prefix}MRV branch ({r + 1},{c + 1}) = {num} ({opts} candidates)",
                "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
            }

    yield {
        "type": "solution",
        "state": snap(board),
        "highlights": {},
        "desc": f"Solved {dim}x{dim} Sudoku ({logic_count} deductions, {backtrack_count} guesses)",
        "stats": {"logic_deductions": logic_count, "backtracks": backtrack_count},
    }
