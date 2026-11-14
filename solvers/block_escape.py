"""Block Escape solver (ported from solver_tools/Block_Escape3.py).
Supports multi-tile blocks, directional constraints, ice sliding, portals, Tap(0,0), and lockstep chains.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, List, Set, Tuple

META: Dict[str, Any] = {
    "slug": "block_escape",
    "name": "Block Escape (Portals & Chains)",
    "category": "2D Grid",
    "renderer": "grid",
    "description": "BFS solver for sliding block puzzles with multi-tile pieces, ice ('), portals, and lockstep chains.",
    "grid_meta": {
        "mode": "token",
        "editable": False,
    },
    "presets": {
        "Portal Chains": {
            "terrain": (
                "A B o o o o o o D C\n"
                "A B o o o o o o D C\n"
                "A B o o T o o o D C\n"
                "D C o o o o o o A B\n"
                "D C o o o o o o A B\n"
                "D C o o o o o o A B"
            ),
            "blocks": (
                "t' o o o o o o o o w'\n"
                "o  o o o o o o o o w'\n"
                "o  o g' o o o o o o w'\n"
                "e' o o o o o o o o o\n"
                "e' o o o o o o o o o\n"
                "e' o o o o o o o o o"
            ),
            "chains": [
                [["t", "g"], "same"],
                [["w", "e"], "invert"],
            ],
        },
        "Ice Target": {
            "terrain": (
                "o o o x o\n"
                "o x o o o\n"
                "o o o x T\n"
                "o o o o x"
            ),
            "blocks": (
                "t' o o o o\n"
                "o  o b o o\n"
                "o  o b o o\n"
                "o  o o o o"
            ),
            "chains": [],
        },
    },
    "params": [
        {"key": "terrain", "label": "Terrain Map", "type": "textarea", "default": ""},
        {"key": "blocks", "label": "Blocks Map", "type": "textarea", "default": ""},
    ],
}

VALID_DIRS = {
    "r": {(-1, 0), (1, 0)},
    "b": {(0, -1), (0, 1)},
    "t": {(-1, 0), (1, 0), (0, -1), (0, 1)},
    "g": {(-1, 0), (1, 0), (0, -1), (0, 1)},
    "n": {(0, -1)},
    "s": {(0, 1)},
    "e": {(1, 0)},
    "w": {(-1, 0)},
}


def _get_components(cells: Set[Tuple[int, int]]) -> List[Set[Tuple[int, int]]]:
    components: List[Set[Tuple[int, int]]] = []
    unvisited = set(cells)
    while unvisited:
        start = unvisited.pop()
        comp = {start}
        q = deque([start])
        while q:
            cx, cy = q.popleft()
            for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nxt = (cx + dx, cy + dy)
                if nxt in unvisited:
                    unvisited.remove(nxt)
                    comp.add(nxt)
                    q.append(nxt)
        components.append(comp)
    return components


def _parse_level(terrain_str: str, blocks_str: str, chains_config: List[Any]):
    terrain_lines = [l.split() for l in terrain_str.strip().splitlines() if l.strip()]
    blocks_lines = [l.split() for l in blocks_str.strip().splitlines() if l.strip()]
    max_y = len(terrain_lines)
    max_x = len(terrain_lines[0]) if max_y > 0 else 0

    static_grid: Set[Tuple[int, int]] = set()
    raw_portals: Dict[str, Set[Tuple[int, int]]] = {}
    target_zone: Set[Tuple[int, int]] = set()
    portal_labels: Dict[Tuple[int, int], str] = {}

    for y, line in enumerate(terrain_lines, 1):
        for x, char in enumerate(line, 1):
            if char == "x":
                static_grid.add((x, y))
            elif char == "T":
                target_zone.add((x, y))
            elif char != "o":
                raw_portals.setdefault(char, set()).add((x, y))
                portal_labels[(x, y)] = char

    portal_pairs = []
    for _, coords in raw_portals.items():
        comps = _get_components(coords)
        if len(comps) == 2:
            portal_pairs.append((comps[0], comps[1]))

    raw_blocks: Dict[Tuple[str, bool], Set[Tuple[int, int]]] = {}
    for y, line in enumerate(blocks_lines, 1):
        for x, cell in enumerate(line, 1):
            if cell != "o":
                base_char = cell.replace("'", "")
                is_ice = "'" in cell
                raw_blocks.setdefault((base_char, is_ice), set()).add((x, y))

    blocks_info: Dict[int, Dict[str, Any]] = {}
    initial_dict: Dict[int, Set[Tuple[int, int]]] = {}
    b_id = 0
    for (base_char, is_ice), coords in raw_blocks.items():
        for comp in _get_components(coords):
            blocks_info[b_id] = {"type": base_char, "ice": is_ice}
            initial_dict[b_id] = comp
            b_id += 1

    groups = []
    assigned = set()
    for chain_chars, mode in chains_config:
        g_ids = [bid for bid, bdata in blocks_info.items() if bdata["type"] in chain_chars]
        for bid in g_ids:
            assigned.add(bid)
        if g_ids:
            groups.append({"ids": g_ids, "mode": mode, "leader_type": blocks_info[g_ids[0]]["type"]})

    for bid in blocks_info:
        if bid not in assigned:
            groups.append({"ids": [bid], "mode": "same", "leader_type": blocks_info[bid]["type"]})

    initial_state = tuple(sorted((bid, tuple(sorted(cells))) for bid, cells in initial_dict.items()))
    return static_grid, portal_pairs, portal_labels, target_zone, blocks_info, groups, initial_state, max_x, max_y


def _render_board(
    state_tuple,
    blocks_info,
    static_grid,
    target_zone,
    portal_labels,
    max_x: int,
    max_y: int,
) -> List[List[str]]:
    board = [["" for _ in range(max_x)] for _ in range(max_y)]
    for x, y in static_grid:
        board[y - 1][x - 1] = "#"
    for (x, y), label in portal_labels.items():
        board[y - 1][x - 1] = label
    for x, y in target_zone:
        board[y - 1][x - 1] = "★"
    for bid, cells in state_tuple:
        lbl = blocks_info[bid]["type"].upper()
        if blocks_info[bid]["ice"]:
            lbl += "'"
        for x, y in cells:
            board[y - 1][x - 1] = lbl
    return board


def _preset_board(terrain: str, blocks: str, chains: List[Any]) -> List[List[str]]:
    sg, _, pl, tz, bi, _, init_st, mx, my = _parse_level(terrain, blocks, chains)
    return _render_board(init_st, bi, sg, tz, pl, mx, my)


for _p in META["presets"].values():
    _p["board"] = _preset_board(_p["terrain"], _p["blocks"], _p.get("chains", []))


def _get_moves(state_t, groups, static_grid, portal_pairs, blocks_info, max_x, max_y):

    cur = {bid: set(cells) for bid, cells in state_t}
    moves = []
    for group in groups:
        leader_type = group["leader_type"]
        allowed = list(VALID_DIRS.get(leader_type, set())) + [(0, 0)]
        for ld in allowed:
            vectors = {}
            valid_input = True
            for idx, bid in enumerate(group["ids"]):
                b_type = blocks_info[bid]["type"]
                md = (-ld[0], -ld[1]) if (group["mode"] == "invert" and idx > 0) else ld
                if md != (0, 0) and md not in VALID_DIRS.get(b_type, set()):
                    valid_input = False
                    break
                vectors[bid] = md
            if not valid_input:
                continue

            sim = {k: set(v) for k, v in cur.items()}
            stepped = False
            if ld != (0, 0):
                is_ice = any(blocks_info[bid]["ice"] for bid in group["ids"])
                while True:
                    all_new, all_old = set(), set()
                    for bid in group["ids"]:
                        mdx, mdy = vectors[bid]
                        b_cells = sim[bid]
                        all_old.update(b_cells)
                        all_new.update({(cx + mdx, cy + mdy) for cx, cy in b_cells})
                    edge = all_new - all_old
                    blocked = False
                    for tx, ty in edge:
                        if tx < 1 or tx > max_x or ty < 1 or ty > max_y or (tx, ty) in static_grid:
                            blocked = True
                            break
                        if any((tx, ty) in cells for oid, cells in sim.items() if oid not in group["ids"]):
                            blocked = True
                            break
                    if blocked:
                        break
                    for bid in group["ids"]:
                        mdx, mdy = vectors[bid]
                        sim[bid] = {(cx + mdx, cy + mdy) for cx, cy in sim[bid]}
                    stepped = True
                    if not is_ice:
                        break

            teleported = False
            for bid in group["ids"]:
                b_cells = sim[bid]
                for p1, p2 in portal_pairs:
                    if b_cells == p1:
                        sim[bid] = p2
                        teleported = True
                        break
                    if b_cells == p2:
                        sim[bid] = p1
                        teleported = True
                        break

            if stepped or teleported:
                nxt_t = tuple(sorted((bid, tuple(sorted(cells))) for bid, cells in sim.items()))
                desc = (
                    f"Tap {leader_type}-group (Portal)"
                    if ld == (0, 0)
                    else f"Slide {leader_type}-group ({ld[0]:+d}, {ld[1]:+d})"
                )
                moves.append((nxt_t, desc))
    return moves


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    terrain = params.get("terrain") or state.get("terrain", "")
    blocks = params.get("blocks") or state.get("blocks", "")
    chains = state.get("chains", [])

    static_grid, portal_pairs, portal_labels, target_zone, blocks_info, groups, init_state, max_x, max_y = (
        _parse_level(terrain, blocks, chains)
    )

    def make_state(st) -> Dict[str, Any]:
        return {
            "terrain": terrain,
            "blocks": blocks,
            "chains": chains,
            "board": _render_board(st, blocks_info, static_grid, target_zone, portal_labels, max_x, max_y),
        }

    t_id = next((bid for bid, data in blocks_info.items() if data["type"] == "t"), None)
    yield {
        "type": "start",
        "state": make_state(init_state),
        "highlights": {"cells": [[y - 1, x - 1] for x, y in target_zone], "color": "primary"},
        "desc": f"Loaded {max_x}x{max_y} Block Escape ({len(blocks_info)} blocks, {len(portal_pairs)} portals)",
        "stats": {"visited": 1},
    }

    if t_id is None or not target_zone:
        yield {
            "type": "failed",
            "state": make_state(init_state),
            "highlights": {},
            "desc": "Missing target block 't' or target zone 'T'.",
            "stats": {},
        }
        return

    queue = deque([(init_state, [])])
    visited = {init_state}

    while queue:
        if should_abort():
            return
        cur_state, path = queue.popleft()
        cur_dict = {bid: set(cells) for bid, cells in cur_state}
        if cur_dict[t_id] == target_zone:
            if not path:
                yield {
                    "type": "solution",
                    "state": make_state(cur_state),
                    "highlights": {},
                    "desc": "Target block is already on the goal zone!",
                    "stats": {"moves": 0, "visited": len(visited)},
                }
                return
            for idx, (st_snap, desc) in enumerate(path, 1):
                t_cells = [[y - 1, x - 1] for bid, cells in st_snap if bid == t_id for x, y in cells]
                yield {
                    "type": "solution" if idx == len(path) else "deduce",
                    "state": make_state(st_snap),
                    "highlights": {"cells": t_cells, "color": "primary"},
                    "desc": f"Move {idx}/{len(path)}: {desc}",
                    "stats": {"moves": len(path), "visited": len(visited)},
                }
            return

        for nxt_state, desc in _get_moves(cur_state, groups, static_grid, portal_pairs, blocks_info, max_x, max_y):
            if nxt_state not in visited:
                visited.add(nxt_state)
                queue.append((nxt_state, path + [(nxt_state, desc)]))

    yield {
        "type": "failed",
        "state": make_state(init_state),
        "highlights": {},
        "desc": "No escape path found.",
        "stats": {"visited": len(visited)},
    }
