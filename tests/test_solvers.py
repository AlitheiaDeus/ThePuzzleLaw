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
