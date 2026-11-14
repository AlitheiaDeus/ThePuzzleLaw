# The Puzzle Law (v2)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![uv](https://img.shields.io/badge/package%20manager-uv-DE5FE9.svg)](https://docs.astral.sh/uv/)
[![FastAPI](https://img.shields.io/badge/backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

> **Modular, local-first Puzzle & Cipher Solver Hub**  
> Python solver generators (`solvers/*.py`) served over a local FastAPI backend (`127.0.0.1:8000`) to a zero-build Vanilla HTML/CSS/JS workspace with Chalkboard & Midnight Plum themes.

*(The legacy PySide6 desktop app is preserved in Git under the `legacy/pyside6` branch and `v1-pyside6` tag.)*

---

## Quickstart

```bash
uv sync
uv run python -m app.main
```

This starts the local server on `http://127.0.0.1:8000` and opens it in your default browser.

- Run headless tests:
  ```bash
  uv run pytest
  ```
- Start server without auto-opening a browser tab:
  ```bash
  uv run python -m app.main --no-browser --port 8000
  ```

---

## Architecture

```text
ThePuzzleLaw/
├── pyproject.toml           # uv project & dependency manifest
├── app/
│   ├── main.py              # FastAPI server, static mount, SSE solve streaming
│   ├── registry.py          # Auto-discovers solvers/*.py and reads META
│   └── runner.py            # Generator runner with cooperative abort & step caps
├── solvers/                 # Single-file pure-Python solver modules
│   ├── block_escape.py      # Multi-tile sliding blocks, ice, portals, lockstep chains
│   ├── chess_attack.py      # Zoned N-Queens & N-Superking (Rook + King)
│   ├── cipher_suite.py      # Caesar/ROT, Atbash, Reverse, Vigenere, Base64/Hex/Bin, Freq
│   ├── flip.py              # Lights Out GF(2) Gaussian elimination
│   ├── flood.py             # Flood-It component contraction + IDA*
│   ├── flow.py              # Numberlink & Checkpoint Saturation Flow
│   ├── liquid_sorter.py     # Variable-capacity A* pouring solver
│   ├── loop_games.py        # Slitherlink single-loop solver
│   ├── maze_navigator.py    # 2D obstacle maze A* / BFS
│   ├── morse_decoder.py     # Spaced & unspaced/smooshed Morse Trie beam search
│   ├── packing_grids.py     # Nonogram (Picross) line intersection + backtracking
│   ├── sliding_tile.py      # N-Puzzle (8/15-puzzle) A* Manhattan solver
│   ├── sudoku.py            # Hybrid Naked/Hidden Singles + MRV backtracking
│   ├── unruly.py            # Binary grid parity & no-3-in-a-row CSP
│   ├── urjo.py              # Binary grid with Moore clues & adjacent line disparity
│   └── data/morse/          # Multilingual wordlists for smooshed Morse decoding
├── web/
│   ├── index.html           # Permanent Hub Shell (Sidebar, Stage, Transport, Logs)
│   ├── styles.css           # Chalkboard & Midnight Plum themes
│   ├── app.js               # SSE client, Edit/Playback state, timeline scrubber
│   └── renderers/
│       ├── grid.js          # Generic interactive 2D grid/board renderer
│       ├── text.js          # Cipher & signal workbench + frequency bar chart
│       └── custom/          # Specialized SVG/HTML views (liquid_tubes.js, loop_board.js)
└── tests/
    ├── test_registry.py     # Solver autodiscovery & META schema validation
    ├── test_solvers.py      # Default preset solve & cooperative abort tests
    └── test_api.py          # FastAPI endpoints & SSE stream smoke tests
```

---

## Adding a New Solver

Drop a single `.py` file into `solvers/` exporting `META` and `solve(state, params, should_abort)`:

```python
META = {
    "slug": "my_puzzle",
    "name": "My Puzzle",
    "category": "2D Grid",
    "renderer": "grid",  # "grid" | "text" | "custom"
    "description": "Short description.",
    "grid_meta": {"mode": "number", "editable": True},
    "presets": {"Default": {"board": [[0, 0], [0, 0]]}},
    "params": [],
}

def solve(state, params, should_abort):
    yield {"type": "start", "state": state, "highlights": {}, "desc": "Loaded", "stats": {}}
    if should_abort():
        return
    # ... compute steps ...
    yield {"type": "solution", "state": solved_state, "highlights": {}, "desc": "Solved!", "stats": {}}
```

`app/registry.py` discovers it automatically on startup—no config file registration required.
