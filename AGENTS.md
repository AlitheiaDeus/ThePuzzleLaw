# AGENTS.md — Developer & Agent Guide for The Puzzle Law (v2)

**The Puzzle Law** is a local-first, modular puzzle and cipher solver hub built with **Python + FastAPI** on the backend and **Vanilla HTML/CSS/JS** on the frontend, managed via **`uv`**.

*(The legacy PySide6 desktop app is archived in Git on branch `legacy/pyside6` and tag `v1-pyside6`. Do not reintroduce Qt/`QPainter` dependencies.)*

---

## 1. Environment & Commands

* **Package Manager**: `uv` (Python 3.10+, dependencies defined in `pyproject.toml`).
* **Install / Sync**:
  ```bash
  uv sync
  ```
* **Run Application** (launches local server at `http://127.0.0.1:8000`):
  ```bash
  uv run python -m app.main
  ```
* **Run Headless Tests** (must pass with exit code `0` before any change is complete):
  ```bash
  uv run pytest
  ```

---

## 2. Repository Topology

```text
ThePuzzleLaw/
├── pyproject.toml           # uv dependencies (fastapi, uvicorn, numpy, pytest, httpx)
├── app/
│   ├── main.py              # FastAPI endpoints & static web/ mount
│   ├── registry.py          # Auto-discovers solvers/*.py and normalizes META
│   └── runner.py            # Sync & SSE streaming execution with cooperative abort
├── solvers/                 # Pure-Python single-file solver modules (zero UI code)
│   └── data/morse/          # Multilingual frequency dictionaries for morse_decoder.py
├── web/
│   ├── index.html           # Permanent App Shell (Sidebar, Stage, Transport Bar, Logs)
│   ├── styles.css           # Chalkboard (chalk) & Midnight Plum (plum) CSS variables
│   ├── app.js               # Hub controller, SSE streaming, timeline scrubbing
│   └── renderers/
│       ├── grid.js          # Generic interactive 2D grid/board renderer
│       ├── text.js          # Generic text/cipher workbench & frequency bar chart
│       └── custom/          # Optional per-solver JS views (liquid_tubes.js, loop_board.js)
└── tests/                   # Automated pytest suites
```

---

## 3. Solver Contract (`solvers/<slug>.py`)

Every solver is a single pure-Python file in `solvers/` with **no web/UI imports**. It must expose:

1. **`META: dict`**:
   * `slug` (`str`), `name` (`str`), `category` (`str`)
   * `renderer`: `"grid"` | `"text"` | `"custom"` (plus optional `custom_view` URL under `/renderers/custom/...`)
   * `description` (`str`)
   * `grid_meta` (`dict`, optional): hints for `web/renderers/grid.js` (`mode`: `"number" | "binary" | "cycle" | "palette" | "token"`, `min_val`, `max_val`, `labels`, `colors`, `editable`)
   * `presets` (`dict[str, dict]`): at least 1 valid, solvable JSON-serializable initial state
   * `params` (`list[dict]`): optional parameter definitions (`select`, `bool`, `text`)

2. **`solve(state: dict, params: dict, should_abort: Callable[[], bool]) -> Generator[dict, None, None]`**:
   * Yield plain JSON-serializable step dicts:
     ```python
     {
         "type": "start" | "deduce" | "explore" | "backtrack" | "solution" | "failed",
         "state": { ... },
         "highlights": { ... },
         "desc": "Human-readable step description",
         "stats": { ... },
     }
     ```
   * **First yielded step** must have `"type": "start"`.
   * **Cooperative Cancellation**: Check `should_abort()` inside loops/recursions and return cleanly when `True`.
   * **Completion**: End with `"type": "solution"` on success or `"type": "failed"` if unsolvable.

---

## 4. Frontend Conventions (`web/`)

* **Never replace the whole HTML page** when switching puzzles. `web/index.html` is the permanent App Shell; switching puzzles swaps only `<div id="stage">`.
* **Theme Tokens**: Use CSS variables from `web/styles.css` (`--bg-main`, `--bg-panel`, `--accent-primary`, `--accent-secondary`, `--accent-hot`, etc.) so both **Chalkboard** and **Midnight Plum** themes work automatically.
* **Edit vs. Playback Mode**: Clicking a preset or editing the board clears any active playback trajectory and returns to `EDIT MODE`.

---

## 5. Portability & Testing Rules

* Never hardcode machine-specific absolute paths or PII in tracked files.
* Any new solver added to `solvers/` is automatically tested by `tests/test_registry.py` and `tests/test_solvers.py` on its first preset—ensure every default preset is mathematically solvable.
