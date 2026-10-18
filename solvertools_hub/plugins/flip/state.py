"""
state.py - Flip / Lights Out state representation, serialization, and validation.
"""

import json
from typing import List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class FlipState(BasePuzzleState):
    """
    Represents an M x N grid of toggleable lights.
    grid[r][c] is 1 (Light ON) or 0 (Light OFF).
    """

    def __init__(
        self,
        rows: int = 5,
        cols: int = 5,
        grid: Optional[List[List[int]]] = None,
    ):
        self.rows = rows
        self.cols = cols
        if grid is not None:
            self.grid = [list(row) for row in grid]
        else:
            # Solvable default pattern (a nice cross pattern on 5x5)
            self.grid = [[0 for _ in range(cols)] for _ in range(rows)]
            if rows == 5 and cols == 5:
                # Classic pattern
                self.grid[1][2] = 1
                self.grid[2][1] = 1
                self.grid[2][2] = 1
                self.grid[2][3] = 1
                self.grid[3][2] = 1

    def clone(self) -> "FlipState":
        return FlipState(self.rows, self.cols, [list(r) for r in self.grid])

    def serialize(self) -> str:
        return json.dumps({
            "puzzle": "flip",
            "rows": self.rows,
            "cols": self.cols,
            "grid": self.grid,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "FlipState":
        data = json.loads(raw_data)
        return cls(
            rows=int(data["rows"]),
            cols=int(data["cols"]),
            grid=data["grid"],
        )

    def validate(self) -> Tuple[bool, str]:
        if self.rows < 2 or self.cols < 2:
            return False, "Grid dimensions must be at least 2x2."
        if len(self.grid) != self.rows or any(len(r) != self.cols for r in self.grid):
            return False, f"Grid must strictly match {self.rows}x{self.cols} dimensions."
        for row in self.grid:
            for val in row:
                if val not in (0, 1):
                    return False, "Cell values must be binary (0 or 1)."
        return True, "Valid Flip puzzle configuration."

    def is_solved(self) -> bool:
        """All lights are OFF."""
        return all(all(val == 0 for val in row) for row in self.grid)

    def toggle_cell_and_neighbors(self, r: int, c: int) -> None:
        """Simulates pressing a button, toggling itself and orthogonal neighbors."""
        for dr, dc in [(0, 0), (-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.rows and 0 <= nc < self.cols:
                self.grid[nr][nc] ^= 1
