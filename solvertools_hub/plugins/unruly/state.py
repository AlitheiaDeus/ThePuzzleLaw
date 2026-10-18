"""
state.py - Unruly (Binary Puzzle) state representation, serialization, and validation.
Supports even grid sizes, three cell states (Empty, Color A, Color B), and edge constraints.
"""

import json
from typing import Dict, List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class UnrulyState(BasePuzzleState):
    """
    Represents an N x N Unruly binary puzzle grid (N is even).
    0 = Empty
    1 = Color A (Pastel Sky)
    2 = Color B (Pastel Peach)
    """
    EMPTY = 0
    COLOR_A = 1
    COLOR_B = 2

    def __init__(
        self,
        grid_size: int = 6,
        board: Optional[List[List[int]]] = None,
        edge_constraints: Optional[Dict[str, str]] = None,
        unique_rows_cols: bool = True,
    ):
        self.grid_size = grid_size
        self.unique_rows_cols = unique_rows_cols

        if board is not None:
            self.board = [list(r) for r in board]
        else:
            # Solvable default starting level (6x6)
            self.board = [[self.EMPTY for _ in range(grid_size)] for _ in range(grid_size)]
            if grid_size == 6:
                # Classic gentle 6x6 sample
                self.board[0][1] = self.COLOR_A
                self.board[0][3] = self.COLOR_A
                self.board[1][4] = self.COLOR_B
                self.board[2][1] = self.COLOR_B
                self.board[3][2] = self.COLOR_A
                self.board[4][0] = self.COLOR_B
                self.board[5][5] = self.COLOR_A

        # Edge constraints stored as string key "r1,c1-r2,c2" -> "equal" or "opposite"
        self.edge_constraints: Dict[str, str] = dict(edge_constraints or {})

    def clone(self) -> "UnrulyState":
        return UnrulyState(
            self.grid_size,
            [list(r) for r in self.board],
            dict(self.edge_constraints),
            self.unique_rows_cols,
        )

    def serialize(self) -> str:
        return json.dumps({
            "puzzle": "unruly",
            "grid_size": self.grid_size,
            "board": self.board,
            "edge_constraints": self.edge_constraints,
            "unique_rows_cols": self.unique_rows_cols,
        }, sort_keys=True)

    @classmethod
    def deserialize(cls, raw_data: str) -> "UnrulyState":
        data = json.loads(raw_data)
        return cls(
            grid_size=int(data["grid_size"]),
            board=data["board"],
            edge_constraints=data.get("edge_constraints", {}),
            unique_rows_cols=bool(data.get("unique_rows_cols", True)),
        )

    def is_line_valid(self, line: List[int]) -> bool:
        # Check no three consecutive identical colors
        for i in range(len(line) - 2):
            if line[i] != self.EMPTY and line[i] == line[i + 1] == line[i + 2]:
                return False
        # Check balance count
        half = self.grid_size // 2
        if line.count(self.COLOR_A) > half or line.count(self.COLOR_B) > half:
            return False
        return True

    def validate(self) -> Tuple[bool, str]:
        if self.grid_size < 2 or self.grid_size % 2 != 0:
            return False, f"Grid size ({self.grid_size}) must be an even number >= 2."

        if len(self.board) != self.grid_size or any(len(row) != self.grid_size for row in self.board):
            return False, f"Board must strictly be {self.grid_size}x{self.grid_size}."

        # Check rows
        for r, row in enumerate(self.board):
            if not self.is_line_valid(row):
                return False, f"Row #{r + 1} violates no-three-in-a-row or color balance."

        # Check columns
        for c in range(self.grid_size):
            col = [self.board[r][c] for r in range(self.grid_size)]
            if not self.is_line_valid(col):
                return False, f"Column #{c + 1} violates no-three-in-a-row or color balance."

        # Check edge constraints
        for key, constraint in self.edge_constraints.items():
            try:
                p1, p2 = key.split("-")
                r1, c1 = map(int, p1.split(","))
                r2, c2 = map(int, p2.split(","))
                v1, v2 = self.board[r1][c1], self.board[r2][c2]
                if v1 != self.EMPTY and v2 != self.EMPTY:
                    if constraint == "equal" and v1 != v2:
                        return False, f"Edge constraint Equal violated between ({r1+1},{c1+1}) and ({r2+1},{c2+1})."
                    elif constraint == "opposite" and v1 == v2:
                        return False, f"Edge constraint Opposite violated between ({r1+1},{c1+1}) and ({r2+1},{c2+1})."
            except Exception:
                pass

        return True, "Valid Unruly puzzle configuration."

    def is_solved(self) -> bool:
        """All cells filled and legal."""
        if any(self.EMPTY in row for row in self.board):
            return False
        is_ok, _ = self.validate()
        return is_ok
