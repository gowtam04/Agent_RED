"""Type effectiveness chart accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to type chart data
DEFAULT_TYPE_CHART_PATH = Path(__file__).parent.parent.parent / "data" / "type_chart.json"


class TypeChart(KnowledgeBase):
    """Accessor for Pokemon type effectiveness chart.

    The chart maps attacking types to defending types with effectiveness multipliers:
    - 2.0: Super effective
    - 0.5: Not very effective
    - 0.0: No effect
    - 1.0: Normal effectiveness (implicit, not stored)

    Gen 1 quirks are preserved:
    - Ghost vs Psychic: 0.0 (bug, should be 2.0)
    """

    def __init__(self, data_path: Path = DEFAULT_TYPE_CHART_PATH):
        """Initialize the type chart accessor.

        Args:
            data_path: Path to type_chart.json file.
        """
        super().__init__(data_path)

    def get(self, attack_type: str) -> dict[str, float] | None:
        """Get all effectiveness matchups for an attacking type.

        Args:
            attack_type: The attacking type (e.g., "FIRE").

        Returns:
            Dictionary mapping defending types to multipliers, or None if type not found.
        """
        return self.data.get(attack_type.upper())

    def get_effectiveness(self, attack_type: str, defend_types: list[str]) -> float:
        """Calculate total effectiveness multiplier for an attack.

        Args:
            attack_type: The attacking type (e.g., "FIRE").
            defend_types: List of defending types (e.g., ["GRASS", "POISON"]).

        Returns:
            Total effectiveness multiplier (product of individual matchups).
            Returns 1.0 for neutral matchups.
        """
        multiplier = 1.0
        attack_matchups = self.data.get(attack_type.upper(), {})

        for defend_type in defend_types:
            defend_upper = defend_type.upper()
            if defend_upper in attack_matchups:
                multiplier *= attack_matchups[defend_upper]

        return multiplier

    def is_super_effective(self, attack_type: str, defend_types: list[str]) -> bool:
        """Check if an attack type is super effective against defending types.

        Args:
            attack_type: The attacking type.
            defend_types: List of defending types.

        Returns:
            True if effectiveness > 1.0.
        """
        return self.get_effectiveness(attack_type, defend_types) > 1.0

    def is_not_very_effective(self, attack_type: str, defend_types: list[str]) -> bool:
        """Check if an attack type is not very effective against defending types.

        Args:
            attack_type: The attacking type.
            defend_types: List of defending types.

        Returns:
            True if 0 < effectiveness < 1.0.
        """
        eff = self.get_effectiveness(attack_type, defend_types)
        return 0 < eff < 1.0

    def is_immune(self, attack_type: str, defend_types: list[str]) -> bool:
        """Check if defending types are immune to an attack type.

        Args:
            attack_type: The attacking type.
            defend_types: List of defending types.

        Returns:
            True if effectiveness == 0.0.
        """
        return self.get_effectiveness(attack_type, defend_types) == 0.0

    def get_all_types(self) -> list[str]:
        """Get all types in the chart.

        Returns:
            List of all type names.
        """
        all_types = set(self.data.keys())
        for matchups in self.data.values():
            all_types.update(matchups.keys())
        return sorted(all_types)
