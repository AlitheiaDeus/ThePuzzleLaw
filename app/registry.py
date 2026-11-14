"""Dynamic solver discovery and metadata registry for solvers/*.py."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Callable, Dict, Generator, List

SOLVERS_DIR = Path(__file__).resolve().parent.parent / "solvers"

SolveFn = Callable[[Dict[str, Any], Dict[str, Any], Callable[[], bool]], Generator[Dict[str, Any], None, None]]


@dataclass(frozen=True)
class SolverEntry:
    slug: str
    meta: Dict[str, Any]
    solve: SolveFn
    module: ModuleType


def _load_module_from_path(path: Path) -> ModuleType:
    module_name = f"solvers.{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not create module spec for {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def discover_solvers(solvers_dir: Path = SOLVERS_DIR) -> Dict[str, SolverEntry]:
    """Scan solvers/*.py and return validated SolverEntry objects keyed by slug."""
    entries: Dict[str, SolverEntry] = {}
    if not solvers_dir.exists():
        return entries

    for path in sorted(solvers_dir.glob("*.py")):
        if path.name.startswith("_"):
            continue
        module = _load_module_from_path(path)
        meta = getattr(module, "META", None)
        solve_fn = getattr(module, "solve", None)
        if not isinstance(meta, dict) or not callable(solve_fn):
            continue
        slug = str(meta.get("slug") or path.stem)
        normalized_meta = {
            "slug": slug,
            "name": meta.get("name", slug.replace("_", " ").title()),
            "category": meta.get("category", "General"),
            "renderer": meta.get("renderer", "grid"),
            "custom_view": meta.get("custom_view"),
            "description": meta.get("description", ""),
            "grid_meta": meta.get("grid_meta", {}),
            "presets": meta.get("presets", {}),
            "params": meta.get("params", []),
        }
        entries[slug] = SolverEntry(
            slug=slug,
            meta=normalized_meta,
            solve=solve_fn,
            module=module,
        )
    return entries


def list_solver_metadata(solvers_dir: Path = SOLVERS_DIR) -> List[Dict[str, Any]]:
    """Return sorted solver metadata dictionaries suitable for JSON API responses."""
    entries = discover_solvers(solvers_dir)
    return sorted(
        (entry.meta for entry in entries.values()),
        key=lambda m: (m["category"].lower(), m["name"].lower()),
    )
