"""Generator execution engine with cooperative cancellation and step capping."""

from __future__ import annotations

import threading
import time
import uuid
from typing import Any, Dict, Iterator, List, Optional

from .registry import SolverEntry

MAX_BUFFERED_STEPS = 2000


class JobRegistry:
    """Tracks active solver jobs so the frontend can request cooperative abort."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._events: Dict[str, threading.Event] = {}

    def create(self) -> tuple[str, threading.Event]:
        job_id = uuid.uuid4().hex[:12]
        ev = threading.Event()
        with self._lock:
            self._events[job_id] = ev
        return job_id, ev

    def abort(self, job_id: str) -> bool:
        with self._lock:
            ev = self._events.get(job_id)
        if ev is None:
            return False
        ev.set()
        return True

    def remove(self, job_id: str) -> None:
        with self._lock:
            self._events.pop(job_id, None)


JOBS = JobRegistry()


def run_solver_sync(
    entry: SolverEntry,
    state: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    max_steps: int = MAX_BUFFERED_STEPS,
) -> Dict[str, Any]:
    """Execute a solver generator synchronously and return all yielded steps."""
    params = params or {}
    t0 = time.perf_counter()
    steps: List[Dict[str, Any]] = []
    aborted = False

    def should_abort() -> bool:
        return aborted

    try:
        for idx, step in enumerate(entry.solve(state, params, should_abort)):
            steps.append(step)
            if idx + 1 >= max_steps:
                aborted = True
                break
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ok": True,
            "slug": entry.slug,
            "steps": steps,
            "elapsed_ms": elapsed_ms,
            "truncated": aborted,
        }
    except Exception as exc:
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        return {
            "ok": False,
            "slug": entry.slug,
            "error": str(exc),
            "steps": steps,
            "elapsed_ms": elapsed_ms,
        }


def iter_solver_events(
    entry: SolverEntry,
    state: Dict[str, Any],
    params: Optional[Dict[str, Any]] = None,
    max_steps: int = MAX_BUFFERED_STEPS,
) -> Iterator[Dict[str, Any]]:
    """Yield SSE-ready event dicts for a solver job with cooperative cancellation."""
    params = params or {}
    job_id, abort_event = JOBS.create()
    t0 = time.perf_counter()
    yield {"event": "job", "data": {"job_id": job_id, "slug": entry.slug}}

    try:
        count = 0
        for step in entry.solve(state, params, abort_event.is_set):
            if abort_event.is_set():
                yield {"event": "aborted", "data": {"job_id": job_id, "steps": count}}
                return
            yield {"event": "step", "data": step}
            count += 1
            if count >= max_steps:
                abort_event.set()
                yield {
                    "event": "warning",
                    "data": {"message": f"Step limit ({max_steps}) reached."},
                }
                break
        elapsed_ms = round((time.perf_counter() - t0) * 1000, 2)
        yield {"event": "done", "data": {"job_id": job_id, "steps": count, "elapsed_ms": elapsed_ms}}
    except Exception as exc:
        yield {"event": "error", "data": {"job_id": job_id, "error": str(exc)}}
    finally:
        JOBS.remove(job_id)
