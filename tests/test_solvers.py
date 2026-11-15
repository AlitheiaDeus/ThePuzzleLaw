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
