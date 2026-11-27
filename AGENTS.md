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
├── pyproject.toml           # uv dependencies (fastapi, uvicorn, numpy; dev: pytest, httpx)
├── kanban.md                # Project task board (keep tasks/bugs out of AGENTS.md)
├── app/
│   ├── main.py              # FastAPI endpoints & static web/ mount
│   ├── registry.py          # Auto-discovers solvers/*.py and normalizes META
│   └── runner.py            # Sync & SSE streaming execution with cooperative abort
├── solvers/                 # Pure-Python single-file solver modules (zero UI code)
│   ├── data/morse/          # Multilingual frequency dictionaries for morse_decoder.py
│   └── native/              # Optional compiled native accelerators (e.g. Rust binary)
├── web/
│   ├── index.html           # Permanent App Shell (Sidebar, Stage, Transport Bar, Logs)
│   ├── styles.css           # Chalkboard (chalk) & Midnight Plum (plum) CSS variables
│   ├── app.js               # Hub controller, SSE streaming, timeline scrubbing
│   └── renderers/
│       ├── grid.js          # Generic interactive 2D grid/board renderer
│       ├── text.js          # Generic text/cipher workbench & frequency bar chart
│       └── custom/          # Per-solver JS views (block_escape, hex_maze, liquid_tubes,
│                            #   loop_board, poly_loop_board, rubiks_cube)
└── tests/
    ├── test_registry.py     # Validates solver discovery, categories, and expected slugs
    ├── test_solvers.py      # Runs every preset of every solver + edge/abort cases
    └── test_api.py          # FastAPI endpoint & SSE streaming integration tests
```

---

## 3. Solver Contract (`solvers/<slug>.py`)

Every solver is a single pure-Python file in `solvers/` with **no web/UI imports**. It must expose:

1. **`META: dict`**:
   * `slug` (`str`), `name` (`str`)
   * `category` (`str`): must be one of:
     * `"Path"` — sequential move/path puzzles where move order matters (e.g. Sliding Tile, Block Escape, Peg Solitaire, Rubik's Cube, Maze Navigator)
     * `"State"` — static constraint-satisfaction / unordered assignment puzzles (e.g. Sudoku, Flip, Slitherlink, Unruly)
     * `"Cipher"` — text decoding / frequency analysis (e.g. Cipher Suite, Morse Decoder)
   * `renderer`: `"grid"` | `"text"` | `"custom"` (plus optional `custom_view` URL under `/renderers/custom/...`)
   * `description` (`str`)
   * `grid_meta` (`dict`, optional): hints for `web/renderers/grid.js`:
     * `mode`: `"number" | "binary" | "cycle" | "palette" | "token" | "permutation"`
     * `min_val`, `max_val`, `empty_val`, `labels`, `colors`, `editable`
     * Optional sizing/layout: `resizable` (`True` or `"square"`), `min_dim`, `max_dim`, `dim_step`, `size_layouts`, `zone_editable`
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

## 5. Adding a New Solver & Testing Rules

* **No hardcoded machine-specific absolute paths or PII** in tracked files.
* **All presets are tested**: `tests/test_solvers.py` (`ALL_PRESET_CASES`) automatically runs **every preset** of **every discovered solver** and asserts it starts with `"start"` and ends with `"solution"`. Ensure every preset in `META["presets"]` is mathematically solvable and fast enough for headless CI.
* **Registry expectation**: When adding a new solver in `solvers/`, add its `slug` to `expected` in `tests/test_registry.py`, and add targeted edge-case/unsolvable/abort tests in `tests/test_solvers.py`.
