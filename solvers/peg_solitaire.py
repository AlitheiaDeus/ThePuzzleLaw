"""Peg Solitaire (Peg Jump) solver supporting arbitrary/irregular grid shapes."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "peg_solitaire",
    "name": "Peg Solitaire",
    "category": "Path",
    "renderer": "grid",
    "description": (
        "Bitmask DFS solver with dead-end memoization for Peg Solitaire (Peg Jump) "
        "on arbitrary or irregular grid shapes (0 = Void, 1 = Empty Hole, 2 = Peg)."
    ),
    "grid_meta": {
        "mode": "palette",
        "min_val": 0,
        "max_val": 2,
        "empty_val": 0,
        "labels": {"0": "", "1": "○", "2": "●"},
        "colors": {"0": "#16181c", "1": "#25292E", "2": "#E9C46A"},
        "editable": True,
        "resizable": True,
        "min_dim": 2,
        "max_dim": 10,
    },
    "presets": {
        "3x4 + Tail (6x4)": {
            "board": [
                [1, 1, 2, 1],
                [1, 1, 2, 1],
                [2, 1, 1, 2],
                [0, 0, 2, 0],
                [0, 0, 1, 0],
                [0, 0, 2, 0],
            ],
        },
        "4x4 (Top-Edge Empty)": {
            "board": [
                [2, 1, 2, 2],
                [2, 2, 2, 2],
                [2, 2, 2, 2],
                [2, 2, 2, 2],
            ],
        },
        "4x5 (Corner Empty)": {
            "board": [
                [1, 2, 2, 2, 2],
                [2, 2, 2, 2, 2],
                [2, 2, 2, 2, 2],
                [2, 2, 2, 2, 2],
            ],
        },
        "English Cross (7x7)": {
            "board": [
                [0, 0, 2, 2, 2, 0, 0],
                [0, 0, 2, 2, 2, 0, 0],
                [2, 2, 2, 2, 2, 2, 2],
                [2, 2, 2, 1, 2, 2, 2],
                [2, 2, 2, 2, 2, 2, 2],
                [0, 0, 2, 2, 2, 0, 0],
                [0, 0, 2, 2, 2, 0, 0],
            ],
        },
    },
    "params": [
        {
            "key": "goal_mode",
            "label": "Goal",
            "type": "select",
            "options": ["Any Hole", "Start Empty Hole(s)"],
            "default": "Any Hole",
        },
        {
            "key": "movement",
            "label": "Movement",
            "type": "select",
            "options": ["Orthogonal (4-Way)", "Orthogonal + Diagonal (8-Way)"],
            "default": "Orthogonal (4-Way)",
        },
    ],
}

ORTHO_DIRS = [(-1, 0), (1, 0), (0, -1), (0, 1)]
DIAG_DIRS = [(-1, -1), (-1, 1), (1, -1), (1, 1)]

# Jump tuple: (src_bit, over_bit, dst_bit, xor_mask, src_rc, over_rc, dst_rc)
Jump = Tuple[int, int, int, int, Tuple[int, int], Tuple[int, int], Tuple[int, int]]


def _build_jumps(
    grid: List[List[int]],
    allow_diagonal: bool,
) -> Tuple[List[Tuple[int, int]], Dict[Tuple[int, int], int], List[Jump]]:
    rows, cols = len(grid), len(grid[0])
    holes: List[Tuple[int, int]] = []
    coord_to_idx: Dict[Tuple[int, int], int] = {}
    for r in range(rows):
        for c in range(cols):
            if grid[r][c] in (1, 2):
                coord_to_idx[(r, c)] = len(holes)
                holes.append((r, c))

    if not holes:
        return holes, coord_to_idx, []

    cr = sum(r for r, _ in holes) / len(holes)
    cc = sum(c for _, c in holes) / len(holes)
    dirs = ORTHO_DIRS + DIAG_DIRS if allow_diagonal else ORTHO_DIRS

    raw_jumps: List[Tuple[float, Jump]] = []
    for r, c in holes:
        src_bit = 1 << coord_to_idx[(r, c)]
        for dr, dc in dirs:
            mr, mc = r + dr, c + dc
            tr, tc = r + 2 * dr, c + 2 * dc
            if (mr, mc) in coord_to_idx and (tr, tc) in coord_to_idx:
                over_bit = 1 << coord_to_idx[(mr, mc)]
                dst_bit = 1 << coord_to_idx[(tr, tc)]
                xor_mask = src_bit | over_bit | dst_bit
                # Prefer jumps that move pegs inward toward the board centroid.
                src_dist = (r - cr) ** 2 + (c - cc) ** 2
                dst_dist = (tr - cr) ** 2 + (tc - cc) ** 2
                score = dst_dist - src_dist
                raw_jumps.append(
                    (score, (src_bit, over_bit, dst_bit, xor_mask, (r, c), (mr, mc), (tr, tc)))
                )

    raw_jumps.sort(key=lambda item: item[0])
    return holes, coord_to_idx, [j for _, j in raw_jumps]


def _search_solution(
    start_mask: int,
    start_pegs: int,
    goal_mask: Optional[int],
    jumps: List[Jump],
    should_abort: Callable[[], bool],
) -> Tuple[Optional[List[Jump]], int, bool]:
    """Iterative bitmask DFS with dead-end memoization.

    Returns (solution_jumps, nodes_visited, aborted).
    """
    if start_pegs == 1:
        if goal_mask is None or (start_mask & goal_mask):
            return [], 1, False
        return None, 1, False

    visited: set[int] = set()
    # Stack frames: (mask, pegs_left, next_jump_idx, chosen_jump_or_None)
    stack: List[List[Any]] = [[start_mask, start_pegs, 0, None]]
    nodes = 0
    num_jumps = len(jumps)

    while stack:
        frame = stack[-1]
        mask: int = frame[0]
        pegs: int = frame[1]
        idx: int = frame[2]

        if pegs == 1:
            if goal_mask is None or (mask & goal_mask):
                path = [f[3] for f in stack[1:] if f[3] is not None]
                return path, nodes, False
            visited.add(mask)
            stack.pop()
            continue

        found_next = False
        while idx < num_jumps:
            src_bit, over_bit, dst_bit, xor_mask, _, _, _ = jumps[idx]
            idx += 1
            if (mask & src_bit) and (mask & over_bit) and not (mask & dst_bit):
                nxt = mask ^ xor_mask
                if nxt not in visited:
                    frame[2] = idx
                    nodes += 1
                    if (nodes & 1023) == 0 and should_abort():
                        return None, nodes, True
                    stack.append([nxt, pegs - 1, 0, jumps[idx - 1]])
                    found_next = True
                    break

        if not found_next:
            visited.add(mask)
            stack.pop()

    return None, nodes, False


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    grid = [list(row) for row in state["board"]]
    rows = len(grid)
    cols = len(grid[0]) if rows else 0

    goal_mode = params.get("goal_mode", "Any Hole")
    movement = params.get("movement", "Orthogonal (4-Way)")
    allow_diagonal = movement == "Orthogonal + Diagonal (8-Way)"

    holes, coord_to_idx, jumps = _build_jumps(grid, allow_diagonal)

    start_mask = 0
    empty_mask = 0
    start_pegs = 0
    for r, c in holes:
        bit = 1 << coord_to_idx[(r, c)]
        if grid[r][c] == 2:
            start_mask |= bit
            start_pegs += 1
        else:
            empty_mask |= bit

    yield {
        "type": "start",
        "state": {"board": [list(row) for row in grid]},
        "highlights": {},
        "desc": (
            f"Loaded {rows}x{cols} Peg Solitaire board "
            f"({len(holes)} holes, {start_pegs} pegs, {goal_mode})"
        ),
        "stats": {"holes": len(holes), "pegs_left": start_pegs, "moves": 0, "nodes": 0},
    }

    if should_abort():
        return

    if start_pegs == 0:
        yield {
            "type": "failed",
            "state": {"board": [list(row) for row in grid]},
            "highlights": {},
            "desc": "No pegs on the board (place at least 1 peg).",
            "stats": {"holes": len(holes), "pegs_left": 0, "moves": 0, "nodes": 0},
        }
        return

    if start_pegs == 1:
        if goal_mode == "Start Empty Hole(s)" and not (start_mask & empty_mask):
            yield {
                "type": "failed",
                "state": {"board": [list(row) for row in grid]},
                "highlights": {},
                "desc": "Only 1 peg present, but it is not in a starting empty hole.",
                "stats": {"holes": len(holes), "pegs_left": 1, "moves": 0, "nodes": 0},
            }
            return
        yield {
            "type": "solution",
            "state": {"board": [list(row) for row in grid]},
            "highlights": {},
            "desc": "Board already solved with 1 peg remaining.",
            "stats": {"holes": len(holes), "pegs_left": 1, "moves": 0, "nodes": 0},
        }
        return

    if not jumps:
        yield {
            "type": "failed",
            "state": {"board": [list(row) for row in grid]},
            "highlights": {},
            "desc": "No valid jump geometry exists on this hole layout.",
            "stats": {"holes": len(holes), "pegs_left": start_pegs, "moves": 0, "nodes": 0},
        }
        return

    goal_mask = empty_mask if goal_mode == "Start Empty Hole(s)" else None
    if goal_mask == 0:
        yield {
            "type": "failed",
            "state": {"board": [list(row) for row in grid]},
            "highlights": {},
            "desc": "Start Empty Hole(s) goal requires at least one empty hole (○).",
            "stats": {"holes": len(holes), "pegs_left": start_pegs, "moves": 0, "nodes": 0},
        }
        return

    solution_jumps, nodes, aborted = _search_solution(
        start_mask, start_pegs, goal_mask, jumps, should_abort
    )
    if aborted:
        return

    if solution_jumps is None:
        yield {
            "type": "failed",
            "state": {"board": [list(row) for row in grid]},
            "highlights": {},
            "desc": f"Unsolvable board under '{goal_mode}' ({nodes} states explored).",
            "stats": {"holes": len(holes), "pegs_left": start_pegs, "moves": 0, "nodes": nodes},
        }
        return

    total_moves = len(solution_jumps)
    for move_idx, (_, _, _, _, src, over, dst) in enumerate(solution_jumps, start=1):
        if should_abort():
            return
        sr, sc = src
        mr, mc = over
        tr, tc = dst
        grid[sr][sc] = 1
        grid[mr][mc] = 1
        grid[tr][tc] = 2
        pegs_left = start_pegs - move_idx
        is_last = move_idx == total_moves

        yield {
            "type": "solution" if is_last else "deduce",
            "state": {"board": [list(row) for row in grid]},
            "highlights": {
                "cells": [[sr, sc], [mr, mc], [tr, tc]],
                "path": [[sr, sc], [tr, tc]],
                "color": "hot",
            },
            "desc": (
                f"Move {move_idx}/{total_moves}: ({sr},{sc}) → ({tr},{tc}), "
                f"ate ({mr},{mc}) | {pegs_left} peg{'s' if pegs_left != 1 else ''} left"
            ),
            "stats": {
                "holes": len(holes),
                "pegs_left": pegs_left,
                "moves": move_idx,
                "nodes": nodes,
            },
        }
