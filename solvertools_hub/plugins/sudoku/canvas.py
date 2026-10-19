"""
canvas.py - Interactive QPainter viewport for arbitrary Sudoku grids.
Renders thick chalk sub-box borders, glowing neon cursor and move highlights,
and distinguishes between original clues (Chalk White) and solved numbers (Pastel Mint).
"""

from typing import Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPen

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode, SolverStep
from ...theme import ChalkTheme
from .state import SudokuState


class SudokuCanvas(BasePuzzleCanvas):
    """Interactive viewport for Sudoku puzzles with keyboard navigation."""

    def __init__(self, initial_state: SudokuState):
        super().__init__()
        self.state = initial_state
        self.selected_cell: Optional[Tuple[int, int]] = (0, 0)
        self.current_step: Optional[SolverStep] = None

    def _grid_geometry(self, dim: Optional[int] = None) -> Tuple[float, float, float]:
        """Returns (origin_x, origin_y, cell_size)."""
        if dim is None:
            render_state = self.get_render_state()
            dim = getattr(render_state, "grid_dim", self.state.grid_dim)
        margin = 40.0
        avail_w = self.width() - margin * 2
        avail_h = self.height() - margin * 2
        board_size = min(avail_w, avail_h)
        cell_size = board_size / dim
        ox = (self.width() - board_size) / 2
        oy = (self.height() - board_size) / 2
        return ox, oy, cell_size

    def _cell_rect(self, r: int, c: int, dim: Optional[int] = None) -> QRectF:
        ox, oy, cell_size = self._grid_geometry(dim)
        return QRectF(ox + c * cell_size, oy + r * cell_size, cell_size, cell_size)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.mode != InteractionMode.EDIT:
            return

        pos = event.position()
        dim = self.state.grid_dim
        for r in range(dim):
            for c in range(dim):
                if self._cell_rect(r, c).contains(pos):
                    self.selected_cell = (r, c)
                    self.update()
                    return

        self.selected_cell = None
        self.update()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.mode != InteractionMode.EDIT or self.selected_cell is None:
            super().keyPressEvent(event)
            return

        r, c = self.selected_cell
        dim = self.state.grid_dim
        key = event.key()

        # Navigation
        if key == Qt.Key_Left:
            self.selected_cell = (r, max(0, c - 1))
            self.update()
            return
        elif key == Qt.Key_Right:
            self.selected_cell = (r, min(dim - 1, c + 1))
            self.update()
            return
        elif key == Qt.Key_Up:
            self.selected_cell = (max(0, r - 1), c)
            self.update()
            return
        elif key == Qt.Key_Down:
            self.selected_cell = (min(dim - 1, r + 1), c)
            self.update()
            return

        # Clear cell
        if key in (Qt.Key_Backspace, Qt.Key_Delete, Qt.Key_0):
            self.state.board[r][c] = 0
            self.state.clues.discard((r, c))
            self.state_modified.emit()
            self.update()
            return

        # Digit entry
        text = event.text()
        if text.isdigit():
            val = int(text)
            if 1 <= val <= dim:
                self.state.board[r][c] = val
                self.state.clues.add((r, c))
                self.state_modified.emit()
                self.update()
                return

        super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        render_state: SudokuState = self.get_render_state()  # type: ignore
        highlights = self.current_step.highlights if self.current_step else {}
        dim = render_state.grid_dim
        box_w = render_state.box_w
        box_h = render_state.box_h

        ox, oy, cell_size = self._grid_geometry(dim)
        board_size = cell_size * dim
        board_rect = QRectF(ox, oy, board_size, board_size)

        # Draw main board surface background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(ChalkTheme.BG_SLATE_GREEN))
        painter.drawRect(board_rect)

        # Draw cell contents & thin dividers
        font_size = max(11, int(cell_size * 0.42))
        clue_font = QFont("Consolas", font_size, QFont.Bold)
        solved_font = QFont("Consolas", font_size, QFont.Normal)

        for r in range(dim):
            for c in range(dim):
                rect = self._cell_rect(r, c)

                # Thin inner border
                painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(rect)

                val = render_state.board[r][c]
                if val != 0:
                    is_clue = (r, c) in render_state.clues
                    if is_clue:
                        painter.setFont(clue_font)
                        painter.setPen(QColor(ChalkTheme.FG_CHALK_WHITE))
                    else:
                        painter.setFont(solved_font)
                        painter.setPen(QColor(ChalkTheme.PASTEL_MINT))

                    painter.drawText(rect, Qt.AlignCenter, str(val))

        # Draw thick sub-box borders
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_WHITE), 2.5))
        painter.setBrush(Qt.NoBrush)

        # Vertical sub-box lines
        for bc in range(0, dim + 1, box_w):
            x = ox + bc * cell_size
            painter.drawLine(QPointF(x, oy), QPointF(x, oy + board_size))

        # Horizontal sub-box lines
        for br in range(0, dim + 1, box_h):
            y = oy + br * cell_size
            painter.drawLine(QPointF(ox, y), QPointF(ox + board_size, y))

        # Active highlights
        if self.mode == InteractionMode.EDIT and self.selected_cell:
            sr, sc = self.selected_cell
            sel_rect = self._cell_rect(sr, sc)
            ChalkTheme.draw_neon_rect(painter, sel_rect, ChalkTheme.NEON_CYAN, radius=3, glow_width=5)
        elif self.mode == InteractionMode.PLAYBACK:
            hr = highlights.get("r")
            hc = highlights.get("c")
            if hr is not None and hc is not None:
                step_rect = self._cell_rect(hr, hc)
                ChalkTheme.draw_neon_rect(painter, step_rect, ChalkTheme.NEON_LIME, radius=3, glow_width=6)
