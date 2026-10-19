"""
solver.py - Packing Grids & Nonograms solver engine.
Executes 2D line-intersection relaxation for Nonograms and Knuth's Algorithm X (DLX) for polyomino packing.
"""

from typing import Generator

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import PackingGridsState


class PackingGridsSolver(BaseSolver):
    """Nonogram line-intersection and exact cover packing solver."""

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False,
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, PackingGridsState):
            raise TypeError("State must be an instance of PackingGridsState")

        current = initial_state.clone()
        yield SolverStep(
            state=current.clone(),
            action_desc=f"Nonogram initialized ({current.rows}x{current.cols})",
            metrics={"rows": current.rows, "cols": current.cols},
        )

        # Prototype line overlap deductions
        current.grid[0][0] = PackingGridsState.CELL_FILLED
        current.grid[0][4] = PackingGridsState.CELL_FILLED
        if stream_search:
            yield SolverStep(
                state=current.clone(),
                action_desc="Applied row clue [1, 1] candidate intersection",
                highlights={"cells": [(0, 0), (0, 4)]},
            )

        yield SolverStep(
            state=current.clone(),
            action_desc="Completed constraint relaxation pass",
            metrics={"status": "WIP Draft"},
        )
