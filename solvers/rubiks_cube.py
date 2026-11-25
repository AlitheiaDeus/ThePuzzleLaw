"""Rubik's Cube (3x3) solver using Thistlethwaite's 4-phase group reduction algorithm."""

from __future__ import annotations

from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Set, Tuple

# Face order in 54-facelet array: U(0..8), R(9..17), F(18..26), D(27..35), L(36..44), B(45..53)
FACE_NAMES = ("U", "R", "F", "D", "L", "B")
DEFAULT_COLORS = {"U": "W", "R": "R", "F": "G", "D": "Y", "L": "O", "B": "B"}

COLOR_HEX = {
    "W": "#F5F6FA",
    "Y": "#FFE600",
    "G": "#01CA6B",
    "B": "#2E86DE",
    "O": "#FA8231",
    "R": "#FF3F34",
}


def _solved_faces() -> Dict[str, List[List[str]]]:
    return {f: [[DEFAULT_COLORS[f]] * 3 for _ in range(3)] for f in FACE_NAMES}


# 54-facelet clockwise quarter-turn permutation tables (dst[i] = src[perm[i]])
def _make_facelet_perm(cycles: List[Tuple[int, int, int, int]]) -> Tuple[int, ...]:
    p = list(range(54))
    for a, b, c, d in cycles:
        # a -> b -> c -> d -> a (clockwise)
        p[b], p[c], p[d], p[a] = a, b, c, d
    return tuple(p)


def _face_cycles(base: int) -> List[Tuple[int, int, int, int]]:
    return [
        (base + 0, base + 2, base + 8, base + 6),
        (base + 1, base + 5, base + 7, base + 3),
    ]


# Face offsets: U=0, R=9, F=18, D=27, L=36, B=45
_BASE_FACELET_PERMS: Dict[str, Tuple[int, ...]] = {
    "U": _make_facelet_perm(
        _face_cycles(0)
        + [
            (18, 36, 45, 9),
            (19, 37, 46, 10),
            (20, 38, 47, 11),
        ]
    ),
    "D": _make_facelet_perm(
        _face_cycles(27)
        + [
            (24, 15, 51, 42),
            (25, 16, 52, 43),
            (26, 17, 53, 44),
        ]
    ),
    "R": _make_facelet_perm(
        _face_cycles(9)
        + [
            (2, 51, 29, 20),
            (5, 48, 32, 23),
            (8, 45, 35, 26),
        ]
    ),
    "L": _make_facelet_perm(
        _face_cycles(36)
        + [
            (0, 18, 27, 53),
            (3, 21, 30, 50),
            (6, 24, 33, 47),
        ]
    ),
    "F": _make_facelet_perm(
        _face_cycles(18)
        + [
            (6, 9, 29, 44),
            (7, 12, 28, 41),
            (8, 15, 27, 38),
        ]
    ),
    "B": _make_facelet_perm(
        _face_cycles(45)
        + [
            (2, 36, 33, 17),
            (1, 39, 34, 14),
            (0, 42, 35, 11),
        ]
    ),
}


def _apply_facelet_perm(arr: List[str], perm: Tuple[int, ...]) -> List[str]:
    return [arr[perm[i]] for i in range(54)]


def _compose_perm(p1: Tuple[int, ...], p2: Tuple[int, ...]) -> Tuple[int, ...]:
    return tuple(p1[p2[i]] for i in range(len(p1)))


ALL_MOVES: List[str] = [
    "U", "U2", "U'",
    "D", "D2", "D'",
    "L", "L2", "L'",
    "R", "R2", "R'",
    "F", "F2", "F'",
    "B", "B2", "B'",
]

MOVE_PERMS: Dict[str, Tuple[int, ...]] = {}
for _f, _p1 in _BASE_FACELET_PERMS.items():
    _p2 = _compose_perm(_p1, _p1)
    _p3 = _compose_perm(_p2, _p1)
    MOVE_PERMS[_f] = _p1
    MOVE_PERMS[_f + "2"] = _p2
    MOVE_PERMS[_f + "'"] = _p3


def _invert_move(m: str) -> str:
    if m.endswith("2"):
        return m
    if m.endswith("'"):
        return m[0]
    return m + "'"


def _apply_moves_to_faces(faces: Dict[str, List[List[str]]], moves: List[str]) -> Dict[str, List[List[str]]]:
    arr: List[str] = []
    for f in FACE_NAMES:
        for row in faces[f]:
            arr.extend(row)
    for m in moves:
        arr = _apply_facelet_perm(arr, MOVE_PERMS[m])
    out: Dict[str, List[List[str]]] = {}
    for idx, f in enumerate(FACE_NAMES):
        base = idx * 9
        out[f] = [arr[base : base + 3], arr[base + 3 : base + 6], arr[base + 6 : base + 9]]
    return out


def _scrambled_faces(moves_str: str) -> Dict[str, List[List[str]]]:
    return _apply_moves_to_faces(_solved_faces(), moves_str.split())


META: Dict[str, Any] = {
    "slug": "rubiks_cube",
    "name": "Rubik's Cube (3x3)",
    "category": "Path",
    "renderer": "custom",
    "custom_view": "/renderers/custom/rubiks_cube.js",
    "description": "3x3x3 Rubik's Cube solver using Thistlethwaite's 4-phase group reduction algorithm.",
    "presets": {
        "Quick Scramble (6 moves)": {
            "faces": _scrambled_faces("R U R' U' F' U"),
        },
        "T-Perm": {
            "faces": _scrambled_faces("R U R' U' R' F R2 U' R' U' R U R' F'"),
        },
        "Checkerboard + Twist": {
            "faces": _scrambled_faces("U2 D2 L2 R2 F2 B2 R U2 F' L"),
        },
        "Superflip (20-move)": {
            "faces": _scrambled_faces("U R2 F B R B2 R U2 L B2 R U' D' R2 F R' L B2 U2 F2"),
        },
        "Deep Scramble": {
            "faces": _scrambled_faces("F2 D' B L2 U R' F U2 L' B2 D R2 U' F' L D2 B' U R"),
        },
    },
    "params": [],
}


# ---------------------------------------------------------------------------
# Cubie representation (8 corners, 12 edges)
# ---------------------------------------------------------------------------
# Corner indices:
# 0: URF (U8, R9, F20)   1: UFL (U6, F18, L38)  2: ULB (U0, L36, B47)  3: UBR (U2, B45, R11)
# 4: DFR (D29, F26, R15) 5: DLF (D27, L44, F24) 6: DBL (D33, B53, L42) 7: DRB (D35, R17, B51)
CORNER_FACELETS: Tuple[Tuple[int, int, int], ...] = (
    (8, 9, 20),
    (6, 18, 38),
    (0, 36, 47),
    (2, 45, 11),
    (29, 26, 15),
    (27, 44, 24),
    (33, 53, 42),
    (35, 17, 51),
)

# Canonical corner face names in (U/D, cw1, cw2) order
CORNER_NAMES: Tuple[Tuple[str, str, str], ...] = (
    ("U", "R", "F"),
    ("U", "F", "L"),
    ("U", "L", "B"),
    ("U", "B", "R"),
    ("D", "F", "R"),
    ("D", "L", "F"),
    ("D", "B", "L"),
    ("D", "R", "B"),
)

# Edge indices:
# 0..3 U-layer: UR(5,10), UF(7,19), UL(3,37), UB(1,46)
# 4..7 D-layer: DR(32,16), DF(28,25), DL(30,43), DB(34,52)
# 8..11 E-slice: FR(23,12), FL(21,41), BL(50,39), BR(48,14)
EDGE_FACELETS: Tuple[Tuple[int, int], ...] = (
    (5, 10),
    (7, 19),
    (3, 37),
    (1, 46),
    (32, 16),
    (28, 25),
    (30, 43),
    (34, 52),
    (23, 12),
    (21, 41),
    (50, 39),
    (48, 14),
)

EDGE_NAMES: Tuple[Tuple[str, str], ...] = (
    ("U", "R"),
    ("U", "F"),
    ("U", "L"),
    ("U", "B"),
    ("D", "R"),
    ("D", "F"),
    ("D", "L"),
    ("D", "B"),
    ("F", "R"),
    ("F", "L"),
    ("B", "L"),
    ("B", "R"),
)

CubieState = Tuple[Tuple[int, ...], Tuple[int, ...], Tuple[int, ...], Tuple[int, ...]]
# (cp, co, ep, eo)

SOLVED_CUBIE: CubieState = (
    tuple(range(8)),
    (0,) * 8,
    tuple(range(12)),
    (0,) * 12,
)


def _parse_facelets_to_cubie(
    facelets: List[str],
) -> Tuple[Optional[CubieState], Optional[str]]:
    if len(facelets) != 54:
        return None, "Cube must have exactly 54 facelets."

    # Map center sticker color -> canonical face letter (U, R, F, D, L, B)
    centers = [facelets[i * 9 + 4] for i in range(6)]
    if len(set(centers)) != 6:
        return None, "All 6 center stickers must have distinct colors."
    color_to_face = {centers[i]: FACE_NAMES[i] for i in range(6)}

    counts: Dict[str, int] = {c: 0 for c in color_to_face}
    mapped: List[str] = []
    for s in facelets:
        if s not in color_to_face:
            return None, f"Sticker color '{s}' does not match any center sticker."
        counts[s] += 1
        mapped.append(color_to_face[s])

    for c, n in counts.items():
        if n != 9:
            return None, f"Color '{c}' appears {n} times (must appear exactly 9 times)."

    corner_lookup = {frozenset(CORNER_NAMES[i]): i for i in range(8)}
    cp: List[int] = []
    co: List[int] = []
    for f0, f1, f2 in CORNER_FACELETS:
        cols = (mapped[f0], mapped[f1], mapped[f2])
        cid = corner_lookup.get(frozenset(cols))
        if cid is None:
            return None, f"Invalid corner cubie with stickers {cols}."
        # Orientation: index of U/D sticker in (f0, f1, f2)
        ori = -1
        for k in range(3):
            if cols[k] in ("U", "D"):
                ori = k
                break
        if ori == -1:
            return None, f"Corner cubie {cols} missing U/D sticker."
        # Verify cyclic order matches canonical corner
        canon = CORNER_NAMES[cid]
        if (cols[ori], cols[(ori + 1) % 3], cols[(ori + 2) % 3]) != canon:
            return None, f"Corner cubie {cols} has impossible sticker twist/chirality."
        cp.append(cid)
        co.append(ori)

    if len(set(cp)) != 8:
        return None, "Duplicate corner cubie detected."
    if sum(co) % 3 != 0:
        return None, "Unsolvable cube: corner twist parity invalid (sum mod 3 != 0)."

    edge_lookup = {frozenset(EDGE_NAMES[i]): i for i in range(12)}
    ep: List[int] = []
    eo: List[int] = []
    for f0, f1 in EDGE_FACELETS:
        cols = (mapped[f0], mapped[f1])
        eid = edge_lookup.get(frozenset(cols))
        if eid is None:
            return None, f"Invalid edge cubie with stickers {cols}."
        canon = EDGE_NAMES[eid]
        if cols == canon:
            ori = 0
        elif cols == (canon[1], canon[0]):
            ori = 1
        else:
            return None, f"Invalid edge cubie {cols}."
        ep.append(eid)
        eo.append(ori)

    if len(set(ep)) != 12:
        return None, "Duplicate edge cubie detected."
    if sum(eo) % 2 != 0:
        return None, "Unsolvable cube: edge flip parity invalid (sum mod 2 != 0)."

    if _perm_parity(cp) != _perm_parity(ep):
        return None, "Unsolvable cube: corner and edge permutation parities do not match."

    return (tuple(cp), tuple(co), tuple(ep), tuple(eo)), None


def _perm_parity(perm: List[int] | Tuple[int, ...]) -> int:
    seen = [False] * len(perm)
    parity = 0
    for i in range(len(perm)):
        if not seen[i]:
            j = i
            cyc = 0
            while not seen[j]:
                seen[j] = True
                j = perm[j]
                cyc += 1
            parity ^= (cyc - 1) & 1
    return parity


# Precompute cubie-level move transitions from the verified facelet perms
def _build_cubie_move(facelet_perm: Tuple[int, ...]) -> CubieState:
    solved_arr: List[str] = []
    for f in FACE_NAMES:
        solved_arr.extend([f] * 9)
    after = _apply_facelet_perm(solved_arr, facelet_perm)
    cubie, err = _parse_facelets_to_cubie(after)
    assert cubie is not None and err is None, err
    return cubie


CUBIE_MOVES: Dict[str, CubieState] = {
    m: _build_cubie_move(MOVE_PERMS[m]) for m in ALL_MOVES
}


def _mul_cubie(a: CubieState, b: CubieState) -> CubieState:
    acp, aco, aep, aeo = a
    bcp, bco, bep, beo = b
    cp = tuple(acp[bcp[i]] for i in range(8))
    co = tuple((aco[bcp[i]] + bco[i]) % 3 for i in range(8))
    ep = tuple(aep[bep[i]] for i in range(12))
    eo = tuple(aeo[bep[i]] ^ beo[i] for i in range(12))
    return (cp, co, ep, eo)


# Precompute valid G3 corner permutations (96 reachable via half-turns only)
def _compute_valid_g3_corners() -> Set[Tuple[int, ...]]:
    half_moves = ["U2", "D2", "L2", "R2", "F2", "B2"]
    cp_moves = [CUBIE_MOVES[m][0] for m in half_moves]
    start = tuple(range(8))
    seen: Set[Tuple[int, ...]] = {start}
    q = deque([start])
    while q:
        cur = q.popleft()
        for m in cp_moves:
            nxt = tuple(cur[m[i]] for i in range(8))
            if nxt not in seen:
                seen.add(nxt)
                q.append(nxt)
    return seen


VALID_G3_CORNERS: Set[Tuple[int, ...]] = _compute_valid_g3_corners()


# ---------------------------------------------------------------------------
# Thistlethwaite 4-Phase Bidirectional BFS
# ---------------------------------------------------------------------------
_AXIS = {"U": 0, "D": 0, "L": 1, "R": 1, "F": 2, "B": 2}


def _allow_next_move(prev_move: Optional[str], next_move: str) -> bool:
    if prev_move is None:
        return True
    f1, f2 = prev_move[0], next_move[0]
    if f1 == f2:
        return False
    # Canonical ordering for commuting opposite faces: U before D, L before R, F before B
    if _AXIS[f1] == _AXIS[f2] and f1 > f2:
        return False
    return True


def _bidirectional_phase(
    start_state: CubieState,
    allowed_moves: List[str],
    key_fn: Callable[[CubieState], Any],
    goal_states: List[CubieState],
    should_abort: Callable[[], bool],
) -> Optional[List[str]]:
    start_key = key_fn(start_state)
    goal_keys = {key_fn(g) for g in goal_states}
    if start_key in goal_keys:
        return []

    fwd_parent: Dict[Any, Tuple[Any, Optional[str], CubieState]] = {
        start_key: (None, None, start_state)
    }
    bwd_parent: Dict[Any, Tuple[Any, Optional[str], CubieState]] = {}
    fwd_q = deque([(start_key, None)])
    bwd_q = deque()

    for g in goal_states:
        gk = key_fn(g)
        if gk not in bwd_parent:
            bwd_parent[gk] = (None, None, g)
            bwd_q.append((gk, None))

    def reconstruct(meet_key: Any) -> List[str]:
        path_fwd: List[str] = []
        cur = meet_key
        while cur is not None:
            p_key, mv, _ = fwd_parent[cur]
            if mv is not None:
                path_fwd.append(mv)
            cur = p_key
        path_fwd.reverse()

        path_bwd: List[str] = []
        cur = meet_key
        while cur is not None:
            p_key, mv, _ = bwd_parent[cur]
            if mv is not None:
                path_bwd.append(_invert_move(mv))
            cur = p_key
        return path_fwd + path_bwd

    while fwd_q and bwd_q:
        if should_abort():
            return None
        # Expand smaller frontier
        if len(fwd_q) <= len(bwd_q):
            for _ in range(len(fwd_q)):
                if should_abort():
                    return None
                cur_key, last_mv = fwd_q.popleft()
                cur_state = fwd_parent[cur_key][2]
                for mv in allowed_moves:
                    if not _allow_next_move(last_mv, mv):
                        continue
                    nxt_state = _mul_cubie(cur_state, CUBIE_MOVES[mv])
                    nxt_key = key_fn(nxt_state)
                    if nxt_key not in fwd_parent:
                        fwd_parent[nxt_key] = (cur_key, mv, nxt_state)
                        if nxt_key in bwd_parent:
                            return reconstruct(nxt_key)
                        fwd_q.append((nxt_key, mv))
        else:
            for _ in range(len(bwd_q)):
                if should_abort():
                    return None
                cur_key, last_mv = bwd_q.popleft()
                cur_state = bwd_parent[cur_key][2]
                for mv in allowed_moves:
                    if not _allow_next_move(last_mv, mv):
                        continue
                    nxt_state = _mul_cubie(cur_state, CUBIE_MOVES[mv])
                    nxt_key = key_fn(nxt_state)
                    if nxt_key not in bwd_parent:
                        bwd_parent[nxt_key] = (cur_key, mv, nxt_state)
                        if nxt_key in fwd_parent:
                            return reconstruct(nxt_key)
                        bwd_q.append((nxt_key, mv))
    return None


def _solve_thistlethwaite(
    cubie: CubieState,
    should_abort: Callable[[], bool],
) -> Optional[Tuple[List[str], Dict[str, int]]]:
    cur = cubie
    all_moves: List[str] = []
    phase_counts: Dict[str, int] = {}

    # Phase 1: G0 -> G1 (orient all 12 edges)
    g1_moves = ALL_MOVES
    p1 = _bidirectional_phase(
        cur,
        g1_moves,
        lambda s: s[3],  # eo tuple
        [SOLVED_CUBIE],
        should_abort,
    )
    if p1 is None:
        return None
    for m in p1:
        cur = _mul_cubie(cur, CUBIE_MOVES[m])
    all_moves.extend(p1)
    phase_counts["p1"] = len(p1)

    # Phase 2: G1 -> G2 (orient all 8 corners + E-slice edges {8,9,10,11} in positions 8..11)
    g2_moves = ["U", "U2", "U'", "D", "D2", "D'", "L", "L2", "L'", "R", "R2", "R'", "F2", "B2"]
    p2 = _bidirectional_phase(
        cur,
        g2_moves,
        lambda s: (s[1], tuple(1 if s[2][i] >= 8 else 0 for i in range(12))),
        [SOLVED_CUBIE],
        should_abort,
    )
    if p2 is None:
        return None
    for m in p2:
        cur = _mul_cubie(cur, CUBIE_MOVES[m])
    all_moves.extend(p2)
    phase_counts["p2"] = len(p2)

    # Phase 3: G2 -> G3 (corners in VALID_G3_CORNERS, M-slice edges {1,3,5,7} in M-slice, even edge parity)
    g3_moves = ["U", "U2", "U'", "D", "D2", "D'", "L2", "R2", "F2", "B2"]
    m_slice_set = {1, 3, 5, 7}
    g3_goals = [
        (g_cp, (0,) * 8, tuple(range(12)), (0,) * 12)
        for g_cp in VALID_G3_CORNERS
    ]
    p3 = _bidirectional_phase(
        cur,
        g3_moves,
        lambda s: (
            s[0],
            tuple(1 if s[2][i] in m_slice_set else 0 for i in range(8)),
            _perm_parity(s[2]),
        ),
        g3_goals,
        should_abort,
    )
    if p3 is None:
        return None
    for m in p3:
        cur = _mul_cubie(cur, CUBIE_MOVES[m])
    all_moves.extend(p3)
    phase_counts["p3"] = len(p3)

    # Phase 4: G3 -> G4 (half-turns only to solved)
    g4_moves = ["U2", "D2", "L2", "R2", "F2", "B2"]
    p4 = _bidirectional_phase(
        cur,
        g4_moves,
        lambda s: (s[0], s[2]),
        [SOLVED_CUBIE],
        should_abort,
    )
    if p4 is None:
        return None
    all_moves.extend(p4)
    phase_counts["p4"] = len(p4)

    return _simplify_moves(all_moves), phase_counts


def _simplify_moves(moves: List[str]) -> List[str]:
    """Merge consecutive same-face moves (e.g. R + R -> R2, U + U' -> cancel)."""
    power_map = {"": 1, "2": 2, "'": 3}
    inv_power = {1: "", 2: "2", 3: "'"}
    stack: List[Tuple[str, int]] = []
    for m in moves:
        face = m[0]
        pwr = power_map[m[1:]]
        if stack and stack[-1][0] == face:
            npwr = (stack[-1][1] + pwr) % 4
            stack.pop()
            if npwr != 0:
                stack.append((face, npwr))
        else:
            stack.append((face, pwr))
    return [f + inv_power[p] for f, p in stack]


def _faces_from_state(state: Dict[str, Any]) -> Dict[str, List[List[str]]]:
    faces = state.get("faces")
    if not isinstance(faces, dict):
        return _solved_faces()
    return {
        f: [list(row) for row in faces[f]]
        for f in FACE_NAMES
    }


def _is_solved_faces(faces: Dict[str, List[List[str]]]) -> bool:
    for f in FACE_NAMES:
        grid = faces[f]
        c = grid[1][1]
        if any(grid[r][col] != c for r in range(3) for col in range(3)):
            return False
    return True


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    faces = _faces_from_state(state)

    yield {
        "type": "start",
        "state": {"faces": faces},
        "highlights": {},
        "desc": "Loaded 3x3 Rubik's Cube",
        "stats": {"moves": 0},
    }

    if should_abort():
        return

    arr: List[str] = []
    for f in FACE_NAMES:
        for row in faces[f]:
            arr.extend(row)

    cubie, err = _parse_facelets_to_cubie(arr)
    if cubie is None:
        yield {
            "type": "failed",
            "state": {"faces": faces},
            "highlights": {},
            "desc": err or "Invalid cube state",
            "stats": {"moves": 0},
        }
        return

    if _is_solved_faces(faces):
        yield {
            "type": "solution",
            "state": {"faces": faces},
            "highlights": {},
            "desc": "Cube is already solved (0 moves)",
            "stats": {"moves": 0},
        }
        return

    res = _solve_thistlethwaite(cubie, should_abort)
    if should_abort():
        return
    if res is None:
        yield {
            "type": "failed",
            "state": {"faces": faces},
            "highlights": {},
            "desc": "Failed to find solution within Thistlethwaite search",
            "stats": {},
        }
        return

    moves, phase_counts = res

    yield {
        "type": "deduce",
        "state": {"faces": faces},
        "highlights": {},
        "desc": (
            f"Found {len(moves)}-move solution "
            f"(G1:{phase_counts['p1']} G2:{phase_counts['p2']} G3:{phase_counts['p3']} G4:{phase_counts['p4']})"
        ),
        "stats": {"moves": len(moves), **phase_counts},
    }

    cur_faces = faces
    for idx, mv in enumerate(moves, start=1):
        if should_abort():
            return
        cur_faces = _apply_moves_to_faces(cur_faces, [mv])
        is_last = idx == len(moves)
        yield {
            "type": "solution" if is_last else "explore",
            "state": {"faces": cur_faces},
            "highlights": {"face": mv[0], "move": mv},
            "desc": (
                f"Solved in {len(moves)} moves: {' '.join(moves)}"
                if is_last
                else f"Move {idx}/{len(moves)}: {mv}"
            ),
            "stats": {"step": idx, "total_moves": len(moves), "move": mv},
        }
