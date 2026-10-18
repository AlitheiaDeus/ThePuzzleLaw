"""
solver.py - Hybrid logic and backtracking solver for arbitrary Sudoku grids.
Applies deterministic deduction (Naked Singles, Hidden Singles) first,
falling back to MRV (Minimum Remaining Values) backtracking only when logic stalls.
"""

from typing import Generator, List, Optional, Set, Tuple

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import SudokuState


class SudokuSolver(BaseSolver):
    """Hybrid logic deduction + recursive backtracking Sudoku solver."""

    def _get_peers(self, r: int, c: int, state: SudokuState) -> Set[Tuple[int, int]]:
        peers = set()
        dim = state.grid_dim
        # Row & Column
        for i in range(dim):
            if i != c:
                peers.add((r, i))
            if i != r:
                peers.add((i, c))
        # Box
        start_row = r - (r % state.box_h)
        start_col = c - (c % state.box_w)
        for i in range(state.box_h):
            for j in range(state.box_w):
                if (start_row + i, start_col + j) != (r, c):
                    peers.add((start_row + i, start_col + j))
        return peers

    def _get_initial_candidates(
        self, state: SudokuState
    ) -> List[List[Set[int]]]:
        candidates: List[List[Set[int]]] = [
            [set() for _ in range(state.grid_dim)] for _ in range(state.grid_dim)
        ]
        for r in range(state.grid_dim):
            for c in range(state.grid_dim):
                if state.board[r][c] == 0:
                    possible = set(range(1, state.grid_dim + 1))
                    for pr, pc in self._get_peers(r, c, state):
                        val = state.board[pr][pc]
                        if val != 0:
                            possible.discard(val)
                    candidates[r][c] = possible
        return candidates

    def _is_safe(self, board: List[List[int]], num: int, r: int, c: int, state: SudokuState) -> bool:
        for pr, pc in self._get_peers(r, c, state):
            if board[pr][pc] == num:
                return False
        return True

    def _find_mrv_cell(
        self, board: List[List[int]], candidates: List[List[Set[int]]], state: SudokuState
    ) -> Optional[Tuple[int, int]]:
        min_len = state.grid_dim + 1
        best_pos = None
        for r in range(state.grid_dim):
            for c in range(state.grid_dim):
                if board[r][c] == 0:
                    count = len(candidates[r][c])
                    if count < min_len:
                        min_len = count
                        best_pos = (r, c)
                        if count <= 1:
                            return best_pos
        return best_pos

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, SudokuState):
            raise TypeError("Expected SudokuState")

        working_state = initial_state.clone()
        board = working_state.board
        candidates = self._get_initial_candidates(working_state)

        timeline_steps: List[SolverStep] = []
        logic_count = 0
        backtrack_count = 0

        # Initial starting step
        start_step = SolverStep(
            state=initial_state.clone(),
            action_desc="Initial Given Clues",
            metrics={"logic_deductions": 0, "backtracks": 0},
        )
        if stream_search:
            yield start_step
        timeline_steps.append(start_step)

        # -----------------------------------------------------------------
        # Phase 1: Deterministic Logic Loop (Naked & Hidden Singles)
        # -----------------------------------------------------------------
        stalled = False
        while not stalled:
            stalled = True

            # Strategy 1: Naked Singles
            for r in range(working_state.grid_dim):
                for c in range(working_state.grid_dim):
                    if board[r][c] == 0 and len(candidates[r][c]) == 1:
                        num = candidates[r][c].pop()
                        board[r][c] = num
                        logic_count += 1
                        stalled = False

                        # Update peers
                        for pr, pc in self._get_peers(r, c, working_state):
                            candidates[pr][pc].discard(num)

                        step = SolverStep(
                            state=working_state.clone(),
                            action_desc=f"Naked Single: ({r + 1}, {c + 1}) = {num}",
                            highlights={"r": r, "c": c},
                            metrics={"logic_deductions": logic_count, "backtracks": backtrack_count},
                        )
                        if stream_search:
                            yield step
                        timeline_steps.append(step)

            # Strategy 2: Hidden Singles
            if stalled:
                for unit in working_state.get_all_units():
                    for num in range(1, working_state.grid_dim + 1):
                        places = [
                            (r, c)
                            for r, c in unit
                            if board[r][c] == 0 and num in candidates[r][c]
                        ]
                        if len(places) == 1:
                            r, c = places[0]
                            board[r][c] = num
                            candidates[r][c] = set()
                            logic_count += 1
                            stalled = False

                            for pr, pc in self._get_peers(r, c, working_state):
                                candidates[pr][pc].discard(num)

                            step = SolverStep(
                                state=working_state.clone(),
                                action_desc=f"Hidden Single in unit: ({r + 1}, {c + 1}) = {num}",
                                highlights={"r": r, "c": c},
                                metrics={"logic_deductions": logic_count, "backtracks": backtrack_count},
                            )
                            if stream_search:
                                yield step
                            timeline_steps.append(step)

        # -----------------------------------------------------------------
        # Phase 2: MRV Recursive Backtracking (if unsolved)
        # -----------------------------------------------------------------
        def _backtrack() -> bool:
            nonlocal backtrack_count
            mrv_cell = self._find_mrv_cell(board, candidates, working_state)
            if not mrv_cell:
                return True  # All cells filled!

            r, c = mrv_cell
            possible_nums = [
                n for n in sorted(list(candidates[r][c]))
                if self._is_safe(board, n, r, c, working_state)
            ]

            for num in possible_nums:
                backtrack_count += 1
                board[r][c] = num

                if stream_search:
                    yield SolverStep(
                        state=working_state.clone(),
                        action_desc=f"Trial Guess: ({r + 1}, {c + 1}) = {num}",
                        highlights={"r": r, "c": c},
                        metrics={"logic_deductions": logic_count, "backtracks": backtrack_count},
                    )

                if (yield from _backtrack()):
                    step = SolverStep(
                        state=working_state.clone(),
                        action_desc=f"Confirmed Choice: ({r + 1}, {c + 1}) = {num}",
                        highlights={"r": r, "c": c},
                        metrics={"logic_deductions": logic_count, "backtracks": backtrack_count},
                    )
                    timeline_steps.append(step)
                    return True

                # Undo trial
                board[r][c] = 0

            return False

        has_empty = any(0 in row for row in board)
        if has_empty:
            success = yield from _backtrack()
            if not success:
                return

        # Yield entire buffered timeline for playback
        if not stream_search:
            for step in timeline_steps:
                yield step
