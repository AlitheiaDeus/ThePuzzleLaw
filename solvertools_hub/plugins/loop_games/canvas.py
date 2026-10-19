"""
canvas.py - Interactive QPainter canvas for Loop Family (Slitherlink / Palisade / Pearl).
Renders lattice grid of vertex dots, numeric cell clues, and line/cross edges.
"""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode
from ...theme import ChalkTheme
from .state import LoopFamilyState


class LoopFamilyCanvas(BasePuzzleCanvas):
    """Canvas for drawing loop lines and editing Slitherlink clues."""

    def __init__(self, initial_state: LoopFamilyState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state: LoopFamilyState = initial_state

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(ChalkTheme.BG_CHALK_BLACK))

        st = self.state if self.mode == InteractionMode.EDIT or not self.current_step else self.current_step.state
        if not isinstance(st, LoopFamilyState):
            st = self.state

        sz = st.size
        margin = 40
        board_dim = min(w - 2 * margin, h - 2 * margin)
        cell_size = board_dim / sz
        top_left_x = (w - board_dim) / 2
        top_left_y = (h - board_dim) / 2

        # Draw cell clues
        font = painter.font()
        font.setPointSize(int(cell_size * 0.45))
        font.setBold(True)
        painter.setFont(font)

        for r in range(sz):
            for c in range(sz):
                clue = st.cell_clues[r][c]
                if clue is not None:
                    rect = QRectF(top_left_x + c * cell_size, top_left_y + r * cell_size, cell_size, cell_size)
                    painter.setPen(QPen(QColor(ChalkTheme.PASTEL_PEACH)))
                    painter.drawText(rect, Qt.AlignCenter, str(clue))

        # Draw horizontal edges
        for r in range(sz + 1):
            for c in range(sz):
                x1 = top_left_x + c * cell_size
                x2 = x1 + cell_size
                y = top_left_y + r * cell_size
                edge = st.h_edges[r][c]

                if edge == LoopFamilyState.EDGE_LINE:
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_LIME), 4, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(QPointF(x1, y), QPointF(x2, y))
                elif edge == LoopFamilyState.EDGE_CROSS:
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_CORAL), 2))
                    mx = (x1 + x2) / 2
                    painter.drawLine(QPointF(mx - 4, y - 4), QPointF(mx + 4, y + 4))
                    painter.drawLine(QPointF(mx - 4, y + 4), QPointF(mx + 4, y - 4))
                else:
                    painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1, Qt.DotLine))
                    painter.drawLine(QPointF(x1, y), QPointF(x2, y))

        # Draw vertical edges
        for r in range(sz):
            for c in range(sz + 1):
                x = top_left_x + c * cell_size
                y1 = top_left_y + r * cell_size
                y2 = y1 + cell_size
                edge = st.v_edges[r][c]

                if edge == LoopFamilyState.EDGE_LINE:
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_LIME), 4, Qt.SolidLine, Qt.RoundCap))
                    painter.drawLine(QPointF(x, y1), QPointF(x, y2))
                elif edge == LoopFamilyState.EDGE_CROSS:
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_CORAL), 2))
                    my = (y1 + y2) / 2
                    painter.drawLine(QPointF(x - 4, my - 4), QPointF(x + 4, my + 4))
                    painter.drawLine(QPointF(x - 4, my + 4), QPointF(x + 4, my - 4))
                else:
                    painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1, Qt.DotLine))
                    painter.drawLine(QPointF(x, y1), QPointF(x, y2))

        # Draw grid vertex dots
        painter.setBrush(QBrush(QColor(ChalkTheme.FG_CHALK_WHITE)))
        painter.setPen(Qt.NoPen)
        for r in range(sz + 1):
            for c in range(sz + 1):
                vx = top_left_x + c * cell_size
                vy = top_left_y + r * cell_size
                painter.drawEllipse(QPointF(vx, vy), 3.5, 3.5)

    def mousePressEvent(self, event):
        if self.mode != InteractionMode.PLAYBACK:
            # Simple click toggle for clues in draft mode
            w, h = self.width(), self.height()
            sz = self.state.size
            margin = 40
            board_dim = min(w - 2 * margin, h - 2 * margin)
            cell_size = board_dim / sz
            top_left_x = (w - board_dim) / 2
            top_left_y = (h - board_dim) / 2

            pos = event.position()
            c = int((pos.x() - top_left_x) // cell_size)
            r = int((pos.y() - top_left_y) // cell_size)

            if 0 <= r < sz and 0 <= c < sz:
                curr = self.state.cell_clues[r][c]
                if event.button() == Qt.LeftButton:
                    self.state.cell_clues[r][c] = (curr + 1) % 4 if curr is not None else 0
                elif event.button() == Qt.RightButton:
                    self.state.cell_clues[r][c] = None

                self.current_step = None
                self.state_modified.emit()
                self.update()
