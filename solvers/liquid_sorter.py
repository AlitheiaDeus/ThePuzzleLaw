"""Liquid Sorter Pro / Sand Tubes A* solver with variable tube capacities."""

from __future__ import annotations

import heapq
from collections import Counter
from typing import Any, Callable, Dict, Generator, List, Tuple

META: Dict[str, Any] = {
    "slug": "liquid_sorter",
    "name": "Liquid Sorter Pro",
    "category": "Path",
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


def _can_match_single_tubes(counts: List[int], capacities: List[int]) -> bool:
    """Return True if every color count matches a distinct tube capacity 1-to-1."""
    cap_avail = Counter(capacities)
    for cnt in counts:
        if cap_avail[cnt] <= 0:
            return False
        cap_avail[cnt] -= 1
    return True


def _can_partition_capacities(counts: List[int], capacities: List[int]) -> bool:
    """Return True if color counts can partition a subset of tube capacities into full tubes."""
    if not counts or sum(counts) > sum(capacities):
        return False
    sorted_counts = sorted(counts, reverse=True)
    sorted_caps = sorted(capacities, reverse=True)
    used = [False] * len(sorted_caps)

    def assign_color(color_idx: int, remaining_sum: int, start_cap_idx: int) -> bool:
        if remaining_sum == 0:
            if color_idx + 1 == len(sorted_counts):
                return True
            return assign_color(color_idx + 1, sorted_counts[color_idx + 1], 0)

        prev_tried = -1
        for i in range(start_cap_idx, len(sorted_caps)):
            if used[i]:
                continue
            cap = sorted_caps[i]
            if cap == prev_tried or cap > remaining_sum:
                continue
            prev_tried = cap
            used[i] = True
            if assign_color(color_idx, remaining_sum - cap, i + 1):
                return True
            used[i] = False
        return False

    return assign_color(0, sorted_counts[0], 0)


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
        if allow_split:
            if len(t) != capacities[idx]:
                return False
        else:
            if len(t) != total_counts[t[0]] or len(t) != capacities[idx]:
                return False
    if not allow_split:
        seen_colors = set()
        for t in tubes:
            if t:
                if t[0] in seen_colors:
                    return False
                seen_colors.add(t[0])
    return True


def _parse_and_validate_tubes(
    raw_input: List[List[Any]],
    caps: List[int],
) -> Tuple[List[List[Any]], str | None]:
    """Validate gaps/overflow and trim trailing empty slots."""
    cleaned: List[List[Any]] = []
    for idx, tube in enumerate(raw_input):
        seen_empty = False
        trimmed: List[Any] = []
        for val in tube:
            if val is None or val == "":
                seen_empty = True
            else:
                if seen_empty:
                    return cleaned, f"Tube {idx + 1} has floating tile(s) above an empty slot."
                trimmed.append(val)
        if len(trimmed) > caps[idx]:
            return cleaned, f"Tube {idx + 1} has {len(trimmed)} tiles, exceeding capacity {caps[idx]}."
        cleaned.append(trimmed)
    return cleaned, None


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    raw_input = state.get("tubes", [])
    num_tubes = len(raw_input)
    caps = [int(c) for c in (state.get("capacities") or [4] * num_tubes)]
    if len(caps) < num_tubes:
        caps.extend([caps[-1] if caps else 4] * (num_tubes - len(caps)))
    caps = caps[:num_tubes]
    allow_split = bool(params.get("allow_split_colors", state.get("allow_split_colors", False)))

    cleaned_tubes, struct_err = _parse_and_validate_tubes(raw_input, caps)
    display_tubes = [
        [c for c in t if c is not None and c != ""] if idx >= len(cleaned_tubes) else cleaned_tubes[idx]
        for idx, t in enumerate(raw_input)
    ]

    # Map arbitrary hashable tokens (ints or strings) to canonical int IDs for A*
    tok_to_id: Dict[Any, int] = {}
    id_to_tok: List[Any] = []
    for t in display_tubes:
        for val in t:
            if val not in tok_to_id:
                tok_to_id[val] = len(id_to_tok)
                id_to_tok.append(val)

    start_tubes = tuple(tuple(tok_to_id[v] for v in t) for t in display_tubes)
    total_counts = Counter(c for t in start_tubes for c in t)

    def decode_tubes(tubes_seq: Any) -> List[List[Any]]:
        return [[id_to_tok[cid] for cid in t] for t in tubes_seq]

    yield {
        "type": "start",
        "state": {"tubes": decode_tubes(start_tubes), "capacities": caps, "allow_split_colors": allow_split},
        "highlights": {},
        "desc": f"Initial {num_tubes} tubes ({len(total_counts)} colors)",
        "stats": {"expanded": 0},
    }

    if num_tubes < 2:
        yield {
            "type": "failed",
            "state": {"tubes": decode_tubes(start_tubes), "capacities": caps},
            "highlights": {},
            "desc": "At least 2 tubes are required.",
            "stats": {},
        }
        return

    if any(c < 1 for c in caps):
        yield {
            "type": "failed",
            "state": {"tubes": decode_tubes(start_tubes), "capacities": caps},
            "highlights": {},
            "desc": "Every tube must have capacity of at least 1.",
            "stats": {},
        }
        return

    if struct_err:
        yield {
            "type": "failed",
            "state": {"tubes": raw_input, "capacities": caps},
            "highlights": {},
            "desc": struct_err,
            "stats": {},
        }
        return

    if not total_counts:
        yield {
            "type": "failed",
            "state": {"tubes": decode_tubes(start_tubes), "capacities": caps},
            "highlights": {},
            "desc": "Board is empty — place some tiles to solve.",
            "stats": {},
        }
        return

    counts_list = list(total_counts.values())
    if not allow_split:
        if len(total_counts) > num_tubes:
            yield {
                "type": "failed",
                "state": {"tubes": decode_tubes(start_tubes), "capacities": caps},
                "highlights": {},
                "desc": f"{len(total_counts)} distinct colors cannot fit into {num_tubes} tubes without splitting.",
                "stats": {},
            }
            return
        if not _can_match_single_tubes(counts_list, caps):
            yield {
                "type": "failed",
                "state": {"tubes": decode_tubes(start_tubes), "capacities": caps},
                "highlights": {},
                "desc": "Color counts cannot each fill a distinct tube capacity completely.",
                "stats": {},
            }
            return
    else:
        if not _can_partition_capacities(counts_list, caps):
            yield {
                "type": "failed",
                "state": {"tubes": decode_tubes(start_tubes), "capacities": caps},
                "highlights": {},
                "desc": "Color counts cannot partition into full 1-color or completely empty tubes.",
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
                    "state": {"tubes": decode_tubes(replay), "capacities": caps, "allow_split_colors": allow_split},
                    "highlights": {},
                    "desc": "Tubes are already sorted!",
                    "stats": {"step": 0, "total": 0, "expanded": expanded},
                }
                return
            for step_idx, (src, dst, amount) in enumerate(path, 1):
                poured = [replay[src].pop() for _ in range(amount)]
                replay[dst].extend(poured)
                yield {
                    "type": "solution" if step_idx == len(path) else "explore",
                    "state": {
                        "tubes": decode_tubes(replay),
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
        "state": {"tubes": decode_tubes(start_tubes), "capacities": caps},
        "highlights": {},
        "desc": "No valid pouring sequence found.",
        "stats": {"expanded": expanded},
    }
