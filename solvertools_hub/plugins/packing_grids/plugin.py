"""
plugin.py - Packing Grids & Nonograms plugin descriptor.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver
from .canvas import PackingGridsCanvas
from .solver import PackingGridsSolver
from .state import PackingGridsState


class PackingGridsPlugin(BasePuzzlePlugin):
    """Plugin descriptor for Packing Grids & Nonograms."""

    name = "Packing Grids"
    category = "Exact Cover & Packing"
    description = (
        "Advanced constraint and exact cover solver for Nonograms (Picross) "
        "and Knuth's Algorithm X (DLX) polyomino tile packings."
    )
    is_wip = True

    def create_default_state(self) -> BasePuzzleState:
        return PackingGridsState(5, 5)

    def create_solver(self) -> BaseSolver:
        return PackingGridsSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, PackingGridsState):
            initial_state = PackingGridsState(5, 5)
        return PackingGridsCanvas(initial_state)
