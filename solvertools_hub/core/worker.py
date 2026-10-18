"""
worker.py - Background QThread execution engine for puzzle solvers.
Maintains a responsive UI during heavy searches and provides dual-mode execution:
1. Timeline Buffering (Playback): buffers steps into a scrubbable list[SolverStep].
2. Instant Mode: runs generator at full CPython speed, emitting only the final solution.
"""

import time
from typing import List

from loguru import logger
from PySide6.QtCore import QThread, Signal

from .base_plugin import BasePuzzleState, BaseSolver, SolverStep


class SolverWorker(QThread):
    """Executes a BaseSolver generator in a dedicated background worker thread."""
    finished_timeline = Signal(list, float)      # (List[SolverStep], elapsed_seconds)
    finished_instant = Signal(list, int, float)  # (List[SolverStep], total_step_count, elapsed_seconds)
    failed = Signal(str)                         # Error message
    progress_step = Signal(object)               # (SolverStep) for optional real-time streaming

    def __init__(
        self,
        solver: BaseSolver,
        initial_state: BasePuzzleState,
        instant_mode: bool = False,
        stream_search: bool = False,
    ):
        super().__init__()
        self.solver = solver
        self.initial_state = initial_state.clone()
        self.instant_mode = instant_mode
        self.stream_search = stream_search
        self._abort = False

    def abort(self) -> None:
        """Signals the running solver to terminate gracefully."""
        self._abort = True

    def run(self) -> None:
        start_time = time.perf_counter()
        try:
            gen = self.solver.solve(self.initial_state, stream_search=self.stream_search)

            if self.instant_mode:
                timeline: List[SolverStep] = []
                for step in gen:
                    if self._abort:
                        logger.info("Instant solve aborted by user.")
                        return
                    timeline.append(step)

                elapsed = time.perf_counter() - start_time
                if not timeline:
                    self.failed.emit("Solver exhausted search space without finding a solution.")
                else:
                    self.finished_instant.emit(timeline, len(timeline), elapsed)
            else:
                timeline: List[SolverStep] = []
                for step in gen:
                    if self._abort:
                        logger.info("Timeline solve aborted by user.")
                        return
                    timeline.append(step)
                    if self.stream_search:
                        self.progress_step.emit(step)

                elapsed = time.perf_counter() - start_time
                if not timeline:
                    self.failed.emit("Solver exhausted search space without finding a solution.")
                else:
                    self.finished_timeline.emit(timeline, elapsed)

        except Exception as exc:
            logger.exception("Solver execution failed with exception")
            self.failed.emit(f"Solver Exception: {exc}")
