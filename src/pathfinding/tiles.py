"""Tile types and movement costs for pathfinding."""

from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

# Default path for map data
DEFAULT_MAPS_PATH = Path(__file__).parent.parent.parent / "data" / "maps"


class TileType(IntEnum):
    """Tile types affecting pathfinding."""

    BLOCKED = 0  # Impassable terrain
    WALKABLE = 1  # Normal ground
    GRASS = 2  # Wild encounter zones
    WATER = 3  # Requires SURF
    CUT_TREE = 4  # Requires CUT
    STRENGTH_BOULDER = 5  # Requires STRENGTH
    LEDGE_DOWN = 6  # One-way jump down
    LEDGE_LEFT = 7  # One-way jump left
    LEDGE_RIGHT = 8  # One-way jump right
    WARP = 9  # Map transition tile
    TRAINER_VISION = 10  # Virtual tile for trainer line-of-sight


@dataclass
class TileWeights:
    """Configurable weights for pathfinding preferences."""

    walkable: float = 1.0
    grass: float = 3.0  # Penalize for encounter avoidance
    water: float = 1.5  # Slight penalty for needing HM
    cut_tree: float = 2.0  # Penalty for HM usage
    strength_boulder: float = 3.0  # Higher penalty (positioning required)
    trainer_adjacent: float = 100.0  # Heavy penalty for trainer LOS

    @classmethod
    def avoid_encounters(cls) -> "TileWeights":
        """Weights optimized for avoiding wild encounters."""
        return cls(grass=5.0)

    @classmethod
    def seek_encounters(cls) -> "TileWeights":
        """Weights for when we want wild encounters (grinding)."""
        return cls(grass=0.5)  # Prefer grass

    @classmethod
    def speed_run(cls) -> "TileWeights":
        """Weights for fastest path regardless of encounters."""
        return cls(grass=1.0, trainer_adjacent=1000.0)


# Base tile weights (infinite = impassable)
BASE_TILE_WEIGHTS: dict[TileType, float] = {
    TileType.BLOCKED: float("inf"),
    TileType.WALKABLE: 1.0,
    TileType.GRASS: 3.0,
    TileType.WATER: float("inf"),  # Blocked without SURF
    TileType.CUT_TREE: float("inf"),  # Blocked without CUT
    TileType.STRENGTH_BOULDER: float("inf"),  # Blocked without STRENGTH
    TileType.LEDGE_DOWN: 1.0,  # One-way (checked separately)
    TileType.LEDGE_LEFT: 1.0,
    TileType.LEDGE_RIGHT: 1.0,
    TileType.WARP: 1.0,
    TileType.TRAINER_VISION: 100.0,
}


def get_tile_weight(
    tile_type: TileType,
    hms_available: list[str] | None = None,
    weights: TileWeights | None = None,
) -> float:
    """Get movement cost for a tile.

    Args:
        tile_type: The type of tile
        hms_available: List of HM names available (e.g., ["CUT", "SURF"])
        weights: Custom weight preferences

    Returns:
        Movement cost (float('inf') if impassable)
    """
    hms = set(hm.upper() for hm in (hms_available or []))
    w = weights or TileWeights()

    # Handle HM-clearable obstacles
    if tile_type == TileType.WATER:
        if "SURF" in hms:
            return w.water
        return float("inf")

    if tile_type == TileType.CUT_TREE:
        if "CUT" in hms:
            return w.cut_tree
        return float("inf")

    if tile_type == TileType.STRENGTH_BOULDER:
        if "STRENGTH" in hms:
            return w.strength_boulder
        return float("inf")

    # Grass weight preference
    if tile_type == TileType.GRASS:
        return w.grass

    # Trainer vision
    if tile_type == TileType.TRAINER_VISION:
        return w.trainer_adjacent

    # Default weights
    return BASE_TILE_WEIGHTS.get(tile_type, float("inf"))


def can_traverse_ledge(ledge_type: TileType, direction: str) -> bool:
    """Check if a ledge can be traversed in the given direction.

    Ledges are one-way - you can only jump in the direction they allow.

    Args:
        ledge_type: The ledge tile type
        direction: Movement direction (UP, DOWN, LEFT, RIGHT)

    Returns:
        True if the ledge allows movement in that direction
    """
    ledge_directions = {
        TileType.LEDGE_DOWN: "DOWN",
        TileType.LEDGE_LEFT: "LEFT",
        TileType.LEDGE_RIGHT: "RIGHT",
    }
    return ledge_directions.get(ledge_type) == direction.upper()


def is_passable(
    tile_type: TileType,
    direction: str | None = None,
    hms_available: list[str] | None = None,
) -> bool:
    """Check if a tile is passable.

    Args:
        tile_type: The type of tile
        direction: Movement direction (needed for ledge checks)
        hms_available: List of available HMs

    Returns:
        True if the tile can be traversed
    """
    # Always blocked
    if tile_type == TileType.BLOCKED:
        return False

    # Ledge checks
    if tile_type in (TileType.LEDGE_DOWN, TileType.LEDGE_LEFT, TileType.LEDGE_RIGHT):
        if direction:
            return can_traverse_ledge(tile_type, direction)
        return False  # Can't enter ledge without direction

    # HM requirements
    hms = set(hm.upper() for hm in (hms_available or []))

    if tile_type == TileType.WATER:
        return "SURF" in hms

    if tile_type == TileType.CUT_TREE:
        return "CUT" in hms

    if tile_type == TileType.STRENGTH_BOULDER:
        return "STRENGTH" in hms

    return True


def classify_tile(
    tile_id: int,
    walkable_tiles: set[int],
    grass_tile: int | None = None,
) -> TileType:
    """Classify a tile ID into a TileType.

    Args:
        tile_id: The numeric tile ID from map data
        walkable_tiles: Set of tile IDs that are walkable for this tileset
        grass_tile: The grass tile ID for this tileset (if any)

    Returns:
        The TileType classification
    """
    # Check if it's grass
    if grass_tile is not None and tile_id == grass_tile:
        return TileType.GRASS

    # Check if it's walkable
    if tile_id in walkable_tiles:
        return TileType.WALKABLE

    # Otherwise it's blocked
    return TileType.BLOCKED
