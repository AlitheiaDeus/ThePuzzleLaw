"""
state.py - Pure serializable state model for the Flood (Flood-It) puzzle.
Tracks an n x m grid with C distinct colors, anchor at (0, 0), and connected flooded regions.
"""

import json
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Set, Tuple

from ...core.base_plugin import BasePuzzleState
from ...theme import ChalkTheme


@dataclass
class FloodState(BasePuzzleState):
    """
    Represents an n x m Flood-It grid.
    Anchor is always (0, 0).
    Colors are integers in range [0, num_colors - 1].
    """

    rows: int = 12
    cols: int = 12
    num_colors: int = 6
    grid: List[List[int]] = field(default_factory=list)

    # Standard palette colors mapping to ChalkTheme tokens
    COLOR_NAMES = [
        "Orange", "Red", "Green", "Yellow", "Blue", "Purple", "Magenta", "Cyan"
    ]
    COLOR_HEXES = [
        "#FA8231",  # 0: Vibrant Tangerine Orange
        "#FF4757",  # 1: Vivid Crimson Red
        "#2ED573",  # 2: Neon Emerald Green
        "#FED330",  # 3: Sunny Sunflower Yellow
        "#3867D6",  # 4: Royal Cobalt Blue
        "#8854D0",  # 5: Electric Purple
        "#FF3385",  # 6: Hot Magenta Pink
        "#00D2D3",  # 7: Bright Electric Cyan
    ]

    def __post_init__(self):
        if not self.grid:
            self.grid = [[0 for _ in range(self.cols)] for _ in range(self.rows)]

    def clone(self) -> "FloodState":
        """Produces a deep copy of the state."""
        return FloodState(
            rows=self.rows,
            cols=self.cols,
            num_colors=self.num_colors,
            grid=[row[:] for row in self.grid],
        )

    def serialize(self) -> str:
        """Exports state to a standardized JSON string."""
        return json.dumps({
            "rows": self.rows,
            "cols": self.cols,
            "num_colors": self.num_colors,
            "grid": self.grid,
        }, separators=(",", ":"))

    @classmethod
    def deserialize(cls, raw_data: str) -> "FloodState":
        """Parses an exported state string into a concrete FloodState instance."""
        data = json.loads(raw_data)
        return cls(
            rows=int(data.get("rows", 12)),
            cols=int(data.get("cols", 12)),
            num_colors=int(data.get("num_colors", 6)),
            grid=data.get("grid", []),
        )

    def validate(self) -> Tuple[bool, str]:
        """Validates whether the grid dimensions and cell colors are legal."""
        if self.rows < 2 or self.cols < 2:
            return False, f"Grid dimensions ({self.rows}x{self.cols}) must be at least 2x2."
        if self.num_colors < 2 or self.num_colors > len(self.COLOR_HEXES):
            return False, f"Number of colors ({self.num_colors}) must be between 2 and {len(self.COLOR_HEXES)}."
        if len(self.grid) != self.rows:
            return False, f"Expected {self.rows} rows, found {len(self.grid)}."
        for r_idx, row in enumerate(self.grid):
            if len(row) != self.cols:
                return False, f"Row {r_idx} has length {len(row)}, expected {self.cols}."
            for c_idx, val in enumerate(row):
                if not isinstance(val, int) or val < 0 or val >= self.num_colors:
                    return False, f"Cell ({r_idx}, {c_idx}) has invalid color {val} (must be 0..{self.num_colors - 1})."
        return True, "Valid Flood grid."

    def get_color_hex(self, color_idx: int) -> str:
        """Returns the hex color code for a color index."""
        if 0 <= color_idx < len(self.COLOR_HEXES):
            return self.COLOR_HEXES[color_idx]
        return ChalkTheme.get_color(color_idx)

    def get_color_name(self, color_idx: int) -> str:
        """Returns the human-readable name of the color."""
        if 0 <= color_idx < len(self.COLOR_NAMES):
            return self.COLOR_NAMES[color_idx]
        return f"Color {color_idx}"

    @property
    def anchor_color(self) -> int:
        """Returns the current color of the anchor at (0, 0)."""
        if self.grid and self.grid[0]:
            return self.grid[0][0]
        return 0

    def get_flooded_region(self) -> Set[Tuple[int, int]]:
        """
        Computes all cells currently connected to (0, 0) sharing the anchor's color.
        In Flood-It, this represents the entire active player-controlled territory.
        """
        if not self.grid or not self.grid[0]:
            return set()

        target_color = self.grid[0][0]
        flooded: Set[Tuple[int, int]] = set()
        queue = deque([(0, 0)])
        flooded.add((0, 0))

        while queue:
            r, c = queue.popleft()
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if (nr, nc) not in flooded and self.grid[nr][nc] == target_color:
                        flooded.add((nr, nc))
                        queue.append((nr, nc))

        return flooded

    def get_boundary_cells(self) -> Set[Tuple[int, int]]:
        """Returns unflooded cells orthogonally adjacent to the flooded region."""
        flooded = self.get_flooded_region()
        boundary: Set[Tuple[int, int]] = set()
        for r, c in flooded:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.rows and 0 <= nc < self.cols:
                    if (nr, nc) not in flooded:
                        boundary.add((nr, nc))
        return boundary

    def get_adjacent_colors(self) -> Set[int]:
        """Returns the set of colors present on the immediate boundary of the flooded region."""
        boundary = self.get_boundary_cells()
        return {self.grid[r][c] for r, c in boundary}

    def is_solved(self) -> bool:
        """Returns True if the entire grid is uniform (100% captured by the anchor)."""
        return len(self.get_flooded_region()) == (self.rows * self.cols)

    def apply_move(self, new_color: int) -> "FloodState":
        """
        Applies a flood move: changes every cell in the current flooded region
        to new_color, returning the resulting state.
        """
        next_state = self.clone()
        flooded = self.get_flooded_region()
        for r, c in flooded:
            next_state.grid[r][c] = new_color
        return next_state
