"""Liquid Sorter Pro / Sand Tubes A* solver with variable tube capacities."""

from __future__ import annotations

import heapq
from collections import Counter
from typing import Any, Callable, Dict, Generator, List, Tuple

META: Dict[str, Any] = {
    "slug": "liquid_sorter",
    "name": "Liquid Sorter Pro",
    "category": "Vector Containers",
    "renderer": "custom",
    "custom_view": "/renderers/custom/liquid_tubes.js",
    "description": "A* pouring solver with variable tube capacities and symmetry-breaking pruning.",
    "presets": {
        "5 Tubes": {
            "capacities": [4, 4, 4, 4, 4],
            "allow_split_colors": False,
            "tubes": [
                [0, 1, 2, 0],
                [2, 0, 1, 2],
                [1, 2, 0, 1],
                [],
                [],
            ],
        },
        "6 Tubes": {
            "capacities": [4, 4, 4, 4, 3, 3],
            "allow_split_colors": False,
            "tubes": [
                [0, 1, 2, 3],
                [3, 2, 1, 0],
                [0, 2, 1, 3],
                [1, 3, 0, 2],
                [],
                [],
            ],
        },
    },
    "params": [
        {"key": "allow_split_colors", "label": "Allow Split Colors", "type": "bool", "default": False}
    ],
}


def _heuristic(tubes: Tuple[Tuple[int, ...], ...]) -> int:
    transitions = 0
    for t in tubes:
        for k in range(1, len(t)):
            if t[k] != t[k - 1]:
                transitions += 1
    return transitions


def _is_solved(
    tubes: Tuple[Tuple[int, ...], ...],
    capacities: List[int],
    allow_split: bool,
    total_counts: Counter,
) -> bool:
    for idx, t in enumerate(tubes):
        if not t:
            continue
        if len(set(t)) > 1:
            return False
        if not allow_split and len(t) != total_counts[t[0]] and len(t) < capacities[idx]:
            return False
    if not allow_split:
        # Each color must appear in at most one non-empty tube
        seen_colors = set()
        for t in tubes:
            if t:
                if t[0] in seen_colors:
                    return False
                seen_colors.add(t[0])
    return True


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    raw_tubes = [[c for c in t if c is not None] for t in state["tubes"]]
    num_tubes = len(raw_tubes)
    caps = list(state.get("capacities") or [4] * num_tubes)
    if len(caps) < num_tubes:
        caps.extend([caps[-1] if caps else 4] * (num_tubes - len(caps)))
    allow_split = bool(params.get("allow_split_colors", state.get("allow_split_colors", False)))

    start_tubes = tuple(tuple(t) for t in raw_tubes)
    total_counts = Counter(c for t in start_tubes for c in t)

    yield {
        "type": "start",
        "state": {"tubes": [list(t) for t in start_tubes], "capacities": caps, "allow_split_colors": allow_split},
        "highlights": {},
        "desc": f"Initial {num_tubes} tubes ({len(total_counts)} colors)",
        "stats": {"expanded": 0},
    }

    if not allow_split:
        avail_caps = sorted(caps, reverse=True)
        for color, cnt in total_counts.items():
            if not any(cap >= cnt for cap in avail_caps):
                yield {
                    "type": "failed",
                    "state": {"tubes": raw_tubes, "capacities": caps},
                    "highlights": {},
                    "desc": f"Color {color} has count {cnt}, exceeding max tube capacity {max(caps)}.",
                    "stats": {},
                }
                return

    def normalize(tubes_t: Tuple[Tuple[int, ...], ...]) -> Tuple[Tuple[int, Tuple[int, ...]], ...]:
        return tuple(sorted((caps[i], tubes_t[i]) for i in range(num_tubes)))

    counter = 0
    pq: List[Tuple[int, int, Tuple[Tuple[int, ...], ...], List[Tuple[int, int, int]]]] = [
        (0, counter, start_tubes, [])
    ]
    best_cost = {normalize(start_tubes): 0}
    expanded = 0

    while pq:
        if should_abort():
            return
        _, _, cur_tubes, path = heapq.heappop(pq)
        expanded += 1

        if _is_solved(cur_tubes, caps, allow_split, total_counts):
            replay = [list(t) for t in start_tubes]
            if not path:
                yield {
                    "type": "solution",
                    "state": {"tubes": replay, "capacities": caps, "allow_split_colors": allow_split},
                    "highlights": {},
                    "desc": "Tubes are already sorted!",
                    "stats": {"step": 0, "total": 0, "expanded": expanded},
                }
                return
            for step_idx, (src, dst, amount) in enumerate(path, 1):
                poured = [replay[src].pop() for _ in range(amount)]
                replay[dst].extend(poured)
                yield {
                    "type": "solution" if step_idx == len(path) else "deduce",
                    "state": {
                        "tubes": [list(t) for t in replay],
                        "capacities": caps,
                        "allow_split_colors": allow_split,
                    },
                    "highlights": {"src": src, "dst": dst, "amount": amount},
                    "desc": f"Pour Tube {src + 1} -> Tube {dst + 1} ({amount} unit{'s' if amount > 1 else ''})",
                    "stats": {"step": step_idx, "total": len(path), "expanded": expanded},
                }
            return

        first_empty: Dict[int, int] = {}
        for j, t in enumerate(cur_tubes):
            if not t and caps[j] not in first_empty:
                first_empty[caps[j]] = j

        for i, src in enumerate(cur_tubes):
            if not src:
                continue
            cap_i = caps[i]
            if not allow_split and len(src) == cap_i and len(set(src)) == 1 and cap_i == total_counts[src[0]]:
                continue

            top = src[-1]
            block = 0
            for seg in reversed(src):
                if seg == top:
                    block += 1
                else:
                    break

            for j, dst in enumerate(cur_tubes):
                if i == j:
                    continue
                cap_j = caps[j]
                space = cap_j - len(dst)
                if space <= 0:
                    continue
                is_empty = len(dst) == 0
                if is_empty and j != first_empty.get(cap_j):
                    continue
                if is_empty or dst[-1] == top:
                    amt = min(block, space)
                    if is_empty and amt == len(src) and cap_j >= cap_i:
                        continue
                    nxt_list = [list(t) for t in cur_tubes]
                    poured = [nxt_list[i].pop() for _ in range(amt)]
                    nxt_list[j].extend(poured)
                    nxt_t = tuple(tuple(t) for t in nxt_list)
                    norm = normalize(nxt_t)
                    new_cost = len(path) + 1
                    if new_cost < best_cost.get(norm, 10**9):
                        best_cost[norm] = new_cost
                        counter += 1
                        prio = new_cost + _heuristic(nxt_t)
                        heapq.heappush(pq, (prio, counter, nxt_t, path + [(i, j, amt)]))

    yield {
        "type": "failed",
        "state": {"tubes": raw_tubes, "capacities": caps},
        "highlights": {},
        "desc": "No valid pouring sequence found.",
        "stats": {"expanded": expanded},
    }
