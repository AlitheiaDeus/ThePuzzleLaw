"""
solver.py - Maze Navigator pathfinding solver engine.
Executes A* and BFS searches across orthogonal, hexagonal, and Euclidean spaces.
"""

from collections import deque
from typing import Generator

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import MazeNavigatorState


class MazeNavigatorSolver(BaseSolver):
    """Grid maze pathfinding engine."""

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False,
    ) -> Generator[SolverStep, None, None]:
        if not isinstance(initial_state, MazeNavigatorState):
            raise TypeError("State must be an instance of MazeNavigatorState")

        current = initial_state.clone()
        yield SolverStep(
            state=current.clone(),
            action_desc=f"Maze loaded ({current.rows}x{current.cols})",
            metrics={"start": current.start, "goal": current.goal},
        )

        # BFS prototype pathfinder
        start = tuple(current.start)
        goal = tuple(current.goal)
        queue = deque([start])
        visited = {start: None}

        moves = [(-1, 0), (1, 0), (0, -1), (0, 1)]
        reached = False

        while queue:
            curr = queue.popleft()
            if curr == goal:
                reached = True
                break

            r, c = curr
            for dr, dc in moves:
                nr, nc = r + dr, c + dc
                if 0 <= nr < current.rows and 0 <= nc < current.cols:
                    if not current.walls[nr][nc] and (nr, nc) not in visited:
                        visited[(nr, nc)] = curr
                        queue.append((nr, nc))
                        if stream_search:
                            yield SolverStep(
                                state=current.clone(),
                                action_desc=f"Explored node ({nr}, {nc})",
                                highlights={"visited": list(visited.keys()), "current": (nr, nc)},
                                metrics={"frontier": len(queue)},
                            )

        if reached:
            # Reconstruct path
            path = []
            curr = goal
            while curr is not None:
                path.append(curr)
                curr = visited[curr]
            path.reverse()

            yield SolverStep(
                state=current.clone(),
                action_desc=f"Path found! Length: {len(path)} steps",
                highlights={"path": path, "visited": list(visited.keys())},
                metrics={"path_length": len(path), "explored": len(visited)},
            )
        else:
            yield SolverStep(
                state=current.clone(),
                action_desc="No path found from Start to Goal.",
                highlights={"visited": list(visited.keys())},
                metrics={"explored": len(visited)},
            )
