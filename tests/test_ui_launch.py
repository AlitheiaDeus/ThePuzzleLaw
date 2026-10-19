"""
test_ui_launch.py - Tests Qt Application and PuzzleHubWindow initialization in offscreen mode.
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import os
os.environ["QT_QPA_PLATFORM"] = "offscreen"

import unittest
from PySide6.QtWidgets import QApplication
from solvertools_hub.theme import ChalkTheme
from solvertools_hub.core.registry import PluginRegistry
from solvertools_hub.plugins.sliding_tile import SlidingTilePlugin
from solvertools_hub.plugins.sand_tubes import SandTubePlugin
from solvertools_hub.plugins.sudoku import SudokuPlugin
from solvertools_hub.plugins.flip import FlipPlugin
from solvertools_hub.plugins.unruly import UnrulyPlugin
from solvertools_hub.plugins.urjo import UrjoPlugin
from solvertools_hub.ui.hub_window import PuzzleHubWindow


class TestUILaunch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if not cls.app:
            cls.app = QApplication(sys.argv)
        cls.app.setStyleSheet(ChalkTheme.get_stylesheet())

    def test_hub_window_instantiation_and_plugin_switch(self):
        registry = PluginRegistry()
        registry.register(SlidingTilePlugin())
        registry.register(SandTubePlugin())
        registry.register(SudokuPlugin())
        registry.register(FlipPlugin())
        registry.register(UnrulyPlugin())
        registry.register(UrjoPlugin())

        window = PuzzleHubWindow(registry.list_plugins())
        self.assertIsNotNone(window)
        self.assertEqual(window.nav_list.count(), 6)

        # Switch to Sand Tubes / Liquid Sorter
        window.nav_list.setCurrentRow(1)
        self.assertEqual(window.active_plugin.name, "Liquid Sorter Pro")
        self.assertIsNotNone(window.active_canvas)

        # Switch to Sudoku
        window.nav_list.setCurrentRow(2)
        self.assertEqual(window.active_plugin.name, "Sudoku (Constraint Grid)")
        self.assertIsNotNone(window.active_canvas)

        # Switch to Flip
        window.nav_list.setCurrentRow(3)
        self.assertEqual(window.active_plugin.name, "Flip (Lights Out)")
        self.assertIsNotNone(window.active_canvas)

        # Switch to Unruly
        window.nav_list.setCurrentRow(4)
        self.assertEqual(window.active_plugin.name, "Unruly (Binary Puzzle)")
        self.assertIsNotNone(window.active_canvas)

        # Switch to Urjo
        window.nav_list.setCurrentRow(5)
        self.assertEqual(window.active_plugin.name, "Urjo")
        self.assertIsNotNone(window.active_canvas)

        # Switch back to Sliding Tile
        window.nav_list.setCurrentRow(0)
        self.assertEqual(window.active_plugin.name, "Sliding Tile (N-Puzzle)")
        self.assertIsNotNone(window.active_canvas)

        window.close()

    def test_state_preserved_across_plugin_switch(self):
        registry = PluginRegistry()
        registry.register(SandTubePlugin())
        registry.register(SudokuPlugin())

        window = PuzzleHubWindow(registry.list_plugins())
        # Active is Sand Tubes (row 0)
        self.assertEqual(window.active_plugin.name, "Liquid Sorter Pro")
        # Mutate sand tube 0 slot 0 to color 5
        window.active_canvas.state.set_slot(0, 0, 5)
        self.assertEqual(window.active_canvas.state.get_slot(0, 0), 5)

        # Switch to Sudoku (row 1)
        window.nav_list.setCurrentRow(1)
        self.assertEqual(window.active_plugin.name, "Sudoku (Constraint Grid)")

        # Switch back to Sand Tubes (row 0)
        window.nav_list.setCurrentRow(0)
        self.assertEqual(window.active_plugin.name, "Liquid Sorter Pro")
        # Verify color 5 was preserved!
        self.assertEqual(window.active_canvas.state.get_slot(0, 0), 5)

        window.close()

    def test_instant_solve_timeline_and_reset(self):
        from solvertools_hub.plugins.sand_tubes.state import SandTubeState
        from solvertools_hub.core.base_plugin import InteractionMode

        registry = PluginRegistry()
        registry.register(SandTubePlugin())
        window = PuzzleHubWindow(registry.list_plugins())

        # Simple 1-pour puzzle
        st = SandTubeState([[0, 0, 0], [0], []], capacity=4)
        window.active_canvas.state = st
        self.assertFalse(window.active_canvas.state.is_solved())

        # Trigger Instant Solve
        window._trigger_solve(instant=True)
        self.assertIsNotNone(window.worker)
        window.worker.wait(2000)
        self.app.processEvents()

        # Ensure full timeline was stored and scrubbable
        self.assertGreaterEqual(len(window.timeline), 2)
        self.assertEqual(window.timeline_idx, len(window.timeline) - 1)
        self.assertTrue(window.active_canvas.state.is_solved())

        # Unlock / Return to Edit Mode: pre-solve board must be restored!
        window._unlock_edit_mode()
        self.assertEqual(window.active_canvas.mode, InteractionMode.EDIT)
        self.assertFalse(window.active_canvas.state.is_solved())
        self.assertEqual(window.active_canvas.state.tubes[0], [0, 0, 0])
        self.assertEqual(window.active_canvas.state.tubes[1], [0])

        window.close()

    def test_sidebar_toggle(self):
        registry = PluginRegistry()
        registry.register(SandTubePlugin())
        window = PuzzleHubWindow(registry.list_plugins())

        self.assertFalse(window.sidebar_frame.isHidden())
        # Toggle hide
        window._toggle_sidebar()
        self.assertTrue(window.sidebar_frame.isHidden())
        self.assertIn("Sidebar", window.btn_toggle_sidebar.text())

        # Toggle show
        window._toggle_sidebar()
        self.assertFalse(window.sidebar_frame.isHidden())
        self.assertIn("Sidebar", window.btn_toggle_sidebar.text())

        window.close()

    def test_dynamic_color_spawning_ui(self):
        from PySide6.QtWidgets import QPushButton
        from solvertools_hub.plugins.sand_tubes.state import SandTubeState

        registry = PluginRegistry()
        registry.register(SandTubePlugin())
        window = PuzzleHubWindow(registry.list_plugins())

        # Initially, default state has 3 colors (0, 1, 2)
        canvas = window.active_canvas
        tool_strip = window.tool_strip_container
        self.assertEqual(canvas.state.get_used_colors(), [0, 1, 2])

        # Find the "+ Color" button
        add_color_buttons = [b for b in tool_strip.findChildren(QPushButton) if b.text() == "+ Color"]
        self.assertEqual(len(add_color_buttons), 1)
        btn_add = add_color_buttons[0]

        # Click "+ Color" to spawn a new color (should spawn index 3, which is Color #4)
        btn_add.click()
        self.assertEqual(canvas.active_brush_color, 3)

        # Clear all tubes and verify spawning starts from 0
        canvas.state.clear_all_tubes()
        canvas.active_brush_color = None
        canvas.state_modified.emit()
        self.assertEqual(canvas.state.get_used_colors(), [])
        btn_add.click()
        self.assertEqual(canvas.active_brush_color, 0)

        window.close()


if __name__ == "__main__":
    unittest.main()
