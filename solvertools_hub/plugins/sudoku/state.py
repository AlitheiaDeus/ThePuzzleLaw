"""
state.py - Sudoku state representation, validation, and serialization.
Supports arbitrary dimensions (e.g., 4x4, 9x9, 16x16) and rectangular sub-boxes (box_w x box_h).
"""

import json
from typing import List, Optional, Set, Tuple

from ...core.base_plugin import BasePuzzleState


class SudokuState(BasePuzzleState):
    """
    Represents an arbitrary N x N Sudoku grid partitioned into (box_w x box_h) sub-grids.
    Values are 0 for empty, and integers 1..N for digits.
    """

    def __init__(
        self,
        grid_dim: int = 9,
        box_w: int = 3,
        box_h: int = 3,
        board: Optional[List[List[int]]] = None,
        clues: Optional[Set[Tuple[int, int]]] = None,
    ):
        self.grid_dim = grid_dim
        self.box_w = box_w
        self.box_h = box_h

        if board is not None:
            self.board = [list(row) for row in board]
        else:
            # Default classic 9x9 puzzle or empty board
            if grid_dim == 9 and box_w == 3 and box_h == 3:
                # Classic gentle sample puzzle
                self.board = [
                    [5, 3, 0, 0, 7, 0, 0, 0, 0],
                    [6, 0, 0, 1, 9, 5, 0, 0, 0],
                    [0, 9, 8, 0, 0, 0, 0, 6, 0],
                    [8, 0, 0, 0, 6, 0, 0, 0, 3],
                    [4, 0, 0, 8, 0, 3, 0, 0, 1],
                    [7, 0, 0, 0, 2, 0, 0, 0, 6],
                    [0, 6, 0, 0, 0, 0, 2, 8, 0],
                    [0, 0, 0, 4, 1, 9, 0, 0, 5],
                    [0, 0, 0, 0, 8, 0, 0, 7, 9],
                ]
            else:
                self.board = [[0 for _ in range(grid_dim)] for _ in range(grid_dim)]

        if clues is not None:
            self.clues = set(clues)
        else:
            self.clues = {
                (r, c)
                for r in range(self.grid_dim)
                for c in range(self.grid_dim)
                if self.board[r][c] != 0
            }

    def clone(self) -> "SudokuState":
        return SudokuState(
            self.grid_dim,
            self.box_w,
            self.box_h,
            [list(row) for row in self.board],
            set(self.clues),
        )

    def serialize(self) -> str:
        return json.dumps({
            "puzzle": "sudoku",
            "grid_dim": self.grid_dim,
            "box_w": self.box_w,
            "box_h": self.box_h,
            "board": self.board,
            "clues": sorted(list(self.clues)),
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "SudokuState":
        data = json.loads(raw_data)
        clues_set = {tuple(x) for x in data.get("clues", [])}
        return cls(
            grid_dim=int(data["grid_dim"]),
            box_w=int(data["box_w"]),
            box_h=int(data["box_h"]),
            board=data["board"],
            clues=clues_set,
        )

    def get_all_units(self):
        """Yields coordinate lists for all rows, columns, and sub-boxes."""
        # Rows
        for r in range(self.grid_dim):
            yield [(r, c) for c in range(self.grid_dim)]
        # Columns
        for c in range(self.grid_dim):
            yield [(r, c) for r in range(self.grid_dim)]
        # Sub-boxes
        for br in range(0, self.grid_dim, self.box_h):
            for bc in range(0, self.grid_dim, self.box_w):
                yield [
                    (br + r, bc + c)
                    for r in range(self.box_h)
                    for c in range(self.box_w)
                ]

    def validate(self) -> Tuple[bool, str]:
        if self.grid_dim != self.box_w * self.box_h:
            return (
                False,
                f"Grid dimension ({self.grid_dim}) must equal Box Width x Height ({self.box_w}x{self.box_h}={self.box_w*self.box_h}).",
            )

        if len(self.board) != self.grid_dim or any(len(row) != self.grid_dim for row in self.board):
            return False, f"Board dimensions must strictly be {self.grid_dim}x{self.grid_dim}."

        for unit in self.get_all_units():
            nums = [self.board[r][c] for r, c in unit if self.board[r][c] != 0]
            if any(n < 1 or n > self.grid_dim for n in nums):
                return False, f"Numbers must be between 1 and {self.grid_dim}."
            if len(nums) != len(set(nums)):
                return False, "Duplicate numbers found within a row, column, or sub-box."

        return True, "Valid Sudoku board configuration."
