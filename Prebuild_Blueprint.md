# **Architectural Reference: Modular Puzzle Solver Suite (solvertools-ui)**

This reference blueprint outlines a unified, plugin-oriented desktop application built on **PySide6 (6.10.1)**, utilizing standard library tools and lightweight helper packages (loguru, pyperclip, numpy) already installed in your pylearn environment.  
The architecture separates **State**, **Solver Logic**, and **Interactive Rendering**. Adding a new puzzle type requires dropping a single folder or module into plugins/ without touching the main window, navigation bar, playback engine, or theme files.

## **1\. Directory & Module Topology**

Plaintext  
solvertools\_hub/  
├── main.py                      \# Application entry point, QSS injection, global exception hook  
├── theme.py                     \# Chalkboard & Pastel-Neon color tokens \+ QSS generator  
├── core/  
│   ├── \_\_init\_\_.py  
│   ├── base\_plugin.py           \# Abstract interfaces: BaseState, BaseSolver, BasePuzzleWidget  
│   ├── registry.py              \# Auto-discovery and registration of puzzle plugins  
│   ├── worker.py                \# QThread \+ QTimer dual-mode execution engine (Playback vs Instant)  
│   └── io\_manager.py            \# Clipboard (pyperclip) and JSON state import/export handlers  
├── ui/  
│   ├── \_\_init\_\_.py  
│   ├── hub\_window.py            \# Main QMainWindow: Sidebar \+ QStackedWidget \+ Transport Bar  
│   ├── transport\_bar.py         \# Unified Play/Pause, Step, Speed Slider, and Instant Solve UI  
│   └── log\_drawer.py            \# Collapsible step/heuristic trace console  
└── plugins/                     \# Drop-in puzzle modules  
    ├── \_\_init\_\_.py  
    ├── sliding\_tile/            \# Example 1: 2D Grid \+ A\* Search (Order-dependent playback)  
    │   ├── plugin.py  
    │   ├── solver.py  
    │   └── canvas.py  
    ├── sand\_tubes/              \# Example 2: Custom Vector Containers \+ DFS/BFS  
    │   └── ...  
    └── sudoku\_grid/             \# Example 3: Text/Constraint Grid (Instant state solve)  
        └── ...

## **2\. Aesthetic & Theme Specification: "Chalkboard & Neon Pastel"**

Rather than styling individual widgets inside puzzle plugins, the hub enforces a global Qt Style Sheet (QSS) alongside a shared Palette dictionary for custom QPainter canvases.

### **Color Token Matrix**

| Role | Token Name | Hex Code | Visual Description & Usage |
| :---- | :---- | :---- | :---- |
| **Canvas Base** | BG\_CHALK\_BLACK | \#0F1412 | Deep obsidian-tinted chalkboard black for main viewport background |
| **Panel Surface** | BG\_SLATE\_GREEN | \#16211D | Very dark forest chalkboard green for sidebars, cards, and headers |
| **Control Surface** | BG\_BOARD\_RAISED | \#1E2D27 | Subtle elevated surface for interactive buttons, inputs, and cells |
| **Grid / Chalk Line** | FG\_CHALK\_DUST | \#3A4D45 | Muted dusty green-grey for grid borders, dividers, and empty slots |
| **Primary Text** | FG\_CHALK\_WHITE | \#EAE6DF | Warm, slightly off-white chalk tone for crisp readability |
| **Secondary Text** | FG\_CHALK\_MUTED | \#96A8A0 | Faded sage chalk for metadata, coordinates, and step counters |
| **Pastel Structural 1** | PASTEL\_MINT | \#A8E6CF | Soft pastel green for default tiles, valid tokens, or static walls |
| **Pastel Structural 2** | PASTEL\_LAVENDER | \#D7BDE2 | Soft pastel purple for secondary piece groups or tube liquids |
| **Pastel Structural 3** | PASTEL\_PEACH | \#FAD7A0 | Warm pastel amber for tertiary puzzle elements |
| **Pastel Structural 4** | PASTEL\_SKY | \#A9CCE3 | Soft pastel blue for start nodes or player tokens |
| **Neon Emphasis (Active)** | NEON\_CYAN | \#00F5D4 | Glowing electric cyan for active cursor, current search head, or selected item |
| **Neon Emphasis (Path)** | NEON\_LIME | \#B5FF4D | High-visibility neon chartreuse for solved path highlights and goal states |
| **Neon Emphasis (Alert)** | NEON\_CORAL | \#FF4D80 | Vibrant neon pink/coral for invalid transcriptions, dead ends, or conflicts |

### **Glow & Chalk Rendering Tricks in QPainter**

When drawing custom puzzle boards (like sand tubes or mazes) on a QWidget, you can achieve a glowing neon effect without heavy shaders by layering two strokes in QPainter:

> 1. **Outer Glow Pass:** Draw the path/border with QPen(QColor(0, 245, 212, 55), width=8, Qt.SolidLine, Qt.RoundCap).  
> 2. **Core Neon Pass:** Draw the exact same geometry over top with QPen(QColor("\#00F5D4"), width=2).

## **3\. Core Architecture & The Plugin Contract**

Every puzzle has vastly different geometry (grids, graphs, tubes, freeform polygons) and input habits (typing numbers, dragging tiles, clicking walls). To keep them unified, the hub only cares about **four abstract contracts**.

### **3.1 PuzzleState (Immutable or Cloneable Snapshot)**

Represents a single configuration of the puzzle at any moment in time.

* **serialize() \-\> str**: Dumps the state to a compact JSON or raw text string for clipboard copying or saving.  
* **deserialize(raw\_str: str) \-\> PuzzleState**: Parses an exported string from an external game or clipboard into a valid internal state.  
* **validate() \-\> tuple\[bool, str\]**: Checks if your manual 1:1 transcription is solvable/legal before the solver runs (e.g., checking if a transcribed Sand Tube puzzle has 4 segments of every color, or if a Sliding Tile board has an even inversion count).

### **3.2 SolverStep (Standardized Yield Payload)**

Whether a solver uses A\*, BFS, Backtracking, or Simulated Annealing, it yields SolverStep objects:

* state: The updated PuzzleState.  
* action\_desc: Human-readable string (e.g., "Pour Tube 3 \-\> Tube 1", "Move Tile 7 Down").  
* highlights: A dictionary/list of coordinates or entity IDs to light up in NEON\_CYAN or NEON\_LIME on the canvas.  
* metrics: Optional dict ({"depth": 14, "heuristic": 6, "visited": 420}).

### **3.3 BaseSolver (Generator-Driven Algorithm)**

Instead of writing separate code for "Playback Mode" and "Instant Mode", every solver is written as a **Python Generator** (yield SolverStep).

* **Why a Generator?**  
  * In **Playback Mode**, the execution engine calls next(generator) on a QTimer tick (or buffers all steps into a timeline array so you can scrub backward and forward with a slider).  
  * In **Instant Mode**, the background worker runs a tight loop consuming the generator at full CPython speed, discards intermediate UI updates, and emits only the final SolverStep and summary statistics.

### **3.4 BasePuzzleCanvas (Interactive Transcription \+ Renderer)**

Inherits from QWidget (or QGraphicsView for zoomable/pannable puzzles). It operates in two distinct modes toggled by the hub:

* **InteractionMode.EDIT (Default Transcription Mode):**  
  * Mouse clicks, drags, scroll wheels, and keyboard presses directly mutate the starting PuzzleState.  
  * Includes a puzzle-specific **Quick-Palette Bar** (e.g., color swatches for Sand Tubes, Wall/Start/End brushes for Mazes, or dimension spinners Rows x Cols).  
* **InteractionMode.PLAYBACK (Locked Solver Mode):**  
  * Locks manual editing so accidental clicks don't break a running trace.  
  * Renders SolverStep.state and overlays SolverStep.highlights using the neon emphasis colors.

## **4\. Dual-Mode Execution & Timeline Buffering Flow**

\[ Manual Canvas Edit / Paste \]  
              │  
              ▼  
    ┌───────────────────┐  
    │PuzzleState.validate│ ──(Invalid)──► Highlight error in NEON\_CORAL  
    └─────────┬─────────┘  
              │ (Valid)  
              ▼  
    ┌───────────────────────────────────────────────────┐  
    │          SolverWorker (QThread)                   │  
    │ Runs BaseSolver.solve\_generator(initial\_state)    │  
    └─────────┬───────────────────────────────┬─────────┘  
              │                               │  
     \[Mode: PLAYBACK\]                 \[Mode: INSTANT\]  
              │                               │  
              ▼                               ▼  
   Append steps to History         Consume generator to end;  
   List\[SolverStep\] & emit         emit only final SolverStep  
   to QTimer Playback Controller   \+ total elapsed time/steps  
              │                               │  
              └───────────────┬───────────────┘  
                              ▼  
             \[ BasePuzzleCanvas.render\_step() \]

**Why Timeline Buffering beats live sleep() inside threads:**  
Most puzzle solvers finish in 5ms to 2000ms in Python, even when exploring thousands of nodes. By running the generator in a QThread and collecting the solution path into a list\[SolverStep\], you get an instant **Timeline Scrubber**:

* Play forward at 1x, 2x, 10x human speed (500ms down to 20ms per step).  
* Step **backward** (\< Prev) and **forward** (Next \>) one move at a time when following along on a second screen or phone game.  
* If a search algorithm is genuinely massive and you want to watch the live search tree explore dead ends, a checkbox (Stream Raw Search Tree) yields every visited node directly to the UI thread with a throttled semaphore.

## **5\. Complete Reference Implementation Blueprint**

Below is the complete, runnable single-file reference foundation (solver\_hub\_prototype.py). It implements the **Chalkboard & Pastel-Neon theme**, the **Sidebar Hub**, the **Dual-Mode Playback/Scrubber Engine**, **Clipboard State I/O**, and **two distinct working puzzle plugins** (an interactive **Sliding Tile A\* Solver** and an interactive **Sand Tube Pouring Solver**) so you can see how two completely different board geometries share the same hub.

Python  
import sys  
import json  
import time  
import heapq  
from abc import ABC, abstractmethod  
from dataclasses import dataclass, field  
from enum import Enum, auto  
from typing import Any, Dict, Generator, List, Optional, Tuple

import pyperclip  
from loguru import logger  
from PySide6.QtCore import Qt, QThread, QTimer, Signal, QRectF, QPointF  
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QBrush, QKeyEvent, QMouseEvent, QPainterPath  
from PySide6.QtWidgets import (  
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,  
    QListWidget, QListWidgetItem, QStackedWidget, QPushButton,  
    QLabel, QSlider, QSplitter, QTextEdit, QComboBox, QSpinBox,  
    QFrame, QMessageBox, QCheckBox  
)

\# \=====================================================================  
\# 1\. THEME & COLOR PALETTE SPECIFICATION (Chalkboard \+ Pastel/Neon)  
\# \=====================================================================

class ChalkTheme:  
    \# Surfaces  
    BG\_CHALK\_BLACK \= "\#0F1412"  
    BG\_SLATE\_GREEN \= "\#16211D"  
    BG\_BOARD\_RAISED \= "\#1E2D27"  
    FG\_CHALK\_DUST \= "\#3A4D45"

    \# Typography  
    FG\_CHALK\_WHITE \= "\#EAE6DF"  
    FG\_CHALK\_MUTED \= "\#96A8A0"

    \# Pastels (Puzzle Structural Elements)  
    PASTEL\_MINT \= "\#A8E6CF"  
    PASTEL\_LAVENDER \= "\#D7BDE2"  
    PASTEL\_PEACH \= "\#FAD7A0"  
    PASTEL\_SKY \= "\#A9CCE3"  
    PASTEL\_ROSE \= "\#F5B7B1"  
    PASTEL\_LEMON \= "\#F9E79F"

    PASTEL\_PALETTE \= \[  
        PASTEL\_MINT, PASTEL\_LAVENDER, PASTEL\_PEACH,  
        PASTEL\_SKY, PASTEL\_ROSE, PASTEL\_LEMON  
    \]

    \# Neons (Emphasis, Active States, Solved Paths, Errors)  
    NEON\_CYAN \= "\#00F5D4"  
    NEON\_LIME \= "\#B5FF4D"  
    NEON\_CORAL \= "\#FF4D80"  
    NEON\_AMBER \= "\#FFB800"

    @classmethod  
    def get\_stylesheet(cls) \-\> str:  
        return f"""  
        QMainWindow, QWidget {{  
            background-color: {cls.BG\_CHALK\_BLACK};  
            color: {cls.FG\_CHALK\_WHITE};  
            font-family: "Consolas", "Source Code Pro", "Segoe UI", monospace;  
            font-size: 13px;  
        }}  
        QFrame\#PanelFrame {{  
            background-color: {cls.BG\_SLATE\_GREEN};  
            border: 1px solid {cls.FG\_CHALK\_DUST};  
            border-radius: 6px;  
        }}  
        QListWidget {{  
            background-color: {cls.BG\_SLATE\_GREEN};  
            border: 1px solid {cls.FG\_CHALK\_DUST};  
            border-radius: 6px;  
            padding: 4px;  
            outline: none;  
        }}  
        QListWidget::item {{  
            padding: 10px 12px;  
            border-radius: 4px;  
            color: {cls.FG\_CHALK\_MUTED};  
            margin-bottom: 2px;  
        }}  
        QListWidget::item:hover {{  
            background-color: {cls.BG\_BOARD\_RAISED};  
            color: {cls.FG\_CHALK\_WHITE};  
        }}  
        QListWidget::item:selected {{  
            background-color: {cls.BG\_BOARD\_RAISED};  
            color: {cls.NEON\_CYAN};  
            border-left: 3px solid {cls.NEON\_CYAN};  
            font-weight: bold;  
        }}  
        QPushButton {{  
            background-color: {cls.BG\_BOARD\_RAISED};  
            color: {cls.FG\_CHALK\_WHITE};  
            border: 1px solid {cls.FG\_CHALK\_DUST};  
            border-radius: 4px;  
            padding: 6px 12px;  
            font-weight: bold;  
        }}  
        QPushButton:hover {{  
            border: 1px solid {cls.PASTEL\_MINT};  
            color: {cls.PASTEL\_MINT};  
        }}  
        QPushButton:pressed {{  
            background-color: {cls.FG\_CHALK\_DUST};  
        }}  
        QPushButton\#NeonActionBtn {{  
            border: 1px solid {cls.NEON\_CYAN};  
            color: {cls.NEON\_CYAN};  
        }}  
        QPushButton\#NeonActionBtn:hover {{  
            background-color: \#003B33;  
        }}  
        QPushButton\#InstantActionBtn {{  
            border: 1px solid {cls.NEON\_LIME};  
            color: {cls.NEON\_LIME};  
        }}  
        QPushButton\#InstantActionBtn:hover {{  
            background-color: \#263812;  
        }}  
        QTextEdit {{  
            background-color: {cls.BG\_SLATE\_GREEN};  
            border: 1px solid {cls.FG\_CHALK\_DUST};  
            border-radius: 4px;  
            color: {cls.FG\_CHALK\_WHITE};  
            padding: 6px;  
        }}  
        QSlider::groove:horizontal {{  
            height: 6px;  
            background: {cls.BG\_BOARD\_RAISED};  
            border-radius: 3px;  
        }}  
        QSlider::sub-page:horizontal {{  
            background: {cls.PASTEL\_MINT};  
            border-radius: 3px;  
        }}  
        QSlider::handle:horizontal {{  
            background: {cls.NEON\_CYAN};  
            width: 14px;  
            margin-top: \-4px;  
            margin-bottom: \-4px;  
            border-radius: 7px;  
        }}  
        QSpinBox, QComboBox {{  
            background-color: {cls.BG\_BOARD\_RAISED};  
            border: 1px solid {cls.FG\_CHALK\_DUST};  
            border-radius: 4px;  
            padding: 4px 8px;  
            color: {cls.FG\_CHALK\_WHITE};  
        }}  
        """

    @staticmethod  
    def draw\_neon\_rect(painter: QPainter, rect: QRectF, hex\_color: str, radius: float \= 6.0, glow\_width: int \= 6):  
        """Helper to render a soft neon glow border around a QRectF."""  
        base\_color \= QColor(hex\_color)  
        glow\_color \= QColor(base\_color.red(), base\_color.green(), base\_color.blue(), 60)

        painter.save()  
        \# Outer Glow  
        painter.setPen(QPen(glow\_color, glow\_width, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))  
        painter.setBrush(Qt.NoBrush)  
        painter.drawRoundedRect(rect, radius, radius)  
        \# Inner Crisp Core  
        painter.setPen(QPen(base\_color, 2.0, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))  
        painter.drawRoundedRect(rect, radius, radius)  
        painter.restore()

\# \=====================================================================  
\# 2\. CORE PLUGIN CONTRACTS (State, Step, Solver, Canvas, Plugin)  
\# \=====================================================================

class InteractionMode(Enum):  
    EDIT \= auto()      \# User is manually transcribing / setting up the puzzle  
    PLAYBACK \= auto()  \# Solver trace is active; canvas is locked from accidental edits

class BasePuzzleState(ABC):  
    """Abstract representation of a puzzle's state at a single point in time."""

    @abstractmethod  
    def clone(self) \-\> "BasePuzzleState":  
        pass

    @abstractmethod  
    def serialize(self) \-\> str:  
        """Export state to JSON string for clipboard/file persistence."""  
        pass

    @classmethod  
    @abstractmethod  
    def deserialize(cls, raw\_data: str) \-\> "BasePuzzleState":  
        """Load state from JSON or external string format."""  
        pass

    @abstractmethod  
    def validate(self) \-\> Tuple\[bool, str\]:  
        """Verify if the manually transcribed state is legal before solving."""  
        pass

@dataclass  
class SolverStep:  
    """Standardized yield item from any puzzle solver."""  
    state: BasePuzzleState  
    action\_desc: str \= "Initial State"  
    highlights: Dict\[str, Any\] \= field(default\_factory=dict)  
    metrics: Dict\[str, Any\] \= field(default\_factory=dict)

class BaseSolver(ABC):  
    """Generator-based solver contract supporting both step-by-step and instant execution."""

    @abstractmethod  
    def solve(self, initial\_state: BasePuzzleState, stream\_search: bool \= False) \-\> Generator\[SolverStep, None, None\]:  
        """  
        Yields SolverStep objects.  
        If stream\_search is False, yields only the final winning path steps in sequence.  
        If stream\_search is True, yields intermediate exploratory steps as they are evaluated.  
        """  
        pass

class BasePuzzleCanvas(QWidget):  
    """Base interactive viewport for rendering and manual transcription."""  
    state\_modified \= Signal()

    def \_\_init\_\_(self, parent: Optional\[QWidget\] \= None):  
        super().\_\_init\_\_(parent)  
        self.mode \= InteractionMode.EDIT  
        self.current\_step: Optional\[SolverStep\] \= None  
        self.setMinimumSize(480, 420)  
        self.setFocusPolicy(Qt.StrongFocus)

    def set\_step(self, step: SolverStep):  
        self.current\_step \= step  
        self.update()

    def set\_mode(self, mode: InteractionMode):  
        self.mode \= mode  
        self.update()

class BasePuzzlePlugin(ABC):  
    """Top-level descriptor registered in the Hub."""  
    name: str \= "Unnamed Puzzle"  
    category: str \= "General"  
    description: str \= ""

    @abstractmethod  
    def create\_default\_state(self) \-\> BasePuzzleState:  
        pass

    @abstractmethod  
    def create\_solver(self) \-\> BaseSolver:  
        pass

    @abstractmethod  
    def create\_canvas(self, initial\_state: BasePuzzleState) \-\> BasePuzzleCanvas:  
        pass

    def create\_tool\_strip(self, canvas: BasePuzzleCanvas) \-\> Optional\[QWidget\]:  
        """Optional puzzle-specific toolbar for transcription (e.g., grid size, color picker)."""  
        return None

\# \=====================================================================  
\# 3\. BACKGROUND EXECUTION ENGINE (QThread Worker)  
\# \=====================================================================

class SolverWorker(QThread):  
    """Executes the solver generator in a background thread to keep UI responsive."""  
    finished\_timeline \= Signal(list, float)  \# Emits (List\[SolverStep\], elapsed\_sec)  
    finished\_instant \= Signal(object, int, float)  \# Emits (Final SolverStep, total\_steps, elapsed\_sec)  
    failed \= Signal(str)

    def \_\_init\_\_(  
        self,  
        solver: BaseSolver,  
        initial\_state: BasePuzzleState,  
        instant\_mode: bool \= False,  
        stream\_search: bool \= False  
    ):  
        super().\_\_init\_\_()  
        self.solver \= solver  
        self.initial\_state \= initial\_state.clone()  
        self.instant\_mode \= instant\_mode  
        self.stream\_search \= stream\_search  
        self.\_abort \= False

    def abort(self):  
        self.\_abort \= True

    def run(self):  
        start\_time \= time.perf\_counter()  
        try:  
            gen \= self.solver.solve(self.initial\_state, stream\_search=self.stream\_search)  
            if self.instant\_mode:  
                last\_step \= None  
                count \= 0  
                for step in gen:  
                    if self.\_abort:  
                        return  
                    last\_step \= step  
                    count \+= 1  
                elapsed \= time.perf\_counter() \- start\_time  
                if last\_step is None:  
                    self.failed.emit("Solver exhausted search space without finding a valid solution.")  
                else:  
                    self.finished\_instant.emit(last\_step, count, elapsed)  
            else:  
                timeline: List\[SolverStep\] \= \[\]  
                for step in gen:  
                    if self.\_abort:  
                        return  
                    timeline.append(step)  
                elapsed \= time.perf\_counter() \- start\_time  
                if not timeline:  
                    self.failed.emit("Solver exhausted search space without finding a valid solution.")  
                else:  
                    self.finished\_timeline.emit(timeline, elapsed)  
        except Exception as exc:  
            logger.exception("Solver execution failed")  
            self.failed.emit(f"Solver Exception: {exc}")

\# \=====================================================================  
\# 4\. EXAMPLE PLUGIN A: SLIDING TILE PUZZLE (Grid \+ A\* Manhattan)  
\# \=====================================================================

class SlidingTileState(BasePuzzleState):  
    def \_\_init\_\_(self, size: int \= 3, grid: Optional\[List\[int\]\] \= None):  
        self.size \= size  
        if grid is not None:  
            self.grid \= list(grid)  
        else:  
            \# Default slightly scrambled solvable 3x3  
            self.grid \= \[1, 2, 3, 4, 5, 6, 0, 7, 8\] if size \== 3 else list(range(1, size \* size)) \+ \[0\]

    def clone(self) \-\> "SlidingTileState":  
        return SlidingTileState(self.size, list(self.grid))

    def serialize(self) \-\> str:  
        return json.dumps({"puzzle": "sliding\_tile", "size": self.size, "grid": self.grid})

    @classmethod  
    def deserialize(cls, raw\_data: str) \-\> "SlidingTileState":  
        data \= json.loads(raw\_data)  
        if "grid" not in data or "size" not in data:  
            raise ValueError("Missing 'size' or 'grid' keys in JSON state.")  
        return cls(int(data\["size"\]), list(data\["grid"\]))

    def validate(self) \-\> Tuple\[bool, str\]:  
        expected \= set(range(self.size \* self.size))  
        if set(self.grid) \!= expected:  
            return False, f"Grid must contain exact numbers 0 through {self.size \* self.size \- 1}."  
        \# Check solvability via inversion count  
        tiles \= \[x for x in self.grid if x \!= 0\]  
        inversions \= sum(1 for i in range(len(tiles)) for j in range(i \+ 1, len(tiles)) if tiles\[i\] \> tiles\[j\])  
        if self.size % 2 \== 1:  
            if inversions % 2 \!= 0:  
                return False, f"Unsolvable transcription: odd inversion count ({inversions}) on odd grid."  
        else:  
            blank\_row\_from\_bottom \= self.size \- (self.grid.index(0) // self.size)  
            if (blank\_row\_from\_bottom % 2 \== 0) \== (inversions % 2 \== 0):  
                return False, "Unsolvable transcription: parity mismatch for even grid."  
        return True, "Valid & solvable state."

class SlidingTileSolver(BaseSolver):  
    def \_manhattan(self, grid: Tuple\[int, ...\], size: int) \-\> int:  
        dist \= 0  
        for idx, val in enumerate(grid):  
            if val \== 0:  
                continue  
            target\_idx \= val \- 1  
            r1, c1 \= divmod(idx, size)  
            r2, c2 \= divmod(target\_idx, size)  
            dist \+= abs(r1 \- r2) \+ abs(c1 \- c2)  
        return dist

    def solve(self, initial\_state: SlidingTileState, stream\_search: bool \= False) \-\> Generator\[SolverStep, None, None\]:  
        size \= initial\_state.size  
        start\_tuple \= tuple(initial\_state.grid)  
        goal\_tuple \= tuple(list(range(1, size \* size)) \+ \[0\])

        pq \= \[(self.\_manhattan(start\_tuple, size), 0, start\_tuple, \[\])\]  
        visited \= {start\_tuple: 0}  
        nodes\_expanded \= 0

        while pq:  
            f, g, current, path \= heapq.heappop(pq)  
            nodes\_expanded \+= 1

            if stream\_search:  
                yield SolverStep(  
                    state=SlidingTileState(size, list(current)),  
                    action\_desc=f"Exploring node (g={g}, h={f-g})",  
                    highlights={"active\_idx": current.index(0)},  
                    metrics={"expanded": nodes\_expanded, "depth": g}  
                )

            if current \== goal\_tuple:  
                \# Reconstruct step-by-step playback sequence  
                yield SolverStep(  
                    state=SlidingTileState(size, list(start\_tuple)),  
                    action\_desc="Start State",  
                    highlights={"active\_idx": start\_tuple.index(0)},  
                    metrics={"expanded": nodes\_expanded, "step": 0, "total": len(path)}  
                )  
                for step\_num, (grid\_snap, desc, moved\_idx) in enumerate(path, 1):  
                    yield SolverStep(  
                        state=SlidingTileState(size, list(grid\_snap)),  
                        action\_desc=desc,  
                        highlights={"moved\_idx": moved\_idx, "active\_idx": grid\_snap.index(0)},  
                        metrics={"expanded": nodes\_expanded, "step": step\_num, "total": len(path)}  
                    )  
                return

            zero\_idx \= current.index(0)  
            zr, zc \= divmod(zero\_idx, size)  
            for dr, dc, move\_name in \[(-1, 0, "Down"), (1, 0, "Up"), (0, \-1, "Right"), (0, 1, "Left")\]:  
                nr, nc \= zr \+ dr, zc \+ dc  
                if 0 \<= nr \< size and 0 \<= nc \< size:  
                    n\_idx \= nr \* size \+ nc  
                    nxt \= list(current)  
                    tile\_val \= nxt\[n\_idx\]  
                    nxt\[zero\_idx\], nxt\[n\_idx\] \= nxt\[n\_idx\], nxt\[zero\_idx\]  
                    nxt\_t \= tuple(nxt)  
                    new\_g \= g \+ 1  
                    if nxt\_t not in visited or new\_g \< visited\[nxt\_t\]:  
                        visited\[nxt\_t\] \= new\_g  
                        h \= self.\_manhattan(nxt\_t, size)  
                        desc \= f"Slide Tile {tile\_val} {move\_name}"  
                        heapq.heappush(pq, (new\_g \+ h, new\_g, nxt\_t, path \+ \[(nxt\_t, desc, zero\_idx)\]))

class SlidingTileCanvas(BasePuzzleCanvas):  
    """  
    Transcription ergonomics:  
    \- Click any two tiles in EDIT mode to swap them (for rapid 1:1 visual transcription),  
      OR type a number while hovering/selecting a cell.  
    """  
    def \_\_init\_\_(self, initial\_state: SlidingTileState):  
        super().\_\_init\_\_()  
        self.state \= initial\_state  
        self.selected\_edit\_idx: Optional\[int\] \= None  
        self.current\_step \= SolverStep(state=self.state, action\_desc="Edit Mode: Click two tiles to swap, or type numbers.")

    def \_cell\_rect(self, idx: int) \-\> QRectF:  
        size \= self.state.size  
        board\_dim \= min(self.width(), self.height()) \- 60  
        cell\_dim \= board\_dim / size  
        ox \= (self.width() \- board\_dim) / 2  
        oy \= (self.height() \- board\_dim) / 2  
        r, c \= divmod(idx, size)  
        return QRectF(ox \+ c \* cell\_dim \+ 4, oy \+ r \* cell\_dim \+ 4, cell\_dim \- 8, cell\_dim \- 8)

    def mousePressEvent(self, event: QMouseEvent):  
        if self.mode \!= InteractionMode.EDIT:  
            return  
        pos \= event.position()  
        for idx in range(self.state.size \* self.state.size):  
            if self.\_cell\_rect(idx).contains(pos):  
                if self.selected\_edit\_idx is None:  
                    self.selected\_edit\_idx \= idx  
                else:  
                    \# Swap tiles for fast visual transcription  
                    g \= self.state.grid  
                    g\[self.selected\_edit\_idx\], g\[idx\] \= g\[idx\], g\[self.selected\_edit\_idx\]  
                    self.selected\_edit\_idx \= None  
                    self.current\_step \= SolverStep(state=self.state, action\_desc="Swapped tiles manually.")  
                    self.state\_modified.emit()  
                self.update()  
                return

    def paintEvent(self, event):  
        painter \= QPainter(self)  
        painter.setRenderHint(QPainter.Antialiasing)

        render\_state: SlidingTileState \= self.current\_step.state if self.current\_step else self.state  
        highlights \= self.current\_step.highlights if self.current\_step else {}

        for idx, val in enumerate(render\_state.grid):  
            rect \= self.\_cell\_rect(idx)  
            if val \== 0:  
                painter.setPen(QPen(QColor(ChalkTheme.FG\_CHALK\_DUST), 1.5, Qt.DashLine))  
                painter.setBrush(QColor(ChalkTheme.BG\_CHALK\_BLACK))  
                painter.drawRoundedRect(rect, 8, 8)  
            else:  
                painter.setPen(QPen(QColor(ChalkTheme.PASTEL\_MINT), 2))  
                painter.setBrush(QColor(ChalkTheme.BG\_BOARD\_RAISED))  
                painter.drawRoundedRect(rect, 8, 8)

                painter.setPen(QColor(ChalkTheme.FG\_CHALK\_WHITE))  
                painter.setFont(QFont("Consolas", 22, QFont.Bold))  
                painter.drawText(rect, Qt.AlignCenter, str(val))

            \# Neon highlights for Edit selection or Playback moved tile  
            if self.mode \== InteractionMode.EDIT and self.selected\_edit\_idx \== idx:  
                ChalkTheme.draw\_neon\_rect(painter, rect, ChalkTheme.NEON\_CYAN)  
            elif self.mode \== InteractionMode.PLAYBACK and highlights.get("moved\_idx") \== idx:  
                ChalkTheme.draw\_neon\_rect(painter, rect, ChalkTheme.NEON\_LIME)

class SlidingTilePlugin(BasePuzzlePlugin):  
    name \= "Sliding Tile (N-Puzzle)"  
    category \= "Grid / Sequential"  
    description \= "Click two cells to swap tiles to match your target screen, then run A\* Playback or Instant Solve."

    def create\_default\_state(self) \-\> BasePuzzleState:  
        return SlidingTileState(3)

    def create\_solver(self) \-\> BaseSolver:  
        return SlidingTileSolver()

    def create\_canvas(self, initial\_state: BasePuzzleState) \-\> BasePuzzleCanvas:  
        return SlidingTileCanvas(initial\_state)

\# \=====================================================================  
\# 5\. EXAMPLE PLUGIN B: SAND / WATER TUBE SORT PUZZLE (Vector Containers)  
\# \=====================================================================

class SandTubeState(BasePuzzleState):  
    """  
    Each tube is a list of color indices (0 to N-1) from bottom to top, max capacity 4\.  
    """  
    def \_\_init\_\_(self, tubes: Optional\[List\[List\[int\]\]\] \= None, capacity: int \= 4):  
        self.capacity \= capacity  
        if tubes is not None:  
            self.tubes \= \[list(t) for t in tubes\]  
        else:  
            self.tubes \= \[  
                \[0, 1, 2, 0\],  
                \[2, 0, 1, 2\],  
                \[1, 2, 0, 1\],  
                \[\],  
                \[\]  
            \]

    def clone(self) \-\> "SandTubeState":  
        return SandTubeState(\[list(t) for t in self.tubes\], self.capacity)

    def serialize(self) \-\> str:  
        return json.dumps({"puzzle": "sand\_tubes", "capacity": self.capacity, "tubes": self.tubes})

    @classmethod  
    def deserialize(cls, raw\_data: str) \-\> "SandTubeState":  
        data \= json.loads(raw\_data)  
        return cls(data\["tubes"\], int(data.get("capacity", 4)))

    def validate(self) \-\> Tuple\[bool, str\]:  
        counts: Dict\[int, int\] \= {}  
        for t in self.tubes:  
            if len(t) \> self.capacity:  
                return False, f"A tube exceeds capacity ({self.capacity})."  
            for c in t:  
                counts\[c\] \= counts.get(c, 0) \+ 1  
        for color\_id, count in counts.items():  
            if count \!= self.capacity:  
                return False, f"Color \#{color\_id \+ 1} has {count} segments (must equal {self.capacity})."  
        return True, "Valid tube state."

    def is\_solved(self) \-\> bool:  
        return all(len(t) \== 0 or (len(t) \== self.capacity and len(set(t)) \== 1) for t in self.tubes)

class SandTubeSolver(BaseSolver):  
    def solve(self, initial\_state: SandTubeState, stream\_search: bool \= False) \-\> Generator\[SolverStep, None, None\]:  
        cap \= initial\_state.capacity  
        start\_key \= tuple(tuple(t) for t in initial\_state.tubes)  
        queue \= \[(initial\_state.clone(), \[\])\]  
        visited \= {start\_key}  
        expanded \= 0

        while queue:  
            curr\_state, path \= queue.pop(0)  
            expanded \+= 1

            if curr\_state.is\_solved():  
                yield SolverStep(state=initial\_state.clone(), action\_desc="Initial Tubes", metrics={"expanded": expanded})  
                for step\_idx, (st, desc, src, dst) in enumerate(path, 1):  
                    yield SolverStep(  
                        state=st,  
                        action\_desc=desc,  
                        highlights={"src": src, "dst": dst},  
                        metrics={"expanded": expanded, "step": step\_idx, "total": len(path)}  
                    )  
                return

            tubes \= curr\_state.tubes  
            for i, src in enumerate(tubes):  
                if not src:  
                    continue  
                \# Skip pouring from an already completed monochrome tube  
                if len(src) \== cap and len(set(src)) \== 1:  
                    continue  
                top\_color \= src\[-1\]  
                \# Count contiguous top segments of the same color  
                pour\_amount \= 0  
                for seg in reversed(src):  
                    if seg \== top\_color:  
                        pour\_amount \+= 1  
                    else:  
                        break

                for j, dst in enumerate(tubes):  
                    if i \== j or len(dst) \>= cap:  
                        continue  
                    \# Don't pour a single-color partial tube into an empty tube (pointless cycle)  
                    if not dst and len(set(src)) \== 1:  
                        continue  
                    if not dst or dst\[-1\] \== top\_color:  
                        space \= cap \- len(dst)  
                        actual\_pour \= min(pour\_amount, space)  
                        nxt\_state \= curr\_state.clone()  
                        for \_ in range(actual\_pour):  
                            nxt\_state.tubes\[j\].append(nxt\_state.tubes\[i\].pop())  
                        nxt\_key \= tuple(tuple(t) for t in nxt\_state.tubes)  
                        if nxt\_key not in visited:  
                            visited.add(nxt\_key)  
                            desc \= f"Pour Tube {i \+ 1} \-\> Tube {j \+ 1} ({actual\_pour} seg)"  
                            queue.append((nxt\_state, path \+ \[(nxt\_state, desc, i, j)\]))

class SandTubeCanvas(BasePuzzleCanvas):  
    """  
    Transcription ergonomics:  
    \- Left-click a tube to push the currently selected brush color into it.  
    \- Right-click a tube to pop the top segment off.  
    """  
    def \_\_init\_\_(self, initial\_state: SandTubeState):  
        super().\_\_init\_\_()  
        self.state \= initial\_state  
        self.active\_brush\_color: int \= 0  
        self.current\_step \= SolverStep(  
            state=self.state,  
            action\_desc="Edit Mode: Left-click tube to add color, Right-click to pop top segment."  
        )

    def \_tube\_rect(self, idx: int, total: int) \-\> QRectF:  
        w \= self.width()  
        h \= self.height()  
        tube\_w \= min(68.0, (w \- 80) / max(1, total) \- 16)  
        tube\_h \= min(240.0, h \- 100)  
        total\_span \= total \* (tube\_w \+ 20) \- 20  
        start\_x \= (w \- total\_span) / 2  
        y \= (h \- tube\_h) / 2  
        return QRectF(start\_x \+ idx \* (tube\_w \+ 20), y, tube\_w, tube\_h)

    def mousePressEvent(self, event: QMouseEvent):  
        if self.mode \!= InteractionMode.EDIT:  
            return  
        pos \= event.position()  
        total \= len(self.state.tubes)  
        for idx in range(total):  
            if self.\_tube\_rect(idx, total).contains(pos):  
                tube \= self.state.tubes\[idx\]  
                if event.button() \== Qt.LeftButton and len(tube) \< self.state.capacity:  
                    tube.append(self.active\_brush\_color)  
                    self.state\_modified.emit()  
                elif event.button() \== Qt.RightButton and tube:  
                    tube.pop()  
                    self.state\_modified.emit()  
                self.current\_step \= SolverStep(state=self.state, action\_desc=f"Edited Tube {idx \+ 1}")  
                self.update()  
                return

    def paintEvent(self, event):  
        painter \= QPainter(self)  
        painter.setRenderHint(QPainter.Antialiasing)

        render\_state: SandTubeState \= self.current\_step.state if self.current\_step else self.state  
        highlights \= self.current\_step.highlights if self.current\_step else {}  
        total \= len(render\_state.tubes)

        for idx, tube in enumerate(render\_state.tubes):  
            rect \= self.\_tube\_rect(idx, total)  
            seg\_h \= (rect.height() \- 12) / render\_state.capacity

            \# Draw sand/liquid segments from bottom to top  
            for seg\_idx, color\_id in enumerate(tube):  
                seg\_y \= rect.bottom() \- 6 \- (seg\_idx \+ 1) \* seg\_h  
                seg\_rect \= QRectF(rect.left() \+ 5, seg\_y, rect.width() \- 10, seg\_h \- 2)  
                hex\_col \= ChalkTheme.PASTEL\_PALETTE\[color\_id % len(ChalkTheme.PASTEL\_PALETTE)\]  
                painter.setPen(Qt.NoPen)  
                painter.setBrush(QColor(hex\_col))  
                painter.drawRoundedRect(seg\_rect, 4, 4)

            \# Draw Chalkboard Glass Tube Outline  
            painter.setPen(QPen(QColor(ChalkTheme.FG\_CHALK\_WHITE), 2.5))  
            painter.setBrush(Qt.NoBrush)  
            painter.drawRoundedRect(rect, 10, 10)

            \# Tube index label below  
            lbl\_rect \= QRectF(rect.left(), rect.bottom() \+ 8, rect.width(), 24)  
            painter.setPen(QColor(ChalkTheme.FG\_CHALK\_MUTED))  
            painter.setFont(QFont("Consolas", 11, QFont.Bold))  
            painter.drawText(lbl\_rect, Qt.AlignCenter, f"\#{idx \+ 1}")

            \# Neon highlights during playback  
            if self.mode \== InteractionMode.PLAYBACK:  
                if highlights.get("src") \== idx:  
                    ChalkTheme.draw\_neon\_rect(painter, rect, ChalkTheme.NEON\_CYAN, radius=10)  
                elif highlights.get("dst") \== idx:  
                    ChalkTheme.draw\_neon\_rect(painter, rect, ChalkTheme.NEON\_LIME, radius=10)

class SandTubePlugin(BasePuzzlePlugin):  
    name \= "Sand Tube Sort"  
    category \= "Container / BFS"  
    description \= "Select a pastel brush color, Left-Click tubes to fill, Right-Click to pop, then solve."

    def create\_default\_state(self) \-\> BasePuzzleState:  
        return SandTubeState()

    def create\_solver(self) \-\> BaseSolver:  
        return SandTubeSolver()

    def create\_canvas(self, initial\_state: BasePuzzleState) \-\> BasePuzzleCanvas:  
        return SandTubeCanvas(initial\_state)

    def create\_tool\_strip(self, canvas: SandTubeCanvas) \-\> Optional\[QWidget\]:  
        strip \= QWidget()  
        layout \= QHBoxLayout(strip)  
        layout.setContentsMargins(0, 0, 0, 0)  
        layout.addWidget(QLabel("Brush Color:"))

        for i, hex\_col in enumerate(ChalkTheme.PASTEL\_PALETTE):  
            btn \= QPushButton(f"C{i+1}")  
            btn.setStyleSheet(f"background-color: {hex\_col}; color: \#0F1412; font-weight: bold;")  
            btn.clicked.connect(lambda checked=False, c=i: setattr(canvas, "active\_brush\_color", c))  
            layout.addWidget(btn)

        add\_tube\_btn \= QPushButton("+ Tube")  
        def \_add\_tube():  
            if canvas.mode \== InteractionMode.EDIT:  
                canvas.state.tubes.append(\[\])  
                canvas.update()  
        add\_tube\_btn.clicked.connect(\_add\_tube)  
        layout.addWidget(add\_tube\_btn)

        rem\_tube\_btn \= QPushButton("- Tube")  
        def \_rem\_tube():  
            if canvas.mode \== InteractionMode.EDIT and len(canvas.state.tubes) \> 2:  
                canvas.state.tubes.pop()  
                canvas.update()  
        rem\_tube\_btn.clicked.connect(\_rem\_tube)  
        layout.addWidget(rem\_tube\_btn)  
        layout.addStretch()  
        return strip

\# \=====================================================================  
\# 6\. UNIFIED HUB WINDOW & PLAYBACK CONTROLLER  
\# \=====================================================================

class PuzzleHubWindow(QMainWindow):  
    def \_\_init\_\_(self, plugins: List\[BasePuzzlePlugin\]):  
        super().\_\_init\_\_()  
        self.setWindowTitle("SolverTools Hub // Chalkboard Suite")  
        self.resize(1180, 740)  
        self.plugins \= plugins

        \# Active session references  
        self.active\_plugin: Optional\[BasePuzzlePlugin\] \= None  
        self.active\_canvas: Optional\[BasePuzzleCanvas\] \= None  
        self.worker: Optional\[SolverWorker\] \= None  
        self.timeline: List\[SolverStep\] \= \[\]  
        self.timeline\_idx: int \= 0

        \# Playback QTimer  
        self.playback\_timer \= QTimer(self)  
        self.playback\_timer.timeout.connect(self.\_on\_timer\_tick)

        self.\_build\_ui()  
        if self.plugins:  
            self.nav\_list.setCurrentRow(0)

    def \_build\_ui(self):  
        root \= QWidget()  
        self.setCentralWidget(root)  
        main\_layout \= QHBoxLayout(root)  
        main\_layout.setContentsMargins(12, 12, 12, 12)  
        main\_layout.setSpacing(12)

        \# \--- LEFT SIDEBAR: Navigation & State I/O \---  
        sidebar\_frame \= QFrame()  
        sidebar\_frame.setObjectName("PanelFrame")  
        sidebar\_frame.setFixedWidth(240)  
        sidebar\_layout \= QVBoxLayout(sidebar\_frame)

        title\_lbl \= QLabel("SOLVERTOOLS // HUB")  
        title\_lbl.setStyleSheet(f"color: {ChalkTheme.NEON\_CYAN}; font-size: 15px; font-weight: bold;")  
        sidebar\_layout.addWidget(title\_lbl)

        self.nav\_list \= QListWidget()  
        for plugin in self.plugins:  
            item \= QListWidgetItem(f"{plugin.name}\\n\[{plugin.category}\]")  
            self.nav\_list.addItem(item)  
        self.nav\_list.currentRowChanged.connect(self.\_switch\_plugin)  
        sidebar\_layout.addWidget(self.nav\_list, stretch=1)

        \# Clipboard State I/O Buttons  
        io\_lbl \= QLabel("STATE TRANSCRIPTION I/O")  
        io\_lbl.setStyleSheet(f"color: {ChalkTheme.FG\_CHALK\_MUTED}; font-size: 11px; margin-top: 8px;")  
        sidebar\_layout.addWidget(io\_lbl)

        btn\_copy \= QPushButton("Copy State (Clipboard)")  
        btn\_copy.clicked.connect(self.\_copy\_state\_to\_clipboard)  
        sidebar\_layout.addWidget(btn\_copy)

        btn\_paste \= QPushButton("Paste State (Clipboard)")  
        btn\_paste.clicked.connect(self.\_paste\_state\_from\_clipboard)  
        sidebar\_layout.addWidget(btn\_paste)

        btn\_reset \= QPushButton("Reset / Unlock Edit Mode")  
        btn\_reset.clicked.connect(self.\_unlock\_edit\_mode)  
        sidebar\_layout.addWidget(btn\_reset)

        main\_layout.addWidget(sidebar\_frame)

        \# \--- CENTER WORKSPACE: Header \+ Tool Strip \+ Canvas \+ Transport Bar \---  
        center\_layout \= QVBoxLayout()  
        center\_layout.setSpacing(10)

        \# Puzzle Header  
        header\_frame \= QFrame()  
        header\_frame.setObjectName("PanelFrame")  
        header\_layout \= QVBoxLayout(header\_frame)  
        self.puzzle\_title\_lbl \= QLabel("")  
        self.puzzle\_title\_lbl.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {ChalkTheme.PASTEL\_MINT};")  
        self.puzzle\_desc\_lbl \= QLabel("")  
        self.puzzle\_desc\_lbl.setStyleSheet(f"color: {ChalkTheme.FG\_CHALK\_MUTED};")  
        header\_layout.addWidget(self.puzzle\_title\_lbl)  
        header\_layout.addWidget(self.puzzle\_desc\_lbl)  
        self.tool\_strip\_container \= QVBoxLayout()  
        header\_layout.addLayout(self.tool\_strip\_container)  
        center\_layout.addWidget(header\_frame)

        \# Stacked Canvas Viewport  
        self.canvas\_frame \= QFrame()  
        self.canvas\_frame.setObjectName("PanelFrame")  
        self.canvas\_stack \= QStackedWidget(self.canvas\_frame)  
        canvas\_frame\_layout \= QVBoxLayout(self.canvas\_frame)  
        canvas\_frame\_layout.addWidget(self.canvas\_stack)  
        center\_layout.addWidget(self.canvas\_frame, stretch=1)

        \# Transport & Execution Bar  
        transport\_frame \= QFrame()  
        transport\_frame.setObjectName("PanelFrame")  
        t\_layout \= QVBoxLayout(transport\_frame)

        top\_t\_row \= QHBoxLayout()  
        self.btn\_solve\_playback \= QPushButton("Solve (Playback Timeline)")  
        self.btn\_solve\_playback.setObjectName("NeonActionBtn")  
        self.btn\_solve\_playback.clicked.connect(lambda: self.\_run\_solver(instant=False))  
        top\_t\_row.addWidget(self.btn\_solve\_playback)

        self.btn\_solve\_instant \= QPushButton("Instant Solve (Skip to End)")  
        self.btn\_solve\_instant.setObjectName("InstantActionBtn")  
        self.btn\_solve\_instant.clicked.connect(lambda: self.\_run\_solver(instant=True))  
        top\_t\_row.addWidget(self.btn\_solve\_instant)

        top\_t\_row.addSpacing(16)  
        self.btn\_prev \= QPushButton("\< Step")  
        self.btn\_prev.clicked.connect(lambda: self.\_step\_Manual(-1))  
        top\_t\_row.addWidget(self.btn\_prev)

        self.btn\_play\_pause \= QPushButton("Play / Pause")  
        self.btn\_play\_pause.clicked.connect(self.\_toggle\_timer)  
        top\_t\_row.addWidget(self.btn\_play\_pause)

        self.btn\_next \= QPushButton("Step \>")  
        self.btn\_next.clicked.connect(lambda: self.\_step\_Manual(1))  
        top\_t\_row.addWidget(self.btn\_next)

        top\_t\_row.addSpacing(12)  
        top\_t\_row.addWidget(QLabel("Speed:"))  
        self.speed\_slider \= QSlider(Qt.Horizontal)  
        self.speed\_slider.setRange(20, 800)  
        self.speed\_slider.setValue(280)  
        self.speed\_slider.setInvertedAppearance(True)  \# Right \= faster (lower ms interval)  
        self.speed\_slider.valueChanged.connect(lambda val: self.playback\_timer.setInterval(val))  
        top\_t\_row.addWidget(self.speed\_slider)  
        t\_layout.addLayout(top\_t\_row)

        \# Timeline Scrubber Row  
        scrub\_row \= QHBoxLayout()  
        self.step\_status\_lbl \= QLabel("Mode: EDIT // Ready for transcription")  
        self.step\_status\_lbl.setStyleSheet(f"color: {ChalkTheme.NEON\_CYAN}; font-weight: bold;")  
        scrub\_row.addWidget(self.step\_status\_lbl)

        self.timeline\_scrubber \= QSlider(Qt.Horizontal)  
        self.timeline\_scrubber.setEnabled(False)  
        self.timeline\_scrubber.valueChanged.connect(self.\_scrub\_to\_index)  
        scrub\_row.addWidget(self.timeline\_scrubber, stretch=1)  
        t\_layout.addLayout(scrub\_row)

        center\_layout.addWidget(transport\_frame)  
        main\_layout.addLayout(center\_layout, stretch=1)

        \# \--- RIGHT SIDEBAR: Action & Step Trace Log \---  
        log\_frame \= QFrame()  
        log\_frame.setObjectName("PanelFrame")  
        log\_frame.setFixedWidth(270)  
        log\_layout \= QVBoxLayout(log\_frame)  
        log\_hdr \= QLabel("STEP & TRACE INSPECTOR")  
        log\_hdr.setStyleSheet(f"color: {ChalkTheme.PASTEL\_LAVENDER}; font-weight: bold;")  
        log\_layout.addWidget(log\_hdr)

        self.log\_box \= QTextEdit()  
        self.log\_box.setReadOnly(True)  
        log\_layout.addWidget(self.log\_box, stretch=1)

        btn\_clear\_log \= QPushButton("Clear Log")  
        btn\_clear\_log.clicked.connect(self.log\_box.clear)  
        log\_layout.addWidget(btn\_clear\_log)  
        main\_layout.addWidget(log\_frame)

    \# \-----------------------------------------------------------------  
    \# Plugin Navigation & Setup  
    \# \-----------------------------------------------------------------  
    def \_switch\_plugin(self, row: int):  
        if row \< 0 or row \>= len(self.plugins):  
            return  
        self.playback\_timer.stop()  
        self.active\_plugin \= self.plugins\[row\]  
        self.puzzle\_title\_lbl.setText(self.active\_plugin.name)  
        self.puzzle\_desc\_lbl.setText(self.active\_plugin.description)

        \# Clear previous tool strip  
        while self.tool\_strip\_container.count():  
            item \= self.tool\_strip\_container.takeAt(0)  
            if item.widget():  
                item.widget().deleteLater()

        \# Instantiate fresh canvas for the selected puzzle  
        state \= self.active\_plugin.create\_default\_state()  
        canvas \= self.active\_plugin.create\_canvas(state)  
        self.active\_canvas \= canvas

        \# Remove old stacked widget children and mount new canvas  
        while self.canvas\_stack.count():  
            w \= self.canvas\_stack.widget(0)  
            self.canvas\_stack.removeWidget(w)  
            w.deleteLater()  
        self.canvas\_stack.addWidget(canvas)

        tool\_strip \= self.active\_plugin.create\_tool\_strip(canvas)  
        if tool\_strip:  
            self.tool\_strip\_container.addWidget(tool\_strip)

        self.\_unlock\_edit\_mode()  
        self.\_log(f"Loaded plugin: \<b\>{self.active\_plugin.name}\</b\>")

    def \_unlock\_edit\_mode(self):  
        self.playback\_timer.stop()  
        self.timeline.clear()  
        self.timeline\_scrubber.setEnabled(False)  
        if self.active\_canvas:  
            self.active\_canvas.set\_mode(InteractionMode.EDIT)  
            self.active\_canvas.set\_step(SolverStep(state=self.active\_canvas.state, action\_desc="Edit Mode"))  
        self.step\_status\_lbl.setStyleSheet(f"color: {ChalkTheme.NEON\_CYAN}; font-weight: bold;")  
        self.step\_status\_lbl.setText("Mode: EDIT // Interactive setup active")

    \# \-----------------------------------------------------------------  
    \# Solver Execution & Playback Controls  
    \# \-----------------------------------------------------------------  
    def \_run\_solver(self, instant: bool):  
        if not self.active\_plugin or not self.active\_canvas:  
            return  
        self.playback\_timer.stop()

        valid, msg \= self.active\_canvas.state.validate()  
        if not valid:  
            self.step\_status\_lbl.setStyleSheet(f"color: {ChalkTheme.NEON\_CORAL}; font-weight: bold;")  
            self.step\_status\_lbl.setText(f"Validation Error: {msg}")  
            self.\_log(f"\<span style='color:{ChalkTheme.NEON\_CORAL};'\>\[INVALID\] {msg}\</span\>")  
            return

        self.active\_canvas.set\_mode(InteractionMode.PLAYBACK)  
        self.step\_status\_lbl.setStyleSheet(f"color: {ChalkTheme.PASTEL\_PEACH}; font-weight: bold;")  
        self.step\_status\_lbl.setText("Solving in background thread...")

        solver \= self.active\_plugin.create\_solver()  
        self.worker \= SolverWorker(solver, self.active\_canvas.state, instant\_mode=instant)  
        self.worker.finished\_timeline.connect(self.\_on\_timeline\_ready)  
        self.worker.finished\_instant.connect(self.\_on\_instant\_ready)  
        self.worker.failed.connect(self.\_on\_solver\_failed)  
        self.worker.start()

    def \_on\_timeline\_ready(self, timeline: List\[SolverStep\], elapsed: float):  
        self.timeline \= timeline  
        self.timeline\_idx \= 0  
        self.timeline\_scrubber.setEnabled(True)  
        self.timeline\_scrubber.setRange(0, len(timeline) \- 1)  
        self.timeline\_scrubber.setValue(0)

        self.\_log(  
            f"\<span style='color:{ChalkTheme.NEON\_LIME};'\>Solved in {elapsed\*1000:.1f} ms "  
            f"({len(timeline)-1} moves).\</span\>"  
        )  
        for idx, step in enumerate(timeline):  
            self.\_log(f"\<b\>\#{idx:02d}\</b\>: {step.action\_desc}")

        self.playback\_timer.setInterval(self.speed\_slider.value())  
        self.playback\_timer.start()

    def \_on\_instant\_ready(self, final\_step: SolverStep, total\_steps: int, elapsed: float):  
        self.timeline \= \[final\_step\]  
        self.timeline\_scrubber.setEnabled(False)  
        if self.active\_canvas:  
            self.active\_canvas.state \= final\_step.state.clone()  
            self.active\_canvas.set\_step(final\_step)  
        self.step\_status\_lbl.setStyleSheet(f"color: {ChalkTheme.NEON\_LIME}; font-weight: bold;")  
        self.step\_status\_lbl.setText(f"INSTANT SOLVED // {total\_steps \- 1} steps ({elapsed\*1000:.1f} ms)")  
        self.\_log(  
            f"\<span style='color:{ChalkTheme.NEON\_LIME};'\>\[INSTANT\] Jumped to final state "  
            f"in {elapsed\*1000:.1f} ms.\</span\>"  
        )

    def \_on\_solver\_failed(self, err\_msg: str):  
        self.step\_status\_lbl.setStyleSheet(f"color: {ChalkTheme.NEON\_CORAL}; font-weight: bold;")  
        self.step\_status\_lbl.setText(err\_msg)  
        self.\_log(f"\<span style='color:{ChalkTheme.NEON\_CORAL};'\>{err\_msg}\</span\>")

    def \_on\_timer\_tick(self):  
        if self.timeline\_idx \< len(self.timeline) \- 1:  
            self.timeline\_scrubber.setValue(self.timeline\_idx \+ 1)  
        else:  
            self.playback\_timer.stop()

    def \_toggle\_timer(self):  
        if not self.timeline:  
            return  
        if self.playback\_timer.isActive():  
            self.playback\_timer.stop()  
        else:  
            if self.timeline\_idx \>= len(self.timeline) \- 1:  
                self.timeline\_scrubber.setValue(0)  
            self.playback\_timer.start(self.speed\_slider.value())

    def \_step\_Manual(self, delta: int):  
        if not self.timeline:  
            return  
        self.playback\_timer.stop()  
        new\_idx \= max(0, min(len(self.timeline) \- 1, self.timeline\_idx \+ delta))  
        self.timeline\_scrubber.setValue(new\_idx)

    def \_scrub\_to\_index(self, idx: int):  
        if not self.timeline or idx \< 0 or idx \>= len(self.timeline):  
            return  
        self.timeline\_idx \= idx  
        step \= self.timeline\[idx\]  
        if self.active\_canvas:  
            self.active\_canvas.state \= step.state.clone()  
            self.active\_canvas.set\_step(step)  
        self.step\_status\_lbl.setStyleSheet(f"color: {ChalkTheme.NEON\_LIME}; font-weight: bold;")  
        self.step\_status\_lbl.setText(f"Step {idx}/{len(self.timeline)-1}: {step.action\_desc}")

    \# \-----------------------------------------------------------------  
    \# Clipboard Serialization I/O  
    \# \-----------------------------------------------------------------  
    def \_copy\_state\_to\_clipboard(self):  
        if not self.active\_canvas:  
            return  
        raw \= self.active\_canvas.state.serialize()  
        pyperclip.copy(raw)  
        self.\_log(f"Copied state JSON to clipboard ({len(raw)} chars).")

    def \_paste\_state\_from\_clipboard(self):  
        if not self.active\_canvas:  
            return  
        raw \= pyperclip.paste().strip()  
        if not raw:  
            self.\_log(f"\<span style='color:{ChalkTheme.NEON\_CORAL};'\>Clipboard is empty.\</span\>")  
            return  
        try:  
            state\_cls \= type(self.active\_canvas.state)  
            new\_state \= state\_cls.deserialize(raw)  
            self.active\_canvas.state \= new\_state  
            self.\_unlock\_edit\_mode()  
            self.\_log(f"\<span style='color:{ChalkTheme.NEON\_LIME};'\>Imported state from clipboard.\</span\>")  
        except Exception as exc:  
            logger.error(f"Clipboard state parse error: {exc}")  
            self.\_log(f"\<span style='color:{ChalkTheme.NEON\_CORAL};'\>Import Failed: {exc}\</span\>")

    def \_log(self, html\_line: str):  
        self.log\_box.append(html\_line)

\# \=====================================================================  
\# 7\. ENTRY POINT & VALIDATION  
\# \=====================================================================

if \_\_name\_\_ \== "\_\_main\_\_":  
    app \= QApplication(sys.argv)  
    app.setStyleSheet(ChalkTheme.get\_stylesheet())

    registered\_plugins: List\[BasePuzzlePlugin\] \= \[  
        SlidingTilePlugin(),  
        SandTubePlugin(),  
    \]

    \# Quick sanity assertion on state serialization & validation before launch  
    for p in registered\_plugins:  
        st \= p.create\_default\_state()  
        ok, reason \= st.validate()  
        assert ok, f"Default state failed validation for {p.name}: {reason}"  
        roundtrip \= st.deserialize(st.serialize())  
        assert roundtrip.serialize() \== st.serialize(), f"Serialization mismatch in {p.name}"

    window \= PuzzleHubWindow(registered\_plugins)  
    window.show()  
    sys.exit(app.exec())

## **6\. Recipes for Adding Future Puzzle Archetypes**

Because BasePuzzleCanvas is just a standard QWidget with access to ChalkTheme, you can handle any future puzzle format without changing the hub:

| Puzzle Archetype | Transcription UI Strategy (InteractionMode.EDIT) | Rendering Strategy (paintEvent) | Recommended Solver Yield Pattern |
| :---- | :---- | :---- | :---- |
| **2D Mazes / Grid Pathfinding** | Left-click \+ drag (mouseMoveEvent) to paint walls in PASTEL\_MINT; Middle-click to place Start (PASTEL\_SKY) and Goal (NEON\_LIME). | QPainter.fillRect over a 2D numpy array (uint8). | Yield each frontier expansion (stream\_search=True) or yield the final coordinate path. |
| **Constraint Grids (Sudoku, Nonograms, Queens)** | Click cell to focus (NEON\_CYAN border), press 1-9 or Backspace in keyPressEvent. | Draw thick 3x3 chalk sub-grids (FG\_CHALK\_WHITE) and thin inner lines (FG\_CHALK\_DUST). | Use **Instant Solve** (instant=True) to run backtracking/DLX and render the filled numbers in PASTEL\_MINT so they visually contrast with your initial FG\_CHALK\_WHITE clues. |
| **Jigsaw / Polyomino Packing (Pentominoes, Tangrams)** | Split canvas into a Left Staging Tray and a Right Target Board; toggle piece shapes in the tool strip. | Assign each piece ID a distinct color from ChalkTheme.PASTEL\_PALETTE and outline piece boundaries with a 2px dark chalk border. | Yield each placement/backtrack step, or jump straight to the final packed board. |
| **Text / Cipher / Word Ladders** | Override create\_canvas to include a QLineEdit or QPlainTextEdit styled with the chalkboard QSS directly inside the canvas widget. | Render character transformation chains or letter-frequency histograms using QPainter bars. | Yield candidate plaintexts or word-hop steps along with heuristic scores in SolverStep.metrics. |

## **7\. Next Steps for Your Transcription Workflow**

If you find yourself frequently transcribing grids or tube states from another window or emulator on your screen, your pylearn environment also includes **opencv (4.12.0)** and **pillow (11.3.0)**. Later on, you can drop a "Grab Screen Region" button right next to "Paste State (Clipboard)" in the left sidebar that lets you drag a bounding box over a puzzle window and passes the cropped numpy RGB array into an optional BasePuzzlePlugin.parse\_from\_image(img\_array) hook to pre-fill the board automatically.