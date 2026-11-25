"""Maze Navigator pathfinder: Manhattan default, weighted terrain, edge walls, Dijkstra/A*/BFS, Euclidean & Quarter-Arc geometry."""

from __future__ import annotations

import heapq
import math
from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

META: Dict[str, Any] = {
    "slug": "maze_navigator",
    "name": "Maze Navigator",
    "category": "Path",
    "renderer": "custom",
    "custom_view": "/renderers/custom/hex_maze.js",
    "description": (
        "Shortest-path solver (A*, Dijkstra, BFS) supporting tile walls, lattice edge walls, "
        "weighted terrain (2x/4x), Euclidean tie-breakers/shortcuts, and quarter-arc corner smoothing."
    ),
    "grid_meta": {
        "mode": "cycle",
        "min_val": 0,
        "max_val": 5,
        "labels": {"0": "", "1": "█", "2": "S", "3": "G", "4": "2×", "5": "4×"},
        "colors": {
            "0": "#232629",
            "1": "#621D19",
            "2": "#01CA6B",
            "3": "#FFE600",
            "4": "#4E4326",
            "5": "#61324A",
        },
        "editable": True,
        "resizable": True,
        "min_dim": 2,
        "max_dim": 12,
    },
    "presets": {
        "6x6": {
            "maze_type": "Tile Walls",
            "movement": "Manhattan (4-Way)",
            "tie_breaker": "None",
            "board": [
                [2, 0, 0, 1, 0, 0],
                [0, 1, 0, 1, 0, 0],
                [0, 1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0, 0],
                [0, 0, 0, 1, 1, 0],
                [0, 0, 0, 0, 0, 3],
            ],
        },
        "7x7": {
            "maze_type": "Tile Walls",
            "movement": "Manhattan (4-Way)",
            "tie_breaker": "None",
            "board": [
                [2, 0, 1, 0, 0, 0, 0],
                [0, 0, 1, 0, 1, 1, 0],
                [1, 0, 0, 0, 1, 0, 0],
                [0, 0, 1, 1, 1, 0, 1],
                [0, 1, 0, 0, 0, 0, 0],
                [0, 1, 0, 1, 1, 1, 0],
                [0, 0, 0, 0, 0, 1, 3],
            ],
        },
        "9x9": {
            "maze_type": "Tile Walls",
            "movement": "Manhattan (4-Way)",
            "tie_breaker": "None",
            "board": [
                [2, 0, 1, 0, 0, 0, 1, 0, 0],
                [0, 0, 1, 0, 1, 0, 1, 0, 0],
                [0, 1, 1, 0, 1, 0, 0, 0, 1],
                [0, 0, 0, 0, 1, 1, 1, 0, 0],
                [1, 1, 1, 0, 0, 0, 1, 1, 0],
                [0, 0, 0, 1, 1, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 1, 1, 0],
                [0, 1, 1, 1, 1, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 1, 0, 3],
            ],
        },
        "Weighted Terrain 7x7": {
            "maze_type": "Tile Walls",
            "movement": "Manhattan (4-Way)",
            "tie_breaker": "None",
            "board": [
                [2, 5, 5, 5, 0, 0, 0],
                [4, 4, 5, 0, 0, 1, 0],
                [4, 0, 0, 0, 1, 0, 0],
                [5, 0, 1, 0, 0, 0, 4],
                [5, 0, 0, 0, 5, 5, 0],
                [4, 4, 5, 0, 5, 4, 0],
                [4, 4, 5, 0, 0, 0, 3],
            ],
        },
        "Edge Walls 6x6": {
            "maze_type": "Edge Walls",
            "movement": "Manhattan (4-Way)",
            "tie_breaker": "None",
            "board": [
                [2, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 3],
            ],
            "h_walls": [
                [0, 0, 0, 0, 0, 0],
                [0, 1, 1, 0, 1, 0],
                [0, 0, 1, 1, 0, 0],
                [1, 1, 0, 0, 1, 1],
                [0, 0, 1, 1, 0, 0],
                [0, 1, 0, 0, 1, 0],
                [0, 0, 0, 0, 0, 0],
            ],
            "v_walls": [
                [0, 0, 1, 0, 0, 0, 0],
                [0, 1, 0, 0, 1, 0, 0],
                [0, 0, 0, 1, 0, 0, 0],
                [0, 1, 0, 0, 1, 0, 0],
                [0, 0, 1, 0, 0, 1, 0],
                [0, 0, 0, 1, 0, 0, 0],
            ],
        },
        "Hex Maze 7x7": {
            "geometry": "Hexagonal (6-Way)",
            "maze_type": "Tile Walls",
            "movement": "Manhattan (4-Way)",
            "tie_breaker": "None",
            "board": [
                [2, 0, 1, 0, 0, 0, 0],
                [0, 1, 1, 0, 1, 1, 0],
                [0, 0, 0, 0, 1, 0, 0],
                [1, 1, 0, 1, 1, 0, 1],
                [0, 0, 0, 0, 0, 0, 0],
                [0, 1, 1, 1, 0, 1, 0],
                [0, 0, 0, 1, 0, 0, 3],
            ],
        },
        "Hex Weighted Terrain 7x7": {
            "geometry": "Hexagonal (6-Way)",
            "maze_type": "Tile Walls",
            "movement": "Manhattan (4-Way)",
            "tie_breaker": "None",
            "board": [
                [2, 5, 5, 0, 0, 0, 0],
                [4, 5, 0, 0, 1, 0, 0],
                [0, 0, 0, 1, 0, 0, 4],
                [0, 1, 0, 0, 0, 5, 4],
                [0, 0, 0, 5, 5, 0, 0],
                [4, 4, 0, 5, 0, 0, 0],
                [0, 0, 0, 0, 0, 1, 3],
            ],
        },
    },
    "params": [
        {
            "key": "geometry",
            "label": "Grid",
            "type": "select",
            "default": "Square Grid",
            "options": ["Square Grid", "Hexagonal (6-Way)"],
        },
        {
            "key": "algorithm",
            "label": "Algorithm",
            "type": "select",
            "default": "A*",
            "options": ["A*", "Dijkstra", "BFS"],
        },
        {
            "key": "movement",
            "label": "Movement",
            "type": "select",
            "default": "Manhattan (4-Way)",
            "options": [
                "Manhattan (4-Way)",
                "Diagonal Euclidean (8-Way)",
            ],
        },
        {
            "key": "tie_breaker",
            "label": "Tie-Breaker",
            "type": "select",
            "default": "None",
            "options": ["None", "Euclidean", "Corner Arc"],
        },
        {
            "key": "show_tied_paths",
            "label": "Show Ties",
            "type": "bool",
            "default": True,
        },
    ],
}

SQRT2 = math.sqrt(2.0)
SQRT3 = math.sqrt(3.0)
QUARTER_ARC_LEN = math.pi / 4.0
HEX_TIGHT_ARC_LEN = math.pi / (3.0 * SQRT3)
HEX_WIDE_ARC_LEN = math.pi / (2.0 * SQRT3)
HEX_TIGHT_RAD = 1.0 / (2.0 * SQRT3)
HEX_WIDE_RAD = SQRT3 / 2.0


def _hex_norm_center(r: int, c: int) -> Tuple[float, float]:
    return (c + (0.5 if (r & 1) else 0.0), r * (SQRT3 / 2.0))


def _build_hex_path_svg(path: List[List[int]], tie_breaker: str) -> List[Dict[str, Any]]:
    """Build normalized-hex-coordinate SVG ops (entry-midpoint to exit-midpoint chords/arcs)."""
    if not path:
        return []
    p0 = _hex_norm_center(path[0][0], path[0][1])
    ops: List[Dict[str, Any]] = [{"op": "M", "x": p0[0], "y": p0[1]}]
    if len(path) == 1:
        return ops
    if tie_breaker == "None" or len(path) < 3:
        for pr, pc in path[1:]:
            px, py = _hex_norm_center(pr, pc)
            ops.append({"op": "L", "x": px, "y": py})
        return ops

    use_arc = tie_breaker in ("Corner Arc", "Quarter-Arc")
    for i in range(1, len(path) - 1):
        ax, ay = _hex_norm_center(path[i - 1][0], path[i - 1][1])
        bx, by = _hex_norm_center(path[i][0], path[i][1])
        cx, cy = _hex_norm_center(path[i + 1][0], path[i + 1][1])
        in_x, in_y = (ax + bx) * 0.5, (ay + by) * 0.5
        out_x, out_y = (bx + cx) * 0.5, (by + cy) * 0.5
        ux, uy = bx - ax, by - ay
        vx, vy = cx - bx, cy - by
        dot = ux * vx + uy * vy
        ops.append({"op": "L", "x": in_x, "y": in_y})
        if use_arc and dot < 0.9:
            rad = HEX_WIDE_RAD if dot > 0.0 else HEX_TIGHT_RAD
            cross = ux * vy - uy * vx
            sweep = 1 if cross > 0 else 0
            ops.append({"op": "A", "rx": rad, "ry": rad, "sweep": sweep, "x": out_x, "y": out_y})
        else:
            ops.append({"op": "L", "x": out_x, "y": out_y})

    pend = _hex_norm_center(path[-1][0], path[-1][1])
    ops.append({"op": "L", "x": pend[0], "y": pend[1]})
    return ops


def _cell_weight(board: List[List[int]], weights: Optional[List[List[float]]], r: int, c: int) -> float:
    if weights and r < len(weights) and c < len(weights[r]):
        return max(0.1, float(weights[r][c]))
    v = board[r][c]
    if v == 4:
        return 2.0
    if v == 5:
        return 4.0
    return 1.0


def _is_ortho_blocked(
    r: int,
    c: int,
    dr: int,
    dc: int,
    rows: int,
    cols: int,
    board: List[List[int]],
    use_edge_walls: bool,
    h_walls: List[List[int]],
    v_walls: List[List[int]],
) -> bool:
    nr, nc = r + dr, c + dc
    if not (0 <= nr < rows and 0 <= nc < cols):
        return True
    if board[nr][nc] == 1:
        return True
    if use_edge_walls:
        if dr == 1 and h_walls[r + 1][c] == 1:
            return True
        if dr == -1 and h_walls[r][c] == 1:
            return True
        if dc == 1 and v_walls[r][c + 1] == 1:
            return True
        if dc == -1 and v_walls[r][c] == 1:
            return True
    return False


def _is_step_allowed(
    r: int,
    c: int,
    dr: int,
    dc: int,
    rows: int,
    cols: int,
    board: List[List[int]],
    use_edge_walls: bool,
    h_walls: List[List[int]],
    v_walls: List[List[int]],
) -> bool:
    nr, nc = r + dr, c + dc
    if not (0 <= nr < rows and 0 <= nc < cols) or board[nr][nc] == 1:
        return False
    if abs(dr) + abs(dc) == 1:
        return not _is_ortho_blocked(r, c, dr, dc, rows, cols, board, use_edge_walls, h_walls, v_walls)
    # Diagonal: disallow corner cutting across blocked cells or edge walls
    if _is_ortho_blocked(r, c, dr, 0, rows, cols, board, use_edge_walls, h_walls, v_walls):
        return False
    if _is_ortho_blocked(r, c, 0, dc, rows, cols, board, use_edge_walls, h_walls, v_walls):
        return False
    if _is_ortho_blocked(r + dr, c, 0, dc, rows, cols, board, use_edge_walls, h_walls, v_walls):
        return False
    if _is_ortho_blocked(r, c + dc, dr, 0, rows, cols, board, use_edge_walls, h_walls, v_walls):
        return False
    return True


def _build_path_svg(path: List[List[int]], curved: bool) -> List[Dict[str, Any]]:
    """Convert cell path [[r, c], ...] into SVG path ops in cell-grid coordinates."""
    if not path:
        return []
    ops: List[Dict[str, Any]] = [{"op": "M", "x": path[0][1] + 0.5, "y": path[0][0] + 0.5}]
    if len(path) == 1:
        return ops

    if not curved or len(path) < 3:
        for pr, pc in path[1:]:
            ops.append({"op": "L", "x": pc + 0.5, "y": pr + 0.5})
        return ops

    for i in range(1, len(path) - 1):
        r0, c0 = path[i - 1]
        r1, c1 = path[i]
        r2, c2 = path[i + 1]
        dr1, dc1 = r1 - r0, c1 - c0
        dr2, dc2 = r2 - r1, c2 - c1
        is_ortho_90 = (
            abs(dr1) + abs(dc1) == 1
            and abs(dr2) + abs(dc2) == 1
            and (dr1 != dr2 or dc1 != dc2)
            and (dr1 + dr2 != 0 or dc1 + dc2 != 0)
        )
        if is_ortho_90:
            in_x = (c0 + c1) / 2.0 + 0.5
            in_y = (r0 + r1) / 2.0 + 0.5
            out_x = (c1 + c2) / 2.0 + 0.5
            out_y = (r1 + r2) / 2.0 + 0.5
            cross = dc1 * dr2 - dr1 * dc2
            sweep = 1 if cross > 0 else 0
            ops.append({"op": "L", "x": in_x, "y": in_y})
            ops.append({"op": "A", "rx": 0.5, "ry": 0.5, "sweep": sweep, "x": out_x, "y": out_y})
        else:
            ops.append({"op": "L", "x": c1 + 0.5, "y": r1 + 0.5})

    ops.append({"op": "L", "x": path[-1][1] + 0.5, "y": path[-1][0] + 0.5})
    return ops


def _cross_track_deviation(r: int, c: int, start: Tuple[int, int], goal: Tuple[int, int]) -> float:
    sr, sc = start
    gr, gc = goal
    dr, dc = gr - sr, gc - sc
    denom = math.hypot(dr, dc)
    if denom == 0.0:
        return 0.0
    return abs((c - sc) * dr - (r - sr) * dc) / denom


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = [list(r) for r in state["board"]]
    rows, cols = len(board), len(board[0])
    weights = state.get("weights")

    algo = str(params.get("algorithm") or state.get("algorithm") or "A*")
    geometry = str(params.get("geometry") or state.get("geometry") or "Square Grid")
    is_hex = geometry == "Hexagonal (6-Way)"
    maze_type = str(params.get("maze_type") or state.get("maze_type") or "Tile Walls")
    movement = str(params.get("movement") or state.get("movement") or "Manhattan (4-Way)")
    tie_breaker = str(params.get("tie_breaker") or state.get("tie_breaker") or "None")
    show_tied_paths = bool(params.get("show_tied_paths", True))

    raw_h = state.get("h_walls")
    raw_v = state.get("v_walls")
    h_walls = (
        [list(row[:cols]) + [0] * max(0, cols - len(row)) for row in raw_h[: rows + 1]]
        + [[0] * cols for _ in range(max(0, rows + 1 - len(raw_h)))]
        if isinstance(raw_h, list)
        else [[0] * cols for _ in range(rows + 1)]
    )
    v_walls = (
        [list(row[: cols + 1]) + [0] * max(0, cols + 1 - len(row)) for row in raw_v[:rows]]
        + [[0] * (cols + 1) for _ in range(max(0, rows - len(raw_v)))]
        if isinstance(raw_v, list)
        else [[0] * (cols + 1) for _ in range(rows)]
    )
    raw_hex = state.get("hex_walls")
    hex_walls = set(str(x) for x in raw_hex) if isinstance(raw_hex, list) else set()
    use_edge_walls = maze_type == "Edge Walls" or ("h_walls" in state and "v_walls" in state)

    start = next(((r, c) for r in range(rows) for c in range(cols) if board[r][c] == 2), (0, 0))
    goal = next(((r, c) for r in range(rows) for c in range(cols) if board[r][c] == 3), (rows - 1, cols - 1))

    def snap() -> Dict[str, Any]:
        out: Dict[str, Any] = {
            "board": [list(row) for row in board],
            "geometry": geometry,
            "maze_type": "Edge Walls" if use_edge_walls else "Tile Walls",
            "movement": movement,
            "tie_breaker": tie_breaker,
        }
        if use_edge_walls:
            out["h_walls"] = h_walls
            out["v_walls"] = v_walls
        if hex_walls:
            out["hex_walls"] = sorted(hex_walls)
        if weights is not None:
            out["weights"] = weights
        return out

    open_weights = [
        _cell_weight(board, weights, r, c)
        for r in range(rows)
        for c in range(cols)
        if board[r][c] != 1
    ]
    min_w = min(open_weights) if open_weights else 1.0

    yield {
        "type": "start",
        "state": snap(),
        "highlights": {"cells": [list(start), list(goal)], "color": "secondary"},
        "desc": f"{algo} ({movement}, tie={tie_breaker}) from {start} to {goal}",
        "stats": {"explored": 0, "movement": movement, "tie_breaker": tie_breaker},
    }

    ortho_dirs = [(-1, 0), (1, 0), (0, -1), (0, 1)]
    diag_dirs = [(-1, -1), (-1, 1), (1, -1), (1, 1)]
    hex_even_dirs = [(-1, -1), (-1, 0), (0, -1), (0, 1), (1, -1), (1, 0)]
    hex_odd_dirs = [(-1, 0), (-1, 1), (0, -1), (0, 1), (1, 0), (1, 1)]
    allow_diag = (not is_hex) and movement in ("Diagonal Euclidean (8-Way)", "Quarter-Arc Corners")
    use_quarter_arc = (not is_hex) and movement == "Quarter-Arc Corners"
    dirs = ortho_dirs + diag_dirs if allow_diag else ortho_dirs

    def _to_cube(r: int, c: int) -> Tuple[int, int, int]:
        q = c - (r - (r & 1)) // 2
        s = -q - r
        return (q, r, s)

    goal_cube = _to_cube(goal[0], goal[1])

    def _hex_edge_key(r1: int, c1: int, r2: int, c2: int) -> str:
        a, b = ((r1, c1), (r2, c2)) if (r1, c1) < (r2, c2) else ((r2, c2), (r1, c1))
        return f"{a[0]},{a[1]}|{b[0]},{b[1]}"

    def hex_neighbors(r: int, c: int) -> List[Tuple[int, int]]:
        offsets = hex_odd_dirs if (r & 1) else hex_even_dirs
        out: List[Tuple[int, int]] = []
        for dr, dc in offsets:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != 1:
                if hex_walls and _hex_edge_key(r, c, nr, nc) in hex_walls:
                    continue
                out.append((nr, nc))
        return out

    def heuristic(r: int, c: int) -> float:
        if algo in ("Dijkstra", "BFS"):
            return 0.0
        if is_hex:
            q, rr, s = _to_cube(r, c)
            gq, gr, gs = goal_cube
            return min_w * max(abs(q - gq), abs(rr - gr), abs(s - gs))
        dr, dc = abs(r - goal[0]), abs(c - goal[1])
        if movement == "Manhattan (4-Way)":
            return min_w * (dr + dc)
        if movement == "Diagonal Euclidean (8-Way)":
            return min_w * ((SQRT2 - 1.0) * min(dr, dc) + max(dr, dc))
        # Quarter-Arc Corners: strictly admissible lower bound
        return min_w * QUARTER_ARC_LEN * math.hypot(dr, dc)

    # Search state: (r, c, enter_dir) when turn angle affects cost or arc/hex tie-breaker; else (r, c, None)
    track_dir = use_quarter_arc or tie_breaker in ("Corner Arc", "Quarter-Arc") or (is_hex and tie_breaker != "None")
    start_key: Tuple[int, int, Optional[Tuple[int, int]]] = (start[0], start[1], None)
    parent: Dict[Tuple[int, int, Optional[Tuple[int, int]]], Optional[Tuple[int, int, Optional[Tuple[int, int]]]]] = {
        start_key: None
    }
    best_score: Dict[Tuple[int, int, Optional[Tuple[int, int]]], Tuple[float, float]] = {start_key: (0.0, 0.0)}
    best_g_cell: Dict[Tuple[int, int], float] = {start: 0.0}
    eq_parents: Dict[Tuple[int, int], List[Tuple[int, int]]] = {start: []}
    explored_cells: List[Tuple[int, int]] = []
    explored_seen: set = set()
    goal_key: Optional[Tuple[int, int, Optional[Tuple[int, int]]]] = None
    final_cost: Optional[float] = None

    def _record_eq_parent(nr: int, nc: int, pr: int, pc: int, ng: float) -> None:
        if not show_tied_paths:
            return
        prev_g = best_g_cell.get((nr, nc))
        rng = round(ng, 9)
        if prev_g is None or rng < round(prev_g, 9):
            best_g_cell[(nr, nc)] = ng
            eq_parents[(nr, nc)] = [(pr, pc)]
        elif rng == round(prev_g, 9) and (pr, pc) not in eq_parents[(nr, nc)]:
            eq_parents[(nr, nc)].append((pr, pc))

    def transition_costs(
        r: int,
        c: int,
        enter_dir: Optional[Tuple[int, int]],
        dr: int,
        dc: int,
    ) -> Tuple[float, float]:
        """Return (primary_cost, secondary_tie_delta)."""
        nr, nc = r + dr, c + dc
        is_diag = abs(dr) == 1 and abs(dc) == 1
        w_cur = _cell_weight(board, weights, r, c)
        w_nxt = _cell_weight(board, weights, nr, nc)
        is_ortho_90 = (
            enter_dir is not None
            and not is_diag
            and abs(enter_dir[0]) + abs(enter_dir[1]) == 1
            and (dr, dc) != enter_dir
            and (dr + enter_dir[0] != 0 or dc + enter_dir[1] != 0)
        )

        # Primary cost
        if algo == "BFS":
            primary = SQRT2 if is_diag else (QUARTER_ARC_LEN if (use_quarter_arc and is_ortho_90) else 1.0)
        elif use_quarter_arc:
            # Half-tile symmetric accounting so every edge weight is strictly positive
            if is_diag:
                exit_cur = (SQRT2 * 0.5 - 0.5) * w_cur if (r, c) != start else SQRT2 * 0.5 * w_cur
                entry_nxt = SQRT2 * 0.5 * w_nxt
                if (nr, nc) == goal:
                    entry_nxt += 0.5 * (1.0 - SQRT2 * 0.5) * w_nxt
                primary = exit_cur + entry_nxt
            else:
                if (r, c) == start:
                    exit_cur = 0.5 * w_cur
                elif is_ortho_90:
                    # Total cost inside corner tile = 0.5 + (pi/4 - 0.5) = (pi/4) * w_cur
                    exit_cur = (QUARTER_ARC_LEN - 0.5) * w_cur
                else:
                    exit_cur = 0.5 * w_cur
                entry_nxt = 0.5 * w_nxt + (0.5 * w_nxt if (nr, nc) == goal else 0.0)
                primary = exit_cur + entry_nxt
        elif is_diag:
            primary = SQRT2 * w_nxt
        else:
            primary = w_nxt

        # Secondary tie-breaker delta (active primarily on Manhattan / equal primary cost)
        if tie_breaker == "Euclidean":
            step_len = SQRT2 if is_diag else 1.0
            turn_pen = 0.01 if (enter_dir is not None and enter_dir != (dr, dc)) else 0.0
            sec = step_len + 0.15 * _cross_track_deviation(nr, nc, start, goal) + turn_pen
        elif tie_breaker in ("Corner Arc", "Quarter-Arc"):
            # Prefer paths whose 90-degree corner turns round through lower-weight cells using pi/4 scaling
            if is_ortho_90:
                sec = (QUARTER_ARC_LEN - 1.0) * w_cur + w_nxt
            else:
                sec = SQRT2 * w_nxt if is_diag else w_nxt
        else:
            sec = 0.0

        return primary, sec

    if is_hex:
        sx, sy = _hex_norm_center(start[0], start[1])
        gx, gy = _hex_norm_center(goal[0], goal[1])
        sg_len = math.hypot(gx - sx, gy - sy)

        def hex_cross_dev(hr: int, hc: int) -> float:
            if sg_len == 0.0:
                return 0.0
            hx, hy = _hex_norm_center(hr, hc)
            return abs((hx - sx) * (gy - sy) - (hy - sy) * (gx - sx)) / sg_len

        counter = 0
        pq_hex: List[Tuple[float, float, float, int, Tuple[int, int, Optional[Tuple[int, int]]]]] = [
            (heuristic(start[0], start[1]), 0.0, 0.0, counter, start_key)
        ]
        while pq_hex:
            if should_abort():
                return
            f_val, tie_s, g, _, cur = heapq.heappop(pq_hex)
            if final_cost is not None and f_val > round(final_cost, 9):
                break
            if (round(g, 9), round(tie_s, 9)) > (round(best_score[cur][0], 9), round(best_score[cur][1], 9)):
                continue
            r, c, enter_vec = cur
            if (r, c) not in explored_seen:
                explored_seen.add((r, c))
                explored_cells.append((r, c))
            if (r, c) == goal:
                if goal_key is None:
                    goal_key = cur
                    final_cost = g
                if not show_tied_paths:
                    break
                continue
            cx, cy = _hex_norm_center(r, c)
            w_cur = _cell_weight(board, weights, r, c)
            for nr, nc in hex_neighbors(r, c):
                nx, ny = _hex_norm_center(nr, nc)
                vx, vy = nx - cx, ny - cy
                step_vec = (round(vx, 4), round(vy, 4))
                nxt_key = (nr, nc, step_vec if tie_breaker != "None" else None)
                step_cost = 1.0 if algo == "BFS" else _cell_weight(board, weights, nr, nc)
                ng = g + step_cost
                _record_eq_parent(nr, nc, r, c, ng)

                ds = 0.0
                if tie_breaker != "None":
                    w_nxt = _cell_weight(board, weights, nr, nc)
                    if enter_vec is not None:
                        dot = enter_vec[0] * vx + enter_vec[1] * vy
                        if tie_breaker in ("Corner Arc", "Quarter-Arc"):
                            if dot > 0.9:
                                turn_len = 1.0
                            elif dot > 0.0:
                                turn_len = HEX_WIDE_ARC_LEN
                            else:
                                turn_len = HEX_TIGHT_ARC_LEN
                            ds = (turn_len - 1.0) * w_cur + w_nxt
                        else:
                            # Euclidean shortcut chord inside current hex + cross-track straightness
                            chord = 1.0 if dot > 0.9 else (HEX_WIDE_RAD if dot > 0.0 else 0.5)
                            ds = (chord - 1.0) * w_cur + w_nxt + 0.05 * hex_cross_dev(nr, nc)
                    else:
                        ds = w_nxt + (0.05 * hex_cross_dev(nr, nc) if tie_breaker == "Euclidean" else 0.0)

                nt = tie_s + ds
                prev = best_score.get(nxt_key)
                if prev is None or (round(ng, 9), round(nt, 9)) < (round(prev[0], 9), round(prev[1], 9)):
                    best_score[nxt_key] = (ng, nt)
                    parent[nxt_key] = cur
                    counter += 1
                    f = ng + heuristic(nr, nc)
                    heapq.heappush(pq_hex, (round(f, 9), round(nt, 9), ng, counter, nxt_key))
    elif algo == "BFS" and movement == "Manhattan (4-Way)" and tie_breaker == "None":
        q = deque([start_key])
        while q:
            if should_abort():
                return
            cur = q.popleft()
            r, c, _ = cur
            cur_g = best_score[cur][0]
            if final_cost is not None and round(cur_g, 9) > round(final_cost, 9):
                break
            if (r, c) not in explored_seen:
                explored_seen.add((r, c))
                explored_cells.append((r, c))
            if (r, c) == goal:
                if goal_key is None:
                    goal_key = cur
                    final_cost = float(cur_g)
                if not show_tied_paths:
                    break
                continue
            for dr, dc in dirs:
                if not _is_step_allowed(r, c, dr, dc, rows, cols, board, use_edge_walls, h_walls, v_walls):
                    continue
                nr, nc = r + dr, c + dc
                ng = cur_g + 1.0
                _record_eq_parent(nr, nc, r, c, ng)
                nxt_key = (nr, nc, None)
                if nxt_key not in best_score:
                    best_score[nxt_key] = (ng, 0.0)
                    parent[nxt_key] = cur
                    q.append(nxt_key)
    else:
        counter = 0
        pq: List[Tuple[float, float, float, int, Tuple[int, int, Optional[Tuple[int, int]]]]] = [
            (heuristic(start[0], start[1]), 0.0, 0.0, counter, start_key)
        ]
        while pq:
            if should_abort():
                return
            f_val, tie_s, g, _, cur = heapq.heappop(pq)
            if final_cost is not None and f_val > round(final_cost, 9):
                break
            if (round(g, 9), round(tie_s, 9)) > (round(best_score[cur][0], 9), round(best_score[cur][1], 9)):
                continue
            r, c, enter_dir = cur
            if (r, c) not in explored_seen:
                explored_seen.add((r, c))
                explored_cells.append((r, c))
            if (r, c) == goal:
                if goal_key is None:
                    goal_key = cur
                    final_cost = g
                if not show_tied_paths:
                    break
                continue
            for dr, dc in dirs:
                if not _is_step_allowed(r, c, dr, dc, rows, cols, board, use_edge_walls, h_walls, v_walls):
                    continue
                nr, nc = r + dr, c + dc
                nxt_dir = (dr, dc) if track_dir else (None if tie_breaker == "None" else (dr, dc))
                nxt_key = (nr, nc, nxt_dir)
                dp, ds = transition_costs(r, c, enter_dir, dr, dc)
                ng = g + dp
                _record_eq_parent(nr, nc, r, c, ng)
                nt = tie_s + ds
                prev = best_score.get(nxt_key)
                if prev is None or (round(ng, 9), round(nt, 9)) < (round(prev[0], 9), round(prev[1], 9)):
                    best_score[nxt_key] = (ng, nt)
                    parent[nxt_key] = cur
                    counter += 1
                    f = ng + heuristic(nr, nc)
                    heapq.heappush(pq, (round(f, 9), round(nt, 9), ng, counter, nxt_key))

    # Emit sampled frontier exploration steps so [EXPLORE] search progression is visible
    total_exp = len(explored_cells)
    if total_exp > 1:
        stride = max(1, total_exp // 10)
        for idx in range(stride, total_exp, stride):
            if should_abort():
                return
            yield {
                "type": "explore",
                "state": snap(),
                "highlights": {"cells": [[pr, pc] for pr, pc in explored_cells[:idx]], "color": "secondary"},
                "desc": f"{algo} expanded {idx}/{total_exp} frontier cells",
                "stats": {"explored": idx, "total_explored": total_exp},
            }

    if goal_key is None:
        yield {
            "type": "failed",
            "state": snap(),
            "highlights": {"cells": [list(p) for p in explored_cells], "color": "hot"},
            "desc": "No path exists from Start (S) to Goal (G).",
            "stats": {"explored": len(explored_cells)},
        }
        return

    path: List[List[int]] = []
    cur_k: Optional[Tuple[int, int, Optional[Tuple[int, int]]]] = goal_key
    while cur_k is not None:
        path.append([cur_k[0], cur_k[1]])
        cur_k = parent[cur_k]
    path.reverse()

    curved = use_quarter_arc or tie_breaker in ("Corner Arc", "Quarter-Arc")
    path_svg = _build_hex_path_svg(path, tie_breaker) if is_hex else _build_path_svg(path, curved=curved)

    tied_paths: List[List[List[int]]] = []
    if show_tied_paths and goal in eq_parents:
        max_ties = 24
        stack: List[Tuple[Tuple[int, int], List[Tuple[int, int]]]] = [(goal, [goal])]
        while stack and len(tied_paths) < max_ties:
            node, rev = stack.pop()
            if node == start:
                cand = [[pr, pc] for pr, pc in reversed(rev)]
                if cand != path:
                    tied_paths.append(cand)
                continue
            for p_cell in eq_parents.get(node, ()):
                if p_cell not in rev:
                    stack.append((p_cell, rev + [p_cell]))

    tied_paths_svg = [
        _build_hex_path_svg(tp, tie_breaker) if is_hex else _build_path_svg(tp, curved=curved)
        for tp in tied_paths
    ]

    fc = float(final_cost or 0.0)
    cost_display = int(fc) if abs(fc - round(fc)) < 1e-6 else round(fc, 3)
    yield {
        "type": "solution",
        "state": snap(),
        "highlights": {
            "cells": path,
            "path": path,
            "path_svg": path_svg,
            "tied_paths": tied_paths,
            "tied_paths_svg": tied_paths_svg,
            "color": "primary",
        },
        "desc": (
            f"{algo} ({movement}, tie={tie_breaker}) found path: {len(path) - 1} steps, "
            f"cost={cost_display} (explored {len(explored_cells)} cells"
            + (f", +{len(tied_paths)} tied" if tied_paths else "")
            + ")"
        ),
        "stats": {
            "steps": len(path) - 1,
            "cost": cost_display,
            "explored": len(explored_cells),
            **({"ties": len(tied_paths)} if tied_paths else {}),
        },
    }
