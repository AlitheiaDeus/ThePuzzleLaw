"""
canvas.py - Interactive QPainter viewport for the Sliding Tile puzzle.
Supports rapid click-to-swap visual transcription in EDIT mode,
and glowing neon playback animations in PLAYBACK mode.
"""

from typing import Optional

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode, SolverStep
from ...theme import ChalkTheme
from .state import SlidingTileState


class SlidingTileCanvas(BasePuzzleCanvas):
    """Interactive viewport for sliding tile board."""

    def __init__(self, initial_state: SlidingTileState):
        super().__init__()
        self.state = initial_state
        self.selected_edit_idx: Optional[int] = None
        self.current_step: Optional[SolverStep] = None

    def _cell_rect(self, idx: int, size: Optional[int] = None) -> QRectF:
        if size is None:
            render_state = self.get_render_state()
            size = getattr(render_state, "size", self.state.size)
        board_dim = min(self.width(), self.height()) - 60
        cell_dim = board_dim / size
        ox = (self.width() - board_dim) / 2
        oy = (self.height() - board_dim) / 2
        r, c = divmod(idx, size)
        return QRectF(ox + c * cell_dim + 4, oy + r * cell_dim + 4, cell_dim - 8, cell_dim - 8)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.mode != InteractionMode.EDIT:
            return

        self.current_step = None
        pos = event.position()
        for idx in range(self.state.size * self.state.size):
            if self._cell_rect(idx).contains(pos):
                if self.selected_edit_idx is None:
                    self.selected_edit_idx = idx
                else:
                    # Swap tiles for fast 1:1 transcription
                    g = self.state.grid
                    g[self.selected_edit_idx], g[idx] = g[idx], g[self.selected_edit_idx]
                    self.selected_edit_idx = None
                    self.state_modified.emit()
                self.update()
                return

        # Click outside deselects
        self.selected_edit_idx = None
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        render_state: SlidingTileState = self.get_render_state()  # type: ignore
        highlights = self.current_step.highlights if self.current_step else {}

        # Draw background container frame
        board_dim = min(self.width(), self.height()) - 50
        ox = (self.width() - board_dim) / 2
        oy = (self.height() - board_dim) / 2
        frame_rect = QRectF(ox, oy, board_dim, board_dim)
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 2))
        painter.setBrush(QColor(ChalkTheme.BG_SLATE_GREEN))
        painter.drawRoundedRect(frame_rect, 10, 10)

        # Draw individual tiles
        for idx, val in enumerate(render_state.grid):
            rect = self._cell_rect(idx)
            if val == 0:
                # Blank tile slot
                painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1.5, Qt.DashLine))
                painter.setBrush(QColor(ChalkTheme.BG_CHALK_BLACK))
                painter.drawRoundedRect(rect, 8, 8)
            else:
                # Numbered tile
                painter.setPen(QPen(QColor(ChalkTheme.PASTEL_MINT), 2))
                painter.setBrush(QColor(ChalkTheme.BG_BOARD_RAISED))
                painter.drawRoundedRect(rect, 8, 8)

                painter.setPen(QColor(ChalkTheme.FG_CHALK_WHITE))
                font_size = max(14, int(rect.height() * 0.38))
                painter.setFont(QFont("Consolas", font_size, QFont.Bold))
                painter.drawText(rect, Qt.AlignCenter, str(val))

            # Neon highlights
            if self.mode == InteractionMode.EDIT and self.selected_edit_idx == idx:
                ChalkTheme.draw_neon_rect(painter, rect, ChalkTheme.NEON_CYAN)
            elif self.mode == InteractionMode.PLAYBACK:
                if highlights.get("moved_idx") == idx:
                    ChalkTheme.draw_neon_rect(painter, rect, ChalkTheme.NEON_LIME)
                elif highlights.get("active_idx") == idx:
                    ChalkTheme.draw_neon_rect(painter, rect, ChalkTheme.NEON_CYAN)
