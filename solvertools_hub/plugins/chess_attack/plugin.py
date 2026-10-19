"""
plugin.py - Chess Attack & Tactical Zoned Boards plugin descriptor.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver
from .canvas import ChessAttackCanvas
from .solver import ChessAttackSolver
from .state import ChessAttackState


class ChessAttackPlugin(BasePuzzlePlugin):
    """Plugin descriptor for Chess Attack & Tactical Zoned Boards."""

    name = "Chess Attack"
    category = "Tactical / Board"
    description = (
        "Tactical constraint engine for non-attacking chess pieces (Queen, Superking, "
        "Extended King) across arbitrary user-painted territorial zones."
    )
    is_wip = True

    def create_default_state(self) -> BasePuzzleState:
        return ChessAttackState(8)

    def create_solver(self) -> BaseSolver:
        return ChessAttackSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, ChessAttackState):
            initial_state = ChessAttackState(8)
        return ChessAttackCanvas(initial_state)
