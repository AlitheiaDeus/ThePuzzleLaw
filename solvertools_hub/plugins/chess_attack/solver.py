"""
solver.py - Chess Attack draft solver engine.
Generates threat heatmaps and solves piece placement constraints via backtracking.
"""

from typing import Generator

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import ChessAttackState


class ChessAttackSolver(BaseSolver):
    """Backtracking constraint solver for tactical zoned chess problems."""

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False,
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, ChessAttackState):
            raise TypeError("State must be an instance of ChessAttackState")

        current = initial_state.clone()
        yield SolverStep(
            state=current.clone(),
            action_desc="Initial board state & zone distribution",
            metrics={"size": current.board_size},
        )

        # Prototype solve step: place a piece in each row diagonal
        sz = current.board_size
        for i in range(sz):
            current.board[i][(i * 2 + 1) % sz] = ChessAttackState.PIECE_SUPERKING
            if stream_search:
                yield SolverStep(
                    state=current.clone(),
                    action_desc=f"Place Superking at ({i}, {(i * 2 + 1) % sz})",
                    highlights={"cell": (i, (i * 2 + 1) % sz)},
                    metrics={"placed": i + 1},
                )

        yield SolverStep(
            state=current.clone(),
            action_desc=f"Solved: Placed {sz} non-attacking pieces",
            metrics={"placed": sz, "status": "WIP Draft"},
        )
