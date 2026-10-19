"""
canvas.py - Interactive QPainter canvas for Flow Free & Numberlink.
Renders chalkboard grid, glowing pastel endpoints, and connected paths.
"""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode
from ...theme import ChalkTheme
from .state import FlowState


class FlowCanvas(BasePuzzleCanvas):
    """Canvas for transcribing endpoints and visualizing continuous path flows."""

    FLOW_COLORS = {
        FlowState.COLOR_MINT: QColor(ChalkTheme.PASTEL_MINT),
        FlowState.COLOR_LAVENDER: QColor(ChalkTheme.PASTEL_LAVENDER),
        FlowState.COLOR_PEACH: QColor(ChalkTheme.PASTEL_PEACH),
        FlowState.COLOR_SKY: QColor(ChalkTheme.PASTEL_SKY),
        FlowState.COLOR_CORAL: QColor(ChalkTheme.NEON_CORAL),
    }

    def __init__(self, initial_state: FlowState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state: FlowState = initial_state
        self.active_color = FlowState.COLOR_MINT

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(ChalkTheme.BG_CHALK_BLACK))

        st = self.state if self.mode == InteractionMode.EDIT or not self.current_step else self.current_step.state
        if not isinstance(st, FlowState):
            st = self.state

        sz = st.grid_size
        margin = 32
        board_dim = min(w - 2 * margin, h - 2 * margin)
        cell_size = board_dim / sz
        top_left_x = (w - board_dim) / 2
        top_left_y = (h - board_dim) / 2

        # Draw grid
        for r in range(sz):
            for c in range(sz):
                rect = QRectF(top_left_x + c * cell_size, top_left_y + r * cell_size, cell_size, cell_size)
                painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1))
                painter.fillRect(rect, QColor(ChalkTheme.BG_SLATE_GREEN))
                painter.drawRect(rect)

                cid = st.board[r][c]
                if cid in self.FLOW_COLORS:
                    color = self.FLOW_COLORS[cid]
                    # Check if this cell is an endpoint
                    is_endpoint = False
                    for ep_list in st.endpoints.values():
                        if [r, c] in ep_list:
                            is_endpoint = True
                            break

                    center = rect.center()
                    radius = cell_size * 0.38 if is_endpoint else cell_size * 0.25
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(color))
                    painter.drawEllipse(center, radius, radius)

                    if is_endpoint:
                        painter.setPen(QPen(QColor("#FFFFFF"), 2))
                        painter.setBrush(Qt.NoBrush)
                        painter.drawEllipse(center, radius * 0.45, radius * 0.45)

        # Outer border
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_WHITE), 2))
        painter.drawRect(QRectF(top_left_x, top_left_y, board_dim, board_dim))

    def mousePressEvent(self, event):
        if self.mode != InteractionMode.PLAYBACK:
            w, h = self.width(), self.height()
            sz = self.state.grid_size
            margin = 32
            board_dim = min(w - 2 * margin, h - 2 * margin)
            cell_size = board_dim / sz
            top_left_x = (w - board_dim) / 2
            top_left_y = (h - board_dim) / 2

            pos = event.position()
            c = int((pos.x() - top_left_x) // cell_size)
            r = int((pos.y() - top_left_y) // cell_size)

            if 0 <= r < sz and 0 <= c < sz:
                if event.button() == Qt.LeftButton:
                    self.state.board[r][c] = (
                        self.active_color if self.state.board[r][c] == FlowState.EMPTY else FlowState.EMPTY
                    )
                elif event.button() == Qt.RightButton:
                    self.state.board[r][c] = FlowState.EMPTY

                self.current_step = None
                self.state_modified.emit()
                self.update()
