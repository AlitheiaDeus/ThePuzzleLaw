"""
plugin.py - Urjo puzzle plugin descriptor and interactive tool strip for solvertools_hub.
"""

from typing import Optional

from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QPushButton, QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver, InteractionMode
from ...theme import ChalkTheme
from .canvas import UrjoCanvas
from .solver import UrjoSolver
from .state import UrjoState


class UrjoPlugin(BasePuzzlePlugin):
    """Urjo binary puzzle plugin with neighborhood clues, line balance, and adjacent disparity."""

    name = "Urjo"
    category = "Grid / Binary"
    description = (
        "Color every spot Blue or Red. Each row and column must contain equal colors. "
        "No two adjacent rows or columns may be identical. Numbers indicate how many "
        "surrounding cells share the same color as that spot."
    )

    def create_default_state(self) -> BasePuzzleState:
        return UrjoState(6)

    def create_solver(self) -> BaseSolver:
        return UrjoSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, UrjoState):
            initial_state = UrjoState(6)
        return UrjoCanvas(initial_state)

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        if not isinstance(canvas, UrjoCanvas):
            return None

        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # 1. Grid Size Selector
        layout.addWidget(QLabel("Size:"))
        size_combo = QComboBox()
        size_combo.addItems(["4×4", "6×6", "8×8"])
        size_combo.setCurrentIndex(1)  # Default 6x6

        def _on_size_changed(idx: int):
            if canvas.mode == InteractionMode.EDIT:
                sz = [4, 6, 8][idx]
                canvas.state = UrjoState(sz)
                canvas.current_step = None
                canvas.selected_cell = (0, 0)
                canvas.state_modified.emit()
                canvas.update()

        size_combo.currentIndexChanged.connect(_on_size_changed)
        layout.addWidget(size_combo)

        # 2. Paint & Clue Tools
        layout.addWidget(QLabel("Tool:"))
        btn_cycle = QPushButton("🔄 Cycle")
        btn_cycle.setToolTip("Left-Click: Blank → Blue → Red\nRight-Click: Blank → Red → Blue\n(Space / Shift+Space)")

        btn_blue = QPushButton("🔵 Blue")
        btn_blue.setToolTip("Left-Click: Set Blue\nRight-Click: Clear cell\n(Key: B)")

        btn_red = QPushButton("🔴 Red")
        btn_red.setToolTip("Left-Click: Set Red\nRight-Click: Clear cell\n(Key: R)")

        btn_clue = QPushButton("🔢 Clue")
        btn_clue.setToolTip("Left-Click: +1 clue count\nRight-Click: -1 clue count\n(Or type digits 0-8, Delete to clear)")

        tool_buttons = {
            "cycle": btn_cycle,
            "blue": btn_blue,
            "red": btn_red,
            "clue": btn_clue,
        }

        def _set_tool(tool_name: str):
            canvas.edit_tool = tool_name
            for name, btn in tool_buttons.items():
                if name == tool_name:
                    btn.setStyleSheet(f"border: 1.5px solid {ChalkTheme.NEON_CYAN}; font-weight: bold;")
                else:
                    btn.setStyleSheet("")

        btn_cycle.clicked.connect(lambda: _set_tool("cycle"))
        btn_blue.clicked.connect(lambda: _set_tool("blue"))
        btn_red.clicked.connect(lambda: _set_tool("red"))
        btn_clue.clicked.connect(lambda: _set_tool("clue"))
        _set_tool("cycle")

        layout.addWidget(btn_cycle)
        layout.addWidget(btn_blue)
        layout.addWidget(btn_red)
        layout.addWidget(btn_clue)

        # 3. Solvable Presets
        btn_sample6 = QPushButton("Sample 6×6")
        def _load_sample6():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state = UrjoState(6)
                canvas.current_step = None
                size_combo.setCurrentIndex(1)
                canvas.selected_cell = (0, 0)
                canvas.state_modified.emit()
                canvas.update()
        btn_sample6.clicked.connect(_load_sample6)
        layout.addWidget(btn_sample6)

        btn_sample4 = QPushButton("Sample 4×4")
        def _load_sample4():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state = UrjoState(4)
                canvas.current_step = None
                size_combo.setCurrentIndex(0)
                canvas.selected_cell = (0, 0)
                canvas.state_modified.emit()
                canvas.update()
        btn_sample4.clicked.connect(_load_sample4)
        layout.addWidget(btn_sample4)

        # 4. Clear Board
        btn_clear = QPushButton("Clear Board")
        def _clear():
            if canvas.mode == InteractionMode.EDIT:
                sz = canvas.state.grid_size
                canvas.state = UrjoState(
                    sz,
                    board=[[UrjoState.EMPTY] * sz for _ in range(sz)],
                    clues=[[None] * sz for _ in range(sz)],
                    givens=[[False] * sz for _ in range(sz)],
                )
                canvas.current_step = None
                canvas.selected_cell = (0, 0)
                canvas.state_modified.emit()
                canvas.update()
        btn_clear.clicked.connect(_clear)
        layout.addWidget(btn_clear)

        layout.addStretch()
        return strip
