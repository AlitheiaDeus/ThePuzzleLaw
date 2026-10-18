"""
solver.py - A* Manhattan Distance solver for the Sliding Tile (N-Puzzle).
Yields step-by-step SolverStep playback states with move descriptions and neon highlights.
"""

import heapq
from typing import Generator, List, Tuple

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import SlidingTileState


class SlidingTileSolver(BaseSolver):
    """A* graph search using Manhattan distance heuristic."""

    def _manhattan(self, grid: Tuple[int, ...], size: int) -> int:
        dist = 0
        for idx, val in enumerate(grid):
            if val == 0:
                continue
            target_idx = val - 1
            r1, c1 = divmod(idx, size)
            r2, c2 = divmod(target_idx, size)
            dist += abs(r1 - r2) + abs(c1 - c2)
        return dist

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, SlidingTileState):
            raise TypeError("Expected SlidingTileState")

        size = initial_state.size
        start_tuple = tuple(initial_state.grid)
        goal_tuple = tuple(list(range(1, size * size)) + [0])

        pq = [(self._manhattan(start_tuple, size), 0, start_tuple, [])]
        visited = {start_tuple: 0}
        nodes_expanded = 0

        while pq:
            f, g, current, path = heapq.heappop(pq)
            nodes_expanded += 1

            if stream_search:
                yield SolverStep(
                    state=SlidingTileState(size, list(current)),
                    action_desc=f"Exploring node (g={g}, h={f-g})",
                    highlights={"active_idx": current.index(0)},
                    metrics={"expanded": nodes_expanded, "depth": g},
                )

            if current == goal_tuple:
                # Yield full solution sequence for playback scrubber
                yield SolverStep(
                    state=SlidingTileState(size, list(start_tuple)),
                    action_desc="Start State",
                    highlights={"active_idx": start_tuple.index(0)},
                    metrics={"expanded": nodes_expanded, "step": 0, "total": len(path)},
                )
                for step_num, (grid_snap, desc, moved_idx) in enumerate(path, 1):
                    yield SolverStep(
                        state=SlidingTileState(size, list(grid_snap)),
                        action_desc=desc,
                        highlights={"moved_idx": moved_idx, "active_idx": grid_snap.index(0)},
                        metrics={"expanded": nodes_expanded, "step": step_num, "total": len(path)},
                    )
                return

            zero_idx = current.index(0)
            zr, zc = divmod(zero_idx, size)

            for dr, dc, move_name in [(-1, 0, "Down"), (1, 0, "Up"), (0, -1, "Right"), (0, 1, "Left")]:
                nr, nc = zr + dr, zc + dc
                if 0 <= nr < size and 0 <= nc < size:
                    n_idx = nr * size + nc
                    nxt = list(current)
                    tile_val = nxt[n_idx]
                    nxt[zero_idx], nxt[n_idx] = nxt[n_idx], nxt[zero_idx]
                    nxt_t = tuple(nxt)
                    new_g = g + 1

                    if nxt_t not in visited or new_g < visited[nxt_t]:
                        visited[nxt_t] = new_g
                        h = self._manhattan(nxt_t, size)
                        desc = f"Slide Tile {tile_val} {move_name}"
                        heapq.heappush(pq, (new_g + h, new_g, nxt_t, path + [(nxt_t, desc, zero_idx)]))
