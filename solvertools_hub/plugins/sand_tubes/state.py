"""
state.py - Liquid Sorter Pro state representation, serialization, and validation.
Supports per-tube variable capacities, split color toggles, and feasibility pruning.
"""

from collections import Counter
import json
from typing import Dict, List, Optional, Tuple, Union

from ...core.base_plugin import BasePuzzleState


class SandTubeState(BasePuzzleState):
    """
    State representing liquid / sand tubes with independent stack capacities.
    tubes[i] is a list of color IDs (integers), stored from bottom to top:
    - tubes[i][0] is the base item
    - tubes[i][-1] is the top item
    """

    def __init__(
        self,
        tubes: Optional[List[List[int]]] = None,
        capacity: Union[int, List[int]] = 4,
        allow_split_colors: bool = False,
    ):
        self.allow_split_colors = allow_split_colors

        if tubes is not None:
            self.tubes = [list(t) for t in tubes]
        else:
            # Default starting level (3 filled, 2 empty buffer tubes)
            self.tubes = [
                [0, 1, 2, 0],
                [2, 0, 1, 2],
                [1, 2, 0, 1],
                [],
                [],
            ]

        num_tubes = len(self.tubes)
        if isinstance(capacity, list):
            if len(capacity) < num_tubes:
                # Pad with last capacity or default 4
                last_cap = capacity[-1] if capacity else 4
                self.capacities = list(capacity) + [last_cap] * (num_tubes - len(capacity))
            else:
                self.capacities = list(capacity[:num_tubes])
        else:
            self.capacities = [int(capacity)] * num_tubes

    @property
    def capacity(self) -> int:
        """Backward-compatibility property returning max capacity across all tubes."""
        return max(self.capacities) if self.capacities else 4

    def clone(self) -> "SandTubeState":
        return SandTubeState(
            tubes=[list(t) for t in self.tubes],
            capacity=list(self.capacities),
            allow_split_colors=self.allow_split_colors,
        )

    def serialize(self) -> str:
        return json.dumps({
            "puzzle": "liquid_sorter",
            "capacities": self.capacities,
            "tubes": self.tubes,
            "allow_split_colors": self.allow_split_colors,
        }, sort_keys=True)

    @classmethod
    def deserialize(cls, raw_data: str) -> "SandTubeState":
        data = json.loads(raw_data)
        tubes = data["tubes"]
        capacities = data.get("capacities")
        if capacities is None:
            # Legacy format with scalar capacity
            cap_scalar = int(data.get("capacity", 4))
            capacities = [cap_scalar] * len(tubes)
        allow_split = bool(data.get("allow_split_colors", False))
        return cls(tubes=tubes, capacity=capacities, allow_split_colors=allow_split)

    def to_notation(self) -> str:
        """
        Exports the puzzle state to snippet notation:
        'item,item,-,- / item,-,-,- / -,-,-'
        Items are listed from bottom to top; empty slots are '-'.
        """
        stacks = []
        for tube, cap in zip(self.tubes, self.capacities):
            tokens = []
            for s in range(cap):
                val = tube[s] if s < len(tube) else None
                if val is not None:
                    tokens.append(f"C{val + 1}")
                else:
                    tokens.append("-")
            stacks.append(",".join(tokens))
        return " / ".join(stacks)

    @classmethod
    def from_notation(cls, notation: str, allow_split_colors: bool = False) -> "SandTubeState":
        """
        Parses snippet notation format:
        Stacks separated by '/', items by ',' (bottom-to-top), empty slots with '-'.
        Supports letter tokens ('w', 'n', 'c', 'l') or numeric tokens ('1', '2', 'C1', 'C2').
        """
        raw_stacks = [s.strip() for s in notation.split('/') if s.strip()]
        if not raw_stacks:
            return cls(allow_split_colors=allow_split_colors)

        symbol_map: Dict[str, int] = {}
        tubes: List[List[int]] = []
        capacities: List[int] = []

        for stack_str in raw_stacks:
            raw_tokens = [t.strip() for t in stack_str.split(',') if t.strip()]
            cap = len(raw_tokens) if raw_tokens else 4
            tube: List[int] = []
            for t in raw_tokens:
                if t in ('-', '_', '.'):
                    continue
                if t.upper().startswith('C') and t[1:].isdigit():
                    col = int(t[1:]) - 1
                elif t.isdigit():
                    val = int(t)
                    col = val - 1 if val > 0 else 0
                else:
                    # Letter/symbol token (e.g. 'w', 'n', 'c', 'l')
                    key = t.lower()
                    if key not in symbol_map:
                        symbol_map[key] = len(symbol_map)
                    col = symbol_map[key]
                tube.append(col)

            tubes.append(tube)
            capacities.append(max(cap, len(tube), 1))

        return cls(tubes=tubes, capacity=capacities, allow_split_colors=allow_split_colors)

    def get_slot(self, tube_idx: int, slot_idx: int) -> Optional[int]:
        """Returns the color at a specific slot in tube_idx (0-indexed from bottom), or None."""
        if 0 <= tube_idx < len(self.tubes):
            tube = self.tubes[tube_idx]
            if 0 <= slot_idx < len(tube):
                return tube[slot_idx]
        return None

    def set_slot(self, tube_idx: int, slot_idx: int, color: Optional[int]) -> None:
        """Sets or clears the color at a specific slot in tube_idx (0-indexed from bottom)."""
        if 0 <= tube_idx < len(self.tubes):
            cap = self.capacities[tube_idx]
            if 0 <= slot_idx < cap:
                tube = self.tubes[tube_idx]
                if slot_idx >= len(tube):
                    tube.extend([None] * (slot_idx + 1 - len(tube)))
                tube[slot_idx] = color
                # Trim trailing None items to keep representation compact
                while tube and tube[-1] is None:
                    tube.pop()

    def settle_tubes(self) -> None:
        """Gravity-drops any floating segments to the bottom of their respective tubes."""
        for idx in range(len(self.tubes)):
            self.tubes[idx] = [c for c in self.tubes[idx] if c is not None]

    def clear_tube(self, tube_idx: int) -> None:
        """Empties all segments in the specified tube."""
        if 0 <= tube_idx < len(self.tubes):
            self.tubes[tube_idx].clear()

    def clear_all_tubes(self) -> None:
        """Empties all segments across all tubes."""
        for t in self.tubes:
            t.clear()

    def get_used_colors(self) -> List[int]:
        """Returns a sorted list of unique color IDs currently placed on the board."""
        colors = set()
        for t in self.tubes:
            for c in t:
                if c is not None:
                    colors.add(c)
        return sorted(colors)

    def get_color_counts(self) -> Counter:
        """Returns Counter mapping color ID to total number of segments on board."""
        return Counter(c for t in self.tubes for c in t if c is not None)

    def has_floating_segments(self) -> bool:
        """Returns True if any tube contains an empty slot beneath a filled segment."""
        for tube in self.tubes:
            seen_none = False
            for val in tube:
                if val is None:
                    seen_none = True
                elif seen_none:
                    return True
        return False

    def can_satisfy_unique_capacities(self) -> Tuple[bool, str]:
        """
        When split colors are forbidden, checks whether color segment counts
        can mathematically fit into the available tube capacities.
        """
        color_counts = Counter(item for tube in self.tubes for item in tube if item is not None)
        available_caps = list(self.capacities)

        for color_id, count in color_counts.items():
            if count in available_caps:
                available_caps.remove(count)
            else:
                return (
                    False,
                    f"Color #{color_id + 1} has {count} segments, which does not match any available tube capacity {self.capacities} without splitting.",
                )
        return True, "Valid color-to-capacity partition."

    def validate(self) -> Tuple[bool, str]:
        if not self.tubes or len(self.tubes) < 2:
            return False, "At least two tubes are required to sort."

        if len(self.capacities) != len(self.tubes):
            return False, "Capacities count does not match number of tubes."

        for idx, (tube, cap) in enumerate(zip(self.tubes, self.capacities)):
            if cap < 1:
                return False, f"Tube #{idx + 1} has invalid capacity ({cap}). Capacity must be >= 1."

            # Check for hovering / floating segments (empty slot below filled segment)
            seen_none = False
            for s_idx, val in enumerate(tube):
                if val is None:
                    seen_none = True
                elif seen_none:
                    return (
                        False,
                        f"Tube #{idx + 1} has floating/hovering segments (slot {s_idx + 1} is above an empty slot). Click 'Settle' to drop segments to bottom.",
                    )

            filled_count = sum(1 for c in tube if c is not None)
            if filled_count > cap:
                return False, f"Tube #{idx + 1} has {filled_count} segments, exceeding its capacity ({cap})."

        all_items = [c for t in self.tubes for c in t if c is not None]
        if not all_items:
            return False, "All tubes are empty. Please paint at least one color segment."

        total_capacity = sum(self.capacities)
        if len(all_items) > total_capacity:
            return False, f"Total segments ({len(all_items)}) exceed total capacity ({total_capacity})."

        # Check if any empty/buffer space exists
        total_empty_slots = total_capacity - len(all_items)
        if total_empty_slots < 1 and not self.is_solved():
            return False, "No empty slots available. Sorting is impossible without at least 1 open buffer slot."

        # Unique capacity partition check if split colors disallowed
        if not self.allow_split_colors:
            ok, reason = self.can_satisfy_unique_capacities()
            if not ok:
                return False, reason

        return True, "Valid liquid sorting configuration."

    def is_solved(self) -> bool:
        """
        A state is solved when each tube is either completely empty (len == 0)
        or completely filled to its specific capacity with a single uniform color.
        If allow_split_colors is False, no two completed tubes may share the same color.
        """
        seen_colors = set()
        for tube, cap in zip(self.tubes, self.capacities):
            clean_tube = [c for c in tube if c is not None]
            if not clean_tube:
                continue
            if len(clean_tube) != cap:
                return False
            if len(set(clean_tube)) != 1:
                return False

            color = clean_tube[0]
            if not self.allow_split_colors:
                if color in seen_colors:
                    return False
                seen_colors.add(color)

        return True
