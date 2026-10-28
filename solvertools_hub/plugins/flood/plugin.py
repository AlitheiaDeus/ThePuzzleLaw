"""
plugin.py - Flood puzzle plugin descriptor and interactive tool strip for solvertools_hub.
Provides grid size controls, color palette brush swatches, randomize generation, and presets.
"""

import random
from typing import Optional

from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QWidget,
)

from ...core.base_plugin import (
    BasePuzzleCanvas,
    BasePuzzlePlugin,
    BasePuzzleState,
    BaseSolver,
    InteractionMode,
)
from ...theme import ChalkTheme
from .canvas import FloodCanvas
from .solver import FloodSolver
from .state import FloodState


class FloodPlugin(BasePuzzlePlugin):
    """Flood-It puzzle plugin: minimum-move color flood engine with optimal IDA*."""

    name = "Flood"
    category = "Grid / Graph Search"
    description = (
        "Flood-It: Homogenize the grid in the minimum number of color moves by absorbing "
        "orthogonally adjacent tiles of matching colors starting from the top-left anchor (0, 0)."
    )

    def _generate_random_grid(self, rows: int, cols: int, num_colors: int, seed: Optional[int] = None) -> FloodState:
        rng = random.Random(seed)
        grid = [[rng.randint(0, num_colors - 1) for _ in range(cols)] for _ in range(rows)]
        return FloodState(rows=rows, cols=cols, num_colors=num_colors, grid=grid)

    def create_default_state(self) -> BasePuzzleState:
        # Default 12x12 grid with 6 colors (seed=42 for deterministic reproducible default)
        return self._generate_random_grid(12, 12, 6, seed=42)

    def create_solver(self) -> BaseSolver:
        return FloodSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, FloodState):
            initial_state = self.create_default_state()
        return FloodCanvas(initial_state)

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        if not isinstance(canvas, FloodCanvas):
            return None

        strip = QWidget()
        layout = QHBoxLayout(strip)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(8)

        # 1. Grid Size Selector
        layout.addWidget(QLabel("Size:"))
        size_combo = QComboBox()
        size_combo.addItems(["6×6", "8×8", "10×10", "12×12"])
        size_combo.setCurrentIndex(3)  # Default 12x12

        # 2. Number of Colors Selector
        layout.addWidget(QLabel("Colors:"))
        colors_combo = QComboBox()
        colors_combo.addItems(["3", "4", "5", "6", "7", "8"])
        colors_combo.setCurrentIndex(3)  # Default 6 colors

        # Separator line
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet(f"color: {ChalkTheme.BORDER_MUTED};")
        layout.addWidget(sep1)

        # 3. Brush Color Swatches
        layout.addWidget(QLabel("Brush:"))
        brush_group = QButtonGroup(strip)
        brush_group.setExclusive(True)

        cycle_btn = QPushButton("Cycle")
        cycle_btn.setCheckable(True)
        cycle_btn.setChecked(True)
        cycle_btn.setToolTip("Click a tile to cycle its color; right-click to cycle backwards.")
        brush_group.addButton(cycle_btn)
        layout.addWidget(cycle_btn)

        swatch_buttons = []
        for c_idx in range(len(FloodState.COLOR_HEXES)):
            btn = QPushButton()
            btn.setCheckable(True)
            btn.setFixedSize(24, 24)
            hex_color = FloodState.COLOR_HEXES[c_idx]
            name = FloodState.COLOR_NAMES[c_idx]
            btn.setToolTip(f"Paint with {name}")
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {hex_color};
                    border: 1.5px solid #2B3A33;
                    border-radius: 4px;
                }}
                QPushButton:checked {{
                    border: 2px solid #FFFFFF;
                }}
            """)
            brush_group.addButton(btn)
            layout.addWidget(btn)
            swatch_buttons.append((c_idx, btn))

        def _update_swatch_visibility():
            active_colors = int(colors_combo.currentText())
            for c_idx, btn in swatch_buttons:
                btn.setVisible(c_idx < active_colors)

        _update_swatch_visibility()

        def _on_brush_toggled():
            if canvas.mode != InteractionMode.EDIT:
                return
            if cycle_btn.isChecked():
                canvas.active_brush_color = None
            else:
                for c_idx, btn in swatch_buttons:
                    if btn.isChecked():
                        canvas.active_brush_color = c_idx
                        break

        cycle_btn.toggled.connect(_on_brush_toggled)
        for _, btn in swatch_buttons:
            btn.toggled.connect(_on_brush_toggled)

        # Separator line
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"color: {ChalkTheme.BORDER_MUTED};")
        layout.addWidget(sep2)

        # 4. Randomize Button
        rand_btn = QPushButton("🎲 Randomize")
        rand_btn.setToolTip("Generate a new random board")

        def _on_randomize():
            if canvas.mode != InteractionMode.EDIT:
                return
            dim = [6, 8, 10, 12][size_combo.currentIndex()]
            num_c = int(colors_combo.currentText())
            canvas.state = self._generate_random_grid(dim, dim, num_c)
            canvas.current_step = None
            canvas.selected_cell = (0, 0)
            canvas.state_modified.emit()
            canvas.update()

        rand_btn.clicked.connect(_on_randomize)
        layout.addWidget(rand_btn)

        # 5. Size or Color count change handlers
        def _on_config_changed():
            if canvas.mode != InteractionMode.EDIT:
                return
            _update_swatch_visibility()
            _on_randomize()

        size_combo.currentIndexChanged.connect(_on_config_changed)
        colors_combo.currentIndexChanged.connect(_on_config_changed)

        # 6. Presets ComboBox
        layout.addWidget(QLabel("Preset:"))
        preset_combo = QComboBox()
        preset_combo.addItems([
            "Select Preset...",
            "Micro 6×6 (4 Colors)",
            "Standard 8×8 (6 Colors)",
            "Classic 12×12 (6 Colors)",
            "Checkerboard Wave",
            "Concentric Rings",
        ])

        def _on_preset_selected(idx: int):
            if canvas.mode != InteractionMode.EDIT or idx == 0:
                return

            canvas.current_step = None
            canvas.selected_cell = (0, 0)

            if idx == 1:  # Micro 6x6
                size_combo.setCurrentIndex(0)
                colors_combo.setCurrentIndex(1)
                canvas.state = self._generate_random_grid(6, 6, 4, seed=101)
            elif idx == 2:  # Standard 8x8
                size_combo.setCurrentIndex(1)
                colors_combo.setCurrentIndex(3)
                canvas.state = self._generate_random_grid(8, 8, 6, seed=202)
            elif idx == 3:  # Classic 12x12
                size_combo.setCurrentIndex(3)
                colors_combo.setCurrentIndex(3)
                canvas.state = self._generate_random_grid(12, 12, 6, seed=42)
            elif idx == 4:  # Checkerboard Wave
                dim = 8
                grid = [[(r + c) % 4 for c in range(dim)] for r in range(dim)]
                size_combo.setCurrentIndex(1)
                colors_combo.setCurrentIndex(1)
                canvas.state = FloodState(rows=dim, cols=dim, num_colors=4, grid=grid)
            elif idx == 5:  # Concentric Rings
                dim = 10
                grid = [[min(r, c, dim - 1 - r, dim - 1 - c) % 5 for c in range(dim)] for r in range(dim)]
                size_combo.setCurrentIndex(2)
                colors_combo.setCurrentIndex(2)
                canvas.state = FloodState(rows=dim, cols=dim, num_colors=5, grid=grid)

            _update_swatch_visibility()
            canvas.state_modified.emit()
            canvas.update()
            preset_combo.setCurrentIndex(0)

        preset_combo.currentIndexChanged.connect(_on_preset_selected)
        layout.addWidget(preset_combo)

        return strip
