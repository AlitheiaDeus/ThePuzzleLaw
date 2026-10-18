"""
solver.py - High-performance constraint-propagating solver for Unruly binary puzzles.
Combines deterministic deduction (avoid triples, fill sandwiches, balance counting, edge constraints)
with forward-checking constraint propagation during backtracking search.
"""

from typing import Generator, List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import UnrulyState


class UnrulySolver(BaseSolver):
    """Fast constraint-propagating hybrid solver for Unruly binary puzzles."""

    def _is_edge_valid(self, b: List[List[int]], r: int, c: int, state: UnrulyState) -> bool:
        color = b[r][c]
        if color == UnrulyState.EMPTY:
            return True

        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < state.grid_size and 0 <= nc < state.grid_size:
                p1 = f"{min(r, nr)},{min(c, nc)}" if (r, c) < (nr, nc) else f"{nr},{nc}"
                p2 = f"{max(r, nr)},{max(c, nc)}" if (r, c) < (nr, nc) else f"{r},{c}"
                key = f"{p1}-{p2}"
                if key in state.edge_constraints:
                    neighbor_val = b[nr][nc]
                    if neighbor_val != UnrulyState.EMPTY:
                        constraint = state.edge_constraints[key]
                        if constraint == "equal" and color != neighbor_val:
                            return False
                        elif constraint == "opposite" and color == neighbor_val:
                            return False
        return True

    def _propagate(self, b: List[List[int]], state: UnrulyState, step_collector: Optional[List[Tuple[int, int, int, str]]] = None) -> bool:
        size = state.grid_size
        half = size // 2
        changed = True

        while changed:
            changed = False

            # Validity checks
            for r in range(size):
                if not state.is_line_valid(b[r]):
                    return False
            for c in range(size):
                col = [b[r][c] for r in range(size)]
                if not state.is_line_valid(col):
                    return False

            # 1. Avoid Triples & Sandwiches (Rows)
            for r in range(size):
                for c in range(size - 1):
                    if b[r][c] != UnrulyState.EMPTY and b[r][c] == b[r][c + 1]:
                        other = 3 - b[r][c]
                        if c > 0 and b[r][c - 1] == UnrulyState.EMPTY:
                            b[r][c - 1] = other
                            if not self._is_edge_valid(b, r, c - 1, state):
                                return False
                            if step_collector is not None:
                                step_collector.append((r, c - 1, other, "Avoid Triple"))
                            changed = True
                        if c < size - 2 and b[r][c + 2] == UnrulyState.EMPTY:
                            b[r][c + 2] = other
                            if not self._is_edge_valid(b, r, c + 2, state):
                                return False
                            if step_collector is not None:
                                step_collector.append((r, c + 2, other, "Avoid Triple"))
                            changed = True

                for c in range(size - 2):
                    if b[r][c] != UnrulyState.EMPTY and b[r][c] == b[r][c + 2] and b[r][c + 1] == UnrulyState.EMPTY:
                        other = 3 - b[r][c]
                        b[r][c + 1] = other
                        if not self._is_edge_valid(b, r, c + 1, state):
                            return False
                        if step_collector is not None:
                            step_collector.append((r, c + 1, other, "Fill Sandwich"))
                        changed = True

                # Row balance count
                ca, cb = b[r].count(UnrulyState.COLOR_A), b[r].count(UnrulyState.COLOR_B)
                fill_color = UnrulyState.COLOR_B if ca == half and cb < half else (UnrulyState.COLOR_A if cb == half and ca < half else None)
                if fill_color:
                    for c in range(size):
                        if b[r][c] == UnrulyState.EMPTY:
                            b[r][c] = fill_color
                            if not self._is_edge_valid(b, r, c, state):
                                return False
                            if step_collector is not None:
                                step_collector.append((r, c, fill_color, "Balance Count"))
                            changed = True

            # 2. Avoid Triples & Sandwiches (Columns)
            for c in range(size):
                col = [b[r][c] for r in range(size)]
                for r in range(size - 1):
                    if b[r][c] != UnrulyState.EMPTY and b[r][c] == b[r + 1][c]:
                        other = 3 - b[r][c]
                        if r > 0 and b[r - 1][c] == UnrulyState.EMPTY:
                            b[r - 1][c] = other
                            if not self._is_edge_valid(b, r - 1, c, state):
                                return False
                            if step_collector is not None:
                                step_collector.append((r - 1, c, other, "Avoid Triple"))
                            changed = True
                        if r < size - 2 and b[r + 2][c] == UnrulyState.EMPTY:
                            b[r + 2][c] = other
                            if not self._is_edge_valid(b, r + 2, c, state):
                                return False
                            if step_collector is not None:
                                step_collector.append((r + 2, c, other, "Avoid Triple"))
                            changed = True

                for r in range(size - 2):
                    if b[r][c] != UnrulyState.EMPTY and b[r][c] == b[r + 2][c] and b[r + 1][c] == UnrulyState.EMPTY:
                        other = 3 - b[r][c]
                        b[r + 1][c] = other
                        if not self._is_edge_valid(b, r + 1, c, state):
                            return False
                        if step_collector is not None:
                            step_collector.append((r + 1, c, other, "Fill Sandwich"))
                        changed = True

                # Column balance count
                ca, cb = col.count(UnrulyState.COLOR_A), col.count(UnrulyState.COLOR_B)
                fill_color = UnrulyState.COLOR_B if ca == half and cb < half else (UnrulyState.COLOR_A if cb == half and ca < half else None)
                if fill_color:
                    for r in range(size):
                        if b[r][c] == UnrulyState.EMPTY:
                            b[r][c] = fill_color
                            if not self._is_edge_valid(b, r, c, state):
                                return False
                            if step_collector is not None:
                                step_collector.append((r, c, fill_color, "Balance Count"))
                            changed = True

        return True

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, UnrulyState):
            raise TypeError("Expected UnrulyState")

        working_state = initial_state.clone()
        size = working_state.grid_size
        timeline_steps: List[SolverStep] = []

        start_step = SolverStep(
            state=initial_state.clone(),
            action_desc="Initial Given Tiles",
            metrics={"size": size},
        )
        if stream_search:
            yield start_step
        timeline_steps.append(start_step)

        # 1. Run initial deterministic logic pass
        initial_board = [list(r) for r in working_state.board]
        logic_steps: List[Tuple[int, int, int, str]] = []
        if not self._propagate(initial_board, working_state, step_collector=logic_steps):
            raise ValueError("Contradiction detected in initial Unruly constraints.")

        for r, c, color, reason in logic_steps:
            working_state.board[r][c] = color
            color_name = "Sky" if color == UnrulyState.COLOR_A else "Peach"
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
            # Find first empty cell
            empty_pos = None
            for r in range(size):
                for c in range(size):
                    if current_board[r][c] == UnrulyState.EMPTY:
                        empty_pos = (r, c)
                        break
                if empty_pos:
                    break

            if empty_pos is None:
                # Board completely filled! Check uniqueness if enabled
                if working_state.unique_rows_cols:
                    rows = {tuple(r) for r in current_board}
                    if len(rows) != size:
                        return None
                    cols = {tuple(current_board[r][c] for r in range(size)) for c in range(size)}
                    if len(cols) != size:
                        return None
                return current_board

            er, ec = empty_pos
            for candidate_color in [UnrulyState.COLOR_A, UnrulyState.COLOR_B]:
                branch_board = [list(row) for row in current_board]
                branch_board[er][ec] = candidate_color
                if not self._is_edge_valid(branch_board, er, ec, working_state):
                    continue

                branch_steps: List[Tuple[int, int, int, str]] = []
                if self._propagate(branch_board, working_state, step_collector=branch_steps):
                    result = _backtrack_search(branch_board)
                    if result is not None:
                        # Record successful branch steps
                        color_name = "Sky" if candidate_color == UnrulyState.COLOR_A else "Peach"
                        step = SolverStep(
                            state=UnrulyState(size, [list(row) for row in branch_board], working_state.edge_constraints),
                            action_desc=f"Branch Choice: ({er + 1}, {ec + 1}) = {color_name}",
                            highlights={"r": er, "c": ec},
                        )
                        timeline_steps.append(step)
                        return result

            return None

        has_empty = any(UnrulyState.EMPTY in row for row in working_state.board)
        if has_empty:
            solved_board = _backtrack_search(initial_board)
            if solved_board is None:
                raise ValueError("No valid Unruly solution exists for this configuration.")
            final_step = SolverStep(
                state=UnrulyState(size, solved_board, working_state.edge_constraints),
                action_desc="Solved: All constraints satisfied!",
                highlights={},
            )
            timeline_steps.append(final_step)

        if not stream_search:
            for step in timeline_steps:
                yield step
