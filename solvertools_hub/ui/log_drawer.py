"""
log_drawer.py - Collapsible log and heuristic console drawer for solvertools_hub.
Renders step traces, algorithm metrics, and status diagnostics using chalk/neon HTML formatting.
"""

from datetime import datetime
from typing import Any, Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..theme import ChalkTheme


class LogDrawer(QFrame):
    """Collapsible trace and heuristic metrics console."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("PanelFrame")
        self._is_collapsed = False
        self._init_ui()

    def _init_ui(self) -> None:
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(10, 8, 10, 8)
        self.layout.setSpacing(6)

        # Header bar
        header = QHBoxLayout()
        header.setSpacing(8)

        self.lbl_title = QLabel("TRACE & METRICS CONSOLE")
        self.lbl_title.setStyleSheet(f"color: {ChalkTheme.FG_CHALK_MUTED}; font-size: 11px; font-weight: bold;")
        header.addWidget(self.lbl_title)

        header.addStretch()

        self.btn_clear = QPushButton("Clear")
        self.btn_clear.setFixedWidth(55)
        self.btn_clear.setStyleSheet("padding: 2px 6px; font-size: 11px;")
        self.btn_clear.clicked.connect(self.clear)
        header.addWidget(self.btn_clear)

        self.btn_toggle = QPushButton("▼")
        self.btn_toggle.setFixedWidth(30)
        self.btn_toggle.setStyleSheet("padding: 2px 4px; font-size: 11px;")
        self.btn_toggle.clicked.connect(self.toggle_collapsed)
        header.addWidget(self.btn_toggle)

        self.layout.addLayout(header)

        # Log viewer
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(100)
        self.log_text.setMaximumHeight(200)
        self.layout.addWidget(self.log_text)

    def toggle_collapsed(self) -> None:
        self._is_collapsed = not self._is_collapsed
        self.log_text.setVisible(not self._is_collapsed)
        self.btn_toggle.setText("▲" if self._is_collapsed else "▼")

    def clear(self) -> None:
        self.log_text.clear()

    def _timestamp(self) -> str:
        return datetime.now().strftime("%H:%M:%S")

    def log(self, html_line: str) -> None:
        """Appends raw HTML line to log and scrolls to bottom."""
        self.log_text.append(html_line)
        sb = self.log_text.verticalScrollBar()
        if sb:
            sb.setValue(sb.maximum())

    def log_info(self, message: str) -> None:
        t = self._timestamp()
        line = f"<span style='color:{ChalkTheme.FG_CHALK_MUTED};'>[{t}]</span> " \
               f"<span style='color:{ChalkTheme.FG_CHALK_WHITE};'>{message}</span>"
        self.log(line)

    def log_success(self, message: str) -> None:
        t = self._timestamp()
        line = f"<span style='color:{ChalkTheme.FG_CHALK_MUTED};'>[{t}]</span> " \
               f"<span style='color:{ChalkTheme.NEON_LIME}; font-weight:bold;'>✓ {message}</span>"
        self.log(line)

    def log_error(self, message: str) -> None:
        t = self._timestamp()
        line = f"<span style='color:{ChalkTheme.FG_CHALK_MUTED};'>[{t}]</span> " \
               f"<span style='color:{ChalkTheme.NEON_CORAL}; font-weight:bold;'>✗ {message}</span>"
        self.log(line)

    def log_metrics(self, title: str, metrics: Dict[str, Any]) -> None:
        t = self._timestamp()
        parts = [f"<span style='color:{ChalkTheme.NEON_CYAN};'>{k}</span>={v}" for k, v in metrics.items()]
        metrics_str = " | ".join(parts)
        line = f"<span style='color:{ChalkTheme.FG_CHALK_MUTED};'>[{t}]</span> " \
               f"<span style='color:{ChalkTheme.PASTEL_MINT}; font-weight:bold;'>[{title}]</span> {metrics_str}"
        self.log(line)
