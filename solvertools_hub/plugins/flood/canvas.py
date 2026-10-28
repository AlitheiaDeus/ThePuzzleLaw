"""
canvas.py - Interactive QPainter chalkboard canvas for the Flood puzzle.
Renders an n x m grid of pastel/neon tiles with anchor badge, glowing boundary frontiers,
color brush painting, keyboard navigation, and solution step highlights.
"""

from typing import Optional, Set, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPainterPath,
    QPen,
)

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode, SolverStep
from ...theme import ChalkTheme
from .state import FloodState


class FloodCanvas(BasePuzzleCanvas):
    """Interactive viewport for Flood puzzle editing and playback scrubbing."""

    def __init__(self, initial_state: FloodState):
        super().__init__()
        self.state = initial_state
        self.selected_cell: Optional[Tuple[int, int]] = (0, 0)
        self.active_brush_color: Optional[int] = None  # None = cycle mode, int = paint brush
        self.current_step: Optional[SolverStep] = None
        self._mouse_pressed: bool = False

    def set_mode(self, mode: InteractionMode) -> None:
        """Sets the canvas mode (EDIT vs. PLAYBACK) and clears transient playback step."""
        super().set_mode(mode)
        if mode == InteractionMode.EDIT:
            self.current_step = None
        self.update()

    def _grid_geometry(
        self, rows: int, cols: int
    ) -> Tuple[float, float, float, float, float]:
        """
        Calculates board geometry preserving square cells centered in viewport.
        Returns: (start_x, start_y, cell_size, board_w, board_h)
        """
        margin = 30.0
        avail_w = max(50.0, self.width() - margin * 2)
        avail_h = max(50.0, self.height() - margin * 2)

        cell_size = min(avail_w / cols, avail_h / rows)
        cell_size = max(8.0, min(cell_size, 64.0))

        board_w = cell_size * cols
        board_h = cell_size * rows
        start_x = (self.width() - board_w) / 2.0
        start_y = (self.height() - board_h) / 2.0

        return start_x, start_y, cell_size, board_w, board_h

    def _pos_to_cell(self, pos: QPointF, rows: int, cols: int) -> Optional[Tuple[int, int]]:
        """Maps canvas pixel position to (row, col) grid coordinates."""
        start_x, start_y, cell_size, board_w, board_h = self._grid_geometry(rows, cols)
        if (
            pos.x() < start_x
            or pos.x() >= start_x + board_w
            or pos.y() < start_y
            or pos.y() >= start_y + board_h
        ):
            return None

        c = int((pos.x() - start_x) / cell_size)
        r = int((pos.y() - start_y) / cell_size)
        if 0 <= r < rows and 0 <= c < cols:
            return r, c
        return None

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.mode != InteractionMode.EDIT:
            return

        render_state: FloodState = self.get_render_state()
        cell = self._pos_to_cell(event.position(), render_state.rows, render_state.cols)
        if cell is None:
            return

        self._mouse_pressed = True
        self.selected_cell = cell
        r, c = cell

        # Invariant: clear active playback step on state modification
        self.current_step = None

        if event.button() == Qt.LeftButton:
            if self.active_brush_color is not None:
                self.state.grid[r][c] = self.active_brush_color
            else:
                # Cycle forward
                self.state.grid[r][c] = (self.state.grid[r][c] + 1) % self.state.num_colors
        elif event.button() == Qt.RightButton:
            # Cycle reverse
            self.state.grid[r][c] = (self.state.grid[r][c] - 1) % self.state.num_colors

        self.state_modified.emit()
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self.mode != InteractionMode.EDIT or not self._mouse_pressed:
            return

        render_state: FloodState = self.get_render_state()
        cell = self._pos_to_cell(event.position(), render_state.rows, render_state.cols)
        if cell is not None and self.active_brush_color is not None:
            r, c = cell
            if self.state.grid[r][c] != self.active_brush_color:
                self.current_step = None
                self.state.grid[r][c] = self.active_brush_color
                self.selected_cell = cell
                self.state_modified.emit()
                self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        self._mouse_pressed = False

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if self.mode != InteractionMode.EDIT or self.selected_cell is None:
            super().keyPressEvent(event)
            return

        r, c = self.selected_cell
        render_state: FloodState = self.get_render_state()

        if event.key() == Qt.Key_Up:
            self.selected_cell = (max(0, r - 1), c)
            self.update()
        elif event.key() == Qt.Key_Down:
            self.selected_cell = (min(render_state.rows - 1, r + 1), c)
            self.update()
        elif event.key() == Qt.Key_Left:
            self.selected_cell = (r, max(0, c - 1))
            self.update()
        elif event.key() == Qt.Key_Right:
            self.selected_cell = (r, min(render_state.cols - 1, c + 1))
            self.update()
        elif event.key() in (Qt.Key_Space, Qt.Key_Return):
            self.current_step = None
            self.state.grid[r][c] = (self.state.grid[r][c] + 1) % self.state.num_colors
            self.state_modified.emit()
            self.update()
        elif Qt.Key_1 <= event.key() <= Qt.Key_9:
            num = event.key() - Qt.Key_1
            if num < self.state.num_colors:
                self.current_step = None
                self.state.grid[r][c] = num
                self.state_modified.emit()
                self.update()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 1. Background slate surface
        painter.fillRect(self.rect(), QColor(ChalkTheme.BG_CHALK_BLACK))

        # Always read render_state safely via BasePuzzleCanvas contract
        render_state: FloodState = self.get_render_state()
        if not render_state.grid or not render_state.grid[0]:
            return

        rows = render_state.rows
        cols = render_state.cols
        start_x, start_y, cell_size, board_w, board_h = self._grid_geometry(rows, cols)

        # 2. Outer chalkboard frame
        board_rect = QRectF(start_x - 6, start_y - 6, board_w + 12, board_h + 12)
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1.5))
        painter.setBrush(QColor(ChalkTheme.BG_SLATE_GREEN))
        painter.drawRoundedRect(board_rect, 8.0, 8.0)

        # 3. Determine flooded region and playback highlights
        flooded_cells = render_state.get_flooded_region()
        newly_captured: Set[Tuple[int, int]] = set()
        if self.current_step and "newly_captured" in self.current_step.highlights:
            newly_captured = set(tuple(p) for p in self.current_step.highlights["newly_captured"])

        # 4. Render individual tiles
        radius = max(2.0, min(6.0, cell_size * 0.18))
        for r in range(rows):
            for c in range(cols):
                color_idx = render_state.grid[r][c]
                hex_color = render_state.get_color_hex(color_idx)
                tile_rect = QRectF(
                    start_x + c * cell_size + 1.5,
                    start_y + r * cell_size + 1.5,
                    cell_size - 3.0,
                    cell_size - 3.0,
                )

                base_qcolor = QColor(hex_color)

                # Dim unflooded cells slightly during playback to emphasize player territory
                if self.mode == InteractionMode.PLAYBACK and (r, c) not in flooded_cells:
                    base_qcolor.setAlpha(165)

                painter.setPen(Qt.NoPen)
                painter.setBrush(base_qcolor)
                painter.drawRoundedRect(tile_rect, radius, radius)

                # Soft internal chalk bevel
                painter.setPen(QPen(QColor(255, 255, 255, 30), 1.0))
                painter.setBrush(Qt.NoBrush)
                painter.drawRoundedRect(tile_rect, radius, radius)

                # Newly captured pulse glow during playback
                if (r, c) in newly_captured:
                    painter.setPen(QPen(QColor(ChalkTheme.NEON_CYAN), 2.2))
                    painter.drawRoundedRect(tile_rect, radius, radius)

                # Selected cursor marker in EDIT mode
                if (
                    self.mode == InteractionMode.EDIT
                    and self.selected_cell == (r, c)
                ):
                    painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_WHITE), 2.0))
                    painter.drawRoundedRect(tile_rect.adjusted(-1, -1, 1, 1), radius + 1, radius + 1)

        # 5. Anchor badge at (0, 0)
        anchor_rect = QRectF(
            start_x + 1.5,
            start_y + 1.5,
            cell_size - 3.0,
            cell_size - 3.0,
        )
        painter.setPen(QPen(QColor("#FFFFFF"), 2.0))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(anchor_rect.center(), cell_size * 0.28, cell_size * 0.28)

        # Subtle anchor symbol or dot
        painter.setFont(QFont("Segoe UI Emoji", int(max(9, cell_size * 0.38))))
        painter.setPen(QColor("#FFFFFF"))
        painter.drawText(anchor_rect, Qt.AlignCenter, "⚓")

        # 6. Flooded territory border contour
        # Draw a subtle chalk outline along the perimeter of the active flooded region
        border_pen = QPen(QColor(255, 255, 255, 120), 2.0)
        painter.setPen(border_pen)
        for r, c in flooded_cells:
            cx = start_x + c * cell_size
            cy = start_y + r * cell_size
            # Check orthogonal neighbors
            if (r - 1, c) not in flooded_cells:  # Top border
                painter.drawLine(QPointF(cx, cy), QPointF(cx + cell_size, cy))
            if (r + 1, c) not in flooded_cells:  # Bottom border
                painter.drawLine(QPointF(cx, cy + cell_size), QPointF(cx + cell_size, cy + cell_size))
            if (r, c - 1) not in flooded_cells:  # Left border
                painter.drawLine(QPointF(cx, cy), QPointF(cx, cy + cell_size))
            if (r, c + 1) not in flooded_cells:  # Right border
                painter.drawLine(QPointF(cx + cell_size, cy), QPointF(cx + cell_size, cy + cell_size))
