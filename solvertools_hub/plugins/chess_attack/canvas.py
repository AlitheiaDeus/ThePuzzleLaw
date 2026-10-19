"""
canvas.py - Interactive QPainter canvas for Chess Attack & Tactical Zones.
Renders zoned grid territories, chess glyphs, and threat heatmaps.
"""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode
from ...theme import ChalkTheme
from .state import ChessAttackState


class ChessAttackCanvas(BasePuzzleCanvas):
    """Canvas for painting zones and placing tactical chess pieces."""

    ZONE_COLORS = [
        QColor(168, 230, 207, 45),  # Pastel Mint
        QColor(215, 189, 226, 45),  # Pastel Lavender
        QColor(250, 215, 160, 45),  # Pastel Peach
        QColor(169, 204, 227, 45),  # Pastel Sky
        QColor(245, 183, 177, 45),  # Pastel Rose
        QColor(163, 228, 215, 45),  # Pastel Aqua
        QColor(249, 231, 159, 45),  # Pastel Lemon
        QColor(210, 180, 222, 45),  # Pastel Violet
    ]

    def __init__(self, initial_state: ChessAttackState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state: ChessAttackState = initial_state
        self.active_brush_piece = ChessAttackState.PIECE_SUPERKING
        self.active_zone_id = 0

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(ChalkTheme.BG_CHALK_BLACK))

        st = self.state if self.mode == InteractionMode.EDIT or not self.current_step else self.current_step.state
        if not isinstance(st, ChessAttackState):
            st = self.state

        sz = st.board_size
        margin = 32
        board_dim = min(w - 2 * margin, h - 2 * margin)
        cell_size = board_dim / sz
        top_left_x = (w - board_dim) / 2
        top_left_y = (h - board_dim) / 2

        # Draw cells & zones
        for r in range(sz):
            for c in range(sz):
                rect = QRectF(top_left_x + c * cell_size, top_left_y + r * cell_size, cell_size, cell_size)

                # Zone background
                z_id = st.zones[r][c] % len(self.ZONE_COLORS)
                painter.fillRect(rect, self.ZONE_COLORS[z_id])

                # Cell border
                painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1))
                painter.drawRect(rect)

                # Piece glyph
                p_id = st.board[r][c]
                glyph = ChessAttackState.PIECE_GLYPHS.get(p_id, "")
                if glyph:
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_CYAN)))
                    font = painter.font()
                    font.setPointSize(int(cell_size * 0.55))
                    painter.setFont(font)
                    painter.drawText(rect, Qt.AlignCenter, glyph)

        # Highlight if playback
        if self.current_step and self.current_step.highlights:
            hl = self.current_step.highlights.get("cell")
            if hl:
                hr, hc = hl
                hl_rect = QRectF(top_left_x + hc * cell_size, top_left_y + hr * cell_size, cell_size, cell_size)
                painter.setPen(QPen(QColor(ChalkTheme.NEON_LIME), 2))
                painter.drawRect(hl_rect)

        # Chalkboard outer frame
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_WHITE), 2))
        painter.drawRect(QRectF(top_left_x, top_left_y, board_dim, board_dim))

    def mousePressEvent(self, event):
        if self.mode != InteractionMode.PLAYBACK:
            # Click toggles piece
            w, h = self.width(), self.height()
            sz = self.state.board_size
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
                        self.active_brush_piece if self.state.board[r][c] == ChessAttackState.EMPTY else ChessAttackState.EMPTY
                    )
                elif event.button() == Qt.RightButton:
                    self.state.zones[r][c] = (self.state.zones[r][c] + 1) % sz

                self.current_step = None
                self.state_modified.emit()
                self.update()
