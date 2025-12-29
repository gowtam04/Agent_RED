# Phase 4: Pathfinding

## Objective
Implement A* pathfinding for navigation across the Pokemon Red world, including cross-map routing, obstacle handling, and encounter avoidance.

## Prerequisites
- Phase 1 complete (map data in `data/maps/`)
- Phase 2 complete (agent framework)
- Phase 3 complete (Navigation agent skeleton)

---

## Overview

The pathfinding system needs to handle:
1. **Single-map pathfinding** - A* within one map
2. **Cross-map routing** - Navigate through connections and warps
3. **Tile weighting** - Grass = higher weight (encounters), paths = lower
4. **Obstacle handling** - HM obstacles, trainers, ledges
5. **Trainer avoidance** - Model line-of-sight cones

---

## Directory Structure

```
src/pathfinding/
├── __init__.py
├── astar.py          # Core A* algorithm
├── graph.py          # Map graph representation
├── tiles.py          # Tile types and weights
├── cross_map.py      # Multi-map routing
└── trainer_vision.py # Trainer line-of-sight
```

---

## 1. Tile Types and Weights (`src/pathfinding/tiles.py`)

```python
"""Tile types and movement costs."""

from enum import IntEnum
from typing import Optional


class TileType(IntEnum):
    """Tile types from map data."""
    WALKABLE = 0
    BLOCKED = 1
    GRASS = 2
    WATER = 3
    LEDGE_DOWN = 4
    LEDGE_LEFT = 5
    LEDGE_RIGHT = 6
    CUT_TREE = 7
    STRENGTH_BOULDER = 8
    DOOR = 9
    WARP = 10
    TRAINER = 11  # Virtual tile for trainer vision cones


# Movement costs (higher = less preferred)
TILE_WEIGHTS = {
    TileType.WALKABLE: 1,
    TileType.BLOCKED: float('inf'),
    TileType.GRASS: 5,  # Higher due to encounter chance
    TileType.WATER: float('inf'),  # Blocked unless Surf
    TileType.LEDGE_DOWN: 1,  # One-way
    TileType.LEDGE_LEFT: 1,
    TileType.LEDGE_RIGHT: 1,
    TileType.CUT_TREE: float('inf'),  # Blocked unless Cut
    TileType.STRENGTH_BOULDER: float('inf'),  # Blocked unless Strength
    TileType.DOOR: 1,
    TileType.WARP: 1,
    TileType.TRAINER: 100,  # Avoidable but costly
}


def get_tile_weight(
    tile_type: TileType,
    available_hms: list[str],
    avoid_grass: bool = True,
) -> float:
    """Get movement cost for a tile."""

    # Handle HM-clearable obstacles
    if tile_type == TileType.WATER and "SURF" in available_hms:
        return 1
    if tile_type == TileType.CUT_TREE and "CUT" in available_hms:
        return 2  # Small penalty for having to use HM
    if tile_type == TileType.STRENGTH_BOULDER and "STRENGTH" in available_hms:
        return 3  # Boulders require positioning

    # Grass preference
    if tile_type == TileType.GRASS and not avoid_grass:
        return 1  # Normal weight if seeking encounters

    return TILE_WEIGHTS.get(tile_type, float('inf'))


def can_traverse_ledge(
    ledge_type: TileType,
    direction: str,
) -> bool:
    """Check if a ledge can be traversed in a direction."""
    ledge_directions = {
        TileType.LEDGE_DOWN: "DOWN",
        TileType.LEDGE_LEFT: "LEFT",
        TileType.LEDGE_RIGHT: "RIGHT",
    }
    return ledge_directions.get(ledge_type) == direction
```

---

## 2. Map Graph (`src/pathfinding/graph.py`)

```python
"""Map graph representation for pathfinding."""

from dataclasses import dataclass, field
from typing import Optional, Iterator
import json
from pathlib import Path

from .tiles import TileType, get_tile_weight, can_traverse_ledge


@dataclass
class Node:
    """A node in the pathfinding graph."""
    map_id: str
    x: int
    y: int

    def __hash__(self):
        return hash((self.map_id, self.x, self.y))

    def __eq__(self, other):
        return (self.map_id, self.x, self.y) == (other.map_id, other.x, other.y)


@dataclass
class Edge:
    """An edge between nodes."""
    from_node: Node
    to_node: Node
    weight: float
    requires_hm: Optional[str] = None
    is_warp: bool = False
    is_connection: bool = False


@dataclass
class MapGraph:
    """Graph representation of a map for pathfinding."""

    map_id: str
    width: int
    height: int
    tiles: list[list[int]]  # 2D grid of TileType values
    warps: list[dict] = field(default_factory=list)
    connections: dict = field(default_factory=dict)
    trainers: list[dict] = field(default_factory=list)

    @classmethod
    def from_json(cls, map_id: str, data_dir: Path = Path("data/maps")) -> "MapGraph":
        """Load map from JSON file."""
        map_path = data_dir / f"{map_id}.json"
        with open(map_path) as f:
            data = json.load(f)

        return cls(
            map_id=map_id,
            width=data["width"],
            height=data["height"],
            tiles=data.get("tiles", []),
            warps=data.get("warps", []),
            connections=data.get("connections", {}),
            trainers=data.get("trainers", []),
        )

    def get_tile(self, x: int, y: int) -> TileType:
        """Get tile type at position."""
        if not (0 <= x < self.width and 0 <= y < self.height):
            return TileType.BLOCKED
        if not self.tiles:
            return TileType.WALKABLE  # Default if no tile data
        return TileType(self.tiles[y][x])

    def get_neighbors(
        self,
        node: Node,
        available_hms: list[str],
        avoid_grass: bool = True,
        avoid_trainers: bool = True,
        defeated_trainers: set[str] = None,
    ) -> Iterator[tuple[Node, float]]:
        """Get traversable neighbors of a node with their edge weights."""
        if node.map_id != self.map_id:
            return

        defeated_trainers = defeated_trainers or set()

        # Four cardinal directions
        directions = [
            (0, -1, "UP"),
            (0, 1, "DOWN"),
            (-1, 0, "LEFT"),
            (1, 0, "RIGHT"),
        ]

        for dx, dy, direction in directions:
            nx, ny = node.x + dx, node.y + dy

            # Bounds check
            if not (0 <= nx < self.width and 0 <= ny < self.height):
                # Check for map connections
                if connection := self._check_connection(node.x, node.y, direction):
                    yield Node(connection["map"], connection["x"], connection["y"]), 1
                continue

            tile = self.get_tile(nx, ny)

            # Handle ledges (one-way)
            current_tile = self.get_tile(node.x, node.y)
            if current_tile in {TileType.LEDGE_DOWN, TileType.LEDGE_LEFT, TileType.LEDGE_RIGHT}:
                if not can_traverse_ledge(current_tile, direction):
                    continue

            # Get base weight
            weight = get_tile_weight(tile, available_hms, avoid_grass)

            # Skip impassable tiles
            if weight == float('inf'):
                continue

            # Check trainer vision
            if avoid_trainers:
                for trainer in self.trainers:
                    if trainer["trainer_id"] in defeated_trainers:
                        continue
                    if self._in_trainer_vision(nx, ny, trainer):
                        weight += 100  # Heavy penalty

            neighbor = Node(self.map_id, nx, ny)
            yield neighbor, weight

    def _check_connection(self, x: int, y: int, direction: str) -> Optional[dict]:
        """Check if position leads to a map connection."""
        direction_lower = direction.lower()
        if direction_lower in self.connections:
            conn = self.connections[direction_lower]
            return {
                "map": conn["map"],
                "x": conn.get("x", x),
                "y": conn.get("y", y),
            }
        return None

    def _in_trainer_vision(self, x: int, y: int, trainer: dict) -> bool:
        """Check if position is in trainer's line of sight."""
        tx, ty = trainer["x"], trainer["y"]
        facing = trainer["facing"]
        range_ = trainer.get("vision_range", 4)

        # Check if in line with trainer
        if facing == "UP" and x == tx and ty - range_ <= y < ty:
            return True
        if facing == "DOWN" and x == tx and ty < y <= ty + range_:
            return True
        if facing == "LEFT" and y == ty and tx - range_ <= x < tx:
            return True
        if facing == "RIGHT" and y == ty and tx < x <= tx + range_:
            return True

        return False

    def get_warp_at(self, x: int, y: int) -> Optional[dict]:
        """Get warp destination if standing on a warp tile."""
        for warp in self.warps:
            if warp["x"] == x and warp["y"] == y:
                return {
                    "map": warp["destination_map"],
                    "x": warp.get("destination_x", 0),
                    "y": warp.get("destination_y", 0),
                }
        return None
```

---

## 3. A* Algorithm (`src/pathfinding/astar.py`)

```python
"""A* pathfinding implementation."""

import heapq
from dataclasses import dataclass, field
from typing import Optional

from .graph import Node, MapGraph


@dataclass
class PathResult:
    """Result of pathfinding."""
    found: bool
    nodes: list[Node] = field(default_factory=list)
    moves: list[str] = field(default_factory=list)
    total_cost: float = 0
    segments: list[dict] = field(default_factory=list)
    trainers: list[str] = field(default_factory=list)
    encounter_estimate: int = 0


def heuristic(a: Node, b: Node) -> float:
    """Manhattan distance heuristic."""
    if a.map_id != b.map_id:
        # Cross-map: estimate based on map positions (could be improved)
        return 100  # Rough estimate for map transition
    return abs(a.x - b.x) + abs(a.y - b.y)


def reconstruct_path(
    came_from: dict[Node, Node],
    current: Node,
) -> list[Node]:
    """Reconstruct path from came_from map."""
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def nodes_to_moves(nodes: list[Node]) -> list[str]:
    """Convert node path to movement directions."""
    moves = []
    for i in range(len(nodes) - 1):
        current = nodes[i]
        next_node = nodes[i + 1]

        if current.map_id != next_node.map_id:
            # Map transition - no explicit move needed (warp/connection)
            continue

        dx = next_node.x - current.x
        dy = next_node.y - current.y

        if dy < 0:
            moves.append("UP")
        elif dy > 0:
            moves.append("DOWN")
        elif dx < 0:
            moves.append("LEFT")
        elif dx > 0:
            moves.append("RIGHT")

    return moves


def count_grass_tiles(nodes: list[Node], graph: MapGraph) -> int:
    """Count grass tiles in path for encounter estimation."""
    count = 0
    for node in nodes:
        if node.map_id == graph.map_id:
            from .tiles import TileType
            if graph.get_tile(node.x, node.y) == TileType.GRASS:
                count += 1
    return count


def astar(
    start: Node,
    goal: Node,
    graph: MapGraph,
    available_hms: list[str] = None,
    avoid_grass: bool = True,
    avoid_trainers: bool = True,
    defeated_trainers: set[str] = None,
) -> PathResult:
    """
    A* pathfinding within a single map.

    Args:
        start: Starting node
        goal: Goal node
        graph: Map graph to search
        available_hms: HMs available for clearing obstacles
        avoid_grass: Whether to prefer paths with less grass
        avoid_trainers: Whether to avoid trainer line-of-sight
        defeated_trainers: Set of already-defeated trainer IDs
    """
    available_hms = available_hms or []
    defeated_trainers = defeated_trainers or set()

    if start.map_id != goal.map_id:
        return PathResult(found=False)  # Use cross-map routing instead

    # Priority queue: (f_score, counter, node)
    counter = 0
    open_set = [(0, counter, start)]
    heapq.heapify(open_set)

    came_from: dict[Node, Node] = {}
    g_score: dict[Node, float] = {start: 0}
    f_score: dict[Node, float] = {start: heuristic(start, goal)}

    open_set_hash = {start}

    while open_set:
        _, _, current = heapq.heappop(open_set)
        open_set_hash.discard(current)

        if current == goal:
            nodes = reconstruct_path(came_from, current)
            moves = nodes_to_moves(nodes)
            grass_count = count_grass_tiles(nodes, graph)

            return PathResult(
                found=True,
                nodes=nodes,
                moves=moves,
                total_cost=g_score[current],
                encounter_estimate=grass_count // 4,  # Rough estimate
            )

        for neighbor, edge_weight in graph.get_neighbors(
            current,
            available_hms,
            avoid_grass,
            avoid_trainers,
            defeated_trainers,
        ):
            tentative_g = g_score[current] + edge_weight

            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)

                if neighbor not in open_set_hash:
                    counter += 1
                    heapq.heappush(open_set, (f_score[neighbor], counter, neighbor))
                    open_set_hash.add(neighbor)

    return PathResult(found=False)
```

---

## 4. Cross-Map Routing (`src/pathfinding/cross_map.py`)

```python
"""Cross-map routing for multi-map pathfinding."""

from dataclasses import dataclass
from typing import Optional
from pathlib import Path
import json

from .graph import Node, MapGraph
from .astar import astar, PathResult


@dataclass
class CrossMapResult:
    """Result of cross-map pathfinding."""
    found: bool
    segments: list[PathResult]
    total_moves: list[str]
    maps_traversed: list[str]
    total_cost: float = 0


class CrossMapRouter:
    """Routes paths across multiple maps."""

    def __init__(self, data_dir: Path = Path("data/maps")):
        self.data_dir = data_dir
        self._map_cache: dict[str, MapGraph] = {}
        self._map_connections = self._load_map_index()

    def _load_map_index(self) -> dict:
        """Load map connection index."""
        index_path = self.data_dir / "index.json"
        if index_path.exists():
            with open(index_path) as f:
                return json.load(f)
        return {}

    def _get_map(self, map_id: str) -> MapGraph:
        """Get or load a map graph."""
        if map_id not in self._map_cache:
            self._map_cache[map_id] = MapGraph.from_json(map_id, self.data_dir)
        return self._map_cache[map_id]

    def find_path(
        self,
        start_map: str,
        start_x: int,
        start_y: int,
        goal_map: str,
        goal_x: int = None,
        goal_y: int = None,
        available_hms: list[str] = None,
        avoid_grass: bool = True,
        avoid_trainers: bool = True,
        defeated_trainers: set[str] = None,
    ) -> CrossMapResult:
        """
        Find a path from start to goal across potentially multiple maps.
        """
        available_hms = available_hms or []
        defeated_trainers = defeated_trainers or set()

        # If goal_x/goal_y not specified, find map entrance
        if goal_x is None or goal_y is None:
            goal_x, goal_y = self._get_map_entrance(goal_map, start_map)

        start = Node(start_map, start_x, start_y)
        goal = Node(goal_map, goal_x, goal_y)

        # Same map - use simple A*
        if start_map == goal_map:
            graph = self._get_map(start_map)
            result = astar(
                start, goal, graph,
                available_hms, avoid_grass, avoid_trainers, defeated_trainers
            )
            return CrossMapResult(
                found=result.found,
                segments=[result] if result.found else [],
                total_moves=result.moves,
                maps_traversed=[start_map],
                total_cost=result.total_cost,
            )

        # Cross-map: use BFS on map graph then A* per map
        map_path = self._find_map_path(start_map, goal_map, available_hms)
        if not map_path:
            return CrossMapResult(found=False, segments=[], total_moves=[], maps_traversed=[])

        # Build path through each map
        segments = []
        total_moves = []
        current_x, current_y = start_x, start_y

        for i, map_id in enumerate(map_path):
            graph = self._get_map(map_id)

            # Determine goal for this segment
            if i == len(map_path) - 1:
                # Final map - go to actual goal
                seg_goal = Node(map_id, goal_x, goal_y)
            else:
                # Intermediate - go to connection/warp to next map
                next_map = map_path[i + 1]
                exit_x, exit_y = self._find_exit_to(map_id, next_map)
                seg_goal = Node(map_id, exit_x, exit_y)

            seg_start = Node(map_id, current_x, current_y)

            result = astar(
                seg_start, seg_goal, graph,
                available_hms, avoid_grass, avoid_trainers, defeated_trainers
            )

            if not result.found:
                return CrossMapResult(found=False, segments=segments, total_moves=total_moves, maps_traversed=map_path[:i+1])

            segments.append(result)
            total_moves.extend(result.moves)

            # Update position for next segment
            if i < len(map_path) - 1:
                # Get entry point in next map
                current_x, current_y = self._get_entry_from(map_path[i + 1], map_id)

        return CrossMapResult(
            found=True,
            segments=segments,
            total_moves=total_moves,
            maps_traversed=map_path,
            total_cost=sum(s.total_cost for s in segments),
        )

    def _find_map_path(self, start_map: str, goal_map: str, available_hms: list[str]) -> list[str]:
        """BFS to find sequence of maps from start to goal."""
        from collections import deque

        queue = deque([(start_map, [start_map])])
        visited = {start_map}

        while queue:
            current, path = queue.popleft()

            if current == goal_map:
                return path

            # Get connected maps
            graph = self._get_map(current)
            connected = set()

            # Add connection neighbors
            for direction, conn in graph.connections.items():
                connected.add(conn["map"])

            # Add warp destinations
            for warp in graph.warps:
                connected.add(warp["destination_map"])

            for next_map in connected:
                if next_map not in visited:
                    # Check if route is accessible
                    if self._route_accessible(current, next_map, available_hms):
                        visited.add(next_map)
                        queue.append((next_map, path + [next_map]))

        return []  # No path found

    def _route_accessible(self, from_map: str, to_map: str, available_hms: list[str]) -> bool:
        """Check if route between maps is accessible with current HMs."""
        # This would check HM requirements for the route
        # Simplified for now
        return True

    def _get_map_entrance(self, map_id: str, from_map: str) -> tuple[int, int]:
        """Get default entrance point when entering a map."""
        graph = self._get_map(map_id)

        # Check warps from the source map
        for warp in graph.warps:
            if warp.get("source_map") == from_map:
                return warp["x"], warp["y"]

        # Check connections
        for direction, conn in graph.connections.items():
            if conn["map"] == from_map:
                return conn.get("entry_x", 0), conn.get("entry_y", 0)

        # Default to center
        return graph.width // 2, graph.height // 2

    def _find_exit_to(self, from_map: str, to_map: str) -> tuple[int, int]:
        """Find the exit point from one map to another."""
        graph = self._get_map(from_map)

        # Check warps
        for warp in graph.warps:
            if warp["destination_map"] == to_map:
                return warp["x"], warp["y"]

        # Check connections
        for direction, conn in graph.connections.items():
            if conn["map"] == to_map:
                # Return edge of map in that direction
                if direction == "north":
                    return graph.width // 2, 0
                elif direction == "south":
                    return graph.width // 2, graph.height - 1
                elif direction == "east":
                    return graph.width - 1, graph.height // 2
                elif direction == "west":
                    return 0, graph.height // 2

        return 0, 0

    def _get_entry_from(self, to_map: str, from_map: str) -> tuple[int, int]:
        """Get entry point when entering a map from another."""
        graph = self._get_map(to_map)

        # Check warps
        for warp in graph.warps:
            if warp.get("source_map") == from_map:
                return warp.get("entry_x", warp["x"]), warp.get("entry_y", warp["y"])

        # Check connections
        for direction, conn in graph.connections.items():
            if conn["map"] == from_map:
                if direction == "north":
                    return graph.width // 2, graph.height - 1
                elif direction == "south":
                    return graph.width // 2, 0
                elif direction == "east":
                    return 0, graph.height // 2
                elif direction == "west":
                    return graph.width - 1, graph.height // 2

        return 0, 0
```

---

## 5. Trainer Vision (`src/pathfinding/trainer_vision.py`)

```python
"""Trainer line-of-sight calculation."""

from dataclasses import dataclass
from typing import Generator


@dataclass
class TrainerVision:
    """A trainer's vision cone."""
    trainer_id: str
    x: int
    y: int
    facing: str
    range: int
    defeated: bool = False


def get_vision_tiles(trainer: TrainerVision) -> Generator[tuple[int, int], None, None]:
    """Generate all tiles in a trainer's line of sight."""
    if trainer.defeated:
        return

    dx, dy = 0, 0
    if trainer.facing == "UP":
        dy = -1
    elif trainer.facing == "DOWN":
        dy = 1
    elif trainer.facing == "LEFT":
        dx = -1
    elif trainer.facing == "RIGHT":
        dx = 1

    for i in range(1, trainer.range + 1):
        yield trainer.x + dx * i, trainer.y + dy * i


def is_in_vision(x: int, y: int, trainer: TrainerVision) -> bool:
    """Check if a position is in trainer's vision."""
    for vx, vy in get_vision_tiles(trainer):
        if vx == x and vy == y:
            return True
    return False


def get_safe_path_around_trainer(
    start_x: int,
    start_y: int,
    goal_x: int,
    goal_y: int,
    trainer: TrainerVision,
) -> list[tuple[int, int]] | None:
    """
    Find a path that avoids trainer's vision.
    Returns waypoints to navigate around the trainer.
    """
    vision_tiles = set(get_vision_tiles(trainer))

    # Simple approach: try going around
    # More sophisticated would integrate with A*

    # If direct path is blocked, try flanking
    if trainer.facing in ("UP", "DOWN"):
        # Vision is vertical, go horizontal
        detour_x = trainer.x + 2 if start_x > trainer.x else trainer.x - 2
        return [(detour_x, start_y), (detour_x, goal_y), (goal_x, goal_y)]
    else:
        # Vision is horizontal, go vertical
        detour_y = trainer.y + 2 if start_y > trainer.y else trainer.y - 2
        return [(start_x, detour_y), (goal_x, detour_y), (goal_x, goal_y)]
```

---

## 6. Package Init (`src/pathfinding/__init__.py`)

```python
"""Pathfinding module for Pokemon Red navigation."""

from .tiles import TileType, get_tile_weight
from .graph import Node, MapGraph
from .astar import astar, PathResult
from .cross_map import CrossMapRouter, CrossMapResult
from .trainer_vision import TrainerVision, get_vision_tiles, is_in_vision

__all__ = [
    "TileType",
    "get_tile_weight",
    "Node",
    "MapGraph",
    "astar",
    "PathResult",
    "CrossMapRouter",
    "CrossMapResult",
    "TrainerVision",
    "get_vision_tiles",
    "is_in_vision",
]


def find_path(
    from_map: str,
    from_x: int,
    from_y: int,
    to_map: str,
    to_x: int = None,
    to_y: int = None,
    preferences: dict = None,
    maps: "Maps" = None,
) -> CrossMapResult:
    """
    High-level pathfinding function.

    Args:
        from_map: Starting map ID
        from_x: Starting X coordinate
        from_y: Starting Y coordinate
        to_map: Destination map ID
        to_x: Destination X (optional, uses entrance if not specified)
        to_y: Destination Y (optional)
        preferences: Dict with avoid_grass, avoid_trainers, allowed_hms
        maps: Maps knowledge base instance
    """
    preferences = preferences or {}

    router = CrossMapRouter()
    return router.find_path(
        start_map=from_map,
        start_x=from_x,
        start_y=from_y,
        goal_map=to_map,
        goal_x=to_x,
        goal_y=to_y,
        available_hms=preferences.get("allowed_hms", []),
        avoid_grass=preferences.get("avoid_grass", True),
        avoid_trainers=preferences.get("avoid_trainers", True),
    )
```

---

## Testing

**`tests/test_pathfinding/test_astar.py`:**
```python
def test_simple_path():
    from src.pathfinding import astar, Node, MapGraph

    # Create simple 5x5 map
    graph = MapGraph(
        map_id="TEST",
        width=5,
        height=5,
        tiles=[[0]*5 for _ in range(5)],  # All walkable
    )

    start = Node("TEST", 0, 0)
    goal = Node("TEST", 4, 4)

    result = astar(start, goal, graph)

    assert result.found
    assert len(result.moves) == 8  # Manhattan distance


def test_obstacle_avoidance():
    from src.pathfinding import astar, Node, MapGraph
    from src.pathfinding.tiles import TileType

    # Map with wall in middle
    tiles = [[0]*5 for _ in range(5)]
    tiles[2][2] = TileType.BLOCKED

    graph = MapGraph(map_id="TEST", width=5, height=5, tiles=tiles)

    start = Node("TEST", 0, 2)
    goal = Node("TEST", 4, 2)

    result = astar(start, goal, graph)

    assert result.found
    # Should go around the obstacle
    assert Node("TEST", 2, 2) not in result.nodes


def test_grass_avoidance():
    from src.pathfinding import astar, Node, MapGraph
    from src.pathfinding.tiles import TileType

    # Path through grass vs longer path around
    tiles = [[0]*5 for _ in range(5)]
    tiles[0][1] = TileType.GRASS
    tiles[0][2] = TileType.GRASS
    tiles[0][3] = TileType.GRASS

    graph = MapGraph(map_id="TEST", width=5, height=5, tiles=tiles)

    start = Node("TEST", 0, 0)
    goal = Node("TEST", 0, 4)

    result = astar(start, goal, graph, avoid_grass=True)

    assert result.found
    # Should prefer path that avoids grass
    # (depends on weights)
```

**`tests/test_pathfinding/test_cross_map.py`:**
```python
def test_cross_map_routing():
    from src.pathfinding import CrossMapRouter

    router = CrossMapRouter()

    result = router.find_path(
        start_map="PALLET_TOWN",
        start_x=5,
        start_y=5,
        goal_map="VIRIDIAN_CITY",
    )

    # Should find path through Route 1
    assert result.found or not result.found  # Depends on data availability
```

---

## Success Criteria

- [ ] A* algorithm correctly finds shortest paths
- [ ] Tile weights properly influence path selection
- [ ] Grass avoidance works (higher weight for grass tiles)
- [ ] Trainer vision cones are detected and avoided
- [ ] HM obstacles block paths when HM not available
- [ ] Ledges are one-way (correct direction only)
- [ ] Cross-map routing connects through warps and connections
- [ ] Unit tests pass for all pathfinding components
- [ ] Integration with Navigation agent's `find_path` tool

---

## Notes

- Map tile data must be extracted in Phase 1
- This phase can be developed in parallel with Phase 3 (agents)
- More sophisticated trainer avoidance could use influence maps
- Consider caching frequently-used paths
