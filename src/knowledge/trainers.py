"""Trainer data accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to trainers data
DEFAULT_TRAINERS_PATH = Path(__file__).parent.parent.parent / "data" / "trainers.json"


class TrainerData(KnowledgeBase):
    """Accessor for trainer party data."""

    def __init__(self, data_path: Path = DEFAULT_TRAINERS_PATH):
        """Initialize the trainers accessor.

        Args:
            data_path: Path to trainers.json file.
        """
        super().__init__(data_path)

    def get(self, trainer_id: str) -> dict | None:
        """Get trainer data by ID.

        Args:
            trainer_id: The trainer ID (e.g., "BROCK_1").

        Returns:
            Trainer data dictionary or None if not found.
        """
        return self.data.get(trainer_id.upper())

    def get_team(self, trainer_id: str) -> list[dict]:
        """Get a trainer's team.

        Args:
            trainer_id: The trainer ID.

        Returns:
            List of dicts with 'species' and 'level' keys.
        """
        trainer = self.get(trainer_id)
        return trainer.get("team", []) if trainer else []

    def get_trainers_by_class(self, class_name: str) -> list[dict]:
        """Get all trainers of a specific class.

        Args:
            class_name: The trainer class (e.g., "BUGCATCHER").

        Returns:
            List of trainer data dictionaries.
        """
        class_upper = class_name.upper()
        return [t for t in self.data.values() if t.get("class") == class_upper]

    def get_boss_trainers(self) -> list[dict]:
        """Get all boss trainers (Gym Leaders, Elite Four, Rivals).

        Returns:
            List of boss trainer data dictionaries.
        """
        return [t for t in self.data.values() if t.get("is_boss")]

    def get_gym_leaders(self) -> list[dict]:
        """Get all Gym Leader trainers.

        Returns:
            List of Gym Leader trainer data dictionaries.
        """
        return [t for t in self.data.values()
                if t.get("boss_type") == "GYM_LEADER"]

    def get_elite_four(self) -> list[dict]:
        """Get all Elite Four trainers.

        Returns:
            List of Elite Four trainer data dictionaries.
        """
        return [t for t in self.data.values()
                if t.get("boss_type") == "ELITE_FOUR"]

    def get_rival_battles(self) -> list[dict]:
        """Get all Rival battle trainers.

        Returns:
            List of Rival trainer data dictionaries.
        """
        return [t for t in self.data.values()
                if t.get("boss_type") == "RIVAL"]

    def get_max_level(self, trainer_id: str) -> int:
        """Get the maximum level Pokemon in a trainer's team.

        Args:
            trainer_id: The trainer ID.

        Returns:
            Maximum level, or 0 if not found.
        """
        team = self.get_team(trainer_id)
        if not team:
            return 0
        return max(p.get("level", 0) for p in team)

    def get_badge_reward(self, trainer_id: str) -> str | None:
        """Get the badge reward for defeating a Gym Leader.

        Args:
            trainer_id: The trainer ID.

        Returns:
            Badge name or None if not a Gym Leader.
        """
        trainer = self.get(trainer_id)
        return trainer.get("badge_reward") if trainer else None
