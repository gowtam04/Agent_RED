"""Map graph representation for pathfinding."""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .tiles import (
    TileType,
    TileWeights,
    get_tile_weight,
    is_passable,
)

# Default path for map data
DEFAULT_MAPS_PATH = Path(__file__).parent.parent.parent / "data" / "maps"


@dataclass(frozen=True)
class Node:
    """A node in the pathfinding graph representing a tile position."""

    x: int
    y: int

    def __hash__(self) -> int:
        return hash((self.x, self.y))

    def __lt__(self, other: "Node") -> bool:
        """Allow comparison for heap operations."""
        return (self.x, self.y) < (other.x, other.y)


@dataclass
class Edge:
    """An edge between nodes with movement cost."""

    destination: Node
    cost: float
    direction: str  # UP, DOWN, LEFT, RIGHT
    requires_hm: str | None = None


class MapGraph:
    """Navigable graph for a single map.

    Loads map data and provides neighbor iteration for A* pathfinding.
    """

    # Direction vectors: (dx, dy, name)
    DIRECTIONS = [
        (0, -1, "UP"),
        (0, 1, "DOWN"),
        (-1, 0, "LEFT"),
        (1, 0, "RIGHT"),
    ]

    def __init__(
        self,
        map_id: str,
        maps_path: Path = DEFAULT_MAPS_PATH,
    ):
        """Initialize the map graph.

        Args:
            map_id: The map identifier (e.g., "PALLETTOWN")
            maps_path: Path to the maps data directory
        """
        self.map_id = map_id
        self._maps_path = maps_path
        self._data: dict[str, Any] = {}
        self._walkable_tiles: set[int] = set()
        self._grass_tile: int | None = None
        self._trainer_zones: set[tuple[int, int]] = set()

        self._load_map_data()

    def _load_map_data(self) -> None:
        """Load map data from JSON file."""
        map_file = self._maps_path / f"{self.map_id}.json"
        if not map_file.exists():
            # Try without underscores
            map_file = self._maps_path / f"{self.map_id.replace('_', '')}.json"

        if map_file.exists():
            with open(map_file) as f:
                self._data = json.load(f)
            self._walkable_tiles = set(self._data.get("walkable_tiles", []))
            self._grass_tile = self._data.get("grass_tile")

    @property
    def width(self) -> int:
        """Map width in tiles."""
        return self._data.get("width", 0)

    @property
    def height(self) -> int:
        """Map height in tiles."""
        return self._data.get("height", 0)

    @property
    def tileset(self) -> str | None:
        """The tileset used by this map."""
        return self._data.get("tileset")

    @property
    def connections(self) -> dict[str, dict]:
        """Map connections to adjacent maps."""
        return self._data.get("connections", {})

    @property
    def warps(self) -> list[dict]:
        """Warp points on this map."""
        return self._data.get("warps", [])

    @property
    def trainers(self) -> list[dict]:
        """Trainers on this map."""
        return self._data.get("trainers", [])

    def set_trainer_zones(self, zones: set[tuple[int, int]]) -> None:
        """Set tiles in trainer line-of-sight for avoidance.

        Args:
            zones: Set of (x, y) tiles that are in trainer vision
        """
        self._trainer_zones = zones

    def in_bounds(self, x: int, y: int) -> bool:
        """Check if coordinates are within map bounds."""
        return 0 <= x < self.width and 0 <= y < self.height

    def get_tile_type(self, x: int, y: int) -> TileType:
        """Get the tile type at a position.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            The TileType at this position
        """
        if not self.in_bounds(x, y):
            return TileType.BLOCKED

        # Check trainer vision zones
        if (x, y) in self._trainer_zones:
            return TileType.TRAINER_VISION

        # For now, we don't have per-tile data, so we check if position
        # would be on a walkable tile based on the tileset info.
        # A full implementation would need actual tile grid data.
        #
        # For now, assume all tiles are walkable unless they're in trainer zones.
        # The actual collision will be handled when we have block data.
        return TileType.WALKABLE

    def neighbors(
        self,
        node: Node,
        hms_available: list[str] | None = None,
        weights: TileWeights | None = None,
    ) -> Iterator[Edge]:
        """Yield valid neighboring nodes with their edge costs.

        Args:
            node: The current node
            hms_available: List of available HMs
            weights: Custom weight preferences

        Yields:
            Edge objects for each valid neighbor
        """
        weights = weights or TileWeights()

        for dx, dy, direction in self.DIRECTIONS:
            nx, ny = node.x + dx, node.y + dy

            # Check bounds
            if not self.in_bounds(nx, ny):
                continue

            # Get tile type
            tile_type = self.get_tile_type(nx, ny)

            # Check if passable
            if not is_passable(tile_type, direction, hms_available):
                continue

            # Calculate cost
            cost = get_tile_weight(tile_type, hms_available, weights)

            # Skip if impassable
            if cost == float("inf"):
                continue

            # Determine HM requirement
            requires_hm = None
            if tile_type == TileType.WATER:
                requires_hm = "SURF"
            elif tile_type == TileType.CUT_TREE:
                requires_hm = "CUT"
            elif tile_type == TileType.STRENGTH_BOULDER:
                requires_hm = "STRENGTH"

            yield Edge(
                destination=Node(nx, ny),
                cost=cost,
                direction=direction,
                requires_hm=requires_hm,
            )

    def get_warp_at(self, x: int, y: int) -> dict | None:
        """Get warp destination if standing on a warp tile.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Warp data dict or None
        """
        for warp in self.warps:
            if warp.get("x") == x and warp.get("y") == y:
                return {
                    "destination_map": warp.get("destination_map"),
                    "destination_warp_id": warp.get("destination_warp_id"),
                }
        return None

    def get_connection_at(self, x: int, y: int) -> dict | None:
        """Get map connection if at map edge.

        Args:
            x: X coordinate
            y: Y coordinate

        Returns:
            Connection data dict or None
        """
        # Check each direction
        if y < 0 and "NORTH" in self.connections:
            return {
                "direction": "NORTH",
                "map": self.connections["NORTH"]["map"],
                "offset": self.connections["NORTH"].get("offset", 0),
            }
        if y >= self.height and "SOUTH" in self.connections:
            return {
                "direction": "SOUTH",
                "map": self.connections["SOUTH"]["map"],
                "offset": self.connections["SOUTH"].get("offset", 0),
            }
        if x < 0 and "WEST" in self.connections:
            return {
                "direction": "WEST",
                "map": self.connections["WEST"]["map"],
                "offset": self.connections["WEST"].get("offset", 0),
            }
        if x >= self.width and "EAST" in self.connections:
            return {
                "direction": "EAST",
                "map": self.connections["EAST"]["map"],
                "offset": self.connections["EAST"].get("offset", 0),
            }
        return None
