"""Polyomino / Pentomino exact-cover tiling solver using Algorithm X with Dancing Links (DLX)."""

from __future__ import annotations

from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

PENTOMINOES: Dict[str, List[Tuple[int, int]]] = {
    "F": [(0, 1), (0, 2), (1, 0), (1, 1), (2, 1)],
    "I": [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0)],
    "L": [(0, 0), (1, 0), (2, 0), (3, 0), (3, 1)],
    "P": [(0, 0), (0, 1), (1, 0), (1, 1), (2, 0)],
    "N": [(0, 0), (1, 0), (1, 1), (2, 1), (3, 1)],
    "T": [(0, 0), (0, 1), (0, 2), (1, 1), (2, 1)],
    "U": [(0, 0), (0, 2), (1, 0), (1, 1), (1, 2)],
    "V": [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)],
    "W": [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2)],
    "X": [(0, 1), (1, 0), (1, 1), (1, 2), (2, 1)],
    "Y": [(0, 1), (1, 0), (1, 1), (2, 1), (3, 1)],
    "Z": [(0, 0), (0, 1), (1, 1), (2, 1), (2, 2)],
}

TETROMINOES: Dict[str, List[Tuple[int, int]]] = {
    "I": [(0, 0), (1, 0), (2, 0), (3, 0)],
    "O": [(0, 0), (0, 1), (1, 0), (1, 1)],
    "T": [(0, 0), (0, 1), (0, 2), (1, 1)],
    "L": [(0, 0), (1, 0), (2, 0), (2, 1)],
    "S": [(0, 1), (0, 2), (1, 0), (1, 1)],
}

PIECE_ORDER = ["F", "I", "L", "P", "N", "T", "U", "V", "W", "X", "Y", "Z", "O", "S"]
PIECE_COLORS = [
    "#00F5D4",
    "#FF007F",
    "#FFE600",
    "#01CA6B",
    "#FA8231",
    "#B9A7E3",
    "#45AAF2",
    "#FF4D4D",
    "#A3CB38",
    "#FDA7DF",
    "#F7B731",
    "#8854D0",
    "#20BF6B",
    "#E76C8F",
]


def _hole_board_8x8() -> List[List[int]]:
    b = [[0] * 8 for _ in range(8)]
    for r in (3, 4):
        for c in (3, 4):
            b[r][c] = -1
    return b


META: Dict[str, Any] = {
    "slug": "polyomino_dlx",
    "name": "Polyomino Tiling",
    "category": "State",
    "renderer": "grid",
    "description": "Exact-cover polyomino & pentomino tiling solver using Knuth's Algorithm X (Dancing Links).",
    "grid_meta": {
        "mode": "cycle",
        "min_val": -1,
        "max_val": 0,
        "labels": {
            "-1": "#",
            "0": "",
            **{str(i + 1): name for i, name in enumerate(PIECE_ORDER)},
        },
        "colors": {
            "-1": "#111315",
            "0": "#232629",
            **{str(i + 1): PIECE_COLORS[i] for i in range(len(PIECE_ORDER))},
        },
        "editable": True,
        "resizable": True,
        "min_dim": 2,
        "max_dim": 12,
    },
    "presets": {
        "4x4 T-Tetrominoes": {
            "board": [[0] * 4 for _ in range(4)],
            "piece_set": "Custom",
            "pieces": {
                "T1": [list(pt) for pt in TETROMINOES["T"]],
                "T2": [list(pt) for pt in TETROMINOES["T"]],
                "T3": [list(pt) for pt in TETROMINOES["T"]],
                "T4": [list(pt) for pt in TETROMINOES["T"]],
            },
        },
        "4x5 Pentominoes": {
            "board": [[0] * 5 for _ in range(4)],
            "piece_set": "Custom",
            "pieces": {k: [list(pt) for pt in PENTOMINOES[k]] for k in ("P", "U", "L", "Y")},
        },
        "6x10 Classic Pentominoes": {
            "board": [[0] * 10 for _ in range(6)],
            "piece_set": "Pentominoes (12)",
        },
        "8x8 Checkerboard Hole": {
            "board": _hole_board_8x8(),
            "piece_set": "Pentominoes (12)",
        },
    },
    "params": [
        {
            "key": "allow_flip",
            "label": "Allow Flip",
            "type": "bool",
            "default": True,
        },
        {
            "key": "step_stride",
            "label": "Trace",
            "type": "select",
            "default": "Key Branches",
            "options": ["Key Branches", "Every Step"],
        },
    ],
}


def _normalize(cells: List[Tuple[int, int]]) -> Tuple[Tuple[int, int], ...]:
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    return tuple(sorted((r - min_r, c - min_c) for r, c in cells))


def _orientations(cells: List[Tuple[int, int]], allow_flip: bool) -> List[Tuple[Tuple[int, int], ...]]:
    seen: Set[Tuple[Tuple[int, int], ...]] = set()
    out: List[Tuple[Tuple[int, int], ...]] = []
    cur = list(cells)
    flips = [False, True] if allow_flip else [False]
    for do_flip in flips:
        pts = [(-r, c) if do_flip else (r, c) for r, c in cur]
        for _ in range(4):
            pts = [(c, -r) for r, c in pts]
            norm = _normalize(pts)
            if norm not in seen:
                seen.add(norm)
                out.append(norm)
    return out


class _Node:
    __slots__ = ("left", "right", "up", "down", "col", "row_id")

    def __init__(self) -> None:
        self.left: _Node = self
        self.right: _Node = self
        self.up: _Node = self
        self.down: _Node = self
        self.col: _ColHeader = None  # type: ignore[assignment]
        self.row_id: int = -1


class _ColHeader(_Node):
    __slots__ = ("size", "name")

    def __init__(self, name: Any) -> None:
        super().__init__()
        self.col = self
        self.size: int = 0
        self.name = name


class _DLX:
    def __init__(self, num_cols: int) -> None:
        self.header = _ColHeader("ROOT")
        self.cols: List[_ColHeader] = []
        prev: _Node = self.header
        for i in range(num_cols):
            col = _ColHeader(i)
            col.left = prev
            col.right = self.header
            prev.right = col
            self.header.left = col
            prev = col
            self.cols.append(col)

    def add_row(self, row_id: int, col_indices: List[int]) -> None:
        first: Optional[_Node] = None
        for c_idx in col_indices:
            col = self.cols[c_idx]
            node = _Node()
            node.col = col
            node.row_id = row_id
            # Link vertically at bottom of column
            node.up = col.up
            node.down = col
            col.up.down = node
            col.up = node
            col.size += 1
            # Link horizontally
            if first is None:
                first = node
            else:
                node.left = first.left
                node.right = first
                first.left.right = node
                first.left = node

    def cover(self, col: _ColHeader) -> None:
        col.right.left = col.left
        col.left.right = col.right
        r = col.down
        while r is not col:
            j = r.right
            while j is not r:
                j.down.up = j.up
                j.up.down = j.down
                j.col.size -= 1
                j = j.right
            r = r.down

    def uncover(self, col: _ColHeader) -> None:
        r = col.up
        while r is not col:
            j = r.left
            while j is not r:
                j.col.size += 1
                j.down.up = j
                j.up.down = j
                j = j.left
            r = r.up
        col.right.left = col
        col.left.right = col

    def choose_col(self) -> Optional[_ColHeader]:
        best: Optional[_ColHeader] = None
        best_size = 10**9
        c = self.header.right
        while c is not self.header:
            assert isinstance(c, _ColHeader)
            if c.size < best_size:
                best_size = c.size
                best = c
                if best_size == 0:
                    return best
            c = c.right
        return best


def _resolve_pieces(state: Dict[str, Any]) -> Dict[str, List[Tuple[int, int]]]:
    raw_pieces = state.get("pieces")
    if isinstance(raw_pieces, dict) and raw_pieces:
        return {
            str(k): [(int(pt[0]), int(pt[1])) for pt in v]
            for k, v in raw_pieces.items()
        }
    pset = str(state.get("piece_set") or "Pentominoes (12)")
    if pset.startswith("Tetromino"):
        return dict(TETROMINOES)
    return dict(PENTOMINOES)


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    raw_board = state["board"]
    rows, cols = len(raw_board), len(raw_board[0])
    base_board = [[-1 if cell == -1 else 0 for cell in row] for row in raw_board]
    pieces = _resolve_pieces(state)
    allow_flip = bool(params.get("allow_flip", True))
    every_step = str(params.get("step_stride") or "Key Branches") == "Every Step"

    piece_names = list(pieces.keys())
    piece_ids: Dict[str, int] = {}
    for name in piece_names:
        if name in PIECE_ORDER:
            piece_ids[name] = PIECE_ORDER.index(name) + 1
        else:
            piece_ids[name] = (len(piece_ids) % len(PIECE_ORDER)) + 1

    open_cells = [(r, c) for r in range(rows) for c in range(cols) if base_board[r][c] == 0]
    total_piece_area = sum(len(pts) for pts in pieces.values())

    def snap(b: List[List[int]]) -> Dict[str, Any]:
        out: Dict[str, Any] = {"board": [list(row) for row in b]}
        if "piece_set" in state:
            out["piece_set"] = state["piece_set"]
        if "pieces" in state:
            out["pieces"] = state["pieces"]
        return out

    yield {
        "type": "start",
        "state": snap(base_board),
        "highlights": {},
        "desc": f"Loaded {rows}x{cols} board ({len(open_cells)} open cells, {len(piece_names)} pieces)",
        "stats": {"open_cells": len(open_cells), "pieces": len(piece_names)},
    }

    if should_abort():
        return

    if len(open_cells) != total_piece_area:
        yield {
            "type": "failed",
            "state": snap(base_board),
            "highlights": {},
            "desc": f"Area mismatch: {len(open_cells)} open cells vs {total_piece_area} piece squares.",
            "stats": {"open_cells": len(open_cells), "piece_area": total_piece_area},
        }
        return

    cell_to_col = {rc: len(piece_names) + idx for idx, rc in enumerate(open_cells)}
    dlx = _DLX(len(piece_names) + len(open_cells))
    placements: List[Tuple[str, int, List[Tuple[int, int]]]] = []

    for p_idx, p_name in enumerate(piece_names):
        pid = piece_ids[p_name]
        for orient in _orientations(pieces[p_name], allow_flip):
            max_r = max(dr for dr, _ in orient)
            max_c = max(dc for _, dc in orient)
            for r0 in range(rows - max_r):
                for c0 in range(cols - max_c):
                    cells = [(r0 + dr, c0 + dc) for dr, dc in orient]
                    if all(base_board[r][c] == 0 for r, c in cells):
                        row_id = len(placements)
                        placements.append((p_name, pid, cells))
                        dlx.add_row(row_id, [p_idx] + [cell_to_col[rc] for rc in cells])

    work_board = [list(row) for row in base_board]
    nodes_visited = 0
    backtracks = 0
    stride = 1 if every_step else 40
    solution_found = False
    events_buffer: List[Dict[str, Any]] = []

    def search() -> bool:
        nonlocal nodes_visited, backtracks, solution_found
        if should_abort():
            return False
        col = dlx.choose_col()
        if col is None:
            solution_found = True
            return True
        if col.size == 0:
            return False

        dlx.cover(col)
        r_node = col.down
        while r_node is not col:
            if should_abort():
                dlx.uncover(col)
                return False
            nodes_visited += 1
            p_name, pid, cells = placements[r_node.row_id]
            for pr, pc in cells:
                work_board[pr][pc] = pid

            if nodes_visited % stride == 0:
                events_buffer.append(
                    {
                        "type": "explore",
                        "state": snap(work_board),
                        "highlights": {"cells": [[pr, pc] for pr, pc in cells], "color": "secondary"},
                        "desc": f"Placed {p_name} (node {nodes_visited})",
                        "stats": {"nodes": nodes_visited, "backtracks": backtracks},
                    }
                )

            j = r_node.right
            while j is not r_node:
                dlx.cover(j.col)
                j = j.right

            if search():
                return True

            j = r_node.left
            while j is not r_node:
                dlx.uncover(j.col)
                j = j.left

            for pr, pc in cells:
                work_board[pr][pc] = 0
            backtracks += 1

            if backtracks % stride == 0:
                events_buffer.append(
                    {
                        "type": "backtrack",
                        "state": snap(work_board),
                        "highlights": {"cells": [[pr, pc] for pr, pc in cells], "color": "hot"},
                        "desc": f"Backtracked {p_name} (backtracks={backtracks})",
                        "stats": {"nodes": nodes_visited, "backtracks": backtracks},
                    }
                )

            r_node = r_node.down
        dlx.uncover(col)
        return False

    search()
    if should_abort():
        return

    for ev in events_buffer:
        if should_abort():
            return
        yield ev

    if solution_found:
        yield {
            "type": "solution",
            "state": snap(work_board),
            "highlights": {},
            "desc": f"Tiled {len(piece_names)} pieces ({nodes_visited} nodes, {backtracks} backtracks)",
            "stats": {
                "pieces": len(piece_names),
                "nodes": nodes_visited,
                "backtracks": backtracks,
            },
        }
    else:
        yield {
            "type": "failed",
            "state": snap(base_board),
            "highlights": {},
            "desc": f"No exact cover tiling exists ({nodes_visited} nodes explored).",
            "stats": {"nodes": nodes_visited, "backtracks": backtracks},
        }
