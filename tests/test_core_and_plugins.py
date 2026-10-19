"""
test_core_and_plugins.py - Headless sanity test suite for solvertools_hub.
Tests:
1. Theme palette tokens and CSS generation
2. State serialization, deserialization, and validation for all plugins
3. Solver execution (A* for Sliding Tile, BFS for Sand Tubes)
4. Worker logic and step yields
"""

import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import unittest
from solvertools_hub.theme import ChalkTheme
from solvertools_hub.core.registry import PluginRegistry
from solvertools_hub.plugins.sliding_tile import SlidingTilePlugin, SlidingTileState, SlidingTileSolver
from solvertools_hub.plugins.sand_tubes import SandTubePlugin, SandTubeState, SandTubeSolver
from solvertools_hub.plugins.sudoku import SudokuPlugin, SudokuState, SudokuSolver
from solvertools_hub.plugins.flip import FlipPlugin, FlipState, FlipSolver
from solvertools_hub.plugins.unruly import UnrulyPlugin, UnrulyState, UnrulySolver
from solvertools_hub.plugins.urjo import UrjoPlugin, UrjoState, UrjoSolver


class TestTheme(unittest.TestCase):
    def test_theme_tokens_and_stylesheet(self):
        qss = ChalkTheme.get_stylesheet()
        self.assertIn(ChalkTheme.BG_CHALK_BLACK, qss)
        self.assertIn(ChalkTheme.NEON_CYAN, qss)
        self.assertIn(ChalkTheme.PASTEL_MINT, qss)


class TestSlidingTile(unittest.TestCase):
    def test_state_validation_valid(self):
        st = SlidingTileState(3, [1, 2, 3, 4, 5, 6, 0, 7, 8])
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

    def test_state_validation_invalid_inversion(self):
        # 1-swap on 3x3 is unsolvable
        st = SlidingTileState(3, [1, 2, 3, 4, 5, 6, 8, 7, 0])
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("inversion count", reason)

    def test_serialization_roundtrip(self):
        st = SlidingTileState(3, [1, 2, 3, 4, 5, 6, 0, 7, 8])
        raw = st.serialize()
        restored = SlidingTileState.deserialize(raw)
        self.assertEqual(restored.size, st.size)
        self.assertEqual(restored.grid, st.grid)

    def test_solver_execution(self):
        # State with 2 moves to goal: [1, 2, 3, 4, 5, 6, 7, 0, 8] -> slide 8 left
        st = SlidingTileState(3, [1, 2, 3, 4, 5, 6, 7, 0, 8])
        solver = SlidingTileSolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        # Final step must be goal state
        self.assertEqual(steps[-1].state.grid, [1, 2, 3, 4, 5, 6, 7, 8, 0])


class TestSandTubes(unittest.TestCase):
    def test_state_validation_valid(self):
        st = SandTubeState()
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

    def test_state_validation_invalid_segment_count(self):
        # Missing a segment without split colors
        st = SandTubeState([[0, 0, 0], [1, 1, 1, 1]], capacity=4)
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("segments", reason)

    def test_serialization_roundtrip(self):
        st = SandTubeState([[0, 1], [1, 0], []], capacity=[3, 4, 2], allow_split_colors=True)
        raw = st.serialize()
        restored = SandTubeState.deserialize(raw)
        self.assertEqual(restored.capacities, st.capacities)
        self.assertEqual(restored.tubes, st.tubes)
        self.assertTrue(restored.allow_split_colors)

    def test_solver_execution(self):
        # Simple 1-pour puzzle: Tube 1 has [0, 0, 0], Tube 2 has [0], Tube 3 has []
        st = SandTubeState([[0, 0, 0], [0], []], capacity=4)
        solver = SandTubeSolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        final_state = steps[-1].state
        self.assertTrue(final_state.is_solved())

    def test_variable_capacities_solve(self):
        # Asymmetric capacities: tube 0 cap 3, tube 1 cap 2, tube 2 cap 3
        # Color 0 (3 items), Color 1 (2 items)
        st = SandTubeState(
            tubes=[[0, 1, 0], [1], [0]],
            capacity=[3, 2, 3],
            allow_split_colors=False,
        )
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

        solver = SandTubeSolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        final_state = steps[-1].state
        self.assertTrue(final_state.is_solved())

    def test_snippet_7tube_mixed_capacities_solve(self):
        # 7-tube puzzle from snippet with mixed capacities [4, 4, 4, 4, 4, 4, 3]
        st = SandTubeState(
            tubes=[
                [0, 1],
                [2, 1],
                [2, 3],
                [2, 0],
                [3, 1, 3, 0],
                [2, 3, 1, 0],
                [],
            ],
            capacity=[4, 4, 4, 4, 4, 4, 3],
            allow_split_colors=False,
        )
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

        solver = SandTubeSolver()
        steps = list(solver.solve(st))
        self.assertEqual(len(steps), 14)  # 1 initial + 13 moves
        self.assertTrue(steps[-1].state.is_solved())

    def test_split_colors_allowed_solve(self):
        # 4 items of color 0 in tubes of capacity 2, requiring split colors
        st = SandTubeState(
            tubes=[[0, 0], [0], [0]],
            capacity=[2, 2, 2],
            allow_split_colors=True,
        )
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

        solver = SandTubeSolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        final_state = steps[-1].state
        self.assertTrue(final_state.is_solved())

    def test_slot_level_editing_and_settle(self):
        st = SandTubeState(tubes=[[], []], capacity=[4, 4])
        # Set slot 2 to color 1 (leaving slot 0 and 1 empty - floating segment)
        st.set_slot(0, 2, 1)
        self.assertEqual(st.get_slot(0, 2), 1)
        self.assertIsNone(st.get_slot(0, 0))
        self.assertTrue(st.has_floating_segments())

        # Settle should drop it down to slot 0
        st.settle_tubes()
        self.assertFalse(st.has_floating_segments())
        self.assertEqual(st.get_slot(0, 0), 1)
        self.assertIsNone(st.get_slot(0, 2))

    def test_floating_segments_validation(self):
        st = SandTubeState(tubes=[[None, 0], [1, 1], []], capacity=2, allow_split_colors=True)
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("floating", reason.lower())

    def test_notation_roundtrip_and_snippet_format(self):
        # Snippet 7-tube notation: w,n,-,-/c,n,-,-/c,l,-,-/c,w,-,-/l,n,l,w/c,l,n,w/-,-,-
        raw_snippet = "w,n,-,-/c,n,-,-/c,l,-,-/c,w,-,-/l,n,l,w/c,l,n,w/-,-,-"
        st = SandTubeState.from_notation(raw_snippet)
        self.assertEqual(len(st.tubes), 7)
        self.assertEqual(st.capacities, [4, 4, 4, 4, 4, 4, 3])
        # Verify 4 distinct colors mapped to 0, 1, 2, 3
        all_colors = {c for t in st.tubes for c in t}
        self.assertEqual(len(all_colors), 4)

        # Verify export to notation format
        exported = st.to_notation()
        self.assertIn(" / ", exported)
        self.assertEqual(len(exported.split(" / ")), 7)

    def test_dynamic_palette_colors_and_contrast(self):
        from solvertools_hub.theme import ChalkTheme
        st = SandTubeState(tubes=[[0, 0, 1], [1, 2]], capacity=[4, 4])
        self.assertEqual(st.get_used_colors(), [0, 1, 2])
        counts = st.get_color_counts()
        self.assertEqual(counts[0], 2)
        self.assertEqual(counts[1], 2)
        self.assertEqual(counts[2], 1)

        # High contrast and dynamic fallback verification
        for idx in range(30):
            col = ChalkTheme.get_color(idx)
            self.assertTrue(col.startswith("#"))
            self.assertEqual(len(col), 7)
            text_col = ChalkTheme.get_contrast_text_color(col)
            self.assertIn(text_col, ["#0A0D0C", "#FFFFFF"])

        # Luminance edge cases
        self.assertEqual(ChalkTheme.get_contrast_text_color("#FFFFFF"), "#0A0D0C")
        self.assertEqual(ChalkTheme.get_contrast_text_color("#000000"), "#FFFFFF")


class TestSudoku(unittest.TestCase):
    def test_state_validation_valid(self):
        st = SudokuState(9, 3, 3)
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

    def test_state_validation_invalid_dimension(self):
        st = SudokuState(9, 3, 2)  # 3*2 = 6 != 9
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("must equal", reason)

    def test_state_validation_duplicate_in_row(self):
        st = SudokuState(4, 2, 2, [[1, 1, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]])
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("Duplicate", reason)

    def test_serialization_roundtrip(self):
        st = SudokuState(9, 3, 3)
        raw = st.serialize()
        restored = SudokuState.deserialize(raw)
        self.assertEqual(restored.grid_dim, st.grid_dim)
        self.assertEqual(restored.board, st.board)
        self.assertEqual(restored.clues, st.clues)

    def test_solver_execution_4x4(self):
        sample_4x4 = [
            [1, 0, 0, 0],
            [0, 0, 2, 0],
            [0, 3, 0, 0],
            [0, 0, 0, 4],
        ]
        st = SudokuState(4, 2, 2, sample_4x4)
        solver = SudokuSolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        final_board = steps[-1].state.board
        # Assert no empty cells
        self.assertFalse(any(0 in row for row in final_board))
        # Validate final state is legal
        ok, reason = steps[-1].state.validate()
        self.assertTrue(ok, reason)


class TestFlip(unittest.TestCase):
    def test_state_validation_valid(self):
        st = FlipState(5, 5)
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

    def test_state_validation_invalid_dimension(self):
        st = FlipState(1, 5)
        ok, reason = st.validate()
        self.assertFalse(ok)

    def test_serialization_roundtrip(self):
        st = FlipState(3, 3, [[1, 0, 1], [0, 1, 0], [1, 0, 1]])
        raw = st.serialize()
        restored = FlipState.deserialize(raw)
        self.assertEqual(restored.rows, st.rows)
        self.assertEqual(restored.cols, st.cols)
        self.assertEqual(restored.grid, st.grid)

    def test_solver_single_press(self):
        # A 3x3 where cell (1, 1) and its 4 neighbors are ON: pressing (1, 1) should turn all off!
        st = FlipState(3, 3, [
            [0, 1, 0],
            [1, 1, 1],
            [0, 1, 0],
        ])
        solver = FlipSolver()
        steps = list(solver.solve(st))
        self.assertEqual(len(steps), 2)  # Initial + 1 press
        final_state = steps[-1].state
        self.assertTrue(final_state.is_solved())


class TestUnruly(unittest.TestCase):
    def test_state_validation_valid(self):
        st = UnrulyState(6)
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

    def test_state_validation_odd_size(self):
        st = UnrulyState(5)
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("even number", reason)

    def test_state_validation_triple_violation(self):
        # 3 identical colors in a row
        board = [[1, 1, 1, 0, 0, 0], [0]*6, [0]*6, [0]*6, [0]*6, [0]*6]
        st = UnrulyState(6, board)
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("violates", reason)

    def test_serialization_roundtrip(self):
        st = UnrulyState(6)
        raw = st.serialize()
        restored = UnrulyState.deserialize(raw)
        self.assertEqual(restored.grid_size, st.grid_size)
        self.assertEqual(restored.board, st.board)
        self.assertEqual(restored.edge_constraints, st.edge_constraints)

    def test_solver_sample_6x6(self):
        st = UnrulyState(6)
        solver = UnrulySolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        final_state = steps[-1].state
        self.assertTrue(final_state.is_solved())


class TestUrjo(unittest.TestCase):
    def test_state_validation_valid(self):
        st = UrjoState(4)
        ok, reason = st.validate()
        self.assertTrue(ok, reason)

    def test_state_validation_odd_size(self):
        st = UrjoState(5)
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("even integer", reason)

    def test_state_validation_line_overflow(self):
        # 4x4 allows max 2 Reds per row; place 3 Reds
        board = [[1, 1, 1, 0], [0]*4, [0]*4, [0]*4]
        st = UrjoState(4, board=board)
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("exceeds maximum color capacity", reason)

    def test_adjacent_line_clash_detection(self):
        # Two identical adjacent rows fully filled
        board = [
            [1, 2, 1, 2],
            [1, 2, 1, 2],
            [2, 1, 2, 1],
            [2, 1, 2, 1],
        ]
        st = UrjoState(4, board=board)
        ok, reason = st.validate()
        self.assertFalse(ok)
        self.assertIn("identical", reason)

    def test_serialization_roundtrip(self):
        st = UrjoState(6)
        raw = st.serialize()
        restored = UrjoState.deserialize(raw)
        self.assertEqual(restored.grid_size, st.grid_size)
        self.assertEqual(restored.board, st.board)
        self.assertEqual(restored.clues, st.clues)

    def test_solver_sample_4x4(self):
        st = UrjoState(4)
        solver = UrjoSolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        final_state = steps[-1].state
        self.assertTrue(final_state.is_solved())

    def test_solver_sample_6x6(self):
        st = UrjoState(6)
        solver = UrjoSolver()
        steps = list(solver.solve(st))
        self.assertGreaterEqual(len(steps), 2)
        final_state = steps[-1].state
        self.assertTrue(final_state.is_solved())

    def test_color_cycle_order(self):
        from solvertools_hub.plugins.urjo.canvas import UrjoCanvas
        # Forward: Blank -> Blue -> Red -> Blank
        self.assertEqual(UrjoCanvas.CYCLE_FORWARD[UrjoState.EMPTY], UrjoState.COLOR_BLUE)
        self.assertEqual(UrjoCanvas.CYCLE_FORWARD[UrjoState.COLOR_BLUE], UrjoState.COLOR_RED)
        self.assertEqual(UrjoCanvas.CYCLE_FORWARD[UrjoState.COLOR_RED], UrjoState.EMPTY)

        # Reverse: Blank -> Red -> Blue -> Blank
        self.assertEqual(UrjoCanvas.CYCLE_REVERSE[UrjoState.EMPTY], UrjoState.COLOR_RED)
        self.assertEqual(UrjoCanvas.CYCLE_REVERSE[UrjoState.COLOR_RED], UrjoState.COLOR_BLUE)
        self.assertEqual(UrjoCanvas.CYCLE_REVERSE[UrjoState.COLOR_BLUE], UrjoState.EMPTY)


class TestRegistry(unittest.TestCase):
    def test_registry_registration(self):
        registry = PluginRegistry()
        tile_plugin = SlidingTilePlugin()
        tube_plugin = SandTubePlugin()
        registry.register(tile_plugin)
        registry.register(tube_plugin)

        plugins = registry.list_plugins()
        self.assertEqual(len(plugins), 2)
        self.assertIn(tile_plugin, plugins)
        self.assertIn(tube_plugin, plugins)

    def test_registry_auto_discovery_includes_urjo(self):
        registry = PluginRegistry()
        registry.auto_discover()
        plugin_names = [p.name for p in registry.list_plugins()]
        self.assertIn("Urjo", plugin_names)


if __name__ == "__main__":
    unittest.main()
