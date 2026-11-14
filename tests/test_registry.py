"""Verify dynamic solver discovery and metadata contract across solvers/*.py."""

from app.registry import discover_solvers, list_solver_metadata


def test_all_solvers_discovered_and_valid():
    solvers = discover_solvers()
    expected = {
        "block_escape",
        "chess_attack",
        "cipher_suite",
        "flip",
        "flood",
        "flow",
        "liquid_sorter",
        "loop_games",
        "maze_navigator",
        "morse_decoder",
        "packing_grids",
        "sliding_tile",
        "sudoku",
        "unruly",
        "urjo",
    }
    assert expected.issubset(set(solvers.keys()))

    meta_list = list_solver_metadata()
    assert len(meta_list) == len(solvers)
    for meta in meta_list:
        assert meta["slug"]
        assert meta["name"]
        assert meta["category"]
        assert meta["renderer"] in ("grid", "text", "custom")
        assert isinstance(meta["presets"], dict) and len(meta["presets"]) >= 1
