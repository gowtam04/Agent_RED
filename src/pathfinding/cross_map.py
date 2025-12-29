"""Cross-map routing for multi-map pathfinding."""

import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .astar import astar
from .graph import MapGraph, Node
from .tiles import TileWeights
from .trainer_vision import get_all_trainer_zones

# Default path for map data
DEFAULT_MAPS_PATH = Path(__file__).parent.parent.parent / "data" / "maps"


@dataclass
class MapTransition:
    """A transition between two maps."""

    from_map: str
    from_pos: tuple[int, int]
    to_map: str
    to_pos: tuple[int, int]
    transition_type: str  # "warp" or "connection"


@dataclass
class CrossMapPath:
    """Result of cross-map pathfinding."""

    success: bool
    segments: list[tuple[str, list[str]]] = field(default_factory=list)
    maps_traversed: list[str] = field(default_factory=list)
    total_moves: int = 0
    hms_required: list[str] = field(default_factory=list)
    transitions: list[MapTransition] = field(default_factory=list)


class CrossMapRouter:
    """Routes paths across multiple maps.

    Uses BFS to find the sequence of maps to traverse, then A* to
    find the path within each map segment.
    """

    def __init__(self, maps_path: Path = DEFAULT_MAPS_PATH):
        """Initialize the router.

        Args:
            maps_path: Path to the maps data directory
        """
        self._maps_path = maps_path
        self._map_cache: dict[str, MapGraph] = {}
        self._map_index = self._load_map_index()

    def _load_map_index(self) -> dict[str, Any]:
        """Load the map index for quick lookups."""
        index_path = self._maps_path / "index.json"
        if index_path.exists():
            with open(index_path) as f:
                return json.load(f)
        return {"maps": []}

    def _get_map(self, map_id: str) -> MapGraph:
        """Get or load a map graph.

        Args:
            map_id: The map identifier

        Returns:
            MapGraph for the specified map
        """
        # Normalize map ID
        norm_id = map_id.replace("_", "").upper()

        if norm_id not in self._map_cache:
            self._map_cache[norm_id] = MapGraph(norm_id, self._maps_path)

        return self._map_cache[norm_id]

    def _normalize_map_id(self, map_id: str) -> str:
        """Normalize a map ID to the format used in JSON files."""
        return map_id.replace("_", "").upper()

    def find_path(
        self,
        from_map: str,
        from_x: int,
        from_y: int,
        to_map: str,
        to_x: int | None = None,
        to_y: int | None = None,
        hms_available: list[str] | None = None,
        weights: TileWeights | None = None,
        defeated_trainers: set[str] | None = None,
    ) -> CrossMapPath:
        """Find a path from one map position to another.

        Args:
            from_map: Starting map ID
            from_x: Starting X coordinate
            from_y: Starting Y coordinate
            to_map: Destination map ID
            to_x: Destination X (optional, uses map entrance if not specified)
            to_y: Destination Y (optional)
            hms_available: List of available HMs
            weights: Tile weight preferences
            defeated_trainers: Set of defeated trainer IDs

        Returns:
            CrossMapPath with route information
        """
        hms_available = hms_available or []
        weights = weights or TileWeights()
        defeated_trainers = defeated_trainers or set()

        # Normalize map IDs
        from_map = self._normalize_map_id(from_map)
        to_map = self._normalize_map_id(to_map)

        # Same map - simple A*
        if from_map == to_map:
            return self._single_map_path(
                from_map,
                from_x,
                from_y,
                to_x or from_x,
                to_y or from_y,
                hms_available,
                weights,
                defeated_trainers,
            )

        # Different maps - find map sequence first
        map_sequence = self._find_map_sequence(from_map, to_map, hms_available)

        if not map_sequence:
            return CrossMapPath(success=False)

        # Build detailed path through each map
        return self._build_multi_map_path(
            map_sequence,
            from_x,
            from_y,
            to_x,
            to_y,
            hms_available,
            weights,
            defeated_trainers,
        )

    def _single_map_path(
        self,
        map_id: str,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        hms_available: list[str],
        weights: TileWeights,
        defeated_trainers: set[str],
    ) -> CrossMapPath:
        """Find path within a single map."""
        graph = self._get_map(map_id)

        # Set up trainer avoidance
        if weights.trainer_adjacent > 1:
            zones = get_all_trainer_zones(
                graph.trainers,
                defeated_trainers,
                graph.width,
                graph.height,
            )
            graph.set_trainer_zones(zones)

        start = Node(from_x, from_y)
        goal = Node(to_x, to_y)

        result = astar(graph, start, goal, hms_available, weights)

        if result.success:
            return CrossMapPath(
                success=True,
                segments=[(map_id, result.moves)],
                maps_traversed=[map_id],
                total_moves=len(result.moves),
                hms_required=result.hms_required,
            )

        return CrossMapPath(success=False)

    def _find_map_sequence(
        self,
        from_map: str,
        to_map: str,
        hms_available: list[str],
    ) -> list[str]:
        """Find sequence of maps to traverse using BFS.

        Args:
            from_map: Starting map ID
            to_map: Destination map ID
            hms_available: Available HMs

        Returns:
            List of map IDs from start to goal, or empty list if no path
        """
        queue = deque([(from_map, [from_map])])
        visited = {from_map}

        while queue:
            current_map, path = queue.popleft()

            if current_map == to_map:
                return path

            # Get connected maps
            graph = self._get_map(current_map)
            connected = set()

            # Add connection neighbors
            for direction, conn in graph.connections.items():
                dest_map = self._normalize_map_id(conn.get("map", ""))
                if dest_map:
                    connected.add(dest_map)

            # Add warp destinations
            for warp in graph.warps:
                dest_map = self._normalize_map_id(warp.get("destination_map", ""))
                if dest_map:
                    connected.add(dest_map)

            for next_map in connected:
                if next_map not in visited:
                    visited.add(next_map)
                    queue.append((next_map, path + [next_map]))

        return []

    def _build_multi_map_path(
        self,
        map_sequence: list[str],
        from_x: int,
        from_y: int,
        to_x: int | None,
        to_y: int | None,
        hms_available: list[str],
        weights: TileWeights,
        defeated_trainers: set[str],
    ) -> CrossMapPath:
        """Build detailed path through multiple maps.

        Args:
            map_sequence: Ordered list of maps to traverse
            from_x: Starting X in first map
            from_y: Starting Y in first map
            to_x: Goal X in final map (optional)
            to_y: Goal Y in final map (optional)
            hms_available: Available HMs
            weights: Tile weight preferences
            defeated_trainers: Defeated trainer IDs

        Returns:
            CrossMapPath with all segments
        """
        segments: list[tuple[str, list[str]]] = []
        transitions: list[MapTransition] = []
        all_hms: set[str] = set()
        total_moves = 0

        current_x, current_y = from_x, from_y

        for i, map_id in enumerate(map_sequence):
            graph = self._get_map(map_id)

            # Set up trainer avoidance
            if weights.trainer_adjacent > 1:
                zones = get_all_trainer_zones(
                    graph.trainers,
                    defeated_trainers,
                    graph.width,
                    graph.height,
                )
                graph.set_trainer_zones(zones)

            # Determine goal for this segment
            if i == len(map_sequence) - 1:
                # Final map - go to specified goal or center
                goal_x = to_x if to_x is not None else graph.width // 2
                goal_y = to_y if to_y is not None else graph.height // 2
            else:
                # Intermediate map - find exit to next map
                next_map = map_sequence[i + 1]
                exit_pos = self._find_exit_to(graph, next_map)
                if not exit_pos:
                    return CrossMapPath(
                        success=False,
                        segments=segments,
                        maps_traversed=map_sequence[: i + 1],
                    )
                goal_x, goal_y = exit_pos

            start = Node(current_x, current_y)
            goal = Node(goal_x, goal_y)

            result = astar(graph, start, goal, hms_available, weights)

            if not result.success:
                return CrossMapPath(
                    success=False,
                    segments=segments,
                    maps_traversed=map_sequence[: i + 1],
                )

            segments.append((map_id, result.moves))
            all_hms.update(result.hms_required)
            total_moves += len(result.moves)

            # Prepare for next map
            if i < len(map_sequence) - 1:
                next_map = map_sequence[i + 1]
                entry_pos = self._find_entry_from(
                    self._get_map(next_map), map_id, goal_x, goal_y
                )
                if entry_pos:
                    current_x, current_y = entry_pos
                    transitions.append(
                        MapTransition(
                            from_map=map_id,
                            from_pos=(goal_x, goal_y),
                            to_map=next_map,
                            to_pos=entry_pos,
                            transition_type="connection",
                        )
                    )
                else:
                    # Default to center of next map
                    next_graph = self._get_map(next_map)
                    current_x = next_graph.width // 2
                    current_y = next_graph.height // 2

        return CrossMapPath(
            success=True,
            segments=segments,
            maps_traversed=map_sequence,
            total_moves=total_moves,
            hms_required=list(all_hms),
            transitions=transitions,
        )

    def _find_exit_to(
        self, graph: MapGraph, target_map: str
    ) -> tuple[int, int] | None:
        """Find exit position from a map to reach another map.

        Args:
            graph: Current map graph
            target_map: Map we want to reach

        Returns:
            (x, y) of exit position, or None
        """
        target_norm = self._normalize_map_id(target_map)

        # Check warps
        for warp in graph.warps:
            dest = self._normalize_map_id(warp.get("destination_map", ""))
            if dest == target_norm:
                return warp.get("x", 0), warp.get("y", 0)

        # Check connections
        for direction, conn in graph.connections.items():
            dest = self._normalize_map_id(conn.get("map", ""))
            if dest == target_norm:
                # Return edge of map in that direction
                if direction == "NORTH":
                    return graph.width // 2, 0
                elif direction == "SOUTH":
                    return graph.width // 2, graph.height - 1
                elif direction == "EAST":
                    return graph.width - 1, graph.height // 2
                elif direction == "WEST":
                    return 0, graph.height // 2

        return None

    def _find_entry_from(
        self,
        graph: MapGraph,
        from_map: str,
        exit_x: int,
        exit_y: int,
    ) -> tuple[int, int] | None:
        """Find entry position when entering a map from another.

        Args:
            graph: Target map graph
            from_map: Map we're coming from
            exit_x: X position we exited from
            exit_y: Y position we exited from

        Returns:
            (x, y) of entry position, or None
        """
        from_norm = self._normalize_map_id(from_map)

        # Check connections
        for direction, conn in graph.connections.items():
            dest = self._normalize_map_id(conn.get("map", ""))
            if dest == from_norm:
                offset = conn.get("offset", 0)
                # Return entry edge based on direction
                if direction == "NORTH":
                    return exit_x + offset, graph.height - 1
                elif direction == "SOUTH":
                    return exit_x + offset, 0
                elif direction == "EAST":
                    return 0, exit_y + offset
                elif direction == "WEST":
                    return graph.width - 1, exit_y + offset

        # For warps, just use center of map
        return graph.width // 2, graph.height // 2
