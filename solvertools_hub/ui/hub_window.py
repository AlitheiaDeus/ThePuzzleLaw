"""
hub_window.py - Main application shell (PuzzleHubWindow) for solvertools_hub.
Orchestrates plugin switching, transport controls, background worker execution,
QTimer animation loop, and clipboard I/O.
"""

from typing import List, Optional

from loguru import logger
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from ..core.base_plugin import BasePuzzleCanvas, BasePuzzlePlugin, InteractionMode, SolverStep
from ..core.io_manager import IOManager
from ..core.worker import SolverWorker
from ..theme import ChalkTheme
from .log_drawer import LogDrawer
from .transport_bar import TransportBar


class PuzzleHubWindow(QMainWindow):
    """Main window hosting the plugin sidebar, active workspace, transport bar, and log drawer."""

    def __init__(self, plugins: List[BasePuzzlePlugin]):
        super().__init__()
        self.setWindowTitle("The Puzzle Law // solvertools-ui")
        self.resize(1080, 750)
        self.setMinimumSize(780, 560)
        self.plugins = plugins

        # Active session state
        self.active_plugin: Optional[BasePuzzlePlugin] = None
        self.active_canvas: Optional[BasePuzzleCanvas] = None
        self.worker: Optional[SolverWorker] = None
        self.timeline: List[SolverStep] = []
        self.timeline_idx: int = 0
        self._saved_plugin_states: dict = {}
        self._pre_solve_state: Optional[BasePuzzleState] = None

        # Playback QTimer
        self.playback_timer = QTimer(self)
        self.playback_timer.timeout.connect(self._on_timer_tick)

        self._build_ui()
        self._setup_shortcuts()

        if self.plugins:
            self.nav_list.setCurrentRow(0)

    def _build_ui(self) -> None:
        root = QWidget()
        self.setCentralWidget(root)
        main_layout = QHBoxLayout(root)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(12)

        # =====================================================================
        # LEFT SIDEBAR: Navigation & State I/O
        # =====================================================================
        self.sidebar_frame = QFrame()
        self.sidebar_frame.setObjectName("PanelFrame")
        self.sidebar_frame.setFixedWidth(260)
        sidebar_layout = QVBoxLayout(self.sidebar_frame)
        sidebar_layout.setContentsMargins(10, 10, 10, 10)
        sidebar_layout.setSpacing(8)

        # Title
        title_lbl = QLabel("THE PUZZLE LAW")
        title_lbl.setStyleSheet(f"color: {ChalkTheme.NEON_CYAN}; font-size: 16px; font-weight: bold;")
        sidebar_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Modular Solver Suite")
        sub_lbl.setStyleSheet(f"color: {ChalkTheme.FG_CHALK_MUTED}; font-size: 11px;")
        sidebar_layout.addWidget(sub_lbl)

        # Navigation List
        self.nav_list = QListWidget()
        for plugin in self.plugins:
            item = QListWidgetItem(f"{plugin.name}\n[{plugin.category}]")
            self.nav_list.addItem(item)
        self.nav_list.currentRowChanged.connect(self._switch_plugin)
        sidebar_layout.addWidget(self.nav_list, stretch=1)

        # State I/O Section
        io_lbl = QLabel("STATE TRANSCRIPTION I/O")
        io_lbl.setStyleSheet(f"color: {ChalkTheme.FG_CHALK_MUTED}; font-size: 11px; margin-top: 6px;")
        sidebar_layout.addWidget(io_lbl)

        btn_copy = QPushButton("Copy State (Clipboard)")
        btn_copy.clicked.connect(self._copy_state_to_clipboard)
        sidebar_layout.addWidget(btn_copy)

        btn_paste = QPushButton("Paste State (Clipboard)")
        btn_paste.clicked.connect(self._paste_state_from_clipboard)
        sidebar_layout.addWidget(btn_paste)

        btn_reset = QPushButton("Reset to Edit Mode")
        btn_reset.clicked.connect(self._unlock_edit_mode)
        sidebar_layout.addWidget(btn_reset)

        main_layout.addWidget(self.sidebar_frame)

        # =====================================================================
        # CENTER WORKSPACE: Header + Tool Strip + Canvas + Transport + Logs
        # =====================================================================
        center_layout = QVBoxLayout()
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)

        # Header Frame
        header_frame = QFrame()
        header_frame.setObjectName("PanelFrame")
        h_layout = QHBoxLayout(header_frame)
        h_layout.setContentsMargins(10, 8, 10, 8)
        h_layout.setSpacing(10)

        self.btn_toggle_sidebar = QPushButton("◀ Sidebar")
        self.btn_toggle_sidebar.setToolTip("Toggle Navigation Sidebar (Ctrl+B)")
        self.btn_toggle_sidebar.setCursor(Qt.PointingHandCursor)
        self.btn_toggle_sidebar.setFixedWidth(95)
        self.btn_toggle_sidebar.setStyleSheet(
            f"background-color: {ChalkTheme.BG_BOARD_RAISED}; color: {ChalkTheme.NEON_CYAN}; "
            f"border: 1px solid {ChalkTheme.BORDER_MUTED}; border-radius: 4px; padding: 4px 6px; font-weight: bold;"
        )
        self.btn_toggle_sidebar.clicked.connect(self._toggle_sidebar)
        h_layout.addWidget(self.btn_toggle_sidebar)

        title_vbox = QVBoxLayout()
        title_vbox.setSpacing(2)
        self.puzzle_title_lbl = QLabel("Active Puzzle")
        self.puzzle_title_lbl.setStyleSheet(f"color: {ChalkTheme.PASTEL_MINT}; font-size: 16px; font-weight: bold;")
        title_vbox.addWidget(self.puzzle_title_lbl)

        self.puzzle_desc_lbl = QLabel("Description")
        self.puzzle_desc_lbl.setStyleSheet(f"color: {ChalkTheme.FG_CHALK_MUTED}; font-size: 11px;")
        self.puzzle_desc_lbl.setWordWrap(True)
        title_vbox.addWidget(self.puzzle_desc_lbl)
        h_layout.addLayout(title_vbox, stretch=1)

        center_layout.addWidget(header_frame)

        # Dynamic Tool Strip Area
        self.tool_strip_container = QWidget()
        self.tool_strip_layout = QHBoxLayout(self.tool_strip_container)
        self.tool_strip_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.tool_strip_container)

        # Dynamic Canvas Container
        self.canvas_container = QWidget()
        self.canvas_layout = QVBoxLayout(self.canvas_container)
        self.canvas_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.addWidget(self.canvas_container, stretch=1)

        # Transport Bar
        self.transport_bar = TransportBar()
        self.transport_bar.playback_solve_requested.connect(lambda: self._trigger_solve(instant=False))
        self.transport_bar.instant_solve_requested.connect(lambda: self._trigger_solve(instant=True))
        self.transport_bar.reset_edit_requested.connect(self._unlock_edit_mode)
        self.transport_bar.scrubbed.connect(self._scrub_to_index)
        self.transport_bar.play_toggled.connect(self._toggle_timer)
        self.transport_bar.step_manual.connect(self._step_manual)
        self.transport_bar.speed_changed.connect(self._on_speed_changed)
        center_layout.addWidget(self.transport_bar)

        # Collapsible Log Drawer
        self.log_drawer = LogDrawer()
        center_layout.addWidget(self.log_drawer)

        main_layout.addLayout(center_layout, stretch=1)

    def _setup_shortcuts(self) -> None:
        """Configures ergonomic keyboard shortcuts."""
        QShortcut(QKeySequence(Qt.Key_Space), self, self._toggle_timer)
        QShortcut(QKeySequence(Qt.Key_Left), self, lambda: self._step_manual(-1))
        QShortcut(QKeySequence(Qt.Key_Right), self, lambda: self._step_manual(1))
        QShortcut(QKeySequence("Ctrl+C"), self, self._copy_state_to_clipboard)
        QShortcut(QKeySequence("Ctrl+V"), self, self._paste_state_from_clipboard)
        QShortcut(QKeySequence("Ctrl+B"), self, self._toggle_sidebar)
        QShortcut(QKeySequence(Qt.Key_Escape), self, self._unlock_edit_mode)

    def _toggle_sidebar(self) -> None:
        """Toggles visibility of the navigation and I/O sidebar."""
        is_hidden = self.sidebar_frame.isHidden()
        self.sidebar_frame.setVisible(is_hidden)
        self.btn_toggle_sidebar.setText("◀ Sidebar" if is_hidden else "▶ Sidebar")

    # -----------------------------------------------------------------
    # Plugin Switching
    # -----------------------------------------------------------------
    def _switch_plugin(self, row: int) -> None:
        if row < 0 or row >= len(self.plugins):
            return

        # Stop any active timer and abort any active solver worker
        self.playback_timer.stop()
        if self.worker and self.worker.isRunning():
            self.worker.abort()
            self.worker.wait(1000)

        # Save previous plugin's active state if available
        if self.active_plugin and self.active_canvas and hasattr(self.active_canvas, "state") and self.active_canvas.state:
            self._saved_plugin_states[self.active_plugin.name] = self.active_canvas.state.clone()

        self.active_plugin = self.plugins[row]
        self.puzzle_title_lbl.setText(self.active_plugin.name)
        self.puzzle_desc_lbl.setText(self.active_plugin.description)

        # Clear tool strip container
        while self.tool_strip_layout.count():
            item = self.tool_strip_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Clear canvas container
        while self.canvas_layout.count():
            item = self.canvas_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        # Restore saved state if exists, else create default state
        if self.active_plugin.name in self._saved_plugin_states:
            initial_state = self._saved_plugin_states[self.active_plugin.name].clone()
            self.log_drawer.log_info(f"Restored saved progress for: {self.active_plugin.name}")
        else:
            initial_state = self.active_plugin.create_default_state()
            self.log_drawer.log_info(f"Loaded plugin: {self.active_plugin.name}")

        self.active_canvas = self.active_plugin.create_canvas(initial_state)
        self.canvas_layout.addWidget(self.active_canvas)

        # Instantiate tool strip if provided
        tool_strip = self.active_plugin.create_tool_strip(self.active_canvas)
        if tool_strip:
            self.tool_strip_layout.addWidget(tool_strip)
            self.tool_strip_container.show()
        else:
            self.tool_strip_container.hide()

        # Connect canvas mutation signal
        self.active_canvas.state_modified.connect(self._on_canvas_modified)

        # Reset timeline & transport
        self.timeline.clear()
        self.timeline_idx = 0
        self._pre_solve_state = None
        self.transport_bar.configure_timeline(0)
        self.transport_bar.set_playing(False)
        self.transport_bar.set_status(f"Ready: {self.active_plugin.name} loaded (Edit Mode).", ChalkTheme.FG_CHALK_MUTED)

    def _on_canvas_modified(self) -> None:
        """Called whenever the user mutates puzzle state in EDIT mode."""
        self.timeline.clear()
        self.timeline_idx = 0
        self.transport_bar.configure_timeline(0)
        self.transport_bar.set_status("State modified. Ready to solve.", ChalkTheme.FG_CHALK_WHITE)

    # -----------------------------------------------------------------
    # Solver Execution & Lifecycle
    # -----------------------------------------------------------------
    def _trigger_solve(self, instant: bool = False) -> None:
        if not self.active_canvas or not self.active_plugin:
            return

        # Automatically drop any floating segments with gravity before validation/solve
        if hasattr(self.active_canvas.state, "settle_tubes"):
            self.active_canvas.state.settle_tubes()
            self.active_canvas.update()

        # 1. State validation check before solver launch
        is_valid, reason = self.active_canvas.state.validate()
        if not is_valid:
            self.transport_bar.set_status(f"Invalid State: {reason}", ChalkTheme.NEON_CORAL)
            self.log_drawer.log_error(f"Validation failed: {reason}")
            return

        # Store pre-solve state to restore cleanly upon returning to edit mode
        self._pre_solve_state = self.active_canvas.state.clone()

        # Stop existing timer
        self.playback_timer.stop()
        self.transport_bar.set_playing(False)

        # Lock canvas into playback mode so accidental clicks don't disrupt
        self.active_canvas.set_mode(InteractionMode.PLAYBACK)

        # Spawn background worker
        self.transport_bar.set_controls_enabled(solving=True)
        self.transport_bar.set_status("Solving in background...", ChalkTheme.NEON_CYAN)
        self.log_drawer.log_info(f"Launching solver ({'Instant' if instant else 'Playback'} mode)...")

        solver = self.active_plugin.create_solver()
        self.worker = SolverWorker(
            solver=solver,
            initial_state=self.active_canvas.state,
            instant_mode=instant,
            stream_search=False,
        )
        self.worker.finished_timeline.connect(self._on_solve_timeline_finished)
        self.worker.finished_instant.connect(self._on_solve_instant_finished)
        self.worker.failed.connect(self._on_solve_failed)
        self.worker.start()

    def _on_solve_timeline_finished(self, timeline: List[SolverStep], elapsed: float) -> None:
        self.transport_bar.set_controls_enabled(solving=False)
        self.timeline = timeline
        self.timeline_idx = 0

        self.transport_bar.configure_timeline(len(self.timeline))
        self._scrub_to_index(0)

        total_steps = len(self.timeline) - 1
        self.log_drawer.log_success(f"Solved in {elapsed*1000:.1f}ms! Solution path length: {total_steps} moves:")
        for idx, step in enumerate(self.timeline[1:], 1):
            self.log_drawer.log_info(f"  Step {idx}: {step.action_desc}")

        if self.timeline and self.timeline[-1].metrics:
            self.log_drawer.log_metrics("Final Search Metrics", self.timeline[-1].metrics)

        # Automatically start playback animation
        if len(self.timeline) > 1:
            self.playback_timer.start(self.transport_bar.get_speed())
            self.transport_bar.set_playing(True)

    def _on_solve_instant_finished(self, timeline: List[SolverStep], count: int, elapsed: float) -> None:
        self.transport_bar.set_controls_enabled(solving=False)
        self.timeline = timeline
        self.timeline_idx = max(0, len(timeline) - 1)

        self.transport_bar.configure_timeline(len(self.timeline))
        self.transport_bar.set_scrubber_value(self.timeline_idx)
        self._scrub_to_index(self.timeline_idx)

        total_moves = max(0, len(self.timeline) - 1)
        self.transport_bar.set_status(
            f"Solved in {elapsed*1000:.1f}ms! ({total_moves} moves). Use Scrubber or Prev/Next to inspect.",
            ChalkTheme.NEON_LIME,
        )
        self.log_drawer.log_success(f"Instant Solve finished in {elapsed*1000:.1f}ms ({total_moves} moves in solution path):")
        for idx, step in enumerate(self.timeline[1:], 1):
            self.log_drawer.log_info(f"  Move {idx}: {step.action_desc}")

        if self.timeline and self.timeline[-1].metrics:
            self.log_drawer.log_metrics("Instant Metrics", self.timeline[-1].metrics)

    def _on_solve_failed(self, err_msg: str) -> None:
        self.transport_bar.set_controls_enabled(solving=False)
        self.transport_bar.set_status(err_msg, ChalkTheme.NEON_CORAL)
        self.log_drawer.log_error(err_msg)
        # Ensure canvas is unlocked back to EDIT mode so user is never frozen
        if self.active_canvas:
            self.active_canvas.set_mode(InteractionMode.EDIT)
            self.active_canvas.update()

    def _unlock_edit_mode(self) -> None:
        """Unlocks canvas manual editing, restores pre-solve state, and stops playback."""
        self.playback_timer.stop()
        self.transport_bar.set_playing(False)
        self.timeline.clear()
        self.timeline_idx = 0
        self.transport_bar.configure_timeline(0)

        if self.active_canvas:
            # Restore state prior to solver execution if available
            if hasattr(self, "_pre_solve_state") and self._pre_solve_state is not None:
                self.active_canvas.state = self._pre_solve_state.clone()
            self.active_canvas.set_mode(InteractionMode.EDIT)
            self.active_canvas.current_step = None
            self.active_canvas.update()

        self.transport_bar.set_status("Edit Mode active. Click canvas to transcribe or edit.", ChalkTheme.FG_CHALK_MUTED)
        self.log_drawer.log_info("Switched to Edit Mode (restored board).")

    # -----------------------------------------------------------------
    # Playback & Scrubbing Controller
    # -----------------------------------------------------------------
    def _on_timer_tick(self) -> None:
        if self.timeline_idx < len(self.timeline) - 1:
            self.transport_bar.set_scrubber_value(self.timeline_idx + 1)
            self._scrub_to_index(self.timeline_idx + 1)
        else:
            self.playback_timer.stop()
            self.transport_bar.set_playing(False)

    def _toggle_timer(self) -> None:
        if not self.timeline:
            return
        if self.playback_timer.isActive():
            self.playback_timer.stop()
            self.transport_bar.set_playing(False)
        else:
            if self.timeline_idx >= len(self.timeline) - 1:
                self.transport_bar.set_scrubber_value(0)
                self._scrub_to_index(0)
            self.playback_timer.start(self.transport_bar.get_speed())
            self.transport_bar.set_playing(True)

    def _step_manual(self, delta: int) -> None:
        if not self.timeline:
            return
        self.playback_timer.stop()
        self.transport_bar.set_playing(False)
        new_idx = max(0, min(len(self.timeline) - 1, self.timeline_idx + delta))
        self.transport_bar.set_scrubber_value(new_idx)
        self._scrub_to_index(new_idx)

    def _scrub_to_index(self, idx: int) -> None:
        if not self.timeline or idx < 0 or idx >= len(self.timeline):
            return
        self.timeline_idx = idx
        step = self.timeline[idx]
        if self.active_canvas:
            self.active_canvas.state = step.state.clone()
            self.active_canvas.set_step(step)

        max_idx = len(self.timeline) - 1
        status_text = f"Step {idx}/{max_idx}: {step.action_desc}"
        self.transport_bar.set_status(status_text, ChalkTheme.NEON_LIME)

    def _on_speed_changed(self, delay_ms: int) -> None:
        if self.playback_timer.isActive():
            self.playback_timer.setInterval(delay_ms)

    # -----------------------------------------------------------------
    # Clipboard Serialization I/O
    # -----------------------------------------------------------------
    def _copy_state_to_clipboard(self) -> None:
        if not self.active_canvas:
            return
        try:
            raw = IOManager.copy_state_to_clipboard(self.active_canvas.state)
            self.log_drawer.log_success(f"Copied state to clipboard ({len(raw)} chars).")
            self.transport_bar.set_status("State copied to clipboard.", ChalkTheme.NEON_CYAN)
        except Exception as exc:
            self.log_drawer.log_error(f"Copy failed: {exc}")

    def _paste_state_from_clipboard(self) -> None:
        if not self.active_canvas:
            return
        try:
            state_cls = type(self.active_canvas.state)
            new_state = IOManager.paste_state_from_clipboard(state_cls)
            self.active_canvas.state = new_state
            self._unlock_edit_mode()
            self.log_drawer.log_success("Imported state from clipboard.")
            self.transport_bar.set_status("State pasted from clipboard.", ChalkTheme.NEON_LIME)
        except Exception as exc:
            logger.error(f"Clipboard paste error: {exc}")
            self.log_drawer.log_error(f"Paste failed: {exc}")
            self.transport_bar.set_status(f"Paste Error: {exc}", ChalkTheme.NEON_CORAL)
