"""
state.py - Chess Attack & Tactical Zoned Boards state model.
Represents an NxN board with partitioned territorial zones, piece placements,
and threat maps for Queens, Superkings, and Extended Kings.
"""

import json
from typing import List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class ChessAttackState(BasePuzzleState):
    """
    Chess attack puzzle state.
    board: 2D array where 0 = Empty, 1 = Queen, 2 = Extended King, 3 = Superking
    zones: 2D array assigning each cell (r, c) to a zone index (0 to num_zones-1)
    """

    EMPTY = 0
    PIECE_QUEEN = 1
    PIECE_EXTENDED_KING = 2
    PIECE_SUPERKING = 3

    PIECE_GLYPHS = {
        EMPTY: "",
        PIECE_QUEEN: "♕",
        PIECE_EXTENDED_KING: "♖",
        PIECE_SUPERKING: "♔",
    }

    def __init__(
        self,
        board_size: int = 8,
        board: Optional[List[List[int]]] = None,
        zones: Optional[List[List[int]]] = None,
    ):
        self.board_size = max(4, min(16, int(board_size)))

        if board is not None:
            self.board = [list(r) for r in board]
        else:
            self.board = [[self.EMPTY for _ in range(self.board_size)] for _ in range(self.board_size)]

        if zones is not None:
            self.zones = [list(r) for r in zones]
        else:
            # Default horizontal stripe zones
            self.zones = [[r for _ in range(self.board_size)] for r in range(self.board_size)]

    def clone(self) -> "ChessAttackState":
        return ChessAttackState(
            board_size=self.board_size,
            board=[list(r) for r in self.board],
            zones=[list(r) for r in self.zones],
        )

    def serialize(self) -> str:
        return json.dumps({
            "board_size": self.board_size,
            "board": self.board,
            "zones": self.zones,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "ChessAttackState":
        data = json.loads(raw_data)
        return cls(
            board_size=data["board_size"],
            board=data["board"],
            zones=data["zones"],
        )

    def validate(self) -> Tuple[bool, str]:
        sz = self.board_size
        if len(self.board) != sz or any(len(r) != sz for r in self.board):
            return False, f"Board dimensions must be {sz}x{sz}"
        if len(self.zones) != sz or any(len(r) != sz for r in self.zones):
            return False, f"Zone dimensions must be {sz}x{sz}"
        return True, ""
