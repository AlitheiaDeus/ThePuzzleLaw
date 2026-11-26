"""Block Escape solver (ported from solver_tools/Block_Escape3.py).
Supports multi-tile blocks, directional constraints, ice sliding, portals, Tap(0,0), and lockstep chains.
"""

from __future__ import annotations

from collections import deque
import heapq
import os
from pathlib import Path
import re
import subprocess
import time
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

_NATIVE_BIN = Path(__file__).resolve().parent / "native" / (
    "block_escape_fast.exe" if os.name == "nt" else "block_escape_fast"
)

META: Dict[str, Any] = {
    "slug": "block_escape",
    "name": "Block Escape (Portals & Chains)",
    "category": "Path",
    "renderer": "custom",
    "custom_view": "/renderers/custom/block_escape.js",
    "description": "Sliding block puzzle solver with merged multi-tile pieces, distinct touching blocks (g1, g2...), ice ('), portals, and lockstep chains.",
    "grid_meta": {
        "mode": "token",
        "editable": True,
        "resizable": True,
        "min_dim": 3,
        "max_dim": 15,
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
        {
            "key": "search_mode",
            "label": "Search Mode",
            "type": "select",
            "options": ["bfs", "wastar", "astar", "greedy"],
            "default": "bfs",
        },
        {"key": "glitches_allowed", "label": "Glitches Allowed (Skip Portals)", "type": "bool", "default": False},
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


def _parse_token_info(token: str) -> Tuple[str, str, bool]:
    """Return (role_char, dir_key, is_target) for a block token like 't', 'tr', 'g1', 'n'."""
    low = token.lower()
    is_target = low.startswith("t")
    if is_target and len(low) >= 2 and low[1] in VALID_DIRS:
        return "t", low[1], True
    base = low[0]
    return base, base, is_target


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
    max_y = max(len(terrain_lines), len(blocks_lines))
    max_x = max(
        max((len(l) for l in terrain_lines), default=0),
        max((len(l) for l in blocks_lines), default=0),
    )

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
    numbered_sides: Dict[str, Dict[str, Set[Tuple[int, int]]]] = {}
    legacy_portals: Dict[str, Set[Tuple[int, int]]] = {}
    for p_tok, coords in raw_portals.items():
        m = re.match(r"^([AB])(\d+)$", p_tok)
        if m:
            side, num = m.group(1), m.group(2)
            numbered_sides.setdefault(num, {})[side] = coords
        else:
            legacy_portals[p_tok] = coords

    for num, sides in numbered_sides.items():
        if "A" in sides and "B" in sides:
            comps_a = _get_components(sides["A"])
            comps_b = _get_components(sides["B"])
            if len(comps_a) == 1 and len(comps_b) == 1:
                portal_pairs.append((comps_a[0], comps_b[0]))
        else:
            for coords in sides.values():
                comps = _get_components(coords)
                if len(comps) == 2:
                    portal_pairs.append((comps[0], comps[1]))

    for coords in legacy_portals.values():
        comps = _get_components(coords)
        if len(comps) == 2:
            portal_pairs.append((comps[0], comps[1]))

    raw_blocks: Dict[Tuple[str, bool], Set[Tuple[int, int]]] = {}
    for y, line in enumerate(blocks_lines, 1):
        for x, cell in enumerate(line, 1):
            if cell != "o":
                is_ice = "'" in cell
                token = cell.replace("'", "")
                raw_blocks.setdefault((token, is_ice), set()).add((x, y))

    blocks_info: Dict[int, Dict[str, Any]] = {}
    initial_dict: Dict[int, Set[Tuple[int, int]]] = {}
    b_id = 0
    for (token, is_ice), coords in raw_blocks.items():
        role_char, dir_key, is_target = _parse_token_info(token)
        for comp in _get_components(coords):
            blocks_info[b_id] = {
                "type": role_char,
                "dir_type": dir_key,
                "is_target": is_target,
                "token": token,
                "ice": is_ice,
            }
            initial_dict[b_id] = comp
            b_id += 1

    # Build chain groups via graph traversal so multi-link chains (same/invert) bind strictly
    adj: Dict[int, List[Tuple[int, int]]] = {bid: [] for bid in blocks_info}
    for chain_chars, mode in chains_config:
        g_ids = [
            bid
            for bid, bdata in blocks_info.items()
            if bdata["type"] in chain_chars or bdata["token"] in chain_chars
        ]
        if len(g_ids) >= 2:
            rel = -1 if mode == "invert" else 1
            anchor = g_ids[0]
            for other in g_ids[1:]:
                adj[anchor].append((other, rel))
                adj[other].append((anchor, rel))

    groups = []
    assigned = set()
    for bid in sorted(blocks_info):
        if bid in assigned:
            continue
        comp_signs: Dict[int, int] = {bid: 1}
        q_comp = deque([bid])
        assigned.add(bid)
        while q_comp:
            u = q_comp.popleft()
            for v, rel in adj[u]:
                if v not in assigned:
                    assigned.add(v)
                    comp_signs[v] = comp_signs[u] * rel
                    q_comp.append(v)
        g_ids = sorted(comp_signs.keys())
        groups.append({
            "ids": g_ids,
            "signs": comp_signs,
            "leader_type": blocks_info[g_ids[0]]["dir_type"],
        })

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
        lbl = blocks_info[bid]["token"].upper()
        if blocks_info[bid]["ice"]:
            lbl += "'"
        for x, y in cells:
            board[y - 1][x - 1] = lbl
    return board


def _render_pieces(state_tuple, max_x: int, max_y: int) -> List[List[int]]:
    pieces = [[-1 for _ in range(max_x)] for _ in range(max_y)]
    for bid, cells in state_tuple:
        for x, y in cells:
            pieces[y - 1][x - 1] = bid
    return pieces


def _preset_board(terrain: str, blocks: str, chains: List[Any]) -> Tuple[List[List[str]], List[List[int]]]:
    sg, _, pl, tz, bi, _, init_st, mx, my = _parse_level(terrain, blocks, chains)
    return _render_board(init_st, bi, sg, tz, pl, mx, my), _render_pieces(init_st, mx, my)


for _p in META["presets"].values():
    _p["board"], _p["pieces"] = _preset_board(_p["terrain"], _p["blocks"], _p.get("chains", []))


def _mask_to_cells(mask: int, stride: int) -> Set[Tuple[int, int]]:
    cells: Set[Tuple[int, int]] = set()
    m = mask
    while m:
        lsb = m & -m
        idx = lsb.bit_length() - 1
        y, x = divmod(idx, stride)
        cells.add((x, y))
        m ^= lsb
    return cells


def _cells_to_mask(cells: Set[Tuple[int, int]], stride: int) -> int:
    m = 0
    for x, y in cells:
        m |= 1 << (y * stride + x)
    return m


def _shift_mask(mask: int, delta: int) -> int:
    return mask << delta if delta >= 0 else mask >> (-delta)


def _format_move_desc(leader_type: str, ld: Tuple[int, int], kind: int) -> str:
    if kind == 0:
        return f"Tap {leader_type}-group (Portal)"
    slide = f"Slide {leader_type}-group ({ld[0]:+d}, {ld[1]:+d})"
    if kind == 2:
        return f"{slide} -> Portal"
    if kind == 3:
        return f"{slide} (Glitch: Swipe Off Next)"
    return slide


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    terrain = params.get("terrain") or state.get("terrain", "")
    blocks = params.get("blocks") or state.get("blocks", "")
    chains = state.get("chains", [])
    search_mode = params.get("search_mode", "bfs")
    glitches_allowed = bool(params.get("glitches_allowed", False))

    static_grid, portal_pairs, portal_labels, target_zone, blocks_info, groups, init_state, max_x, max_y = (
        _parse_level(terrain, blocks, chains)
    )

    stride = max_x + 2

    def make_state_from_masks(masks: Tuple[int, ...]) -> Dict[str, Any]:
        st_tuple = tuple((bid, tuple(sorted(_mask_to_cells(m, stride)))) for bid, m in enumerate(masks))
        return {
            "terrain": terrain,
            "blocks": blocks,
            "chains": chains,
            "board": _render_board(st_tuple, blocks_info, static_grid, target_zone, portal_labels, max_x, max_y),
            "pieces": _render_pieces(st_tuple, max_x, max_y),
        }

    init_masks = tuple(_cells_to_mask(set(cells), stride) for _, cells in init_state)
    t_id = next((bid for bid, data in blocks_info.items() if data["type"] == "t"), None)

    yield {
        "type": "start",
        "state": make_state_from_masks(init_masks),
        "highlights": {"cells": [[y - 1, x - 1] for x, y in target_zone], "color": "primary"},
        "desc": f"Loaded {max_x}x{max_y} Block Escape ({len(blocks_info)} blocks, {len(portal_pairs)} portals, {search_mode.upper()})",
        "stats": {"visited": 1},
    }

    if t_id is None or not target_zone:
        yield {
            "type": "failed",
            "state": make_state_from_masks(init_masks),
            "highlights": {},
            "desc": "Missing target block 't' or target zone 'T'.",
            "stats": {},
        }
        return

    # Precompute bitmask wall + boundary mask (1-cell border around 1..max_x, 1..max_y)
    wall_mask = 0
    board_mask = 0
    for y in range(max_y + 2):
        for x in range(max_x + 2):
            bit = 1 << (y * stride + x)
            if x == 0 or x == max_x + 1 or y == 0 or y == max_y + 1 or (x, y) in static_grid:
                wall_mask |= bit
            else:
                board_mask |= bit

    portal_masks = [(_cells_to_mask(p1, stride), _cells_to_mask(p2, stride)) for p1, p2 in portal_pairs]
    target_mask = _cells_to_mask(target_zone, stride)

    # Identify interchangeable unchained block classes for exact state canonicalization
    chained_bids = {bid for group in groups if len(group["ids"]) > 1 for bid in group["ids"]}
    class_map: Dict[Any, List[int]] = {}
    for bid, cells in init_state:
        bdata = blocks_info[bid]
        if bid == t_id or bid in chained_bids:
            key: Any = ("unique", bid)
        else:
            min_x = min(x for x, _ in cells)
            min_y = min(y for _, y in cells)
            norm_shape = tuple(sorted((x - min_x, y - min_y) for x, y in cells))
            key = ("cls", bdata["dir_type"], bdata["ice"], norm_shape)
        class_map.setdefault(key, []).append(bid)

    canon_classes: List[Tuple[int, ...]] = [tuple(bids) for bids in class_map.values()]
    has_symmetry = any(len(cls) > 1 for cls in canon_classes)

    def canonicalize(masks: Tuple[int, ...]) -> Tuple[int, ...]:
        if not has_symmetry:
            return masks
        out: List[int] = []
        for cls in canon_classes:
            if len(cls) == 1:
                out.append(masks[cls[0]])
            else:
                out.extend(sorted(masks[bid] for bid in cls))
        return tuple(out)

    def masks_from_canon(ck: Tuple[int, ...]) -> Tuple[int, ...]:
        if not has_symmetry:
            return ck
        arr = [0] * len(init_masks)
        pos = 0
        for cls in canon_classes:
            for bid in cls:
                arr[bid] = ck[pos]
                pos += 1
        return tuple(arr)

    # Precompute valid (ld, [(bid, delta), ...], is_ice) per group
    group_specs = []
    for g_idx, group in enumerate(groups):
        leader_type = group["leader_type"]
        group_ids = group["ids"]
        signs = group["signs"]
        is_ice = any(blocks_info[bid]["ice"] for bid in group_ids)
        allowed = list(VALID_DIRS.get(leader_type, set())) + ([(0, 0)] if portal_masks else [])
        actions = []
        for ld in allowed:
            if ld == (0, 0):
                actions.append((ld, [], True))
                continue
            bid_deltas = []
            ok = True
            for bid in group_ids:
                b_dir = blocks_info[bid]["dir_type"]
                sgn = signs[bid]
                md = (ld[0] * sgn, ld[1] * sgn)
                if md not in VALID_DIRS.get(b_dir, set()):
                    ok = False
                    break
                bid_deltas.append((bid, md[1] * stride + md[0]))
            if ok:
                actions.append((ld, bid_deltas, False))
        group_specs.append((g_idx, leader_type, group_ids, is_ice, actions))

    # Precompute BFS distance map from target_zone through static_grid using the target block's full shape
    # and directional constraints so A*/W-A*/Greedy never route a multi-tile target through too-narrow holes,
    # and unreachable targets without portals fail immediately.
    target_anchor = min(target_zone, key=lambda c: (c[1], c[0]))
    t_init_cells = next(cells for bid, cells in init_state if bid == t_id)
    t_init_anchor = min(t_init_cells, key=lambda c: (c[1], c[0]))
    t_offsets = [(x - t_init_anchor[0], y - t_init_anchor[1]) for x, y in t_init_cells]
    t_dir_type = blocks_info[t_id]["dir_type"]
    t_unchained = t_id not in chained_bids
    rev_dirs = [(-dx, -dy) for dx, dy in VALID_DIRS[t_dir_type]] if not portal_masks else [(-1, 0), (1, 0), (0, -1), (0, 1)]
    dist_map: Dict[int, int] = {}

    def _fits_at(ax: int, ay: int) -> bool:
        for ox, oy in t_offsets:
            px, py = ax + ox, ay + oy
            if px < 1 or px > max_x or py < 1 or py > max_y or (px, py) in static_grid:
                return False
        return True

    if search_mode in ("astar", "wastar", "greedy") or (not portal_masks and t_unchained):
        dq = deque([(target_anchor[0], target_anchor[1], 0)])
        seen_d = {target_anchor}
        while dq:
            cx, cy, cd = dq.popleft()
            dist_map[cy * stride + cx] = cd
            for dx, dy in rev_dirs:
                nx, ny = cx + dx, cy + dy
                if (nx, ny) not in seen_d and _fits_at(nx, ny):
                    seen_d.add((nx, ny))
                    dq.append((nx, ny, cd + 1))

    if not portal_masks and t_unchained and t_init_anchor not in seen_d:
        yield {
            "type": "failed",
            "state": make_state_from_masks(init_masks),
            "highlights": {},
            "desc": "Target block cannot physically reach Goal zone given walls and directional locks.",
            "stats": {"visited": 1},
        }
        return

    def heuristic(masks: Tuple[int, ...]) -> int:
        tm = masks[t_id]
        lsb = tm & -tm
        idx = lsb.bit_length() - 1
        return dist_map.get(idx, 0)

    # Try native Rust 256-bit bitboard accelerator when available and grid fits in 256 bits
    if _NATIVE_BIN.exists() and stride * (max_y + 2) <= 256:
        lines_in = [
            f"{len(init_masks)} {t_id} {search_mode} {1 if glitches_allowed else 0}",
            f"{wall_mask:064x} {board_mask:064x} {target_mask:064x}",
            " ".join(f"{m:064x}" for m in init_masks),
            str(len(portal_masks)),
        ]
        for p1m, p2m in portal_masks:
            lines_in.append(f"{p1m:064x} {p2m:064x}")
        lines_in.append(str(len(group_specs)))
        for _, _, group_ids, is_ice, actions in group_specs:
            lines_in.append(f"{1 if is_ice else 0} {len(group_ids)} " + " ".join(str(b) for b in group_ids))
            lines_in.append(str(len(actions)))
            for _, bid_deltas, is_tap in actions:
                if is_tap:
                    lines_in.append("T")
                else:
                    lines_in.append(f"M {len(bid_deltas)} " + " ".join(f"{b} {d}" for b, d in bid_deltas))
        lines_in.append(str(len(canon_classes)))
        for cls in canon_classes:
            lines_in.append(f"{len(cls)} " + " ".join(str(b) for b in cls))
        lines_in.append(f"{len(dist_map)} " + " ".join(f"{k} {v}" for k, v in dist_map.items()))
        payload = "\n".join(lines_in) + "\n"

        proc = subprocess.Popen(
            [str(_NATIVE_BIN)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )
        try:
            assert proc.stdin is not None and proc.stdout is not None
            proc.stdin.write(payload)
            proc.stdin.close()
            while True:
                if should_abort():
                    proc.terminate()
                    proc.wait(timeout=2)
                    return
                line = proc.stdout.readline()
                if not line:
                    break
                parts = line.strip().split()
                if not parts:
                    continue
                if parts[0] == "PROG":
                    visited_n = int(parts[1])
                    depth_n = int(parts[2])
                    yield {
                        "type": "explore",
                        "state": make_state_from_masks(init_masks),
                        "highlights": {},
                        "desc": f"Searching (Rust {search_mode.upper()})... {visited_n:,} states, depth {depth_n}",
                        "stats": {"visited": visited_n, "depth": depth_n},
                    }
                elif parts[0] == "SOL":
                    n_steps = int(parts[1])
                    visited_n = int(parts[2])
                    if n_steps == 0:
                        proc.wait()
                        yield {
                            "type": "solution",
                            "state": make_state_from_masks(init_masks),
                            "highlights": {},
                            "desc": "Target block is already on the goal zone!",
                            "stats": {"moves": 0, "visited": visited_n},
                        }
                        return
                    for idx in range(1, n_steps + 1):
                        sline = proc.stdout.readline().strip().split()
                        mcode = int(sline[0])
                        masks_snap = tuple(int(h, 16) for h in sline[1:])
                        g_idx = mcode >> 16
                        ld_idx = (mcode >> 4) & 0xFFF
                        kind = mcode & 0xF
                        _, leader_type, _, _, actions = group_specs[g_idx]
                        ld = actions[ld_idx][0]
                        desc = _format_move_desc(leader_type, ld, kind)
                        t_cells = [[y - 1, x - 1] for x, y in _mask_to_cells(masks_snap[t_id], stride)]
                        yield {
                            "type": "solution" if idx == n_steps else "explore",
                            "state": make_state_from_masks(masks_snap),
                            "highlights": {"cells": t_cells, "color": "primary"},
                            "desc": f"Move {idx}/{n_steps}: {desc}",
                            "stats": {"moves": n_steps, "visited": visited_n},
                        }
                    proc.wait()
                    return
                elif parts[0] == "FAIL":
                    visited_n = int(parts[1])
                    proc.wait()
                    yield {
                        "type": "failed",
                        "state": make_state_from_masks(init_masks),
                        "highlights": {},
                        "desc": f"No escape path found ({visited_n:,} states checked).",
                        "stats": {"visited": visited_n},
                    }
                    return
        finally:
            if proc.poll() is None:
                proc.terminate()
                proc.wait(timeout=2)

    def gen_moves(masks: Tuple[int, ...], pending_gid: Optional[int]):
        total_occ = 0
        for m in masks:
            total_occ |= m
        empty_mask = board_mask ^ total_occ

        for g_idx, _, group_ids, is_ice, actions in group_specs:
            if pending_gid is not None and g_idx != pending_gid:
                continue
            group_occ = 0
            for bid in group_ids:
                group_occ |= masks[bid]
            other_occ = total_occ ^ group_occ
            blocked_mask = wall_mask | other_occ

            for ld_idx, (ld, bid_deltas, is_tap) in enumerate(actions):
                if is_tap:
                    sim = list(masks)
                    teleported = False
                    for bid in group_ids:
                        bm = sim[bid]
                        for p1m, p2m in portal_masks:
                            dest = p2m if bm == p1m else (p1m if bm == p2m else 0)
                            if dest:
                                cur_other = other_occ
                                for ob in group_ids:
                                    if ob != bid:
                                        cur_other |= sim[ob]
                                if (dest & (wall_mask | cur_other)) == 0:
                                    sim[bid] = dest
                                    teleported = True
                                break
                    if teleported:
                        yield (canonicalize(tuple(sim)), None), (g_idx, ld_idx, 0)
                    continue

                # Fast skip: if no block in the group has an empty neighbor in its move direction, skip
                if len(group_ids) == 1:
                    bid0, delta0 = bid_deltas[0]
                    if (_shift_mask(masks[bid0], delta0) & (empty_mask | masks[bid0])) == 0:
                        continue

                sim = list(masks)
                stepped = False
                while True:
                    collision = False
                    nxt_vals = []
                    for bid, delta in bid_deltas:
                        nm = _shift_mask(sim[bid], delta)
                        if nm & blocked_mask:
                            collision = True
                            break
                        nxt_vals.append((bid, nm))
                    if collision:
                        break
                    for bid, nm in nxt_vals:
                        sim[bid] = nm
                    stepped = True
                    if not is_ice:
                        break

                if not stepped:
                    continue

                slide_masks = tuple(sim)
                if portal_masks:
                    tele = list(slide_masks)
                    teleported = False
                    for bid in group_ids:
                        bm = tele[bid]
                        for p1m, p2m in portal_masks:
                            dest = p2m if bm == p1m else (p1m if bm == p2m else 0)
                            if dest:
                                cur_other = other_occ
                                for ob in group_ids:
                                    if ob != bid:
                                        cur_other |= tele[ob]
                                if (dest & (wall_mask | cur_other)) == 0:
                                    tele[bid] = dest
                                    teleported = True
                                break
                    if teleported:
                        yield (canonicalize(tuple(tele)), None), (g_idx, ld_idx, 2)
                        if glitches_allowed:
                            yield (canonicalize(slide_masks), g_idx), (g_idx, ld_idx, 3)
                        continue

                yield (canonicalize(slide_masks), None), (g_idx, ld_idx, 1)

    init_canon = canonicalize(init_masks)
    t_canon_idx = next(
        idx for idx, cls in enumerate(canon_classes) if len(cls) == 1 and cls[0] == t_id
    ) if has_symmetry else t_id

    init_key = (init_canon, None)
    parent: Dict[Any, Tuple[Optional[Any], Optional[Tuple[int, int, int]]]] = {init_key: (None, None)}
    solved_key = None
    last_report = time.monotonic()

    if search_mode in ("astar", "wastar", "greedy"):
        h_weight = 3 if search_mode == "wastar" else 1
        g_score: Dict[Any, int] = {init_key: 0}
        tie = 0
        heap: List[Tuple[int, int, int, Any]] = [(heuristic(init_masks) * h_weight, 0, tie, init_key)]
        while heap:
            if should_abort():
                return
            _, cur_g, _, cur_key = heapq.heappop(heap)
            if cur_g > g_score.get(cur_key, 10**9):
                continue
            cur_canon, cur_pending = cur_key
            if cur_pending is None and cur_canon[t_canon_idx] == target_mask:
                solved_key = cur_key
                break
            cur_masks = masks_from_canon(cur_canon)
            now = time.monotonic()
            if now - last_report >= 1.0:
                last_report = now
                yield {
                    "type": "explore",
                    "state": make_state_from_masks(cur_masks),
                    "highlights": {},
                    "desc": f"Searching ({search_mode.upper()})... {len(parent):,} states, depth {cur_g}",
                    "stats": {"visited": len(parent), "depth": cur_g},
                }
            nxt_g = cur_g + 1
            for nxt_key, move_code in gen_moves(cur_masks, cur_pending):
                if nxt_key not in g_score or nxt_g < g_score[nxt_key]:
                    g_score[nxt_key] = nxt_g
                    parent[nxt_key] = (cur_key, move_code)
                    tie += 1
                    lsb = nxt_key[0][t_canon_idx] & -nxt_key[0][t_canon_idx]
                    h = dist_map.get(lsb.bit_length() - 1, 0)
                    f = h if search_mode == "greedy" else nxt_g + h * h_weight
                    heapq.heappush(heap, (f, nxt_g, tie, nxt_key))
    else:
        queue = deque([(init_key, 0)])
        while queue:
            if should_abort():
                return
            cur_key, cur_depth = queue.popleft()
            cur_canon, cur_pending = cur_key
            if cur_pending is None and cur_canon[t_canon_idx] == target_mask:
                solved_key = cur_key
                break
            cur_masks = masks_from_canon(cur_canon)
            now = time.monotonic()
            if now - last_report >= 1.0:
                last_report = now
                yield {
                    "type": "explore",
                    "state": make_state_from_masks(cur_masks),
                    "highlights": {},
                    "desc": f"Searching (BFS)... {len(parent):,} states, depth {cur_depth}, queue {len(queue):,}",
                    "stats": {"visited": len(parent), "depth": cur_depth},
                }
            nxt_depth = cur_depth + 1
            for nxt_key, move_code in gen_moves(cur_masks, cur_pending):
                if nxt_key not in parent:
                    parent[nxt_key] = (cur_key, move_code)
                    queue.append((nxt_key, nxt_depth))

    if solved_key is not None:
        path: List[Tuple[Tuple[int, ...], str]] = []
        cur = solved_key
        while True:
            prev, mcode = parent[cur]
            if prev is None or mcode is None:
                break
            g_idx, ld_idx, kind = mcode
            _, leader_type, _, _, actions = group_specs[g_idx]
            ld = actions[ld_idx][0]
            path.append((masks_from_canon(cur[0]), _format_move_desc(leader_type, ld, kind)))
            cur = prev
        path.reverse()

        if not path:
            yield {
                "type": "solution",
                "state": make_state_from_masks(masks_from_canon(solved_key[0])),
                "highlights": {},
                "desc": "Target block is already on the goal zone!",
                "stats": {"moves": 0, "visited": len(parent)},
            }
            return
        for idx, (masks_snap, desc) in enumerate(path, 1):
            t_cells = [[y - 1, x - 1] for x, y in _mask_to_cells(masks_snap[t_id], stride)]
            yield {
                "type": "solution" if idx == len(path) else "explore",
                "state": make_state_from_masks(masks_snap),
                "highlights": {"cells": t_cells, "color": "primary"},
                "desc": f"Move {idx}/{len(path)}: {desc}",
                "stats": {"moves": len(path), "visited": len(parent)},
            }
        return

    yield {
        "type": "failed",
        "state": make_state_from_masks(init_masks),
        "highlights": {},
        "desc": f"No escape path found ({len(parent):,} states checked).",
        "stats": {"visited": len(parent)},
    }
