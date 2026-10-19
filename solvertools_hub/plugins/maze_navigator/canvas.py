"""
canvas.py - Interactive QPainter canvas for Maze Navigator.
Renders chalkboard grid, wall barriers, Start/Goal markers, and live search frontiers.
"""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode
from ...theme import ChalkTheme
from .state import MazeNavigatorState


class MazeNavigatorCanvas(BasePuzzleCanvas):
    """Canvas for drawing maze barriers and scrubbing search paths."""

    def __init__(self, initial_state: MazeNavigatorState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state: MazeNavigatorState = initial_state

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(ChalkTheme.BG_CHALK_BLACK))

        st = self.state if self.mode == InteractionMode.EDIT or not self.current_step else self.current_step.state
        if not isinstance(st, MazeNavigatorState):
            st = self.state

        rows, cols = st.rows, st.cols
        margin = 32
        cell_w = (w - 2 * margin) / cols
        cell_h = (h - 2 * margin) / rows
        cell_size = min(cell_w, cell_h)

        board_w = cell_size * cols
        board_h = cell_size * rows
        top_left_x = (w - board_w) / 2
        top_left_y = (h - board_h) / 2

        # Draw cells & walls
        for r in range(rows):
            for c in range(cols):
                rect = QRectF(top_left_x + c * cell_size, top_left_y + r * cell_size, cell_size, cell_size)

                if st.walls[r][c]:
                    painter.fillRect(rect, QColor(ChalkTheme.PASTEL_MINT))
                else:
                    painter.fillRect(rect, QColor(ChalkTheme.BG_SLATE_GREEN))

                painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1))
                painter.drawRect(rect)

        # Highlight search paths / visited nodes
        if self.current_step and self.current_step.highlights:
            visited = self.current_step.highlights.get("visited", [])
            for vr, vc in visited:
                if not st.walls[vr][vc] and [vr, vc] != st.start and [vr, vc] != st.goal:
                    v_rect = QRectF(top_left_x + vc * cell_size, top_left_y + vr * cell_size, cell_size, cell_size)
                    painter.fillRect(v_rect, QColor(0, 245, 212, 40))

            path = self.current_step.highlights.get("path", [])
            for pr, pc in path:
                if [pr, pc] != st.start and [pr, pc] != st.goal:
                    p_rect = QRectF(top_left_x + pc * cell_size, top_left_y + pr * cell_size, cell_size, cell_size)
                    painter.fillRect(p_rect, QColor(ChalkTheme.NEON_LIME))

        # Start & Goal markers
        sr, sc = st.start
        s_rect = QRectF(top_left_x + sc * cell_size, top_left_y + sr * cell_size, cell_size, cell_size)
        painter.setBrush(QBrush(QColor(ChalkTheme.PASTEL_SKY)))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(s_rect.center(), cell_size * 0.4, cell_size * 0.4)

        gr, gc = st.goal
        g_rect = QRectF(top_left_x + gc * cell_size, top_left_y + gr * cell_size, cell_size, cell_size)
        painter.setBrush(QBrush(QColor(ChalkTheme.NEON_CORAL)))
        painter.drawEllipse(g_rect.center(), cell_size * 0.4, cell_size * 0.4)

        # Outer border
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_WHITE), 2))
        painter.drawRect(QRectF(top_left_x, top_left_y, board_w, board_h))

    def mousePressEvent(self, event):
        if self.mode != InteractionMode.PLAYBACK:
            w, h = self.width(), self.height()
            rows, cols = self.state.rows, self.state.cols
            margin = 32
            cell_size = min((w - 2 * margin) / cols, (h - 2 * margin) / rows)
            top_left_x = (w - cell_size * cols) / 2
            top_left_y = (h - cell_size * rows) / 2

            pos = event.position()
            c = int((pos.x() - top_left_x) // cell_size)
            r = int((pos.y() - top_left_y) // cell_size)

            if 0 <= r < rows and 0 <= c < cols:
                if event.button() == Qt.LeftButton:
                    self.state.walls[r][c] = not self.state.walls[r][c]
                elif event.button() == Qt.RightButton:
                    if self.state.start != [r, c]:
                        self.state.start = [r, c]
                    else:
                        self.state.goal = [r, c]

                self.current_step = None
                self.state_modified.emit()
                self.update()
