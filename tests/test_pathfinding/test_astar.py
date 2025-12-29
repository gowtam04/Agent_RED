"""Tests for A* pathfinding algorithm."""

import pytest
from src.pathfinding.graph import Node, MapGraph
from src.pathfinding.astar import astar, path_to_moves, heuristic, PathResult
from src.pathfinding.tiles import TileWeights


class TestHeuristic:
    """Tests for Manhattan distance heuristic."""

    def test_same_position(self):
        """Test heuristic for same position is zero."""
        a = Node(5, 5)
        b = Node(5, 5)
        assert heuristic(a, b) == 0

    def test_horizontal_distance(self):
        """Test heuristic for horizontal movement."""
        a = Node(0, 0)
        b = Node(5, 0)
        assert heuristic(a, b) == 5

    def test_vertical_distance(self):
        """Test heuristic for vertical movement."""
        a = Node(0, 0)
        b = Node(0, 7)
        assert heuristic(a, b) == 7

    def test_diagonal_distance(self):
        """Test heuristic for diagonal (Manhattan distance)."""
        a = Node(0, 0)
        b = Node(3, 4)
        assert heuristic(a, b) == 7  # 3 + 4


class TestPathToMoves:
    """Tests for converting paths to move directions."""

    def test_empty_path(self):
        """Test empty path returns no moves."""
        assert path_to_moves([]) == []

    def test_single_node(self):
        """Test single node returns no moves."""
        assert path_to_moves([Node(0, 0)]) == []

    def test_move_right(self):
        """Test rightward movement."""
        path = [Node(0, 0), Node(1, 0)]
        assert path_to_moves(path) == ["RIGHT"]

    def test_move_left(self):
        """Test leftward movement."""
        path = [Node(1, 0), Node(0, 0)]
        assert path_to_moves(path) == ["LEFT"]

    def test_move_down(self):
        """Test downward movement."""
        path = [Node(0, 0), Node(0, 1)]
        assert path_to_moves(path) == ["DOWN"]

    def test_move_up(self):
        """Test upward movement."""
        path = [Node(0, 1), Node(0, 0)]
        assert path_to_moves(path) == ["UP"]

    def test_complex_path(self):
        """Test complex path with multiple directions."""
        path = [
            Node(0, 0),
            Node(1, 0),  # RIGHT
            Node(1, 1),  # DOWN
            Node(1, 2),  # DOWN
            Node(2, 2),  # RIGHT
        ]
        expected = ["RIGHT", "DOWN", "DOWN", "RIGHT"]
        assert path_to_moves(path) == expected


class TestAstarAlgorithm:
    """Tests for A* pathfinding."""

    def test_same_start_and_goal(self):
        """Test when start equals goal."""
        graph = MapGraph("PALLETTOWN")
        start = Node(5, 5)
        goal = Node(5, 5)

        result = astar(graph, start, goal)

        assert result.success is True
        assert len(result.moves) == 0
        assert result.total_cost == 0

    def test_simple_horizontal_path(self):
        """Test simple horizontal path."""
        graph = MapGraph("PALLETTOWN")
        start = Node(0, 5)
        goal = Node(3, 5)

        result = astar(graph, start, goal)

        assert result.success is True
        assert len(result.moves) == 3
        assert all(m == "RIGHT" for m in result.moves)

    def test_simple_vertical_path(self):
        """Test simple vertical path."""
        graph = MapGraph("PALLETTOWN")
        start = Node(5, 0)
        goal = Node(5, 3)

        result = astar(graph, start, goal)

        assert result.success is True
        assert len(result.moves) == 3
        assert all(m == "DOWN" for m in result.moves)

    def test_diagonal_path(self):
        """Test path with both horizontal and vertical movement."""
        graph = MapGraph("PALLETTOWN")
        start = Node(0, 0)
        goal = Node(3, 3)

        result = astar(graph, start, goal)

        assert result.success is True
        assert len(result.moves) == 6  # Manhattan distance

    def test_out_of_bounds_start(self):
        """Test with out-of-bounds start position."""
        graph = MapGraph("PALLETTOWN")
        start = Node(-1, -1)
        goal = Node(5, 5)

        result = astar(graph, start, goal)

        assert result.success is False

    def test_out_of_bounds_goal(self):
        """Test with out-of-bounds goal position."""
        graph = MapGraph("PALLETTOWN")
        start = Node(5, 5)
        goal = Node(100, 100)

        result = astar(graph, start, goal)

        assert result.success is False

    def test_max_iterations_limit(self):
        """Test that max iterations prevents infinite loops."""
        graph = MapGraph("PALLETTOWN")
        start = Node(0, 0)
        goal = Node(9, 8)

        # Use very low max iterations
        result = astar(graph, start, goal, max_iterations=5)

        # Should fail due to iteration limit
        assert result.nodes_explored <= 5


class TestPathResult:
    """Tests for PathResult dataclass."""

    def test_default_values(self):
        """Test PathResult default values."""
        result = PathResult(success=True)
        assert result.success is True
        assert result.path == []
        assert result.moves == []
        assert result.total_cost == 0.0
        assert result.hms_required == []
        assert result.nodes_explored == 0

    def test_with_path_data(self):
        """Test PathResult with actual path data."""
        path = [Node(0, 0), Node(1, 0), Node(2, 0)]
        moves = ["RIGHT", "RIGHT"]
        result = PathResult(
            success=True,
            path=path,
            moves=moves,
            total_cost=2.0,
            nodes_explored=5,
        )
        assert result.success is True
        assert len(result.path) == 3
        assert len(result.moves) == 2
        assert result.total_cost == 2.0
