"""
solver.py - Exact linear algebra solver over GF(2) for Flip / Lights Out.
Constructs adjacency matrix and performs Gaussian elimination over Galois Field 2.
"""

from typing import Generator, List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import FlipState


class FlipSolver(BaseSolver):
    """Gaussian elimination solver over GF(2)."""

    def _solve_gf2(self, rows: int, cols: int, grid: List[List[int]]) -> Optional[List[int]]:
        size = rows * cols

        # 1. Build adjacency matrix A
        A = [[0] * size for _ in range(size)]
        for r in range(rows):
            for c in range(cols):
                idx = r * cols + c
                A[idx][idx] = 1  # Button affects itself
                if r > 0:
                    A[idx - cols][idx] = 1  # North
                if r < rows - 1:
                    A[idx + cols][idx] = 1  # South
                if c > 0:
                    A[idx - 1][idx] = 1  # West
                if c < cols - 1:
                    A[idx + 1][idx] = 1  # East

        b = [grid[r][c] for r in range(rows) for c in range(cols)]

        # Augment matrix
        for i in range(size):
            A[i].append(b[i])

        # 2. Gaussian elimination over GF(2)
        pivot_row = 0
        for j in range(size):
            if pivot_row >= size:
                break
            i = pivot_row
            while i < size and A[i][j] == 0:
                i += 1
            if i < size:
                # Row swap
                A[pivot_row], A[i] = A[i], A[pivot_row]
                for k in range(pivot_row + 1, size):
                    if A[k][j] == 1:
                        for l in range(j, size + 1):
                            A[k][l] ^= A[pivot_row][l]
                pivot_row += 1

        # 3. Check for solvability
        for i in range(pivot_row, size):
            if A[i][size] == 1:
                return None  # Inconsistent 0 = 1

        # 4. Back substitution
        x = [0] * size
        for i in range(pivot_row - 1, -1, -1):
            pivot_col = -1
            for j in range(size):
                if A[i][j] == 1:
                    pivot_col = j
                    break
            if pivot_col != -1:
                val = A[i][size]
                for j in range(pivot_col + 1, size):
                    val ^= (A[i][j] * x[j])
                x[pivot_col] = val

        return x

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, FlipState):
            raise TypeError("Expected FlipState")

        solution_vec = self._solve_gf2(initial_state.rows, initial_state.cols, initial_state.grid)
        if solution_vec is None:
            raise ValueError("This puzzle configuration is mathematically unsolvable.")

        press_coords: List[Tuple[int, int]] = []
        for idx, val in enumerate(solution_vec):
            if val == 1:
                r, c = divmod(idx, initial_state.cols)
                press_coords.append((r, c))

        # Initial step
        yield SolverStep(
            state=initial_state.clone(),
            action_desc=f"Start State (Total presses required: {len(press_coords)})",
            metrics={"press_count": len(press_coords)},
        )

        curr_state = initial_state.clone()
        for step_idx, (r, c) in enumerate(press_coords, 1):
            curr_state.toggle_cell_and_neighbors(r, c)
            yield SolverStep(
                state=curr_state.clone(),
                action_desc=f"Press button at ({r + 1}, {c + 1})",
                highlights={"press": (r, c)},
                metrics={"step": step_idx, "total_presses": len(press_coords)},
            )
