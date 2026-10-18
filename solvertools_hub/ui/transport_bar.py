"""
transport_bar.py - Unified playback, scrubbing, and solver execution controls.
Provides Play/Pause, Step Prev/Next, Timeline Scrubber, Speed controls, and Action buttons.
"""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from ..theme import ChalkTheme


class TransportBar(QFrame):
    """Unified transport bar for stepping, scrubbing, playback, and triggering solves."""

    playback_solve_requested = Signal()
    instant_solve_requested = Signal()
    reset_edit_requested = Signal()
    scrubbed = Signal(int)
    play_toggled = Signal()
    step_manual = Signal(int)  # delta: -1 or +1
    speed_changed = Signal(int)  # delay in ms

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self._is_playing = False
        self._max_steps = 0
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(8)

        # --- Top Row: Solve Actions & Status ---
        top_row = QHBoxLayout()
        top_row.setSpacing(10)

        self.btn_playback_solve = QPushButton("▶ Playback Solve")
        self.btn_playback_solve.setObjectName("NeonActionBtn")
        self.btn_playback_solve.clicked.connect(self.playback_solve_requested.emit)
        top_row.addWidget(self.btn_playback_solve)

        self.btn_instant_solve = QPushButton("⚡ Instant Solve")
        self.btn_instant_solve.setObjectName("InstantActionBtn")
        self.btn_instant_solve.clicked.connect(self.instant_solve_requested.emit)
        top_row.addWidget(self.btn_instant_solve)

        self.btn_reset = QPushButton("↺ Edit Mode")
        self.btn_reset.clicked.connect(self.reset_edit_requested.emit)
        top_row.addWidget(self.btn_reset)

        self.lbl_status = QLabel("Ready (Edit Mode: Modify or transcribe puzzle)")
        self.lbl_status.setStyleSheet(f"color: {ChalkTheme.FG_CHALK_MUTED}; font-weight: bold;")
        top_row.addWidget(self.lbl_status, stretch=1)

        layout.addLayout(top_row)

        # --- Bottom Row: Scrubber & Playback Controls ---
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(8)

        self.btn_prev = QPushButton("◀ Prev")
        self.btn_prev.setFixedWidth(70)
        self.btn_prev.clicked.connect(lambda: self.step_manual.emit(-1))
        bottom_row.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶ Play")
        self.btn_play.setFixedWidth(80)
        self.btn_play.clicked.connect(self.play_toggled.emit)
        bottom_row.addWidget(self.btn_play)

        self.btn_next = QPushButton("Next ▶")
        self.btn_next.setFixedWidth(70)
        self.btn_next.clicked.connect(lambda: self.step_manual.emit(1))
        bottom_row.addWidget(self.btn_next)

        # Scrubber
        self.scrubber = QSlider(Qt.Horizontal)
        self.scrubber.setRange(0, 0)
        self.scrubber.setValue(0)
        self.scrubber.valueChanged.connect(self.scrubbed.emit)
        bottom_row.addWidget(self.scrubber, stretch=1)

        # Speed Control
        self.lbl_speed = QLabel("250ms")
        self.lbl_speed.setStyleSheet(f"color: {ChalkTheme.FG_CHALK_MUTED}; font-size: 11px;")
        bottom_row.addWidget(self.lbl_speed)

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(20, 1000)
        self.speed_slider.setValue(250)
        self.speed_slider.setFixedWidth(100)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        bottom_row.addWidget(self.speed_slider)

        layout.addLayout(bottom_row)

    def _on_speed_changed(self, value: int) -> None:
        self.lbl_speed.setText(f"{value}ms")
        self.speed_changed.emit(value)

    def get_speed(self) -> int:
        return self.speed_slider.value()

    def set_playing(self, is_playing: bool) -> None:
        self._is_playing = is_playing
        self.btn_play.setText("⏸ Pause" if is_playing else "▶ Play")

    def configure_timeline(self, total_steps: int) -> None:
        """Configures scrubber slider range for a completed solve timeline."""
        self._max_steps = max(0, total_steps - 1)
        self.scrubber.blockSignals(True)
        self.scrubber.setRange(0, self._max_steps)
        self.scrubber.setValue(0)
        self.scrubber.blockSignals(False)

    def set_scrubber_value(self, index: int) -> None:
        self.scrubber.blockSignals(True)
        self.scrubber.setValue(index)
        self.scrubber.blockSignals(False)

    def set_status(self, text: str, hex_color: str = ChalkTheme.FG_CHALK_WHITE) -> None:
        self.lbl_status.setStyleSheet(f"color: {hex_color}; font-weight: bold;")
        self.lbl_status.setText(text)

    def set_controls_enabled(self, solving: bool) -> None:
        """Disables/enables solve triggers during active solving."""
        self.btn_playback_solve.setEnabled(not solving)
        self.btn_instant_solve.setEnabled(not solving)
