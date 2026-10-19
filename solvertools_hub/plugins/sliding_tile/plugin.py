"""
plugin.py - Sliding Tile (N-Puzzle) plugin descriptor for solvertools_hub.
"""

import random
from typing import Optional

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QSpinBox, QWidget

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver, InteractionMode
from .canvas import SlidingTileCanvas
from .solver import SlidingTileSolver
from .state import SlidingTileState


class SlidingTilePlugin(BasePuzzlePlugin):
    """Sliding Tile N-Puzzle plugin with A* Manhattan distance solver."""
    name = "Sliding Tile (N-Puzzle)"
    category = "Sequential / A*"
    description = "Click two cells to swap tiles for rapid 1:1 screen transcription, then run Playback or Instant Solve."

    def create_default_state(self) -> BasePuzzleState:
        return SlidingTileState(3)

    def create_solver(self) -> BaseSolver:
        return SlidingTileSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, SlidingTileState):
            initial_state = SlidingTileState(3)
        return SlidingTileCanvas(initial_state)

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        if not isinstance(canvas, SlidingTileCanvas):
            return None

        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        layout.addWidget(QLabel("Grid Size:"))

        spin = QSpinBox()
        spin.setRange(2, 5)
        spin.setValue(canvas.state.size)

        def _on_size_changed(val: int):
            if canvas.mode == InteractionMode.EDIT:
                canvas.state = SlidingTileState(val)
                canvas.selected_edit_idx = None
                canvas.current_step = None
                canvas.state_modified.emit()
                canvas.update()

        spin.valueChanged.connect(_on_size_changed)
        layout.addWidget(spin)

        btn_shuffle = QPushButton("Random Solvable Shuffle")

        def _shuffle():
            if canvas.mode == InteractionMode.EDIT:
                size = canvas.state.size
                tiles = list(range(1, size * size)) + [0]
                # Random walk shuffle from solved state guarantees solvability
                zero_idx = len(tiles) - 1
                for _ in range(80):
                    zr, zc = divmod(zero_idx, size)
                    valid_moves = []
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = zr + dr, zc + dc
                        if 0 <= nr < size and 0 <= nc < size:
                            valid_moves.append(nr * size + nc)
                    pick = random.choice(valid_moves)
                    tiles[zero_idx], tiles[pick] = tiles[pick], tiles[zero_idx]
                    zero_idx = pick

                canvas.state.grid = tiles
                canvas.selected_edit_idx = None
                canvas.current_step = None
                canvas.state_modified.emit()
                canvas.update()

        btn_shuffle.clicked.connect(_shuffle)
        layout.addWidget(btn_shuffle)

        layout.addStretch()
        return strip
