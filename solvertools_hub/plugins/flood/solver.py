"""
solver.py - Strict Optimal A*/IDA* Graph Contraction Engine for Flood (Flood-It).
Contracts the grid into a planar component adjacency graph and executes IDA*
with admissible graph distance and color coverage heuristics to guarantee
the theoretical minimum sequence of flood color changes.
"""

import time
from collections import deque
from typing import Dict, Generator, List, Optional, Set, Tuple

from ...core.base_plugin import BasePuzzleState, BaseSolver, SolverStep
from .state import FloodState


class FloodSolver(BaseSolver):
    """
    Optimal Flood-It solver using component-graph contraction and IDA*.
    Guarantees the minimum number of moves to homogenize the grid.
    """

    def __init__(self):
        self._is_aborted: bool = False

    def abort(self) -> None:
        """Signals the search to terminate gracefully."""
        self._is_aborted = True

    def should_abort(self) -> bool:
        """Checks if cancellation has been requested."""
        return self._is_aborted

    def _extract_components(
        self, grid: List[List[int]], rows: int, cols: int
    ) -> Tuple[List[Dict], List[List[int]]]:
        """
        Decomposes grid into maximal monochromatic connected components.
        Component 0 is guaranteed to be the component containing (0, 0).
        """
        comp_map = [[-1] * cols for _ in range(rows)]
        components: List[Dict] = []
        comp_id = 0

        # Component 0 must be the anchor component containing (0, 0)
        for start_r in range(rows):
            for start_c in range(cols):
                if comp_map[start_r][start_c] != -1:
                    continue
                color = grid[start_r][start_c]
                cells: List[Tuple[int, int]] = []
                q = deque([(start_r, start_c)])
                comp_map[start_r][start_c] = comp_id

                while q:
                    cr, cc = q.popleft()
                    cells.append((cr, cc))
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if 0 <= nr < rows and 0 <= nc < cols:
                            if comp_map[nr][nc] == -1 and grid[nr][nc] == color:
                                comp_map[nr][nc] = comp_id
                                q.append((nr, nc))

                components.append({
                    "id": comp_id,
                    "color": color,
                    "size": len(cells),
                    "cells": cells,
                    "adj": set(),
                })
                comp_id += 1

        # Build adjacency graph between contiguous differing-color components
        for r in range(rows):
            for c in range(cols):
                cid = comp_map[r][c]
                for dr, dc in [(1, 0), (0, 1)]:
                    nr, nc = r + dr, c + dc
                    if 0 <= nr < rows and 0 <= nc < cols:
                        nid = comp_map[nr][nc]
                        if cid != nid:
                            components[cid]["adj"].add(nid)
                            components[nid]["adj"].add(cid)

        return components, comp_map

    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False,
    ) -> Generator[SolverStep, None, None]:
        """
        Solves the Flood puzzle yielding step-by-step scrubbable SolverSteps.
        """
        if not isinstance(initial_state, FloodState):
            raise TypeError("State must be an instance of FloodState")

        self._is_aborted = False
        valid, msg = initial_state.validate()
        if not valid:
            raise ValueError(f"Invalid Flood state: {msg}")

        rows, cols = initial_state.rows, initial_state.cols
        total_cells = rows * cols
        grid = initial_state.grid

        # 1. Yield initial starting step
        start_flooded = initial_state.get_flooded_region()
        start_color = initial_state.anchor_color
        start_color_name = initial_state.get_color_name(start_color)

        yield SolverStep(
            state=initial_state.clone(),
            action_desc=f"Initial state: Anchor at (0, 0) [{start_color_name}], {len(start_flooded)}/{total_cells} cells captured",
            highlights={
                "anchor": (0, 0),
                "flooded": list(start_flooded),
                "color": initial_state.get_color_hex(start_color),
            },
            metrics={
                "move": 0,
                "flooded_cells": len(start_flooded),
                "total_cells": total_cells,
                "coverage_pct": round(len(start_flooded) / total_cells * 100, 1),
            },
        )

        # Check if already uniform
        if len(start_flooded) == total_cells:
            yield SolverStep(
                state=initial_state.clone(),
                action_desc="Already uniform! Puzzle is solved.",
                highlights={"flooded": list(start_flooded)},
                metrics={"status": "Solved in 0 moves", "total_moves": 0},
            )
            return

        # 2. Extract graph components
        components, comp_map = self._extract_components(grid, rows, cols)
        num_comp = len(components)
        comp_colors = [c["color"] for c in components]
        comp_sizes = [c["size"] for c in components]
        comp_adj = [list(c["adj"]) for c in components]

        # 3. All-pairs shortest paths in component graph
        dist_matrix = [[9999] * num_comp for _ in range(num_comp)]
        for i in range(num_comp):
            dist_matrix[i][i] = 0
            q = deque([i])
            while q:
                u = q.popleft()
                d = dist_matrix[i][u]
                for v in comp_adj[u]:
                    if dist_matrix[i][v] > d + 1:
                        dist_matrix[i][v] = d + 1
                        q.append(v)

        # Initial search state
        start_merged = 1 << 0
        init_dists = tuple(dist_matrix[0][v] for v in range(num_comp))
        start_boundary = 0
        for v in comp_adj[0]:
            start_boundary |= (1 << v)

        full_mask = (1 << num_comp) - 1
        nodes_expanded = [0]
        tt: Dict[Tuple[int, int], int] = {}

        # Precompute initial color counts
        init_color_counts = [0] * initial_state.num_colors
        for c in comp_colors:
            init_color_counts[c] += 1
        # Component 0 is already merged
        init_color_counts[comp_colors[0]] -= 1

        def compute_h(merged: int, dists: Tuple[int, ...], color_counts: Tuple[int, ...]) -> int:
            max_d = 0
            rem_colors = 0
            for cnt in color_counts:
                if cnt > 0:
                    rem_colors += 1
            for v in range(num_comp):
                if not (merged & (1 << v)):
                    if dists[v] > max_d:
                        max_d = dists[v]
            return max(max_d, rem_colors)

        h0 = compute_h(start_merged, init_dists, tuple(init_color_counts))
        threshold = h0

        def ida_search(
            merged: int,
            current_color: int,
            boundary_mask: int,
            dists: Tuple[int, ...],
            color_counts: Tuple[int, ...],
            g: int,
            limit: int,
            path: List[int],
        ) -> Tuple[int, Optional[List[int]]]:
            nodes_expanded[0] += 1

            if self.should_abort():
                return -1, None

            # Compute admissible lower bound h
            max_d = 0
            rem_colors = 0
            for cnt in color_counts:
                if cnt > 0:
                    rem_colors += 1
            for v in range(num_comp):
                if not (merged & (1 << v)):
                    if dists[v] > max_d:
                        max_d = dists[v]
            h = max(max_d, rem_colors)
            f = g + h
            if f > limit:
                return f, None
            if merged == full_mask:
                return g, path

            # Transposition table check
            tt_key = (merged, current_color)
            if tt_key in tt and tt[tt_key] <= g:
                return 999999, None

            min_exceeded = 999999

            # Group immediate boundary components by color
            color_to_comps: Dict[int, List[int]] = {}
            for v in range(num_comp):
                if boundary_mask & (1 << v):
                    c = comp_colors[v]
                    if c not in color_to_comps:
                        color_to_comps[c] = []
                    color_to_comps[c].append(v)

            # Generate and score candidate moves
            candidate_moves = []
            for color, comps in color_to_comps.items():
                absorbed_mask = 0
                new_cells = 0
                for c_id in comps:
                    absorbed_mask |= (1 << c_id)
                    new_cells += comp_sizes[c_id]

                new_merged = merged | absorbed_mask
                new_boundary = boundary_mask & ~new_merged
                for c_id in comps:
                    for nxt in comp_adj[c_id]:
                        if not (new_merged & (1 << nxt)):
                            new_boundary |= (1 << nxt)

                new_dists = list(dists)
                for c_id in comps:
                    row = dist_matrix[c_id]
                    for v in range(num_comp):
                        if not (new_merged & (1 << v)):
                            if row[v] < new_dists[v]:
                                new_dists[v] = row[v]

                new_color_counts = list(color_counts)
                for c_id in comps:
                    new_color_counts[comp_colors[c_id]] -= 1

                # Fast new_h calculation for move ordering
                cand_max_d = 0
                cand_rem = 0
                for cnt in new_color_counts:
                    if cnt > 0:
                        cand_rem += 1
                for v in range(num_comp):
                    if not (new_merged & (1 << v)):
                        if new_dists[v] > cand_max_d:
                            cand_max_d = new_dists[v]
                cand_h = max(cand_max_d, cand_rem)

                candidate_moves.append((
                    cand_h,
                    -new_cells,
                    color,
                    comps,
                    new_merged,
                    new_boundary,
                    tuple(new_dists),
                    tuple(new_color_counts),
                ))

            # Prioritize branches with lowest projected h, breaking ties with maximum newly absorbed cells
            candidate_moves.sort(key=lambda x: (x[0], x[1]))

            for cand_h, _, color, comps, new_merged, next_boundary, next_dists, next_counts in candidate_moves:
                t, res_path = ida_search(
                    new_merged,
                    color,
                    next_boundary,
                    next_dists,
                    next_counts,
                    g + 1,
                    limit,
                    path + [color],
                )
                if res_path is not None:
                    return t, res_path
                if self.should_abort():
                    return -1, None
                if t < min_exceeded:
                    min_exceeded = t

            tt[tt_key] = g
            return min_exceeded, None

        # 4. Execute IDA* search loop
        optimal_color_sequence: Optional[List[int]] = None
        while True:
            if self.should_abort():
                return

            tt.clear()
            t, found_path = ida_search(
                start_merged,
                start_color,
                start_boundary,
                init_dists,
                tuple(init_color_counts),
                0,
                threshold,
                [],
            )

            if stream_search:
                yield SolverStep(
                    state=initial_state.clone(),
                    action_desc=f"IDA* depth bound {threshold}: explored {nodes_expanded[0]} nodes...",
                    highlights={"anchor": (0, 0)},
                    metrics={
                        "threshold": threshold,
                        "nodes_expanded": nodes_expanded[0],
                        "status": "Searching",
                    },
                )

            if found_path is not None:
                optimal_color_sequence = found_path
                break
            if t >= 999999 or t == -1:
                break
            threshold = t

        if self.should_abort() or optimal_color_sequence is None:
            return

        # 5. Yield optimal solution playback sequence
        current_playback_state = initial_state.clone()
        total_moves = len(optimal_color_sequence)

        for step_idx, color_choice in enumerate(optimal_color_sequence, 1):
            if self.should_abort():
                return

            prev_flooded = current_playback_state.get_flooded_region()
            current_playback_state = current_playback_state.apply_move(color_choice)
            new_flooded = current_playback_state.get_flooded_region()
            newly_absorbed = new_flooded - prev_flooded

            color_name = current_playback_state.get_color_name(color_choice)
            color_hex = current_playback_state.get_color_hex(color_choice)
            pct = round(len(new_flooded) / total_cells * 100, 1)

            yield SolverStep(
                state=current_playback_state.clone(),
                action_desc=f"Move {step_idx}/{total_moves}: Change anchor to {color_name} (+{len(newly_absorbed)} cells, {len(new_flooded)}/{total_cells} uniform)",
                highlights={
                    "newly_captured": list(newly_absorbed),
                    "flooded": list(new_flooded),
                    "anchor": (0, 0),
                    "color_hex": color_hex,
                    "color_choice": color_choice,
                },
                metrics={
                    "move": step_idx,
                    "total_moves": total_moves,
                    "color": color_name,
                    "absorbed_this_step": len(newly_absorbed),
                    "flooded_cells": len(new_flooded),
                    "total_cells": total_cells,
                    "coverage_pct": pct,
                },
            )

        # 6. Final completion step
        yield SolverStep(
            state=current_playback_state.clone(),
            action_desc=f"Optimal Flood Completed in {total_moves} moves! 100% grid uniform.",
            highlights={
                "flooded": list(current_playback_state.get_flooded_region()),
                "anchor": (0, 0),
            },
            metrics={
                "status": "Optimal Solution Found",
                "total_moves": total_moves,
                "nodes_evaluated": nodes_expanded[0],
                "coverage_pct": 100.0,
            },
        )
