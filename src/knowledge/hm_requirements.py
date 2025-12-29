"""HM requirements accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to HM requirements data
DEFAULT_HM_PATH = Path(__file__).parent.parent.parent / "data" / "hm_requirements.json"


class HMRequirements(KnowledgeBase):
    """Accessor for HM field move requirements.

    Provides access to badge and item requirements for using HM moves
    outside of battle.
    """

    def __init__(self, data_path: Path = DEFAULT_HM_PATH):
        """Initialize the HM requirements accessor.

        Args:
            data_path: Path to hm_requirements.json file.
        """
        super().__init__(data_path)

    def get(self, hm_name: str) -> dict | None:
        """Get requirements for an HM move.

        Args:
            hm_name: The HM move name (e.g., "CUT", "SURF").

        Returns:
            Requirements dictionary or None if not found.
        """
        return self.data.get(hm_name.upper())

    def can_use(self, hm_name: str, badges: int, has_items: set[str] | None = None) -> bool:
        """Check if an HM can be used with current badges and items.

        Args:
            hm_name: The HM move name.
            badges: Bitmask of owned badges (bit 0 = Boulder, etc.).
            has_items: Set of owned item names (for special requirements).

        Returns:
            True if the HM can be used.
        """
        req = self.get(hm_name)
        if not req:
            return False

        # Check badge requirement
        badge_name = req.get("badge_required")
        if badge_name:
            badge_index = self._get_badge_index(badge_name)
            if badge_index is not None and not (badges & (1 << badge_index)):
                return False

        # Check item requirements (e.g., POKE_FLUTE for SURF to wake Snorlax)
        item_required = req.get("item_required")
        if item_required:
            if has_items is None or item_required not in has_items:
                return False

        return True

    def _get_badge_index(self, badge_name: str) -> int | None:
        """Get badge bit index from badge name.

        Args:
            badge_name: Badge name (e.g., "CASCADE").

        Returns:
            Bit index (0-7) or None if invalid.
        """
        badge_order = [
            "BOULDER",  # 0 - Brock
            "CASCADE",  # 1 - Misty
            "THUNDER",  # 2 - Lt. Surge
            "RAINBOW",  # 3 - Erika
            "SOUL",     # 4 - Koga
            "MARSH",    # 5 - Sabrina
            "VOLCANO",  # 6 - Blaine
            "EARTH",    # 7 - Giovanni
        ]
        badge_upper = badge_name.upper()
        if badge_upper in badge_order:
            return badge_order.index(badge_upper)
        return None

    def get_badge_for_hm(self, hm_name: str) -> str | None:
        """Get the badge required to use an HM.

        Args:
            hm_name: The HM move name.

        Returns:
            Badge name or None if no badge required.
        """
        req = self.get(hm_name)
        return req.get("badge_required") if req else None

    def get_all_hms(self) -> list[str]:
        """Get all HM move names.

        Returns:
            List of HM move names.
        """
        return list(self.data.keys())

    def get_hms_available(self, badges: int) -> list[str]:
        """Get all HMs available with current badges.

        Args:
            badges: Bitmask of owned badges.

        Returns:
            List of HM names that can be used.
        """
        available = []
        for hm_name in self.data.keys():
            if self.can_use(hm_name, badges):
                available.append(hm_name)
        return available
