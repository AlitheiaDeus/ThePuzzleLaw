"""Execute every discovered solver on its default preset and verify it reaches a valid solution step."""

import copy
import pytest

from app.registry import discover_solvers
from app.runner import run_solver_sync

SOLVERS = discover_solvers()


@pytest.mark.parametrize("slug", sorted(SOLVERS.keys()))
def test_solver_default_preset_solves(slug: str):
    entry = SOLVERS[slug]
    first_preset_name = next(iter(entry.meta["presets"]))
    initial_state = copy.deepcopy(entry.meta["presets"][first_preset_name])
    default_params = {p["key"]: p.get("default") for p in entry.meta.get("params", [])}

    result = run_solver_sync(entry, initial_state, default_params)
    assert result["ok"] is True, f"{slug} raised error: {result.get('error')}"
    steps = result["steps"]
    assert len(steps) >= 2, f"{slug} yielded too few steps ({len(steps)})"
    assert steps[0]["type"] == "start"
    assert steps[-1]["type"] == "solution", f"{slug} ended with {steps[-1]['type']}: {steps[-1]['desc']}"


def test_cooperative_abort_stops_immediately():
    entry = SOLVERS["sudoku"]
    initial_state = copy.deepcopy(entry.meta["presets"]["Hard 9x9"])
    steps = list(entry.solve(initial_state, {}, lambda: True))
    # Only the initial start step should be yielded before abort check triggers
    assert len(steps) == 1
    assert steps[0]["type"] == "start"
