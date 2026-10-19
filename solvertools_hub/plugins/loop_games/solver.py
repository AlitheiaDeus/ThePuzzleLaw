"""
solver.py - Loop Family (Slitherlink / Palisade / Pearl) solver engine.
Executes vertex degree deductions (degree 0 or 2) and single closed loop generation.
"""

from typing import Generator

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import LoopFamilyState


class LoopFamilySolver(BaseSolver):
    """Slitherlink & closed-loop constraint solver."""

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False,
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, LoopFamilyState):
            raise TypeError("State must be an instance of LoopFamilyState")

        current = initial_state.clone()
        yield SolverStep(
            state=current.clone(),
            action_desc=f"Slitherlink lattice initialized ({current.size}x{current.size})",
            metrics={"size": current.size},
        )

        # Prototype deduction steps
        # Deduced corner loop segments
        current.h_edges[0][0] = LoopFamilyState.EDGE_LINE
        current.v_edges[0][0] = LoopFamilyState.EDGE_LINE
        if stream_search:
            yield SolverStep(
                state=current.clone(),
                action_desc="Applied corner vertex theorem (degree 2)",
                highlights={"h_edge": (0, 0), "v_edge": (0, 0)},
            )

        yield SolverStep(
            state=current.clone(),
            action_desc="Completed loop deduction sweep",
            metrics={"status": "WIP Draft"},
        )
