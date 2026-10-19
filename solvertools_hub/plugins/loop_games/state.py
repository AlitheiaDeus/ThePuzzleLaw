"""
state.py - Loop Family (Slitherlink / Palisade / Pearl) state model.
Represents a lattice grid of vertices, numerical cell clues (0-3), and horizontal/vertical loop edges.
"""

import json
from typing import List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class LoopFamilyState(BasePuzzleState):
    """
    Loop puzzle state (Slitherlink lattice).
    size: Dimension N of the NxN cell grid (vertices are (N+1)x(N+1)).
    cell_clues: 2D array of Optional[int] with numbers 0, 1, 2, 3 or None.
    h_edges: (N+1) x N array of integers (0 = None, 1 = Line, -1 = Cross/X).
    v_edges: N x (N+1) array of integers (0 = None, 1 = Line, -1 = Cross/X).
    """

    EDGE_NONE = 0
    EDGE_LINE = 1
    EDGE_CROSS = -1

    def __init__(
        self,
        size: int = 5,
        cell_clues: Optional[List[List[Optional[int]]]] = None,
        h_edges: Optional[List[List[int]]] = None,
        v_edges: Optional[List[List[int]]] = None,
    ):
        self.size = max(3, min(15, int(size)))
        sz = self.size

        if cell_clues is not None:
            self.cell_clues = [list(r) for r in cell_clues]
        else:
            self.cell_clues = [[None for _ in range(sz)] for _ in range(sz)]
            # Sample Slitherlink clues
            self.cell_clues[0][1] = 3
            self.cell_clues[1][1] = 2
            self.cell_clues[2][2] = 3
            self.cell_clues[3][3] = 1

        if h_edges is not None:
            self.h_edges = [list(r) for r in h_edges]
        else:
            self.h_edges = [[self.EDGE_NONE for _ in range(sz)] for _ in range(sz + 1)]

        if v_edges is not None:
            self.v_edges = [list(r) for r in v_edges]
        else:
            self.v_edges = [[self.EDGE_NONE for _ in range(sz + 1)] for _ in range(sz)]

    def clone(self) -> "LoopFamilyState":
        return LoopFamilyState(
            size=self.size,
            cell_clues=[list(r) for r in self.cell_clues],
            h_edges=[list(r) for r in self.h_edges],
            v_edges=[list(r) for r in self.v_edges],
        )

    def serialize(self) -> str:
        return json.dumps({
            "size": self.size,
            "cell_clues": self.cell_clues,
            "h_edges": self.h_edges,
            "v_edges": self.v_edges,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "LoopFamilyState":
        data = json.loads(raw_data)
        return cls(
            size=data["size"],
            cell_clues=data["cell_clues"],
            h_edges=data["h_edges"],
            v_edges=data["v_edges"],
        )

    def validate(self) -> Tuple[bool, str]:
        sz = self.size
        if len(self.cell_clues) != sz or any(len(r) != sz for r in self.cell_clues):
            return False, f"Cell clues must be {sz}x{sz}"
        if len(self.h_edges) != sz + 1 or any(len(r) != sz for r in self.h_edges):
            return False, f"Horizontal edges must be {sz+1}x{sz}"
        if len(self.v_edges) != sz or any(len(r) != sz + 1 for r in self.v_edges):
            return False, f"Vertical edges must be {sz}x{sz+1}"
        return True, ""
