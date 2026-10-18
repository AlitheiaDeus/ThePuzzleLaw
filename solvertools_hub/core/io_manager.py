"""
io_manager.py - Clipboard and JSON file serialization handlers for solvertools_hub.
Wraps pyperclip and file I/O with validation and structured error handling.
"""

from pathlib import Path
from typing import Type

from loguru import logger
import pyperclip

from .base_plugin import BasePuzzleState


class IOManager:
    """Manages clipboard and file serialization for puzzle states."""

    @staticmethod
    def copy_state_to_clipboard(state: BasePuzzleState) -> str:
        """Serializes state and copies it to system clipboard."""
        raw_text = state.serialize()
        pyperclip.copy(raw_text)
        logger.debug(f"Copied state to clipboard ({len(raw_text)} chars).")
        return raw_text

    @staticmethod
    def paste_state_from_clipboard(state_cls: Type[BasePuzzleState]) -> BasePuzzleState:
        """Reads raw string from clipboard and deserializes using target state class."""
        raw_text = pyperclip.paste().strip()
        if not raw_text:
            raise ValueError("Clipboard is empty.")
        new_state = state_cls.deserialize(raw_text)
        is_valid, reason = new_state.validate()
        if not is_valid:
            logger.warning(f"Deserialized state failed validation: {reason}")
        return new_state

    @staticmethod
    def export_state_to_file(state: BasePuzzleState, file_path: str | Path) -> None:
        """Saves serialized state to a file."""
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        raw_text = state.serialize()
        path.write_text(raw_text, encoding="utf-8")
        logger.info(f"State saved to {path}")

    @staticmethod
    def import_state_from_file(
        state_cls: Type[BasePuzzleState], file_path: str | Path
    ) -> BasePuzzleState:
        """Reads state from a file and deserializes it."""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"State file not found: {path}")
        raw_text = path.read_text(encoding="utf-8").strip()
        new_state = state_cls.deserialize(raw_text)
        return new_state
