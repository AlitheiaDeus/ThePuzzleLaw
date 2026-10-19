"""
plugin.py - Sudoku plugin descriptor for solvertools_hub.
"""

from typing import Optional

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver, InteractionMode
from .canvas import SudokuCanvas
from .solver import SudokuSolver
from .state import SudokuState


class SudokuPlugin(BasePuzzlePlugin):
    """Sudoku puzzle plugin supporting arbitrary grids and hybrid deduction/backtracking."""
    name = "Sudoku (Constraint Grid)"
    category = "Grid / Constraints"
    description = "Click cells to focus and type digits 1-9 (or 0/Backspace to clear). Solves via Naked/Hidden Singles logic and MRV backtracking."

    def create_default_state(self) -> BasePuzzleState:
        return SudokuState(9, 3, 3)

    def create_solver(self) -> BaseSolver:
        return SudokuSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, SudokuState):
            initial_state = SudokuState(9, 3, 3)
        return SudokuCanvas(initial_state)

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        if not isinstance(canvas, SudokuCanvas):
            return None

        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Preset:"))
        combo = QComboBox()
        combo.addItems([
            "Classic 9x9 (3x3)",
            "Mini 4x4 (2x2)",
            "6x6 (3x2)",
        ])

        def _on_preset_changed(idx: int):
            if canvas.mode != InteractionMode.EDIT:
                return
            if idx == 0:
                canvas.state = SudokuState(9, 3, 3)
            elif idx == 1:
                sample_4x4 = [
                    [1, 0, 0, 0],
                    [0, 0, 2, 0],
                    [0, 3, 0, 0],
                    [0, 0, 0, 4],
                ]
                canvas.state = SudokuState(4, 2, 2, sample_4x4)
            elif idx == 2:
                canvas.state = SudokuState(6, 3, 2)
            canvas.selected_cell = (0, 0)
            canvas.current_step = None
            canvas.state_modified.emit()
            canvas.update()

        combo.currentIndexChanged.connect(_on_preset_changed)
        layout.addWidget(combo)

        btn_sample = QPushButton("Load Classic Sample")
        def _load_sample():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state = SudokuState(9, 3, 3)
                canvas.current_step = None
                canvas.state_modified.emit()
                canvas.update()
        btn_sample.clicked.connect(_load_sample)
        layout.addWidget(btn_sample)

        btn_clear = QPushButton("Clear Board")
        def _clear_board():
            if canvas.mode == InteractionMode.EDIT:
                dim = canvas.state.grid_dim
                bw = canvas.state.box_w
                bh = canvas.state.box_h
                canvas.state = SudokuState(dim, bw, bh, [[0] * dim for _ in range(dim)], set())
                canvas.current_step = None
                canvas.state_modified.emit()
                canvas.update()
        btn_clear.clicked.connect(_clear_board)
        layout.addWidget(btn_clear)

        layout.addStretch()
        return strip
