"""Local FastAPI server for The Puzzle Law v2."""

from __future__ import annotations

import argparse
import json
import threading
import webbrowser
from pathlib import Path
from typing import Any, Dict

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .registry import discover_solvers, list_solver_metadata
from .runner import JOBS, iter_solver_events, run_solver_sync

WEB_DIR = Path(__file__).resolve().parent.parent / "web"

app = FastAPI(title="The Puzzle Law", version="2.0.0")


class SolveRequest(BaseModel):
    state: Dict[str, Any] = Field(default_factory=dict)
    params: Dict[str, Any] = Field(default_factory=dict)


APP_LAUNCH_THEME = "chalk"


@app.get("/api/health")
def health() -> Dict[str, Any]:
    return {"status": "ok", "version": "2.0.0", "solvers": len(discover_solvers()), "theme": APP_LAUNCH_THEME}


@app.get("/api/solvers")
def get_solvers() -> Dict[str, Any]:
    return {"solvers": list_solver_metadata()}


@app.post("/api/solve/{slug}")
def solve_sync(slug: str, req: SolveRequest) -> Dict[str, Any]:
    solvers = discover_solvers()
    entry = solvers.get(slug)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown solver '{slug}'")
    return run_solver_sync(entry, req.state, req.params)


@app.post("/api/solve/{slug}/stream")
def solve_stream(slug: str, req: SolveRequest) -> StreamingResponse:
    solvers = discover_solvers()
    entry = solvers.get(slug)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Unknown solver '{slug}'")

    def event_generator():
        for item in iter_solver_events(entry, req.state, req.params):
            payload = json.dumps(item["data"])
            yield f"event: {item['event']}\ndata: {payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.post("/api/abort/{job_id}")
def abort_job(job_id: str) -> Dict[str, Any]:
    aborted = JOBS.abort(job_id)
    return {"job_id": job_id, "aborted": aborted}


@app.get("/")
def serve_index() -> FileResponse:
    index_path = WEB_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="web/index.html not found")
    return FileResponse(index_path)


@app.get("/favicon.ico", include_in_schema=False)
def serve_favicon() -> FileResponse:
    icon_path = WEB_DIR / "favicon.svg"
    if not icon_path.exists():
        raise HTTPException(status_code=404, detail="web/favicon.svg not found")
    return FileResponse(icon_path, media_type="image/svg+xml")


if WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=str(WEB_DIR), html=True), name="web")


def main() -> None:
    global APP_LAUNCH_THEME
    parser = argparse.ArgumentParser(description="Launch The Puzzle Law local web hub.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--theme",
        default="chalk",
        choices=["chalk", "plum", "slate", "forge"],
        help="Initial UI theme (default: chalk)",
    )
    parser.add_argument("--no-browser", action="store_true", help="Do not auto-open browser")
    args = parser.parse_args()

    APP_LAUNCH_THEME = args.theme
    url = f"http://{args.host}:{args.port}/?theme={args.theme}"
    if not args.no_browser:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")


if __name__ == "__main__":
    main()
