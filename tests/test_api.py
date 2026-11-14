"""Smoke tests for FastAPI endpoints and SSE step streaming."""

import copy
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_solvers_listing():
    r_health = client.get("/api/health")
    assert r_health.status_code == 200
    assert r_health.json()["status"] == "ok"

    r_solvers = client.get("/api/solvers")
    assert r_solvers.status_code == 200
    solvers = r_solvers.json()["solvers"]
    assert len(solvers) >= 15


def test_index_html_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "The Puzzle Law" in r.text


def test_sync_solve_and_stream_endpoints():
    solvers = client.get("/api/solvers").json()["solvers"]
    sudoku_meta = next(s for s in solvers if s["slug"] == "sudoku")
    preset = copy.deepcopy(sudoku_meta["presets"]["Mini 4x4"])

    r_sync = client.post("/api/solve/sudoku", json={"state": preset, "params": {}})
    assert r_sync.status_code == 200
    data = r_sync.json()
    assert data["ok"] is True
    assert data["steps"][-1]["type"] == "solution"

    r_stream = client.post("/api/solve/sudoku/stream", json={"state": preset, "params": {}})
    assert r_stream.status_code == 200
    assert "event: job" in r_stream.text
    assert "event: step" in r_stream.text
    assert "event: done" in r_stream.text
