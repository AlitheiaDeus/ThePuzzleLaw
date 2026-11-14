# The Puzzle Law v2 — Kanban Board

Project tracker for **The Puzzle Law** (`app/main.py` + `solvers/*.py` + `web/`).  
*(v1 PySide6 history is archived on branch `legacy/pyside6` / tag `v1-pyside6`.)*

```mermaid
%%{init: { "theme": "dark" }}%%
kanban
  backlog["Backlog / Ideas"]
    v2cv["Computer Vision Board Capture Input Adapter (OpenCV + OCR)"]@{ ticket: '[V2-01]', priority: 'Medium' }
    v2dlx["Polyomino / Pentomino DLX Exact Cover Solver"]@{ ticket: '[V2-02]', priority: 'Low' }
    v2hex["Hexagonal & Weighted Terrain Mode in Maze Navigator"]@{ ticket: '[V2-03]', priority: 'Low' }
  todo["Todo"]
  in_progress["In Progress"]
  done["Completed (v2 Core & Port)"]
    v2arch["Archive v1 PySide6 in Git & Flatten Repo to uv + FastAPI + HTML/JS"]@{ ticket: '[V2-CORE]', priority: 'High' }
    v2theme["Chalkboard & Midnight Plum Dual Theme System"]@{ ticket: '[V2-UI]', priority: 'Medium' }
    v2puzzles["Port 13 Hub Plugins + Block Escape + Superking + Cipher/Morse Tools"]@{ ticket: '[V2-PORT]', priority: 'High' }
```

## Notes
- **V2-01 (CV Board Capture):** Planned as a pure input adapter (`POST /api/import/image/{slug}`) returning a JSON state matching the target solver's preset schema.
- **V2-02 (DLX Tiling):** Extend `solvers/packing_grids.py` or add `solvers/polyomino_dlx.py` using the single-file solver contract.
