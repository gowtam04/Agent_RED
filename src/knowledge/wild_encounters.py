"""Wild encounter data accessor."""

from pathlib import Path

from .base import KnowledgeBase


# Default path to wild encounters data
DEFAULT_WILD_PATH = Path(__file__).parent.parent.parent / "data" / "wild_encounters.json"


class WildEncounters(KnowledgeBase):
    """Accessor for wild Pokemon encounter data.

    Provides access to grass and water encounter tables for each map.
    """

    def __init__(self, data_path: Path = DEFAULT_WILD_PATH):
        """Initialize the wild encounters accessor.

        Args:
            data_path: Path to wild_encounters.json file.
        """
        super().__init__(data_path)

    def get(self, map_id: str) -> dict | None:
        """Get encounter data for a map.

        Args:
            map_id: The map ID (e.g., "ROUTE1").

        Returns:
            Encounter data dictionary or None if not found.
        """
        return self.data.get(map_id.upper())

    def get_grass_encounters(self, map_id: str) -> dict | None:
        """Get grass encounter data for a map.

        Args:
            map_id: The map ID.

        Returns:
            Grass encounter dict with 'encounter_rate' and 'pokemon' list.
        """
        enc = self.get(map_id)
        return enc.get("grass") if enc else None

    def get_water_encounters(self, map_id: str) -> dict | None:
        """Get water encounter data for a map.

        Args:
            map_id: The map ID.

        Returns:
            Water encounter dict with 'encounter_rate' and 'pokemon' list.
        """
        enc = self.get(map_id)
        return enc.get("water") if enc else None

    def has_wild_pokemon(self, map_id: str) -> bool:
        """Check if a map has any wild Pokemon.

        Args:
            map_id: The map ID.

        Returns:
            True if the map has grass or water encounters.
        """
        enc = self.get(map_id)
        if not enc:
            return False
        return bool(enc.get("grass") or enc.get("water"))

    def get_encounter_rate(self, map_id: str, encounter_type: str = "grass") -> int:
        """Get the encounter rate for a map.

        Args:
            map_id: The map ID.
            encounter_type: "grass" or "water".

        Returns:
            Encounter rate (0-255) or 0 if not found.
        """
        enc = self.get(map_id)
        if not enc:
            return 0
        type_enc = enc.get(encounter_type)
        return type_enc.get("encounter_rate", 0) if type_enc else 0

    def get_pokemon_at_location(self, map_id: str) -> list[str]:
        """Get all Pokemon species available at a location.

        Args:
            map_id: The map ID.

        Returns:
            List of unique Pokemon species names.
        """
        enc = self.get(map_id)
        if not enc:
            return []

        species = set()
        for enc_type in ["grass", "water"]:
            if enc.get(enc_type):
                for p in enc[enc_type].get("pokemon", []):
                    species.add(p["species"])

        return sorted(species)

    def find_pokemon(self, species: str) -> list[dict]:
        """Find all locations where a Pokemon can be caught.

        Args:
            species: The Pokemon species name.

        Returns:
            List of dicts with 'map_id', 'type', 'slot', 'level', 'probability'.
        """
        species_upper = species.upper()
        locations = []

        for map_id, enc in self.data.items():
            for enc_type in ["grass", "water"]:
                if enc.get(enc_type):
                    for p in enc[enc_type].get("pokemon", []):
                        if p["species"] == species_upper:
                            locations.append({
                                "map_id": map_id,
                                "type": enc_type,
                                "slot": p["slot"],
                                "level": p["level"],
                                "probability": p["probability"],
                            })

        return locations

    def get_maps_with_encounters(self) -> list[str]:
        """Get all maps that have wild encounters.

        Returns:
            List of map IDs.
        """
        return list(self.data.keys())
