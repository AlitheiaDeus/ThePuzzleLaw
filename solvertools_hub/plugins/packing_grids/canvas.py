"""
canvas.py - Interactive QPainter canvas for Packing Grids & Nonograms.
Renders row/col clue gutters, filled pixels, and cross marks.
"""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode
from ...theme import ChalkTheme
from .state import PackingGridsState


class PackingGridsCanvas(BasePuzzleCanvas):
    """Canvas for solving and editing Nonogram pixel grids."""

    def __init__(self, initial_state: PackingGridsState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state: PackingGridsState = initial_state

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(ChalkTheme.BG_CHALK_BLACK))

        st = self.state if self.mode == InteractionMode.EDIT or not self.current_step else self.current_step.state
        if not isinstance(st, PackingGridsState):
            st = self.state

        rows, cols = st.rows, st.cols
        gutter = 60
        margin = 24
        grid_w = min(w - gutter - 2 * margin, h - gutter - 2 * margin)
        cell_size = grid_w / max(rows, cols)

        top_left_x = gutter + (w - gutter - cell_size * cols) / 2
        top_left_y = gutter + (h - gutter - cell_size * rows) / 2

        # Draw cells
        for r in range(rows):
            for c in range(cols):
                rect = QRectF(top_left_x + c * cell_size, top_left_y + r * cell_size, cell_size, cell_size)
                val = st.grid[r][c]

                if val == PackingGridsState.CELL_FILLED:
                    painter.fillRect(rect, QColor(ChalkTheme.NEON_CYAN))
                else:
                    painter.fillRect(rect, QColor(ChalkTheme.BG_SLATE_GREEN))

                painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1))
                painter.drawRect(rect)

                if val == PackingGridsState.CELL_CROSS:
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_CORAL), 2))
                    painter.drawLine(rect.topLeft() + QPointF(4, 4), rect.bottomRight() - QPointF(4, 4))
                    painter.drawLine(rect.topRight() + QPointF(-4, 4), rect.bottomLeft() - QPointF(-4, 4))

        # Draw gutter clues
        font = painter.font()
        font.setPointSize(9)
        painter.setFont(font)
        painter.setPen(QPen(QColor(ChalkTheme.PASTEL_PEACH)))

        # Row clues
        for r in range(rows):
            clues_str = " ".join(map(str, st.row_clues[r]))
            clue_rect = QRectF(top_left_x - gutter, top_left_y + r * cell_size, gutter - 8, cell_size)
            painter.drawText(clue_rect, Qt.AlignRight | Qt.AlignVCenter, clues_str)

        # Col clues
        for c in range(cols):
            clues_str = "\n".join(map(str, st.col_clues[c]))
            clue_rect = QRectF(top_left_x + c * cell_size, top_left_y - gutter, cell_size, gutter - 8)
            painter.drawText(clue_rect, Qt.AlignHCenter | Qt.AlignBottom, clues_str)

        # Outer border
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_WHITE), 2))
        painter.drawRect(QRectF(top_left_x, top_left_y, cell_size * cols, cell_size * rows))

    def mousePressEvent(self, event):
        if self.mode != InteractionMode.PLAYBACK:
            w, h = self.width(), self.height()
            rows, cols = self.state.rows, self.state.cols
            gutter = 60
            margin = 24
            grid_w = min(w - gutter - 2 * margin, h - gutter - 2 * margin)
            cell_size = grid_w / max(rows, cols)
            top_left_x = gutter + (w - gutter - cell_size * cols) / 2
            top_left_y = gutter + (h - gutter - cell_size * rows) / 2

            pos = event.position()
            c = int((pos.x() - top_left_x) // cell_size)
            r = int((pos.y() - top_left_y) // cell_size)

            if 0 <= r < rows and 0 <= c < cols:
                if event.button() == Qt.LeftButton:
                    self.state.grid[r][c] = (
                        PackingGridsState.CELL_FILLED
                        if self.state.grid[r][c] != PackingGridsState.CELL_FILLED
                        else PackingGridsState.CELL_EMPTY
                    )
                elif event.button() == Qt.RightButton:
                    self.state.grid[r][c] = (
                        PackingGridsState.CELL_CROSS
                        if self.state.grid[r][c] != PackingGridsState.CELL_CROSS
                        else PackingGridsState.CELL_EMPTY
                    )

                self.current_step = None
                self.state_modified.emit()
                self.update()
