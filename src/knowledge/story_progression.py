"""Story progression accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to story progression data
DEFAULT_STORY_PATH = Path(__file__).parent.parent.parent / "data" / "story_progression.json"


class StoryProgression(KnowledgeBase):
    """Accessor for story progression milestones.

    Provides access to the sequence of story events and their requirements.
    """

    def __init__(self, data_path: Path = DEFAULT_STORY_PATH):
        """Initialize the story progression accessor.

        Args:
            data_path: Path to story_progression.json file.
        """
        super().__init__(data_path)
        self._milestones_by_id: dict[str, dict] = {}
        self._build_index()

    def _build_index(self):
        """Build index of milestones by ID."""
        for milestone in self.data.get("milestones", []):
            self._milestones_by_id[milestone["id"]] = milestone

    def get(self, milestone_id: str) -> dict | None:
        """Get a milestone by ID.

        Args:
            milestone_id: The milestone ID (e.g., "get_starter").

        Returns:
            Milestone dictionary or None if not found.
        """
        return self._milestones_by_id.get(milestone_id)

    def get_all_milestones(self) -> list[dict]:
        """Get all milestones in order.

        Returns:
            List of milestone dictionaries.
        """
        return self.data.get("milestones", [])

    def get_milestone_by_order(self, order: int) -> dict | None:
        """Get a milestone by its order number.

        Args:
            order: The order number (1-based).

        Returns:
            Milestone dictionary or None if not found.
        """
        for milestone in self.data.get("milestones", []):
            if milestone.get("order") == order:
                return milestone
        return None

    def get_next_milestone(self, current_id: str) -> dict | None:
        """Get the next milestone after the current one.

        Args:
            current_id: Current milestone ID.

        Returns:
            Next milestone dictionary or None if at end.
        """
        current = self.get(current_id)
        if not current:
            return None

        current_order = current.get("order", 0)
        return self.get_milestone_by_order(current_order + 1)

    def get_prerequisites(self, milestone_id: str) -> list[str]:
        """Get prerequisite milestone IDs.

        Args:
            milestone_id: The milestone ID.

        Returns:
            List of prerequisite milestone IDs.
        """
        milestone = self.get(milestone_id)
        if not milestone:
            return []
        return milestone.get("prerequisites", [])

    def can_attempt(self, milestone_id: str, completed: set[str]) -> bool:
        """Check if a milestone can be attempted.

        Args:
            milestone_id: The milestone ID to check.
            completed: Set of completed milestone IDs.

        Returns:
            True if all prerequisites are met.
        """
        prereqs = self.get_prerequisites(milestone_id)
        return all(p in completed for p in prereqs)

    def get_available_milestones(self, completed: set[str]) -> list[dict]:
        """Get all milestones that can currently be attempted.

        Args:
            completed: Set of completed milestone IDs.

        Returns:
            List of available milestone dictionaries.
        """
        available = []
        for milestone in self.data.get("milestones", []):
            mid = milestone["id"]
            if mid not in completed and self.can_attempt(mid, completed):
                available.append(milestone)
        return available

    def get_location(self, milestone_id: str) -> str | None:
        """Get the map location for a milestone.

        Args:
            milestone_id: The milestone ID.

        Returns:
            Map ID or None if not found.
        """
        milestone = self.get(milestone_id)
        return milestone.get("location") if milestone else None

    def get_milestones_at_location(self, map_id: str) -> list[dict]:
        """Get all milestones at a location.

        Args:
            map_id: The map ID.

        Returns:
            List of milestone dictionaries.
        """
        map_upper = map_id.upper()
        return [
            m for m in self.data.get("milestones", [])
            if m.get("location", "").upper() == map_upper
        ]

    def get_gym_milestones(self) -> list[dict]:
        """Get all gym leader milestones.

        Returns:
            List of gym milestone dictionaries.
        """
        return [
            m for m in self.data.get("milestones", [])
            if m["id"].startswith("gym_")
        ]

    def get_elite_four_milestones(self) -> list[dict]:
        """Get all Elite Four milestones.

        Returns:
            List of Elite Four milestone dictionaries.
        """
        return [
            m for m in self.data.get("milestones", [])
            if m["id"].startswith("elite_") or m["id"] == "champion"
        ]

    def get_milestone_count(self) -> int:
        """Get total number of milestones.

        Returns:
            Number of milestones.
        """
        return len(self.data.get("milestones", []))
