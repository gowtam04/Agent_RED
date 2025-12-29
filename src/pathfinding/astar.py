"""A* pathfinding implementation."""

from collections.abc import Callable
from dataclasses import dataclass, field
from heapq import heappop, heappush

from .graph import MapGraph, Node
from .tiles import TileWeights


@dataclass
class PathResult:
    """Result of A* pathfinding."""

    success: bool
    path: list[Node] = field(default_factory=list)
    moves: list[str] = field(default_factory=list)
    total_cost: float = 0.0
    hms_required: list[str] = field(default_factory=list)
    nodes_explored: int = 0


def heuristic(a: Node, b: Node) -> float:
    """Manhattan distance heuristic for A*.

    Args:
        a: First node
        b: Second node

    Returns:
        Manhattan distance between nodes
    """
    return abs(a.x - b.x) + abs(a.y - b.y)


def reconstruct_path(
    came_from: dict[Node, Node],
    current: Node,
) -> list[Node]:
    """Reconstruct the path from start to current node.

    Args:
        came_from: Map of node -> previous node
        current: The goal node

    Returns:
        List of nodes from start to goal
    """
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def path_to_moves(path: list[Node]) -> list[str]:
    """Convert a path of nodes to movement directions.

    Args:
        path: List of nodes representing the path

    Returns:
        List of direction strings (UP, DOWN, LEFT, RIGHT)
    """
    moves = []
    for i in range(1, len(path)):
        prev = path[i - 1]
        curr = path[i]

        dx = curr.x - prev.x
        dy = curr.y - prev.y

        if dy < 0:
            moves.append("UP")
        elif dy > 0:
            moves.append("DOWN")
        elif dx < 0:
            moves.append("LEFT")
        elif dx > 0:
            moves.append("RIGHT")

    return moves


def astar(
    graph: MapGraph,
    start: Node,
    goal: Node,
    hms_available: list[str] | None = None,
    weights: TileWeights | None = None,
    max_iterations: int = 10000,
) -> PathResult:
    """A* pathfinding on a single map.

    Finds the lowest-cost path from start to goal on a single map.
    Does not handle cross-map routing.

    Args:
        graph: The map graph to search
        start: Starting node
        goal: Goal node
        hms_available: List of usable HMs (e.g., ["CUT", "SURF"])
        weights: Tile weight preferences
        max_iterations: Maximum search iterations to prevent infinite loops

    Returns:
        PathResult with path information or failure indication
    """
    hms_available = hms_available or []
    weights = weights or TileWeights()

    # Check if start or goal are valid
    if not graph.in_bounds(start.x, start.y):
        return PathResult(success=False)
    if not graph.in_bounds(goal.x, goal.y):
        return PathResult(success=False)

    # Priority queue: (f_score, counter, node)
    # Counter ensures stable ordering when f_scores are equal
    counter = 0
    open_set: list[tuple[float, int, Node]] = [(0, counter, start)]
    open_set_lookup: set[Node] = {start}

    # Track path reconstruction
    came_from: dict[Node, Node] = {}

    # Cost tracking
    g_score: dict[Node, float] = {start: 0}
    f_score: dict[Node, float] = {start: heuristic(start, goal)}

    # Track HMs used at each node
    hm_used_at: dict[Node, str] = {}

    iterations = 0
    while open_set and iterations < max_iterations:
        iterations += 1

        # Pop node with lowest f_score
        _, _, current = heappop(open_set)
        open_set_lookup.discard(current)

        # Check if we reached the goal
        if current == goal:
            path = reconstruct_path(came_from, current)
            moves = path_to_moves(path)

            # Collect HMs used
            hms_used = set()
            for node in path:
                if node in hm_used_at:
                    hms_used.add(hm_used_at[node])

            return PathResult(
                success=True,
                path=path,
                moves=moves,
                total_cost=g_score[current],
                hms_required=list(hms_used),
                nodes_explored=iterations,
            )

        # Explore neighbors
        for edge in graph.neighbors(current, hms_available, weights):
            neighbor = edge.destination
            tentative_g = g_score[current] + edge.cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                # Found a better path
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                f_score[neighbor] = tentative_g + heuristic(neighbor, goal)

                # Track HM usage
                if edge.requires_hm:
                    hm_used_at[neighbor] = edge.requires_hm

                # Add to open set if not already there
                if neighbor not in open_set_lookup:
                    counter += 1
                    heappush(open_set, (f_score[neighbor], counter, neighbor))
                    open_set_lookup.add(neighbor)

    # No path found
    return PathResult(
        success=False,
        nodes_explored=iterations,
    )


def find_nearest(
    graph: MapGraph,
    start: Node,
    condition: Callable[[int, int], bool],
    hms_available: list[str] | None = None,
    weights: TileWeights | None = None,
    max_iterations: int = 5000,
) -> PathResult:
    """Find the nearest tile that satisfies a condition.

    Uses Dijkstra's algorithm (A* with zero heuristic) to find
    the nearest tile that matches the given condition.

    Args:
        graph: The map graph to search
        start: Starting node
        condition: Function (x, y) -> bool that returns True for target tiles
        hms_available: List of usable HMs
        weights: Tile weight preferences
        max_iterations: Maximum search iterations

    Returns:
        PathResult to the nearest matching tile, or failure
    """
    hms_available = hms_available or []
    weights = weights or TileWeights()

    counter = 0
    open_set: list[tuple[float, int, Node]] = [(0, counter, start)]
    open_set_lookup: set[Node] = {start}

    came_from: dict[Node, Node] = {}
    g_score: dict[Node, float] = {start: 0}
    hm_used_at: dict[Node, str] = {}

    iterations = 0
    while open_set and iterations < max_iterations:
        iterations += 1

        _, _, current = heappop(open_set)
        open_set_lookup.discard(current)

        # Check if current satisfies condition
        if condition(current.x, current.y):
            path = reconstruct_path(came_from, current)
            moves = path_to_moves(path)

            hms_used = set()
            for node in path:
                if node in hm_used_at:
                    hms_used.add(hm_used_at[node])

            return PathResult(
                success=True,
                path=path,
                moves=moves,
                total_cost=g_score[current],
                hms_required=list(hms_used),
                nodes_explored=iterations,
            )

        for edge in graph.neighbors(current, hms_available, weights):
            neighbor = edge.destination
            tentative_g = g_score[current] + edge.cost

            if tentative_g < g_score.get(neighbor, float("inf")):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g

                if edge.requires_hm:
                    hm_used_at[neighbor] = edge.requires_hm

                if neighbor not in open_set_lookup:
                    counter += 1
                    # No heuristic for Dijkstra
                    heappush(open_set, (tentative_g, counter, neighbor))
                    open_set_lookup.add(neighbor)

    return PathResult(
        success=False,
        nodes_explored=iterations,
    )
