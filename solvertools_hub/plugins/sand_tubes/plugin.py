"""
plugin.py - Liquid Sorter Pro plugin descriptor for solvertools_hub.
Supports variable-capacity tubes, split color toggles, preset levels,
and an admissible A* PriorityQueue pouring solver.
"""

from typing import List, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ...core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, BasePuzzleState, BaseSolver, InteractionMode
from ...theme import ChalkTheme
from .canvas import SandTubeCanvas
from .solver import SandTubeSolver
from .state import SandTubeState


class SandTubePlugin(BasePuzzlePlugin):
    """Liquid Sorter Pro plugin with variable capacities and A* heuristic solver."""

    name = "Liquid Sorter Pro"
    category = "Containers / A*"
    description = (
        "Variable-capacity test tubes, 16-color palette, snippet notation, and admissible A* pouring solver. "
        "Click slots to paint/erase, scroll mouse wheel over tubes to adjust capacities, or type snippet notation."
    )

    def create_default_state(self) -> BasePuzzleState:
        return SandTubeState()

    def create_solver(self) -> BaseSolver:
        return SandTubeSolver()

    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        if not isinstance(initial_state, SandTubeState):
            initial_state = SandTubeState()
        return SandTubeCanvas(initial_state)

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        if not isinstance(canvas, SandTubeCanvas):
            return None

        strip = QWidget()
        main_vbox = QVBoxLayout(strip)
        main_vbox.setContentsMargins(6, 4, 6, 4)
        main_vbox.setSpacing(6)

        # -------------------------------------------------------------
        # Row 1: Snippet Notation & Board Topology
        # -------------------------------------------------------------
        row1 = QHBoxLayout()
        row1.setSpacing(6)

        # Notation Text Input (Snippet compatibility)
        row1.addWidget(QLabel("Notation:"))
        notation_input = QLineEdit()
        notation_input.setPlaceholderText("e.g. w,n,-,- / c,n,-,- / -,-,- or 1,2,-,- / 3,2,-,-")
        notation_input.setStyleSheet(
            f"background-color: {ChalkTheme.BG_BOARD_RAISED}; color: {ChalkTheme.FG_CHALK_WHITE}; "
            f"border: 1px solid {ChalkTheme.BORDER_MUTED}; border-radius: 4px; padding: 2px 6px; font-family: Consolas;"
        )
        notation_input.setText(canvas.state.to_notation())
        row1.addWidget(notation_input, stretch=1)

        btn_load = QPushButton("Load")
        btn_load.setToolTip("Parse and load notation string into tubes (Enter)")
        row1.addWidget(btn_load)

        # Separator
        sep1 = QFrame()
        sep1.setFrameShape(QFrame.VLine)
        sep1.setStyleSheet(f"color: {ChalkTheme.BORDER_MUTED};")
        row1.addWidget(sep1)

        # Tube Count Controls
        add_tube_btn = QPushButton("+ Tube")
        add_tube_btn.setToolTip("Add a new empty tube (max 14)")
        def _add_tube():
            if canvas.mode == InteractionMode.EDIT and len(canvas.state.tubes) < 14:
                canvas.state.tubes.append([])
                canvas.state.capacities.append(4)
                canvas.select_tube(len(canvas.state.tubes) - 1)
                canvas.state_modified.emit()
                canvas.update()
        add_tube_btn.clicked.connect(_add_tube)
        row1.addWidget(add_tube_btn)

        rem_tube_btn = QPushButton("- Tube")
        rem_tube_btn.setToolTip("Remove the last tube (min 2)")
        def _rem_tube():
            if canvas.mode == InteractionMode.EDIT and len(canvas.state.tubes) > 2:
                canvas.state.tubes.pop()
                canvas.state.capacities.pop()
                if canvas.selected_tube_idx >= len(canvas.state.tubes):
                    canvas.select_tube(len(canvas.state.tubes) - 1)
                canvas.state_modified.emit()
                canvas.update()
        rem_tube_btn.clicked.connect(_rem_tube)
        row1.addWidget(rem_tube_btn)

        # Separator
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.VLine)
        sep2.setStyleSheet(f"color: {ChalkTheme.BORDER_MUTED};")
        row1.addWidget(sep2)

        # Ergonomic Capacity Stepper (replacing cramped spinbox arrows)
        sel_label = QLabel(f"Tube #{canvas.selected_tube_idx + 1} Cap:")
        row1.addWidget(sel_label)

        cur_cap = canvas.state.capacities[canvas.selected_tube_idx] if canvas.selected_tube_idx < len(canvas.state.capacities) else 4
        btn_cap_dec = QPushButton("–")
        btn_cap_dec.setFixedSize(26, 26)
        btn_cap_dec.setToolTip("Decrease capacity of selected tube (or scroll mouse wheel over tube)")
        row1.addWidget(btn_cap_dec)

        lbl_cap_val = QLabel(str(cur_cap))
        lbl_cap_val.setAlignment(Qt.AlignCenter)
        lbl_cap_val.setFixedWidth(24)
        lbl_cap_val.setStyleSheet(f"color: {ChalkTheme.NEON_CYAN}; font-weight: bold; font-family: Consolas; font-size: 13px;")
        row1.addWidget(lbl_cap_val)

        btn_cap_inc = QPushButton("+")
        btn_cap_inc.setFixedSize(26, 26)
        btn_cap_inc.setToolTip("Increase capacity of selected tube (or scroll mouse wheel over tube)")
        row1.addWidget(btn_cap_inc)

        def _adjust_selected_cap(delta: int):
            if canvas.mode == InteractionMode.EDIT:
                idx = canvas.selected_tube_idx
                if 0 <= idx < len(canvas.state.capacities):
                    cur = canvas.state.capacities[idx]
                    new_cap = max(1, min(8, cur + delta))
                    if new_cap != cur:
                        canvas.state.capacities[idx] = new_cap
                        if len(canvas.state.tubes[idx]) > new_cap:
                            del canvas.state.tubes[idx][new_cap:]
                        lbl_cap_val.setText(str(new_cap))
                        canvas.state_modified.emit()
                        canvas.update()

        btn_cap_dec.clicked.connect(lambda: _adjust_selected_cap(-1))
        btn_cap_inc.clicked.connect(lambda: _adjust_selected_cap(1))

        # Synchronize selection when canvas is clicked
        def _on_tube_selected(idx: int):
            sel_label.setText(f"Tube #{idx + 1} Cap:")
            if 0 <= idx < len(canvas.state.capacities):
                lbl_cap_val.setText(str(canvas.state.capacities[idx]))
        canvas.tube_selected.connect(_on_tube_selected)

        # Separator
        sep3 = QFrame()
        sep3.setFrameShape(QFrame.VLine)
        sep3.setStyleSheet(f"color: {ChalkTheme.BORDER_MUTED};")
        row1.addWidget(sep3)

        # Allow Split Colors Toggle
        split_check = QCheckBox("Allow Split Colors")
        split_check.setToolTip("Permit a single color to be partitioned across multiple completed tubes.")
        split_check.setChecked(canvas.state.allow_split_colors)

        def _on_split_toggled(checked: bool):
            canvas.state.allow_split_colors = checked
            canvas.state_modified.emit()
            _update_feasibility()
        split_check.toggled.connect(_on_split_toggled)
        row1.addWidget(split_check)

        # Feasibility Badge
        feasibility_label = QLabel("Feasibility: OK")
        feasibility_label.setStyleSheet(f"color: {ChalkTheme.NEON_LIME}; font-weight: bold; font-family: Consolas;")
        row1.addWidget(feasibility_label)

        def _update_feasibility():
            if canvas.state.allow_split_colors:
                feasibility_label.setText("Split Mode: Active")
                feasibility_label.setStyleSheet(f"color: {ChalkTheme.NEON_CYAN}; font-weight: bold; font-family: Consolas;")
            else:
                ok, reason = canvas.state.can_satisfy_unique_capacities()
                if ok:
                    feasibility_label.setText("Feasibility: OK")
                    feasibility_label.setStyleSheet(f"color: {ChalkTheme.NEON_LIME}; font-weight: bold; font-family: Consolas;")
                else:
                    feasibility_label.setText("Capacity Mismatch")
                    feasibility_label.setStyleSheet(f"color: {ChalkTheme.NEON_AMBER}; font-weight: bold; font-family: Consolas;")
                    feasibility_label.setToolTip(reason)

        canvas.state_modified.connect(_update_feasibility)
        _update_feasibility()

        main_vbox.addLayout(row1)

        # -------------------------------------------------------------
        # -------------------------------------------------------------
        # Row 2: Dynamic Spawning Palette & Clear Actions
        # -------------------------------------------------------------
        row2 = QHBoxLayout()
        row2.setSpacing(6)

        row2.addWidget(QLabel("Brush:"))

        btn_no_brush = QPushButton("∅ No Color")
        btn_no_brush.setToolTip("Deselect color brush. Click tubes or slots to select/inspect without painting.")
        btn_no_brush.setCursor(Qt.PointingHandCursor)
        row2.addWidget(btn_no_brush)

        # Dynamic palette container
        palette_container = QWidget()
        palette_layout = QHBoxLayout(palette_container)
        palette_layout.setContentsMargins(0, 0, 0, 0)
        palette_layout.setSpacing(4)
        row2.addWidget(palette_container)

        palette_container._displayed_colors = []
        palette_container._color_buttons = []

        btn_add_color = QPushButton("+ Color")
        btn_add_color.setToolTip("Spawn the next available color and select it as brush")
        btn_add_color.setCursor(Qt.PointingHandCursor)
        btn_add_color.setStyleSheet(
            f"background-color: {ChalkTheme.BG_BOARD_RAISED}; color: {ChalkTheme.NEON_LIME}; font-weight: bold; "
            f"border: 1px dashed {ChalkTheme.NEON_LIME}; border-radius: 4px; padding: 3px 8px; font-size: 11px;"
        )
        row2.addWidget(btn_add_color)

        def _update_no_brush_style():
            is_none = (canvas.active_brush_color is None)
            btn_no_brush.setStyleSheet(
                f"background-color: {ChalkTheme.BG_BOARD_RAISED}; "
                f"color: {ChalkTheme.NEON_CYAN if is_none else ChalkTheme.FG_CHALK_MUTED}; "
                f"font-weight: bold; "
                f"border: {'2px solid ' + ChalkTheme.NEON_CYAN if is_none else '1px solid ' + ChalkTheme.BORDER_MUTED}; "
                f"border-radius: 4px; padding: 3px 8px; font-size: 11px;"
            )

        def rebuild_palette():
            _update_no_brush_style()
            used_colors = canvas.state.get_used_colors()
            color_counts = canvas.state.get_color_counts()

            # Active palette consists of all colors present on board + active brush (if any)
            palette_colors = set(used_colors)
            if canvas.active_brush_color is not None:
                palette_colors.add(canvas.active_brush_color)

            # If board is completely empty, ensure at least Color 1 is ready
            if not palette_colors:
                palette_colors.add(0)

            display_colors = sorted(palette_colors)

            # Fast path: update text & styles in place if color list has not changed
            if getattr(palette_container, "_displayed_colors", []) == display_colors:
                for idx, c_idx in enumerate(display_colors):
                    btn = palette_container._color_buttons[idx]
                    count = color_counts.get(c_idx, 0)
                    btn.setText(f"{c_idx + 1} ({count})")
                    is_active = (canvas.active_brush_color == c_idx)
                    hex_col = ChalkTheme.get_color(c_idx)
                    text_col = ChalkTheme.get_contrast_text_color(hex_col)
                    border = f"2px solid {ChalkTheme.NEON_CYAN}" if is_active else f"1px solid {ChalkTheme.BORDER_MUTED}"
                    btn.setStyleSheet(
                        f"background-color: {hex_col}; color: {text_col}; font-weight: bold; "
                        f"border: {border}; border-radius: 4px; padding: 3px 7px; font-family: Consolas; font-size: 11px;"
                    )
                return

            # Rebuild buttons
            while palette_layout.count():
                item = palette_layout.takeAt(0)
                w = item.widget()
                if w:
                    w.deleteLater()

            palette_container._displayed_colors = list(display_colors)
            palette_container._color_buttons = []

            for c_idx in display_colors:
                hex_col = ChalkTheme.get_color(c_idx)
                text_col = ChalkTheme.get_contrast_text_color(hex_col)
                count = color_counts.get(c_idx, 0)
                is_active = (canvas.active_brush_color == c_idx)
                border = f"2px solid {ChalkTheme.NEON_CYAN}" if is_active else f"1px solid {ChalkTheme.BORDER_MUTED}"

                btn = QPushButton(f"{c_idx + 1} ({count})")
                btn.setCursor(Qt.PointingHandCursor)
                btn.setToolTip(
                    f"Color #{c_idx + 1} • {count} segment(s) on board\n"
                    f"• Left-click to select brush (or toggle off)\n"
                    f"• Right-click to clear all Color #{c_idx + 1} segments from board"
                )
                btn.setStyleSheet(
                    f"background-color: {hex_col}; color: {text_col}; font-weight: bold; "
                    f"border: {border}; border-radius: 4px; padding: 3px 7px; font-family: Consolas; font-size: 11px;"
                )
                btn.setContextMenuPolicy(Qt.CustomContextMenu)

                def make_click_handler(col=c_idx):
                    def _click():
                        if canvas.active_brush_color == col:
                            canvas.active_brush_color = None
                        else:
                            canvas.active_brush_color = col
                        rebuild_palette()
                    return _click

                def make_context_handler(col=c_idx):
                    def _context(pos):
                        if canvas.mode == InteractionMode.EDIT:
                            for tube in canvas.state.tubes:
                                for s_i in range(len(tube)):
                                    if tube[s_i] == col:
                                        tube[s_i] = None
                            canvas.state.settle_tubes()
                            if canvas.active_brush_color == col:
                                canvas.active_brush_color = None
                            canvas.state_modified.emit()
                            canvas.update()
                    return _context

                btn.clicked.connect(make_click_handler(c_idx))
                btn.customContextMenuRequested.connect(make_context_handler(c_idx))
                palette_layout.addWidget(btn)
                palette_container._color_buttons.append(btn)

        def _on_add_color():
            current_colors = set(canvas.state.get_used_colors())
            if canvas.active_brush_color is not None:
                current_colors.add(canvas.active_brush_color)
            new_col = 0
            while new_col in current_colors:
                new_col += 1
            canvas.active_brush_color = new_col
            rebuild_palette()

        btn_add_color.clicked.connect(_on_add_color)

        def _clear_brush():
            canvas.active_brush_color = None
            rebuild_palette()

        btn_no_brush.clicked.connect(_clear_brush)

        canvas.state_modified.connect(rebuild_palette)
        rebuild_palette()

        # Separator
        sep4 = QFrame()
        sep4.setFrameShape(QFrame.VLine)
        sep4.setStyleSheet(f"color: {ChalkTheme.BORDER_MUTED};")
        row2.addWidget(sep4)

        btn_clear_tube = QPushButton("✕ Clear Tube")
        btn_clear_tube.setToolTip("Empties the currently selected tube")
        def _on_clear_tube():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state.clear_tube(canvas.selected_tube_idx)
                canvas.state_modified.emit()
                canvas.update()
        btn_clear_tube.clicked.connect(_on_clear_tube)
        row2.addWidget(btn_clear_tube)

        btn_clear_all = QPushButton("✕ Clear All")
        btn_clear_all.setToolTip("Empties all liquid segments across all tubes")
        def _on_clear_all():
            if canvas.mode == InteractionMode.EDIT:
                canvas.state.clear_all_tubes()
                canvas.state_modified.emit()
                canvas.update()
        btn_clear_all.clicked.connect(_on_clear_all)
        row2.addWidget(btn_clear_all)

        row2.addStretch()
        main_vbox.addLayout(row2)

        # -------------------------------------------------------------
        # Two-Way Notation Synchronization
        # -------------------------------------------------------------
        def _sync_notation_from_canvas():
            if not notation_input.hasFocus():
                notation_input.blockSignals(True)
                notation_input.setText(canvas.state.to_notation())
                notation_input.blockSignals(False)

        canvas.state_modified.connect(_sync_notation_from_canvas)

        def _load_notation():
            text = notation_input.text().strip()
            if text:
                new_state = SandTubeState.from_notation(text, allow_split_colors=split_check.isChecked())
                canvas.state = new_state
                canvas.selected_tube_idx = 0
                _on_tube_selected(0)
                canvas.state_modified.emit()
                canvas.update()

        btn_load.clicked.connect(_load_notation)
        notation_input.returnPressed.connect(_load_notation)

        return strip
