"""
state.py - Urjo puzzle state representation, serialization, and constraint validation.
Urjo is played on an N x N even grid with binary color states (Red & Blue),
numerical Moore neighborhood clues (0-8), line balance, and adjacent line disparity.
"""

import json
from typing import List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class UrjoState(BasePuzzleState):
    """
    Represents an N x N Urjo puzzle state (where N is even).

    Cell states:
        0 = Empty / Unfilled
        1 = Red (Vivid Crimson)
        2 = Blue (Cobalt / Cyan)

    Clues:
        None = unnumbered cell
        0..8 = Moore neighborhood clue (number of surrounding cells of the exact same color)
    """

    EMPTY = 0
    COLOR_RED = 1
    COLOR_BLUE = 2

    # Aliases for color pairs
    COLOR_A = 1
    COLOR_B = 2

    def __init__(
        self,
        grid_size: int = 6,
        board: Optional[List[List[int]]] = None,
        clues: Optional[List[List[Optional[int]]]] = None,
        givens: Optional[List[List[bool]]] = None,
    ):
        self.grid_size = grid_size

        if board is not None:
            self.board = [list(r) for r in board]
        else:
            self.board = [[self.EMPTY for _ in range(grid_size)] for _ in range(grid_size)]

        if clues is not None:
            self.clues = [list(r) for r in clues]
        else:
            self.clues = [[None for _ in range(grid_size)] for _ in range(grid_size)]

        if givens is not None:
            self.givens = [list(r) for r in givens]
        else:
            # By default, any non-empty cell or clue cell in the initial setup is a given
            self.givens = [
                [
                    (self.board[r][c] != self.EMPTY or self.clues[r][c] is not None)
                    for c in range(grid_size)
                ]
                for r in range(grid_size)
            ]

        # If clean initialization with no board, populate standard solvable sample
        if board is None and clues is None:
            self._load_default_sample()

    def _load_default_sample(self) -> None:
        """Loads a verified solvable default puzzle for grid_size 4 or 6."""
        sz = self.grid_size
        self.board = [[self.EMPTY for _ in range(sz)] for _ in range(sz)]
        self.clues = [[None for _ in range(sz)] for _ in range(sz)]

        if sz == 4:
            # Solvable 4x4 Urjo puzzle
            # Clues: (0,0)=R(1), (1,1)=R(4), (1,2)=B(4), (3,3)=R(1)
            clue_defs = [
                (0, 0, self.COLOR_RED, 1),
                (1, 1, self.COLOR_RED, 4),
                (1, 2, self.COLOR_BLUE, 4),
                (3, 3, self.COLOR_RED, 1),
            ]
            for r, c, col, k in clue_defs:
                self.board[r][c] = col
                self.clues[r][c] = k
        elif sz == 6:
            # Solvable 6x6 Urjo puzzle
            clue_defs = [
                (0, 0, self.COLOR_RED, 2),
                (0, 4, self.COLOR_BLUE, 3),
                (1, 1, self.COLOR_BLUE, 3),
                (2, 2, self.COLOR_BLUE, 4),
                (2, 3, self.COLOR_RED, 4),
                (3, 2, self.COLOR_RED, 3),
                (3, 3, self.COLOR_BLUE, 4),
                (4, 0, self.COLOR_RED, 1),
                (4, 4, self.COLOR_BLUE, 3),
                (5, 5, self.COLOR_BLUE, 1),
            ]
            for r, c, col, k in clue_defs:
                self.board[r][c] = col
                self.clues[r][c] = k

        self.givens = [
            [
                (self.board[r][c] != self.EMPTY or self.clues[r][c] is not None)
                for c in range(sz)
            ]
            for r in range(sz)
        ]

    def clone(self) -> "UrjoState":
        return UrjoState(
            grid_size=self.grid_size,
            board=[list(r) for r in self.board],
            clues=[list(r) for r in self.clues],
            givens=[list(r) for r in self.givens],
        )

    def serialize(self) -> str:
        return json.dumps({
            "puzzle": "urjo",
            "grid_size": self.grid_size,
            "board": self.board,
            "clues": self.clues,
            "givens": self.givens,
        }, sort_keys=True)

    @classmethod
    def deserialize(cls, raw_data: str) -> "UrjoState":
        data = json.loads(raw_data)
        return cls(
            grid_size=int(data["grid_size"]),
            board=data["board"],
            clues=data.get("clues"),
            givens=data.get("givens"),
        )

    def get_neighbors(self, r: int, c: int) -> List[Tuple[int, int]]:
        """Returns valid coordinates in the 8-cell Moore neighborhood."""
        neighbors = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.grid_size and 0 <= nc < self.grid_size:
                    neighbors.append((nr, nc))
        return neighbors

    def is_line_valid(self, line: List[int]) -> bool:
        """
        Validates line balance quota.
        Each color cannot exceed N / 2.
        (Note: 3-in-a-row IS allowed in Urjo).
        """
        half = self.grid_size // 2
        return (
            line.count(self.COLOR_RED) <= half
            and line.count(self.COLOR_BLUE) <= half
        )

    def validate(self) -> Tuple[bool, str]:
        """
        Validates whether the current state configuration is legal and constraint-adherent.
        Returns: (is_valid, message)
        """
        if self.grid_size < 2 or self.grid_size % 2 != 0:
            return False, f"Grid size ({self.grid_size}) must be an even integer >= 2."

        if len(self.board) != self.grid_size or any(len(row) != self.grid_size for row in self.board):
            return False, f"Board dimensions must strictly be {self.grid_size}x{self.grid_size}."

        half = self.grid_size // 2

        # 1. Line balance validation (rows and columns)
        for r, row in enumerate(self.board):
            if not self.is_line_valid(row):
                return False, f"Row #{r + 1} exceeds maximum color capacity ({half})."

        for c in range(self.grid_size):
            col = [self.board[r][c] for r in range(self.grid_size)]
            if not self.is_line_valid(col):
                return False, f"Column #{c + 1} exceeds maximum color capacity ({half})."

        # 2. Adjacent line uniqueness (if both lines are fully filled)
        for r in range(self.grid_size - 1):
            row1, row2 = self.board[r], self.board[r + 1]
            if self.EMPTY not in row1 and self.EMPTY not in row2:
                if row1 == row2:
                    return False, f"Adjacent rows {r + 1} and {r + 2} are identical."

        for c in range(self.grid_size - 1):
            col1 = [self.board[r][c] for r in range(self.grid_size)]
            col2 = [self.board[r][c + 1] for r in range(self.grid_size)]
            if self.EMPTY not in col1 and self.EMPTY not in col2:
                if col1 == col2:
                    return False, f"Adjacent columns {c + 1} and {c + 2} are identical."

        # 3. Neighborhood clue validity
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                k = self.clues[r][c]
                if k is None:
                    continue

                neighbors = self.get_neighbors(r, c)
                max_k = len(neighbors)
                if not (0 <= k <= max_k):
                    return False, f"Clue at ({r + 1}, {c + 1}) is {k}, which exceeds neighbor count {max_k}."

                color = self.board[r][c]
                if color != self.EMPTY:
                    matching = sum(1 for nr, nc in neighbors if self.board[nr][nc] == color)
                    empty = sum(1 for nr, nc in neighbors if self.board[nr][nc] == self.EMPTY)
                    if matching > k:
                        return False, f"Clue at ({r + 1}, {c + 1}) exceeded: requires {k}, already has {matching} matching."
                    if matching + empty < k:
                        return False, f"Clue at ({r + 1}, {c + 1}) cannot be satisfied: max possible is {matching + empty} < {k}."

        return True, "Valid Urjo puzzle configuration."

    def is_solved(self) -> bool:
        """Returns True if the board is completely filled and satisfies all Urjo constraints."""
        # 1. No empty cells
        if any(self.EMPTY in row for row in self.board):
            return False

        half = self.grid_size // 2

        # 2. Exact balance per row and column
        for row in self.board:
            if row.count(self.COLOR_RED) != half or row.count(self.COLOR_BLUE) != half:
                return False

        for c in range(self.grid_size):
            col = [self.board[r][c] for r in range(self.grid_size)]
            if col.count(self.COLOR_RED) != half or col.count(self.COLOR_BLUE) != half:
                return False

        # 3. Adjacent lines must not be identical
        for r in range(self.grid_size - 1):
            if self.board[r] == self.board[r + 1]:
                return False

        for c in range(self.grid_size - 1):
            col1 = [self.board[r][c] for r in range(self.grid_size)]
            col2 = [self.board[r][c + 1] for r in range(self.grid_size)]
            if col1 == col2:
                return False

        # 4. Clue satisfaction
        for r in range(self.grid_size):
            for c in range(self.grid_size):
                k = self.clues[r][c]
                if k is None:
                    continue
                color = self.board[r][c]
                matching = sum(1 for nr, nc in self.get_neighbors(r, c) if self.board[nr][nc] == color)
                if matching != k:
                    return False

        return True
