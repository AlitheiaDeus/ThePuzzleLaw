"""
canvas.py - Interactive chalkboard terminal & frequency viewer for The Cipher Room.
"""

from typing import Optional

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ...core.base_plugin import BasePuzzleCanvas, InteractionMode
from ...theme import ChalkTheme
from .state import CipherRoomState


class CipherRoomCanvas(BasePuzzleCanvas):
    """Visual terminal and frequency inspector for signal analysis."""

    def __init__(self, initial_state: CipherRoomState, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state: CipherRoomState = initial_state

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QColor(ChalkTheme.BG_CHALK_BLACK))

        st = self.state if self.mode == InteractionMode.EDIT or not self.current_step else self.current_step.state
        if not isinstance(st, CipherRoomState):
            st = self.state

        # Outer terminal frame
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_DUST), 2))
        painter.drawRect(QRectF(20, 20, w - 40, h - 40))

        # Header badge
        painter.setPen(QPen(QColor(ChalkTheme.NEON_CYAN)))
        font = painter.font()
        font.setPointSize(14)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(QRectF(30, 30, w - 60, 30), Qt.AlignLeft, f"CIPHER ROOM :: [{st.cipher_type.upper()}]")

        # Ciphertext display box
        painter.fillRect(QRectF(30, 70, w - 60, 80), QColor(ChalkTheme.BG_BOARD_RAISED))
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_WHITE)))
        font.setPointSize(12)
        font.setBold(False)
        painter.setFont(font)
        painter.drawText(QRectF(40, 75, w - 80, 70), Qt.AlignLeft | Qt.TextWordWrap, f"INPUT:\n{st.ciphertext}")

        # Decoded / Output area
        out_rect = QRectF(30, 170, w - 60, 100)
        painter.fillRect(out_rect, QColor(ChalkTheme.BG_SLATE_GREEN))
        painter.setPen(QPen(QColor(ChalkTheme.NEON_LIME)))
        decoded_text = ""
        if self.current_step and self.current_step.highlights:
            decoded_text = str(self.current_step.highlights.get("decoded", ""))

        msg = f"ANALYSIS / DECODED:\n{decoded_text}" if decoded_text else "STATUS: Ready for analysis. Run solver."
        painter.drawText(QRectF(40, 175, w - 80, 90), Qt.AlignLeft | Qt.TextWordWrap, msg)

        # Bottom status hint
        painter.setPen(QPen(QColor(ChalkTheme.FG_CHALK_MUTED)))
        font.setPointSize(9)
        painter.setFont(font)
        painter.drawText(
            QRectF(30, h - 45, w - 60, 20),
            Qt.AlignLeft,
            "Edit ciphertext via state import/export or preset loaders. (WIP Draft)",
        )
