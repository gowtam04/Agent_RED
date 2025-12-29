"""Pokemon data accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to pokemon data
DEFAULT_POKEMON_PATH = Path(__file__).parent.parent.parent / "data" / "pokemon.json"


class PokemonData(KnowledgeBase):
    """Accessor for Pokemon species data.

    Provides access to all 151 Gen 1 Pokemon with properties including:
    - Base stats (HP, Attack, Defense, Speed, Special)
    - Types
    - Evolutions
    - Level-up learnsets
    - TM/HM compatibility
    """

    def __init__(self, data_path: Path = DEFAULT_POKEMON_PATH):
        """Initialize the Pokemon accessor.

        Args:
            data_path: Path to pokemon.json file.
        """
        super().__init__(data_path)

    def get(self, pokemon_name: str) -> dict | None:
        """Get Pokemon data by name.

        Args:
            pokemon_name: The Pokemon name (e.g., "PIKACHU").

        Returns:
            Pokemon data dictionary or None if not found.
        """
        return self.data.get(pokemon_name.upper())

    def get_by_dex_number(self, dex_number: int) -> dict | None:
        """Get Pokemon data by Pokedex number.

        Args:
            dex_number: The Pokedex number (1-151).

        Returns:
            Pokemon data dictionary or None if not found.
        """
        for pokemon in self.data.values():
            if pokemon.get("dex_number") == dex_number:
                return pokemon
        return None

    def get_base_stat_total(self, pokemon_name: str) -> int:
        """Get the base stat total for a Pokemon.

        Args:
            pokemon_name: The Pokemon name.

        Returns:
            Sum of all base stats, or 0 if not found.
        """
        pokemon = self.get(pokemon_name)
        if not pokemon:
            return 0
        stats = pokemon.get("base_stats", {})
        return sum(stats.values())

    def get_types(self, pokemon_name: str) -> list[str]:
        """Get the types for a Pokemon.

        Args:
            pokemon_name: The Pokemon name.

        Returns:
            List of types (1 or 2 elements).
        """
        pokemon = self.get(pokemon_name)
        return pokemon.get("types", []) if pokemon else []

    def has_type(self, pokemon_name: str, type_name: str) -> bool:
        """Check if a Pokemon has a specific type.

        Args:
            pokemon_name: The Pokemon name.
            type_name: The type to check for.

        Returns:
            True if the Pokemon has the type.
        """
        types = self.get_types(pokemon_name)
        return type_name.upper() in types

    def get_evolution(self, pokemon_name: str) -> list[dict]:
        """Get evolution data for a Pokemon.

        Args:
            pokemon_name: The Pokemon name.

        Returns:
            List of evolution dictionaries with 'method', 'to', and optionally
            'level' or 'item'.
        """
        pokemon = self.get(pokemon_name)
        return pokemon.get("evolutions", []) if pokemon else []

    def get_pre_evolution(self, pokemon_name: str) -> str | None:
        """Get the pre-evolution of a Pokemon.

        Args:
            pokemon_name: The Pokemon name.

        Returns:
            Name of the pre-evolution, or None if this is a base form.
        """
        name_upper = pokemon_name.upper()
        for name, pokemon in self.data.items():
            for evo in pokemon.get("evolutions", []):
                if evo.get("to") == name_upper:
                    return name
        return None

    def get_learnset(self, pokemon_name: str) -> list[dict]:
        """Get the level-up learnset for a Pokemon.

        Args:
            pokemon_name: The Pokemon name.

        Returns:
            List of dicts with 'level' and 'move' keys.
        """
        pokemon = self.get(pokemon_name)
        return pokemon.get("learnset", []) if pokemon else []

    def learns_move_by_level(self, pokemon_name: str, move_name: str) -> int | None:
        """Check if a Pokemon learns a move by leveling up.

        Args:
            pokemon_name: The Pokemon name.
            move_name: The move name.

        Returns:
            The level the move is learned, or None if not learned by level.
        """
        learnset = self.get_learnset(pokemon_name)
        for entry in learnset:
            if entry.get("move") == move_name.upper():
                return entry.get("level")
        return None

    def can_learn_tm(self, pokemon_name: str, tm: str | int) -> bool:
        """Check if a Pokemon can learn a TM.

        Args:
            pokemon_name: The Pokemon name.
            tm: TM number (e.g., 24 or "TM24").

        Returns:
            True if the Pokemon can learn the TM.
        """
        pokemon = self.get(pokemon_name)
        if not pokemon:
            return False

        if isinstance(tm, int):
            tm_key = f"TM{tm:02d}"
        else:
            tm_key = tm.upper()

        return tm_key in pokemon.get("tm_compatibility", [])

    def can_learn_hm(self, pokemon_name: str, hm: str | int) -> bool:
        """Check if a Pokemon can learn an HM.

        Args:
            pokemon_name: The Pokemon name.
            hm: HM number (e.g., 1 or "HM01").

        Returns:
            True if the Pokemon can learn the HM.
        """
        pokemon = self.get(pokemon_name)
        if not pokemon:
            return False

        if isinstance(hm, int):
            hm_key = f"HM{hm:02d}"
        else:
            hm_key = hm.upper()

        return hm_key in pokemon.get("hm_compatibility", [])

    def get_pokemon_by_type(self, type_name: str) -> list[dict]:
        """Get all Pokemon of a specific type.

        Args:
            type_name: The type name (e.g., "FIRE").

        Returns:
            List of Pokemon data dictionaries.
        """
        type_upper = type_name.upper()
        return [p for p in self.data.values() if type_upper in p.get("types", [])]

    def get_all_pokemon(self) -> list[dict]:
        """Get all Pokemon sorted by Pokedex number.

        Returns:
            List of all Pokemon data dictionaries.
        """
        return sorted(self.data.values(), key=lambda x: x.get("dex_number", 0))

    def get_fully_evolved(self) -> list[dict]:
        """Get all fully evolved Pokemon (no further evolutions).

        Returns:
            List of fully evolved Pokemon data dictionaries.
        """
        return [p for p in self.data.values() if not p.get("evolutions")]

    def get_base_forms(self) -> list[dict]:
        """Get all base form Pokemon (no pre-evolutions).

        Returns:
            List of base form Pokemon data dictionaries.
        """
        # Collect all Pokemon that are evolved-to
        evolved_names = set()
        for pokemon in self.data.values():
            for evo in pokemon.get("evolutions", []):
                evolved_names.add(evo.get("to"))

        # Return Pokemon not in that set
        return [p for name, p in self.data.items() if name not in evolved_names]
