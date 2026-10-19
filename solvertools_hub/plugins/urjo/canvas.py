"""
canvas.py - Interactive QPainter viewport for the Urjo logic puzzle.
Renders circular disks in Royal Cobalt (Blue) and Vivid Crimson (Red) with centered
neon chalkboard clue digits (0-8), selection cursors, and playback search glows.
"""

from typing import Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode, SolverStep
from ...theme import ChalkTheme
from .state import UrjoState


class UrjoCanvas(BasePuzzleCanvas):
    """Interactive viewport for Urjo puzzle transcription and solution playback."""

    # Color tokens for Urjo disks
    COLOR_RED_HEX = "#FF4757"       # Vivid Crimson
    COLOR_RED_BORDER = "#FF6B81"
    COLOR_BLUE_HEX = "#2E86DE"      # Royal Cobalt / Electric Blue
    COLOR_BLUE_BORDER = "#54A0FF"

    # Forward: Blank (0) -> Blue (2) -> Red (1) -> Blank (0)
    CYCLE_FORWARD = {
        UrjoState.EMPTY: UrjoState.COLOR_BLUE,
        UrjoState.COLOR_BLUE: UrjoState.COLOR_RED,
        UrjoState.COLOR_RED: UrjoState.EMPTY,
    }

    # Reverse: Blank (0) -> Red (1) -> Blue (2) -> Blank (0)
    CYCLE_REVERSE = {
        UrjoState.EMPTY: UrjoState.COLOR_RED,
        UrjoState.COLOR_RED: UrjoState.COLOR_BLUE,
        UrjoState.COLOR_BLUE: UrjoState.EMPTY,
    }

    def __init__(self, initial_state: UrjoState):
        super().__init__()
        self.state = initial_state
        self.edit_tool: str = "cycle"  # "cycle", "blue", "red", "clue"
        self.selected_cell: Optional[Tuple[int, int]] = (0, 0)
        self.current_step: Optional[SolverStep] = None

    def set_mode(self, mode: InteractionMode) -> None:
        """Sets the canvas interaction mode (EDIT vs. PLAYBACK) and repaints."""
        super().set_mode(mode)
        if mode == InteractionMode.EDIT:
            self.current_step = None
        self.update()

    def _grid_geometry(self, dim: Optional[int] = None) -> Tuple[float, float, float]:
        margin = 35.0
        avail_w = max(100.0, self.width() - margin * 2)
        avail_h = max(100.0, self.height() - margin * 2)
        if dim is None:
            render_state = self.state if self.mode == InteractionMode.EDIT else (self.current_step.state if self.current_step else self.state)
            dim = render_state.grid_size
        cell_size = min(avail_w, avail_h) / dim
        board_size = cell_size * dim
        ox = (self.width() - board_size) / 2
        oy = (self.height() - board_size) / 2
        return ox, oy, cell_size

    def _cell_rect(self, r: int, c: int, dim: int) -> QRectF:
        ox, oy, cell_size = self._grid_geometry(dim)
        pad = cell_size * 0.08
        return QRectF(
            ox + c * cell_size + pad,
            oy + r * cell_size + pad,
            cell_size - pad * 2,
            cell_size - pad * 2,
        )

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.mode != InteractionMode.EDIT:
            return

        pos = event.position()
        dim = self.state.grid_size
        ox, oy, cell_size = self._grid_geometry(dim)

        c = int((pos.x() - ox) // cell_size)
        r = int((pos.y() - oy) // cell_size)

        if not (0 <= r < dim and 0 <= c < dim):
            return

        self.selected_cell = (r, c)
        max_k = len(self.state.get_neighbors(r, c))

        if self.edit_tool == "cycle":
            if event.button() == Qt.LeftButton:
                # Forward: Blank -> Blue -> Red -> Blank
                self.state.board[r][c] = self.CYCLE_FORWARD[self.state.board[r][c]]
            elif event.button() == Qt.RightButton:
                # Reverse: Blank -> Red -> Blue -> Blank
                self.state.board[r][c] = self.CYCLE_REVERSE[self.state.board[r][c]]

        elif self.edit_tool == "clue":
            curr = self.state.clues[r][c]
            if event.button() == Qt.LeftButton:
                # Increment clue: None -> 0 -> 1 -> ... -> max_k -> None
                if curr is None:
                    self.state.clues[r][c] = 0
                elif curr < max_k:
                    self.state.clues[r][c] = curr + 1
                else:
                    self.state.clues[r][c] = None
            elif event.button() == Qt.RightButton:
                # Decrement clue: None -> max_k -> max_k - 1 -> ... -> 0 -> None
                if curr is None:
                    self.state.clues[r][c] = max_k
                elif curr > 0:
                    self.state.clues[r][c] = curr - 1
                else:
                    self.state.clues[r][c] = None

        elif self.edit_tool == "blue":
            if event.button() == Qt.LeftButton:
                self.state.board[r][c] = (
                    UrjoState.EMPTY if self.state.board[r][c] == UrjoState.COLOR_BLUE else UrjoState.COLOR_BLUE
                )
            elif event.button() == Qt.RightButton:
                self.state.board[r][c] = UrjoState.EMPTY

        elif self.edit_tool == "red":
            if event.button() == Qt.LeftButton:
                self.state.board[r][c] = (
                    UrjoState.EMPTY if self.state.board[r][c] == UrjoState.COLOR_RED else UrjoState.COLOR_RED
                )
            elif event.button() == Qt.RightButton:
                self.state.board[r][c] = UrjoState.EMPTY

        self.current_step = None
        self.state_modified.emit()
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.mode != InteractionMode.EDIT or self.selected_cell is None:
            super().keyPressEvent(event)
            return

        r, c = self.selected_cell
        dim = self.state.grid_size
        key = event.key()

        # Numeric clue input (0 through 8)
        if Qt.Key_0 <= key <= Qt.Key_8:
            digit = key - Qt.Key_0
            max_nbrs = len(self.state.get_neighbors(r, c))
            if digit <= max_nbrs:
                self.state.clues[r][c] = digit
                self.current_step = None
                self.state_modified.emit()
                self.update()
            return

        # Clear clue / Clear cell
        if key in (Qt.Key_Delete, Qt.Key_Backspace, Qt.Key_C):
            if self.state.clues[r][c] is not None:
                self.state.clues[r][c] = None
            else:
                self.state.board[r][c] = UrjoState.EMPTY
            self.current_step = None
            self.state_modified.emit()
            self.update()
            return

        # Direct Color Keys: B (Blue), R (Red), E (Empty), Space (Cycle)
        if key == Qt.Key_B:
            self.state.board[r][c] = UrjoState.COLOR_BLUE
            self.current_step = None
            self.state_modified.emit()
            self.update()
            return
        elif key == Qt.Key_R:
            self.state.board[r][c] = UrjoState.COLOR_RED
            self.current_step = None
            self.state_modified.emit()
            self.update()
            return
        elif key == Qt.Key_E:
            self.state.board[r][c] = UrjoState.EMPTY
            self.current_step = None
            self.state_modified.emit()
            self.update()
            return
        elif key == Qt.Key_Space:
            if event.modifiers() & Qt.ShiftModifier:
                self.state.board[r][c] = self.CYCLE_REVERSE[self.state.board[r][c]]
            else:
                self.state.board[r][c] = self.CYCLE_FORWARD[self.state.board[r][c]]
            self.current_step = None
            self.state_modified.emit()
            self.update()
            return

        # Arrow Key Navigation
        if key == Qt.Key_Up:
            self.selected_cell = (max(0, r - 1), c)
            self.update()
            return
        elif key == Qt.Key_Down:
            self.selected_cell = (min(dim - 1, r + 1), c)
            self.update()
            return
        elif key == Qt.Key_Left:
            self.selected_cell = (r, max(0, c - 1))
            self.update()
            return
        elif key == Qt.Key_Right:
            self.selected_cell = (r, min(dim - 1, c + 1))
            self.update()
            return

        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # In EDIT mode, always render the active working state directly
        if self.mode == InteractionMode.EDIT:
            render_state: UrjoState = self.state
            highlights = {}
        else:
            render_state = self.current_step.state if self.current_step else self.state
            highlights = self.current_step.highlights if self.current_step else {}

        dim = render_state.grid_size
        ox, oy, cell_size = self._grid_geometry(dim)

        # 1. Blackboard surface frame
        board_rect = QRectF(ox - 8, oy - 8, cell_size * dim + 16, cell_size * dim + 16)
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 2))
        painter.setBrush(QColor(ChalkTheme.BG_SLATE_GREEN))
        painter.drawRoundedRect(board_rect, 10, 10)

        # 2. Subtle internal grid lines
        grid_pen = QPen(QColor(ChalkTheme.FG_CHALK_DUST))
        grid_pen.setWidthF(0.75)
        painter.setPen(grid_pen)
        for i in range(1, dim):
            painter.drawLine(QPointF(ox, oy + i * cell_size), QPointF(ox + dim * cell_size, oy + i * cell_size))
            painter.drawLine(QPointF(ox + i * cell_size, oy), QPointF(ox + i * cell_size, oy + dim * cell_size))

        # 3. Render circular Urjo cells
        for r in range(dim):
            for c in range(dim):
                rect = self._cell_rect(r, c, dim)
                color = render_state.board[r][c]
                clue = render_state.clues[r][c]

                # Draw disk
                if color == UrjoState.COLOR_BLUE:
                    painter.setPen(QPen(QColor(self.COLOR_BLUE_BORDER), 2.0))
                    painter.setBrush(QColor(self.COLOR_BLUE_HEX))
                    painter.drawEllipse(rect)
                elif color == UrjoState.COLOR_RED:
                    painter.setPen(QPen(QColor(self.COLOR_RED_BORDER), 2.0))
                    painter.setBrush(QColor(self.COLOR_RED_HEX))
                    painter.drawEllipse(rect)
                else:
                    # Empty cell slot
                    painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1.5, Qt.DashLine))
                    painter.setBrush(QColor(ChalkTheme.BG_BOARD_RAISED))
                    painter.drawEllipse(rect)

                # Draw clue digit if present
                if clue is not None:
                    if color == UrjoState.EMPTY:
                        painter.setPen(QColor(ChalkTheme.NEON_AMBER))
                    else:
                        painter.setPen(QColor(ChalkTheme.FG_CHALK_WHITE))

                    font_size = max(11, int(cell_size * 0.44))
                    painter.setFont(QFont("Consolas", font_size, QFont.Bold))
                    painter.drawText(rect, Qt.AlignCenter, str(clue))

                # Playback search highlight
                if self.mode == InteractionMode.PLAYBACK:
                    if highlights.get("r") == r and highlights.get("c") == c:
                        glow_rect = rect.adjusted(-4, -4, 4, 4)
                        ChalkTheme.draw_neon_rect(painter, glow_rect, ChalkTheme.NEON_LIME, radius=glow_rect.width() / 2, glow_width=6)

                # Edit mode selection indicator
                elif self.mode == InteractionMode.EDIT and self.selected_cell == (r, c):
                    sel_rect = rect.adjusted(-3, -3, 3, 3)
                    sel_pen = QPen(QColor(ChalkTheme.NEON_CYAN), 2.0, Qt.SolidLine)
                    painter.setPen(sel_pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawEllipse(sel_rect)
