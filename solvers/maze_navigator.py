"""Maze Navigator pathfinder (A* & BFS on 2D grids with obstacles)."""

from __future__ import annotations

import heapq
from collections import deque
from typing import Any, Callable, Dict, Generator, List, Tuple

META: Dict[str, Any] = {
    "slug": "maze_navigator",
    "name": "Maze Navigator",
    "category": "Navigators / Geometry",
    "renderer": "grid",
    "description": "Finds shortest paths through 2D obstacle mazes using A* or BFS (0=open, 1=wall, 2=start, 3=goal).",
    "grid_meta": {
        "mode": "cycle",
        "min_val": 0,
        "max_val": 3,
        "labels": {"0": "", "1": "█", "2": "S", "3": "G"},
        "colors": {"0": "#232629", "1": "#621D19", "2": "#01CA6B", "3": "#FFE600"},
        "editable": True,
    },
    "presets": {
        "6x6": {
            "board": [
                [2, 0, 0, 1, 0, 0],
                [0, 1, 0, 1, 0, 0],
                [0, 1, 0, 0, 0, 1],
                [0, 1, 1, 1, 0, 0],
                [0, 0, 0, 1, 1, 0],
                [0, 0, 0, 0, 0, 3],
            ]
        },
        "7x7": {
            "board": [
                [2, 0, 1, 0, 0, 0, 0],
                [0, 0, 1, 0, 1, 1, 0],
                [1, 0, 0, 0, 1, 0, 0],
                [0, 0, 1, 1, 1, 0, 1],
                [0, 1, 0, 0, 0, 0, 0],
                [0, 1, 0, 1, 1, 1, 0],
                [0, 0, 0, 0, 0, 1, 3],
            ]
        },
        "9x9": {
            "board": [
                [2, 0, 1, 0, 0, 0, 1, 0, 0],
                [0, 0, 1, 0, 1, 0, 1, 0, 0],
                [0, 1, 1, 0, 1, 0, 0, 0, 1],
                [0, 0, 0, 0, 1, 1, 1, 0, 0],
                [1, 1, 1, 0, 0, 0, 1, 1, 0],
                [0, 0, 0, 1, 1, 0, 0, 0, 0],
                [0, 1, 0, 0, 0, 0, 1, 1, 0],
                [0, 1, 1, 1, 1, 0, 0, 0, 0],
                [0, 0, 0, 0, 1, 0, 1, 0, 3],
            ]
        },
    },
    "params": [
        {
            "key": "algorithm",
            "label": "Algorithm",
            "type": "select",
            "default": "A*",
            "options": ["A*", "BFS"],
        }
    ],
}


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    board = [list(r) for r in state["board"]]
    rows, cols = len(board), len(board[0])
    algo = str(params.get("algorithm", "A*"))

    start = next(((r, c) for r in range(rows) for c in range(cols) if board[r][c] == 2), (0, 0))
    goal = next(((r, c) for r in range(rows) for c in range(cols) if board[r][c] == 3), (rows - 1, cols - 1))

    yield {
        "type": "start",
        "state": {"board": board},
        "highlights": {"cells": [list(start), list(goal)], "color": "secondary"},
        "desc": f"{algo} search from {start} to {goal}",
        "stats": {"explored": 0},
    }

    parent: Dict[Tuple[int, int], Optional[Tuple[int, int]]] = {start: None}
    explored_order: List[Tuple[int, int]] = []
    reached = False

    if algo == "BFS":
        q = deque([start])
        while q:
            if should_abort():
                return
            cur = q.popleft()
            explored_order.append(cur)
            if cur == goal:
                reached = True
                break
            r, c = cur
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != 1 and (nr, nc) not in parent:
                    parent[(nr, nc)] = cur
                    q.append((nr, nc))
    else:
        g_cost = {start: 0}
        pq: List[Tuple[int, int, Tuple[int, int]]] = [(abs(start[0] - goal[0]) + abs(start[1] - goal[1]), 0, start)]
        while pq:
            if should_abort():
                return
            _, g, cur = heapq.heappop(pq)
            if g > g_cost.get(cur, 10**9):
                continue
            explored_order.append(cur)
            if cur == goal:
                reached = True
                break
            r, c = cur
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and board[nr][nc] != 1:
                    ng = g + 1
                    if ng < g_cost.get((nr, nc), 10**9):
                        g_cost[(nr, nc)] = ng
                        parent[(nr, nc)] = cur
                        h = abs(nr - goal[0]) + abs(nc - goal[1])
                        heapq.heappush(pq, (ng + h, ng, (nr, nc)))

    if not reached:
        yield {
            "type": "failed",
            "state": {"board": board},
            "highlights": {"cells": [list(p) for p in explored_order], "color": "hot"},
            "desc": "No path exists from Start (S) to Goal (G).",
            "stats": {"explored": len(explored_order)},
        }
        return

    path: List[List[int]] = []
    cur: Optional[Tuple[int, int]] = goal
    while cur is not None:
        path.append([cur[0], cur[1]])
        cur = parent[cur]
    path.reverse()

    yield {
        "type": "solution",
        "state": {"board": board},
        "highlights": {"path": path, "cells": path, "color": "primary"},
        "desc": f"{algo} found optimal path of length {len(path)} (explored {len(explored_order)} cells)",
        "stats": {"path_length": len(path), "explored": len(explored_order)},
    }
