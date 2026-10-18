"""
plugin.py - Unruly (Binary Puzzle) plugin descriptor for solvertools_hub.
"""

from typing import Optional

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver, InteractionMode
from ...theme import ChalkTheme
from .canvas import UnrulyCanvas
from .solver import UnrulySolver
from .state import UnrulyState


class UnrulyPlugin(BasePuzzlePlugin):
    """Unruly binary puzzle plugin with deduction rules and backtracking."""
    name = "Unruly (Binary Puzzle)"
    category = "Grid / Binary"
    description = "Color each cell Pastel Sky or Pastel Peach. No 3 consecutive same colors, equal colors per line, and optional edge constraints."

    def create_default_state(self) -> BasePuzzleState:
        return UnrulyState(6)

    def create_solver(self) -> BaseSolver:
        return UnrulySolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, UnrulyState):
            initial_state = UnrulyState(6)
        return UnrulyCanvas(initial_state)

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        if not isinstance(canvas, UnrulyCanvas):
            return None

        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Grid Size:"))
        size_combo = QComboBox()
        size_combo.addItems(["6×6", "8×8", "10×10"])

        def _on_size_changed(idx: int):
            if canvas.mode == InteractionMode.EDIT:
                sz = [6, 8, 10][idx]
                canvas.state = UnrulyState(sz, [[0] * sz for _ in range(sz)])
                canvas.state_modified.emit()
                canvas.update()

        size_combo.currentIndexChanged.connect(_on_size_changed)
        layout.addWidget(size_combo)

        layout.addWidget(QLabel("Tool:"))
        btn_paint = QPushButton("■ Paint Cells")
        btn_equal = QPushButton("= Edge Equal")
        btn_opp = QPushButton("× Edge Opposite")

        def _set_tool(tool: str):
            canvas.edit_tool = tool
            btn_paint.setStyleSheet("border: 1px solid #00F5D4;" if tool == "paint" else "")
            btn_equal.setStyleSheet("border: 1px solid #00F5D4;" if tool == "edge_equal" else "")
            btn_opp.setStyleSheet("border: 1px solid #00F5D4;" if tool == "edge_opposite" else "")

        btn_paint.clicked.connect(lambda: _set_tool("paint"))
        btn_equal.clicked.connect(lambda: _set_tool("edge_equal"))
        btn_opp.clicked.connect(lambda: _set_tool("edge_opposite"))
        _set_tool("paint")

        layout.addWidget(btn_paint)
        layout.addWidget(btn_equal)
        layout.addWidget(btn_opp)

        btn_sample = QPushButton("Sample 6×6")
        def _load_sample():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state = UnrulyState(6)
                canvas.state_modified.emit()
                canvas.update()
        btn_sample.clicked.connect(_load_sample)
        layout.addWidget(btn_sample)

        btn_clear = QPushButton("Clear Board")
        def _clear():
            if canvas.mode == InteractionMode.EDIT:
                sz = canvas.state.grid_size
                canvas.state = UnrulyState(sz, [[0] * sz for _ in range(sz)])
                canvas.state_modified.emit()
                canvas.update()
        btn_clear.clicked.connect(_clear)
        layout.addWidget(btn_clear)

        layout.addStretch()
        return strip
