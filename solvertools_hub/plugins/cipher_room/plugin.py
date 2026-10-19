"""
plugin.py - The Cipher Room cryptanalysis plugin descriptor.
"""

from typing import Optional
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver
from .canvas import CipherRoomCanvas
from .solver import CipherRoomSolver
from .state import CipherRoomState


class CipherRoomPlugin(BasePuzzlePlugin):
    """Plugin descriptor for The Cipher Room."""

    name = "The Cipher Room"
    category = "Crypt & Signal"
    description = (
        "Cryptanalysis suite featuring unspaced Morse beam-search, classical ciphers "
        "(Caesar/ROT, Substitution), frequency analysis, and ARG transformations."
    )
    is_wip = True

    def create_default_state(self) -> BasePuzzleState:
        return CipherRoomState("...---...", "morse")

    def create_solver(self) -> BaseSolver:
        return CipherRoomSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, CipherRoomState):
            initial_state = CipherRoomState("...---...", "morse")
        return CipherRoomCanvas(initial_state)
