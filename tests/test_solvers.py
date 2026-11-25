"""Execute every discovered solver on its default preset and verify it reaches a valid solution step."""

import copy
import pytest

from app.registry import discover_solvers
from app.runner import run_solver_sync

SOLVERS = discover_solvers()


ALL_PRESET_CASES = [
    (slug, preset_name)
    for slug in sorted(SOLVERS.keys())
    for preset_name in SOLVERS[slug].meta["presets"]
]


@pytest.mark.parametrize("slug,preset_name", ALL_PRESET_CASES)
def test_solver_all_presets_solve(slug: str, preset_name: str):
    entry = SOLVERS[slug]
    initial_state = copy.deepcopy(entry.meta["presets"][preset_name])
    params = {p["key"]: p.get("default") for p in entry.meta.get("params", [])}
    for key in params:
        if key in initial_state:
            params[key] = initial_state[key]

    result = run_solver_sync(entry, initial_state, params)
    assert result["ok"] is True, f"{slug} [{preset_name}] raised error: {result.get('error')}"
    steps = result["steps"]
    assert len(steps) >= 2, f"{slug} [{preset_name}] yielded too few steps ({len(steps)})"
    assert steps[0]["type"] == "start"
    assert steps[-1]["type"] == "solution", f"{slug} [{preset_name}] ended with {steps[-1]['type']}: {steps[-1]['desc']}"


def test_cooperative_abort_stops_immediately():
    entry = SOLVERS["sudoku"]
    first_preset = next(iter(entry.meta["presets"].values()))
    initial_state = copy.deepcopy(first_preset)
    steps = list(entry.solve(initial_state, {}, lambda: True))
    # Only the initial start step should be yielded before abort check triggers
    assert len(steps) == 1
    assert steps[0]["type"] == "start"


def test_sliding_tile_rectangular_and_unsolvable():
    entry = SOLVERS["sliding_tile"]
    # Solvable 3x4 rectangular board
    rect_state = {
        "rows": 3,
        "cols": 4,
        "board": [
            [1, 2, 3, 4],
            [5, 6, 7, 8],
            [9, 10, 0, 11],
        ],
    }
    res = run_solver_sync(entry, rect_state, {})
    assert res["ok"] is True
    assert res["steps"][-1]["type"] == "solution"

    # Unsolvable 3x3 (swapped 1 and 2)
    bad_state = {
        "rows": 3,
        "cols": 3,
        "board": [
            [2, 1, 3],
            [4, 5, 6],
            [7, 8, 0],
        ],
    }
    res_bad = run_solver_sync(entry, bad_state, {})
    assert res_bad["ok"] is True
    assert res_bad["steps"][-1]["type"] == "failed"
    assert "parity" in res_bad["steps"][-1]["desc"].lower()


def test_unsolvable_diagnostics():
    # Flip (2x2? No, 2x3 or 4x4 has unsolvable states; 4x4 single corner lit is unsolvable over GF(2)?)
    # Actually 5x5 with only (0,0) lit? Let's test 4x4 with a single lit cell or known unsolvable 5x5:
    flip_entry = SOLVERS["flip"]
    res_flip = run_solver_sync(flip_entry, {"board": [[1, 0, 0, 0, 0], [0]*5, [0]*5, [0]*5, [0]*5]}, {})
    assert res_flip["ok"] is True
    assert res_flip["steps"][0]["type"] == "start"
    assert res_flip["steps"][-1]["type"] == "failed"
    assert "gf(2)" in res_flip["steps"][-1]["desc"].lower()

    # Packing grids clue sum mismatch
    pack_entry = SOLVERS["packing_grids"]
    res_pack = run_solver_sync(
        pack_entry,
        {"row_clues": [[1], [1]], "col_clues": [[1], [0]], "board": [[0, 0], [0, 0]]},
        {},
    )
    assert res_pack["ok"] is True
    assert res_pack["steps"][-1]["type"] == "failed"
    assert "parity" in res_pack["steps"][-1]["desc"].lower()

    # Loop games impossible clue
    loop_entry = SOLVERS["loop_games"]
    res_loop = run_solver_sync(
        loop_entry,
        {"rows": 2, "cols": 2, "cell_clues": [[3, 0], [0, 0]], "h_edges": [[0]*2]*3, "v_edges": [[0]*3]*2},
        {},
    )
    assert res_loop["ok"] is True
    assert res_loop["steps"][-1]["type"] == "failed"

    # Palisade invalid region divisibility check
    pal_entry = SOLVERS["palisade"]
    res_pal = run_solver_sync(
        pal_entry,
        {"rows": 4, "cols": 4, "region_size": 5, "cell_clues": [[None] * 4 for _ in range(4)]},
        {},
    )
    assert res_pal["ok"] is True
    assert res_pal["steps"][-1]["type"] == "failed"
    assert "divisibility" in res_pal["steps"][-1]["desc"].lower()


def test_chess_attack_tactics_and_logs():
    entry = SOLVERS["chess_attack"]
    preset = copy.deepcopy(entry.meta["presets"]["6x6 Rook+King"])
    res = run_solver_sync(entry, preset, {"piece_type": "Rook + King", "stars_per_unit": "1"})
    assert res["ok"] is True
    assert res["steps"][-1]["type"] == "solution"
    deduce_steps = [s for s in res["steps"] if s["type"] == "deduce"]
    assert len(deduce_steps) >= 5


def test_maze_geometries_and_tiebreakers():
    entry = SOLVERS["maze_navigator"]
    wt = copy.deepcopy(entry.meta["presets"]["Weighted Terrain 7x7"])

    res_manhattan = run_solver_sync(
        entry,
        copy.deepcopy(wt),
        {"algorithm": "Dijkstra", "maze_type": "Tile Walls", "movement": "Manhattan (4-Way)", "tie_breaker": "None"},
    )
    res_diag = run_solver_sync(
        entry,
        copy.deepcopy(wt),
        {"algorithm": "Dijkstra", "maze_type": "Tile Walls", "movement": "Diagonal Euclidean (8-Way)", "tie_breaker": "None"},
    )
    res_arc = run_solver_sync(
        entry,
        copy.deepcopy(wt),
        {"algorithm": "Dijkstra", "maze_type": "Tile Walls", "movement": "Quarter-Arc Corners", "tie_breaker": "None"},
    )
    assert res_manhattan["steps"][-1]["type"] == "solution"
    assert res_diag["steps"][-1]["type"] == "solution"
    assert res_arc["steps"][-1]["type"] == "solution"
    assert res_diag["steps"][-1]["stats"]["cost"] < res_manhattan["steps"][-1]["stats"]["cost"]
    assert res_arc["steps"][-1]["stats"]["cost"] < res_manhattan["steps"][-1]["stats"]["cost"]
    assert any(op["op"] == "A" for op in res_arc["steps"][-1]["highlights"]["path_svg"])

    # Manhattan default with Quarter-Arc tie-breaker preserves Manhattan cost and adds SVG arcs
    base6 = copy.deepcopy(entry.meta["presets"]["6x6"])
    res_tb_arc = run_solver_sync(
        entry,
        base6,
        {"algorithm": "A*", "maze_type": "Tile Walls", "movement": "Manhattan (4-Way)", "tie_breaker": "Quarter-Arc"},
    )
    assert res_tb_arc["steps"][-1]["type"] == "solution"
    assert res_tb_arc["steps"][-1]["stats"]["cost"] == 10
    assert any(op["op"] == "A" for op in res_tb_arc["steps"][-1]["highlights"]["path_svg"])


def test_rectangular_resizing_and_unified_logs():
    # Rectangular even Unruly 4x6
    res_unruly = run_solver_sync(
        SOLVERS["unruly"],
        {"unique_rows_cols": True, "board": [[0] * 6 for _ in range(4)]},
        {"unique_rows_cols": True},
    )
    assert res_unruly["steps"][-1]["type"] == "solution"

    # Rectangular even Urjo 4x6
    res_urjo = run_solver_sync(
        SOLVERS["urjo"],
        {
            "board": [
                [1, 0, 0, 0, 0, 2],
                [0, 0, 0, 0, 0, 0],
                [0, 0, 0, 0, 0, 0],
                [2, 0, 0, 0, 0, 1],
            ],
            "clues": [[None] * 6 for _ in range(4)],
        },
        {},
    )
    assert res_urjo["steps"][-1]["type"] == "solution"

    # Search solvers emit explore steps (never deduce for heuristic/BFS steps)
    for slug in ("block_escape", "flood", "liquid_sorter", "maze_navigator"):
        e = SOLVERS[slug]
        pst = copy.deepcopy(next(iter(e.meta["presets"].values())))
        res = run_solver_sync(e, pst, {p["key"]: p.get("default") for p in e.meta.get("params", [])})
        assert all(s["type"] != "deduce" for s in res["steps"]), f"{slug} emitted deduce during pure search"
        assert any(s["type"] == "explore" for s in res["steps"]), f"{slug} missing explore step"


def test_liquid_sorter_variable_caps_tokens_and_validation():
    entry = SOLVERS["liquid_sorter"]

    # Variable capacity + mixed letter/number tokens (p,p,p,./1,1,./p,1,.,.)
    res_ok = run_solver_sync(
        entry,
        {
            "capacities": [4, 3, 4],
            "tubes": [["p", "p", "p"], ["1", "1"], ["p", "1"]],
        },
        {"allow_split_colors": False},
    )
    assert res_ok["ok"] is True
    assert res_ok["steps"][-1]["type"] == "solution"
    final_tubes = res_ok["steps"][-1]["state"]["tubes"]
    assert sorted(final_tubes, key=lambda t: (len(t), str(t))) == [[], ["1", "1", "1"], ["p", "p", "p", "p"]]

    # Floating tile rejected
    res_float = run_solver_sync(
        entry,
        {
            "capacities": [4, 4, 4],
            "tubes": [["p", None, "p"], ["p", "p"], []],
        },
        {"allow_split_colors": False},
    )
    assert res_float["steps"][-1]["type"] == "failed"
    assert "floating" in res_float["steps"][-1]["desc"].lower()

    # Mismatched capacity without split rejected
    res_mismatch = run_solver_sync(
        entry,
        {
            "capacities": [4, 4, 4],
            "tubes": [["p", "p", "p"], ["1", "1"], ["1"]],
        },
        {"allow_split_colors": False},
    )
    assert res_mismatch["steps"][-1]["type"] == "failed"

    # Split colors ON: must partition into full 1-color or empty tubes (8 p -> 4+4, 3 r -> 3)
    res_split_ok = run_solver_sync(
        entry,
        {
            "capacities": [4, 4, 3, 4],
            "tubes": [["p", "r", "p", "p"], ["p", "p", "r", "p"], ["r", "p"], ["p"]],
        },
        {"allow_split_colors": True},
    )
    assert res_split_ok["steps"][-1]["type"] == "solution"
    split_final = res_split_ok["steps"][-1]["state"]["tubes"]
    for idx, t in enumerate(split_final):
        assert len(t) == 0 or (len(set(t)) == 1 and len(t) == [4, 4, 3, 4][idx])

    # Split colors ON: impossible to fill whole tubes (5 p, 3 r in [4, 4, 4]) pre-filtered
    res_split_bad = run_solver_sync(
        entry,
        {
            "capacities": [4, 4, 4],
            "tubes": [["p", "p", "p"], ["r", "r", "r"], ["p", "p"]],
        },
        {"allow_split_colors": True},
    )
    assert res_split_bad["steps"][-1]["type"] == "failed"


def test_urjo_coupled_clues_deduction():
    from solvers.urjo import _propagate

    board = [[0] * 6 for _ in range(6)]
    clues = [[None] * 6 for _ in range(6)]
    # Bottom-edge pattern: B at (4,0), R5 at (4,1), B2 at (5,1) -> 3 empty shared neighbors (5,0),(4,2),(5,2)
    # B2 needs 1 more B in those 3 -> 2 R in those 3 -> R5 needs all 3 above it (3,0),(3,1),(3,2) to be R (2).
    board[4][0] = 1
    board[4][1] = 2
    clues[4][1] = 5
    board[5][1] = 1
    clues[5][1] = 2

    steps = []
    ok = _propagate(board, clues, 6, 6, collector=steps)
    assert ok is True
    assert board[3][0] == 2
    assert board[3][1] == 2
    assert board[3][2] == 2
    assert any("Coupled" in reason for _, _, _, reason in steps)


def test_urjo_clue_row_balance_coupling():
    from solvers.urjo import _propagate

    # 6x6: Row 0 has 4 empty cells (0,0)..(0,3) and needs 2 Blues.
    # Clue at (1,1)=1 (Blue) with clue 1 has 0 Blue neighbors and 3 empty neighbors (0,0),(0,1),(0,2).
    # So {(0,0),(0,1),(0,2)} has 1 Blue, forcing (0,3) = 1 (Blue)!
    board = [
        [0, 0, 0, 0, 1, 2],
        [2, 1, 2, 0, 0, 0],
        [2, 2, 2, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0],
    ]
    clues = [[None] * 6 for _ in range(6)]
    clues[1][1] = 1
    steps = []
    ok = _propagate(board, clues, 6, 6, collector=steps)
    assert ok is True
    assert board[0][3] == 1
    assert any("Coupled Clue (2,2) & Row 1" in reason for _, _, _, reason in steps)


def test_urjo_streams_branch_deductions_and_backtracks():
    entry = SOLVERS["urjo"]
    # Empty 4x4 with a single clue forcing branching & backtracking before finding a valid solution
    state = {
        "board": [[0] * 4 for _ in range(4)],
        "clues": [
            [1, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
            [None, None, None, None],
        ],
    }
    res = run_solver_sync(entry, state, {})
    assert res["ok"] is True
    types = [s["type"] for s in res["steps"]]
    assert "explore" in types
    assert "deduce" in types
    assert types[-1] == "solution"
    # Verify branch deductions are interleaved after explore steps rather than batched
    first_explore = types.index("explore")
    assert "deduce" in types[first_explore:]


def test_rubiks_cube_diagnostics_and_abort():
    from solvers.rubiks_cube import _solved_faces, _is_solved_faces

    entry = SOLVERS["rubiks_cube"]
    solved = {"faces": _solved_faces()}
    res_ok = run_solver_sync(entry, solved, {})
    assert res_ok["ok"] is True
    assert res_ok["steps"][0]["type"] == "start"
    assert res_ok["steps"][-1]["type"] == "solution"
    assert _is_solved_faces(res_ok["steps"][-1]["state"]["faces"])

    # Unsolvable: single corner twisted (swap U[2][2] and R[0][0] on URF corner)
    bad_twist = {"faces": _solved_faces()}
    bad_twist["faces"]["U"][2][2], bad_twist["faces"]["R"][0][0] = (
        bad_twist["faces"]["R"][0][0],
        bad_twist["faces"]["U"][2][2],
    )
    res_twist = run_solver_sync(entry, bad_twist, {})
    assert res_twist["ok"] is True
    assert res_twist["steps"][-1]["type"] == "failed"
    assert "twist" in res_twist["steps"][-1]["desc"].lower()

    # Unsolvable: single edge flipped (swap U[2][1] and F[0][1] on UF edge)
    bad_flip = {"faces": _solved_faces()}
    bad_flip["faces"]["U"][2][1], bad_flip["faces"]["F"][0][1] = (
        bad_flip["faces"]["F"][0][1],
        bad_flip["faces"]["U"][2][1],
    )
    res_flip = run_solver_sync(entry, bad_flip, {})
    assert res_flip["ok"] is True
    assert res_flip["steps"][-1]["type"] == "failed"
    assert "edge flip" in res_flip["steps"][-1]["desc"].lower()

    # Cooperative abort stops after start
    first_preset = copy.deepcopy(next(iter(entry.meta["presets"].values())))
    aborted_steps = list(entry.solve(first_preset, {}, lambda: True))
    assert len(aborted_steps) == 1
    assert aborted_steps[0]["type"] == "start"


def test_polyomino_dlx_diagnostics_and_flip():
    entry = SOLVERS["polyomino_dlx"]

    # Area mismatch -> failed cleanly
    res_mismatch = run_solver_sync(
        entry,
        {
            "board": [[0, 0], [0, 0]],
            "pieces": {"I": [[0, 0], [1, 0], [2, 0]]},
        },
        {},
    )
    assert res_mismatch["ok"] is True
    assert res_mismatch["steps"][-1]["type"] == "failed"
    assert "area mismatch" in res_mismatch["steps"][-1]["desc"].lower()

    # Asymmetric L-pentomino on 2x3 with 1 hole needs flip if mirrored:
    # Actually 1x5 I-pentomino on 1x5 solves; unsolvable 2x5 with two L-pentominoes of same chirality vs flip
    asymmetric_state = {
        "board": [[0, 0, 0], [0, 0, -1]],
        "pieces": {"F": [[0, 1], [0, 2], [1, 0], [1, 1], [2, 1]]},
    }
    res_no_sol = run_solver_sync(entry, asymmetric_state, {"allow_flip": False})
    assert res_no_sol["ok"] is True
    assert res_no_sol["steps"][-1]["type"] == "failed"

    # Cooperative abort stops after start
    first_preset = copy.deepcopy(next(iter(entry.meta["presets"].values())))
    aborted_steps = list(entry.solve(first_preset, {}, lambda: True))
    assert len(aborted_steps) == 1
    assert aborted_steps[0]["type"] == "start"

