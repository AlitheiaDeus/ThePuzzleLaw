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
        "2-Gen <R, U> Scramble": {
            "faces": _scrambled_faces("R U R' U R U2 R' U' R2 U R' U R U2 R2"),
        },
        "PLL (Jb-Perm)": {
            "faces": _scrambled_faces("R U R' F' R U R' U' R' F R2 U' R' U'"),
        },
    },
    "params": [
        {
            "key": "method",
            "label": "Solve Method",
            "type": "select",
            "default": "Thistlethwaite",
            "options": [
                "Thistlethwaite",
                "CFOP",
                "ZZ",
                "2-Gen <R, U>",
                "3-Gen <R, U, L>",
                "Half-Turn <U2..B2>",
                "1-Alg: T-Perm Only",
                "1-Alg: Jb-Perm Only",
                "T-Perm + U Only",
                "Jb-Perm + U Only",
            ],
        }
    ],
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


# ---------------------------------------------------------------------------
# Wide/Slice Alg Expander + CFOP (Cross, Intuitive F2L, 57 OLL, 21 PLL) + ZZ + Variants
# ---------------------------------------------------------------------------
_ROT_MAPS: Dict[str, Dict[str, str]] = {
    "x": {"U": "F", "F": "D", "D": "B", "B": "U", "L": "L", "R": "R"},
    "y": {"F": "R", "R": "B", "B": "L", "L": "F", "U": "U", "D": "D"},
    "z": {"U": "L", "L": "D", "D": "R", "R": "U", "F": "F", "B": "B"},
}


def _compose_rot(ori: Dict[str, str], rot_name: str) -> Dict[str, str]:
    mp = _ROT_MAPS[rot_name]
    return {k: ori[mp[k]] for k in ori}


def _expand_alg(alg_str: str) -> List[str]:
    """Expand speedcubing wide (r,l,f,b,u,d), slice (M,E,S), and rotation (x,y,z) notation to <U,D,L,R,F,B>."""
    ori = {f: f for f in FACE_NAMES}
    out: List[str] = []
    for tok in alg_str.split():
        base = tok[0]
        suf = tok[1:]
        cnt = 2 if suf == "2" else (3 if suf == "'" else 1)
        if base in "xyz":
            for _ in range(cnt):
                ori = _compose_rot(ori, base)
        elif base in "UDLRFB":
            out.append(ori[base] + suf)
        elif base in "rlfbud":
            opp_face, rot = {
                "r": ("L", "x"), "l": ("R", "x'"),
                "u": ("D", "y"), "d": ("U", "y'"),
                "f": ("B", "z"), "b": ("F", "z'"),
            }[base]
            for _ in range(cnt):
                out.append(ori[opp_face])
                rbase = rot[0]
                rcnt = 3 if len(rot) > 1 else 1
                for _ in range(rcnt):
                    ori = _compose_rot(ori, rbase)
        elif base in "MES":
            f1, f2, rot = {
                "M": ("R", "L'", "x'"),
                "E": ("U", "D'", "y'"),
                "S": ("F'", "B", "z"),
            }[base]
            for _ in range(cnt):
                out.append(ori[f1[0]] + f1[1:])
                out.append(ori[f2[0]] + f2[1:])
                rbase = rot[0]
                rcnt = 3 if len(rot) > 1 else 1
                for _ in range(rcnt):
                    ori = _compose_rot(ori, rbase)
    return _simplify_moves(out)


def _apply_seq(st: CubieState, seq: List[str]) -> CubieState:
    cur = st
    for m in seq:
        cur = _mul_cubie(cur, CUBIE_MOVES[m])
    return cur


PLL_ALGS: Dict[str, str] = {
    "Ua": "R U' R U R U R U' R' U' R2",
    "Ub": "R2 U R U R' U' R' U' R' U R'",
    "H": "R2 U2 R U2 R2 U2 R2 U2 R U2 R2",
    "Z": "R' U' R U' R U R U' R' U R U R2 U' R'",
    "Aa": "R' F R' B2 R F' R' B2 R2",
    "Ab": "R2 B2 R F R' B2 R F' R",
    "E": "x' R U' R' D R U R' D' R U R' D R U' R' D' x",
    "T": "R U R' U' R' F R2 U' R' U' R U R' F'",
    "Jb": "R U R' F' R U R' U' R' F R2 U' R' U'",
    "Ja": "R' U L' U2 R U' R' U2 R L",
    "F": "R' U' F' R U R' U' R' F R2 U' R' U' R U R' U R",
    "Ra": "R U' R' U' R U R D R' U' R D' R' U2 R'",
    "Rb": "R' U2 R U2 R' F R U R' U' R' F' R2",
    "V": "R' U R' U' B' R' B2 U' B' U B' R B R",
    "Y": "F R U' R' U' R U R' F' R U R' U' R' F R F'",
    "Na": "R U R' U R U R' F' R U R' U' R' F R2 U' R' U2 R U' R'",
    "Nb": "R' U R U' R' F' U' F R U R' F R' F' R U' R",
    "Ga": "R2 U R' U R' U' R U' R2 D U' R' U R D'",
    "Gb": "R' U' R U D' R2 U R' U R U' R U' R2 D",
    "Gc": "R2 U' R U' R U R' U R2 D' U R U' R' D",
    "Gd": "R U R' U' D R2 U' R U' R' U R' U R2 D'",
}

OLL_ALGS: Dict[str, str] = {
    "OLL #1": "R U2 R2 F R F' U2 R' F R F'",
    "OLL #2": "F R U R' U' F' f R U R' U' f'",
    "OLL #3": "f R U R' U' f' U' F R U R' U' F'",
    "OLL #4": "f R U R' U' f' U F R U R' U' F'",
    "OLL #5": "r' U2 R U R' U r",
    "OLL #6": "r U2 R' U' R U' r'",
    "OLL #7": "r U R' U R U2 r'",
    "OLL #8": "r' U' R U' R' U2 r",
    "OLL #9": "R U R' U' R' F R2 U R' U' F'",
    "OLL #10": "R U R' U R' F R F' R U2 R'",
    "OLL #11": "r' R2 U R' U R U2 R' U M'",
    "OLL #12": "M' R' U' R U' R' U2 R U' M",
    "OLL #13": "F U R U' R2 F' R U R U' R'",
    "OLL #14": "R' F R U R' F' R F U' F'",
    "OLL #15": "r' U' r R' U' R U r' U r",
    "OLL #16": "r U r' R U R' U' r U' r'",
    "OLL #17": "R U R' U R' F R F' U2 R' F R F'",
    "OLL #18": "r U R' U R U2 r2 U' R U' R' U2 r",
    "OLL #19": "r' U2 R U R' U r2 U2 R' U' R U' r'",
    "OLL #20": "r U R' U' M2 U R U' R' U' M'",
    "OLL #21 (H)": "R U2 R' U' R U R' U' R U' R'",
    "OLL #22 (Pi)": "R U2 R2 U' R2 U' R2 U2 R",
    "OLL #23 (U)": "R2 D R' U2 R D' R' U2 R'",
    "OLL #24 (T)": "r U R' U' r' F R F'",
    "OLL #25 (L)": "F' r U R' U' r' F R",
    "OLL #26 (Anti-Sune)": "R U2 R' U' R U' R'",
    "OLL #27 (Sune)": "R U R' U R U2 R'",
    "OLL #28 (Stealth)": "r U R' U' r' R U R U' R'",
    "OLL #29": "R U R' U' R U' R' F' U' F R U R'",
    "OLL #30": "F R' F R2 U' R' U' R U R' F2",
    "OLL #31": "R' U' F U R U' R' F' R",
    "OLL #32": "R U B' U' R' U R B R'",
    "OLL #33 (T-Key)": "R U R' U' R' F R F'",
    "OLL #34": "R U R2 U' R' F R U R U' F'",
    "OLL #35": "R U2 R2 F R F' R U2 R'",
    "OLL #36": "L' U' L U' L' U L U L F' L' F",
    "OLL #37": "F R' F' R U R U' R'",
    "OLL #38": "R U R' U R U' R' U' R' F R F'",
    "OLL #39": "L F' L' U' L U F U' L'",
    "OLL #40": "R' F R U R' U' F' U R",
    "OLL #41": "R U R' U R U2 R' F R U R' U' F'",
    "OLL #42": "R' U' R U' R' U2 R F R U R' U' F'",
    "OLL #43": "F' U' L' U L F",
    "OLL #44 (P)": "F U R U' R' F'",
    "OLL #45 (T-Suit)": "F R U R' U' F'",
    "OLL #46": "R' U' R' F R F' U R",
    "OLL #47": "F' L' U' L U L' U' L U F",
    "OLL #48": "F R U R' U' R U R' U' F'",
    "OLL #49": "r U' r2 U r2 U r2 U' r",
    "OLL #50": "r' U r2 U' r2 U' r2 U r'",
    "OLL #51": "f R U R' U' R U R' U' f'",
    "OLL #52": "R U R' U R U' B U' B' R'",
    "OLL #53": "r' U' R U' R' U R U' R' U2 r",
    "OLL #54": "r U R' U R U' R' U R U2 r'",
    "OLL #55": "R U2 R2 U' R U' R' U2 F R F'",
    "OLL #56": "r U r' U R U' R' U R U' R' r U' r'",
    "OLL #57 (H-Edge)": "R U R' U' M' U R U' r'",
}

_OLL_TABLE: Dict[Tuple[Tuple[int, ...], Tuple[int, ...]], Tuple[str, List[str]]] = {}
for _name, _alg in OLL_ALGS.items():
    _moves = _expand_alg(_alg)
    _inv = [_invert_move(m) for m in reversed(_moves)]
    _case = _apply_seq(SOLVED_CUBIE, _inv)
    _OLL_TABLE[(_case[1][:4], _case[3][:4])] = (_name, _moves)

_PLL_TABLE: Dict[CubieState, Tuple[str, List[str]]] = {}
for _name, _alg in PLL_ALGS.items():
    _moves = _expand_alg(_alg)
    _inv = [_invert_move(m) for m in reversed(_moves)]
    _case = _apply_seq(SOLVED_CUBIE, _inv)
    _PLL_TABLE[_case] = (_name, _moves)


def _match_oll(cur: CubieState) -> Optional[Tuple[str, List[str]]]:
    if cur[1][:4] == (0, 0, 0, 0) and cur[3][:4] == (0, 0, 0, 0):
        return ("OLL Skip", [])
    for auf in ("", "U", "U2", "U'"):
        st = _mul_cubie(cur, CUBIE_MOVES[auf]) if auf else cur
        hit = _OLL_TABLE.get((st[1][:4], st[3][:4]))
        if hit is not None:
            name, moves = hit
            return (name, ([auf] if auf else []) + moves)
    return None


def _match_pll(cur: CubieState) -> Optional[Tuple[str, List[str]]]:
    for u1 in ("", "U", "U2", "U'"):
        s1 = _mul_cubie(cur, CUBIE_MOVES[u1]) if u1 else cur
        if s1 == SOLVED_CUBIE:
            return ("PLL Skip (AUF)" if u1 else "PLL Skip", [u1] if u1 else [])
        for u2 in ("", "U", "U2", "U'"):
            # s1 * pll * u2 == SOLVED  <=>  s1 == inv(u2) * inv(pll)
            s_test = _mul_cubie(CUBIE_MOVES[_invert_move(u2)] if u2 else SOLVED_CUBIE, s1)
            hit = _PLL_TABLE.get(s_test)
            if hit is not None:
                name, moves = hit
                seq = ([u1] if u1 else []) + moves + ([u2] if u2 else [])
                return (f"PLL ({name})", seq)
    return None


def _bfs_predicate(
    start: CubieState,
    allowed_moves: List[str],
    goal_fn: Callable[[CubieState], bool],
    should_abort: Callable[[], bool],
    max_states: int = 250000,
) -> Optional[List[str]]:
    if goal_fn(start):
        return []
    q = deque([(start, None)])
    parent: Dict[CubieState, Tuple[Optional[CubieState], Optional[str]]] = {start: (None, None)}
    while q:
        if should_abort():
            return None
        cur, last_mv = q.popleft()
        for mv in allowed_moves:
            if not _allow_next_move(last_mv, mv):
                continue
            nxt = _mul_cubie(cur, CUBIE_MOVES[mv])
            if nxt not in parent:
                parent[nxt] = (cur, mv)
                if goal_fn(nxt):
                    out: List[str] = []
                    c: Optional[CubieState] = nxt
                    while c is not None:
                        p, pm = parent[c]
                        if pm is not None:
                            out.append(pm)
                        c = p
                    out.reverse()
                    return out
                if len(parent) >= max_states:
                    return None
                q.append((nxt, mv))
    return None


def _bfs_macro_sequences(
    start: CubieState,
    macros: List[List[str]],
    goal_fn: Callable[[CubieState], bool],
    should_abort: Callable[[], bool],
    max_states: int = 250000,
) -> Optional[List[str]]:
    """BFS over composite macro move sequences (e.g. F2L triggers)."""
    if goal_fn(start):
        return []
    macro_effects = [(seq, _apply_seq(SOLVED_CUBIE, seq)) for seq in macros]
    q = deque([start])
    parent: Dict[CubieState, Tuple[Optional[CubieState], Optional[List[str]]]] = {start: (None, None)}
    while q:
        if should_abort():
            return None
        cur = q.popleft()
        for seq, eff in macro_effects:
            nxt = _mul_cubie(cur, eff)
            if nxt not in parent:
                parent[nxt] = (cur, seq)
                if goal_fn(nxt):
                    chunks: List[List[str]] = []
                    c: Optional[CubieState] = nxt
                    while c is not None:
                        p, pseq = parent[c]
                        if pseq is not None:
                            chunks.append(pseq)
                        c = p
                    chunks.reverse()
                    flat: List[str] = []
                    for ch in chunks:
                        flat.extend(ch)
                    return flat
                if len(parent) >= max_states:
                    return None
                q.append(nxt)
    return None


def _solve_cfop(
    cubie: CubieState,
    should_abort: Callable[[], bool],
) -> Optional[Tuple[List[Tuple[str, List[str]]], str]]:
    """Solve via CFOP: Cross -> 4x Intuitive F2L -> Right-Handed OLL -> Right-Handed PLL."""
    stages: List[Tuple[str, List[str]]] = []
    cur = cubie

    # 1. Cross (D-layer edges 4,5,6,7)
    def cross_key(s: CubieState):
        return tuple((s[2].index(e), s[3][s[2].index(e)]) for e in (4, 5, 6, 7))

    cross_moves = _bidirectional_phase(cur, ALL_MOVES, cross_key, [SOLVED_CUBIE], should_abort)
    if cross_moves is None:
        return None
    cross_moves = _simplify_moves(cross_moves)
    cur = _apply_seq(cur, cross_moves)
    stages.append(("Cross", cross_moves))

    # 2. F2L Slots: FR(4,8), FL(5,9), BL(6,10), BR(7,11)
    slots = [
        ("F2L #1 (FR)", 4, 8, ["R U R'", "R U' R'", "R U2 R'", "F' U' F", "F' U F", "F' U2 F"]),
        ("F2L #2 (FL)", 5, 9, ["L' U' L", "L' U L", "L' U2 L", "F U F'", "F U' F'", "F U2 F'"]),
        ("F2L #3 (BL)", 6, 10, ["L U L'", "L U' L'", "L U2 L'", "B' U' B", "B' U B", "B' U2 B"]),
        ("F2L #4 (BR)", 7, 11, ["R' U' R", "R' U R", "R' U2 R", "B U B'", "B U' B'", "B U2 B'"]),
    ]

    def cross_ok(s: CubieState) -> bool:
        return s[2][4:8] == (4, 5, 6, 7) and s[3][4:8] == (0, 0, 0, 0)

    def slot_ok(s: CubieState, c_idx: int, e_idx: int) -> bool:
        return s[0][c_idx] == c_idx and s[1][c_idx] == 0 and s[2][e_idx] == e_idx and s[3][e_idx] == 0

    for idx, (label, c_idx, e_idx, _) in enumerate(slots):
        if slot_ok(cur, c_idx, e_idx) and cross_ok(cur):
            stages.append((f"{label} (Skip)", []))
            continue
        # Allow U turns + triggers of current and remaining unsolved slots (plus any solved slot only if needed)
        trigs: List[List[str]] = [["U"], ["U'"], ["U2"]]
        for j in range(idx, len(slots)):
            for t in slots[j][3]:
                trigs.append(t.split())
        solved_prev = [(slots[p][1], slots[p][2]) for p in range(idx)]

        # Search on reduced state of (cross + solved_prev + current slot) to keep BFS tiny and exact!
        def f2l_goal(s: CubieState) -> bool:
            return cross_ok(s) and slot_ok(s, c_idx, e_idx) and all(slot_ok(s, pc, pe) for pc, pe in solved_prev)

        # Since triggers preserve cross & other F2L slots, reduced state = positions/oris of remaining pieces?
        # Even simpler: BFS over triggers directly on full CubieState? No, U-layer pieces differ -> use _bfs_macro_sequences
        # Wait: at depth <= 4 triggers, 15^4 = 50k states! Let's run BFS on reduced key? No, triggers depend ONLY on slot positions,
        # so full CubieState with max_states=150000? Wait: on U layer, 4! * 4! states could exist; let's mask U-layer!
        def f2l_key(s: CubieState):
            # Track where each F2L corner 4..7 and edge 8..11 sits + cross edges 4..7
            return (
                tuple((s[2].index(e), s[3][s[2].index(e)]) for e in (4, 5, 6, 7)),
                tuple((s[0].index(c), s[1][s[0].index(c)]) for c in range(4, 8)),
                tuple((s[2].index(e), s[3][s[2].index(e)]) for e in range(8, 12)),
            )

        # Wait: U turns only permute U pieces, so f2l_key is 100% deterministic under U and slot triggers!
        macro_effects = [(seq, _apply_seq(SOLVED_CUBIE, seq)) for seq in trigs]
        qk = deque([cur])
        par: Dict[Any, Tuple[Optional[Any], Optional[List[str]]]] = {f2l_key(cur): (None, None)}
        found_seq: Optional[List[str]] = None
        while qk:
            if should_abort():
                return None
            st_c = qk.popleft()
            ck = f2l_key(st_c)
            if f2l_goal(st_c):
                chunks: List[List[str]] = []
                w = ck
                while w is not None:
                    pw, pseq = par[w]
                    if pseq is not None:
                        chunks.append(pseq)
                    w = pw
                chunks.reverse()
                found_seq = _simplify_moves([m for ch in chunks for m in ch])
                break
            for seq, eff in macro_effects:
                nxt = _mul_cubie(st_c, eff)
                nk = f2l_key(nxt)
                if nk not in par:
                    par[nk] = (ck, seq)
                    qk.append(nxt)
        if found_seq is None:
            return None
        cur = _apply_seq(cur, found_seq)
        stages.append((label, found_seq))

    # 3. OLL
    oll_hit = _match_oll(cur)
    if oll_hit is None:
        return None
    oll_name, oll_moves = oll_hit
    cur = _apply_seq(cur, oll_moves)
    stages.append((oll_name, oll_moves))

    # 4. PLL
    pll_hit = _match_pll(cur)
    if pll_hit is None:
        return None
    pll_name, pll_moves = pll_hit
    cur = _apply_seq(cur, pll_moves)
    stages.append((pll_name, pll_moves))
    return stages, "CFOP"


def _solve_zz(
    cubie: CubieState,
    should_abort: Callable[[], bool],
) -> Optional[Tuple[List[Tuple[str, List[str]]], str]]:
    """Solve via ZZ: EOLine -> <R, U, L> ZZF2L -> Right-Handed OCLL + PLL."""
    stages: List[Tuple[str, List[str]]] = []
    cur = cubie

    # 1. EOLine: all 12 edges oriented (eo == 0) + DF(5) and DB(7) solved
    def eoline_key(s: CubieState):
        return (s[3], s[2].index(5), s[2].index(7))

    eo_moves = _bidirectional_phase(cur, ALL_MOVES, eoline_key, [SOLVED_CUBIE], should_abort)
    if eo_moves is None:
        return None
    eo_moves = _simplify_moves(eo_moves)
    cur = _apply_seq(cur, eo_moves)
    stages.append(("EOLine", eo_moves))

    # 2. ZZF2L using strictly <R, U, L> moves: first place DL(6) and DR(4), then 4 pairs
    rul_moves = ["U", "U2", "U'", "R", "R2", "R'", "L", "L2", "L'"]

    def d_edges_key(s: CubieState):
        return (s[2].index(4), s[2].index(5), s[2].index(6), s[2].index(7))

    d_moves = _bidirectional_phase(cur, rul_moves, d_edges_key, [SOLVED_CUBIE], should_abort)
    if d_moves is None:
        return None
    d_moves = _simplify_moves(d_moves)
    cur = _apply_seq(cur, d_moves)
    stages.append(("ZZ D-Line <R,U,L>", d_moves))

    slots = [
        ("ZZ-F2L #1 (FR)", 4, 8, ["R U R'", "R U' R'", "R U2 R'"]),
        ("ZZ-F2L #2 (FL)", 5, 9, ["L' U' L", "L' U L", "L' U2 L"]),
        ("ZZ-F2L #3 (BL)", 6, 10, ["L U L'", "L U' L'", "L U2 L'"]),
        ("ZZ-F2L #4 (BR)", 7, 11, ["R' U' R", "R' U R", "R' U2 R"]),
    ]

    def cross_ok(s: CubieState) -> bool:
        return s[2][4:8] == (4, 5, 6, 7) and s[3] == (0,) * 12

    def slot_ok(s: CubieState, c_idx: int, e_idx: int) -> bool:
        return s[0][c_idx] == c_idx and s[1][c_idx] == 0 and s[2][e_idx] == e_idx and s[3][e_idx] == 0

    for idx, (label, c_idx, e_idx, _) in enumerate(slots):
        if slot_ok(cur, c_idx, e_idx) and cross_ok(cur):
            stages.append((f"{label} (Skip)", []))
            continue
        trigs: List[List[str]] = [["U"], ["U'"], ["U2"]]
        for j in range(idx, len(slots)):
            for t in slots[j][3]:
                trigs.append(t.split())
        solved_prev = [(slots[p][1], slots[p][2]) for p in range(idx)]

        def f2l_goal(s: CubieState) -> bool:
            return cross_ok(s) and slot_ok(s, c_idx, e_idx) and all(slot_ok(s, pc, pe) for pc, pe in solved_prev)

        def f2l_key(s: CubieState):
            return (
                tuple(s[2].index(e) for e in (4, 5, 6, 7)),
                tuple((s[0].index(c), s[1][s[0].index(c)]) for c in range(4, 8)),
                tuple(s[2].index(e) for e in range(8, 12)),
            )

        macro_effects = [(seq, _apply_seq(SOLVED_CUBIE, seq)) for seq in trigs]
        qk = deque([cur])
        par: Dict[Any, Tuple[Optional[Any], Optional[List[str]]]] = {f2l_key(cur): (None, None)}
        found_seq: Optional[List[str]] = None
        while qk:
            if should_abort():
                return None
            st_c = qk.popleft()
            ck = f2l_key(st_c)
            if f2l_goal(st_c):
                chunks: List[List[str]] = []
                w = ck
                while w is not None:
                    pw, pseq = par[w]
                    if pseq is not None:
                        chunks.append(pseq)
                    w = pw
                chunks.reverse()
                found_seq = _simplify_moves([m for ch in chunks for m in ch])
                break
            for seq, eff in macro_effects:
                nxt = _mul_cubie(st_c, eff)
                nk = f2l_key(nxt)
                if nk not in par:
                    par[nk] = (ck, seq)
                    qk.append(nxt)
        if found_seq is None:
            return None
        cur = _apply_seq(cur, found_seq)
        stages.append((label, found_seq))

    # 3. OCLL + PLL (eo == 0 guaranteed!)
    oll_hit = _match_oll(cur)
    if oll_hit is None:
        return None
    oll_name, oll_moves = oll_hit
    cur = _apply_seq(cur, oll_moves)
    stages.append((oll_name, oll_moves))

    pll_hit = _match_pll(cur)
    if pll_hit is None:
        return None
    pll_name, pll_moves = pll_hit
    cur = _apply_seq(cur, pll_moves)
    stages.append((pll_name, pll_moves))
    return stages, "ZZ"


def _solve_one_alg(
    cubie: CubieState,
    macro_name: str,
    macro_str: str,
    edge_buf: int,
    edge_tgt: int,
    corner_setup_faces: List[str],
    should_abort: Callable[[], bool],
) -> Optional[List[Tuple[str, List[str]]]]:
    """Solve any valid cube using ONLY conjugated applications of a single PLL macro (Setup · Macro · Setup')."""
    macro = _expand_alg(macro_str)
    stages: List[Tuple[str, List[str]]] = []

    def edge_setup_for(slot: int, ori: int) -> List[str]:
        q = deque([(slot, ori, [])])
        seen = {(slot, ori)}
        while q:
            p, o, path = q.popleft()
            if p == edge_tgt and o == 0:
                return path
            for m in ALL_MOVES:
                cm = CUBIE_MOVES[m]
                if cm[2][edge_buf] != edge_buf or cm[3][edge_buf] != 0:
                    continue
                np = cm[2].index(p)
                no = o ^ cm[3][np]
                if (np, no) not in seen:
                    seen.add((np, no))
                    q.append((np, no, path + [m]))
        return []

    edge_setups = {
        (s, o): edge_setup_for(s, o)
        for s in range(12)
        if s != edge_buf
        for o in (0, 1)
    }

    cur = cubie
    # Phase 1: Edges via Setup · Macro · Setup'
    while cur[2] != tuple(range(12)) or cur[3] != (0,) * 12:
        if should_abort():
            return None
        b_piece, b_ori = cur[2][edge_buf], cur[3][edge_buf]
        if b_piece == edge_buf:
            tgt = next(i for i in range(12) if i != edge_buf and (cur[2][i] != i or cur[3][i] != 0))
            x = edge_setups[(tgt, 0)]
            label = f"Edge Cycle Break ({EDGE_NAMES[tgt][0]}{EDGE_NAMES[tgt][1]}) via {macro_name}"
        else:
            x = edge_setups[(b_piece, b_ori)]
            label = f"Edge {EDGE_NAMES[b_piece][0]}{EDGE_NAMES[b_piece][1]} via {macro_name}"
        seq = x + macro + [_invert_move(m) for m in reversed(x)]
        cur = _apply_seq(cur, seq)
        stages.append((label, seq))

    # Phase 2: Constructive O(1) corner buffer solver (zero search!)
    # For Jb-Perm: URF(0) is fixed by <L,B,D>, which also fixes {UF, UR} and reaches all 7 other corners.
    # For T-Perm: first place ULB(2) home with <F,B,D> (preserving edge parity invariant), then
    # UBR(3) is fixed by <F,D>, which also fixes ULB(2) & {UL, UR} and reaches all 6 remaining corners.
    def corner_setup_for(c_buf: int, c_tgt: int, allowed_c_moves: List[str], target_slot: int, target_ori: int) -> Optional[List[str]]:
        q = deque([(target_slot, target_ori, [])])
        seen = {(target_slot, target_ori)}
        while q:
            p, o, path = q.popleft()
            if p == c_tgt and o == 0:
                return path
            for m in allowed_c_moves:
                cm = CUBIE_MOVES[m]
                if cm[0][c_buf] != c_buf or cm[1][c_buf] != 0:
                    continue
                np = cm[0].index(p)
                no = (o + cm[1][np]) % 3
                if (np, no) not in seen:
                    seen.add((np, no))
                    q.append((np, no, path + [m]))
        return None

    is_t_perm = edge_buf == 2  # T-Perm uses UL(2) edge buffer, Jb-Perm uses UF(1)
    if is_t_perm:
        # Step 2a: Ensure ULB(2) is solved using <F, B, D>
        if cur[0][2] != 2 or cur[1][2] != 0:
            fbd = [f + s for f in ("F", "B", "D") for s in ("", "'", "2")]
            # Shortest BFS on (where corner 2 is, its ori) -> bring to URF(0) or UBR(3)
            # Wait: find setup X in <F, B, D> that maps slot of corner 2 to URF(0) (ori 0) while keeping UBR(3) at 2?
            # Even simpler: 1 or 2 conjugates in <F, B, D> to place corner 2 at slot 2 ori 0!
            pos2 = cur[0].index(2)
            ori2 = cur[1][pos2]
            # Find X in <F,B,D> mapping (pos2, ori2) -> (0, 0) while mapping (2, 0) -> (3, 0) or vice versa?
            # Simple BFS over (pos_of_2, ori_of_2, cur_at_2_pos, cur_at_2_ori) or directly 1-step/2-step conj!
            q2 = deque([(cur, [])])
            seen2 = {(cur[0].index(2), cur[1][cur[0].index(2)])}
            # Generate short <F,B,D> conjugates
            setups_fbd: List[List[str]] = [[]]
            for m1 in fbd:
                setups_fbd.append([m1])
                for m2 in fbd:
                    if m2[0] != m1[0]:
                        setups_fbd.append([m1, m2])
                        for m3 in fbd:
                            if m3[0] != m2[0]:
                                setups_fbd.append([m1, m2, m3])
            conjs_fbd = []
            seen_c2 = set()
            for x in setups_fbd:
                seq = x + macro + [_invert_move(m) for m in reversed(x)]
                eff = _apply_seq(SOLVED_CUBIE, seq)
                if (eff[0], eff[1]) not in seen_c2:
                    seen_c2.add((eff[0], eff[1]))
                    conjs_fbd.append((eff, seq))
            # Find 1-conj that puts corner 2 at slot 2 ori 0!
            found_seq2: Optional[List[str]] = None
            for eff, seq in conjs_fbd:
                nxt = _mul_cubie(cur, eff)
                if nxt[0][2] == 2 and nxt[1][2] == 0:
                    found_seq2 = seq
                    break
            if found_seq2 is None:
                # 2-conj fallback: first move corner 2 to UBR(3) or anywhere reachable, then to slot 2
                for eff1, seq1 in conjs_fbd:
                    mid = _mul_cubie(cur, eff1)
                    for eff2, seq2 in conjs_fbd:
                        nxt = _mul_cubie(mid, eff2)
                        if nxt[0][2] == 2 and nxt[1][2] == 0:
                            found_seq2 = seq1 + seq2
                            break
                    if found_seq2 is not None:
                        break
            if found_seq2 is None:
                return None
            cur = _apply_seq(cur, found_seq2)
            stages.append((f"Corner ULB via {macro_name}", found_seq2))

        c_buf, c_tgt = 3, 0  # UBR buffer, URF target
        c_moves = [f + s for f in ("F", "D") for s in ("", "'", "2")]
        active_slots = [0, 1, 4, 5, 6, 7]
    else:
        c_buf, c_tgt = 0, 3  # URF buffer, UBR target
        c_moves = [f + s for f in ("L", "B", "D") for s in ("", "'", "2")]
        active_slots = [1, 2, 3, 4, 5, 6, 7]

    c_setups = {
        (s, o): corner_setup_for(c_buf, c_tgt, c_moves, s, o)
        for s in active_slots
        for o in (0, 1, 2)
    }

    for _ in range(30):
        if all(cur[0][i] == i and cur[1][i] == 0 for i in range(8)):
            break
        b_piece, b_ori = cur[0][c_buf], cur[1][c_buf]
        if b_piece == c_buf:
            tgt = next(i for i in active_slots if cur[0][i] != i or cur[1][i] != 0)
            x = c_setups[(tgt, 0)]
            label = f"Corner Cycle Break ({CORNER_NAMES[tgt][0]}{CORNER_NAMES[tgt][1]}{CORNER_NAMES[tgt][2]}) via {macro_name}"
        else:
            # Note: buffer sticker orientation: if piece b_piece sits at c_buf with ori b_ori,
            # bringing slot b_piece with ori (3 - b_ori) % 3 to c_tgt aligns its U/D sticker to c_tgt's U/D!
            x = c_setups[(b_piece, (3 - b_ori) % 3)]
            label = f"Corner {CORNER_NAMES[b_piece][0]}{CORNER_NAMES[b_piece][1]}{CORNER_NAMES[b_piece][2]} via {macro_name}"
        if x is None:
            return None
        seq = x + macro + [_invert_move(m) for m in reversed(x)]
        cur = _apply_seq(cur, seq)
        stages.append((label, seq))

    if cur != SOLVED_CUBIE:
        return None
    return stages


def _is_solved_faces(faces: Dict[str, List[List[str]]]) -> bool:
    for f in FACE_NAMES:
        grid = faces[f]
        c = grid[1][1]
        if any(grid[r][col] != c for r in range(3) for col in range(3)):
            return False
    return True


def _solve_restricted(
    cubie: CubieState,
    method: str,
    should_abort: Callable[[], bool],
) -> Tuple[Optional[List[Tuple[str, List[str]]]], Optional[str]]:
    """Solve under subgroup or <Macro, U> restrictions, returning (stages, error_msg)."""
    if method == "2-Gen <R, U>":
        # Left 2x2x3 block (DLF, DBL, DF, DL, DB, FL, BL) + edge orientation == 0 must be solved
        l_corners_ok = cubie[0][5] == 5 and cubie[0][6] == 6 and cubie[1][5] == 0 and cubie[1][6] == 0
        l_edges_ok = all(cubie[2][i] == i for i in (5, 6, 7, 9, 10)) and cubie[3] == (0,) * 12
        if not (l_corners_ok and l_edges_ok):
            return None, "Cube is not in the 2-Gen <R, U> subgroup (left 2x2x3 block and EO must be solved)."
        moves = _bidirectional_phase(
            cubie,
            ["R", "R2", "R'", "U", "U2", "U'"],
            lambda s: s,
            [SOLVED_CUBIE],
            should_abort,
        )
        if moves is None:
            return None, "State unreachable in <R, U> (corner permutation is outside <R, U>)."
        return [("2-Gen <R, U>", _simplify_moves(moves))], None

    if method == "3-Gen <R, U, L>":
        if cubie[2][5] != 5 or cubie[2][7] != 7 or cubie[3] != (0,) * 12:
            return None, "Cube is not in the 3-Gen <R, U, L> subgroup (DF, DB, and EO must be solved)."
        res = _solve_zz(cubie, should_abort)
        if res is None:
            return None, "Failed to solve within <R, U, L>."
        # Skip EOLine stage if already EO+Line
        return res[0][1:], None

    if method == "Half-Turn <U2..B2>":
        if cubie[1] != (0,) * 8 or cubie[3] != (0,) * 12 or cubie[0] not in VALID_G3_CORNERS:
            return None, "Cube is not in the Half-Turn G3 subgroup."
        moves = _bidirectional_phase(
            cubie,
            ["U2", "D2", "L2", "R2", "F2", "B2"],
            lambda s: (s[0], s[2]),
            [SOLVED_CUBIE],
            should_abort,
        )
        if moves is None:
            return None, "State unreachable via half-turns only."
        return [("Half-Turn <U2..B2>", _simplify_moves(moves))], None

    if method in ("T-Perm + U Only", "Jb-Perm + U Only"):
        is_t = method.startswith("T-Perm")
        macro_name = "T-Perm" if is_t else "Jb-Perm"
        macro_seq = _expand_alg(PLL_ALGS["T" if is_t else "Jb"])
        if cubie[0][4:] != (4, 5, 6, 7) or cubie[1] != (0,) * 8 or cubie[2][4:] != tuple(range(4, 12)) or cubie[3] != (0,) * 12:
            return None, f"{method} only solves U-layer PLL states (F2L and LL orientation must be solved)."
        u_macros = [["U"], ["U2"], ["U'"], macro_seq]
        seq = _bfs_macro_sequences(cubie, u_macros, lambda s: s == SOLVED_CUBIE, should_abort, max_states=50000)
        if seq is None:
            return None, f"State is not reachable using only {macro_name} and U turns."
        return [(f"{macro_name} + U", _simplify_moves(seq))], None

    return None, f"Unknown method: {method}"


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    faces = _faces_from_state(state)
    method = str(params.get("method") or state.get("method") or "Thistlethwaite")

    yield {
        "type": "start",
        "state": {"faces": faces, "method": method},
        "highlights": {},
        "desc": f"Loaded 3x3 Rubik's Cube ({method})",
        "stats": {"moves": 0, "method": method},
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

    stages: List[Tuple[str, List[str]]] = []
    summary_stats: Dict[str, Any] = {"method": method}

    if method == "Thistlethwaite":
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
        summary_stats.update(phase_counts)
        stages = [("Thistlethwaite", moves)]
        summary_desc = (
            f"Found {len(moves)}-move solution "
            f"(G1:{phase_counts['p1']} G2:{phase_counts['p2']} G3:{phase_counts['p3']} G4:{phase_counts['p4']})"
        )
    elif method == "CFOP":
        res_cfop = _solve_cfop(cubie, should_abort)
        if should_abort():
            return
        if res_cfop is None:
            yield {"type": "failed", "state": {"faces": faces}, "highlights": {}, "desc": "CFOP search aborted or failed.", "stats": {}}
            return
        stages = res_cfop[0]
        total = sum(len(m) for _, m in stages)
        summary_desc = f"CFOP ({total} moves): " + " | ".join(f"{name} ({len(m)})" for name, m in stages if m or "Skip" in name)
    elif method == "ZZ":
        res_zz = _solve_zz(cubie, should_abort)
        if should_abort():
            return
        if res_zz is None:
            yield {"type": "failed", "state": {"faces": faces}, "highlights": {}, "desc": "ZZ search aborted or failed.", "stats": {}}
            return
        stages = res_zz[0]
        total = sum(len(m) for _, m in stages)
        summary_desc = f"ZZ ({total} moves): " + " | ".join(f"{name} ({len(m)})" for name, m in stages if m or "Skip" in name)
    elif method in ("1-Alg: T-Perm Only", "1-Alg: Jb-Perm Only"):
        is_t = "T-Perm" in method
        res_1a = _solve_one_alg(
            cubie,
            "T-Perm" if is_t else "Jb-Perm",
            PLL_ALGS["T" if is_t else "Jb"],
            2 if is_t else 1,
            0,
            ["F", "B", "D"] if is_t else ["L", "B", "D"],
            should_abort,
        )
        if should_abort():
            return
        if res_1a is None:
            yield {"type": "failed", "state": {"faces": faces}, "highlights": {}, "desc": f"{method} failed.", "stats": {}}
            return
        stages = res_1a
        total = sum(len(m) for _, m in stages)
        summary_desc = f"{method}: {len(stages)} stage(s), {total} total face turns"
    else:
        res_rest, rerr = _solve_restricted(cubie, method, should_abort)
        if should_abort():
            return
        if res_rest is None:
            yield {"type": "failed", "state": {"faces": faces}, "highlights": {}, "desc": rerr or "Unreachable in selected variant.", "stats": {}}
            return
        stages = res_rest
        total = sum(len(m) for _, m in stages)
        summary_desc = f"{method}: solved in {total} moves"

    # Build flat tagged move sequence
    tagged_moves: List[Tuple[str, str]] = [(mv, sname) for sname, smoves in stages for mv in smoves]
    if not tagged_moves:
        yield {"type": "solution", "state": {"faces": faces}, "highlights": {}, "desc": "Cube is already solved (0 moves)", "stats": {"moves": 0}}
        return

    yield {
        "type": "deduce",
        "state": {"faces": faces},
        "highlights": {},
        "desc": summary_desc,
        "stats": {"moves": len(tagged_moves), **summary_stats},
    }

    cur_faces = faces
    flat_moves = [m for m, _ in tagged_moves]
    for idx, (mv, sname) in enumerate(tagged_moves, start=1):
        if should_abort():
            return
        cur_faces = _apply_moves_to_faces(cur_faces, [mv])
        is_last = idx == len(tagged_moves)
        yield {
            "type": "solution" if is_last else "explore",
            "state": {"faces": cur_faces},
            "highlights": {"face": mv[0], "move": mv, "stage": sname},
            "desc": (
                f"Solved in {len(flat_moves)} moves ({method}): {' '.join(flat_moves)}"
                if is_last
                else f"[{sname}] Move {idx}/{len(flat_moves)}: {mv}"
            ),
            "stats": {"step": idx, "total_moves": len(flat_moves), "move": mv, "stage": sname},
        }
