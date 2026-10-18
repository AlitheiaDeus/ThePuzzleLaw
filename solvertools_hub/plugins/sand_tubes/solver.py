"""
solver.py - A* PriorityQueue pouring solver for Liquid Sorter Pro.
Uses an admissible color-transition heuristic, variable-capacity symmetry breaking,
and partial pour handling to identify the optimal move sequence.
"""

import heapq
from typing import Generator, List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import SandTubeState


class PriorityQueue:
    """Heapq-backed PriorityQueue for A* search."""
    def __init__(self):
        self.elements = []
        self._counter = 0

    def empty(self) -> bool:
        return len(self.elements) == 0

    def put(self, item, priority: int) -> None:
        heapq.heappush(self.elements, (priority, self._counter, item))
        self._counter += 1

    def get(self):
        return heapq.heappop(self.elements)[2]


class SandTubeSolver(BaseSolver):
    """A* PriorityQueue solver with variable-capacity symmetry breaking."""

    def _heuristic(self, tubes: Tuple[Tuple[int, ...], ...]) -> int:
        """
        Admissible heuristic: counts adjacent color transitions within all tubes.
        Each move can reduce at most 1 transition. Goal state has 0 transitions.
        """
        transitions = 0
        for t in tubes:
            for k in range(1, len(t)):
                if t[k] != t[k - 1]:
                    transitions += 1
        return transitions

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, SandTubeState):
            raise TypeError("Expected SandTubeState")

        capacities = list(initial_state.capacities)
        num_tubes = len(capacities)

        # Early check
        if not initial_state.allow_split_colors:
            possible, reason = initial_state.can_satisfy_unique_capacities()
            if not possible:
                raise ValueError(f"Unsolvable configuration: {reason}")

        # Stacks stored as tuples bottom-to-top (filtering any empty slot Nones)
        start_tubes = tuple(tuple(c for c in t if c is not None) for t in initial_state.tubes)

        def normalize_state(tubes_tuple: Tuple[Tuple[int, ...], ...]) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
            """Sorts tubes by (capacity, contents) to break identical-capacity empty tube symmetries."""
            return tuple(sorted((capacities[i], tubes_tuple[i]) for i in range(num_tubes)))

        start_norm = normalize_state(start_tubes)
        frontier = PriorityQueue()
        frontier.put((start_tubes, []), 0)
        cost_so_far = {start_norm: 0}
        expanded = 0

        # Initial start step
        initial_step = SolverStep(
            state=initial_state.clone(),
            action_desc="Initial Tubes",
            metrics={"expanded": 0, "tubes": num_tubes},
        )
        if stream_search:
            yield initial_step

        from collections import Counter
        total_color_counts = Counter(item for t in initial_state.tubes for item in t if item is not None)

        while not frontier.empty():
            curr_tubes, path = frontier.get()
            expanded += 1

            # Check goal condition
            st_test = SandTubeState(
                tubes=[list(t) for t in curr_tubes],
                capacity=capacities,
                allow_split_colors=initial_state.allow_split_colors,
            )

            if stream_search:
                yield SolverStep(
                    state=st_test,
                    action_desc=f"Evaluating node #{expanded} (depth={len(path)})",
                    metrics={"expanded": expanded, "depth": len(path)},
                )

            if st_test.is_solved():
                # Yield full solution sequence for playback scrubber
                if not stream_search:
                    yield initial_step

                replay_tubes = [[c for c in t if c is not None] for t in initial_state.tubes]
                for step_idx, (src, dst, pour_amount, desc) in enumerate(path, 1):
                    pour_items = [replay_tubes[src].pop() for _ in range(pour_amount)]
                    replay_tubes[dst].extend(pour_items)
                    step_state = SandTubeState(
                        tubes=[list(t) for t in replay_tubes],
                        capacity=capacities,
                        allow_split_colors=initial_state.allow_split_colors,
                    )
                    yield SolverStep(
                        state=step_state,
                        action_desc=desc,
                        highlights={"src": src, "dst": dst},
                        metrics={"expanded": expanded, "step": step_idx, "total": len(path)},
                    )
                return

            # Find first available empty stack for each capacity (symmetry breaking)
            first_empty_by_cap = {}
            for j, t in enumerate(curr_tubes):
                if len(t) == 0:
                    cap_j = capacities[j]
                    if cap_j not in first_empty_by_cap:
                        first_empty_by_cap[cap_j] = j

            # Generate legal moves
            for i, src in enumerate(curr_tubes):
                if not src:
                    continue

                cap_i = capacities[i]
                # Skip pouring from an already completed monochrome tube only if it holds all items of that color
                if not initial_state.allow_split_colors:
                    if len(src) == cap_i and len(set(src)) == 1 and cap_i == total_color_counts.get(src[0]):
                        continue

                top_color = src[-1]
                # Count contiguous segments of top_color at the top of src stack
                block_size = 0
                for seg in reversed(src):
                    if seg == top_color:
                        block_size += 1
                    else:
                        break

                for j, dst in enumerate(curr_tubes):
                    if i == j:
                        continue

                    cap_j = capacities[j]
                    dst_len = len(dst)
                    available_space = cap_j - dst_len
                    if available_space <= 0:
                        continue

                    is_empty = (dst_len == 0)
                    # Symmetry breaking on empty targets
                    if is_empty and j != first_empty_by_cap.get(cap_j):
                        continue

                    # Target must either be empty or match top color
                    if is_empty or dst[-1] == top_color:
                        pour_amount = min(block_size, available_space)

                        # Prevent moving entire homogeneous partial tube into an equal-or-larger empty tube (pointless cycle)
                        if is_empty and pour_amount == len(src) and cap_j >= cap_i:
                            continue

                        # Construct successor state
                        next_tubes_list = [list(t) for t in curr_tubes]
                        poured = [next_tubes_list[i].pop() for _ in range(pour_amount)]
                        next_tubes_list[j].extend(poured)
                        next_tubes_t = tuple(tuple(t) for t in next_tubes_list)

                        next_norm = normalize_state(next_tubes_t)
                        new_cost = len(path) + 1

                        if next_norm not in cost_so_far or new_cost < cost_so_far[next_norm]:
                            cost_so_far[next_norm] = new_cost
                            h = self._heuristic(next_tubes_t)
                            priority = new_cost + h
                            move_desc = f"Pour Tube {i + 1} -> Tube {j + 1} ({pour_amount} seg)"
                            frontier.put(
                                (next_tubes_t, path + [(i, j, pour_amount, move_desc)]),
                                priority,
                            )

        raise ValueError("Search space exhausted without finding a valid pouring solution.")
