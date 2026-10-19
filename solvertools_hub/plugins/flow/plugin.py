"""
plugin.py - Flow Free & Numberlink plugin descriptor.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver
from .canvas import FlowCanvas
from .solver import FlowSolver
from .state import FlowState


class FlowPlugin(BasePuzzlePlugin):
    """Plugin descriptor for Flow Free & Numberlink."""

    name = "Flow Free"
    category = "Paths / Topological"
    description = (
        "Topological path connection and 100% saturation grid solver. Connects matching "
        "color endpoints across the grid without crossing or isolated unvisited cells."
    )
    is_wip = True

    def create_default_state(self) -> BasePuzzleState:
        return FlowState(5)

    def create_solver(self) -> BaseSolver:
        return FlowSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, FlowState):
            initial_state = FlowState(5)
        return FlowCanvas(initial_state)
