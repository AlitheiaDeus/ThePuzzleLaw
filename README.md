# The Puzzle Law (`solvertools-hub`)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-3776AB.svg?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![GUI Framework](https://img.shields.io/badge/GUI-PySide6%20(Qt%206)-41CD52.svg?style=flat&logo=qt&logoColor=white)](https://pypi.org/project/PySide6/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Status](https://img.shields.io/badge/architecture-modular%20plugin%20hub-00F5D4.svg)](#architecture)

> **High-Performance Modular Puzzle Solver & Interactive Visualizer Suite**  
> Built with Python & PySide6, featuring a chalkboard-neon visual aesthetic, asynchronous generator-driven solver execution, and interactive step scrubbing.

---

## Overview

**The Puzzle Law** is an extensible desktop application designed to solve, transcribe, and visually step through combinatorial and constraint-satisfaction puzzles. 

Rather than isolated command-line scripts, it provides a unified hub where each puzzle operates as an independent plugin adhering to strict architectural contracts: **PuzzleState**, **Generator Solver**, and **Interactive Canvas**.

```
┌───────────────────────────────────────────────────────────────┐
│                      The Puzzle Law Hub                       │
├─────────────────┬─────────────────────────────────────────────┤
│  Sidebar        │  Active Puzzle Viewport (QPainter Canvas)   │
│  - Sliding Tile │  - Interactive Board / Grid Transcription   │
│  - Liquid Sort  │  - Real-time Glow & Move Highlights         │
│  - Sudoku       ├─────────────────────────────────────────────┤
│  - Flip         │  Transport Bar & Timeline Scrubbing         │
│  - Unruly       │  [⏮] [◀] [▶ Play] [▶| Step] [⏭] [⚡ Solve]  │
│  - (More...)    ├─────────────────────────────────────────────┤
│                 │  Collapsible Log Drawer & Metrics           │
└─────────────────┴─────────────────────────────────────────────┘
```

---

## Key Features

- **Decoupled Plugin Architecture**: Add new puzzles by dropping a folder into `solvertools_hub/plugins/` without modifying core navigation, theme, or playback systems.
- **Generator-Driven Solvers**: All solvers yield `SolverStep` objects as Python generators (`yield SolverStep`), enabling:
  - **Playback Mode**: Smooth tick-based animation with forward/backward timeline scrubbing.
  - **Instant Solve**: Fast headless execution returning the optimal solution trajectory and performance metrics.
- **Responsive Background Execution**: Solvers run on dedicated `QThread` workers with cooperative cancellation (`abort`) to keep the UI silky smooth at 60 FPS.
- **Interactive Transcription**: Canvas widgets feature an **Edit Mode** (paint, click, type, or configure custom start states) and a **Playback Mode** (locked visualization).
- **"Chalkboard & Neon Pastel" Design System**: Custom Qt Style Sheets (QSS) paired with multi-pass glow rendering in `QPainter` for high-contrast visual clarity.
- **Import / Export**: Full clipboard and JSON serialization for saving puzzle states or pasting external layouts.

---

## Built-in Puzzle Solvers

| Puzzle | Algorithm / Engine | Description |
| :--- | :--- | :--- |
| **Sliding Tile (N-Puzzle)** | $A^*$ Search + Manhattan / Linear Conflict | Finds optimal sliding tile trajectories ($3\times3$, $4\times4$, etc.) with solvability parity validation. |
| **Liquid Sorter Pro** | $A^*$ Search + Canonical Pruning | Solves multi-colored test tube / sand sorting with cycle detection and dead-end pruning. |
| **Sudoku** | Constraint Satisfaction (CSP) + Backtracking | Solves standard $9\times9$ grid constraints with real-time cell conflicts and naked single propagation. |
| **Flip (Lights Out)** | Linear Algebra over $\mathbb{F}_2$ (GF(2)) | Uses Gaussian elimination to calculate exact toggle patterns for matrix light grids. |
| **Unruly** | Binary Constraint Satisfaction | Solves binary grid puzzles with strict row/column parity and no-three-in-a-row rules. |
| **Urjo** | Constraint Satisfaction + Neighborhood Propagation | Solves dual-color grid puzzles with Moore neighborhood numerical clues, line parity, and adjacent line disparity. |

*Additional solvers currently in development / integration: Flow Free, Chess Attack, ASCII/Morse, and Superking.*

---

## Architecture & Directory Topology

```
The_Puzzle_Law/
├── solvertools_hub/
│   ├── main.py                  # Entry point, QSS injection, dynamic autodiscovery
│   ├── plugins_config.json      # Plugin activation & curtain filter configuration
│   ├── theme.py                 # Chalkboard & Neon color tokens + global styling
│   ├── core/
│   │   ├── base_plugin.py       # Contracts: BasePuzzleState, BaseSolver, BasePuzzleCanvas
│   │   ├── registry.py          # Dynamic plugin discovery and config-driven filtering
│   │   ├── worker.py            # QThread asynchronous solver runner
│   │   └── io_manager.py        # JSON & clipboard serialization utilities
│   ├── ui/
│   │   ├── hub_window.py        # Main application window (Sidebar + Stacked Viewport)
│   │   ├── transport_bar.py     # Unified playback controls & scrub slider
│   │   └── log_drawer.py        # Real-time search trace and heuristic logger
│   └── plugins/                 # Modular puzzle implementations
│       ├── sliding_tile/        # [Active] 15-puzzle / NxN sliding tile
│       ├── sand_tubes/          # [Active] Liquid Sorter Pro
│       ├── sudoku/              # [Active] 9x9 Constraint Grid
│       ├── flip/                # [Active] Lights Out GF(2) solver
│       ├── unruly/              # [Active] Binary puzzle parity & run-length
│       ├── urjo/                # [Active] Binary grid with Moore neighborhood clues
│       ├── chess_attack/        # [Curtain / Draft] Tactical zoned chess pieces
│       ├── cipher_room/         # [Curtain / Draft] Smooshed Morse & classical cryptanalysis
│       ├── flow/                # [Curtain / Draft] Topological path saturation router
│       ├── maze_navigator/      # [Curtain / Draft] 2D grid, hex, & Euclidean navigators
│       ├── loop_games/          # [Curtain / Draft] Slitherlink, Palisade, Pearl loops
│       └── packing_grids/       # [Curtain / Draft] Nonograms & Knuth DLX polyominoes
├── tests/                       # Automated test suites (core, plugins, UI launch)
├── Snippets To Integrate/       # Staging area for upcoming puzzle algorithms
├── Prebuild_Blueprint.md        # Complete architectural blueprint and technical spec
├── Waypoint_Implementation_Plan.md # Milestone tracker
└── environment_pylearn.yml      # Conda environment definition
```

---

## Quickstart

### 1. Prerequisites
- Python 3.10 or higher
- Conda or virtual environment (recommended)

### 2. Environment Setup

Using the provided conda environment:
```powershell
conda env create -f environment_pylearn.yml
conda activate pylearn
```

Or install the dependencies via `pip`:
```powershell
pip install PySide6 loguru pyperclip numpy pytest
```

### 3. Launching the Hub

From the root of the repository:
```powershell
python -m solvertools_hub.main
```
*(or run directly: `python solvertools_hub/main.py`)*

---

## Running Tests

Test suites verify plugin contracts, state transitions, solvers, and UI initialization:

```powershell
# Run the complete test suite
pytest tests/ -v
```

---

## Developer Guide: Adding a Puzzle Plugin

To create a new puzzle plugin, add a new directory under `solvertools_hub/plugins/<your_puzzle>/` implementing the core contracts:

1. **`state.py`**: Inherit from `BasePuzzleState`. Implement `clone()`, `validate()`, `serialize()`, and `deserialize()`.
2. **`solver.py`**: Inherit from `BaseSolver`. Implement `solve(initial_state, stream_search=False)` yielding `SolverStep` instances.
3. **`canvas.py`**: Inherit from `BasePuzzleCanvas`. Handle user interaction (`mousePressEvent`, `keyPressEvent`) and paint the board in `paintEvent`.
4. **`plugin.py`**: Inherit from `BasePlugin` to bundle metadata, state, solver, and canvas.

Register your plugin in `solvertools_hub/plugins/__init__.py` and the Hub will automatically load it with full playback and transcription support!

---

## License

This project is licensed under the [MIT License](LICENSE).
