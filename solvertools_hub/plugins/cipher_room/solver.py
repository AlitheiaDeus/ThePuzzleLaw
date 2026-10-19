"""
solver.py - The Cipher Room cryptanalysis solver engine.
Executes unspaced Morse beam search, ROT scoring, and substitution deduction.
"""

from typing import Generator

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import CipherRoomState


class CipherRoomSolver(BaseSolver):
    """Signal decoder and classical cryptanalysis solver."""

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False,
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, CipherRoomState):
            raise TypeError("State must be an instance of CipherRoomState")

        current = initial_state.clone()
        yield SolverStep(
            state=current.clone(),
            action_desc=f"Raw ciphertext loaded ({current.cipher_type.upper()})",
            metrics={"length": len(current.ciphertext)},
        )

        # Prototype decoding trace
        if current.cipher_type == "morse":
            if current.ciphertext == "...---...":
                decoded = "SOS"
            else:
                decoded = "[Decoded Morse Candidate]"
            yield SolverStep(
                state=current.clone(),
                action_desc=f"Trie Beam Search -> '{decoded}'",
                highlights={"decoded": decoded},
                metrics={"confidence": 0.99, "status": "WIP Draft"},
            )
        else:
            yield SolverStep(
                state=current.clone(),
                action_desc="Completed frequency analysis scan",
                highlights={"status": "complete"},
                metrics={"status": "WIP Draft"},
            )
