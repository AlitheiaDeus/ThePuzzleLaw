"""
canvas.py - Interactive QPainter viewport for the Unruly binary puzzle.
Renders alternating Pastel Sky / Pastel Peach tokens and edge constraint symbols.
"""

from typing import Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode, SolverStep
from ...theme import ChalkTheme
from .state import UnrulyState


class UnrulyCanvas(BasePuzzleCanvas):
    """Interactive viewport for Unruly binary puzzle."""

    def __init__(self, initial_state: UnrulyState):
        super().__init__()
        self.state = initial_state
        self.edit_tool: str = "paint"  # "paint", "edge_equal", "edge_opposite"
        self.current_step = SolverStep(
            state=self.state,
            action_desc="Edit Mode: Left-Click cell to cycle Sky / Peach / Empty.",
        )

    def _grid_geometry(self) -> Tuple[float, float, float]:
        margin = 40.0
        avail_w = self.width() - margin * 2
        avail_h = self.height() - margin * 2
        dim = self.state.grid_size
        cell_size = min(avail_w, avail_h) / dim
        board_size = cell_size * dim
        ox = (self.width() - board_size) / 2
        oy = (self.height() - board_size) / 2
        return ox, oy, cell_size

    def _cell_rect(self, r: int, c: int) -> QRectF:
        ox, oy, cell_size = self._grid_geometry()
        pad = 2.0
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
        ox, oy, cell_size = self._grid_geometry()

        c = int((pos.x() - ox) // cell_size)
        r = int((pos.y() - oy) // cell_size)

        if not (0 <= r < dim and 0 <= c < dim):
            return

        if self.edit_tool == "paint":
            # Cycle cell state: Empty -> Color A -> Color B -> Empty
            self.state.board[r][c] = (self.state.board[r][c] + 1) % 3
            self.state_modified.emit()
            self.update()
        else:
            # Detect which edge was clicked
            cx = ox + c * cell_size
            cy = oy + r * cell_size
            dx = pos.x() - cx
            dy = pos.y() - cy
            dist_top, dist_bottom = dy, cell_size - dy
            dist_left, dist_right = dx, cell_size - dx
            min_dist = min(dist_top, dist_bottom, dist_left, dist_right)

            nr, nc = -1, -1
            if min_dist == dist_top and r > 0:
                nr, nc = r - 1, c
            elif min_dist == dist_bottom and r < dim - 1:
                nr, nc = r + 1, c
            elif min_dist == dist_left and c > 0:
                nr, nc = r, c - 1
            elif min_dist == dist_right and c < dim - 1:
                nr, nc = r, c + 1

            if nr != -1 and nc != -1:
                p1 = f"{min(r, nr)},{min(c, nc)}" if (r, c) < (nr, nc) else f"{nr},{nc}"
                p2 = f"{max(r, nr)},{max(c, nc)}" if (r, c) < (nr, nc) else f"{r},{c}"
                key = f"{p1}-{p2}"
                constraint_type = "equal" if self.edit_tool == "edge_equal" else "opposite"

                if key in self.state.edge_constraints and self.state.edge_constraints[key] == constraint_type:
                    del self.state.edge_constraints[key]
                else:
                    self.state.edge_constraints[key] = constraint_type

                self.state_modified.emit()
                self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        render_state: UnrulyState = self.current_step.state if self.current_step else self.state
        highlights = self.current_step.highlights if self.current_step else {}
        dim = render_state.grid_size
        ox, oy, cell_size = self._grid_geometry()

        # Board background
        board_rect = QRectF(ox - 6, oy - 6, cell_size * dim + 12, cell_size * dim + 12)
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 2))
        painter.setBrush(QColor(ChalkTheme.BG_SLATE_GREEN))
        painter.drawRoundedRect(board_rect, 8, 8)

        # Draw cells
        for r in range(dim):
            for c in range(dim):
                rect = self._cell_rect(r, c)
                val = render_state.board[r][c]

                if val == UnrulyState.COLOR_A:
                    painter.setPen(QPen(QColor(ChalkTheme.PASTEL_SKY), 1.5))
                    painter.setBrush(QColor(ChalkTheme.PASTEL_SKY))
                    painter.drawRoundedRect(rect, 4, 4)
                elif val == UnrulyState.COLOR_B:
                    painter.setPen(QPen(QColor(ChalkTheme.PASTEL_PEACH), 1.5))
                    painter.setBrush(QColor(ChalkTheme.PASTEL_PEACH))
                    painter.drawRoundedRect(rect, 4, 4)
                else:
                    # Empty
                    painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1))
                    painter.setBrush(QColor(ChalkTheme.BG_BOARD_RAISED))
                    painter.drawRoundedRect(rect, 4, 4)

                # Playback highlight
                if self.mode == InteractionMode.PLAYBACK:
                    if highlights.get("r") == r and highlights.get("c") == c:
                        ChalkTheme.draw_neon_rect(painter, rect, ChalkTheme.NEON_LIME, radius=4, glow_width=6)

        # Draw edge constraints
        for key, constraint in render_state.edge_constraints.items():
            try:
                p1, p2 = key.split("-")
                r1, c1 = map(int, p1.split(","))
                r2, c2 = map(int, p2.split(","))
                rect1 = self._cell_rect(r1, c1)
                rect2 = self._cell_rect(r2, c2)
                mid_x = (rect1.center().x() + rect2.center().x()) / 2
                mid_y = (rect1.center().y() + rect2.center().y()) / 2

                symbol = "=" if constraint == "equal" else "×"
                sym_color = ChalkTheme.NEON_CYAN if constraint == "equal" else ChalkTheme.NEON_CORAL
                painter.setPen(QColor(sym_color))
                font_sz = max(10, int(cell_size * 0.35))
                painter.setFont(QFont("Consolas", font_sz, QFont.Bold))
                sym_rect = QRectF(mid_x - 12, mid_y - 12, 24, 24)
                painter.drawText(sym_rect, Qt.AlignCenter, symbol)
            except Exception:
                pass
