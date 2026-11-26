"""Poly-Slitherlink single-loop solver for Hexagonal, Triangular, and Rhombitrihexagonal (3-4-6-4) tilings."""

from __future__ import annotations

import math
from collections import deque
from typing import Any, Callable, Dict, Generator, List, Optional, Tuple

SQRT3 = math.sqrt(3.0)


def build_tiling(tiling: str, rows: int = 3, cols: int = 3) -> Dict[str, Any]:
    """Construct a flat-top / horizontal-x aligned planar polygon tiling (hex, tri, or 3464) for rows x cols."""
    rows = max(1, min(8, int(rows)))
    cols = max(1, min(8, int(cols)))
    vert_map: Dict[Tuple[int, int], int] = {}
    vertices: List[List[float]] = []
    edge_map: Dict[Tuple[int, int], int] = {}
    edges: List[List[int]] = []
    face_sigs: set[Tuple[int, ...]] = set()
    faces: List[Dict[str, Any]] = []

    def get_vid(x: float, y: float) -> int:
        key = (round(x * 10000), round(y * 10000))
        vid = vert_map.get(key)
        if vid is None:
            vid = len(vertices)
            vert_map[key] = vid
            vertices.append([round(x, 5), round(y, 5)])
        return vid

    def get_eid(u: int, v: int) -> int:
        key = (u, v) if u < v else (v, u)
        eid = edge_map.get(key)
        if eid is None:
            eid = len(edges)
            edge_map[key] = eid
            edges.append([key[0], key[1]])
        return eid

    def add_poly(pts: List[Tuple[float, float]]) -> None:
        vids = [get_vid(px, py) for px, py in pts]
        sig = tuple(sorted(vids))
        if sig in face_sigs:
            return
        face_sigs.add(sig)
        eids = [get_eid(vids[i], vids[(i + 1) % len(vids)]) for i in range(len(vids))]
        faces.append({"verts": vids, "edges": eids, "clue": None})

    if tiling == "hex":
        # Flat-top hexagons (horizontal top/bottom edges), odd-q vertical stagger: downright, upright...
        for r in range(rows):
            for c in range(cols):
                cx = 1.5 * c
                cy = SQRT3 * (r + 0.5 * (c % 2))
                pts = [
                    (cx + math.cos(math.radians(60 * k)), cy + math.sin(math.radians(60 * k)))
                    for k in range(6)
                ]
                add_poly(pts)

    elif tiling == "square":
        # Unit squares in a rows x cols grid
        for r in range(rows):
            for c in range(cols):
                add_poly([(c, r), (c + 1, r), (c + 1, r + 1), (c, r + 1)])

    elif tiling == "tri":
        # Horizontal-base equilateral triangles in a rows x cols grid
        h_tri = SQRT3 / 2.0
        for r in range(rows):
            for c in range(cols):
                x0 = 0.5 * c
                x1 = x0 + 0.5
                x2 = x0 + 1.0
                y_top = r * h_tri
                y_bot = (r + 1) * h_tri
                if (r + c) % 2 == 0:
                    add_poly([(x0, y_bot), (x2, y_bot), (x1, y_top)])
                else:
                    add_poly([(x0, y_top), (x2, y_top), (x1, y_bot)])

    else:  # "3464" Great Honeycomb: only placed hexes + connecting squares + enclosed interior triangles
        D = SQRT3 + 1.0
        hex_centers: Dict[Tuple[int, int], Tuple[float, float, List[Tuple[float, float]]]] = {}
        for r in range(rows):
            for c in range(cols):
                cx = D * (SQRT3 / 2.0) * c
                cy = D * (r + 0.5 * (c % 2))
                h_pts = [
                    (cx + math.cos(math.radians(60 * k)), cy + math.sin(math.radians(60 * k)))
                    for k in range(6)
                ]
                hex_centers[(round(cx * 1000), round(cy * 1000))] = (cx, cy, h_pts)
                add_poly(h_pts)

        for cx, cy, h_pts in hex_centers.values():
            # Add connecting square only if the neighbor hexagon across that edge also exists
            for k in range(6):
                ang = math.radians(30 + 60 * k)
                nx, ny = math.cos(ang), math.sin(ang)
                nb_key = (round((cx + D * nx) * 1000), round((cy + D * ny) * 1000))
                if nb_key in hex_centers:
                    p1 = h_pts[k]
                    p2 = h_pts[(k + 1) % 6]
                    add_poly([p1, p2, (p2[0] + nx, p2[1] + ny), (p1[0] + nx, p1[1] + ny)])

            # Add triangle only if BOTH neighbor hexagons around that corner exist (enclosed gap)
            for k in range(6):
                a1 = math.radians(60 * k - 30)
                a2 = math.radians(60 * k + 30)
                k1 = (round((cx + D * math.cos(a1)) * 1000), round((cy + D * math.sin(a1)) * 1000))
                k2 = (round((cx + D * math.cos(a2)) * 1000), round((cy + D * math.sin(a2)) * 1000))
                if k1 in hex_centers and k2 in hex_centers:
                    p0 = h_pts[k]
                    add_poly([
                        p0,
                        (p0[0] + math.cos(a1), p0[1] + math.sin(a1)),
                        (p0[0] + math.cos(a2), p0[1] + math.sin(a2)),
                    ])

    if vertices:
        xs = [p[0] for p in vertices]
        ys = [p[1] for p in vertices]
        mx = (min(xs) + max(xs)) / 2.0
        my = (min(ys) + max(ys)) / 2.0
        for p in vertices:
            p[0] = round(p[0] - mx, 5)
            p[1] = round(p[1] - my, 5)

    return {
        "tiling": tiling,
        "rows": rows,
        "cols": cols,
        "vertices": vertices,
        "edges": edges,
        "faces": faces,
        "edge_values": [0] * len(edges),
    }


def _build_validated_presets() -> Dict[str, Dict[str, Any]]:
    """Build presets whose clues come directly from an actual valid single loop on each tiling."""
    specs = [
        ("Hexagonal (3x3)", "hex", 3, 3),
        ("Triangular (3x5)", "tri", 3, 5),
        ("3-4-6-4 (2x3)", "3464", 2, 3),
        ("Square (4x4)", "square", 4, 4),
    ]
    out: Dict[str, Dict[str, Any]] = {}
    for name, tiling, rows, cols in specs:
        g = build_tiling(tiling, rows, cols)
        faces = g["faces"]
        edges = g["edges"]
        verts = g["vertices"]
        centroids = [
            (sum(verts[v][0] for v in f["verts"]) / len(f["verts"]), sum(verts[v][1] for v in f["verts"]) / len(f["verts"]))
            for f in faces
        ]

        chosen_faces = set()
        if tiling == "hex":
            for idx, (cx, cy) in enumerate(centroids):
                if math.hypot(cx, cy) < 1.85:
                    chosen_faces.add(idx)
        elif tiling == "square":
            for idx, (cx, cy) in enumerate(centroids):
                if abs(cx) < 1.1 and abs(cy) < 1.1:
                    chosen_faces.add(idx)
        elif tiling == "tri":
            for idx, (cx, cy) in enumerate(centroids):
                if abs(cx) < 0.85 and abs(cy) < 0.55:
                    chosen_faces.add(idx)
        else:  # 3464: pick center-most hexagon + its edge-adjacent squares that keep boundary 2-regular
            hex_indices = [i for i, f in enumerate(faces) if len(f["verts"]) == 6]
            if hex_indices:
                best_h = min(hex_indices, key=lambda i: math.hypot(*centroids[i]))
                chosen_faces.add(best_h)
                h_edges = set(faces[best_h]["edges"])
                for i, f in enumerate(faces):
                    if i != best_h and len(f["verts"]) == 4 and (set(f["edges"]) & h_edges):
                        if len(chosen_faces) < 4:
                            chosen_faces.add(i)

        if not chosen_faces:
            chosen_faces.add(0)

        edge_parity = [0] * len(edges)
        for fi in chosen_faces:
            for ei in faces[fi]["edges"]:
                edge_parity[ei] ^= 1

        for fi, f in enumerate(faces):
            cnt = sum(edge_parity[ei] for ei in f["edges"])
            if fi % 3 != 2 or cnt in (0, len(f["edges"])):
                f["clue"] = cnt
        out[name] = g
    return out


PRESETS = _build_validated_presets()

META: Dict[str, Any] = {
    "slug": "poly_slitherlink",
    "name": "Poly-Slitherlink (Sq / Hex / Tri / 3-4-6-4)",
    "category": "State",
    "renderer": "custom",
    "custom_view": "/renderers/custom/poly_loop_board.js",
    "description": "Solves Slitherlink single-loop puzzles on Square, Hexagonal, Triangular, and Great Honeycomb (3-4-6-4) tilings.",
    "presets": PRESETS,
    "params": [
        {
            "key": "assume_unique",
            "label": "Assume Unique Solution",
            "type": "bool",
            "default": False,
        }
    ],
}


def solve(
    state: Dict[str, Any],
    params: Dict[str, Any],
    should_abort: Callable[[], bool],
) -> Generator[Dict[str, Any], None, None]:
    assume_unique = bool(params.get("assume_unique", False))
    tiling = str(state.get("tiling", "hex"))
    rows = int(state.get("rows", 3))
    cols = int(state.get("cols", 3))
    if "vertices" in state and "edges" in state and "faces" in state:
        vertices = [list(p) for p in state["vertices"]]
        edges = [list(e) for e in state["edges"]]
        faces = [
            {"verts": list(f["verts"]), "edges": list(f["edges"]), "clue": f.get("clue")}
            for f in state["faces"]
        ]
        init_ev = list(state.get("edge_values", [0] * len(edges)))
    else:
        g = build_tiling(tiling, rows, cols)
        vertices = g["vertices"]
        edges = g["edges"]
        faces = g["faces"]
        init_ev = [0] * len(edges)

    n_v = len(vertices)
    n_e = len(edges)
    n_f = len(faces)
    ev = [int(x) if int(x) in (-1, 0, 1) else 0 for x in init_ev]

    # Build vertex -> incident edge indices, and edge -> incident face indices (ext_node = n_f)
    v_edges: List[List[int]] = [[] for _ in range(n_v)]
    for ei, (u, v) in enumerate(edges):
        v_edges[u].append(ei)
        v_edges[v].append(ei)

    ext_node = n_f
    edge_faces: List[List[int]] = [[] for _ in range(n_e)]
    for fi, f in enumerate(faces):
        for ei in f["edges"]:
            edge_faces[ei].append(fi)
    for ei in range(n_e):
        while len(edge_faces[ei]) < 2:
            edge_faces[ei].append(ext_node)

    def snap() -> Dict[str, Any]:
        return {
            "tiling": tiling,
            "rows": rows,
            "cols": cols,
            "vertices": vertices,
            "edges": edges,
            "faces": faces,
            "edge_values": list(ev),
        }

    def count_on() -> int:
        return ev.count(1)

    def is_single_loop() -> bool:
        adj: Dict[int, List[int]] = {}
        for ei, val in enumerate(ev):
            if val == 1:
                u, v = edges[ei]
                adj.setdefault(u, []).append(v)
                adj.setdefault(v, []).append(u)
        if not adj or any(len(nbs) != 2 for nbs in adj.values()):
            return False
        start = next(iter(adj))
        seen = {start}
        q = deque([start])
        while q:
            cur = q.popleft()
            for nb in adj[cur]:
                if nb not in seen:
                    seen.add(nb)
                    q.append(nb)
        if len(seen) != len(adj):
            return False
        for f in faces:
            cl = f["clue"]
            if cl is not None and sum(1 for ei in f["edges"] if ev[ei] == 1) != cl:
                return False
        return True

    def has_premature_loop() -> bool:
        adj: Dict[int, List[int]] = {}
        edge_cnt = 0
        for ei, val in enumerate(ev):
            if val == 1:
                edge_cnt += 1
                u, v = edges[ei]
                adj.setdefault(u, []).append(v)
                adj.setdefault(v, []).append(u)
        if edge_cnt == 0:
            return False
        seen = set()
        for start in adj:
            if start in seen:
                continue
            comp_verts = []
            q = deque([start])
            seen.add(start)
            while q:
                cur = q.popleft()
                comp_verts.append(cur)
                for nb in adj[cur]:
                    if nb not in seen:
                        seen.add(nb)
                        q.append(nb)
            if all(len(adj[x]) == 2 for x in comp_verts):
                if len(comp_verts) < edge_cnt:
                    return True
                for f in faces:
                    cl = f["clue"]
                    if cl is not None and cl > 0:
                        if sum(1 for ei in f["edges"] if ev[ei] == 1) < cl:
                            return True
        return False

    def propagate(
        trail: List[int], allow_lookahead: bool = True, record_events: bool = True
    ) -> Tuple[bool, List[Tuple[int, int, str, Optional[Dict[str, Any]], int]], str]:
        events: List[Tuple[int, int, str, Optional[Dict[str, Any]], int]] = []

        def force(ei: int, val: int, reason: str) -> Optional[bool]:
            if ev[ei] == val:
                return False
            if ev[ei] == -val:
                return None
            ev[ei] = val
            trail.append(ei)
            if record_events:
                events.append((ei, val, reason, snap(), count_on()))
            return True

        changed = True
        while changed:
            changed = False

            # 1. Face clues
            for fi, f in enumerate(faces):
                cl = f["clue"]
                if cl is None:
                    continue
                fe = f["edges"]
                ones = sum(1 for ei in fe if ev[ei] == 1)
                unk = sum(1 for ei in fe if ev[ei] == 0)
                if ones > cl:
                    return False, events, f"Face {fi + 1}={cl} exceeded ({ones} ON)"
                if ones + unk < cl:
                    return False, events, f"Face {fi + 1}={cl} starved ({ones + unk} possible)"
                if unk > 0:
                    if ones == cl:
                        for ei in fe:
                            if ev[ei] == 0:
                                rf = force(ei, -1, f"Face {fi + 1}={cl} satisfied -> E{ei} OFF")
                                if rf is None: return False, events, "Contradiction"
                                if rf: changed = True
                    elif ones + unk == cl:
                        for ei in fe:
                            if ev[ei] == 0:
                                rf = force(ei, 1, f"Face {fi + 1}={cl} needs {unk} -> E{ei} ON")
                                if rf is None: return False, events, "Contradiction"
                                if rf: changed = True

            # 2. Vertex degree rules
            for vi in range(n_v):
                ve = v_edges[vi]
                ones = sum(1 for ei in ve if ev[ei] == 1)
                unk = sum(1 for ei in ve if ev[ei] == 0)
                if ones > 2:
                    return False, events, f"Vertex {vi} degree {ones} > 2"
                if unk == 0 and ones == 1:
                    return False, events, f"Vertex {vi} dead-end (degree 1)"
                if unk > 0:
                    if ones == 2:
                        for ei in ve:
                            if ev[ei] == 0:
                                rf = force(ei, -1, f"Vertex {vi} degree 2 -> E{ei} OFF")
                                if rf is None: return False, events, "Contradiction"
                                if rf: changed = True
                    elif ones == 1 and unk == 1:
                        for ei in ve:
                            if ev[ei] == 0:
                                rf = force(ei, 1, f"Vertex {vi} degree 1 with 1 open -> E{ei} ON")
                                if rf is None: return False, events, "Contradiction"
                                if rf: changed = True
                    elif ones == 0 and unk == 1:
                        for ei in ve:
                            if ev[ei] == 0:
                                rf = force(ei, -1, f"Vertex {vi} isolated (1 open) -> E{ei} OFF")
                                if rf is None: return False, events, "Contradiction"
                                if rf: changed = True

            if changed:
                continue

            # 2b. Generalized (n-1) Umbrella, 1-Bite/Quota, and Adjacent (n-1)-(n-1)
            for fi, f in enumerate(faces):
                cl = f["clue"]
                if cl is None:
                    continue
                n_sides = len(f["edges"])
                f_set = set(f["edges"])
                if cl == n_sides - 1:
                    for vi in f["verts"]:
                        ext_es = [ei for ei in v_edges[vi] if ei not in f_set]
                        in_es = [ei for ei in v_edges[vi] if ei in f_set]
                        if any(ev[ei] == 1 for ei in ext_es):
                            for ei in f["edges"]:
                                if ei not in f_set or ei in in_es:
                                    continue
                                rf = force(ei, 1, f"{n_sides - 1}-Umbrella on Face {fi + 1} -> E{ei} ON")
                                if rf is None: return False, events, "Umbrella contradiction"
                                if rf: changed = True
                            for ei in ext_es:
                                if ev[ei] == 0:
                                    rf = force(ei, -1, f"{n_sides - 1}-Umbrella cull on Face {fi + 1} -> E{ei} OFF")
                                    if rf is None: return False, events, "Umbrella contradiction"
                                    if rf: changed = True
                        elif all(ev[ei] == -1 for ei in ext_es):
                            for ei in in_es:
                                rf = force(ei, 1, f"{n_sides - 1}-Isolated Vertex {vi} on Face {fi + 1} -> E{ei} ON")
                                if rf is None: return False, events, "Isolated vertex contradiction"
                                if rf: changed = True
                # Unified Corner-Entry Quota (for any cell & any clue):
                # If a corner has 1 external ON and all other external edges OFF while both inner edges are open,
                # that corner pair contributes exactly 1 ON and 1 OFF to this cell!
                for vi in f["verts"]:
                    ext_es = [ei for ei in v_edges[vi] if ei not in f_set]
                    in_es = [ei for ei in v_edges[vi] if ei in f_set]
                    if len(in_es) != 2 or any(ev[ei] != 0 for ei in in_es):
                        continue
                    ext_on = sum(1 for ei in ext_es if ev[ei] == 1)
                    ext_off = sum(1 for ei in ext_es if ev[ei] == -1)
                    if ext_on == 1 and ext_on + ext_off == len(ext_es):
                        ones_f = sum(1 for ei in f["edges"] if ev[ei] == 1)
                        unk_f = sum(1 for ei in f["edges"] if ev[ei] == 0)
                        if ones_f + 1 > cl:
                            return False, events, f"Corner-entry quota exceeded on Face {fi + 1}={cl}"
                        if ones_f + unk_f - 1 < cl:
                            return False, events, f"Corner-entry quota starved on Face {fi + 1}={cl}"
                        if ones_f + 1 == cl:
                            for ei in f["edges"]:
                                if ei not in in_es and ev[ei] == 0:
                                    rf = force(ei, -1, f"Corner-entry quota on Face {fi + 1}={cl} -> E{ei} OFF")
                                    if rf is None: return False, events, "Corner-entry quota contradiction"
                                    if rf: changed = True
                        elif ones_f + unk_f - 1 == cl:
                            for ei in f["edges"]:
                                if ei not in in_es and ev[ei] == 0:
                                    rf = force(ei, 1, f"Corner-entry quota on Face {fi + 1}={cl} -> E{ei} ON")
                                    if rf is None: return False, events, "Corner-entry quota contradiction"
                                    if rf: changed = True

                if cl == 1:
                    for vi in f["verts"]:
                        ext_es = [ei for ei in v_edges[vi] if ei not in f_set]
                        in_es = [ei for ei in v_edges[vi] if ei in f_set]
                        ext_off = sum(1 for ei in ext_es if ev[ei] == -1)
                        if ext_off == len(ext_es):
                            for ei in in_es:
                                rf = force(ei, -1, f"1-Bite on Face {fi + 1} -> E{ei} OFF")
                                if rf is None: return False, events, "1-Bite contradiction"
                                if rf: changed = True
                elif n_sides == 4 and cl == 2:
                    verts_4 = f["verts"]
                    for k, vi in enumerate(verts_4):
                        ovi = verts_4[(k + 2) % 4]
                        ext_es = [ei for ei in v_edges[vi] if ei not in f_set]
                        in_es = [ei for ei in v_edges[vi] if ei in f_set]
                        opp_ext = [ei for ei in v_edges[ovi] if ei not in f_set]
                        opp_in = [ei for ei in v_edges[ovi] if ei in f_set]
                        ext_on = sum(1 for ei in ext_es if ev[ei] == 1)
                        ext_off = sum(1 for ei in ext_es if ev[ei] == -1)

                        # Isolated corner on 2: pair its 2 inner edges
                        if ext_off == len(ext_es):
                            if any(ev[ei] == 1 for ei in in_es):
                                for ei in in_es:
                                    rf = force(ei, 1, f"2-Corner Pair on Face {fi + 1} -> E{ei} ON")
                                    if rf is None: return False, events, "2-Corner contradiction"
                                    if rf: changed = True
                            elif any(ev[ei] == -1 for ei in in_es):
                                for ei in in_es:
                                    rf = force(ei, -1, f"2-Corner Pair on Face {fi + 1} -> E{ei} OFF")
                                    if rf is None: return False, events, "2-Corner contradiction"
                                    if rf: changed = True
                                for ei in opp_in:
                                    rf = force(ei, 1, f"2-Corner Pair on Face {fi + 1} -> E{ei} ON")
                                    if rf is None: return False, events, "2-Corner contradiction"
                                    if rf: changed = True

                        # Lone stem entering corner (or 1 ON + 1 OFF on inner edges) -> opposite corner contributes 1 & relays!
                        in_on = sum(1 for ei in in_es if ev[ei] == 1)
                        in_off = sum(1 for ei in in_es if ev[ei] == -1)
                        if (ext_on == 1 and ext_on + ext_off == len(ext_es)) or (in_on == 1 and in_off == 1):
                            opp_off = sum(1 for ei in opp_ext if ev[ei] == -1)
                            opp_on = sum(1 for ei in opp_ext if ev[ei] == 1)
                            opp_unk = [ei for ei in opp_ext if ev[ei] == 0]
                            if opp_off == len(opp_ext):
                                return False, events, f"2-Symmetry contradiction on Face {fi + 1}"
                            if opp_on == 0 and len(opp_unk) == 1:
                                rf = force(opp_unk[0], 1, f"2-Symmetry stem relay on Face {fi + 1} -> E{opp_unk[0]} ON")
                                if rf is None: return False, events, "2-Symmetry contradiction"
                                if rf: changed = True
                            elif opp_on == 1 and opp_unk:
                                for ei in opp_unk:
                                    rf = force(ei, -1, f"2-Symmetry stem cap on Face {fi + 1} -> E{ei} OFF")
                                    if rf is None: return False, events, "2-Symmetry contradiction"
                                    if rf: changed = True

                        # Any external ON edge touching a 2 whose opposite corner is isolated pushes opposite corner ON
                        if ext_on >= 1 and all(ev[ei] == -1 for ei in opp_ext):
                            for ei in opp_in:
                                rf = force(ei, 1, f"2-Corner Push on Face {fi + 1} -> E{ei} ON")
                                if rf is None: return False, events, "2-Corner Push contradiction"
                                if rf: changed = True

            if changed:
                continue

            # 3. Inside/Outside (Jordan Curve 2-Color Parity)
            uf_p = list(range(ext_node + 1))
            uf_w = [0] * (ext_node + 1)

            def uf_find(x: int) -> Tuple[int, int]:
                p = 0
                while uf_p[x] != x:
                    p ^= uf_w[x]
                    x = uf_p[x]
                return x, p

            def uf_union(u: int, v: int, w: int) -> bool:
                ru, pu = uf_find(u)
                rv, pv = uf_find(v)
                if ru == rv:
                    return (pu ^ pv) == w
                uf_p[rv] = ru
                uf_w[rv] = pu ^ pv ^ w
                return True

            for ei, val in enumerate(ev):
                if val != 0:
                    fa, fb = edge_faces[ei]
                    if not uf_union(fa, fb, 1 if val == 1 else 0):
                        return False, events, f"Inside/Outside parity contradiction at E{ei}"

            for ei, val in enumerate(ev):
                if val == 0:
                    fa, fb = edge_faces[ei]
                    ra, pa = uf_find(fa)
                    rb, pb = uf_find(fb)
                    if ra == rb:
                        nv = 1 if (pa ^ pb) == 1 else -1
                        lbl = "ON" if nv == 1 else "OFF"
                        rf = force(ei, nv, f"Inside/Outside parity -> E{ei} {lbl}")
                        if rf is None: return False, events, "Inside/Outside parity contradiction"
                        if rf: changed = True

            # 3b. A|B Opposite-Parity Pair on 1 / (n-1) cells:
            # If two undecided edges of a cell lead to neighbors with opposite parities in the same UF component,
            # exactly 1 of those 2 edges is ON and 1 is OFF!
            for fi, f in enumerate(faces):
                cl = f["clue"]
                if cl is None:
                    continue
                n_sides = len(f["edges"])
                if cl not in (1, n_sides - 1):
                    continue
                unk_es = [ei for ei in f["edges"] if ev[ei] == 0]
                if len(unk_es) <= 2:
                    continue
                seen_pair: Dict[int, List[Tuple[int, int]]] = {}
                opp_pair: Optional[Tuple[int, int]] = None
                for ei in unk_es:
                    fa, fb = edge_faces[ei]
                    nb = fb if fa == fi else fa
                    rn, pn = uf_find(nb)
                    lst = seen_pair.setdefault(rn, [])
                    for oei, op in lst:
                        if op != pn:
                            opp_pair = (oei, ei)
                            break
                    if opp_pair is not None:
                        break
                    lst.append((ei, pn))
                if opp_pair is not None:
                    forced_v = -1 if cl == 1 else 1
                    lbl = "OFF" if forced_v == -1 else "ON"
                    for ei in unk_es:
                        if ei not in opp_pair:
                            rf = force(ei, forced_v, f"A|B parity pair on Face {fi + 1}={cl} -> E{ei} {lbl}")
                            if rf is None: return False, events, "A|B parity pair contradiction"
                            if rf: changed = True

            # 4. Pangea (No-Islands + A|B + Connecting Rivers Cut-Vertex)
            pass_adj: List[List[Tuple[int, int]]] = [[] for _ in range(ext_node + 1)]
            for ei, val in enumerate(ev):
                if val != 1:
                    fa, fb = edge_faces[ei]
                    pass_adj[fa].append((fb, ei))
                    pass_adj[fb].append((fa, ei))

            known_state = [-1] * (ext_node + 1)
            known_state[ext_node] = 0
            in_cells: List[int] = []
            out_cells: List[int] = []
            ab_groups: Dict[int, Tuple[List[int], List[int]]] = {}
            for fi in range(n_f):
                rc, pc = uf_find(fi)
                if rc == ext_node:
                    known_state[fi] = pc
                    (in_cells if pc == 1 else out_cells).append(fi)
                else:
                    g0, g1 = ab_groups.setdefault(rc, ([], []))
                    (g1 if pc == 1 else g0).append(fi)

            def bfs_pass(start: int, forbidden: int) -> List[bool]:
                vis = [False] * (ext_node + 1)
                if known_state[start] == forbidden:
                    return vis
                vis[start] = True
                q = [start]
                qi = 0
                while qi < len(q):
                    cur = q[qi]
                    qi += 1
                    for nb, _ in pass_adj[cur]:
                        if not vis[nb] and known_state[nb] != forbidden:
                            vis[nb] = True
                            q.append(nb)
                return vis

            reach_ext = bfs_pass(ext_node, 1)
            for oc in out_cells:
                if not reach_ext[oc]:
                    return False, events, f"Isolated OUTSIDE face {oc + 1}"

            reach_in: Optional[List[bool]] = None
            if in_cells:
                reach_in = bfs_pass(in_cells[0], 0)
                for ic in in_cells[1:]:
                    if not reach_in[ic]:
                        return False, events, f"Disconnected INSIDE island at face {ic + 1}"

            resolved_any = False
            for rc, (g0, g1) in ab_groups.items():
                g0_out = all(reach_ext[x] for x in g0)
                g1_out = all(reach_ext[x] for x in g1)
                g0_in = True if reach_in is None else all(reach_in[x] for x in g0)
                g1_in = True if reach_in is None else all(reach_in[x] for x in g1)
                if not g0_out and not g1_out:
                    return False, events, "Pangea A|B contradiction (no EXTERIOR path)"
                if not g0_in and not g1_in:
                    return False, events, "Pangea A|B contradiction (no INSIDE path)"
                fg0: Optional[int] = None
                if not g0_out or not g1_in:
                    fg0 = 1
                elif not g1_out or not g0_in:
                    fg0 = 0
                if fg0 is not None:
                    if not uf_union(rc, ext_node, fg0):
                        return False, events, "Pangea A|B parity contradiction"
                    resolved_any = True
                    for x in g0:
                        known_state[x] = fg0
                        (in_cells if fg0 == 1 else out_cells).append(x)
                    for x in g1:
                        known_state[x] = 1 - fg0
                        (in_cells if (1 - fg0) == 1 else out_cells).append(x)

            if len(in_cells) >= 2:
                ld = [-1] * n_f
                ll = [0] * n_f
                ls = [0] * n_f
                lt = [0]
                tot_in = len(in_cells)
                l_cuts: List[int] = []

                def t_land(u: int, p: int) -> None:
                    ld[u] = ll[u] = lt[0]
                    lt[0] += 1
                    ls[u] = 1 if known_state[u] == 1 else 0
                    sep = False
                    for nb, _ in pass_adj[u]:
                        if nb == ext_node or known_state[nb] == 0 or nb == p:
                            continue
                        if ld[nb] == -1:
                            t_land(nb, u)
                            ll[u] = min(ll[u], ll[nb])
                            ls[u] += ls[nb]
                            if p != -1 and ll[nb] >= ld[u] and 0 < ls[nb] < tot_in:
                                sep = True
                        else:
                            ll[u] = min(ll[u], ld[nb])
                    if known_state[u] == -1 and sep:
                        l_cuts.append(u)

                t_land(in_cells[0], -1)
                for w in l_cuts:
                    if not uf_union(w, ext_node, 1):
                        return False, events, "Pangea river-cut contradiction"
                    known_state[w] = 1
                    in_cells.append(w)
                    resolved_any = True

            if out_cells:
                wd = [-1] * (ext_node + 1)
                wl = [0] * (ext_node + 1)
                ws = [0] * (ext_node + 1)
                wt = [0]
                w_cuts: List[int] = []

                def t_water(u: int, p: int) -> None:
                    wd[u] = wl[u] = wt[0]
                    wt[0] += 1
                    ws[u] = 1 if (u != ext_node and known_state[u] == 0) else 0
                    sep = False
                    for nb, _ in pass_adj[u]:
                        if known_state[nb] == 1 or nb == p:
                            continue
                        if wd[nb] == -1:
                            t_water(nb, u)
                            wl[u] = min(wl[u], wl[nb])
                            ws[u] += ws[nb]
                            if p != -1 and wl[nb] >= wd[u] and ws[nb] > 0:
                                sep = True
                        else:
                            wl[u] = min(wl[u], wd[nb])
                    if u != ext_node and known_state[u] == -1 and sep:
                        w_cuts.append(u)

                t_water(ext_node, -1)
                for w in w_cuts:
                    if not uf_union(w, ext_node, 0):
                        return False, events, "Pangea land-cut contradiction"
                    known_state[w] = 0
                    out_cells.append(w)
                    resolved_any = True

            if resolved_any:
                for ei, val in enumerate(ev):
                    if val == 0:
                        fa, fb = edge_faces[ei]
                        ra, pa = uf_find(fa)
                        rb, pb = uf_find(fb)
                        if ra == rb:
                            nv = 1 if (pa ^ pb) == 1 else -1
                            lbl = "ON" if nv == 1 else "OFF"
                            rf = force(ei, nv, f"Pangea cut -> E{ei} {lbl}")
                            if rf is None: return False, events, "Pangea parity contradiction"
                            if rf: changed = True

            # 5. Cycle-Bridge Elimination on (!= -1) vertex graph
            v_adj: List[List[Tuple[int, int]]] = [[] for _ in range(n_v)]
            for ei, val in enumerate(ev):
                if val != -1:
                    u, v = edges[ei]
                    v_adj[u].append((v, ei))
                    v_adj[v].append((u, ei))
            vd = [-1] * n_v
            vl = [0] * n_v
            vt = [0]
            c_bridges: List[int] = []

            def t_cycle(u: int, pei: int) -> None:
                vd[u] = vl[u] = vt[0]
                vt[0] += 1
                for nb, cei in v_adj[u]:
                    if cei == pei:
                        continue
                    if vd[nb] == -1:
                        t_cycle(nb, cei)
                        vl[u] = min(vl[u], vl[nb])
                        if vl[nb] > vd[u]:
                            c_bridges.append(cei)
                    else:
                        vl[u] = min(vl[u], vd[nb])

            for sv in range(n_v):
                if vd[sv] == -1 and v_adj[sv]:
                    t_cycle(sv, -1)

            for ei in c_bridges:
                if ev[ei] == 1:
                    return False, events, f"Stranded bridge ON edge E{ei}"
                if ev[ei] == 0:
                    rf = force(ei, -1, f"Stranded bridge -> E{ei} OFF")
                    if rf is None: return False, events, "Stranded bridge contradiction"
                    if rf: changed = True

            # 6. Premature Loop Avoidance
            adj_on: Dict[int, List[int]] = {}
            tot_on = 0
            for ei, val in enumerate(ev):
                if val == 1:
                    tot_on += 1
                    u, v = edges[ei]
                    adj_on.setdefault(u, []).append(v)
                    adj_on.setdefault(v, []).append(u)
            if tot_on > 0:
                cid_map: Dict[int, int] = {}
                cid_cnt: Dict[int, int] = {}
                cid = 0
                for sv in adj_on:
                    if sv in cid_map:
                        continue
                    st = [sv]
                    cid_map[sv] = cid
                    ec = 0
                    while st:
                        cur = st.pop()
                        for nb in adj_on[cur]:
                            ec += 1
                            if nb not in cid_map:
                                cid_map[nb] = cid
                                st.append(nb)
                    cid_cnt[cid] = ec // 2
                    cid += 1
                any_unsat = any(
                    f["clue"] is not None and f["clue"] > 0
                    and sum(1 for ei in f["edges"] if ev[ei] == 1) < f["clue"]
                    for f in faces
                )
                for ei, val in enumerate(ev):
                    if val == 0:
                        u, v = edges[ei]
                        if u in cid_map and cid_map.get(v) == cid_map[u]:
                            if cid_cnt[cid_map[u]] < tot_on or any_unsat:
                                rf = force(ei, -1, f"Avoid premature loop -> E{ei} OFF")
                                if rf is None: return False, events, "Premature loop contradiction"
                                if rf: changed = True

        if has_premature_loop():
            return False, events, "Premature closed loop detected"

        if allow_lookahead:
            while True:
                if should_abort():
                    return True, events, ""
                cands: List[Tuple[int, int]] = []
                for ei, val in enumerate(ev):
                    if val == 0:
                        u, v = edges[ei]
                        pr = 0
                        if any(ev[xe] == 1 for xe in v_edges[u]) or any(ev[xe] == 1 for xe in v_edges[v]):
                            pr += 10
                        if any(fi < n_f and faces[fi]["clue"] is not None for fi in edge_faces[ei]):
                            pr += 2
                        cands.append((-pr, ei))
                cands.sort()
                forced_any = False
                for _, ei in cands:
                    if should_abort():
                        return True, events, ""
                    if ev[ei] != 0:
                        continue
                    ok_vals: List[int] = []
                    fail_reasons: Dict[int, str] = {}
                    for tv in (1, -1):
                        tmp: List[int] = [ei]
                        ev[ei] = tv
                        tok, _, terr = propagate(tmp, allow_lookahead=False, record_events=False)
                        for te in tmp:
                            ev[te] = 0
                        if tok:
                            ok_vals.append(tv)
                        else:
                            fail_reasons[tv] = terr
                    if not ok_vals:
                        return False, events, f"1-ply contradiction on E{ei}"
                    if len(ok_vals) == 1:
                        wv = ok_vals[0]
                        lose_lbl = "OFF" if wv == 1 else "ON"
                        win_lbl = "ON" if wv == 1 else "OFF"
                        rf = force(ei, wv, f"Lookahead (E{ei}={lose_lbl} -> {fail_reasons[-wv]}) -> {win_lbl}")
                        if rf is None: return False, events, "Lookahead contradiction"
                        if rf:
                            sok, sev, serr = propagate(trail, allow_lookahead=False, record_events=True)
                            events.extend(sev)
                            if not sok:
                                return False, events, serr
                            forced_any = True
                            break
                if not forced_any:
                    break

        return True, events, ""

    def pick_next_edge() -> Optional[int]:
        best: Optional[Tuple[int, int]] = None
        for ei, val in enumerate(ev):
            if val == 0:
                u, v = edges[ei]
                sc = 0
                if any(ev[xe] == 1 for xe in v_edges[u]) or any(ev[xe] == 1 for xe in v_edges[v]):
                    sc += 10
                for fi in edge_faces[ei]:
                    if fi < n_f and faces[fi]["clue"] is not None:
                        sc += 3
                cand = (-sc, ei)
                if best is None or cand < best:
                    best = cand
        return best[1] if best is not None else None

    def group_events(
        raw: List[Tuple[int, int, str, Optional[Dict[str, Any]], int]]
    ) -> List[Tuple[List[int], str, Dict[str, Any], int]]:
        """Group consecutive deductions from the same local rule firing into a single step."""
        no_group = {"Inside/Outside parity", "Stranded bridge", "Avoid premature loop", "Pangea cut"}
        grouped: List[Tuple[List[int], str, Dict[str, Any], int]] = []
        cur_key: Optional[str] = None
        cur_first_reason = ""
        cur_eids: List[int] = []
        cur_labels: List[str] = []
        cur_snap: Dict[str, Any] = {}
        cur_seg = 0
        for ei, ev_val, reason, ev_snap, ev_seg in raw:
            prefix = reason.split(" -> ")[0]
            can_group = prefix not in no_group
            lbl = f"E{ei} {'ON' if ev_val == 1 else 'OFF'}"
            if can_group and cur_key == prefix:
                cur_eids.append(ei)
                cur_labels.append(lbl)
                cur_snap = ev_snap or snap()
                cur_seg = ev_seg
            else:
                if cur_eids:
                    desc = f"{cur_key} -> {', '.join(cur_labels)}" if (cur_key and len(cur_eids) > 1) else cur_first_reason
                    grouped.append((cur_eids, desc, cur_snap, cur_seg))
                cur_key = prefix if can_group else None
                cur_first_reason = reason
                cur_eids = [ei]
                cur_labels = [lbl]
                cur_snap = ev_snap or snap()
                cur_seg = ev_seg
        if cur_eids:
            desc = f"{cur_key} -> {', '.join(cur_labels)}" if (cur_key and len(cur_eids) > 1) else cur_first_reason
            grouped.append((cur_eids, desc, cur_snap, cur_seg))
        return grouped

    yield {
        "type": "start",
        "state": snap(),
        "highlights": {},
        "desc": f"Loaded {tiling.upper()} Slitherlink ({n_f} faces, {n_e} edges)",
        "stats": {"faces": n_f, "edges": n_e, "segments": count_on(), "branches": 0, "backtracks": 0},
    }

    stats = {"branches": 0, "backtracks": 0}
    stalled = False

    def solve_gen() -> Generator[Tuple[str, List[int], str, Dict[str, Any], int], None, bool]:
        nonlocal stalled
        nxt = pick_next_edge()
        if nxt is None:
            return is_single_loop()
        for val in (1, -1):
            if should_abort():
                return False
            stats["branches"] += 1
            trail: List[int] = [nxt]
            ev[nxt] = val
            lbl = "ON" if val == 1 else "OFF"
            prefix = "Deduction stalled -> " if not stalled else ""
            stalled = True
            yield ("explore", [nxt], f"{prefix}Branch E{nxt} = {lbl}", snap(), count_on())
            ok, events, err = propagate(trail)
            for eids_grp, creason, ev_snap, ev_seg in group_events(events):
                yield ("deduce", eids_grp, creason, ev_snap, ev_seg)
            if ok:
                solved = yield from solve_gen()
                if solved:
                    return True
            else:
                stats["backtracks"] += 1
                yield ("backtrack", [nxt], f"Contradiction ({err}) -> backtrack E{nxt}", snap(), count_on())
            for te in trail:
                ev[te] = 0
        return False

    init_trail: List[int] = []
    ok, init_events, init_err = propagate(init_trail)
    for eids_grp, creason, ev_snap, ev_seg in group_events(init_events):
        if should_abort():
            return
        yield {
            "type": "deduce",
            "state": ev_snap,
            "highlights": {"edge_indices": eids_grp},
            "desc": creason,
            "stats": {"segments": ev_seg, **stats},
        }

    if not ok:
        yield {
            "type": "failed",
            "state": snap(),
            "highlights": {},
            "desc": f"Pre-search contradiction: {init_err}.",
            "stats": stats,
        }
        return

    found = False
    gen = solve_gen()
    try:
        while True:
            if should_abort():
                return
            stype, ei_refs, desc, step_snap, step_seg = next(gen)
            yield {
                "type": stype,
                "state": step_snap,
                "highlights": {"edge_indices": ei_refs} if ei_refs else {},
                "desc": desc,
                "stats": {"segments": step_seg, **stats},
            }
    except StopIteration as stop:
        found = bool(stop.value)

    if should_abort():
        return

    if found:
        yield {
            "type": "solution",
            "state": snap(),
            "highlights": {},
            "desc": f"Solved {tiling.upper()} Slitherlink ({count_on()} segments, {stats['branches']} branches, {stats['backtracks']} backtracks)",
            "stats": {"segments": count_on(), **stats},
        }
    else:
        yield {
            "type": "failed",
            "state": snap(),
            "highlights": {},
            "desc": "No valid single loop exists for these clues.",
            "stats": stats,
        }
