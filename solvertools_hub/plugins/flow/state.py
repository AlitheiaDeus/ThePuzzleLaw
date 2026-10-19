"""
state.py - Flow Free & Numberlink topological path state model.
Represents an NxN grid with paired colored endpoints, wall barriers, and cell-occupying paths.
"""

import json
from typing import Dict, List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class FlowState(BasePuzzleState):
    """
    Topological path puzzle state.
    grid_size: Dimension N of the NxN grid.
    board: 2D array of color IDs (0 = Empty, 1..K = Path of color K).
    endpoints: Dict mapping color_id -> List of 2 coordinate tuples [(r1, c1), (r2, c2)].
    """

    EMPTY = 0

    COLOR_MINT = 1
    COLOR_LAVENDER = 2
    COLOR_PEACH = 3
    COLOR_SKY = 4
    COLOR_CORAL = 5

    def __init__(
        self,
        grid_size: int = 5,
        board: Optional[List[List[int]]] = None,
        endpoints: Optional[Dict[str, List[List[int]]]] = None,
    ):
        self.grid_size = max(3, min(16, int(grid_size)))
        sz = self.grid_size

        if board is not None:
            self.board = [list(r) for r in board]
        else:
            self.board = [[self.EMPTY for _ in range(sz)] for _ in range(sz)]

        if endpoints is not None:
            self.endpoints = endpoints
        else:
            # Default 5x5 sample endpoints
            self.endpoints = {
                "1": [[0, 0], [4, 4]],  # Mint
                "2": [[0, 4], [4, 0]],  # Lavender
                "3": [[1, 2], [3, 2]],  # Peach
            }
            # Stamp endpoints onto initial board
            for cid_str, pts in self.endpoints.items():
                cid = int(cid_str)
                for r, c in pts:
                    if 0 <= r < sz and 0 <= c < sz:
                        self.board[r][c] = cid

    def clone(self) -> "FlowState":
        return FlowState(
            grid_size=self.grid_size,
            board=[list(r) for r in self.board],
            endpoints={k: [list(pt) for pt in v] for k, v in self.endpoints.items()},
        )

    def serialize(self) -> str:
        return json.dumps({
            "grid_size": self.grid_size,
            "board": self.board,
            "endpoints": self.endpoints,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "FlowState":
        data = json.loads(raw_data)
        return cls(
            grid_size=data["grid_size"],
            board=data["board"],
            endpoints=data["endpoints"],
        )

    def validate(self) -> Tuple[bool, str]:
        sz = self.grid_size
        if len(self.board) != sz or any(len(r) != sz for r in self.board):
            return False, f"Grid dimensions must be {sz}x{sz}"
        for cid_str, pts in self.endpoints.items():
            if len(pts) != 2:
                return False, f"Color {cid_str} must have exactly 2 endpoints"
        return True, ""
