"""
main.py - Application entry point for The Puzzle Law (solvertools_hub).
Initializes Qt application, injects Chalkboard & Pastel-Neon theme,
discovers active plugins dynamically from plugins_config.json,
executes pre-flight validation checks, and launches PuzzleHubWindow.
"""

import sys
from pathlib import Path
from typing import List

# Ensure package root is in sys.path when invoked directly
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from loguru import logger
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox

from solvertools_hub.core.registry import PluginRegistry
from solvertools_hub.theme import ChalkTheme
from solvertools_hub.ui.hub_window import PuzzleHubWindow


def global_exception_hook(exctype, value, tb):
    """Logs uncaught exceptions to loguru and presents a friendly alert."""
    logger.opt(exception=(exctype, value, tb)).critical("Uncaught application exception")
    msg_box = QMessageBox()
    msg_box.setIcon(QMessageBox.Critical)
    msg_box.setWindowTitle("Application Error")
    msg_box.setText(f"An unexpected error occurred:\n{value}")
    msg_box.exec()
    sys.__excepthook__(exctype, value, tb)


def run():
    sys.excepthook = global_exception_hook

    app = QApplication(sys.argv)
    app.setApplicationName("The Puzzle Law")
    app.setStyleSheet(ChalkTheme.get_stylesheet())

    # Dynamically discover plugins (controlled via plugins_config.json)
    registry = PluginRegistry()
    registry.auto_discover()

    active_plugins = registry.list_plugins()
    logger.info(f"Loaded {len(active_plugins)} active plugins: {[p.name for p in active_plugins]}")
    disabled = registry.list_disabled_plugins()
    if disabled:
        logger.info(f"Behind the curtain ({len(disabled)} plugins): {[p.name for p in disabled]}")

    # Pre-flight sanity assertion on registered active plugins
    logger.info("Executing pre-flight plugin sanity checks on active plugins...")
    for plugin in active_plugins:
        state = plugin.create_default_state()
        is_valid, reason = state.validate()
        assert is_valid, f"Default state validation failed for {plugin.name}: {reason}"

        # Roundtrip serialization check
        serialized = state.serialize()
        restored = type(state).deserialize(serialized)
        assert restored.serialize() == serialized, f"Serialization roundtrip failed for {plugin.name}"
        logger.debug(f"Plugin '{plugin.name}' passed pre-flight sanity checks.")

    window = PuzzleHubWindow(active_plugins)
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
