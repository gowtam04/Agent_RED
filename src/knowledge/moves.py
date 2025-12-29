"""Move data accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to moves data
DEFAULT_MOVES_PATH = Path(__file__).parent.parent.parent / "data" / "moves.json"


class MoveData(KnowledgeBase):
    """Accessor for Pokemon move data.

    Provides access to all 165 Gen 1 moves with properties including:
    - Type, power, accuracy, PP
    - Category (PHYSICAL/SPECIAL/STATUS)
    - Effects and effect chances
    - TM/HM mappings
    """

    def __init__(self, data_path: Path = DEFAULT_MOVES_PATH):
        """Initialize the moves accessor.

        Args:
            data_path: Path to moves.json file.
        """
        super().__init__(data_path)

    @property
    def moves(self) -> dict:
        """Get all moves data."""
        return self.data.get("moves", {})

    @property
    def tm_hm_mapping(self) -> dict:
        """Get TM/HM to move name mapping."""
        return self.data.get("tm_hm_mapping", {})

    def get(self, move_name: str) -> dict | None:
        """Get move data by name.

        Args:
            move_name: The move name (e.g., "THUNDERBOLT").

        Returns:
            Move data dictionary or None if not found.
        """
        return self.moves.get(move_name.upper())

    def get_by_id(self, move_id: int) -> dict | None:
        """Get move data by ID.

        Args:
            move_id: The move ID (1-165).

        Returns:
            Move data dictionary or None if not found.
        """
        for move in self.moves.values():
            if move.get("id") == move_id:
                return move
        return None

    def get_tm_move(self, tm_number: str | int) -> dict | None:
        """Get the move taught by a TM.

        Args:
            tm_number: TM number (e.g., 24 or "TM24").

        Returns:
            Move data or None if not found.
        """
        if isinstance(tm_number, int):
            tm_key = f"TM{tm_number:02d}"
        else:
            tm_key = tm_number.upper()
        move_name = self.tm_hm_mapping.get(tm_key)
        if move_name:
            return self.get(move_name)
        return None

    def get_hm_move(self, hm_number: str | int) -> dict | None:
        """Get the move taught by an HM.

        Args:
            hm_number: HM number (e.g., 1 or "HM01").

        Returns:
            Move data or None if not found.
        """
        if isinstance(hm_number, int):
            hm_key = f"HM{hm_number:02d}"
        else:
            hm_key = hm_number.upper()
        move_name = self.tm_hm_mapping.get(hm_key)
        if move_name:
            return self.get(move_name)
        return None

    def get_moves_by_type(self, type_name: str) -> list[dict]:
        """Get all moves of a specific type.

        Args:
            type_name: The type name (e.g., "FIRE").

        Returns:
            List of move data dictionaries.
        """
        type_upper = type_name.upper()
        return [m for m in self.moves.values() if m.get("type") == type_upper]

    def get_moves_by_category(self, category: str) -> list[dict]:
        """Get all moves of a specific category.

        Args:
            category: PHYSICAL, SPECIAL, or STATUS.

        Returns:
            List of move data dictionaries.
        """
        cat_upper = category.upper()
        return [m for m in self.moves.values() if m.get("category") == cat_upper]

    def get_damaging_moves(self) -> list[dict]:
        """Get all moves that deal damage (power > 0).

        Returns:
            List of move data dictionaries.
        """
        return [m for m in self.moves.values() if m.get("power", 0) > 0]

    def get_status_moves(self) -> list[dict]:
        """Get all status moves (power = 0).

        Returns:
            List of move data dictionaries.
        """
        return [m for m in self.moves.values() if m.get("category") == "STATUS"]

    def is_high_crit(self, move_name: str) -> bool:
        """Check if a move has high critical hit ratio.

        Args:
            move_name: The move name.

        Returns:
            True if the move has high crit rate.
        """
        move = self.get(move_name)
        return move.get("high_crit", False) if move else False

    def get_all_tms(self) -> list[str]:
        """Get all TM numbers.

        Returns:
            List of TM identifiers (e.g., ["TM01", "TM02", ...]).
        """
        return sorted([k for k in self.tm_hm_mapping.keys() if k.startswith("TM")])

    def get_all_hms(self) -> list[str]:
        """Get all HM numbers.

        Returns:
            List of HM identifiers (e.g., ["HM01", "HM02", ...]).
        """
        return sorted([k for k in self.tm_hm_mapping.keys() if k.startswith("HM")])
