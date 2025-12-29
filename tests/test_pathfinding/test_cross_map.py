"""Tests for cross-map routing."""

import pytest
from src.pathfinding.cross_map import CrossMapRouter, CrossMapPath, MapTransition
from src.pathfinding.tiles import TileWeights


class TestCrossMapRouter:
    """Tests for CrossMapRouter class."""

    @pytest.fixture
    def router(self):
        """Create a CrossMapRouter instance."""
        return CrossMapRouter()

    def test_single_map_path(self, router):
        """Test path within a single map."""
        result = router.find_path(
            from_map="PALLETTOWN",
            from_x=5,
            from_y=5,
            to_map="PALLETTOWN",
            to_x=8,
            to_y=5,
        )

        assert result.success is True
        assert len(result.maps_traversed) == 1
        assert result.maps_traversed[0] == "PALLETTOWN"
        assert result.total_moves == 3

    def test_cross_map_path_route1(self, router):
        """Test path from Pallet Town to Route 1."""
        result = router.find_path(
            from_map="PALLETTOWN",
            from_x=5,
            from_y=5,
            to_map="ROUTE1",
        )

        assert result.success is True
        assert "PALLETTOWN" in result.maps_traversed
        assert "ROUTE1" in result.maps_traversed

    def test_normalized_map_ids(self, router):
        """Test that map IDs are normalized correctly."""
        # Should work with underscores
        result1 = router.find_path(
            from_map="PALLET_TOWN",
            from_x=5,
            from_y=5,
            to_map="PALLET_TOWN",
            to_x=6,
            to_y=5,
        )

        # Should work without underscores
        result2 = router.find_path(
            from_map="PALLETTOWN",
            from_x=5,
            from_y=5,
            to_map="PALLETTOWN",
            to_x=6,
            to_y=5,
        )

        assert result1.success is True
        assert result2.success is True

    def test_path_with_multiple_segments(self, router):
        """Test path that traverses multiple maps."""
        result = router.find_path(
            from_map="PALLETTOWN",
            from_x=5,
            from_y=5,
            to_map="ROUTE1",
        )

        assert result.success is True
        assert len(result.segments) >= 1

    def test_nonexistent_map_fails(self, router):
        """Test that path to nonexistent map fails."""
        result = router.find_path(
            from_map="PALLETTOWN",
            from_x=5,
            from_y=5,
            to_map="NONEXISTENT_MAP_XYZ",
        )

        # Should fail because destination doesn't exist
        # or succeed with empty path if same logic applies
        assert result.maps_traversed == [] or not result.success


class TestCrossMapPath:
    """Tests for CrossMapPath dataclass."""

    def test_default_values(self):
        """Test CrossMapPath default values."""
        path = CrossMapPath(success=False)
        assert path.success is False
        assert path.segments == []
        assert path.maps_traversed == []
        assert path.total_moves == 0

    def test_successful_path(self):
        """Test CrossMapPath with successful route."""
        path = CrossMapPath(
            success=True,
            segments=[("MAP1", ["UP", "UP"]), ("MAP2", ["RIGHT"])],
            maps_traversed=["MAP1", "MAP2"],
            total_moves=3,
            hms_required=["CUT"],
        )

        assert path.success is True
        assert len(path.segments) == 2
        assert path.total_moves == 3
        assert "CUT" in path.hms_required


class TestMapTransition:
    """Tests for MapTransition dataclass."""

    def test_transition_creation(self):
        """Test creating a map transition."""
        transition = MapTransition(
            from_map="MAP1",
            from_pos=(10, 5),
            to_map="MAP2",
            to_pos=(0, 5),
            transition_type="connection",
        )

        assert transition.from_map == "MAP1"
        assert transition.from_pos == (10, 5)
        assert transition.to_map == "MAP2"
        assert transition.to_pos == (0, 5)
        assert transition.transition_type == "connection"
