"""
state.py - Sliding Tile (N-Puzzle) state representation, serialization, and validation.
"""

import json
from typing import List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class SlidingTileState(BasePuzzleState):
    """
    Represents an N x N sliding tile grid.
    Grid is stored as a 1D list of integers from 0 to N*N - 1, where 0 is the blank tile.
    """

    def __init__(self, size: int = 3, grid: Optional[List[int]] = None):
        self.size = size
        if grid is not None:
            self.grid = list(grid)
        else:
            # Default slightly scrambled solvable 3x3 or solved N x N
            if size == 3:
                self.grid = [1, 2, 3, 4, 5, 6, 0, 7, 8]
            else:
                self.grid = list(range(1, size * size)) + [0]

    def clone(self) -> "SlidingTileState":
        return SlidingTileState(self.size, list(self.grid))

    def serialize(self) -> str:
        return json.dumps({
            "puzzle": "sliding_tile",
            "size": self.size,
            "grid": self.grid,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "SlidingTileState":
        data = json.loads(raw_data)
        if "grid" not in data or "size" not in data:
            raise ValueError("Missing 'size' or 'grid' keys in JSON state.")
        return cls(int(data["size"]), list(data["grid"]))

    def validate(self) -> Tuple[bool, str]:
        expected = set(range(self.size * self.size))
        if set(self.grid) != expected:
            return False, f"Grid must contain exact numbers 0 through {self.size * self.size - 1}."

        # Inversion parity check for solvability
        tiles = [x for x in self.grid if x != 0]
        inversions = sum(
            1 for i in range(len(tiles))
            for j in range(i + 1, len(tiles))
            if tiles[i] > tiles[j]
        )

        if self.size % 2 == 1:
            if inversions % 2 != 0:
                return False, f"Unsolvable configuration: odd inversion count ({inversions}) on {self.size}x{self.size} grid."
        else:
            blank_row_from_bottom = self.size - (self.grid.index(0) // self.size)
            if (blank_row_from_bottom % 2 == 0) == (inversions % 2 == 0):
                return False, "Unsolvable configuration: parity mismatch for even grid."

        return True, "Valid & solvable state."
