"""
canvas.py - Interactive QPainter viewport for Liquid Sorter Pro.
Renders variable-height rounded test tubes on a chemistry chalkboard bench.
Supports direct slot-based painting/erasing, hovering segment visual warnings,
dedicated tube selection, capacity cycling, and neon pouring playback highlights.
"""

from typing import Dict, Optional, Tuple

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent, QPainter, QPen, QWheelEvent

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode, SolverStep
from ...theme import ChalkTheme
from .state import SandTubeState


class SandTubeCanvas(BasePuzzleCanvas):
    """Interactive viewport for test tubes with direct slot painting and variable capacities."""

    tube_selected = Signal(int)

    def __init__(self, initial_state: SandTubeState):
        super().__init__()
        self.state = initial_state
        self.active_brush_color: Optional[int] = None  # None = Select Tube mode
        self.selected_tube_idx: int = 0
        self.setMouseTracking(True)
        self.current_step: Optional[SolverStep] = None

    def select_tube(self, idx: int) -> None:
        if 0 <= idx < len(self.state.tubes):
            self.selected_tube_idx = idx
            self.tube_selected.emit(idx)
            self.update()

    def _tube_geometry(self, idx: int, total: int, render_state: SandTubeState) -> QRectF:
        """
        Calculates bounding rectangle for a tube grounded on a workbench baseline.
        Tube height is proportional to its individual capacity.
        """
        w = max(300.0, float(self.width()))
        h = max(200.0, float(self.height()))

        tube_w = min(64.0, max(30.0, (w - 80.0) / max(1, total) - 14.0))
        spacing = 16.0
        total_span = total * (tube_w + spacing) - spacing
        start_x = (w - total_span) / 2.0

        max_cap = max(render_state.capacities) if render_state.capacities else 4
        baseline_y = h - 85.0
        unit_h = min(42.0, max(18.0, (h - 180.0) / max(1, max_cap)))

        cap = render_state.capacities[idx] if idx < len(render_state.capacities) else 4
        tube_h = cap * unit_h + 16.0
        tube_x = start_x + idx * (tube_w + spacing)
        tube_y = baseline_y - tube_h

        return QRectF(tube_x, tube_y, tube_w, tube_h)

    def _hit_test(self, pos: QPointF, render_state: SandTubeState) -> Tuple[Optional[int], Optional[int], str]:
        """
        Determines the clicked tube index, slot index, and region ('lip', 'slot', 'label', or 'outside').
        Slot 0 is the bottom slot; slot cap - 1 is the top slot.
        """
        total = len(render_state.tubes)
        h = max(200.0, float(self.height()))
        baseline_y = h - 85.0
        max_cap = max(render_state.capacities) if render_state.capacities else 4
        unit_h = min(42.0, max(18.0, (h - 180.0) / max(1, max_cap)))

        for idx in range(total):
            rect = self._tube_geometry(idx, total, render_state)
            cap = render_state.capacities[idx] if idx < len(render_state.capacities) else 4

            # Check horizontal bounds with padding
            if rect.left() - 4.0 <= pos.x() <= rect.right() + 4.0:
                # 1. Label region below workbench
                if baseline_y <= pos.y() <= baseline_y + 45.0:
                    return idx, None, "label"

                # 2. Lip and capacity badge above tube mouth
                if rect.top() - 30.0 <= pos.y() <= rect.top() + 6.0:
                    return idx, None, "lip"

                # 3. Inside tube slots
                if rect.top() + 6.0 < pos.y() <= baseline_y:
                    y_offset = (baseline_y - 6.0) - pos.y()
                    slot = int(y_offset / unit_h)
                    if 0 <= slot < cap:
                        return idx, slot, "slot"
                    elif slot >= cap:
                        return idx, None, "lip"
                    else:
                        return idx, 0, "slot"

        return None, None, "outside"

    def _cycle_tube_capacity(self, tube_idx: int) -> None:
        """Helper to cycle capacity of a tube between 2 and 6."""
        if 0 <= tube_idx < len(self.state.capacities):
            cap = self.state.capacities[tube_idx]
            new_cap = 2 if cap >= 6 else cap + 1
            self.state.capacities[tube_idx] = new_cap
            if len(self.state.tubes[tube_idx]) > new_cap:
                del self.state.tubes[tube_idx][new_cap:]
            self.current_step = None
            self.state_modified.emit()
            self.update()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self.mode != InteractionMode.EDIT:
            return

        self.current_step = None
        pos = event.position()
        tube_idx, slot_idx, region = self._hit_test(pos, self.state)
        if tube_idx is not None:
            self.select_tube(tube_idx)

            # Lip or label region: purely selects tube (and supports middle click capacity cycle)
            if region in ("lip", "label"):
                if event.button() == Qt.MiddleButton:
                    self._cycle_tube_capacity(tube_idx)
                return

            # Slot region
            if region == "slot" and slot_idx is not None:
                if event.button() == Qt.MiddleButton:
                    self._cycle_tube_capacity(tube_idx)
                    return

                if self.active_brush_color is None:
                    # Select Mode: clicking slot selects the tube without inserting any color
                    return

                if event.button() == Qt.LeftButton:
                    current_col = self.state.get_slot(tube_idx, slot_idx)
                    if current_col == self.active_brush_color:
                        # Clicking same color toggles it off
                        self.state.set_slot(tube_idx, slot_idx, None)
                    else:
                        self.state.set_slot(tube_idx, slot_idx, self.active_brush_color)
                    self.state_modified.emit()
                    self.update()

                elif event.button() == Qt.RightButton:
                    # Right-click erases slot
                    self.state.set_slot(tube_idx, slot_idx, None)
                    self.state_modified.emit()
                    self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Supports drag-painting across slots while left mouse button is held."""
        if self.mode == InteractionMode.EDIT and (event.buttons() & Qt.LeftButton) and self.active_brush_color is not None:
            pos = event.position()
            tube_idx, slot_idx, region = self._hit_test(pos, self.state)
            if tube_idx is not None and region == "slot" and slot_idx is not None:
                if self.state.get_slot(tube_idx, slot_idx) != self.active_brush_color:
                    self.state.set_slot(tube_idx, slot_idx, self.active_brush_color)
                    self.select_tube(tube_idx)
                    self.state_modified.emit()
                    self.update()

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Scrolling the mouse wheel over any tube adjusts its capacity up or down."""
        if self.mode != InteractionMode.EDIT:
            return
        pos = event.position()
        tube_idx, _, _ = self._hit_test(pos, self.state)
        if tube_idx is not None:
            delta = event.angleDelta().y()
            cur_cap = self.state.capacities[tube_idx]
            if delta > 0 and cur_cap < 8:
                new_cap = cur_cap + 1
            elif delta < 0 and cur_cap > 1:
                new_cap = cur_cap - 1
            else:
                return
            self.state.capacities[tube_idx] = new_cap
            if len(self.state.tubes[tube_idx]) > new_cap:
                del self.state.tubes[tube_idx][new_cap:]
            self.select_tube(tube_idx)
            self.state_modified.emit()
            self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        render_state: SandTubeState = self.get_render_state()  # type: ignore
        highlights = self.current_step.highlights if self.current_step else {}
        total = len(render_state.tubes)
        if total == 0:
            return

        w = float(self.width())
        h = float(self.height())
        baseline_y = h - 85.0
        max_cap = max(render_state.capacities) if render_state.capacities else 4
        unit_h = min(42.0, max(18.0, (h - 180.0) / max(1, max_cap)))

        # 1. Draw Workbench Table Shelf
        shelf_pen = QPen(QColor(ChalkTheme.BORDER_MUTED), 2)
        painter.setPen(shelf_pen)
        painter.drawLine(QPointF(20.0, baseline_y + 2.0), QPointF(w - 20.0, baseline_y + 2.0))

        # Subtle shelf thickness line
        painter.setPen(QPen(QColor(ChalkTheme.BG_PANEL_ALT), 4))
        painter.drawLine(QPointF(20.0, baseline_y + 5.0), QPointF(w - 20.0, baseline_y + 5.0))

        # 2. Render Each Tube
        for idx in range(total):
            rect = self._tube_geometry(idx, total, render_state)
            cap = render_state.capacities[idx] if idx < len(render_state.capacities) else 4
            is_selected = (self.mode == InteractionMode.EDIT and idx == self.selected_tube_idx)

            # Render individual slots (from bottom slot 0 to top slot cap - 1)
            filled_count = 0
            for slot_idx in range(cap):
                seg_y = baseline_y - 6.0 - (slot_idx + 1) * unit_h
                seg_rect = QRectF(rect.left() + 4.0, seg_y, rect.width() - 8.0, unit_h - 2.0)
                color_id = render_state.get_slot(idx, slot_idx)

                if color_id is None:
                    # Draw ghost slot marker in edit mode
                    if self.mode == InteractionMode.EDIT:
                        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 1.0, Qt.DotLine))
                        painter.setBrush(QColor(ChalkTheme.BG_SLATE_GREEN))
                        painter.drawRoundedRect(seg_rect, 3.0, 3.0)
                else:
                    filled_count += 1
                    hex_col = ChalkTheme.get_color(color_id)
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QColor(hex_col))
                    painter.drawRoundedRect(seg_rect, 4.0, 4.0)

                    # Contrast-optimized color number inside segment for instant recognition
                    text_col = ChalkTheme.get_contrast_text_color(hex_col)
                    painter.setPen(QColor(text_col))
                    font_size = max(8, min(12, int(unit_h * 0.45)))
                    painter.setFont(QFont("Consolas", font_size, QFont.Bold))
                    painter.drawText(seg_rect, Qt.AlignCenter, str(color_id + 1))

                    # Check if this segment is floating (any slot below it is None)
                    is_floating = any(render_state.get_slot(idx, k) is None for k in range(slot_idx))
                    if is_floating and self.mode == InteractionMode.EDIT:
                        painter.setPen(QPen(QColor(ChalkTheme.NEON_AMBER), 2.0, Qt.DashLine))
                        painter.setBrush(Qt.NoBrush)
                        painter.drawRoundedRect(seg_rect, 4.0, 4.0)

            # Draw Glass Test Tube Contour
            glass_col = ChalkTheme.NEON_CYAN if is_selected else ChalkTheme.FG_CHALK_WHITE
            glass_width = 3.0 if is_selected else 2.2
            painter.setPen(QPen(QColor(glass_col), glass_width))
            painter.setBrush(Qt.NoBrush)

            # Tube Lip (slight flare at top)
            lip_rect = QRectF(rect.left() - 3.0, rect.top(), rect.width() + 6.0, 6.0)
            painter.drawRoundedRect(lip_rect, 3.0, 3.0)

            # Main tube body (open top, rounded bottom)
            painter.drawRoundedRect(rect, 10.0, 10.0)

            # Capacity lip badge above mouth
            badge_rect = QRectF(rect.left() - 8.0, rect.top() - 24.0, rect.width() + 16.0, 18.0)
            clean_tube = [c for c in render_state.tubes[idx] if c is not None] if idx < len(render_state.tubes) else []
            is_monochrome_full = (len(clean_tube) == cap and len(set(clean_tube)) == 1)
            is_full = (len(clean_tube) == cap)

            if is_monochrome_full:
                badge_col = ChalkTheme.NEON_LIME
            elif is_full:
                badge_col = ChalkTheme.NEON_AMBER
            elif not clean_tube:
                badge_col = ChalkTheme.FG_CHALK_MUTED
            else:
                badge_col = ChalkTheme.FG_CHALK_WHITE

            painter.setPen(QColor(badge_col))
            painter.setFont(QFont("Consolas", 9, QFont.Bold))
            painter.drawText(badge_rect, Qt.AlignCenter, f"{filled_count}/{cap}")

            # Tube index label below workbench
            lbl_rect = QRectF(rect.left() - 8.0, baseline_y + 10.0, rect.width() + 16.0, 22.0)
            painter.setPen(QColor(ChalkTheme.NEON_CYAN if is_selected else ChalkTheme.FG_CHALK_MUTED))
            painter.setFont(QFont("Consolas", 10, QFont.Bold))
            painter.drawText(lbl_rect, Qt.AlignCenter, f"#{idx + 1}")

            # Selection marker underline in Edit Mode
            if is_selected:
                painter.setPen(QPen(QColor(ChalkTheme.NEON_CYAN), 2.0))
                painter.drawLine(
                    QPointF(rect.left(), baseline_y + 32.0),
                    QPointF(rect.right(), baseline_y + 32.0),
                )

            # Playback Neon Highlights
            if self.mode == InteractionMode.PLAYBACK:
                if highlights.get("src") == idx:
                    ChalkTheme.draw_neon_rect(painter, rect, ChalkTheme.NEON_CYAN, radius=10.0)
                    tag_rect = QRectF(rect.left() - 10.0, rect.top() - 44.0, rect.width() + 20.0, 18.0)
                    painter.setPen(QColor(ChalkTheme.NEON_CYAN))
                    painter.setFont(QFont("Consolas", 9, QFont.Bold))
                    painter.drawText(tag_rect, Qt.AlignCenter, "POUR")
                elif highlights.get("dst") == idx:
                    ChalkTheme.draw_neon_rect(painter, rect, ChalkTheme.NEON_LIME, radius=10.0)
                    tag_rect = QRectF(rect.left() - 10.0, rect.top() - 44.0, rect.width() + 20.0, 18.0)
                    painter.setPen(QColor(ChalkTheme.NEON_LIME))
                    painter.setFont(QFont("Consolas", 9, QFont.Bold))
                    painter.drawText(tag_rect, Qt.AlignCenter, "RECV")

        # Global Solved Glow
        if render_state.is_solved():
            solved_rect = QRectF(10.0, 10.0, w - 20.0, baseline_y + 40.0)
            painter.setPen(QPen(QColor(ChalkTheme.NEON_LIME), 1.5, Qt.DashLine))
            painter.setBrush(Qt.NoBrush)
            painter.drawRoundedRect(solved_rect, 8.0, 8.0)
