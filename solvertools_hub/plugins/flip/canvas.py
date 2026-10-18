"""
canvas.py - Interactive QPainter viewport for the Flip / Lights Out puzzle.
Renders illuminated neon tiles, dark chalkboard off-cells, and target press indicators.
Supports direct single-cell toggle (Left-Click) and full neighbor toggle (Right-Click) in EDIT mode.
"""

from typing import Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode, SolverStep
from ...theme import ChalkTheme
from .state import FlipState


class FlipCanvas(BasePuzzleCanvas):
    """Interactive viewport for Flip / Lights Out."""

    def __init__(self, initial_state: FlipState):
        super().__init__()
        self.state = initial_state
        self.current_step = SolverStep(
            state=self.state,
            action_desc="Edit Mode: Left-Click cell to toggle light; Right-Click to simulate actual game press.",
        )

    def _grid_geometry(self) -> Tuple[float, float, float]:
        margin = 40.0
        avail_w = self.width() - margin * 2
        avail_h = self.height() - margin * 2
        cell_size = min(avail_w / self.state.cols, avail_h / self.state.rows)
        board_w = cell_size * self.state.cols
        board_h = cell_size * self.state.rows
        ox = (self.width() - board_w) / 2
        oy = (self.height() - board_h) / 2
        return ox, oy, cell_size

    def _cell_rect(self, r: int, c: int) -> QRectF:
        ox, oy, cell_size = self._grid_geometry()
        pad = 4.0
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
        for r in range(self.state.rows):
            for c in range(self.state.cols):
                if self._cell_rect(r, c).contains(pos):
                    if event.button() == Qt.LeftButton:
                        # Direct cell toggle for fast transcription
                        self.state.grid[r][c] ^= 1
                    elif event.button() == Qt.RightButton:
                        # Real game press (toggles neighbors)
                        self.state.toggle_cell_and_neighbors(r, c)

                    self.state_modified.emit()
                    self.update()
                    return

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        render_state: FlipState = self.current_step.state if self.current_step else self.state
        highlights = self.current_step.highlights if self.current_step else {}

        ox, oy, cell_size = self._grid_geometry()
        board_w = cell_size * render_state.cols
        board_h = cell_size * render_state.rows
        board_rect = QRectF(ox - 8, oy - 8, board_w + 16, board_h + 16)

        # Draw frame background
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 2))
        painter.setBrush(QColor(ChalkTheme.BG_SLATE_GREEN))
        painter.drawRoundedRect(board_rect, 10, 10)

        # Draw individual cells
        for r in range(render_state.rows):
            for c in range(render_state.cols):
                rect = self._cell_rect(r, c)
                is_on = render_state.grid[r][c] == 1

                if is_on:
                    # Light is ON: vibrant pastel cyan with neon glow
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_CYAN), 2))
                    painter.setBrush(QColor(0, 245, 212, 180))
                    painter.drawRoundedRect(rect, 6, 6)
                else:
                    # Light is OFF: dark chalkboard tile
                    painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1))
                    painter.setBrush(QColor(ChalkTheme.BG_BOARD_RAISED))
                    painter.drawRoundedRect(rect, 6, 6)

                # Press target indicator during playback
                if self.mode == InteractionMode.PLAYBACK:
                    press_pos = highlights.get("press")
                    if press_pos == (r, c):
                        ChalkTheme.draw_neon_rect(painter, rect, ChalkTheme.NEON_CORAL, radius=6, glow_width=8)
                        center = rect.center()
                        painter.setPen(Qt.NoPen)
                        painter.setBrush(QColor(ChalkTheme.NEON_CORAL))
                        radius = min(rect.width(), rect.height()) * 0.22
                        painter.drawEllipse(center, radius, radius)
