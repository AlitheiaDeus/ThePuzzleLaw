"""
plugin.py - Loop Family (Slitherlink / Palisade / Pearl) plugin descriptor.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver
from .canvas import LoopFamilyCanvas
from .solver import LoopFamilySolver
from .state import LoopFamilyState


class LoopFamilyPlugin(BasePuzzlePlugin):
    """Plugin descriptor for Loop Family (Slitherlink, Palisade, Pearl)."""

    name = "Loop Family"
    category = "Loops & Boundaries"
    description = (
        "Single-loop and boundary partition solver family. Form closed non-intersecting "
        "loops around numeric vertex constraints in Slitherlink, Palisade, and Masyu Pearl."
    )
    is_wip = True

    def create_default_state(self) -> BasePuzzleState:
        return LoopFamilyState(5)

    def create_solver(self) -> BaseSolver:
        return LoopFamilySolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, LoopFamilyState):
            initial_state = LoopFamilyState(5)
        return LoopFamilyCanvas(initial_state)
