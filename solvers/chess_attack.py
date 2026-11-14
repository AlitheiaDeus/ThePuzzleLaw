"""Zoned Chess Attack solver (Queens and Superkings = Rook + King).
Ported from Snippets To Integrate/chess_attack_solver.py & superking_solver.py.
"""

from __future__ import annotations

from itertools import combinations
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

META: Dict[str, Any] = {
    "slug": "chess_attack",
    "name": "Chess Attack (Queens & Superking)",
    "category": "Tactical / Board",
    "renderer": "grid",
    "description": "Places 1 non-attacking Queen or Superking (Rook+King) per row, column, and color zone.",
    "grid_meta": {
        "mode": "binary",
        "min_val": 0,
        "max_val": 1,
        "labels": {"0": "", "1": "♔"},
        "editable": True,
    },
    "presets": {
        "5x5 Zoned Superking": {
            "piece_type": "Superking",
            "zones": [
                [0, 0, 1, 1, 1],
                [0, 2, 2, 1, 3],
                [0, 2, 4, 3, 3],
                [2, 2, 4, 4, 3],
                [4, 4, 4, 3, 3],
            ],
            "board": [[0] * 5 for _ in range(5)],
        },
        "6x6 Zoned Queen": {
            "piece_type": "Queen",
            "zones": [
                [0, 0, 1, 1, 2, 2],
                [0, 0, 1, 2, 2, 3],
                [0, 1, 1, 3, 3, 3],
                [4, 4, 5, 5, 3, 3],
                [4, 4, 5, 5, 5, 3],
                [4, 4, 4, 5, 5, 5],
            ],
            "board": [[0] * 6 for _ in range(6)],
        },
        "6x6 Zoned Superking": {
            "piece_type": "Superking",
            "zones": [
                [0, 0, 0, 1, 1, 2],
                [0, 3, 0, 1, 2, 2],
                [3, 3, 1, 1, 2, 4],
                [3, 5, 5, 4, 4, 4],
                [3, 5, 5, 5, 4, 4],
                [5, 5, 5, 4, 4, 4],
            ],
            "board": [[0] * 6 for _ in range(6)],
        },
    },
    "params": [
        {
            "key": "piece_type",
            "label": "Piece Type",
            "type": "select",
            "default": "Superking",
            "options": ["Superking", "Queen"],
        }
    ],
}


def _attacked_cells(r: int, c: int, n: int, piece_type: str) -> Set[Tuple[int, int]]:
    cells: Set[Tuple[int, int]] = set()
    for i in range(n):
        cells.add((r, i))
        cells.add((i, c))
    if piece_type == "Queen":
        for d in range(1, n):
            for dr, dc in [(-d, -d), (-d, d), (d, -d), (d, d)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n:
                    cells.add((nr, nc))
    else:  # Superking = Rook + King
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n:
                    cells.add((nr, nc))
    return cells


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    zones: List[List[int]] = state.get("zones") or []
    board: List[List[int]] = [list(r) for r in state["board"]]
    n = len(board)
    if not zones:
        zones = [[r for _ in range(n)] for r in range(n)]
    piece_type = str(params.get("piece_type") or state.get("piece_type") or "Superking")

    zone_cells: Dict[int, List[Tuple[int, int]]] = {}
    for r in range(n):
        for c in range(n):
            zone_cells.setdefault(zones[r][c], []).append((r, c))
    zone_ids = sorted(zone_cells.keys())

    def snap(b: List[List[int]]) -> Dict[str, Any]:
        return {"piece_type": piece_type, "zones": zones, "board": [list(row) for row in b]}

    yield {
        "type": "start",
        "state": snap(board),
        "highlights": {},
        "desc": f"Loaded {n}x{n} {piece_type} board ({len(zone_ids)} zones)",
        "stats": {"n": n, "piece": piece_type},
    }

    eliminated: Set[Tuple[int, int]] = set()
    deduction_steps: List[Tuple[List[List[int]], int, int, str]] = []

    def is_safe(r: int, c: int, b: List[List[int]], elim: Set[Tuple[int, int]]) -> bool:
        if (r, c) in elim or b[r][c] == 1:
            return False
        for pr in range(n):
            for pc in range(n):
                if b[pr][pc] == 1:
                    if (r, c) in _attacked_cells(pr, pc, n, piece_type):
                        return False
                    if zones[pr][pc] == zones[r][c]:
                        return False
        return True

    # Deduction Phase (Single Candidate, Locked Set, Walk-Around)
    changed = True
    while changed and not should_abort():
        changed = False
        # 1. Single candidate in row/col
        for r in range(n):
            cands = [
                (r, c)
                for c in range(n)
                if not any(board[zr][zc] for zr, zc in zone_cells[zones[r][c]])
                and is_safe(r, c, board, eliminated)
            ]
            if len(cands) == 1:
                pr, pc = cands[0]
                board[pr][pc] = 1
                deduction_steps.append(([list(x) for x in board], pr, pc, "Single Row Candidate"))
                changed = True
                break
        if changed:
            continue

        for c in range(n):
            cands = [
                (r, c)
                for r in range(n)
                if not any(board[zr][zc] for zr, zc in zone_cells[zones[r][c]])
                and is_safe(r, c, board, eliminated)
            ]
            if len(cands) == 1:
                pr, pc = cands[0]
                board[pr][pc] = 1
                deduction_steps.append(([list(x) for x in board], pr, pc, "Single Col Candidate"))
                changed = True
                break
        if changed:
            continue

        # 2. Locked sets (k zones confined to k rows/cols)
        unsolved_zones = [zid for zid in zone_ids if not any(board[r][c] for r, c in zone_cells[zid])]
        for k in range(2, len(unsolved_zones) // 2 + 1):
            for z_combo in combinations(unsolved_zones, k):
                all_cands = [
                    (r, c)
                    for zid in z_combo
                    for r, c in zone_cells[zid]
                    if is_safe(r, c, board, eliminated)
                ]
                if not all_cands:
                    continue
                u_rows = {r for r, _ in all_cands}
                if len(u_rows) == k:
                    elim_any = False
                    for r in u_rows:
                        for c in range(n):
                            if zones[r][c] not in z_combo and is_safe(r, c, board, eliminated):
                                eliminated.add((r, c))
                                elim_any = True
                    if elim_any:
                        changed = True
                        break
                u_cols = {c for _, c in all_cands}
                if len(u_cols) == k:
                    elim_any = False
                    for c in u_cols:
                        for r in range(n):
                            if zones[r][c] not in z_combo and is_safe(r, c, board, eliminated):
                                eliminated.add((r, c))
                                elim_any = True
                    if elim_any:
                        changed = True
                        break
            if changed:
                break

    for snap_b, pr, pc, reason in deduction_steps:
        if should_abort():
            return
        yield {
            "type": "deduce",
            "state": snap(snap_b),
            "highlights": {"cells": [[pr, pc]], "color": "primary"},
            "desc": f"{reason}: place {piece_type} at ({pr + 1}, {pc + 1})",
            "stats": {"placed": sum(sum(r) for r in snap_b)},
        }

    # Backtracking phase (MRV over remaining zones)
    branch_steps: List[Tuple[List[List[int]], int, int]] = []

    def backtrack() -> bool:
        if should_abort():
            return False
        placed = sum(sum(r) for r in board)
        if placed >= len(zone_ids):
            return True

        best_opts: Optional[List[Tuple[int, int]]] = None
        for zid in zone_ids:
            if any(board[r][c] for r, c in zone_cells[zid]):
                continue
            opts = [(r, c) for r, c in zone_cells[zid] if is_safe(r, c, board, eliminated)]
            if not opts:
                return False
            if best_opts is None or len(opts) < len(best_opts):
                best_opts = opts
        if not best_opts:
            return False

        for r, c in best_opts:
            board[r][c] = 1
            if backtrack():
                branch_steps.append(([list(x) for x in board], r, c))
                return True
            board[r][c] = 0
        return False

    if sum(sum(r) for r in board) < len(zone_ids):
        if not backtrack():
            if not should_abort():
                yield {
                    "type": "failed",
                    "state": snap(board),
                    "highlights": {},
                    "desc": f"No valid {piece_type} placement exists for these zones.",
                    "stats": {},
                }
            return
        for snap_b, pr, pc in reversed(branch_steps):
            yield {
                "type": "explore",
                "state": snap(snap_b),
                "highlights": {"cells": [[pr, pc]], "color": "secondary"},
                "desc": f"Place {piece_type} at ({pr + 1}, {pc + 1})",
                "stats": {"placed": sum(sum(r) for r in snap_b)},
            }

    pieces = [[r, c] for r in range(n) for c in range(n) if board[r][c] == 1]
    yield {
        "type": "solution",
        "state": snap(board),
        "highlights": {"cells": pieces, "color": "primary"},
        "desc": f"Solved {n}x{n} {piece_type}! Placed {len(pieces)} non-attacking pieces.",
        "stats": {"placed": len(pieces)},
    }
