"""Map data accessor."""

import json
from pathlib import Path

from .base import KnowledgeBase


# Default path to maps data
DEFAULT_MAPS_PATH = Path(__file__).parent.parent.parent / "data" / "maps"


class MapData(KnowledgeBase):
    """Accessor for Pokemon map data.

    Maps are stored as individual JSON files in data/maps/.
    """

    def __init__(self, data_path: Path = DEFAULT_MAPS_PATH):
        """Initialize the maps accessor.

        Args:
            data_path: Path to maps directory.
        """
        self.data_path = data_path
        self._index: dict | None = None
        self._cache: dict[str, dict] = {}

    def load(self) -> None:
        """Load the map index."""
        index_path = self.data_path / "index.json"
        with open(index_path) as f:
            self._index = json.load(f)

    @property
    def data(self) -> dict:
        """Get the map index."""
        if self._index is None:
            self.load()
        return self._index  # type: ignore

    def get(self, map_id: str) -> dict | None:
        """Get map data by ID.

        Args:
            map_id: The map ID (e.g., "VIRIDIANFOREST").

        Returns:
            Map data dictionary or None if not found.
        """
        map_id_upper = map_id.upper()
        if map_id_upper in self._cache:
            return self._cache[map_id_upper]

        map_file = self.data_path / f"{map_id_upper}.json"
        if not map_file.exists():
            return None

        with open(map_file) as f:
            data = json.load(f)
        self._cache[map_id_upper] = data
        return data

    def get_all_maps(self) -> list[str]:
        """Get all map IDs.

        Returns:
            List of map IDs.
        """
        return self.data.get("maps", [])

    def get_warps(self, map_id: str) -> list[dict]:
        """Get warps for a map.

        Args:
            map_id: The map ID.

        Returns:
            List of warp dictionaries.
        """
        map_data = self.get(map_id)
        return map_data.get("warps", []) if map_data else []

    def get_items(self, map_id: str) -> list[dict]:
        """Get items on a map.

        Args:
            map_id: The map ID.

        Returns:
            List of item dictionaries.
        """
        map_data = self.get(map_id)
        return map_data.get("items", []) if map_data else []

    def get_trainers(self, map_id: str) -> list[dict]:
        """Get trainers on a map.

        Args:
            map_id: The map ID.

        Returns:
            List of trainer dictionaries.
        """
        map_data = self.get(map_id)
        return map_data.get("trainers", []) if map_data else []

    def find_warp_destination(self, from_map: str, warp_id: int) -> tuple[str, int] | None:
        """Find where a warp leads.

        Args:
            from_map: The source map ID.
            warp_id: The warp ID on the source map.

        Returns:
            Tuple of (destination_map, destination_warp_id) or None.
        """
        warps = self.get_warps(from_map)
        for i, warp in enumerate(warps):
            if i == warp_id:
                return (warp.get("destination_map"), warp.get("destination_warp_id"))
        return None

    def get_connected_maps(self, map_id: str) -> list[str]:
        """Get all maps connected via warps.

        Args:
            map_id: The map ID.

        Returns:
            List of connected map IDs.
        """
        warps = self.get_warps(map_id)
        return list(set(w.get("destination_map") for w in warps if w.get("destination_map")))
