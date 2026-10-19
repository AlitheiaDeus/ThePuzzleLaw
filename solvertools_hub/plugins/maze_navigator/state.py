"""
state.py - Maze Navigator state representation.
Supports 2D orthogonal grid mazes, wall barriers, and customizable Start/Goal endpoints.
"""

import json
from typing import List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class MazeNavigatorState(BasePuzzleState):
    """
    Maze Navigator puzzle state.
    rows, cols: Dimensions of the grid maze.
    walls: 2D boolean array where True = Wall, False = Open.
    start: [r, c] coordinate of the starting node.
    goal: [r, c] coordinate of the goal node.
    """

    def __init__(
        self,
        rows: int = 9,
        cols: int = 9,
        walls: Optional[List[List[bool]]] = None,
        start: Optional[List[int]] = None,
        goal: Optional[List[int]] = None,
    ):
        self.rows = max(5, min(31, int(rows)))
        self.cols = max(5, min(31, int(cols)))

        if walls is not None:
            self.walls = [list(r) for r in walls]
        else:
            self.walls = [[False for _ in range(self.cols)] for _ in range(self.rows)]
            # Add some sample interior barrier walls
            for c in range(1, self.cols - 1):
                self.walls[self.rows // 2][c] = (c % 2 == 0)

        self.start = list(start) if start is not None else [0, 0]
        self.goal = list(goal) if goal is not None else [self.rows - 1, self.cols - 1]

    def clone(self) -> "MazeNavigatorState":
        return MazeNavigatorState(
            rows=self.rows,
            cols=self.cols,
            walls=[list(r) for r in self.walls],
            start=list(self.start),
            goal=list(self.goal),
        )

    def serialize(self) -> str:
        return json.dumps({
            "rows": self.rows,
            "cols": self.cols,
            "walls": self.walls,
            "start": self.start,
            "goal": self.goal,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "MazeNavigatorState":
        data = json.loads(raw_data)
        return cls(
            rows=data["rows"],
            cols=data["cols"],
            walls=data["walls"],
            start=data["start"],
            goal=data["goal"],
        )

    def validate(self) -> Tuple[bool, str]:
        if len(self.walls) != self.rows or any(len(r) != self.cols for r in self.walls):
            return False, f"Wall dimensions must match {self.rows}x{self.cols}"
        sr, sc = self.start
        gr, gc = self.goal
        if not (0 <= sr < self.rows and 0 <= sc < self.cols):
            return False, f"Start node {self.start} is out of bounds"
        if not (0 <= gr < self.rows and 0 <= gc < self.cols):
            return False, f"Goal node {self.goal} is out of bounds"
        if self.walls[sr][sc]:
            return False, "Start node cannot be inside a wall"
        if self.walls[gr][gc]:
            return False, "Goal node cannot be inside a wall"
        return True, ""
