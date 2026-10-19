"""
state.py - Packing Grids & Nonograms state model.
Represents a 2D binary pixel grid with row and column run-length clues (Picross / Nonograms)
and polyomino piece definitions for Exact Cover (DLX).
"""

import json
from typing import List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class PackingGridsState(BasePuzzleState):
    """
    Nonogram & Polyomino Packing puzzle state.
    rows, cols: Dimensions of the grid.
    grid: 2D array of cell states (0 = Empty, 1 = Filled Pixel, -1 = Marked Cross).
    row_clues: List of run-length integer lists for each row.
    col_clues: List of run-length integer lists for each column.
    """

    CELL_EMPTY = 0
    CELL_FILLED = 1
    CELL_CROSS = -1

    def __init__(
        self,
        rows: int = 5,
        cols: int = 5,
        grid: Optional[List[List[int]]] = None,
        row_clues: Optional[List[List[int]]] = None,
        col_clues: Optional[List[List[int]]] = None,
    ):
        self.rows = max(3, min(20, int(rows)))
        self.cols = max(3, min(20, int(cols)))

        if grid is not None:
            self.grid = [list(r) for r in grid]
        else:
            self.grid = [[self.CELL_EMPTY for _ in range(self.cols)] for _ in range(self.rows)]

        if row_clues is not None:
            self.row_clues = [list(c) for c in row_clues]
        else:
            # Sample smiley / cross nonogram clues
            self.row_clues = [[1, 1], [1, 1], [1, 1], [3], [1]]

        if col_clues is not None:
            self.col_clues = [list(c) for c in col_clues]
        else:
            self.col_clues = [[3], [1, 1], [1], [1, 1], [3]]

    def clone(self) -> "PackingGridsState":
        return PackingGridsState(
            rows=self.rows,
            cols=self.cols,
            grid=[list(r) for r in self.grid],
            row_clues=[list(c) for c in self.row_clues],
            col_clues=[list(c) for c in self.col_clues],
        )

    def serialize(self) -> str:
        return json.dumps({
            "rows": self.rows,
            "cols": self.cols,
            "grid": self.grid,
            "row_clues": self.row_clues,
            "col_clues": self.col_clues,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "PackingGridsState":
        data = json.loads(raw_data)
        return cls(
            rows=data["rows"],
            cols=data["cols"],
            grid=data["grid"],
            row_clues=data["row_clues"],
            col_clues=data["col_clues"],
        )

    def validate(self) -> Tuple[bool, str]:
        if len(self.grid) != self.rows or any(len(r) != self.cols for r in self.grid):
            return False, f"Grid dimensions must match {self.rows}x{self.cols}"
        if len(self.row_clues) != self.rows:
            return False, f"Row clues count ({len(self.row_clues)}) must match rows ({self.rows})"
        if len(self.col_clues) != self.cols:
            return False, f"Col clues count ({len(self.col_clues)}) must match cols ({self.cols})"
        return True, ""
