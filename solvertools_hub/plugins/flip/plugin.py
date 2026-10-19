"""
plugin.py - Flip / Lights Out plugin descriptor for solvertools_hub.
"""

import random
from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSpinBox, QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver, InteractionMode
from .canvas import FlipCanvas
from .solver import FlipSolver
from .state import FlipState


class FlipPlugin(BasePuzzlePlugin):
    """Flip / Lights Out puzzle plugin using GF(2) linear algebra solver."""
    name = "Flip (Lights Out)"
    category = "Matrix / GF(2)"
    description = "Left-Click toggles individual light state (for 1:1 screen matching); Right-Click simulates game press with 4-neighbor cascade."

    def create_default_state(self) -> BasePuzzleState:
        return FlipState(5, 5)

    def create_solver(self) -> BaseSolver:
        return FlipSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, FlipState):
            initial_state = FlipState(5, 5)
        return FlipCanvas(initial_state)

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        if not isinstance(canvas, FlipCanvas):
            return None

        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Grid:"))
        row_spin = QSpinBox()
        row_spin.setRange(2, 10)
        row_spin.setValue(canvas.state.rows)

        col_spin = QSpinBox()
        col_spin.setRange(2, 10)
        col_spin.setValue(canvas.state.cols)

        def _update_dims():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state = FlipState(row_spin.value(), col_spin.value())
                canvas.current_step = None
                canvas.state_modified.emit()
                canvas.update()

        row_spin.valueChanged.connect(lambda: _update_dims())
        col_spin.valueChanged.connect(lambda: _update_dims())

        layout.addWidget(row_spin)
        layout.addWidget(QLabel("×"))
        layout.addWidget(col_spin)

        btn_random = QPushButton("Random Solvable State")
        def _randomize():
            if canvas.mode == InteractionMode.EDIT:
                # Start from all off and simulate random presses to guarantee solvability
                canvas.state = FlipState(row_spin.value(), col_spin.value(), [[0] * col_spin.value() for _ in range(row_spin.value())])
                press_count = random.randint(3, row_spin.value() * col_spin.value() // 2)
                for _ in range(press_count):
                    rr = random.randint(0, row_spin.value() - 1)
                    cc = random.randint(0, col_spin.value() - 1)
                    canvas.state.toggle_cell_and_neighbors(rr, cc)
                canvas.current_step = None
                canvas.state_modified.emit()
                canvas.update()

        btn_random.clicked.connect(_randomize)
        layout.addWidget(btn_random)

        btn_all_off = QPushButton("All Off")
        def _clear_all():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state.grid = [[0] * canvas.state.cols for _ in range(canvas.state.rows)]
                canvas.current_step = None
                canvas.state_modified.emit()
                canvas.update()

        btn_all_off.clicked.connect(_clear_all)
        layout.addWidget(btn_all_off)

        layout.addStretch()
        return strip
