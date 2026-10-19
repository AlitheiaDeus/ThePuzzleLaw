"""
plugin.py - Maze Navigator plugin descriptor.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver
from .canvas import MazeNavigatorCanvas
from .solver import MazeNavigatorSolver
from .state import MazeNavigatorState


class MazeNavigatorPlugin(BasePuzzlePlugin):
    """Plugin descriptor for Maze Navigator."""

    name = "Maze Navigator"
    category = "Navigators / Geometry"
    description = (
        "Orthogonal 2D grid, hexagonal, and Euclidean geometric maze pathfinding "
        "navigators with live A* and BFS search tree streaming."
    )
    is_wip = True

    def create_default_state(self) -> BasePuzzleState:
        return MazeNavigatorState(9, 9)

    def create_solver(self) -> BaseSolver:
        return MazeNavigatorSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, MazeNavigatorState):
            initial_state = MazeNavigatorState(9, 9)
        return MazeNavigatorCanvas(initial_state)
