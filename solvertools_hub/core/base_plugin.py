"""
base_plugin.py - Core abstract contracts for solvertools_hub.
Defines InteractionMode, BasePuzzleState, SolverStep, BaseSolver, BasePuzzleCanvas, and BasePuzzlePlugin.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Any, Dict, Generator, Optional, Tuple

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget


class InteractionMode(Enum):
    """Execution state for the interactive canvas."""
    EDIT = auto()      # User is actively transcribing or altering initial state
    PLAYBACK = auto()  # Solution trace is active; direct edits are locked


class BasePuzzleState(ABC):
    """Abstract representation of a puzzle's state snapshot at a single point in time."""

    @abstractmethod
    def clone(self) -> "BasePuzzleState":
        """Returns a deep clone of the current state."""
        pass

    @abstractmethod
    def serialize(self) -> str:
        """Exports state to a standardized JSON or string format for clipboard/file persistence."""
        pass

    @classmethod
    @abstractmethod
    def deserialize(cls, raw_data: str) -> "BasePuzzleState":
        """Parses an exported state string into a concrete BasePuzzleState instance."""
        pass

    @abstractmethod
    def validate(self) -> Tuple[bool, str]:
        """
        Validates whether the manually transcribed state is legal and well-formed.
        Returns: (is_valid, reason_or_message)
        """
        pass


@dataclass
class SolverStep:
    """Standardized yield item produced by puzzle solvers."""
    state: BasePuzzleState
    action_desc: str = "Initial State"
    highlights: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)


class BaseSolver(ABC):
    """Generator-based solver contract supporting step-by-step playback and instant solve."""

    @abstractmethod
    def solve(
        self,
        initial_state: BasePuzzleState,
        stream_search: bool = False
    ) -> Generator[SolverStep, None, None]:
        """
        Executes search algorithm, yielding SolverStep objects.
        - stream_search=False: yields sequential winning path steps from start to finish.
        - stream_search=True: yields exploratory/backtracking steps during search.
        """
        pass


class BasePuzzleCanvas(QWidget):
    """Base interactive viewport for rendering and manual transcription."""
    state_modified = Signal()

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.mode: InteractionMode = InteractionMode.EDIT
        self.current_step: Optional[SolverStep] = None
        self.setMinimumSize(480, 420)
        self.setFocusPolicy(Qt.StrongFocus)

    def set_step(self, step: SolverStep) -> None:
        """Sets the active step to render and repaints."""
        self.current_step = step
        self.update()

    def set_mode(self, mode: InteractionMode) -> None:
        """Sets the canvas interaction mode (EDIT vs. PLAYBACK) and repaints."""
        self.mode = mode
        if mode == InteractionMode.EDIT:
            self.current_step = None
        self.update()

    def get_render_state(self) -> BasePuzzleState:
        """
        Returns the active state to render:
        Always self.state in EDIT mode, or the playback step's state in PLAYBACK mode.
        """
        if self.mode == InteractionMode.EDIT or self.current_step is None:
            return self.state
        return self.current_step.state


class BasePuzzlePlugin(ABC):
    """Top-level descriptor registered in the Hub."""
    name: str = "Unnamed Puzzle"
    category: str = "General"
    description: str = ""
    is_wip: bool = False

    @abstractmethod
    def create_default_state(self) -> BasePuzzleState:
        """Generates a legal default starting state."""
        pass

    @abstractmethod
    def create_solver(self) -> BaseSolver:
        """Instantiates the solver engine."""
        pass

    @abstractmethod
    def create_canvas(self, initial_state: BasePuzzleState) -> BasePuzzleCanvas:
        """Instantiates the interactive QPainter canvas."""
        pass

    def create_tool_strip(self, canvas: BasePuzzleCanvas) -> Optional[QWidget]:
        """
        Optional puzzle-specific toolbar for transcription
        (e.g., brush swatches, dimension spinners, wall toggles).
        """
        return None
