"""Zoned Chess Attack solver: Queens & Rook+King (Star Battle) with deterministic pruning + MRV search."""

from __future__ import annotations

import heapq
from itertools import combinations
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

META: Dict[str, Any] = {
    "slug": "chess_attack",
    "name": "Chess Attack",
    "category": "State",
    "renderer": "grid",
    "description": "Places 1 (or 2) non-attacking Queen or Rook+King (Star Battle) pieces per row, column, and color zone.",
    "grid_meta": {
        "mode": "binary",
        "min_val": 0,
        "max_val": 1,
        "labels": {"0": "", "1": "★"},
        "editable": True,
        "resizable": "square",
        "min_dim": 4,
        "max_dim": 9,
        "zone_editable": True,
    },
    "presets": {
        "5x5 Rook+King": {
            "piece_type": "Rook + King",
            "stars_per_unit": "1",
            "zones": [
                [0, 0, 1, 1, 1],
                [0, 2, 2, 1, 3],
                [0, 2, 4, 3, 3],
                [2, 2, 4, 4, 3],
                [4, 4, 4, 3, 3],
            ],
            "board": [[0] * 5 for _ in range(5)],
        },
        "6x6 Queen": {
            "piece_type": "Queen",
            "stars_per_unit": "1",
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
        "6x6 Rook+King": {
            "piece_type": "Rook + King",
            "stars_per_unit": "1",
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
        "8x8 2-Star Battle": {
            "piece_type": "Rook + King",
            "stars_per_unit": "2",
            "zones": [
                [0, 0, 0, 1, 1, 2, 2, 2],
                [0, 0, 1, 1, 2, 2, 2, 2],
                [0, 0, 1, 1, 1, 3, 2, 3],
                [0, 4, 5, 1, 3, 3, 3, 3],
                [4, 4, 5, 5, 3, 6, 6, 3],
                [4, 5, 5, 6, 6, 6, 6, 3],
                [4, 4, 5, 5, 7, 6, 7, 7],
                [4, 4, 5, 5, 7, 7, 7, 7],
            ],
            "board": [[0] * 8 for _ in range(8)],
        },
    },
    "params": [
        {
            "key": "piece_type",
            "label": "Piece Type",
            "type": "select",
            "default": "Rook + King",
            "options": ["Rook + King", "Queen"],
        },
        {
            "key": "stars_per_unit",
            "label": "Stars / Unit",
            "type": "select",
            "default": "1",
            "options": ["1", "2"],
        },
    ],
}


def _normalize_piece_type(raw: Any) -> str:
    val = str(raw or "Rook + King").strip()
    if val in ("Superking", "Rook + King", "Rook+King"):
        return "Rook + King"
    return "Queen" if val == "Queen" else "Rook + King"


def _normalize_zones(raw_zones: Any, n: int) -> List[List[int]]:
    if (
        isinstance(raw_zones, list)
        and len(raw_zones) == n
        and all(isinstance(row, list) and len(row) == n for row in raw_zones)
    ):
        return [[int(v) for v in row] for row in raw_zones]
    # Fallback row-stripe zones when board was resized cleanly without zones
    return [[r for _ in range(n)] for r in range(n)]


def _attacked_cells(r: int, c: int, n: int, piece_type: str, stars: int) -> Set[Tuple[int, int]]:
    """Return cells forbidden when placing a piece at (r, c)."""
    cells: Set[Tuple[int, int]] = set()
    if stars == 1:
        for i in range(n):
            cells.add((r, i))
            cells.add((i, c))
    if piece_type == "Queen":
        for d in range(1, n):
            for dr, dc in [(-d, -d), (-d, d), (d, -d), (d, d)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n:
                    cells.add((nr, nc))
    else:  # Rook + King: no 8-neighbor touching (and line quota handles >1 star limits)
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
    board: List[List[int]] = [list(r) for r in state["board"]]
    n = len(board)
    zones = _normalize_zones(state.get("zones"), n)
    piece_type = _normalize_piece_type(params.get("piece_type") or state.get("piece_type"))
    stars = max(1, min(2, int(params.get("stars_per_unit") or state.get("stars_per_unit") or 1)))

    zone_cells: Dict[int, List[Tuple[int, int]]] = {}
    for r in range(n):
        for c in range(n):
            zone_cells.setdefault(zones[r][c], []).append((r, c))
    zone_ids = sorted(zone_cells.keys())
    target_total = n * stars

    def snap(b: List[List[int]]) -> Dict[str, Any]:
        return {
            "piece_type": piece_type,
            "stars_per_unit": str(stars),
            "zones": zones,
            "board": [list(row) for row in b],
        }

    yield {
        "type": "start",
        "state": snap(board),
        "highlights": {},
        "desc": f"Loaded {n}x{n} {piece_type} ({stars}-Star Battle, {len(zone_ids)} zones)",
        "stats": {"n": n, "piece": piece_type, "stars": stars, "placed": 0},
    }

    if n < 4 or len(zone_ids) != n:
        yield {
            "type": "failed",
            "state": snap(board),
            "highlights": {},
            "desc": (
                f"Pre-solve check failed: {piece_type} requires N >= 4 and exactly N={n} zones "
                f"(found {len(zone_ids)})."
            ),
            "stats": {},
        }
        return

    if stars == 2 and piece_type == "Rook + King" and n < 8:
        yield {
            "type": "failed",
            "state": snap(board),
            "highlights": {},
            "desc": f"Pre-solve parity check failed: 2-Star Rook + King requires N >= 8 (got {n}x{n}).",
            "stats": {},
        }
        return

    for zid in zone_ids:
        if len(zone_cells[zid]) < stars:
            yield {
                "type": "failed",
                "state": snap(board),
                "highlights": {"cells": [list(p) for p in zone_cells[zid]], "color": "hot"},
                "desc": f"Pre-solve check failed: Zone {zid + 1} has only {len(zone_cells[zid])} cells for {stars} star(s).",
                "stats": {},
            }
            return

    def count_unit_stars(b: List[List[int]]):
        row_cnt = [sum(b[r]) for r in range(n)]
        col_cnt = [sum(b[r][c] for r in range(n)) for c in range(n)]
        zone_cnt = {zid: sum(b[r][c] for r, c in zone_cells[zid]) for zid in zone_ids}
        return row_cnt, col_cnt, zone_cnt

    def can_place(r: int, c: int, b: List[List[int]], elim: Set[Tuple[int, int]], row_cnt, col_cnt, zone_cnt) -> bool:
        if (r, c) in elim or b[r][c] == 1:
            return False
        if row_cnt[r] >= stars or col_cnt[c] >= stars or zone_cnt[zones[r][c]] >= stars:
            return False
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                nr, nc = r + dr, c + dc
                if 0 <= nr < n and 0 <= nc < n and b[nr][nc] == 1:
                    return False
        if piece_type == "Queen":
            for d in range(1, n):
                for dr, dc in [(-d, -d), (-d, d), (d, -d), (d, d)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < n and 0 <= nc < n and b[nr][nc] == 1:
                        return False
        return True

    def place_star(r: int, c: int, b: List[List[int]], elim: Set[Tuple[int, int]]) -> None:
        b[r][c] = 1
        elim.update(_attacked_cells(r, c, n, piece_type, stars))
        row_cnt, col_cnt, zone_cnt = count_unit_stars(b)
        if row_cnt[r] >= stars:
            for cc in range(n):
                if b[r][cc] == 0:
                    elim.add((r, cc))
        if col_cnt[c] >= stars:
            for rr in range(n):
                if b[rr][c] == 0:
                    elim.add((rr, c))
        zid = zones[r][c]
        if zone_cnt[zid] >= stars:
            for zr, zc in zone_cells[zid]:
                if b[zr][zc] == 0:
                    elim.add((zr, zc))

    def build_units(row_cnt, col_cnt, zone_cnt):
        units: List[Tuple[str, str, int, List[Tuple[int, int]]]] = []
        for zid in zone_ids:
            need = stars - zone_cnt[zid]
            if need > 0:
                units.append(("zone", f"Zone {zid + 1}", need, zone_cells[zid]))
        for r in range(n):
            need = stars - row_cnt[r]
            if need > 0:
                units.append(("row", f"Row {r + 1}", need, [(r, c) for c in range(n)]))
        for c in range(n):
            need = stars - col_cnt[c]
            if need > 0:
                units.append(("col", f"Col {c + 1}", need, [(r, c) for r in range(n)]))
        return units

    def propagate(
        b: List[List[int]],
        elim: Set[Tuple[int, int]],
        collector: Optional[List[Tuple[List[List[int]], List[List[int]], str, str]]] = None,
    ) -> Tuple[bool, str]:
        changed = True
        while changed:
            changed = False
            row_cnt, col_cnt, zone_cnt = count_unit_stars(b)

            # Saturate completed units
            for r in range(n):
                if row_cnt[r] > stars:
                    return False, f"Row {r + 1} exceeds {stars} star(s)"
                if row_cnt[r] == stars:
                    for c in range(n):
                        if b[r][c] == 0 and (r, c) not in elim:
                            elim.add((r, c))
                            changed = True
            for c in range(n):
                if col_cnt[c] > stars:
                    return False, f"Col {c + 1} exceeds {stars} star(s)"
                if col_cnt[c] == stars:
                    for r in range(n):
                        if b[r][c] == 0 and (r, c) not in elim:
                            elim.add((r, c))
                            changed = True
            for zid in zone_ids:
                if zone_cnt[zid] > stars:
                    return False, f"Zone {zid + 1} exceeds {stars} star(s)"
                if zone_cnt[zid] == stars:
                    for r, c in zone_cells[zid]:
                        if b[r][c] == 0 and (r, c) not in elim:
                            elim.add((r, c))
                            changed = True

            units = build_units(row_cnt, col_cnt, zone_cnt)
            unit_cands: Dict[Tuple[str, str], Tuple[int, List[Tuple[int, int]]]] = {}
            for kind, name, need, cells in units:
                cands = [(r, c) for r, c in cells if can_place(r, c, b, elim, row_cnt, col_cnt, zone_cnt)]
                if len(cands) < need:
                    return False, f"{name} has only {len(cands)} valid cell(s) for {need} needed star(s)"
                unit_cands[(kind, name)] = (need, cands)

            # 1. Exact candidate fill (Single / Remaining Quota)
            for (kind, name), (need, cands) in unit_cands.items():
                if len(cands) == need:
                    # Ensure chosen cells don't conflict with each other
                    placed_now: List[List[int]] = []
                    for pr, pc in cands:
                        if not can_place(pr, pc, b, elim, row_cnt, col_cnt, zone_cnt):
                            return False, f"{name} forced cells conflict with each other"
                        place_star(pr, pc, b, elim)
                        row_cnt, col_cnt, zone_cnt = count_unit_stars(b)
                        placed_now.append([pr, pc])
                    if collector is not None:
                        collector.append((
                            [list(x) for x in b],
                            placed_now,
                            f"Exact Unit Fill ({name}): place {piece_type} at {', '.join(f'({r+1},{c+1})' for r, c in placed_now)}",
                            "primary",
                        ))
                    changed = True
                    break
            if changed:
                continue

            # 2. Pointing & Claiming (Zone <-> Row/Col intersections when unit quota matches)
            for zid in zone_ids:
                z_key = ("zone", f"Zone {zid + 1}")
                if z_key not in unit_cands:
                    continue
                z_need, z_cands = unit_cands[z_key]
                u_rows = {r for r, _ in z_cands}
                if len(u_rows) == 1:
                    rr = next(iter(u_rows))
                    if z_need == stars - row_cnt[rr]:
                        killed = [(rr, c) for c in range(n) if zones[rr][c] != zid and can_place(rr, c, b, elim, row_cnt, col_cnt, zone_cnt)]
                        if killed:
                            elim.update(killed)
                            if collector is not None:
                                collector.append((
                                    [list(x) for x in b],
                                    [[r, c] for r, c in killed],
                                    f"Pointing (Zone {zid + 1} -> Row {rr + 1}): eliminated {len(killed)} cell(s)",
                                    "secondary",
                                ))
                            changed = True
                            break
                u_cols = {c for _, c in z_cands}
                if len(u_cols) == 1:
                    cc = next(iter(u_cols))
                    if z_need == stars - col_cnt[cc]:
                        killed = [(r, cc) for r in range(n) if zones[r][cc] != zid and can_place(r, cc, b, elim, row_cnt, col_cnt, zone_cnt)]
                        if killed:
                            elim.update(killed)
                            if collector is not None:
                                collector.append((
                                    [list(x) for x in b],
                                    [[r, c] for r, c in killed],
                                    f"Pointing (Zone {zid + 1} -> Col {cc + 1}): eliminated {len(killed)} cell(s)",
                                    "secondary",
                                ))
                            changed = True
                            break
            if changed:
                continue

            for r in range(n):
                r_key = ("row", f"Row {r + 1}")
                if r_key not in unit_cands:
                    continue
                r_need, r_cands = unit_cands[r_key]
                u_zones = {zones[rr][cc] for rr, cc in r_cands}
                if len(u_zones) == 1:
                    zid = next(iter(u_zones))
                    if r_need == stars - zone_cnt[zid]:
                        killed = [(zr, zc) for zr, zc in zone_cells[zid] if zr != r and can_place(zr, zc, b, elim, row_cnt, col_cnt, zone_cnt)]
                        if killed:
                            elim.update(killed)
                            if collector is not None:
                                collector.append((
                                    [list(x) for x in b],
                                    [[kr, kc] for kr, kc in killed],
                                    f"Claiming (Row {r + 1} -> Zone {zid + 1}): eliminated {len(killed)} cell(s)",
                                    "secondary",
                                ))
                            changed = True
                            break
            if changed:
                continue

            for c in range(n):
                c_key = ("col", f"Col {c + 1}")
                if c_key not in unit_cands:
                    continue
                c_need, c_cands = unit_cands[c_key]
                u_zones = {zones[rr][cc] for rr, cc in c_cands}
                if len(u_zones) == 1:
                    zid = next(iter(u_zones))
                    if c_need == stars - zone_cnt[zid]:
                        killed = [(zr, zc) for zr, zc in zone_cells[zid] if zc != c and can_place(zr, zc, b, elim, row_cnt, col_cnt, zone_cnt)]
                        if killed:
                            elim.update(killed)
                            if collector is not None:
                                collector.append((
                                    [list(x) for x in b],
                                    [[kr, kc] for kr, kc in killed],
                                    f"Claiming (Col {c + 1} -> Zone {zid + 1}): eliminated {len(killed)} cell(s)",
                                    "secondary",
                                ))
                            changed = True
                            break
            if changed:
                continue

            # 3. Common-Attack Intersection (King-adjacency / Domino / L-triomino exclusion)
            # If every candidate in a unit requiring a star attacks (r, c), then (r, c) cannot host a star.
            all_open = {
                (r, c)
                for r in range(n)
                for c in range(n)
                if can_place(r, c, b, elim, row_cnt, col_cnt, zone_cnt)
            }
            for (kind, name), (need, cands) in unit_cands.items():
                if need == 1 or kind == "zone":
                    # When need == 1, star MUST be one of cands; when need >= 1 for Rook+King 2x2 saturation handles extras
                    if need == 1:
                        common: Optional[Set[Tuple[int, int]]] = None
                        for cr, cc in cands:
                            att = _attacked_cells(cr, cc, n, piece_type, stars)
                            common = att if common is None else (common & att)
                            if not common:
                                break
                        if common:
                            killed = sorted((common & all_open) - set(cands))
                            if killed:
                                elim.update(killed)
                                if collector is not None:
                                    collector.append((
                                        [list(x) for x in b],
                                        [[kr, kc] for kr, kc in killed],
                                        f"Common-Attack Exclusion ({name}): eliminated {len(killed)} cell(s)",
                                        "secondary",
                                    ))
                                changed = True
                                break
            if changed:
                continue

            # 4. 2x2 Block Saturation (at most 1 star can exist in any 2x2 subgrid)
            for br in range(n - 1):
                for bc in range(n - 1):
                    box = {(br, bc), (br, bc + 1), (br + 1, bc), (br + 1, bc + 1)}
                    for (kind, name), (need, cands) in unit_cands.items():
                        outside = [cell for cell in cands if cell not in box]
                        if len(outside) < need:
                            killed = sorted((box & all_open) - set(cands))
                            if killed:
                                elim.update(killed)
                                if collector is not None:
                                    collector.append((
                                        [list(x) for x in b],
                                        [[kr, kc] for kr, kc in killed],
                                        f"2x2 Box Saturation ({name} claims box ({br + 1},{bc + 1})): eliminated {len(killed)} cell(s)",
                                        "secondary",
                                    ))
                                changed = True
                                break
                    if changed:
                        break
                if changed:
                    break
            if changed:
                continue

            # 5. Locked Sets (k zones in k rows/cols & dual k rows/cols in k zones, for k <= 4)
            unsolved_zones = [zid for zid in zone_ids if zone_cnt[zid] < stars]
            for k in range(2, min(5, len(unsolved_zones) // 2 + 1)):
                for z_combo in combinations(unsolved_zones, k):
                    z_need_sum = sum(stars - zone_cnt[zid] for zid in z_combo)
                    all_cands = [cell for zid in z_combo for cell in unit_cands[("zone", f"Zone {zid + 1}")][1]]
                    if not all_cands:
                        continue
                    u_rows = {r for r, _ in all_cands}
                    row_need_sum = sum(stars - row_cnt[r] for r in u_rows)
                    if z_need_sum == row_need_sum and z_need_sum > 0:
                        killed = [
                            (r, c)
                            for r in u_rows
                            for c in range(n)
                            if zones[r][c] not in z_combo and can_place(r, c, b, elim, row_cnt, col_cnt, zone_cnt)
                        ]
                        if killed:
                            elim.update(killed)
                            if collector is not None:
                                znames = ",".join(str(z + 1) for z in z_combo)
                                collector.append((
                                    [list(x) for x in b],
                                    [[kr, kc] for kr, kc in killed],
                                    f"Locked Set (Zones {{{znames}}} in Rows {{{','.join(str(r+1) for r in sorted(u_rows))}}}): eliminated {len(killed)} cell(s)",
                                    "secondary",
                                ))
                            changed = True
                            break
                    u_cols = {c for _, c in all_cands}
                    col_need_sum = sum(stars - col_cnt[c] for c in u_cols)
                    if z_need_sum == col_need_sum and z_need_sum > 0:
                        killed = [
                            (r, c)
                            for c in u_cols
                            for r in range(n)
                            if zones[r][c] not in z_combo and can_place(r, c, b, elim, row_cnt, col_cnt, zone_cnt)
                        ]
                        if killed:
                            elim.update(killed)
                            if collector is not None:
                                znames = ",".join(str(z + 1) for z in z_combo)
                                collector.append((
                                    [list(x) for x in b],
                                    [[kr, kc] for kr, kc in killed],
                                    f"Locked Set (Zones {{{znames}}} in Cols {{{','.join(str(c+1) for c in sorted(u_cols))}}}): eliminated {len(killed)} cell(s)",
                                    "secondary",
                                ))
                            changed = True
                            break
                if changed:
                    break
            if changed:
                continue

            # Dual Locked Sets: k rows/cols confined to k zones
            unsolved_rows = [r for r in range(n) if row_cnt[r] < stars]
            for k in range(2, min(5, len(unsolved_rows) // 2 + 1)):
                for r_combo in combinations(unsolved_rows, k):
                    r_need_sum = sum(stars - row_cnt[r] for r in r_combo)
                    all_cands = [cell for r in r_combo for cell in unit_cands[("row", f"Row {r + 1}")][1]]
                    if not all_cands:
                        continue
                    u_zones = {zones[r][c] for r, c in all_cands}
                    z_need_sum = sum(stars - zone_cnt[z] for z in u_zones)
                    if r_need_sum == z_need_sum and r_need_sum > 0:
                        killed = [
                            (zr, zc)
                            for zid in u_zones
                            for zr, zc in zone_cells[zid]
                            if zr not in r_combo and can_place(zr, zc, b, elim, row_cnt, col_cnt, zone_cnt)
                        ]
                        if killed:
                            elim.update(killed)
                            if collector is not None:
                                collector.append((
                                    [list(x) for x in b],
                                    [[kr, kc] for kr, kc in killed],
                                    f"Locked Line Set (Rows {{{','.join(str(r+1) for r in r_combo)}}}): eliminated {len(killed)} cell(s)",
                                    "secondary",
                                ))
                            changed = True
                            break
                if changed:
                    break

        return True, ""

    # Initialize eliminations from any user-placed pieces on board
    eliminated: Set[Tuple[int, int]] = set()
    initial_stars = [(r, c) for r in range(n) for c in range(n) if board[r][c] == 1]
    if initial_stars:
        temp_board = [[0] * n for _ in range(n)]
        for sr, sc in initial_stars:
            rc, cc, zc = count_unit_stars(temp_board)
            if not can_place(sr, sc, temp_board, eliminated, rc, cc, zc):
                yield {
                    "type": "failed",
                    "state": snap(board),
                    "highlights": {"cells": [[sr, sc]], "color": "hot"},
                    "desc": f"Pre-solve contradiction: placed piece at ({sr + 1}, {sc + 1}) conflicts with another piece.",
                    "stats": {},
                }
                return
            place_star(sr, sc, temp_board, eliminated)

    deduction_steps: List[Tuple[List[List[int]], List[List[int]], str, str]] = []
    ok, err_msg = propagate(board, eliminated, collector=deduction_steps)
    for snap_b, hl_cells, reason, color in deduction_steps:
        if should_abort():
            return
        yield {
            "type": "deduce",
            "state": snap(snap_b),
            "highlights": {"cells": hl_cells, "color": color},
            "desc": reason,
            "stats": {"placed": sum(sum(r) for r in snap_b), "target": target_total},
        }

    if not ok:
        yield {
            "type": "failed",
            "state": snap(board),
            "highlights": {},
            "desc": f"Pre-solve contradiction: {err_msg}.",
            "stats": {},
        }
        return

    # Backtracking with propagation + MRV
    branch_steps: List[Tuple[List[List[int]], int, int]] = []

    def backtrack(cur_b: List[List[int]], cur_elim: Set[Tuple[int, int]]) -> Optional[List[List[int]]]:
        if should_abort():
            return None
        placed = sum(sum(r) for r in cur_b)
        if placed >= target_total:
            return cur_b

        row_cnt, col_cnt, zone_cnt = count_unit_stars(cur_b)
        best_opts: Optional[List[Tuple[int, int]]] = None
        for _, _, need, cells in build_units(row_cnt, col_cnt, zone_cnt):
            opts = [(r, c) for r, c in cells if can_place(r, c, cur_b, cur_elim, row_cnt, col_cnt, zone_cnt)]
            if len(opts) < need:
                return None
            if best_opts is None or len(opts) < len(best_opts):
                best_opts = opts
        if not best_opts:
            return None

        for pr, pc in best_opts:
            nxt_b = [list(x) for x in cur_b]
            nxt_elim = set(cur_elim)
            place_star(pr, pc, nxt_b, nxt_elim)
            ok_sub, _ = propagate(nxt_b, nxt_elim)
            if not ok_sub:
                continue
            res = backtrack(nxt_b, nxt_elim)
            if res is not None:
                branch_steps.append(([list(x) for x in nxt_b], pr, pc))
                return res
        return None

    solved_board = board
    if sum(sum(r) for r in board) < target_total:
        res = backtrack(board, eliminated)
        if res is None:
            if not should_abort():
                yield {
                    "type": "failed",
                    "state": snap(board),
                    "highlights": {},
                    "desc": f"No valid {piece_type} placement exists for these zones.",
                    "stats": {},
                }
            return
        for idx, (snap_b, pr, pc) in enumerate(reversed(branch_steps)):
            prefix = "Deduction stalled -> MRV branch: " if idx == 0 else "MRV branch: "
            yield {
                "type": "explore",
                "state": snap(snap_b),
                "highlights": {"cells": [[pr, pc]], "color": "secondary"},
                "desc": f"{prefix}Place {piece_type} at ({pr + 1}, {pc + 1})",
                "stats": {"placed": sum(sum(r) for r in snap_b), "target": target_total},
            }
        solved_board = res

    pieces = [[r, c] for r in range(n) for c in range(n) if solved_board[r][c] == 1]
    yield {
        "type": "solution",
        "state": snap(solved_board),
        "highlights": {"cells": pieces, "color": "primary"},
        "desc": f"Solved {n}x{n} {piece_type} ({stars}-Star)! Placed {len(pieces)} non-attacking pieces.",
        "stats": {"placed": len(pieces), "target": target_total},
    }
