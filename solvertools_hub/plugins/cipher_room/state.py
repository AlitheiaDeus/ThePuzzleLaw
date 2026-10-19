"""
state.py - The Cipher Room cryptanalysis state model.
Supports unspaced Morse sequences, classical substitution/ROT inputs, and ARG transformation chains.
"""

import json
from typing import Dict, List, Optional, Tuple

from ...core.base_plugin import BasePuzzleState


class CipherRoomState(BasePuzzleState):
    """
    Cryptanalysis & Signal Suite puzzle state.
    ciphertext: Raw signal or encrypted text to be analyzed.
    cipher_type: 'morse' | 'rot' | 'substitution' | 'arg'
    parameters: Optional dict with cipher-specific keys (e.g. rot_offset, substitution_key).
    """

    def __init__(
        self,
        ciphertext: str = "...---...",
        cipher_type: str = "morse",
        parameters: Optional[Dict[str, str]] = None,
    ):
        self.ciphertext = str(ciphertext)
        self.cipher_type = str(cipher_type)
        self.parameters = dict(parameters) if parameters else {}

    def clone(self) -> "CipherRoomState":
        return CipherRoomState(
            ciphertext=self.ciphertext,
            cipher_type=self.cipher_type,
            parameters=dict(self.parameters),
        )

    def serialize(self) -> str:
        return json.dumps({
            "ciphertext": self.ciphertext,
            "cipher_type": self.cipher_type,
            "parameters": self.parameters,
        })

    @classmethod
    def deserialize(cls, raw_data: str) -> "CipherRoomState":
        data = json.loads(raw_data)
        return cls(
            ciphertext=data.get("ciphertext", ""),
            cipher_type=data.get("cipher_type", "morse"),
            parameters=data.get("parameters", {}),
        )

    def validate(self) -> Tuple[bool, str]:
        if not self.ciphertext:
            return False, "Ciphertext cannot be empty"
        return True, ""
