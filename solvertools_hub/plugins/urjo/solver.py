"""
solver.py - High-performance constraint propagation and backtracking solver for Urjo puzzles.
Applies deterministic deductions:
1. Row and column balance saturation
2. Neighborhood clue fulfillment and elimination
3. Adjacent line disparity forcing
4. Backtracking with forward checking for deep branches
"""

from typing import Generator, List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import UrjoState


class UrjoSolver(BaseSolver):
    """Deterministic constraint-propagating and backtracking solver for Urjo."""

    def _get_neighbors(self, r: int, c: int, size: int) -> List[Tuple[int, int]]:
        res = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < size and 0 <= nc < size:
                    res.append((nr, nc))
        return res

    def _propagate(
        self,
        b: List[List[int]],
        clues: List[List[Optional[int]]],
        size: int,
        step_collector: Optional[List[Tuple[int, int, int, str]]] = None,
    ) -> bool:
        """
        Runs exhaustive deterministic deduction until a fixpoint is reached.
        Returns False if a logical contradiction is detected, True otherwise.
        """
        half = size // 2
        changed = True

        while changed:
            changed = False

            # --- 1. Line Balance (Rows & Columns) ---
            for r in range(size):
                row = b[r]
                cr = row.count(UrjoState.COLOR_RED)
                cb = row.count(UrjoState.COLOR_BLUE)

                if cr > half or cb > half:
                    return False

                fill_color = None
                if cr == half and cb < half:
                    fill_color = UrjoState.COLOR_BLUE
                elif cb == half and cr < half:
                    fill_color = UrjoState.COLOR_RED

                if fill_color:
                    for c in range(size):
                        if b[r][c] == UrjoState.EMPTY:
                            b[r][c] = fill_color
                            if step_collector is not None:
                                step_collector.append((r, c, fill_color, f"Row {r + 1} Balance"))
                            changed = True

            for c in range(size):
                col = [b[r][c] for r in range(size)]
                cr = col.count(UrjoState.COLOR_RED)
                cb = col.count(UrjoState.COLOR_BLUE)

                if cr > half or cb > half:
                    return False

                fill_color = None
                if cr == half and cb < half:
                    fill_color = UrjoState.COLOR_BLUE
                elif cb == half and cr < half:
                    fill_color = UrjoState.COLOR_RED

                if fill_color:
                    for r in range(size):
                        if b[r][c] == UrjoState.EMPTY:
                            b[r][c] = fill_color
                            if step_collector is not None:
                                step_collector.append((r, c, fill_color, f"Col {c + 1} Balance"))
                            changed = True

            # --- 2. Adjacent Line Disparity (Rows & Columns) ---
            # Check for identical fully filled adjacent rows/cols
            for r in range(size - 1):
                row1, row2 = b[r], b[r + 1]
                if UrjoState.EMPTY not in row1 and UrjoState.EMPTY not in row2:
                    if row1 == row2:
                        return False

                # If exactly 1 mismatch slot across adjacent lines and the rest match identically:
                # then that empty slot CANNOT match the neighbor!
                empty_in_row1 = [c for c in range(size) if row1[c] == UrjoState.EMPTY]
                empty_in_row2 = [c for c in range(size) if row2[c] == UrjoState.EMPTY]

                if len(empty_in_row1) == 1 and len(empty_in_row2) == 0:
                    c = empty_in_row1[0]
                    # Check if all other columns match
                    if all(row1[i] == row2[i] for i in range(size) if i != c):
                        opp_color = 3 - row2[c]
                        b[r][c] = opp_color
                        if step_collector is not None:
                            step_collector.append((r, c, opp_color, f"Avoid Identical Adjacent Row {r + 1}-{r + 2}"))
                        changed = True

                elif len(empty_in_row2) == 1 and len(empty_in_row1) == 0:
                    c = empty_in_row2[0]
                    if all(row1[i] == row2[i] for i in range(size) if i != c):
                        opp_color = 3 - row1[c]
                        b[r + 1][c] = opp_color
                        if step_collector is not None:
                            step_collector.append((r + 1, c, opp_color, f"Avoid Identical Adjacent Row {r + 1}-{r + 2}"))
                        changed = True

            for c in range(size - 1):
                col1 = [b[r][c] for r in range(size)]
                col2 = [b[r][c + 1] for r in range(size)]
                if UrjoState.EMPTY not in col1 and UrjoState.EMPTY not in col2:
                    if col1 == col2:
                        return False

                empty_in_col1 = [r for r in range(size) if col1[r] == UrjoState.EMPTY]
                empty_in_col2 = [r for r in range(size) if col2[r] == UrjoState.EMPTY]

                if len(empty_in_col1) == 1 and len(empty_in_col2) == 0:
                    r = empty_in_col1[0]
                    if all(col1[i] == col2[i] for i in range(size) if i != r):
                        opp_color = 3 - col2[r]
                        b[r][c] = opp_color
                        if step_collector is not None:
                            step_collector.append((r, c, opp_color, f"Avoid Identical Adjacent Col {c + 1}-{c + 2}"))
                        changed = True

                elif len(empty_in_col2) == 1 and len(empty_in_col1) == 0:
                    r = empty_in_col2[0]
                    if all(col1[i] == col2[i] for i in range(size) if i != r):
                        opp_color = 3 - col1[r]
                        b[r][c + 1] = opp_color
                        if step_collector is not None:
                            step_collector.append((r, c + 1, opp_color, f"Avoid Identical Adjacent Col {c + 1}-{c + 2}"))
                        changed = True

            # --- 3. Moore Neighborhood Clue Deductions ---
            for r in range(size):
                for c in range(size):
                    k = clues[r][c]
                    if k is None:
                        continue

                    neighbors = self._get_neighbors(r, c, size)
                    color = b[r][c]

                    if color == UrjoState.EMPTY:
                        # Test if Red hypothesis is feasible
                        red_same = sum(1 for nr, nc in neighbors if b[nr][nc] == UrjoState.COLOR_RED)
                        red_empty = sum(1 for nr, nc in neighbors if b[nr][nc] == UrjoState.EMPTY)
                        red_possible = (red_same <= k <= red_same + red_empty)

                        # Test if Blue hypothesis is feasible
                        blue_same = sum(1 for nr, nc in neighbors if b[nr][nc] == UrjoState.COLOR_BLUE)
                        blue_empty = sum(1 for nr, nc in neighbors if b[nr][nc] == UrjoState.EMPTY)
                        blue_possible = (blue_same <= k <= blue_same + blue_empty)

                        if not red_possible and not blue_possible:
                            return False
                        elif red_possible and not blue_possible:
                            b[r][c] = UrjoState.COLOR_RED
                            if step_collector is not None:
                                step_collector.append((r, c, UrjoState.COLOR_RED, f"Clue {k} Forces Color"))
                            changed = True
                            color = UrjoState.COLOR_RED
                        elif blue_possible and not red_possible:
                            b[r][c] = UrjoState.COLOR_BLUE
                            if step_collector is not None:
                                step_collector.append((r, c, UrjoState.COLOR_BLUE, f"Clue {k} Forces Color"))
                            changed = True
                            color = UrjoState.COLOR_BLUE

                    if color != UrjoState.EMPTY:
                        same = sum(1 for nr, nc in neighbors if b[nr][nc] == color)
                        empty_nbrs = [(nr, nc) for nr, nc in neighbors if b[nr][nc] == UrjoState.EMPTY]
                        empty_count = len(empty_nbrs)

                        if same > k or same + empty_count < k:
                            return False

                        opp_color = 3 - color

                        # All remaining empty must be opposite color
                        if same == k and empty_count > 0:
                            for nr, nc in empty_nbrs:
                                b[nr][nc] = opp_color
                                if step_collector is not None:
                                    step_collector.append((nr, nc, opp_color, f"Clue ({r + 1},{c + 1})={k} Saturated"))
                                changed = True

                        # All remaining empty must be same color
                        elif same + empty_count == k and empty_count > 0:
                            for nr, nc in empty_nbrs:
                                b[nr][nc] = color
                                if step_collector is not None:
                                    step_collector.append((nr, nc, color, f"Clue ({r + 1},{c + 1})={k} Demands Color"))
                                changed = True

        return True

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False,
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, UrjoState):
            raise TypeError("Expected UrjoState")

        working_state = initial_state.clone()
        size = working_state.grid_size
        timeline_steps: List[SolverStep] = []

        start_step = SolverStep(
            state=initial_state.clone(),
            action_desc=f"Initial Urjo {size}x{size} Setup",
            metrics={"size": size},
        )
        if stream_search:
            yield start_step
        timeline_steps.append(start_step)

        # 1. Deterministic propagation pass
        initial_board = [list(r) for r in working_state.board]
        logic_steps: List[Tuple[int, int, int, str]] = []

        if not self._propagate(initial_board, working_state.clues, size, step_collector=logic_steps):
            raise ValueError("Contradiction detected in initial Urjo clues and board state.")

        for r, c, color, reason in logic_steps:
            working_state.board[r][c] = color
            color_name = "Red" if color == UrjoState.COLOR_RED else "Blue"
            step = SolverStep(
                state=working_state.clone(),
                action_desc=f"{reason}: ({r + 1}, {c + 1}) = {color_name}",
                highlights={"r": r, "c": c},
            )
            if stream_search:
                yield step
            timeline_steps.append(step)

        # 2. Backtracking search with forward-checking
        def _backtrack_search(current_board: List[List[int]]) -> Optional[List[List[int]]]:
            # Find best empty cell (heuristically prefer cells adjacent to clues)
            best_pos = None
            max_clue_adjacency = -1

            for r in range(size):
                for c in range(size):
                    if current_board[r][c] == UrjoState.EMPTY:
                        clue_adj = sum(
                            1 for nr, nc in self._get_neighbors(r, c, size)
                            if working_state.clues[nr][nc] is not None
                        )
                        if clue_adj > max_clue_adjacency:
                            max_clue_adjacency = clue_adj
                            best_pos = (r, c)

            if best_pos is None:
                # All cells filled! Check state validity
                temp_state = UrjoState(size, current_board, working_state.clues, working_state.givens)
                if temp_state.is_solved():
                    return current_board
                return None

            er, ec = best_pos
            for candidate in [UrjoState.COLOR_RED, UrjoState.COLOR_BLUE]:
                branch_board = [list(row) for row in current_board]
                branch_board[er][ec] = candidate

                branch_steps: List[Tuple[int, int, int, str]] = []
                if self._propagate(branch_board, working_state.clues, size, step_collector=branch_steps):
                    result = _backtrack_search(branch_board)
                    if result is not None:
                        color_name = "Red" if candidate == UrjoState.COLOR_RED else "Blue"
                        step = SolverStep(
                            state=UrjoState(size, [list(r) for r in branch_board], working_state.clues, working_state.givens),
                            action_desc=f"Branch Deduction: ({er + 1}, {ec + 1}) = {color_name}",
                            highlights={"r": er, "c": ec},
                        )
                        timeline_steps.append(step)
                        return result

            return None

        has_empty = any(UrjoState.EMPTY in row for row in working_state.board)
        if has_empty:
            solved_board = _backtrack_search(initial_board)
            if solved_board is None:
                raise ValueError("No valid Urjo solution exists for this configuration.")

            final_state = UrjoState(size, solved_board, working_state.clues, working_state.givens)
            final_step = SolverStep(
                state=final_state,
                action_desc="Solved: All Urjo constraints satisfied!",
                highlights={},
            )
            timeline_steps.append(final_step)

        if not stream_search:
            for step in timeline_steps:
                yield step
