"""Tests for pathfinding tile types and weights."""

import pytest
from src.pathfinding.tiles import (
    TileType,
    TileWeights,
    get_tile_weight,
    can_traverse_ledge,
    is_passable,
    classify_tile,
)


class TestTileType:
    """Tests for TileType enum."""

    def test_tile_types_exist(self):
        """Test that all expected tile types are defined."""
        assert TileType.BLOCKED == 0
        assert TileType.WALKABLE == 1
        assert TileType.GRASS == 2
        assert TileType.WATER == 3
        assert TileType.CUT_TREE == 4

    def test_tile_type_values_unique(self):
        """Test that all tile type values are unique."""
        values = [t.value for t in TileType]
        assert len(values) == len(set(values))


class TestTileWeights:
    """Tests for TileWeights configuration."""

    def test_default_weights(self):
        """Test default weight values."""
        weights = TileWeights()
        assert weights.walkable == 1.0
        assert weights.grass == 3.0
        assert weights.trainer_adjacent == 100.0

    def test_avoid_encounters_weights(self):
        """Test encounter avoidance preset."""
        weights = TileWeights.avoid_encounters()
        assert weights.grass == 5.0

    def test_seek_encounters_weights(self):
        """Test encounter seeking preset."""
        weights = TileWeights.seek_encounters()
        assert weights.grass == 0.5


class TestGetTileWeight:
    """Tests for get_tile_weight function."""

    def test_walkable_tile_weight(self):
        """Test weight for walkable tile."""
        weight = get_tile_weight(TileType.WALKABLE)
        assert weight == 1.0

    def test_grass_tile_weight(self):
        """Test weight for grass tile."""
        weight = get_tile_weight(TileType.GRASS)
        assert weight == 3.0

    def test_blocked_tile_weight(self):
        """Test weight for blocked tile is infinite."""
        weight = get_tile_weight(TileType.BLOCKED)
        assert weight == float("inf")

    def test_water_without_surf(self):
        """Test water is impassable without SURF."""
        weight = get_tile_weight(TileType.WATER, hms_available=[])
        assert weight == float("inf")

    def test_water_with_surf(self):
        """Test water is passable with SURF."""
        weight = get_tile_weight(TileType.WATER, hms_available=["SURF"])
        assert weight < float("inf")

    def test_cut_tree_without_cut(self):
        """Test cut tree is impassable without CUT."""
        weight = get_tile_weight(TileType.CUT_TREE, hms_available=[])
        assert weight == float("inf")

    def test_cut_tree_with_cut(self):
        """Test cut tree is passable with CUT."""
        weight = get_tile_weight(TileType.CUT_TREE, hms_available=["CUT"])
        assert weight < float("inf")

    def test_custom_weights(self):
        """Test using custom weight preferences."""
        weights = TileWeights(grass=10.0)
        weight = get_tile_weight(TileType.GRASS, weights=weights)
        assert weight == 10.0


class TestCanTraverseLedge:
    """Tests for ledge traversal."""

    def test_ledge_down_correct_direction(self):
        """Test ledge down can be traversed downward."""
        assert can_traverse_ledge(TileType.LEDGE_DOWN, "DOWN") is True

    def test_ledge_down_wrong_direction(self):
        """Test ledge down cannot be traversed upward."""
        assert can_traverse_ledge(TileType.LEDGE_DOWN, "UP") is False
        assert can_traverse_ledge(TileType.LEDGE_DOWN, "LEFT") is False
        assert can_traverse_ledge(TileType.LEDGE_DOWN, "RIGHT") is False

    def test_ledge_left_correct_direction(self):
        """Test ledge left can be traversed leftward."""
        assert can_traverse_ledge(TileType.LEDGE_LEFT, "LEFT") is True

    def test_ledge_right_correct_direction(self):
        """Test ledge right can be traversed rightward."""
        assert can_traverse_ledge(TileType.LEDGE_RIGHT, "RIGHT") is True


class TestIsPassable:
    """Tests for is_passable function."""

    def test_walkable_is_passable(self):
        """Test walkable tile is passable."""
        assert is_passable(TileType.WALKABLE) is True

    def test_blocked_is_not_passable(self):
        """Test blocked tile is not passable."""
        assert is_passable(TileType.BLOCKED) is False

    def test_water_passable_with_surf(self):
        """Test water passable with SURF HM."""
        assert is_passable(TileType.WATER, hms_available=["SURF"]) is True

    def test_water_not_passable_without_surf(self):
        """Test water not passable without SURF."""
        assert is_passable(TileType.WATER, hms_available=[]) is False


class TestClassifyTile:
    """Tests for tile classification."""

    def test_classify_walkable(self):
        """Test classifying a walkable tile."""
        walkable_tiles = {0, 1, 2, 3}
        result = classify_tile(1, walkable_tiles)
        assert result == TileType.WALKABLE

    def test_classify_blocked(self):
        """Test classifying a blocked tile."""
        walkable_tiles = {0, 1, 2, 3}
        result = classify_tile(99, walkable_tiles)
        assert result == TileType.BLOCKED

    def test_classify_grass(self):
        """Test classifying a grass tile."""
        walkable_tiles = {0, 1, 82}
        result = classify_tile(82, walkable_tiles, grass_tile=82)
        assert result == TileType.GRASS
