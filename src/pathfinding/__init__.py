"""Pathfinding module for Pokemon Red navigation.

This module provides A* pathfinding for single-map and cross-map routing,
with support for tile weights, HM obstacles, and trainer avoidance.

Example usage:
    from src.pathfinding import CrossMapRouter, TileWeights

    router = CrossMapRouter()
    result = router.find_path(
        from_map="PALLETTOWN",
        from_x=5,
        from_y=5,
        to_map="VIRIDIANCITY",
        hms_available=["CUT"],
        weights=TileWeights.avoid_encounters(),
    )

    if result.success:
        print(f"Path found: {result.total_moves} moves")
        for map_id, moves in result.segments:
            print(f"  {map_id}: {len(moves)} moves")
"""

from .astar import (
    PathResult,
    astar,
    find_nearest,
    heuristic,
    path_to_moves,
)
from .cross_map import (
    CrossMapPath,
    CrossMapRouter,
    MapTransition,
)
from .graph import (
    Edge,
    MapGraph,
    Node,
)
from .tiles import (
    BASE_TILE_WEIGHTS,
    TileType,
    TileWeights,
    can_traverse_ledge,
    classify_tile,
    get_tile_weight,
    is_passable,
)
from .trainer_vision import (
    Trainer,
    calculate_vision_zone,
    get_all_trainer_zones,
    get_safe_positions_around_trainer,
    get_vision_tiles,
    is_in_vision,
)

__all__ = [
    # Tiles
    "TileType",
    "TileWeights",
    "BASE_TILE_WEIGHTS",
    "get_tile_weight",
    "can_traverse_ledge",
    "is_passable",
    "classify_tile",
    # Graph
    "Node",
    "Edge",
    "MapGraph",
    # A*
    "PathResult",
    "astar",
    "find_nearest",
    "heuristic",
    "path_to_moves",
    # Cross-map
    "MapTransition",
    "CrossMapPath",
    "CrossMapRouter",
    # Trainer vision
    "Trainer",
    "get_vision_tiles",
    "calculate_vision_zone",
    "is_in_vision",
    "get_all_trainer_zones",
    "get_safe_positions_around_trainer",
]


def find_path(
    from_map: str,
    from_x: int,
    from_y: int,
    to_map: str,
    to_x: int | None = None,
    to_y: int | None = None,
    hms_available: list[str] | None = None,
    avoid_grass: bool = True,
    avoid_trainers: bool = True,
    defeated_trainers: set[str] | None = None,
) -> CrossMapPath:
    """High-level pathfinding function.

    Convenience function that creates a CrossMapRouter and finds a path.

    Args:
        from_map: Starting map ID
        from_x: Starting X coordinate
        from_y: Starting Y coordinate
        to_map: Destination map ID
        to_x: Destination X (optional)
        to_y: Destination Y (optional)
        hms_available: List of available HMs
        avoid_grass: Whether to prefer paths with less grass
        avoid_trainers: Whether to avoid trainer line-of-sight
        defeated_trainers: Set of already-defeated trainer IDs

    Returns:
        CrossMapPath with route information
    """
    weights = TileWeights()
    if avoid_grass:
        weights.grass = 5.0
    if avoid_trainers:
        weights.trainer_adjacent = 100.0
    else:
        weights.trainer_adjacent = 1.0

    router = CrossMapRouter()
    return router.find_path(
        from_map=from_map,
        from_x=from_x,
        from_y=from_y,
        to_map=to_map,
        to_x=to_x,
        to_y=to_y,
        hms_available=hms_available,
        weights=weights,
        defeated_trainers=defeated_trainers,
    )
